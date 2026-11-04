#!/usr/bin/env python3
"""The one dashboard for every skill in product-suite. Generated from the hub, never authored.

Invoked as `hub.py dashboard`. Writes a self-contained static site that works over file://:
plain HTML, inline CSS, no scripts, no external resources, read-only.

Nothing on a page is written by hand. If it is not in the hub's event logs it is not here, and
where a page would have to guess it prints NO VERDICT and names the condition that had no rows.
That is the same discipline the test-case register applies to findings, applied to the reporting
of them -- a dashboard that can only ever be optimistic is decoration.

The verdict logic, its NO VERDICT default and its condition table come from qa_dashboard.py,
which was built and tested against a real engagement's shape; the conditions are extended with
the hub's cross-role items (open risks, unanswered decisions, unaccepted stories).
"""

from __future__ import annotations

import html
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone

SEVERITY_ORDER = ["critical", "blocker", "major", "minor", "polish"]
BLOCKING_SEVERITIES = {"critical", "blocker"}

TERMINAL_OK = {
    "finding": {"CLOSED", "WITHDRAWN", "DUPLICATE"},
    "story": {"ACCEPTED", "DROPPED"},
    "risk": {"CLOSED", "ACCEPTED"},
    "decision": {"ANSWERED", "WITHDRAWN"},
    "cleanup": {"TORN_DOWN"},
    "case": {"PASS"},
}

RESULT_CLASS = {
    "PASS": "ok", "PASS_SHORT": "warn", "FAIL": "bad", "BLOCKED": "warn",
    "NOT_RUN": "muted", "LONG": "warn", "DESIGNED": "muted",
    "CLOSED": "ok", "VERIFIED": "ok", "FIXED": "warn", "NEW": "bad",
    "ACCEPTED": "ok", "REJECTED": "bad", "STILL_PRESENT": "bad", "PARTIAL": "warn",
    "GREEN": "ok", "NOT_GREEN": "bad", "NO_VERDICT": "warn", "SHIPPED": "ok",
}

CSS = """
:root{--bg:#fbfbfa;--fg:#1a1a18;--mut:#6b6b66;--line:#e2e2dd;--card:#fff;
--ok:#1f7a4d;--okbg:#e8f5ee;--bad:#b3261e;--badbg:#fdecea;--warn:#8a5a00;--warnbg:#fdf3e0}
@media(prefers-color-scheme:dark){:root{--bg:#16161a;--fg:#ececea;--mut:#9a9a94;
--line:#2c2c32;--card:#1d1d22;--okbg:#10271c;--badbg:#2a1412;--warnbg:#2a2110;
--ok:#5fcf98;--bad:#ff8a80;--warn:#e0b050}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.55 ui-sans-serif,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:1200px;margin:0 auto;padding:28px 20px 72px}
h1{font-size:25px;margin:0 0 4px}h2{font-size:18px;margin:34px 0 12px;padding-bottom:6px;
border-bottom:1px solid var(--line)}h3{font-size:14px;margin:20px 0 8px;color:var(--mut);
text-transform:uppercase;letter-spacing:.05em}
a{color:inherit}.sub{color:var(--mut);font-size:13px;margin:0 0 18px}
code,.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12.5px}
table{border-collapse:collapse;width:100%;margin:10px 0 18px;font-size:13.5px}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-weight:600;color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.04em}
tr:last-child td{border-bottom:none}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 18px;margin:0 0 16px}
.verdict{border-radius:10px;padding:18px 20px;margin:0 0 20px;border:1px solid var(--line)}
.verdict .big{font-size:22px;font-weight:650;letter-spacing:-.01em}
.v-green{background:var(--okbg);border-color:var(--ok)}
.v-none{background:var(--warnbg);border-color:var(--warn)}
.v-bad{background:var(--badbg);border-color:var(--bad)}
.pill{display:inline-block;padding:1px 8px;border-radius:999px;font-size:11.5px;font-weight:600;
border:1px solid var(--line)}
.ok{color:var(--ok)}.bad{color:var(--bad)}.warn{color:var(--warn)}.muted{color:var(--mut)}
.p-ok{background:var(--okbg);color:var(--ok);border-color:var(--ok)}
.p-bad{background:var(--badbg);color:var(--bad);border-color:var(--bad)}
.p-warn{background:var(--warnbg);color:var(--warn);border-color:var(--warn)}
.p-muted{color:var(--mut)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin:0 0 18px}
.tile{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:13px 15px}
.tile .n{font-size:26px;font-weight:650;line-height:1.1}
.tile .k{font-size:11.5px;color:var(--mut);text-transform:uppercase;letter-spacing:.05em;margin-top:3px}
.board{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}
.col{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:11px 13px}
.col h4{margin:0 0 7px;font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--mut)}
.col ul{margin:0;padding-left:16px;font-size:13px}.col li{margin:2px 0}
.chain{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px;white-space:pre-wrap}
.lane{display:grid;grid-template-columns:200px 92px 1fr;gap:0 12px;font-size:13px}
.lane>div{padding:5px 0;border-bottom:1px solid var(--line)}
.lane .ts{color:var(--mut);font-size:11.5px;font-family:ui-monospace,Menlo,Consolas,monospace}
.who{font-size:11px;font-weight:650;letter-spacing:.03em;color:var(--mut)}
.prob{background:var(--badbg);border:1px solid var(--bad);border-radius:10px;padding:14px 16px;margin:0 0 18px}
.note{color:var(--mut);font-size:12.5px}
.empty{color:var(--mut);font-style:italic;font-size:13px}
.foot{color:var(--mut);font-size:12px;margin-top:40px;border-top:1px solid var(--line);padding-top:14px}
nav{margin:0 0 20px;font-size:13px}nav a{margin-right:14px}
"""


