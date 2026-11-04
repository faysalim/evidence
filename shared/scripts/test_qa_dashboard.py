#!/usr/bin/env python3
"""Self-test for qa_dashboard.py. Standard library only, no network, no fixtures on disk.

    python -I scripts/test_qa_dashboard.py

Every assertion here is one of the skill's own invariants, so a change that
breaks one is a change to the method, not just to the renderer:

  * only QA may CLOSE -- a DEV CLOSED event is an integrity problem
  * the two ledgers join on finding id -- an id DEV invented is a problem
  * NO VERDICT is the default, and a NOT RUN row guarding a critical class
    is enough on its own to deny GREEN
  * a working-as-designed rejection with no citation does not close anything
  * a malformed log line is reported, never fatal
  * a LONG row open means the report carries no verdict
"""

from __future__ import annotations

import io
import json
import os
import re
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qa_dashboard as qd  # noqa: E402

FAILURES = []


def check(label, condition, detail=""):
    if condition:
        print("  ok   %s" % label)
    else:
        print("  FAIL %s %s" % (label, detail))
        FAILURES.append(label)


QA_STATE = {
    "engagement": "fixture-business",
    "iteration": 2,
    "builds_tested": {
        "1": {"website": "dfd358b", "service": "2.5.0-ui6@faec816"},
        "2": {"website": "a1b2c3d", "service": "2.5.1@9f8e7d6"},
    },
    "findings": [
        {"id": "K1", "title": "Self-hosted activation names the wrong env var",
         "severity": "blocker", "scope": "selfhosted",
         "status": {"1": "OPEN", "2": "VERIFIED FIXED"}, "closed_in": 2},
        {"id": "K4", "title": "Acknowledged writes missing after leader kill",
         "severity": "critical", "scope": "state",
         "status": {"1": "OPEN", "2": "OPEN"}, "closed_in": None},
        {"id": "T4", "title": "Export includes records the role cannot see",
         "severity": "major", "scope": "saas",
         "status": {"2": "OPEN"}, "closed_in": None},
    ],
    "cases": [
        {"id": "S10-00a", "scope": "state", "action": "Form 3 nodes, write 1k keys, read back",
         "oracle": "harness LISTS 3 instances and 1000 keys readable", "result": {"2": "PASS"}},
        {"id": "S10-00b", "scope": "state", "action": "Delete 7 acked keys by hand, run the diff",
         "oracle": "the diff reports exactly 7 Missing", "result": {"2": "PASS"}},
        {"id": "S10-01", "scope": "state", "action": "20k writes RF2, kill -9 leader, read back",
         "oracle": "section 10 diff against my own ledger",
         "guards": {"class": "acknowledged-write loss", "ceiling": "critical"},
         "ran_under": {"topology": "3 nodes listed, RF2", "n": 20000, "duration": "20m",
                       "ran_by": "scope-10-agent", "at": "2026-11-04T09:12:00Z"},
         "result": {"1": "FAIL", "2": "FAIL"}, "finding": "K4"},
        {"id": "S10-04", "scope": "state", "action": "Partition one node 60s, heal, read both",
         "oracle": "both sides agree with my ledger",
         "guards": {"class": "divergence after heal", "ceiling": "critical"},
         "result": {"1": "NOT RUN", "2": "NOT RUN"}, "blocked_by": "only two hosts"},
        {"id": "S5-00a", "scope": "licensing", "action": "Issue one trial key end to end",
         "oracle": "the key activates a real binary", "result": {"2": "PASS"}},
        {"id": "S5-00b", "scope": "licensing", "action": "Plant one wrong price in a fixture page",
         "oracle": "the scraper reports exactly one mismatch", "result": {"2": "PASS"}},
        {"id": "S5-01", "scope": "licensing", "action": "POST /v1/trial, documented payload",
         "oracle": "a usable key in the real mailbox",
         "guards": {"class": "documented path broken", "ceiling": "blocker"},
         "result": {"1": "FAIL", "2": "PASS"}, "finding": "K1"},
        {"id": "R-1", "scope": "requirements", "graded_by": "state",
         "action": "Partition 3 of 9 nodes across a zone",
         "oracle": "section 10 diff; contract 4.2 states RPO=0",
         "guards": {"class": "AZ-loss durability", "ceiling": "critical"},
         "result": {"2": "NOT RUN"}},
        # Deliberate: a journey with no graded_by. Must be reported -- it cannot
        # inherit any scope's calibration, so its result grades nothing.
        {"id": "J-9", "scope": "journeys", "action": "form -> email -> activation",
         "oracle": "a working product reached only through the product's own artifacts",
         "guards": {"class": "business cannot sell", "ceiling": "blocker"},
         "result": {"2": "NOT RUN"}},
    ],
    "stopped": None,
}

