#!/usr/bin/env python3
"""The dashboard answers the questions asked of a QA engagement, per cycle.

    python -I tests/test_process_view.py
    python -I tests/test_process_view.py -v

Why this exists. The dashboard rendered current state and no process. Shown a live one, the operator
said it did not tell them how many defects the first cycle found, how much coverage was reachable,
how many of DEV's fixes QA verified, or how many came back -- and they were right: not one of those
was on the page, although every one was already in the event log with an actor, a role, a timestamp
and an iteration.

So each is computed, per cycle, from the events in fold order. Nothing is stored; it is recomputed
like the verdict.

The two distinctions worth testing hardest, because collapsing either loses the signal:

  - **bounced vs verified.** DEV moving a finding to FIXED is a claim; QA moving it to VERIFIED is a
    verdict. STILL_PRESENT / PARTIAL / NOT_IN_BUILD / CANNOT_RETEST are the claim being refused,
    and counting them as "fixed" would make a loop that never converges look productive.
  - **reopened vs regression.** A reopen keeps the finding's id; a regression introduced by a fix is
    a NEW id linked `introduced_by`. The model says so in as many words. Conflating them hides
    which fixes caused new defects.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HUB = os.path.join(ROOT, "shared", "scripts", "hub.py")
sys.path.insert(0, os.path.join(ROOT, "shared", "scripts"))
VERBOSE = "-v" in sys.argv

FAILURES = []


def check(label, cond, detail=""):
    if cond:
        if VERBOSE:
            print("  ok   %s" % label)
    else:
        print("  FAIL %s%s" % (label, (" -- " + detail) if detail else ""))
        FAILURES.append(label)


def build(hub):
    """Two cycles that exercise every counter, through hub.py only."""
    def run(actor, role, *args):
        p = subprocess.run([sys.executable, "-I", "-B", HUB, "--hub", hub] + list(args)
                           + ["--actor", actor, "--role", role],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if p.returncode != 0 and "iteration" not in args[0]:
            FAILURES.append("setup rejected: %s -- %s"
                            % (" ".join(args[:3]), (p.stdout or p.stderr or "").strip()[:110]))
        return p

    run("h1", "HEAD_OF_PRODUCT", "init", "--engagement", "process probe")

    # ---- cycle 1: four findings, four cases, one fix handed back and verified ----------
    run("h1", "HEAD_OF_PRODUCT", "iteration", "1")
    for cid, state in (("S1-01", "PASS"), ("S1-02", "PASS"), ("S1-03", "FAIL"),
                       ("S1-04", "BLOCKED")):
        run("q1", "QA", "add", "case", cid, "-f", "action=do it",
            "-f", "oracle=an independent ledger")
        extra = (["-f", "reason=no second host"] if state == "BLOCKED"
                 else ["-f", "evidence=observed against the ledger"])
        run("q1", "QA", "move", cid, state, *extra)
    for fid, sv in (("F-1", "critical"), ("F-2", "major"), ("F-3", "minor"), ("F-4", "minor")):
        run("q1", "QA", "add", "finding", fid, "-f", "title=%s defect" % sv, "-f", "severity=%s" % sv)
    run("d1", "DEV", "move", "F-1", "ACCEPTED")
    run("d1", "DEV", "move", "F-1", "FIXED", "-f", "commit=abc1234", "-f", "build=sha256:aaa")
    run("q1", "QA", "move", "F-1", "VERIFIED", "-f", "evidence=re-ran the repro, gone",
        "-f", "variant_used=the original repro")
    run("q1", "QA", "move", "F-1", "CLOSED", "-f", "evidence=closed on sha256:aaa")
    # DEV claims a fix QA refuses -- the bounce
    run("d1", "DEV", "move", "F-2", "ACCEPTED")
    run("d1", "DEV", "move", "F-2", "FIXED", "-f", "commit=def5678", "-f", "build=sha256:aaa")
    run("q1", "QA", "move", "F-2", "STILL_PRESENT", "-f", "evidence=same repro, same result")
    # and one dismissed
    run("d1", "DEV", "move", "F-3", "REJECTED", "-f", "reason=works as designed")

    # ---- cycle 2: a reopen (same id) and a regression (new id) -------------------------
    run("h1", "HEAD_OF_PRODUCT", "iteration", "2")
    run("q1", "QA", "add", "case", "S2-01", "-f", "action=re-run", "-f", "oracle=the ledger")
    run("q1", "QA", "move", "S2-01", "PASS", "-f", "evidence=observed")
    run("q1", "QA", "move", "F-1", "REOPENED", "-f", "evidence=came back on sha256:bbb")
    run("q1", "QA", "add", "finding", "F-5", "-f", "title=new defect from the F-1 fix",
        "-f", "severity=blocker")
    run("q1", "QA", "link", "F-5", "introduced_by", "F-1")
    return hub


def main():
    import dashboard as D
    import hub as H

    tmp = tempfile.mkdtemp(prefix="proc_")
    try:
        hub = build(os.path.join(tmp, "h"))
        if FAILURES:
            print("\n%d setup failure(s) -- the probe never ran" % len(FAILURES))
            for f in FAILURES[:4]:
                print("   ", f)
            return 1
        h = H.Hub(hub)
        order, rows = D.process_by_iteration(h)
        live = [n for n in order if sum(rows[n].values())]
        check("two cycles are reported", live == [1, 2], "got %r" % (live,))
        c1, c2 = rows.get(1, {}), rows.get(2, {})

        # the operator's questions, in their order
        check("findings filed in cycle 1", c1.get("filed") == 4, "got %r" % c1.get("filed"))
        check("  of those blocking", c1.get("filed_blocking") == 1,
              "got %r" % c1.get("filed_blocking"))
        check("cases designed in cycle 1", c1.get("designed") == 4, "got %r" % c1.get("designed"))
        check("cases that actually RAN in cycle 1", c1.get("ran") == 3, "got %r" % c1.get("ran"))
        check("  of those failed", c1.get("failed") == 1, "got %r" % c1.get("failed"))
        check("blocked or not run -- never counted as coverage", c1.get("unreached") == 1,
              "got %r" % c1.get("unreached"))
        check("fixed by DEV in cycle 1", c1.get("fixed_by_dev") == 2,
              "got %r" % c1.get("fixed_by_dev"))
        check("verified by QA in cycle 1", c1.get("verified") == 1,
              "got %r" % c1.get("verified"))
        check("closed in cycle 1", c1.get("closed") == 1, "got %r" % c1.get("closed"))
        check("bounced back by QA in cycle 1 -- a claim refused, not a fix",
              c1.get("bounced") == 1, "got %r" % c1.get("bounced"))
        check("dismissed in cycle 1", c1.get("dismissed") == 1, "got %r" % c1.get("dismissed"))

        check("reopened in cycle 2 -- same id", c2.get("reopened") == 1,
              "got %r" % c2.get("reopened"))
        check("regressions in cycle 2 -- a NEW id linked introduced_by",
              c2.get("regressions") == 1, "got %r" % c2.get("regressions"))
        check("a reopen is NOT counted as a regression", c2.get("regressions") != 2,
              "reopen and regression were collapsed")
        check("cycle 1 has no reopens or regressions",
              not c1.get("reopened") and not c1.get("regressions"),
              "reopened=%r regressions=%r" % (c1.get("reopened"), c1.get("regressions")))

        # Moves are attributed to the cycle they happened in, not the item's creation cycle:
        # F-1 is filed in cycle 1 and its reopen must land in cycle 2.
        check("a move is attributed to the cycle it happened in, not the item's birth cycle",
              c1.get("filed") == 4 and c2.get("reopened") == 1,
              "c1 filed=%r c2 reopened=%r" % (c1.get("filed"), c2.get("reopened")))
        # A regression IS a new finding, so it counts in both columns. Stated rather than
        # asserted away, because a reader adding the columns up will notice.
        check("a regression counts as a finding filed too -- it is a new defect",
              c2.get("filed") == 1 and c2.get("regressions") == 1,
              "filed=%r regressions=%r" % (c2.get("filed"), c2.get("regressions")))

        html = D.render_process(h)
        for want in ("findings filed", "fixed by DEV", "verified by QA", "bounced back by QA",
                     "reopened", "regressions", "blocked or not run", "reached",
                     "first-pass yield"):
            check("the page says %r" % want, want in html, html[:120])
        check("first-pass yield is 50% -- one verified, one bounced", "50%" in html,
              [s for s in html.split("<") if "yield" in s][:1])

        # an empty hub says what to do rather than rendering a blank table
        empty = os.path.join(tmp, "empty")
        subprocess.run([sys.executable, "-I", "-B", HUB, "--hub", empty, "init",
                        "--actor", "h1", "--role", "HEAD_OF_PRODUCT"], capture_output=True)
        html2 = D.render_process(H.Hub(empty))
        check("with no iterations it names the command that starts one",
              "hub.py iteration" in html2, html2[:160])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILURES:
        print("%d failure(s)" % len(FAILURES))
        return 1
    print("  ok   the process is readable per cycle, and a claim is not counted as a verdict")
    return 0


if __name__ == "__main__":
    sys.exit(main())