def esc(v):
    return html.escape("" if v is None else str(v), quote=True)


def pill(text, kind="muted"):
    return '<span class="pill p-%s">%s</span>' % (kind, esc(text))


def state_pill(state):
    return pill(state, RESULT_CLASS.get(state, "muted"))


def page(title, body, nav_html=""):
    return ("<!DOCTYPE html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<title>%s</title><style>%s</style></head><body><div class=\"wrap\">%s%s"
            "<p class=\"foot\">Generated by <code>hub.py dashboard</code> by folding the hub's "
            "append-only event logs. Nothing here is authored: if it is not in the logs, it is "
            "not on this page. Where a verdict cannot be computed it reads NO VERDICT and names "
            "the condition that had no rows.</p></div></body></html>") % (
        esc(title), CSS, nav_html, body)


def tiles(rows):
    out = ['<div class="grid">']
    for n, k, cls in rows:
        out.append('<div class="tile"><div class="n %s">%s</div><div class="k">%s</div></div>'
                   % (cls, esc(n), esc(k)))
    return "".join(out) + "</div>"


def is_open(item):
    return item["state"] not in TERMINAL_OK.get(item["type"], set())


SEVERITIES = ("critical", "blocker", "major", "minor", "polish")


def sev(item):
    """The graded severity, or "" when it is missing or not a recognised value.

    Defensive on purpose: a list-valued severity used to crash the dashboard, and an unknown or
    space-padded one was silently treated as harmless -- so a critical with `severity=P0` or
    `"critical "` was invisible to the verdict. Unknown now means ungraded, and ungraded denies
    the verdict via its own condition below.
    """
    value = item["fields"].get("severity")
    if not isinstance(value, str):
        return ""
    value = value.strip().lower()
    return value if value in SEVERITIES else ""


def ceiling_of(item):
    """The severity ceiling a case declares it guards, or None when it cannot be read."""
    g = item["fields"].get("guards")
    if not isinstance(g, dict):
        return None
    value = g.get("ceiling")
    if not isinstance(value, str):
        return None
    value = value.strip().lower()
    return value if value in SEVERITIES else None