FIX_STATE = {
    "engagement": "fixture-business", "role": "DEV",
    "fixes": [
        {"id": "K1", "triage": "ACCEPTED", "root_cause": "read the undocumented variable name",
         "branch": "fix/qa-k1-env-var", "commit": "9f8e7d6",
         "delivered_in_build": "2.5.1@9f8e7d6", "claimed": "FIXED",
         "satisfies_cases": ["S5-01"]},
        {"id": "T4", "triage": "REJECTED", "reason": "works as designed",
         "design_citation": None, "claimed": None,
         "note_to_qa": "intended; cannot find where it is documented"},
        # Deliberate: an id QA never issued. Must be reported.
        {"id": "Z9", "triage": "ACCEPTED", "claimed": "FIXED", "commit": "deadbee"},
    ],
}

QA_EVENTS = [
    {"ts": "2026-11-04T09:12:03Z", "actor": "qa/scope-5-agent", "role": "QA", "event": "FILED",
     "id": "K1", "severity": "blocker", "case": "S5-01", "iteration": 1},
    {"ts": "2026-11-04T10:02:00Z", "actor": "qa/scope-10-agent", "role": "QA", "event": "FILED",
     "id": "K4", "severity": "critical", "case": "S10-01", "iteration": 1},
    {"ts": "2026-11-04T11:48:11Z", "actor": "qa/lead", "role": "QA", "event": "HANDED_OVER",
     "id": "K1", "iteration": 1},
    {"ts": "2026-11-06T08:15:00Z", "actor": "qa/lead", "role": "QA", "event": "BUILD_IDENTITY",
     "build": "2.5.1@9f8e7d6", "present": ["K1"], "absent": [], "iteration": 2},
    {"ts": "2026-11-06T08:33:02Z", "actor": "qa/scope-5-agent", "role": "QA",
     "event": "VERIFIED", "id": "K1", "status": "VERIFIED FIXED",
     "variant_used": "tag-only local part", "iteration": 2},
    {"ts": "2026-11-06T09:00:00Z", "actor": "qa/lead", "role": "QA", "event": "CLOSED",
     "id": "K1", "iteration": 2},
]

FIX_EVENTS = [
    {"ts": "2026-11-05T11:02:00Z", "actor": "dev/session-2", "role": "DEV", "event": "TRIAGED",
     "id": "K1", "triage": "ACCEPTED", "iteration": 1},
    {"ts": "2026-11-05T15:40:22Z", "actor": "dev/session-2", "role": "DEV",
     "event": "FIX_DELIVERED", "id": "K1", "branch": "fix/qa-k1-env-var", "commit": "9f8e7d6",
     "build": "2.5.1@9f8e7d6", "satisfies_cases": ["S5-01"], "iteration": 1},
    # Deliberate: DEV claiming CLOSED. Must be reported as an integrity problem.
    {"ts": "2026-11-05T16:00:00Z", "actor": "dev/session-2", "role": "DEV", "event": "CLOSED",
     "id": "K1", "iteration": 1},
]


def build_fixture(tmp, long_open=False, clean=False):
    qa = json.loads(json.dumps(QA_STATE))
    fix = json.loads(json.dumps(FIX_STATE))
    qa_events, fix_events = list(QA_EVENTS), list(FIX_EVENTS)

    if long_open:
        for case in qa["cases"]:
            if case["id"] == "S10-01":
                case["result"]["2"] = "LONG"

    if clean:
        # The only configuration in which GREEN is legitimate.
        for f in qa["findings"]:
            f["status"] = {"1": "OPEN", "2": "VERIFIED FIXED"}
            f["closed_in"] = 2
        for case in qa["cases"]:
            case["result"] = {k: "PASS" for k in case["result"]}
        fix["fixes"] = [f for f in fix["fixes"] if f["id"] != "Z9"]
        for case in qa["cases"]:
            if case["id"] == "J-9":
                case["graded_by"] = "licensing"
        fix_events = [e for e in fix_events if e["event"] != "CLOSED"]

    def dump_jsonl(path, rows, trailing_garbage=False):
        with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
            for row in rows:
                fh.write(json.dumps(row) + "\n")
            if trailing_garbage:
                fh.write("this line is deliberately not json\n")

    with io.open(os.path.join(tmp, "qa-state.json"), "w", encoding="utf-8") as fh:
        json.dump(qa, fh, indent=1)
    with io.open(os.path.join(tmp, "fix-state.json"), "w", encoding="utf-8") as fh:
        json.dump(fix, fh, indent=1)
    dump_jsonl(os.path.join(tmp, "qa-events.jsonl"), qa_events, trailing_garbage=not clean)
    dump_jsonl(os.path.join(tmp, "fix-events.jsonl"), fix_events)
    return tmp


