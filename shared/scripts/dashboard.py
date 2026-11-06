#!/usr/bin/env python3
"""The one dashboard for every skill in evidence. Generated from the hub, never authored.

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
    def duplicate_resolves(item):
        """Follow duplicate_of to a non-DUPLICATE finding of the same type.

        A cycle resolves to nothing, and so does a target that is not a finding -- pointing a
        critical at a PASS case used to resolve to something `TERMINAL_OK` counts as closed.
        """
        seen, cur = set(), item
        while cur is not None and cur["state"] == "DUPLICATE":
            if cur["id"] in seen:
                return None                      # cycle: resolves to nothing
            seen.add(cur["id"])
            cur = items.get(cur["fields"].get("duplicate_of"))
            if cur is not None and cur["type"] != item["type"]:
                return None                      # not a finding: resolves to nothing
        return cur

    dangling_dup = []
    for i in items.values():
        if i["type"] != "finding" or i["state"] != "DUPLICATE":
            continue
        target = duplicate_resolves(i)
        if target is None or is_open(target):
            dangling_dup.append(i["id"])
    dangling_dup.sort()
    conditions.append(("Every DUPLICATE finding resolves to a finding that is itself closed",
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
    # Only releases still under consideration. A ROLLED_BACK or already-SHIPPED release's build
    # is not the build this verdict is about, and counting it let a fresh candidate inherit the
    # previous release's gate rows.
    # SHIPPED counts: a verdict about a release that shipped is still a verdict about its build.
    # Only ROLLED_BACK drops out. Excluding SHIPPED made a shipped release report "no release
    # names a build", which is the opposite of the condition's purpose -- the per-release coverage
    # check below is what actually stops a new candidate inheriting an older release's rows.
    IN_FLIGHT = {"CANDIDATE", "NO_VERDICT", "NOT_GREEN", "GREEN", "SHIPPED"}
    builds = {}
    for i in items.values():
        if (i["type"] == "release" and i["state"] in IN_FLIGHT
                and i["fields"].get("build")):
            builds[i["id"]] = i["fields"]["build"]
    named = sorted("%s=%s" % (k, v) for k, v in builds.items())
    conditions.append(("Build identity established per component", bool(builds),
                       ", ".join(named) or "no release names a build"))

    # CR-3: smoke and calibration must have run on the build the verdict names, not on some
    # earlier one. Without this the rows are name-only.
    # The question is per release, not hub-wide. Asking only "is this row's build *some*
    # release's build" let a fresh candidate inherit the previous release's gate rows -- so
    # "the build this verdict names" quietly became "any build in the hub".
    gate_rows = [cid for cid, c in items.items()
                 if c["type"] == "case" and (cid.endswith("-00a") or cid.endswith("-00b"))]
    stamped = {}
    unstamped = []
    for cid in gate_rows:
        ran = items[cid]["fields"].get("ran_under")
        ran_build = ran.get("build") if isinstance(ran, dict) else None
        if not ran_build:
            unstamped.append(cid)               # silence is not agreement
        else:
            stamped.setdefault(ran_build, []).append(cid)

    uncovered = []
    for rel_id, build in sorted(builds.items()):
        rows = stamped.get(build, [])
        if not any(c.endswith("-00a") for c in rows):
            uncovered.append("%s (%s) has no smoke row on its build" % (rel_id, build))
        if not any(c.endswith("-00b") for c in rows):
            uncovered.append("%s (%s) has no calibration row on its build" % (rel_id, build))
    orphan = sorted("%s ran on %s" % (c, b_)
                    for b_, cs in stamped.items() if b_ not in builds.values() for c in cs)

    detail_parts = []
    if uncovered:
        detail_parts.append("; ".join(uncovered))
    if orphan:
        detail_parts.append("; ".join(orphan))
    if unstamped:
        detail_parts.append("no ran_under.build on " + ", ".join(sorted(unstamped)))
    conditions.append(("Smoke and calibration rows ran on the build this verdict names",
                       bool(builds) and bool(gate_rows) and not uncovered and not orphan
                       and not unstamped,
                       "; ".join(detail_parts)
                       or (", ".join(sorted(gate_rows)) or "no gate rows")))

    if hub.validate():
        conditions.append(("The hub itself validates", False,
                           "%d integrity problem(s)" % len(hub.validate())))
    else:
        conditions.append(("The hub itself validates", True, "validate: 0 problems"))

    # Case-first, as a gate rather than an instruction. The verdict is what everyone wants, so it
    # is where skipping the step has to cost something: a scope that produced findings and never
    # recorded a single thing it tried has no coverage denominator, and a green against no
    # denominator is the claim this whole method exists to refuse.
    case_scopes = {i["fields"].get("scope") or i["fields"].get("graded_by")
                   for i in items.values() if i["type"] == "case"}
    any_case = any(i["type"] == "case" for i in items.values())
    findings = [i for i in items.values() if i["type"] == "finding"]
    no_denom = sorted({i["fields"].get("scope") for i in findings
                       if i["fields"].get("scope") and i["fields"].get("scope")
                       not in case_scopes})
    unscoped = [i["id"] for i in findings if not i["fields"].get("scope")]
    if not findings:
        cf_ok, cf_detail = (True, "no findings yet, so nothing claims a denominator")
    elif no_denom or (unscoped and not any_case):
        bits = []
        if no_denom:
            bits.append("scope(s) with findings and no designed case set: " + ", ".join(no_denom))
        if unscoped and not any_case:
            bits.append("%d unscoped finding(s) in a hub with no case at all" % len(unscoped))
        cf_ok, cf_detail = False, "; ".join(bits)
    else:
        cf_detail = "%d finding(s) across %d scope(s), each with a designed case set" % (
            len(findings), len([s for s in case_scopes if s]))
        cf_ok = True
    conditions.append(("Every scope with findings has a designed case set", cf_ok, cf_detail))

    # Readiness outside QA. Until this condition existed, a green verdict meant "QA found nothing"
    # and said nothing about whether the rollback had been rehearsed, an alert fired, anyone was
    # on call, or privacy had signed off -- so the most consequential sentence in the suite was
    # computed from one team's evidence. An independent review named this as the largest gap.
    #
    # No rows yields NO VERDICT, not NOT GREEN -- the same treatment every other condition with no
    # rows gets (`shared/principles.md` §6, and the release skill says it in as many words). It is
    # not a claim that the release is unsafe; it is a refusal to call GREEN on evidence nobody
    # supplied. A team that keeps its ops checklist elsewhere imports it the way `orient` Step 5
    # imports their runbooks and SLOs. The detail line names exactly what the verdict is silent
    # about, so the refusal is readable rather than mysterious.
    # The question is PER RELEASE and PER BUILD, exactly as it already is for QA's gate rows a few
    # lines above. The first version of this condition asked neither: one row, MET with no build,
    # linked to no release, satisfied the gate for a hub holding two releases on two digests. That
    # is the defect the CR-3 comment above was written about, repeated in new code.
    ready = [i for i in items.values() if i["type"] == "readiness"]
    gated = {}                       # release id -> rows linked to it
    unlinked = []
    for i in ready:
        targets = [l["target"] for l in i.get("links", []) if l.get("rel") == "gates"]
        if not targets:
            unlinked.append(i["id"])
        for rel_id in targets:
            gated.setdefault(rel_id, []).append(i)

    # The required SET, not a row count. With ownership and build-scoping enforced, a release could
    # still go green on a single rehearsed rollback, with nothing said about alerting, on-call,
    # privacy or support. The team's own set replaces this suite's defaults entirely -- a team that
    # gates on three things must not be told it is missing twenty-eight.
    profile = hub.meta.get("profile") or {}
    their_set = profile.get("required_checkpoints")
    if isinstance(their_set, str):
        their_set = [their_set]
    if their_set:
        required, set_source = sorted(set(their_set)), "the team's own set"
    else:
        defaults = hub.model.get("default_checkpoints") or {}
        required = sorted({k for role, keys in defaults.items()
                           if role != "doc" and isinstance(keys, dict) for k in keys})
        set_source = "this suite's default set -- orient imports the team's own to replace it"

    problems, satisfied, stale = [], [], []
    for rel_id, build in sorted(builds.items()):
        rows = gated.get(rel_id, [])
        if not rows:
            problems.append("%s (%s) has no readiness checkpoint at all" % (rel_id, build))
            continue
        covered = {i["fields"].get("checkpoint") for i in rows
                   if i["state"] in ("MET", "WAIVED") and i["fields"].get("build") == build}
        uncovered = [k for k in required if k not in covered]
        if uncovered:
            problems.append("%s (%s) is missing %d of %d required checkpoint(s) from %s: %s"
                            % (rel_id, build, len(uncovered), len(required), set_source,
                               ", ".join(uncovered)))
        for i in rows:
            row_build = i["fields"].get("build")
            if i["state"] == "OPEN":
                problems.append("%s still OPEN for %s" % (i["id"], rel_id))
            elif row_build != build:
                # Evidence is about a build. A rehearsal on the previous candidate is not
                # evidence about this one, and saying nothing would let it pass as if it were.
                stale.append("%s was %s on %s, but %s is %s"
                             % (i["id"], i["state"].lower(), row_build or "no build",
                                rel_id, build))
            else:
                satisfied.append("%s %s" % (i["id"], i["state"].lower()))

    if not builds:
        ok = False
        detail = ("no in-flight release names a build, so there is nothing to scope readiness to")
    elif not ready:
        ok = False
        detail = ("none recorded -- this verdict covers QA evidence only and says nothing about "
                  "rollback, alerting, on-call, runbooks, certificates, privacy, legal or support")
    else:
        ok = not problems and not stale
        bits = []
        if problems:
            bits.append("; ".join(problems))
        if stale:
            bits.append("STALE, not counted: " + "; ".join(stale))
        if unlinked:
            bits.append("linked to no release, so counting for nothing: " + ", ".join(
                sorted(unlinked)))
        if ok:
            bits.append("; ".join(satisfied))
        detail = " | ".join(bits)
    conditions.append(("Every release-readiness checkpoint is MET or waived, on this release's "
                       "build", ok, detail))

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


def process_by_iteration(hub):
    """What happened in each cycle: filed, fixed, verified, bounced, reopened, and coverage.

    The dashboard showed current state and no process. It could not answer the questions anyone
    actually asks of a QA engagement -- how many defects did the first pass find, how much of the
    planned coverage was reachable, how many of DEV's fixes survived verification, how many came
    back -- even though every one of those is already in the event log with an actor, a role, a
    timestamp and an iteration.

    Derived by walking the applied events in fold order and tracking the iteration the `iteration`
    op last set, so every move is attributed to the cycle it happened in rather than to the
    item's creation cycle. Nothing here is stored; it is all recomputed, like the verdict.
    """
    BOUNCE = ("STILL_PRESENT", "PARTIAL", "NOT_IN_BUILD", "CANNOT_RETEST")
    DISMISS = ("REJECTED", "DEFERRED", "DUPLICATE", "WITHDRAWN", "DISPUTED")
    RAN = ("PASS", "PASS_SHORT", "FAIL")
    UNREACHED = ("BLOCKED", "NOT_RUN")

    rows = {}
    order = []

    def bucket(n):
        if n not in rows:
            rows[n] = Counter()
            order.append(n)
        return rows[n]

    cur = None
    for ev in hub.applied:
        op = ev.get("op")
        if op == "iteration":
            cur = ev.get("iteration")
            bucket(cur)
            continue
        b = bucket(cur)
        typ = ev.get("type")
        if op == "add" and typ == "finding":
            b["filed"] += 1
            s = str((ev.get("fields") or {}).get("severity") or "").strip().lower()
            if s in ("critical", "blocker"):
                b["filed_blocking"] += 1
        elif op == "add" and typ == "case":
            b["designed"] += 1
        elif op == "move":
            to = ev.get("to")
            role = ev.get("role")
            item = hub.items.get(ev.get("item")) or {}
            if item.get("type") == "finding":
                if to == "FIXED" and role == "DEV":
                    b["fixed_by_dev"] += 1
                elif to == "VERIFIED":
                    b["verified"] += 1
                elif to == "CLOSED":
                    b["closed"] += 1
                elif to in BOUNCE:
                    b["bounced"] += 1
                elif to in DISMISS:
                    b["dismissed"] += 1
                elif to == "REOPENED":
                    b["reopened"] += 1
            elif item.get("type") == "case":
                if to in RAN:
                    b["ran"] += 1
                    if to == "FAIL":
                        b["failed"] += 1
                elif to in UNREACHED:
                    b["unreached"] += 1

    # A regression is a NEW id linked `introduced_by`, not a reopen of the same id -- the model
    # says so explicitly, and conflating them hides which fixes caused new defects.
    for i in hub.items.values():
        if i["type"] != "finding":
            continue
        if any(l.get("rel") == "introduced_by" for l in i.get("links", [])):
            rows.setdefault(i.get("iteration"), Counter())
            if i.get("iteration") not in order:
                order.append(i.get("iteration"))
            rows[i.get("iteration")]["regressions"] += 1
    return order, rows


def render_process(hub):
    order, rows = process_by_iteration(hub)
    if not rows or not any(sum(c.values()) for c in rows.values()):
        return ('<p class="empty">No iterations recorded. <code>hub.py iteration N</code> marks a '
                'cycle, and every count below is then attributed to the cycle it happened in.</p>')

    # A cycle in which nothing countable happened is noise, not information -- the events before
    # the first `iteration` op are usually just init and profile.
    order = [n for n in order if sum(rows[n].values())]
    if not order:
        return ('<p class="empty">Iterations are recorded but nothing countable happened in '
                'them yet.</p>')

    def label(n):
        return "iteration %s" % n if n is not None else "before any iteration"

    out = ['<table><tr><th>cycle</th><th>findings filed</th><th>of those blocking</th>'
           '<th>fixed by DEV</th><th>verified by QA</th><th>closed</th>'
           '<th>bounced back by QA</th><th>dismissed</th><th>reopened</th>'
           '<th>regressions (new id)</th></tr>']
    tot = Counter()
    for n in order:
        c = rows[n]
        tot.update(c)
        out.append("<tr><td>%s</td>%s</tr>"
                   % (esc(label(n)),
                      "".join("<td>%s</td>" % (c.get(k) or "&ndash;")
                              for k in ("filed", "filed_blocking", "fixed_by_dev", "verified",
                                        "closed", "bounced", "dismissed", "reopened",
                                        "regressions"))))
    out.append("<tr><th>all cycles</th>%s</tr>"
               % "".join("<th>%s</th>" % (tot.get(k) or 0)
                         for k in ("filed", "filed_blocking", "fixed_by_dev", "verified",
                                   "closed", "bounced", "dismissed", "reopened",
                                   "regressions")))
    out.append("</table>")

    # First-pass fix yield: of the fixes DEV handed back, how many survived verification. This is
    # the single number that says whether the QA-DEV loop is working, and it was not on the page.
    graded = tot.get("verified", 0) + tot.get("bounced", 0)
    if graded:
        out.append('<p>Of %d fix(es) DEV handed back and QA graded, <strong>%d survived '
                   'verification first time</strong> and %d came back &mdash; first-pass yield '
                   '<strong>%d%%</strong>. A handback that bounces is not a failure of either '
                   'role; a <em>rising</em> bounce rate is.</p>'
                   % (graded, tot.get("verified", 0), tot.get("bounced", 0),
                      round(100.0 * tot.get("verified", 0) / graded)))

    out.append('<h3>Coverage, per cycle</h3>')
    out.append('<table><tr><th>cycle</th><th>cases designed</th><th>run</th><th>of those failed</th>'
               '<th>blocked or not run</th><th>reached</th></tr>')
    for n in order:
        c = rows[n]
        ran, un = c.get("ran", 0), c.get("unreached", 0)
        attempted = ran + un
        pct = ("%d%%" % round(100.0 * ran / attempted)) if attempted else "&ndash;"
        out.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
                   % (esc(label(n)), c.get("designed") or "&ndash;", ran or "&ndash;",
                      c.get("failed") or "&ndash;", un or "&ndash;", pct))
    out.append("</table>")
    out.append('<p><strong>&ldquo;Reached&rdquo; is the honest coverage number</strong>: cases that '
               'actually ran, over cases anyone tried to run. A case that is <code>BLOCKED</code> '
               'or <code>NOT RUN</code> is not coverage and is never counted as such &mdash; it is '
               'the gap, and it is what the verdict denies on.</p>')
    return "".join(out)


def case_category(cid, item):
    """The team's own id conventions decide the category -- QA owns them, stated in skills/release.

    Grouping is not cosmetic here. A smoke row and an acceptance requirement are read differently
    by the verdict, so a flat list of cases hides which part of the evidence is thin.
    """
    if cid.endswith("-00a"):
        return "Smoke (-00a)"
    if cid.endswith("-00b"):
        return "Calibration (-00b)"
    head = cid.split("-")[0]
    if head == "R":
        return "Acceptance requirements (source 0)"
    if head == "J":
        return "Journeys"
    scope = item["fields"].get("scope") or item["fields"].get("graded_by")
    return "Scope: %s" % scope if scope else "Uncategorised"


def case_matrix(hub):
    """Every case, its category, and the state it ended each iteration in.

    Built by replaying the moves in fold order and tracking the iteration the `iteration` op last
    set, so a cell is "where this case stood at the end of that cycle" -- which is the question
    QA asks when deciding what to re-run.
    """
    iters, seen = [], set()
    cur = None
    # (case id, iteration) -> (state, event_id) of the LAST move in that iteration
    cell = {}
    for ev in hub.applied:
        if ev.get("op") == "iteration":
            cur = ev.get("iteration")
            if cur not in seen:
                seen.add(cur)
                iters.append(cur)
            continue
        if ev.get("op") != "move":
            continue
        item = hub.items.get(ev.get("item")) or {}
        if item.get("type") != "case":
            continue
        if cur not in seen:
            seen.add(cur)
            iters.append(cur)
        cell[(ev["item"], cur)] = (ev.get("to"), ev.get("event_id"))

    cases = sorted((i for i in hub.items.values() if i["type"] == "case"),
                   key=lambda i: (case_category(i["id"], i), i["id"]))
    return iters, cases, cell


def next_iteration_work(hub, iters, cases, cell):
    """What QA has to do next cycle, derived rather than remembered.

    The operator's point, and it is the right one: this table is not a report, it is the resume
    point. A case that passed last cycle is a regression candidate; a case that failed and whose
    finding is now claimed FIXED is waiting on verification; a case that could not run is a retry.
    Without this the next iteration starts by re-deciding what to run, from memory.
    """
    last = iters[-1] if iters else None
    regression, verify, retry = [], [], []
    for c in cases:
        state = c["state"]
        if state in ("PASS", "PASS_SHORT"):
            regression.append(c["id"])
        elif state in ("BLOCKED", "NOT_RUN"):
            retry.append((c["id"], c["fields"].get("reason") or "no reason recorded"))
        elif state == "FAIL":
            # Is the finding this case named now claimed fixed? Then it is QA's to verify.
            fixed = []
            for l in c.get("links", []):
                t = hub.items.get(l.get("target")) or {}
                if t.get("type") == "finding" and t.get("state") in ("FIXED", "PARTIAL"):
                    fixed.append(t["id"])
            verify.append((c["id"], fixed))
    return last, regression, verify, retry


def render_case_matrix(hub):
    iters, cases, cell = case_matrix(hub)
    if not cases:
        n_find = sum(1 for i in hub.items.values() if i["type"] == "finding")
        return ('<p class="empty"><strong>No test cases recorded.</strong> This hub holds %d '
                'finding(s) and <strong>no <code>case</code> items</strong>, so there is no record '
                'of what was exercised and <em>no coverage denominator at all</em> &mdash; '
                '&ldquo;how much coverage was possible&rdquo; cannot be answered for this '
                'engagement, and no regression or verification queue can be derived for the next '
                'one. A finding says what broke; a case says what was tried. '
                '<code>hub.py add case &lt;id&gt; -f action=... -f oracle=...</code>.</p>'
                % n_find)

    out = ['<table><tr><th>case</th>']
    for n in iters:
        out.append("<th>%s</th>" % esc("iteration %s" % n if n is not None else "pre"))
    out.append("<th>now</th><th>oracle</th></tr>")

    cat = None
    for c in cases:
        k = case_category(c["id"], c)
        if k != cat:
            cat = k
            out.append('<tr><th colspan="%d" class="mono">%s</th></tr>'
                       % (len(iters) + 3, esc(cat)))
        cells = []
        for n in iters:
            got = cell.get((c["id"], n))
            if not got:
                cells.append('<td class="note">&ndash;</td>')
            else:
                state, eid = got
                # Click the status, get the move that set it -- the evidence is on the item page,
                # anchored at that event.
                cells.append('<td><a href="item-%s.html#%s">%s</a></td>'
                             % (esc(c["id"]), esc(eid or ""), state_pill(state)))
        out.append('<tr><td class="mono"><a href="item-%s.html">%s</a></td>%s'
                   '<td>%s</td><td class="note">%s</td></tr>'
                   % (esc(c["id"]), esc(c["id"]), "".join(cells), state_pill(c["state"]),
                      esc((c["fields"].get("oracle") or "no oracle recorded")[:70])))
    out.append("</table>")
    out.append('<p class="note">Click a case id for its full description and lifecycle; click a '
               'status for the move that set it, with its evidence. A blank cell means the case '
               'was not touched in that cycle &mdash; which is itself a finding if it guards '
               'something blocking.</p>')

    last, regression, verify, retry = next_iteration_work(hub, iters, cases, cell)
    nxt = (last + 1) if isinstance(last, int) else "the next cycle"
    out.append("<h3>What iteration %s has to run</h3>" % esc(str(nxt)))
    out.append('<p class="note">Derived from the matrix, not remembered. This is the resume point: '
               'without it the next cycle begins by re-deciding what to re-run.</p>')
    out.append("<table><tr><th>why</th><th>n</th><th>cases</th></tr>")

    def row(why, ids):
        out.append("<tr><td>%s</td><td>%d</td><td class=\"mono\">%s</td></tr>"
                   % (why, len(ids),
                      " ".join('<a href="item-%s.html">%s</a>' % (esc(i), esc(i))
                               for i in ids[:24]) or "&ndash;"))

    row("<strong>Regression</strong> &mdash; passed before, so a pass is only current until the "
        "build changes", regression)
    row("<strong>Verify a fix</strong> &mdash; failed, and the finding it names is now claimed "
        "FIXED or PARTIAL by DEV", [c for c, f in verify if f])
    row("<strong>Still failing, no fix yet</strong> &mdash; nothing to verify; this is DEV's",
        [c for c, f in verify if not f])
    row("<strong>Retry</strong> &mdash; could not run, so it is a gap and not a pass",
        [c for c, _r in retry])
    out.append("</table>")
    if retry:
        out.append('<p class="note">Why each could not run: %s</p>'
                   % esc("; ".join("%s: %s" % (c, r) for c, r in retry[:6])))
    return "".join(out)


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
    # `found_by` and `graded_by` were missing, so no relation could reach a finding from a case
    # and every finding was reported "not reachable from any initiative, PRD or story" -- while
    # the links to reach it plainly existed.
    chain_rel = {"realizes", "refines", "implements", "verifies", "fixes", "ships", "measures",
                 "derived_from", "found_by", "graded_by", "introduced_by"}
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
            # The event id is the anchor the case matrix links a status cell to, so clicking a
            # status lands on the move that set it rather than at the top of the page.
            vals = h.get("values") or {}
            shown = " ".join(
                '<span class="note">%s=</span>%s' % (esc(k), esc(str(vals[k])[:120]))
                for k in ("evidence", "reason", "cutoff", "build", "variant_used")
                if vals.get(k))
            body.append('<div class="ts" id="%s">%s</div><div class="who">%s</div>'
                        '<div><strong>%s</strong> %s <span class="note">%s</span>%s</div>'
                        % (esc(h.get("event_id") or ""), esc(h.get("ts")), esc(h.get("role")),
                           esc(h.get("op")), detail, esc(h.get("actor")),
                           ("<br>" + shown) if shown else ""))
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
    # An unnamed engagement used to render as the bare word "engagement", in both the <h1>
    # and the <title> -- a label with no value, which reads to a first-time user as a
    # placeholder the tool forgot to fill in. `init --engagement NAME` exists and no skill
    # mentioned it, so every engagement that followed the skills got exactly this. Say what
    # is missing and how to fix it instead.
    engagement = hub.meta.get("engagement")
    body = ['<h1>%s</h1>' % esc(engagement or "unnamed engagement")]
    if not engagement:
        body.append('<p class="sub">This hub has no name. '
                    '<code>hub.py init --engagement "&lt;product and date&gt;"</code> sets it; '
                    'on an existing hub, <code>hub.py iteration --note</code> records why.</p>')
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
    body.append("<h2>Test cases by iteration, and what to run next</h2>"
                + render_case_matrix(hub))
    body.append("<h2>The process, cycle by cycle</h2>" + render_process(hub))
    body.append("<h2>All items by type and state</h2>" + render_overview(hub))
    body.append("<h2>Per role: waiting on them, and what they own</h2>" + render_roles(hub))
    body.append("<h2>Awaiting the operator</h2>" + render_operator_queue(hub))
    body.append("<h2>Traceability</h2>" + render_traceability(hub))
    body.append("<h2>Time in state and reopens</h2>" + render_time_in_state(hub))
    return page(engagement or "unnamed engagement", "".join(body))


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