def guards_unreadable(item):
    """True when a case declares guards the verdict cannot interpret."""
    g = item["fields"].get("guards")
    return g is not None and ceiling_of(item) is None


# ---------------------------------------------------------------------------
# verdict
# ---------------------------------------------------------------------------

def verdict(hub):
    """Computed, never written. NO VERDICT is the default; every row names its evidence."""
    items = hub.items
    conditions = []

    blocking = sorted(i["id"] for i in items.values()
                      if i["type"] == "finding" and is_open(i) and sev(i) in BLOCKING_SEVERITIES)
    conditions.append(("No open critical or blocker finding, including any held at DECIDE",
                       not blocking, ", ".join(blocking) or "none open"))

    cal_ok, owing, unlinked = set(), set(), []
    for cid, c in items.items():
        if c["type"] != "case":
            continue
        if cid.endswith("-00b"):
            if c["state"] == "PASS":
                cal_ok.add(c["fields"].get("graded_by") or c["fields"].get("scope"))
            continue
        if cid.endswith("-00a"):
            continue
        scope = c["fields"].get("graded_by") or c["fields"].get("scope")
        if cid.split("-")[0] in ("R", "J") and not c["fields"].get("graded_by"):
            unlinked.append(cid)
        elif scope:
            owing.add(scope)
    missing = sorted(s for s in owing if s not in cal_ok)
    conditions.append((
        "Every scope that owns a harness has a passing calibration row (00b)",
        not missing and not unlinked and bool(cal_ok),
        ("uncalibrated: " + ", ".join(missing)) if missing else
        ("not linked to a calibrated scope: " + ", ".join(unlinked)) if unlinked else
        (", ".join(sorted(c for c in items if c.endswith("-00b"))) or "no calibration rows")))

    smoke = sorted(c for c, i in items.items() if i["type"] == "case" and c.endswith("-00a"))
    conditions.append(("Smoke row passed on the build this verdict names",
                       bool(smoke) and all(items[c]["state"] == "PASS" for c in smoke),
                       ", ".join(smoke) or "no smoke rows"))

    longs = sorted(c for c, i in items.items() if i["type"] == "case" and i["state"] == "LONG")
    conditions.append(("No LONG row unreconciled", not longs,
                       ", ".join(longs) or "none open"))

    guarding = sorted(
        c for c, i in items.items()
        if i["type"] == "case" and i["state"] in ("NOT_RUN", "BLOCKED")
        and ceiling_of(i) in BLOCKING_SEVERITIES)
    conditions.append(("No BLOCKED or NOT RUN case guarding a critical or blocker class",
                       not guarding, ", ".join(guarding) or "none"))

    # A row whose declared stake cannot be read is not a row that guards nothing.
    unreadable = sorted(c for c, i in items.items()
                        if i["type"] == "case" and guards_unreadable(i))
    conditions.append(("Every case's `guards` names a ceiling the verdict can read",
                       not unreadable,
                       ("unreadable guards: " + ", ".join(unreadable)) if unreadable
                       else "all readable"))

    # HA-5: a recorded FAIL is a defect the hub already knows about. The dashboard used to print
    # "cases fail: 2" and GREEN on the same page.
    failed = sorted(c for c, i in items.items() if i["type"] == "case" and i["state"] == "FAIL")
    unlinked_fail = []
    for cid in failed:
        linked = [items.get(l["target"]) for l in items[cid]["links"]]
        if not any(t is not None and t["type"] == "finding" and is_open(t) for t in linked):
            unlinked_fail.append(cid)
    conditions.append(("Every FAIL case names an open finding", not failed or not unlinked_fail,
                       ("FAIL with no open finding: " + ", ".join(unlinked_fail))
                       if unlinked_fail else (", ".join(failed) or "no FAIL rows")))

    # HA-4: an open finding with no graded severity is unknown, not harmless.
    ungraded = sorted(i["id"] for i in items.values()
                      if i["type"] == "finding" and is_open(i) and not sev(i))
    conditions.append(("Every open finding has a severity from the vocabulary", not ungraded,
                       ("ungraded: " + ", ".join(ungraded)) if ungraded else "all graded"))

    # HA-3: a duplicate pointing at nothing, or at an open blocking finding, is still open.
    dangling_dup = sorted(
        i["id"] for i in items.values()
        if i["type"] == "finding" and i["state"] == "DUPLICATE"
        and (items.get(i["fields"].get("duplicate_of")) is None
             or is_open(items[i["fields"]["duplicate_of"]])))
    conditions.append(("Every DUPLICATE finding points at a finding that is itself closed",
                       not dangling_dup,
                       ("unresolved: " + ", ".join(dangling_dup)) if dangling_dup else "none"))

    reqs = sorted(c for c, i in items.items() if i["type"] == "case" and c.startswith("R-"))
    req_bad = [c for c in reqs if items[c]["state"] != "PASS"]
    conditions.append(("Every operator acceptance requirement has a PASS",
                       bool(reqs) and not req_bad,
                       ("not satisfied: " + ", ".join(req_bad)) if req_bad else
                       (", ".join(reqs) or
                        "none recorded -- green is against the docs only")))

    stories = sorted(i["id"] for i in items.values()
                     if i["type"] == "story" and i["state"] == "DONE")
    conditions.append(("No story claimed DONE but not yet ACCEPTED by the PO",
                       not stories, ", ".join(stories) or "none"))

    decisions = sorted(i["id"] for i in items.values()
                       if i["type"] == "decision" and i["state"] == "OPEN")
    conditions.append(("No decision awaiting the operator", not decisions,
                       ", ".join(decisions) or "none open"))

    risks = sorted(i["id"] for i in items.values()
                   if i["type"] == "risk" and i["state"] in ("OPEN", "REALIZED"))
    conditions.append(("No open or realized risk", not risks,
                       ", ".join(risks) or "none open"))

    # `OPERATORS` means only the operator can remove it -- not that it has been removed. The
    # resource still exists and still bills, so it is open for the verdict and routed to the
    # operator's queue.
    cleanup = sorted(i["id"] for i in items.values()
                     if i["type"] == "cleanup" and i["state"] in ("OPEN", "OPERATORS"))
    conditions.append(("Cleanup ledger has nothing still billing or exposed", not cleanup,
                       ", ".join(cleanup) or "nothing open"))

    # MG-3: restored. This was computed by qa_dashboard.py and dropped in the port -- and it is
    # the condition the whole iteration gate rests on, because a verdict about a build you
    # cannot name is a verdict about nothing.
    builds = {}
    for i in items.values():
        if i["type"] == "release" and i["fields"].get("build"):
            builds[i["id"]] = i["fields"]["build"]
    named = sorted("%s=%s" % (k, v) for k, v in builds.items())
    conditions.append(("Build identity established per component", bool(builds),
                       ", ".join(named) or "no release names a build"))

    # CR-3: smoke and calibration must have run on the build the verdict names, not on some
    # earlier one. Without this the rows are name-only.
    stale = []
    if builds:
        for cid, c in items.items():
            if c["type"] != "case" or not (cid.endswith("-00a") or cid.endswith("-00b")):
                continue
            ran = c["fields"].get("ran_under")
            ran_build = ran.get("build") if isinstance(ran, dict) else None
            if ran_build and ran_build not in builds.values():
                stale.append("%s ran on %s" % (cid, ran_build))
    conditions.append(("Smoke and calibration rows ran on the build this verdict names",
                       not stale, "; ".join(sorted(stale)) or "no disagreement recorded"))

    if hub.validate():
        conditions.append(("The hub itself validates", False,
                           "%d integrity problem(s)" % len(hub.validate())))
    else:
        conditions.append(("The hub itself validates", True, "validate: 0 problems"))

    if all(ok for _, ok, _ in conditions):
        label = "GREEN within stated bounds"
    elif blocking or req_bad or guarding:
        label = "NOT GREEN"
    else:
        label = "NO VERDICT"
    first_fail = next((n for n, ok, _ in conditions if not ok), None)
    return label, first_fail, conditions


