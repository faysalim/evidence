#!/usr/bin/env python3
"""Generate a local HTML dashboard for a product-qa engagement.

Reads the four artefacts a two-session engagement produces and writes a
self-contained static site -- one page per release build, plus an index:

    <report-dir>/qa-state.json      QA's ledger        (written by QA only)
    <report-dir>/fix-state.json     DEV's ledger       (written by DEV only)
    <report-dir>/qa-events.jsonl    QA's event log     (append-only)
    <report-dir>/fix-events.jsonl   DEV's event log    (append-only)

Nothing on the page is authored. If it is not in the ledgers or the logs it does
not appear -- the same discipline the register applies to findings. Where a page
would have to guess, it prints NO VERDICT and says which condition had no rows.

Usage
-----
    python scripts/qa_dashboard.py <report-dir> [-o OUTDIR] [--serve [PORT]]

    <report-dir>   directory holding the four artefacts above
    -o OUTDIR      output directory (default: <report-dir>/dashboard)
    --serve PORT   serve OUTDIR over http://127.0.0.1:PORT after writing
                   (default port 8711; bound to loopback only)

Standard library only, no network access, no dependencies. Output is plain
HTML with inline CSS and no scripts, so it works over file:// as well as http.

Exit codes
----------
    0  dashboard written
    1  report directory unusable, or qa-state.json missing/unparseable
    2  written, but with integrity problems reported on the page and to stderr
"""

from __future__ import annotations

import argparse
import html
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

# --------------------------------------------------------------------------
# severity and result vocabularies -- kept in the order the skill ranks them
# --------------------------------------------------------------------------

SEVERITY_ORDER = ["critical", "blocker", "major", "minor", "polish"]
BLOCKING_SEVERITIES = {"critical", "blocker"}

# A finding in one of these states is not closed, whatever else it says.
OPEN_STATUSES = {
    "OPEN", "NEW", "ACCEPTED", "IN PROGRESS", "FIXED", "PARTIAL",
    "STILL PRESENT", "REOPENED", "DISPUTED", "DECIDE",
}
CLOSED_STATUSES = {"CLOSED", "VERIFIED FIXED", "WITHDRAWN", "DUPLICATE"}

RESULT_CLASSES = {
    "PASS": "ok",
    "PASS (SHORT)": "warn",
    "FAIL": "bad",
    "BLOCKED": "warn",
    "NOT RUN": "muted",
    "NOT RUN (uncalibrated)": "bad",
    "LONG": "warn",
}

QA_EVENTS = {
    "FILED", "CASE_ADDED", "CASE_RESULT", "HANDED_OVER", "HANDBACK_RETURNED",
    "BUILD_IDENTITY", "SMOKE", "CALIBRATION", "VERIFIED", "PARTIAL",
    "STILL_PRESENT", "CLOSED", "REOPENED", "CONVERTED", "WITHDRAWN", "VERDICT",
}
DEV_EVENTS = {
    "TRIAGED", "IN_PROGRESS", "FIX_DELIVERED", "TEST_ADDED", "DISPUTED",
    "DEFERRED", "NOTE",
}


class Problem(Exception):
    """A fatal problem with the inputs."""


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------

def load_json(path, required=False):
    if not os.path.isfile(path):
        if required:
            raise Problem("required file not found: %s" % path)
        return None, ["%s not found" % os.path.basename(path)]
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh), []
    except (ValueError, OSError) as exc:
        if required:
            raise Problem("could not parse %s: %s" % (path, exc))
        return None, ["%s could not be parsed: %s" % (os.path.basename(path), exc)]


