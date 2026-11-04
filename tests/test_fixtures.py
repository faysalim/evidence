#!/usr/bin/env python3
"""Rebuild both fixtures in a temp directory and assert their shape.

    python -I tests/test_fixtures.py

The committed fixtures under tests/fixtures/{existing,new}/ are the readable artifact. This test
rebuilds them somewhere disposable and checks the properties that matter, rather than diffing
bytes -- a byte diff would fail on every timestamp and tell you nothing.

What it asserts is the part that would quietly rot: that the engagement still builds at all
(every lifecycle in shared/hub/model.json still permits the arc a real engagement needs), that
the refusals still refuse, and that the verdicts are still NOT GREEN for the stated reasons. A
fixture whose verdict silently became GREEN would mean a condition stopped being checked.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests", "fixtures"))
sys.path.insert(0, os.path.join(ROOT, "shared", "scripts"))

import build as B        # noqa: E402
import dashboard as D    # noqa: E402

FAILURES = []


def check(label, condition, detail=""):
    if condition:
        print("  ok   %s" % label)
    else:
        print("  FAIL %s %s" % (label, detail))
        FAILURES.append(label)


def main():
    tmp = tempfile.mkdtemp(prefix="fixture-test-")
    try:
        print("existing-product engagement")
        hub, problems = B.build("existing", os.path.join(tmp, "existing"))
        check("builds through hub.py with no rejected calls", not B.FAILED,
              "; ".join(B.FAILED[:3]))
        check("validate is clean", not problems, "; ".join(problems[:3]))
        check("covers the whole arc", len(hub.items) >= 20, "%d items" % len(hub.items))

        types = {i["type"] for i in hub.items.values()}
        expected = {"prd", "requirement", "decision", "story", "design", "adr", "case",
                    "finding", "fix", "release", "doc", "launch", "metric", "risk", "cleanup"}
        check("every lifecycle in the arc is exercised", expected <= types,
              "missing: %s" % sorted(expected - types))

        label, first_fail, conditions = D.verdict(hub)
        check("verdict is NOT GREEN", label == "NOT GREEN", label)
        failed = [n for n, ok, _ in conditions if not ok]
        check("a NOT RUN case guarding a critical class denies the verdict",
              any("BLOCKED or NOT RUN" in n for n in failed), failed)
        check("an unsatisfied acceptance requirement denies the verdict",
              any("acceptance requirement" in n for n in failed), failed)

        # the arc's load-bearing states
        def state(iid):
            it = hub.items.get(iid)
            return it["state"] if it else None

        check("the blocker was closed by QA, not by DEV", state("F-1") == "CLOSED",
              state("F-1"))
        check("the story was accepted only after its case passed",
              state("S-1") == "ACCEPTED" and state("S5-01") == "PASS",
              "%s / %s" % (state("S-1"), state("S5-01")))
        check("the operator shipped against a non-green verdict, recorded",
              state("REL-1") == "SHIPPED"
              and bool(hub.items["REL-1"]["fields"].get("reason")),
              state("REL-1"))
        check("the contractual requirement is still NOT RUN", state("R-1") == "NOT_RUN",
              state("R-1"))
        check("cleanup was torn down with a re-listing",
              state("C-1") == "TORN_DOWN"
              and "NONE" in (hub.items["C-1"]["fields"].get("verified_by") or ""),
              state("C-1"))
        check("the conflicted requirement was settled by an operator decision",
              state("REQ-2") == "AGREED" and state("D-1") == "ANSWERED",
              "%s / %s" % (state("REQ-2"), state("D-1")))
        check("the metric was read by the analyst and interpreted by the PM",
              state("M-1") == "INTERPRETED", state("M-1"))

        # provenance: the reconstructed current-state PRD must be marked as such
        check("the current-state PRD is marked reconstructed",
              hub.items["PRD-0"]["provenance"] == "reconstructed",
              hub.items["PRD-0"]["provenance"])

        print("\nnew-product engagement")
        B.FAILED.clear()
        hub2, problems2 = B.build("new", os.path.join(tmp, "new"))
        check("builds through hub.py with no rejected calls", not B.FAILED,
              "; ".join(B.FAILED[:3]))
        check("validate is clean", not problems2, "; ".join(problems2[:3]))
        label2, _ff2, conditions2 = D.verdict(hub2)
        check("verdict is NOT GREEN", label2 == "NOT GREEN", label2)
        failed2 = [n for n, ok, _ in conditions2 if not ok]
        check("the open critical denies the verdict",
              any("critical or blocker finding" in n for n in failed2), failed2)
        check("a story claimed DONE but unaccepted denies the verdict",
              any("DONE but not yet ACCEPTED" in n for n in failed2), failed2)
        check("the cross-channel leak was filed as critical",
              (hub2.items["F-1"]["fields"].get("severity") or "") == "critical",
              hub2.items["F-1"]["fields"].get("severity"))
        check("the finding states what it does not claim",
              bool(hub2.items["F-1"]["fields"].get("does_not_claim")))

        print("\ndashboards render from both")
        for name, h in (("existing", hub), ("new", hub2)):
            out = os.path.join(tmp, "dash-" + name)
            pages = D.render(h, out)
            index = open(os.path.join(out, "index.html"), encoding="utf-8").read()
            check("%s: a page per item plus boards" % name, pages >= len(h.items) + 1,
                  "%d pages, %d items" % (pages, len(h.items)))
            check("%s: self-contained, no scripts" % name,
                  "http://" not in index and "https://" not in index
                  and "<script" not in index.lower())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILURES:
        print("%d check(s) FAILED: %s" % (len(FAILURES), ", ".join(FAILURES)))
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