def render_verdict(hub):
    label, first_fail, conditions = verdict(hub)
    cls = {"GREEN within stated bounds": "v-green", "NOT GREEN": "v-bad"}.get(label, "v-none")
    rel = [i for i in hub.items.values() if i["type"] == "release"]
    bounds = ", ".join(sorted(filter(None, (i["fields"].get("build") for i in rel)))) \
        or "no release build recorded"
    out = ['<div class="verdict %s"><div class="big">%s</div>' % (cls, esc(label))]
    out.append('<p class="note" style="margin:6px 0 0">Builds: <code>%s</code>. Any other '
               'digest, topology, tenant shape or dataset size than the one named is untested '
               'by this run.</p>' % esc(bounds))
    if first_fail:
        out.append('<p style="margin:8px 0 0"><strong>First condition without rows:</strong> '
                   '%s</p>' % esc(first_fail))
    out.append("</div><table><tr><th>Condition</th><th>Holds</th><th>Rows</th></tr>")
    for name, ok, ev in conditions:
        out.append("<tr><td>%s</td><td>%s</td><td class=\"mono\">%s</td></tr>"
                   % (esc(name), pill("yes", "ok") if ok else pill("no", "bad"), esc(ev)))
    out.append("</table>")
    does_not = [i["fields"].get("does_not_cover") for i in rel
                if i["fields"].get("does_not_cover")]
    if does_not:
        out.append('<div class="card"><h3>What this does not cover</h3>%s</div>'
                   % "".join("<p class=\"note\">%s</p>" % esc(d) for d in does_not))
    else:
        out.append('<p class="empty">No "what this does not cover" statement recorded on any '
                   'release item. An unbounded green is the claim this method exists to '
                   'prevent.</p>')
    return "".join(out)