def run(tmp):
    out = os.path.join(tmp, "dashboard")
    code = qd.main([tmp, "-o", out])
    return code, out


def main():
    tmp = tempfile.mkdtemp(prefix="qa-dash-test-")
    try:
        print("case 1 — a run with real problems")
        build_fixture(tmp)
        code, out = run(tmp)
        eng = qd.Engagement(tmp)

        check("exit code 2 when integrity problems exist", code == 2, "got %r" % code)
        probs = " | ".join(eng.problems)
        check("unknown finding id in fix-state is reported", "Z9" in probs)
        check("a DEV CLOSED event is reported", "only QA may CLOSE" in probs)
        check("a malformed log line is a note, not fatal",
              any("not JSON" in n for n in eng.notes))

        label, first_fail, conditions = eng.verdict(2)
        check("verdict is not GREEN", label != "GREEN within stated bounds", label)
        check("a first failing condition is named", bool(first_fail), repr(first_fail))
        by_name = {n: (ok, ev) for n, ok, ev in conditions}
        crit = [n for n, (ok, _) in by_name.items() if not ok]
        check("open critical denies the verdict",
              not by_name["No open critical or blocker, including any held at DECIDE"][0])
        check("NOT RUN guarding a critical class denies the verdict",
              not by_name[
                  "No BLOCKED or NOT RUN row guarding a critical or blocker class"][0])
        check("unmet acceptance requirement is named",
              "R-1" in by_name["Every operator acceptance requirement has a PASS"][1])
        CAL = "Every scope that owns a harness has a passing calibration row (00b)"
        check("an unlinked journey row is reported",
              any("J-9" in p and "graded_by" in p for p in eng.problems))
        check("an unlinked journey denies the calibration condition",
              not by_name[CAL][0], by_name[CAL][1])

        index = io.open(os.path.join(out, "index.html"), encoding="utf-8").read()
        rel2 = io.open(os.path.join(out, "release-2.html"), encoding="utf-8").read()
        t4 = io.open(os.path.join(out, "finding-T4.html"), encoding="utf-8").read()
        k1 = io.open(os.path.join(out, "finding-K1.html"), encoding="utf-8").read()

        check("one page per release", len(set(re.findall(r"release-(\d+)\.html", index))) == 2)
        check("one page per finding",
              all(os.path.isfile(os.path.join(out, "finding-%s.html" % f))
                  for f in ("K1", "K4", "T4")))
        check("uncited working-as-designed is flagged", "no design citation" in t4)
        check("time-in-state is derived from the log", "Time in state" in k1)
        check("the QA/DEV swimlane renders both roles",
              'class="who QA"' in k1 and 'class="who DEV"' in k1)
        check("integrity problems appear on the page", "Integrity problems" in rel2)
        check("no external resource is referenced",
              not re.search(r'(src|href)="https?://', index + rel2 + k1))
        check("no script tags in output", "<script" not in (index + rel2 + k1).lower())

        print("case 2 — a LONG row is a lien on the verdict")
        shutil.rmtree(out, ignore_errors=True)
        build_fixture(tmp, long_open=True)
        eng = qd.Engagement(tmp)
        _, _, conditions = eng.verdict(2)
        by_name = {n: ok for n, ok, _ in conditions}
        check("an open LONG row denies the verdict",
              not by_name["No LONG row unreconciled"])

        print("case 3 — the only configuration in which GREEN is legitimate")
        shutil.rmtree(out, ignore_errors=True)
        build_fixture(tmp, clean=True)
        code, out = run(tmp)
        eng = qd.Engagement(tmp)
        label, first_fail, _ = eng.verdict(2)
        check("exit code 0 when clean", code == 0, "got %r" % code)
        check("no integrity problems when clean", not eng.problems, "; ".join(eng.problems))
        check("verdict computes to GREEN", label == "GREEN within stated bounds", label)
        check("no failing condition is named", first_fail is None, repr(first_fail))
        rel2 = io.open(os.path.join(out, "release-2.html"), encoding="utf-8").read()
        check("the bounds are stated with the green",
              "is untested by this run" in rel2)
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