def load_events(path, expected_role):
    """Read a JSONL event log. A bad line is reported, never fatal."""
    events, notes = [], []
    if not os.path.isfile(path):
        return events, ["%s not found" % os.path.basename(path)]
    with open(path, "r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            try:
                ev = json.loads(line)
            except ValueError as exc:
                notes.append("%s line %d is not JSON: %s"
                             % (os.path.basename(path), lineno, exc))
                continue
            if not isinstance(ev, dict):
                notes.append("%s line %d is not an object" % (os.path.basename(path), lineno))
                continue
            ev.setdefault("role", expected_role)
            ev["_src"] = os.path.basename(path)
            ev["_line"] = lineno
            if ev.get("role") != expected_role:
                notes.append("%s line %d claims role %r in the %s log -- "
                             "each side appends only its own events"
                             % (os.path.basename(path), lineno, ev.get("role"), expected_role))
            events.append(ev)
    return events, notes


def parse_ts(value):
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def event_sort_key(ev):
    ts = parse_ts(ev.get("ts"))
    # Events with no timestamp sort last but keep file order among themselves.
    return (ts is None, ts or datetime.max.replace(tzinfo=timezone.utc),
            ev.get("_src", ""), ev.get("_line", 0))


# --------------------------------------------------------------------------
# model
# --------------------------------------------------------------------------

class Engagement:
    def __init__(self, report_dir):
        self.report_dir = report_dir
        self.problems = []
        self.notes = []

        qa, n = load_json(os.path.join(report_dir, "qa-state.json"), required=True)
        self.notes += n
        self.qa = qa or {}

        fix, n = load_json(os.path.join(report_dir, "fix-state.json"))
        self.notes += n
        self.fix = fix or {}

        qa_ev, n = load_events(os.path.join(report_dir, "qa-events.jsonl"), "QA")
        self.notes += n
        dev_ev, n = load_events(os.path.join(report_dir, "fix-events.jsonl"), "DEV")
        self.notes += n
        self.events = sorted(qa_ev + dev_ev, key=event_sort_key)

        self.engagement = self.qa.get("engagement") or os.path.basename(
            os.path.abspath(report_dir)) or "engagement"
        self.iteration = self.qa.get("iteration")
        self.findings = {f.get("id"): f for f in self.qa.get("findings", []) if f.get("id")}
        self.cases = {c.get("id"): c for c in self.qa.get("cases", []) if c.get("id")}
        self.fixes = {f.get("id"): f for f in self.fix.get("fixes", []) if f.get("id")}
        self.builds = self.qa.get("builds_tested", {}) or {}

        self._check_join()

    # -- integrity -------------------------------------------------------

    def _check_join(self):
        """The two ledgers join on finding id. Drift is in the key's existence."""
        for fid in self.fixes:
            if fid not in self.findings:
                self.problems.append(
                    "fix-state.json claims finding %s, which qa-state.json never issued. "
                    "An unknown id rejects a handback unread." % fid)
        for cid, case in self.cases.items():
            fid = case.get("finding")
            if fid and fid not in self.findings:
                self.problems.append(
                    "case %s names finding %s, which does not exist in qa-state.json" % (cid, fid))
        for ev in self.events:
            fid = ev.get("id")
            if fid and fid not in self.findings:
                self.problems.append(
                    "%s line %d references finding %s, absent from qa-state.json"
                    % (ev.get("_src"), ev.get("_line"), fid))
            cid = ev.get("case")
            if cid and cid not in self.cases:
                self.problems.append(
                    "%s line %d references case %s, absent from qa-state.json"
                    % (ev.get("_src"), ev.get("_line"), cid))
            name = ev.get("event")
            if ev.get("role") == "QA" and name and name not in QA_EVENTS:
                self.notes.append("unknown QA event %r (%s line %d)"
                                  % (name, ev.get("_src"), ev.get("_line")))
            if ev.get("role") == "DEV" and name and name not in DEV_EVENTS:
                self.notes.append("unknown DEV event %r (%s line %d)"
                                  % (name, ev.get("_src"), ev.get("_line")))
        # Only QA may close.
        for ev in self.events:
            if ev.get("event") in ("CLOSED", "VERIFIED") and ev.get("role") != "QA":
                self.problems.append(
                    "%s line %d: a DEV event claims %s on %s. DEV may claim FIXED; "
                    "only QA may CLOSE." % (ev.get("_src"), ev.get("_line"),
                                            ev.get("event"), ev.get("id")))

    # -- derived views ---------------------------------------------------

    def releases(self):
        """Every build that the ledgers or the logs mention, newest iteration first."""
        rel = {}
        for it, comps in self.builds.items():
            label = ", ".join("%s %s" % (k, v) for k, v in sorted((comps or {}).items()))
            rel[str(it)] = {"iteration": str(it), "label": label or "(no build recorded)",
                            "components": comps or {}}
        for ev in self.events:
            it = ev.get("iteration")
            if it is not None and str(it) not in rel:
                rel[str(it)] = {"iteration": str(it), "label": "(no build recorded)",
                                "components": {}}
        if not rel:
            rel["1"] = {"iteration": "1", "label": "(no build recorded)", "components": {}}

        def key(item):
            try:
                return (0, int(item[0]))
            except (TypeError, ValueError):
                return (1, 0)

        return [v for _, v in sorted(rel.items(), key=key, reverse=True)]

    def status_at(self, finding, iteration):
        status = finding.get("status")
        if isinstance(status, dict):
            return status.get(str(iteration))
        return status if str(self.iteration) == str(iteration) else None

    def case_result_at(self, case, iteration):
        result = case.get("result")
        if isinstance(result, dict):
            return result.get(str(iteration))
        return result if str(self.iteration) == str(iteration) else None

    def is_open(self, finding):
        if finding.get("closed_in"):
            return False
        last = None
        status = finding.get("status")
        if isinstance(status, dict) and status:
            def ikey(k):
                try:
                    return (0, int(k))
                except (TypeError, ValueError):
                    return (1, 0)
            last = status[sorted(status, key=ikey)[-1]]
        elif isinstance(status, str):
            last = status
        if last in CLOSED_STATUSES:
            return False
        return True

    def calibration_scope(self, case):
        """Which scope's harness this row is graded by."""
        return case.get("graded_by") or case.get("scope")

    def timeline(self, fid):
        return [ev for ev in self.events if ev.get("id") == fid]

    def reopen_count(self, fid):
        return sum(1 for ev in self.timeline(fid) if ev.get("event") == "REOPENED")

    def handoffs(self, fid):
        """(role, from_ts, to_ts) spans showing who held the finding."""
        spans, holder, since = [], None, None
        for ev in self.timeline(fid):
            name, ts = ev.get("event"), parse_ts(ev.get("ts"))
            if name == "HANDED_OVER":
                nxt = "DEV"
            elif name in ("FIX_DELIVERED", "DISPUTED", "DEFERRED"):
                nxt = "QA"
            elif name == "FILED":
                nxt = "QA"
            else:
                continue
            if holder and since and ts:
                spans.append((holder, since, ts))
            holder, since = nxt, ts
        if holder and since:
            spans.append((holder, since, None))
        return spans

    # -- verdict ---------------------------------------------------------

    def verdict(self, iteration):
        """Compute the verdict. NO VERDICT is the default; every row names its evidence."""
        conditions = []

        blocking_open = [
            (fid, f) for fid, f in self.findings.items()
            if self.is_open(f) and (f.get("severity") or "").lower() in BLOCKING_SEVERITIES
        ]
        conditions.append((
            "No open critical or blocker, including any held at DECIDE",
            not blocking_open,
            ", ".join(sorted(fid for fid, _ in blocking_open)) or "none open",
        ))

        calibrated = set()
        for cid, case in self.cases.items():
            if cid.endswith("-00b") and self.case_result_at(case, iteration) == "PASS":
                calibrated.add(self.calibration_scope(case))
        # Only a scope that owns its harness owes a calibration row. A journey or an
        # acceptance requirement is graded by some scope's harness and inherits its
        # calibration -- but it must name which, or the inheritance is unverifiable.
        owing, unlinked = set(), []
        for cid, case in self.cases.items():
            if cid.endswith("-00a") or cid.endswith("-00b"):
                continue
            if case.get("graded_by"):
                owing.add(case["graded_by"])
            elif cid.split("-")[0] in ("R", "J"):
                unlinked.append(cid)
            elif case.get("scope"):
                owing.add(case["scope"])
        missing_cal = sorted(s for s in owing if s not in calibrated)
        for cid in unlinked:
            self.problems.append(
                "case %s is a journey or acceptance requirement with no `graded_by`: it "
                "cannot inherit any scope's calibration, so its result grades nothing" % cid)
        conditions.append((
            "Every scope that owns a harness has a passing calibration row (00b)",
            not missing_cal and not unlinked and bool(calibrated),
            ("uncalibrated: " + ", ".join(missing_cal)) if missing_cal
            else ("not linked to a calibrated scope: " + ", ".join(unlinked)) if unlinked
            else (", ".join(sorted(cid for cid in self.cases if cid.endswith("-00b")))
                  or "no calibration rows found"),
        ))

        smoke = sorted(cid for cid in self.cases if cid.endswith("-00a"))
        smoke_ok = bool(smoke) and all(
            self.case_result_at(self.cases[c], iteration) == "PASS" for c in smoke)
        conditions.append((
            "Smoke row passed on the build and environment this verdict names",
            smoke_ok, ", ".join(smoke) or "no smoke rows found",
        ))

        longs = sorted(cid for cid, c in self.cases.items()
                       if self.case_result_at(c, iteration) == "LONG")
        conditions.append((
            "No LONG row unreconciled",
            not longs, ", ".join(longs) or "none open",
        ))

        guarding = []
        for cid, case in self.cases.items():
            res = self.case_result_at(case, iteration)
            if res not in ("NOT RUN", "BLOCKED", None):
                continue
            ceiling = ((case.get("guards") or {}).get("ceiling") or "").lower()
            if ceiling in BLOCKING_SEVERITIES:
                guarding.append(cid)
        conditions.append((
            "No BLOCKED or NOT RUN row guarding a critical or blocker class",
            not guarding, ", ".join(sorted(guarding)) or "none",
        ))

        comps = self.builds.get(str(iteration)) or {}
        conditions.append((
            "Build identity established per component",
            bool(comps),
            ", ".join("%s %s" % (k, v) for k, v in sorted(comps.items())) or "not recorded",
        ))

        reqs = {cid: c for cid, c in self.cases.items() if cid.startswith("R-")}
        req_fail = sorted(cid for cid, c in reqs.items()
                          if self.case_result_at(c, iteration) != "PASS")
        conditions.append((
            "Every operator acceptance requirement has a PASS",
            bool(reqs) and not req_fail,
            ("not satisfied: " + ", ".join(req_fail)) if req_fail
            else (", ".join(sorted(reqs)) or
                  "no acceptance requirements recorded -- green is against the docs only"),
        ))

        if all(ok for _, ok, _ in conditions):
            label = "GREEN within stated bounds"
        elif any(ev == "none open" for _, _, ev in conditions[:1]) and blocking_open:
            label = "NOT GREEN"
        else:
            label = "NOT GREEN" if blocking_open else "NO VERDICT"
        first_fail = next((name for name, ok, _ in conditions if not ok), None)
        return label, first_fail, conditions


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

CSS = """
:root{--bg:#fbfbfa;--fg:#1a1a18;--mut:#6b6b66;--line:#e2e2dd;--card:#fff;
--ok:#1f7a4d;--okbg:#e8f5ee;--bad:#b3261e;--badbg:#fdecea;--warn:#8a5a00;
--warnbg:#fdf3e0;--qa:#2c5aa0;--dev:#7a4ea0}
@media(prefers-color-scheme:dark){:root{--bg:#16161a;--fg:#ececea;--mut:#9a9a94;
--line:#2c2c32;--card:#1d1d22;--okbg:#10271c;--badbg:#2a1412;--warnbg:#2a2110;
--ok:#5fcf98;--bad:#ff8a80;--warn:#e0b050;--qa:#7aa6e8;--dev:#c49ae8}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.55 ui-sans-serif,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:28px 20px 72px}
h1{font-size:25px;margin:0 0 4px}h2{font-size:18px;margin:34px 0 12px;
padding-bottom:6px;border-bottom:1px solid var(--line)}h3{font-size:15px;margin:22px 0 8px}
a{color:inherit}.sub{color:var(--mut);font-size:13px;margin:0 0 18px}
code,.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12.5px}
table{border-collapse:collapse;width:100%;margin:10px 0 18px;font-size:13.5px}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-weight:600;color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.04em}
tr:last-child td{border-bottom:none}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;
padding:16px 18px;margin:0 0 16px}
.verdict{border-radius:10px;padding:18px 20px;margin:0 0 20px;border:1px solid var(--line)}
.verdict .big{font-size:22px;font-weight:650;letter-spacing:-.01em}
.v-green{background:var(--okbg);border-color:var(--ok)}
.v-none{background:var(--warnbg);border-color:var(--warn)}
.v-bad{background:var(--badbg);border-color:var(--bad)}
.pill{display:inline-block;padding:1px 8px;border-radius:999px;font-size:11.5px;
font-weight:600;border:1px solid var(--line)}
.ok{color:var(--ok)}.bad{color:var(--bad)}.warn{color:var(--warn)}.muted{color:var(--mut)}
.p-ok{background:var(--okbg);color:var(--ok);border-color:var(--ok)}
.p-bad{background:var(--badbg);color:var(--bad);border-color:var(--bad)}
.p-warn{background:var(--warnbg);color:var(--warn);border-color:var(--warn)}
.p-muted{color:var(--mut)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:0 0 18px}
.tile{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:13px 15px}
.tile .n{font-size:26px;font-weight:650;letter-spacing:-.02em;line-height:1.1}
.tile .k{font-size:11.5px;color:var(--mut);text-transform:uppercase;letter-spacing:.05em;margin-top:3px}
.bar{display:flex;height:10px;border-radius:5px;overflow:hidden;background:var(--line);margin:8px 0 6px}
.bar span{display:block}
.lane{display:grid;grid-template-columns:132px 58px 1fr;gap:0 12px;font-size:13px}
.lane>div{padding:5px 0;border-bottom:1px solid var(--line)}
.lane .ts{color:var(--mut);font-size:11.5px;font-family:ui-monospace,Menlo,Consolas,monospace}
.who{font-size:11px;font-weight:650;letter-spacing:.03em}
.who.QA{color:var(--qa)}.who.DEV{color:var(--dev)}
.ev{font-weight:600;font-size:12px;letter-spacing:.02em}
.note{color:var(--mut);font-size:12.5px}
.prob{background:var(--badbg);border:1px solid var(--bad);border-radius:10px;padding:14px 16px;margin:0 0 18px}
.prob li{margin:3px 0}
.empty{color:var(--mut);font-style:italic;font-size:13px}
.foot{color:var(--mut);font-size:12px;margin-top:40px;border-top:1px solid var(--line);padding-top:14px}
nav{margin:0 0 20px;font-size:13px}nav a{margin-right:14px}
"""


def esc(value):
    return html.escape("" if value is None else str(value), quote=True)


def pill(text, kind="muted"):
    return '<span class="pill p-%s">%s</span>' % (kind, esc(text))


def result_pill(result):
    if not result:
        return '<span class="empty">no result</span>'
    return pill(result, RESULT_CLASSES.get(result, "muted"))


def page(title, body, nav_html=""):
    return (
        "<!DOCTYPE html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>%s</title><style>%s</style></head><body><div class=\"wrap\">%s%s"
        "<p class=\"foot\">Generated by <code>scripts/qa_dashboard.py</code> from "
        "<code>qa-state.json</code>, <code>fix-state.json</code> and the two append-only event "
        "logs. Nothing on this page is authored: if it is not in the ledgers or the logs, it is "
        "not here.</p></div></body></html>"
    ) % (esc(title), CSS, nav_html, body)


def tiles(pairs):
    out = ['<div class="grid">']
    for n, k, cls in pairs:
        out.append('<div class="tile"><div class="n %s">%s</div><div class="k">%s</div></div>'
                   % (cls, esc(n), esc(k)))
    out.append("</div>")
    return "".join(out)


def stacked_bar(counts):
    total = sum(counts.values())
    if not total:
        return ""
    colour = {"PASS": "var(--ok)", "PASS (SHORT)": "var(--warn)", "FAIL": "var(--bad)",
              "BLOCKED": "var(--warn)", "LONG": "var(--warn)", "NOT RUN": "var(--line)"}
    out = ['<div class="bar">']
    for label, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        pct = 100.0 * n / total
        out.append('<span style="width:%.2f%%;background:%s" title="%s: %d"></span>'
                   % (pct, colour.get(label, "var(--mut)"), esc(label), n))
    out.append("</div>")
    out.append('<div class="note">%s</div>' % " · ".join(
        "%s %d" % (esc(k), v) for k, v in sorted(counts.items(), key=lambda kv: -kv[1])))
    return "".join(out)


def render_problems(eng):
    if not eng.problems and not eng.notes:
        return ""
    out = []
    if eng.problems:
        out.append('<div class="prob"><strong>Integrity problems — these invalidate the '
                   'verdict until resolved</strong><ul>')
        for p in eng.problems:
            out.append("<li>%s</li>" % esc(p))
        out.append("</ul></div>")
    if eng.notes:
        out.append('<div class="card"><strong>Notes on the inputs</strong><ul class="note">')
        for n in eng.notes:
            out.append("<li>%s</li>" % esc(n))
        out.append("</ul></div>")
    return "".join(out)


def render_verdict(eng, iteration):
    label, first_fail, conditions = eng.verdict(iteration)
    cls = {"GREEN within stated bounds": "v-green", "NOT GREEN": "v-bad"}.get(label, "v-none")
    comps = eng.builds.get(str(iteration)) or {}
    bounds = ", ".join("%s %s" % (k, v) for k, v in sorted(comps.items())) or "no build recorded"
    out = ['<div class="verdict %s"><div class="big">%s</div>' % (cls, esc(label))]
    out.append('<p class="note" style="margin:6px 0 0">Builds: <code>%s</code>. '
               'Any other digest, topology, tenant shape or dataset size than the one named '
               'is untested by this run.</p>' % esc(bounds))
    if first_fail:
        out.append('<p style="margin:8px 0 0"><strong>First condition without rows:</strong> %s</p>'
                   % esc(first_fail))
    if eng.problems:
        out.append('<p style="margin:8px 0 0"><strong>%d integrity problem(s) below must be '
                   'resolved before any verdict stands.</strong></p>' % len(eng.problems))
    out.append("</div>")
    out.append("<table><tr><th>Condition</th><th>Holds</th><th>Rows</th></tr>")
    for name, ok, evidence in conditions:
        out.append("<tr><td>%s</td><td>%s</td><td class=\"mono\">%s</td></tr>"
                   % (esc(name), pill("yes", "ok") if ok else pill("no", "bad"), esc(evidence)))
    out.append("</table>")
    return "".join(out)


def render_cases(eng, iteration):
    rows, counts = [], Counter()
    by_scope = defaultdict(Counter)
    for cid, case in sorted(eng.cases.items()):
        res = eng.case_result_at(case, iteration)
        counts[res or "NOT RUN"] += 1
        by_scope[case.get("scope") or "(no scope)"][res or "NOT RUN"] += 1
        guards = case.get("guards") or {}
        ran = case.get("ran_under") or {}
        ran_text = " · ".join(
            "%s %s" % (k, v) for k, v in ran.items() if k not in ("ran_by", "at") and v)
        rows.append(
            "<tr><td class=\"mono\">%s</td><td>%s</td><td>%s</td><td>%s</td>"
            "<td class=\"note\">%s</td><td>%s</td><td class=\"note\">%s</td></tr>" % (
                esc(cid), esc(case.get("scope")), esc(case.get("action")),
                esc(case.get("oracle")),
                esc("%s (%s)" % (guards.get("class"), guards.get("ceiling"))
                    if guards.get("class") else ""),
                result_pill(res),
                esc(ran_text or (ran.get("ran_by") or "")),
            ))
    if not rows:
        return '<p class="empty">No cases in qa-state.json. The register is the run\'s ' \
               'denominator; without it there is nothing to compute a verdict from.</p>'
    out = [stacked_bar(counts)]
    out.append("<table><tr><th>Scope</th><th>Coverage</th></tr>")
    for scope, c in sorted(by_scope.items()):
        out.append("<tr><td>%s</td><td>%s</td></tr>" % (esc(scope), stacked_bar(c)))
    out.append("</table>")
    out.append("<h3>Every case</h3><table><tr><th>id</th><th>scope</th><th>action</th>"
               "<th>oracle</th><th>guards</th><th>result</th><th>ran under</th></tr>")
    out += rows
    out.append("</table>")
    return "".join(out)


def render_findings(eng, iteration):
    def sev_key(item):
        sev = (item[1].get("severity") or "").lower()
        return (SEVERITY_ORDER.index(sev) if sev in SEVERITY_ORDER else len(SEVERITY_ORDER),
                item[0])

    rows = []
    for fid, f in sorted(eng.findings.items(), key=sev_key):
        fx = eng.fixes.get(fid, {})
        status = eng.status_at(f, iteration) or ("CLOSED" if not eng.is_open(f) else "OPEN")
        reopens = eng.reopen_count(fid)
        cls = "bad" if (f.get("severity") or "").lower() in BLOCKING_SEVERITIES and eng.is_open(f) \
            else ("ok" if not eng.is_open(f) else "warn")
        rows.append(
            "<tr><td class=\"mono\"><a href=\"finding-%s.html\">%s</a></td><td>%s</td><td>%s</td>"
            "<td>%s</td><td>%s</td><td class=\"mono note\">%s</td><td>%s</td></tr>" % (
                esc(fid), esc(fid), pill(f.get("severity") or "?", cls),
                esc(f.get("title")), esc(status),
                esc(fx.get("triage") or ""),
                esc(fx.get("commit") or ""),
                ("%d" % reopens) if reopens else "",
            ))
    if not rows:
        return '<p class="empty">No findings recorded.</p>'
    return ("<table><tr><th>id</th><th>severity</th><th>finding</th><th>status</th>"
            "<th>dev triage</th><th>commit</th><th>reopens</th></tr>%s</table>"
            % "".join(rows))


def render_timeline(eng, fid):
    evs = eng.timeline(fid)
    if not evs:
        return '<p class="empty">No events logged for this finding. The lifecycle is ' \
               'reconstructable only from the event logs — a finding with no events has no ' \
               'audit trail.</p>'
    out = ['<div class="lane">']
    for ev in evs:
        detail = {k: v for k, v in ev.items()
                  if k not in ("ts", "actor", "role", "event", "id", "_src", "_line")}
        bits = " · ".join("%s: %s" % (esc(k), esc(json.dumps(v) if isinstance(v, (dict, list))
                                                 else v)) for k, v in sorted(detail.items()))
        out.append('<div class="ts">%s</div><div class="who %s">%s</div>'
                   '<div><span class="ev">%s</span> <span class="note">%s</span><br>'
                   '<span class="note">%s</span></div>'
                   % (esc(ev.get("ts")), esc(ev.get("role")), esc(ev.get("role")),
                      esc(ev.get("event")), esc(ev.get("actor")), bits))
    out.append("</div>")
    spans = eng.handoffs(fid)
    if spans:
        out.append("<h3>Time in state</h3><table><tr><th>held by</th><th>from</th>"
                   "<th>until</th><th>duration</th></tr>")
        for role, start, end in spans:
            dur = (end - start) if (start and end) else None
            hours = ("%.1f h" % (dur.total_seconds() / 3600.0)) if dur else "still held"
            out.append("<tr><td><span class=\"who %s\">%s</span></td><td class=\"mono note\">%s"
                       "</td><td class=\"mono note\">%s</td><td>%s</td></tr>"
                       % (esc(role), esc(role), esc(start.isoformat() if start else ""),
                          esc(end.isoformat() if end else ""), esc(hours)))
        out.append("</table>")
    return "".join(out)


def render_finding_page(eng, fid):
    f = eng.findings[fid]
    fx = eng.fixes.get(fid, {})
    cases = sorted(cid for cid, c in eng.cases.items() if c.get("finding") == fid)
    body = ['<h1>%s — %s</h1>' % (esc(fid), esc(f.get("title")))]
    body.append('<p class="sub">%s · scope %s · %s</p>' % (
        esc(f.get("severity")), esc(f.get("scope")),
        "open" if eng.is_open(f) else "closed in iteration %s" % esc(f.get("closed_in"))))
    body.append('<div class="card"><table>')
    for label, value in (
        ("Severity", f.get("severity")), ("Scope", f.get("scope")),
        ("Cases", ", ".join(cases)), ("Reopens", eng.reopen_count(fid)),
        ("Dev triage", fx.get("triage")), ("Dev reason", fx.get("reason")),
        ("Design citation", fx.get("design_citation")),
        ("Root cause", fx.get("root_cause")), ("Branch", fx.get("branch")),
        ("Commit", fx.get("commit")), ("Delivered in", fx.get("delivered_in_build")),
        ("Claimed", fx.get("claimed")), ("Note to QA", fx.get("note_to_qa")),
    ):
        if value not in (None, "", []):
            body.append("<tr><th>%s</th><td>%s</td></tr>" % (esc(label), esc(value)))
    body.append("</table></div>")
    if fx.get("triage") == "REJECTED" and not fx.get("design_citation"):
        body.append('<div class="prob">Rejected as working-as-designed with <strong>no design '
                    'citation</strong>. That does not close the finding: it converts to a '
                    'documentation finding under the same id, or — where the consequence is data '
                    'loss, a crossed boundary or money moving wrongly — to <code>DECIDE</code> at '
                    'its consequence severity, still open for the verdict.</div>')
    body.append("<h2>Lifecycle</h2>")
    body.append(render_timeline(eng, fid))
    nav = '<nav><a href="index.html">&larr; all releases</a></nav>'
    return page("%s — %s" % (fid, f.get("title") or ""), "".join(body), nav)


def render_release_page(eng, rel):
    it = rel["iteration"]
    open_blocking = sum(1 for f in eng.findings.values() if eng.is_open(f)
                        and (f.get("severity") or "").lower() in BLOCKING_SEVERITIES)
    results = Counter(eng.case_result_at(c, it) or "NOT RUN" for c in eng.cases.values())
    body = ['<h1>%s — iteration %s</h1>' % (esc(eng.engagement), esc(it))]
    body.append('<p class="sub">%s</p>' % esc(rel["label"]))
    body.append(render_verdict(eng, it))
    body.append(render_problems(eng))
    body.append(tiles([
        (len(eng.findings), "findings", ""),
        (open_blocking, "open critical/blocker", "bad" if open_blocking else "ok"),
        (len(eng.cases), "cases", ""),
        (results.get("PASS", 0), "pass", "ok"),
        (results.get("FAIL", 0), "fail", "bad" if results.get("FAIL") else "muted"),
        (results.get("NOT RUN", 0) + results.get("BLOCKED", 0), "not run / blocked", "warn"),
        (results.get("LONG", 0), "long open", "warn" if results.get("LONG") else "muted"),
    ]))
    body.append("<h2>Findings</h2>")
    body.append(render_findings(eng, it))
    body.append("<h2>Case coverage</h2>")
    body.append(render_cases(eng, it))
    body.append("<h2>Full event log</h2>")
    evs = [e for e in eng.events if str(e.get("iteration", it)) == str(it)] or eng.events
    out = ['<div class="lane">']
    for ev in evs:
        out.append('<div class="ts">%s</div><div class="who %s">%s</div>'
                   '<div><span class="ev">%s</span> <span class="note">%s %s</span></div>'
                   % (esc(ev.get("ts")), esc(ev.get("role")), esc(ev.get("role")),
                      esc(ev.get("event")),
                      esc(ev.get("id") or ev.get("case") or ""), esc(ev.get("actor"))))
    out.append("</div>")
    body.append("".join(out))
    nav = '<nav><a href="index.html">&larr; all releases</a></nav>'
    return page("%s — iteration %s" % (eng.engagement, it), "".join(body), nav)


def render_index(eng, releases):
    body = ['<h1>%s</h1>' % esc(eng.engagement)]
    body.append('<p class="sub">QA engagement dashboard · %d release(s) · generated %s</p>'
                % (len(releases), esc(datetime.now(timezone.utc).isoformat(timespec="seconds"))))
    body.append(render_problems(eng))
    body.append("<h2>Releases</h2><table><tr><th>iteration</th><th>build</th><th>verdict</th>"
                "<th>open critical/blocker</th><th>cases pass/fail/not run</th></tr>")
    for rel in releases:
        it = rel["iteration"]
        label, first_fail, _ = eng.verdict(it)
        res = Counter(eng.case_result_at(c, it) or "NOT RUN" for c in eng.cases.values())
        blocking = sum(1 for f in eng.findings.values() if eng.is_open(f)
                       and (f.get("severity") or "").lower() in BLOCKING_SEVERITIES)
        cls = {"GREEN within stated bounds": "ok", "NOT GREEN": "bad"}.get(label, "warn")
        body.append("<tr><td><a href=\"release-%s.html\">iteration %s</a></td>"
                    "<td class=\"mono note\">%s</td><td>%s</td><td>%s</td>"
                    "<td class=\"note\">%d / %d / %d</td></tr>"
                    % (esc(it), esc(it), esc(rel["label"]), pill(label, cls),
                       esc(blocking), res.get("PASS", 0), res.get("FAIL", 0),
                       res.get("NOT RUN", 0) + res.get("BLOCKED", 0)))
    body.append("</table>")
    body.append("<h2>Findings across all releases</h2>")
    body.append(render_findings(eng, eng.iteration))
    return page(eng.engagement, "".join(body))


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------

def write(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Generate a local HTML dashboard for a product-qa engagement.")
    ap.add_argument("report_dir", help="directory holding qa-state.json and friends")
    ap.add_argument("-o", "--out", default=None, help="output directory")
    ap.add_argument("--serve", nargs="?", const=8711, type=int, default=None,
                    metavar="PORT", help="serve the output on 127.0.0.1 after writing")
    args = ap.parse_args(argv)

    if not os.path.isdir(args.report_dir):
        print("not a directory: %s" % args.report_dir, file=sys.stderr)
        return 1
    try:
        eng = Engagement(args.report_dir)
    except Problem as exc:
        print("%s" % exc, file=sys.stderr)
        return 1

    outdir = args.out or os.path.join(args.report_dir, "dashboard")
    os.makedirs(outdir, exist_ok=True)

    releases = eng.releases()
    write(os.path.join(outdir, "index.html"), render_index(eng, releases))
    for rel in releases:
        write(os.path.join(outdir, "release-%s.html" % rel["iteration"]),
              render_release_page(eng, rel))
    for fid in eng.findings:
        write(os.path.join(outdir, "finding-%s.html" % fid), render_finding_page(eng, fid))

    index = os.path.join(outdir, "index.html")
    print("wrote %d page(s) to %s" % (1 + len(releases) + len(eng.findings), outdir))
    print("open: %s" % index)
    for p in eng.problems:
        print("integrity: %s" % p, file=sys.stderr)
    for n in eng.notes:
        print("note: %s" % n, file=sys.stderr)

    if args.serve is not None:
        import http.server
        import socketserver

        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *a, **kw):
                super().__init__(*a, directory=outdir, **kw)

            def log_message(self, *a):
                pass

        with socketserver.TCPServer(("127.0.0.1", args.serve), Handler) as httpd:
            print("serving %s at http://127.0.0.1:%d/ (Ctrl-C to stop)"
                  % (outdir, args.serve))
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\nstopped")

    return 2 if eng.problems else 0


if __name__ == "__main__":
    sys.exit(main())