# ---------------------------------------------------------------------------
# views
# ---------------------------------------------------------------------------

def render_problems(hub):
    problems, skew = hub.validate(), hub.skew
    out = []
    if problems:
        out.append('<div class="prob"><strong>Integrity problems — these invalidate the verdict '
                   'until resolved</strong><ul>')
        out += ["<li>%s</li>" % esc(p) for p in problems]
        out.append("</ul></div>")
    if skew or hub.notes:
        out.append('<div class="card"><h3>Notes on the inputs</h3><ul class="note">')
        out += ["<li>%s</li>" % esc(n) for n in skew + hub.notes]
        out.append("</ul></div>")
    return "".join(out)


def render_overview(hub):
    by_type = defaultdict(Counter)
    for i in hub.items.values():
        by_type[i["type"]][i["state"]] += 1
    if not by_type:
        return '<p class="empty">The hub holds no items yet.</p>'
    out = ["<table><tr><th>type</th><th>n</th><th>by state</th></tr>"]
    for t in sorted(by_type):
        counts = by_type[t]
        out.append("<tr><td><a href=\"type-%s.html\">%s</a></td><td>%d</td><td>%s</td></tr>"
                   % (esc(t), esc(t), sum(counts.values()),
                      " ".join(state_pill("%s %d" % (s, n))
                               for s, n in sorted(counts.items(), key=lambda kv: -kv[1]))))
    return "".join(out) + "</table>"


def render_roles(hub):
    waiting = defaultdict(list)
    owned = defaultdict(list)
    for i in sorted(hub.items.values(), key=lambda x: x["id"]):
        if not is_open(i):
            continue
        for role in hub.waiting_on(i):
            waiting[role].append(i)
        if i["owner_role"]:
            owned[i["owner_role"]].append(i)
    roles = sorted(set(waiting) | set(owned))
    if not roles:
        return '<p class="empty">Nothing open.</p>'
    out = ["<table><tr><th>role</th><th>waiting on them</th><th>they own</th></tr>"]
    for r in roles:
        out.append("<tr><td><strong>%s</strong></td><td>%s</td><td class=\"note\">%s</td></tr>"
                   % (esc(r),
                      " ".join("<a href=\"item-%s.html\">%s</a>" % (esc(i["id"]), esc(i["id"]))
                               for i in waiting[r]) or "<span class=\"empty\">—</span>",
                      " ".join(esc(i["id"]) for i in owned[r]) or "—"))
    return "".join(out) + "</table>"


