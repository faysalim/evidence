#!/usr/bin/env python3
"""The case matrix: what was tested, how it stood each cycle, and what to run next.

    python -I tests/test_case_matrix.py
    python -I tests/test_case_matrix.py -v

Why this exists. Shown a live dashboard, the operator asked for the test cases, categorised, with
their status per iteration as columns, click-through to the case and to the move that set a status --
and then made the point that fixes the design: **this is not a report, it is where QA resumes.**
The next cycle has to re-run what passed (regression), verify what DEV now claims fixed, and retry
what could not run. Without that derived from the hub, the next cycle begins by remembering.

What is asserted here, in the order it matters:

  - a case's cell is the state it ENDED that cycle in, so FAIL in cycle 1 and PASS in cycle 2 reads
    as the fix-verification story across the row;
  - categories come from the team's own id conventions, which QA owns;
  - the resume queue is derived: regression, verify-a-fix, still-failing, retry -- and a case that
    could not run is in *retry*, never counted as a pass;
  - zero cases says so loudly, because a hub of 20 findings and no cases has no coverage
    denominator at all. That was the real engagement's state and the old page simply showed nothing.
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


def sh(hub, actor, role, *args):
    p = subprocess.run([sys.executable, "-I", "-B", HUB, "--hub", hub] + [str(a) for a in args]
                       + ["--actor", actor, "--role", role],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode:
        FAILURES.append("setup rejected: %s -- %s"
                        % (" ".join(str(a) for a in args[:3]),
                           ((p.stdout or "") + (p.stderr or "")).strip()[:110]))
    return p


def build(hub):
    sh(hub, "h1", "HEAD_OF_PRODUCT", "init", "--engagement", "matrix probe")
    sh(hub, "h1", "HEAD_OF_PRODUCT", "iteration", "1")
    # one of each category the id conventions define
    for cid, oracle in (("S1-00a", "smoke: first success through the real client"),
                        ("S1-00b", "calibration: reports exactly one"),
                        ("R-1", "contract 4.2, recomputed independently"),
                        ("J-1", "the whole journey, end to end"),
                        ("S1-01", "an independent ledger")):
        sh(hub, "q1", "QA", "add", "case", cid, "-f", "action=do the thing",
           "-f", "oracle=%s" % oracle, "-f", "scope=licensing")
    sh(hub, "q1", "QA", "move", "S1-00a", "PASS", "-f", "evidence=activated the real binary")
    sh(hub, "q1", "QA", "move", "S1-00b", "PASS", "-f", "evidence=exactly one, not zero")
    sh(hub, "q1", "QA", "move", "R-1", "BLOCKED", "-f", "reason=no second host available")
    sh(hub, "q1", "QA", "move", "J-1", "PASS", "-f", "evidence=completed end to end")
    # the case that fails, gets a finding, and the finding gets fixed
    sh(hub, "q1", "QA", "move", "S1-01", "FAIL", "-f", "evidence=403 from the issuer")
    sh(hub, "q1", "QA", "add", "finding", "F-1", "-f", "title=issuer refuses",
       "-f", "severity=major")
    sh(hub, "q1", "QA", "link", "S1-01", "found_by", "F-1")
    sh(hub, "d1", "DEV", "move", "F-1", "ACCEPTED")
    sh(hub, "d1", "DEV", "move", "F-1", "FIXED", "-f", "commit=abc1234", "-f", "build=sha256:aaa")

    # cycle 2: the failing case is re-run and passes
    sh(hub, "h1", "HEAD_OF_PRODUCT", "iteration", "2")
    sh(hub, "q2", "QA", "move", "S1-01", "DESIGNED")
    sh(hub, "q2", "QA", "move", "S1-01", "PASS", "-f", "evidence=re-ran on sha256:aaa, activated")
    return hub


def main():
    import dashboard as D
    import hub as H

    tmp = tempfile.mkdtemp(prefix="matrix_")
    try:
        hub = build(os.path.join(tmp, "h"))
        if FAILURES:
            print("%d setup failure(s) -- the probe never ran" % len(FAILURES))
            for f in FAILURES[:4]:
                print("   ", f)
            return 1
        h = H.Hub(hub)
        iters, cases, cell = D.case_matrix(h)

        check("iterations become the columns, in order", iters == [1, 2], "got %r" % (iters,))
        check("every case is a row", len(cases) == 5, "got %d" % len(cases))

        cats = {D.case_category(c["id"], c) for c in cases}
        for want in ("Smoke (-00a)", "Calibration (-00b)",
                     "Acceptance requirements (source 0)", "Journeys", "Scope: licensing"):
            check("category %r is derived from the id convention" % want, want in cats,
                  "got %r" % sorted(cats))

        # the fix-verification story, read across one row
        check("S1-01 ended cycle 1 in FAIL", cell.get(("S1-01", 1), (None,))[0] == "FAIL",
              "got %r" % (cell.get(("S1-01", 1)),))
        check("and ended cycle 2 in PASS", cell.get(("S1-01", 2), (None,))[0] == "PASS",
              "got %r" % (cell.get(("S1-01", 2)),))
        check("a cell carries the event id, so a status can link to the move that set it",
              bool(cell.get(("S1-01", 1), (None, None))[1]),
              "got %r" % (cell.get(("S1-01", 1)),))
        check("a case untouched in a cycle has no cell, rather than a stale one",
              ("S1-00a", 2) not in cell, "S1-00a has a cycle-2 cell it never earned")

        # the resume queue
        last, regression, verify, retry = D.next_iteration_work(h, iters, cases, cell)
        check("the queue is built from the last cycle", last == 2, "got %r" % last)
        check("passed cases are regression candidates",
              set(regression) == {"S1-00a", "S1-00b", "J-1", "S1-01"},
              "got %r" % sorted(regression))
        check("a BLOCKED case is a RETRY, never a pass",
              [c for c, _ in retry] == ["R-1"], "got %r" % retry)
        check("  and the retry carries why it could not run",
              retry and "second host" in retry[0][1], "got %r" % (retry,))
        check("nothing is awaiting verification -- the fix was already verified",
              not [c for c, f in verify if f], "got %r" % verify)

        # a failing case whose finding is now claimed FIXED is QA's to verify
        sh(hub, "q2", "QA", "move", "S1-00b", "DESIGNED")
        sh(hub, "q2", "QA", "move", "S1-00b", "FAIL", "-f", "evidence=now reports two")
        sh(hub, "q2", "QA", "link", "S1-00b", "found_by", "F-1")
        h2 = H.Hub(hub)
        i2, c2, cl2 = D.case_matrix(h2)
        _l, _r, verify2, _t = D.next_iteration_work(h2, i2, c2, cl2)
        check("a FAIL whose finding DEV claims FIXED lands in verify-a-fix",
              ("S1-00b", ["F-1"]) in verify2, "got %r" % verify2)

        html = D.render_case_matrix(h2)
        for want in ("iteration 1", "iteration 2", "has to run", "Regression",
                     "Verify a fix", "Retry", "item-S1-01.html", "oracle"):
            check("the page shows %r" % want, want in html, "")
        check("a status links to its own event anchor", 'item-S1-01.html#' in html, "")

        # the real engagement's state: findings, no cases
        bare = os.path.join(tmp, "bare")
        sh(bare, "h1", "HEAD_OF_PRODUCT", "init")
        sh(bare, "q1", "QA", "add", "finding", "F-9", "-f", "title=x", "-f", "severity=major")
        html2 = D.render_case_matrix(H.Hub(bare))
        check("zero cases says so, loudly", "No test cases recorded" in html2, html2[:120])
        check("  and names the consequence: no coverage denominator",
              "coverage denominator" in html2, html2[:200])
        check("  and gives the command that fixes it", "add case" in html2, html2[:200])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILURES:
        print("%d failure(s)" % len(FAILURES))
        return 1
    print("  ok   the matrix reads as a process, and the next cycle's work is derived from it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