def render_board(hub, item_type):
    cols = defaultdict(list)
    for i in sorted(hub.items.values(), key=lambda x: x["id"]):
        if i["type"] == item_type:
            cols[i["state"]].append(i)
    if not cols:
        return '<p class="empty">No %s items.</p>' % esc(item_type)
    out = ['<div class="board">']
    for state in sorted(cols):
        out.append('<div class="col"><h4>%s (%d)</h4><ul>' % (esc(state), len(cols[state])))
        for i in cols[state]:
            out.append('<li><a href="item-%s.html">%s</a> <span class="note">%s</span></li>'
                       % (esc(i["id"]), esc(i["id"]), esc(i["fields"].get("title") or "")))
        out.append("</ul></div>")
    return "".join(out) + "</div>"


def render_traceability(hub):
    """story -> design/adr -> case -> finding -> fix -> release, from links alone."""
    chain_rel = {"realizes", "refines", "implements", "verifies", "fixes", "ships", "measures",
                 "derived_from"}
    outgoing = defaultdict(list)
    for i in hub.items.values():
        for l in i["links"]:
            if l["rel"] in chain_rel:
                outgoing[l["target"]].append((l["rel"], i["id"]))
    roots = [i for i in sorted(hub.items.values(), key=lambda x: x["id"])
             if i["type"] in ("initiative", "prd", "story")]
    if not roots:
        return '<p class="empty">No initiative, PRD or story to trace from.</p>'
    lines = []
    seen_global = set()

    def walk(iid, depth, seen):
        item = hub.items.get(iid)
        if item is None or depth > 6 or iid in seen:
            return
        seen = seen | {iid}
        seen_global.add(iid)
        lines.append("%s%s [%s] %s %s" % (
            "  " * depth, iid, item["type"], item["state"],
            (item["fields"].get("title") or "")[:60]))
        for rel, child in sorted(outgoing.get(iid, [])):
            lines.append("%s  <-%s-" % ("  " * depth, rel))
            walk(child, depth + 2, seen)

    for r in roots:
        walk(r["id"], 0, set())
    orphans = sorted(i["id"] for i in hub.items.values()
                     if i["id"] not in seen_global
                     and i["type"] in ("case", "finding", "fix", "story", "requirement"))
    out = ['<div class="card"><div class="chain">%s</div></div>'
           % esc("\n".join(lines) or "(nothing linked)")]
    if orphans:
        out.append('<p class="note"><strong>Not reachable from any initiative, PRD or story:'
                   '</strong> <span class="mono">%s</span>. An item outside the chain cannot be '
                   'traced to a reason for existing.</p>' % esc(", ".join(orphans)))
    return "".join(out)


def _ts(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def render_time_in_state(hub):
    rows = []
    for i in sorted(hub.items.values(), key=lambda x: x["id"]):
        hist = [h for h in i["history"] if h.get("to")]
        if len(hist) < 2:
            continue
        reopens = sum(1 for h in i["history"] if h.get("to") == "REOPENED")
        spans = []
        for a, b in zip(hist, hist[1:]):
            ta, tb = _ts(a.get("ts")), _ts(b.get("ts"))
            if ta and tb and tb >= ta:
                spans.append((a["to"], (tb - ta).total_seconds() / 3600.0, a.get("role")))
        if not spans:
            continue
        longest = max(spans, key=lambda s: s[1])
        rows.append((i, spans, longest, reopens))
    if not rows:
        return '<p class="empty">Not enough transition history yet to measure time in state.</p>'
    out = ["<table><tr><th>item</th><th>type</th><th>transitions</th>"
           "<th>longest wait</th><th>held by</th><th>reopens</th></tr>"]
    for i, spans, longest, reopens in sorted(rows, key=lambda r: -r[2][1]):
        out.append("<tr><td class=\"mono\"><a href=\"item-%s.html\">%s</a></td><td>%s</td>"
                   "<td>%d</td><td>%s in %s</td><td>%s</td><td>%s</td></tr>"
                   % (esc(i["id"]), esc(i["id"]), esc(i["type"]), len(spans),
                      esc("%.1f h" % longest[1]), esc(longest[0]), esc(longest[2] or "-"),
                      pill(reopens, "bad") if reopens else "0"))
    return "".join(out) + "</table>"


def render_operator_queue(hub):
    rows = []
    for i in sorted(hub.items.values(), key=lambda x: x["id"]):
        if not is_open(i):
            continue
        if "OPERATOR" in hub.waiting_on(i):
            rows.append(i)
    if not rows:
        return '<p class="empty">Nothing is waiting on the operator.</p>'
    out = ["<table><tr><th>item</th><th>type</th><th>state</th><th>what it needs</th></tr>"]
    for i in rows:
        out.append("<tr><td class=\"mono\"><a href=\"item-%s.html\">%s</a></td><td>%s</td>"
                   "<td>%s</td><td class=\"note\">%s</td></tr>"
                   % (esc(i["id"]), esc(i["id"]), esc(i["type"]), state_pill(i["state"]),
                      esc(i["fields"].get("title") or i["fields"].get("reason") or "")))
    return "".join(out) + "</table>"


def render_item_page(hub, item):
    body = ['<h1>%s <span class="note">%s</span></h1>' % (esc(item["id"]), esc(item["type"]))]
    body.append('<p class="sub">%s · owner %s · provenance %s · waiting on %s</p>' % (
        esc(item["state"]), esc(item["owner_role"]), esc(item["provenance"]),
        esc(", ".join(hub.waiting_on(item)) or "nobody")))
    if item["fields"]:
        body.append('<div class="card"><table>')
        for k in sorted(item["fields"]):
            v = item["fields"][k]
            body.append("<tr><th>%s</th><td>%s</td></tr>"
                        % (esc(k), esc(json.dumps(v) if isinstance(v, (dict, list)) else v)))
        body.append("</table></div>")
    if item["links"]:
        body.append("<h2>Links</h2><table><tr><th>rel</th><th>target</th></tr>")
        for l in item["links"]:
            body.append("<tr><td>%s</td><td class=\"mono\"><a href=\"item-%s.html\">%s</a></td>"
                        "</tr>" % (esc(l["rel"]), esc(l["target"]), esc(l["target"])))
        body.append("</table>")
    body.append("<h2>Lifecycle</h2>")
    if item["history"]:
        body.append('<div class="lane">')
        for h in item["history"]:
            detail = " ".join("%s→%s" % (esc(h.get("from")), esc(h.get("to")))
                              for _ in [0] if h.get("to"))
            body.append('<div class="ts">%s</div><div class="who">%s</div>'
                        '<div><strong>%s</strong> %s <span class="note">%s</span></div>'
                        % (esc(h.get("ts")), esc(h.get("role")), esc(h.get("op")),
                           detail, esc(h.get("actor"))))
        body.append("</div>")
    else:
        body.append('<p class="empty">No events. An item with no history has no audit trail.</p>')
    if item["notes"]:
        body.append("<h2>Notes</h2>")
        for n in item["notes"]:
            body.append('<p class="note"><span class="mono">%s %s</span> — %s</p>'
                        % (esc(n.get("ts")), esc(n.get("actor")), esc(n.get("text"))))
    return page("%s — %s" % (item["id"], item["type"]), "".join(body),
                '<nav><a href="index.html">&larr; overview</a></nav>')


def render_type_page(hub, item_type):
    body = ['<h1>%s</h1>' % esc(item_type)]
    body.append('<p class="sub">Lifecycle board, from the hub.</p>')
    body.append(render_board(hub, item_type))
    return page(item_type, "".join(body),
                '<nav><a href="index.html">&larr; overview</a></nav>')


def render_index(hub):
    items = hub.items
    findings = [i for i in items.values() if i["type"] == "finding"]
    cases = [i for i in items.values() if i["type"] == "case"]
    body = ['<h1>%s</h1>' % esc(hub.meta.get("engagement") or "engagement")]
    body.append('<p class="sub">iteration %s · %d items · %d events · generated %s</p>' % (
        esc(hub.meta.get("iteration")), len(items), len(hub.applied),
        esc(datetime.now(timezone.utc).isoformat(timespec="seconds"))))
    body.append(render_verdict(hub))
    body.append(render_problems(hub))
    body.append(tiles([
        (len(items), "items", ""),
        (sum(1 for i in findings if is_open(i) and sev(i) in BLOCKING_SEVERITIES),
         "open critical/blocker",
         "bad" if any(is_open(i) and sev(i) in BLOCKING_SEVERITIES for i in findings) else "ok"),
        (sum(1 for i in cases if i["state"] == "PASS"), "cases pass", "ok"),
        (sum(1 for i in cases if i["state"] == "FAIL"), "cases fail", "bad"),
        (sum(1 for i in cases if i["state"] in ("NOT_RUN", "BLOCKED")), "not run / blocked",
         "warn"),
        (sum(1 for i in items.values() if "OPERATOR" in hub.waiting_on(i) and is_open(i)),
         "waiting on operator", "warn"),
    ]))
    body.append("<h2>All items by type and state</h2>" + render_overview(hub))
    body.append("<h2>Per role: waiting on them, and what they own</h2>" + render_roles(hub))
    body.append("<h2>Awaiting the operator</h2>" + render_operator_queue(hub))
    body.append("<h2>Traceability</h2>" + render_traceability(hub))
    body.append("<h2>Time in state and reopens</h2>" + render_time_in_state(hub))
    return page(hub.meta.get("engagement") or "engagement", "".join(body))


def render(hub, outdir):
    os.makedirs(outdir, exist_ok=True)

    def write(name, text):
        with open(os.path.join(outdir, name), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)

    write("index.html", render_index(hub))
    pages = 1
    for t in sorted({i["type"] for i in hub.items.values()}):
        write("type-%s.html" % t, render_type_page(hub, t))
        pages += 1
    for item in hub.items.values():
        write("item-%s.html" % item["id"], render_item_page(hub, item))
        pages += 1
    return pages


# ---------------------------------------------------------------------------
# adapter interface (interface only -- no implementation ships here)
# ---------------------------------------------------------------------------

class TrackerAdapter:
    """Interface for pushing hub items into an external tracker (Jira, Azure DevOps, GitHub).

    Deliberately an interface and nothing more. An adapter that half-works is worse than none:
    the hub stays the source of truth, and a tracker is a projection of it. Any implementation
    must honour three rules or it breaks the method:

      * One-way by default. The hub is authoritative; the tracker is a view. Two-way sync needs
        a conflict rule, and nobody has written one that survives "the producer claims, a
        different role accepts".
      * Ids are names. `external_id` maps hub id -> tracker key and is never reused.
      * A transition the hub forbids must not be reachable from the tracker. If the tracker can
        let DEV close a finding, the invariant is gone -- so either mirror the workflow or push
        read-only comments, never editable states.
    """

    name = "abstract"

    def push_item(self, item):
        raise NotImplementedError

    def push_transition(self, item, from_state, to_state, actor, role):
        raise NotImplementedError

    def external_id(self, hub_id):
        raise NotImplementedError

    def pull_comments(self, item):
        """Optional. Comments are the only safe inbound direction: they change no state."""
        raise NotImplementedError
