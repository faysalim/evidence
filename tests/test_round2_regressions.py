#!/usr/bin/env python3
"""Regressions for what independent verification found still open after council round 1.

    python -I tests/test_round2_regressions.py

A fresh agent re-ran every applied repro plus one adversarial neighbour each. Most fixes verified;
these are the ones that came back PARTIAL or STILL PRESENT, each now a test. The most valuable was
a defect my own fix created: marking two findings as duplicates *of each other* took two open
criticals out of the verdict, because DUPLICATE counted as closed.

The common root of four of them: the CLI refused the forbidden thing and the FOLD did not, so a
hand-written line did what no command could. That is the same class as the `--state` bypass, which
had been closed on replay -- these were missed.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "shared", "scripts"))

import dashboard as D  # noqa: E402
import hub as H        # noqa: E402

FAILURES = []


def check(label, condition, detail=""):
    if condition:
        print("  ok   %s" % label)
    else:
        print("  FAIL %s %s" % (label, detail))
        FAILURES.append(label)


def cli(hub, actor, role, *args):
    """Run the CLI with stdout silenced. Returns the exit code."""
    out, real = io.StringIO(), sys.stdout
    sys.stdout = out
    try:
        return H.main(["--hub", hub, "--actor", actor, "--role", role] + [str(a) for a in args])
    finally:
        sys.stdout = real


def write_line(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(payload) + "\n")


def green_base(hub):
    """A hub that genuinely computes GREEN, so an attack on it can actually fail.

    This is the point verification made about the first version of these tests: a regression run
    against a hub that was not green anyway would have passed with the fix removed.
    """
    cli(hub, "q", "QA", "init", "--engagement", "base")
    cli(hub, "q", "QA", "iteration", "1")
    for cid, action, oracle in (("S1-00a", "smoke", "first success through the real client"),
                                ("S1-00b", "inject one known defect", "reports exactly one")):
        cli(hub, "q", "QA", "add", "case", cid, "-f", "scope=p", "-f", "graded_by=p",
            "-f", "action=%s" % action, "-f", "oracle=%s" % oracle,
            "-f", 'ran_under={"build":"sha256:abc"}')
        cli(hub, "q", "QA", "move", cid, "PASS", "-f", "evidence=ok")
    cli(hub, "q", "QA", "add", "case", "R-1", "-f", "scope=requirements",
        "-f", "graded_by=p", "-f", "action=contract 4.2", "-f", "oracle=independent recompute")
    cli(hub, "q", "QA", "move", "R-1", "PASS", "-f", "evidence=ok")
    cli(hub, "dm", "DELIVERY", "add", "release", "REL-1", "-f", "title=1.0")
    cli(hub, "d", "DEV", "move", "REL-1", "CANDIDATE", "-f", "build=sha256:abc")
    # Readiness outside QA, scoped to this release and this build: the verdict counts only rows
    # linked to the release being judged whose build matches it.
    cli(hub, "h", "HEAD_OF_PRODUCT", "profile",
        "--set", 'required_checkpoints=["rollback-rehearsed"]')
    cli(hub, "ops", "DEVOPS", "add", "readiness", "RD-1",
        "-f", "title=rollback rehearsed", "-f", "owner_role=DEVOPS",
        "-f", "checkpoint=rollback-rehearsed")
    cli(hub, "ops", "DEVOPS", "link", "RD-1", "gates", "REL-1")
    cli(hub, "ops", "DEVOPS", "move", "RD-1", "MET",
        "-f", "evidence=rehearsed, 41s", "-f", "build=sha256:abc")
    return hub


def main():
    tmp = tempfile.mkdtemp(prefix="round2-")
    try:
        print("HA-3 round 2 -- a DUPLICATE cycle must not hide two criticals")
        # On a GENUINELY GREEN base. The first version of this test ran on a hub that was not
        # green anyway, so it would have passed with the fix removed — verification said so, and
        # it was right. A regression test that cannot fail proves nothing.
        hub = green_base(os.path.join(tmp, "dup", "hub"))
        label0, _gap0, _c0 = D.verdict(H.Hub(hub))
        check("the base really is GREEN before the attack",
              label0 == "GREEN within stated bounds", label0)

        cli(hub, "q", "QA", "add", "finding", "C-1",
            "-f", "title=acked loss", "-f", "severity=critical")
        cli(hub, "q", "QA", "add", "finding", "C-2",
            "-f", "title=same root cause", "-f", "severity=critical")
        a = cli(hub, "dev1", "DEV", "move", "C-1", "DUPLICATE", "-f", "duplicate_of=C-2")
        b = cli(hub, "dev1", "DEV", "move", "C-2", "DUPLICATE", "-f", "duplicate_of=C-1")
        h = H.Hub(hub)
        label, gap, conditions = D.verdict(h)
        check("both moves are legal on their own", a == 0 and b == 0, "rc=%r/%r" % (a, b))
        check("[REGRESSION] the cycle does not produce GREEN on a green base",
              label != "GREEN within stated bounds", "%s / %s" % (label, gap))
        check("   and the failing condition names the cycle",
              any("DUPLICATE" in n and not ok for n, ok, _ in conditions),
              [n for n, ok, _ in conditions if not ok])

        print("\nNEW-1 -- `set duplicate_of` must not bypass that check")
        hub = green_base(os.path.join(tmp, "setdup", "hub"))
        cli(hub, "q", "QA", "add", "finding", "C-9",
            "-f", "title=acked loss", "-f", "severity=critical")
        cli(hub, "q", "QA", "add", "finding", "M-9", "-f", "title=m", "-f", "severity=minor")
        cli(hub, "dev1", "DEV", "move", "C-9", "DUPLICATE", "-f", "duplicate_of=M-9")
        rc = cli(hub, "dev1", "DEV", "set", "C-9", "-f", "duplicate_of=R-1")
        check("[REGRESSION] set cannot point a finding at a case", rc != 0, "rc=%r" % rc)
        rc = cli(hub, "dev1", "DEV", "set", "C-9", "-f", "duplicate_of=C-9")
        check("   nor at itself", rc != 0, "rc=%r" % rc)
        rc = cli(hub, "dev1", "DEV", "set", "C-9", "-f", "duplicate_of=NOPE-1")
        check("   nor at nothing", rc != 0, "rc=%r" % rc)
        label, _gap, _c = D.verdict(H.Hub(hub))
        check("   and the open minor it points at still denies",
              label != "GREEN within stated bounds", label)

        print("\nNEW-2 -- a log nested under another role's directory is not folded")
        hub = green_base(os.path.join(tmp, "nested", "hub"))
        cli(hub, "q", "QA", "add", "finding", "C-7", "-f", "title=t", "-f", "severity=critical")
        write_line(os.path.join(hub, "events", "DEV", "QA", "x.jsonl"),
                   {"v": 1, "event_id": "QA/x#1", "seq": 1, "actor": "x", "role": "QA",
                    "ts": "2026-11-04T23:30:00.000000Z", "op": "move", "item": "C-7",
                    "to": "WITHDRAWN", "fields": {"reason": "forged"}})
        h = H.Hub(hub)
        check("[REGRESSION] the nested line is reported",
              any("not at events/<ROLE>/<actor>.jsonl" in p for p in h.validate()),
              h.validate()[:1])
        check("   and the critical is still open", h.items["C-7"]["state"] == "NEW",
              h.items["C-7"]["state"])
        label, _gap, _c = D.verdict(h)
        check("   so the verdict is not GREEN", label != "GREEN within stated bounds", label)

        print("\nNEW-3 -- gate rows must match a release still under consideration")
        hub = green_base(os.path.join(tmp, "twobuilds", "hub"))
        cli(hub, "dm", "DELIVERY", "add", "release", "REL-2", "-f", "title=next")
        cli(hub, "d", "DEV", "move", "REL-2", "CANDIDATE", "-f", "build=sha256:new")
        label, gap, conditions = D.verdict(H.Hub(hub))
        row = [(n, ok, ev) for n, ok, ev in conditions if "ran on the build" in n]
        check("[REGRESSION] a new candidate cannot inherit the old release's gate rows",
              row and not row[0][1], row)

        print("\nNEW-4 -- a JSON-typed empty does not satisfy a required field")
        hub = green_base(os.path.join(tmp, "jsonempty", "hub"))
        cli(hub, "q", "QA", "add", "finding", "F-4", "-f", "title=t", "-f", "severity=minor")
        for literal in ("null", "[]", "{}", '""'):
            rc = cli(hub, "d1", "DEV", "move", "F-4", "REJECTED", "-f", "reason=%s" % literal)
            check("[REGRESSION] reason=%s is refused" % literal, rc != 0, "rc=%r" % rc)
        cli(hub, "an", "ANALYST", "add", "metric", "MM-1", "-f", "name=x",
            "-f", "denominator=signups, excluding internal")
        rc = cli(hub, "an", "ANALYST", "move", "MM-1", "BASELINED",
                 "-f", "denominator=signups", "-f", "baseline=0",
                 "-f", "evidence=counted the rows; there were none")
        check("   but a baseline of 0 is still a reading", rc == 0, "rc=%r" % rc)

        print("\nreplay gaps -- a hand-written line must not do what the CLI refuses")
        cases = [
            ({"op": "add", "item": "S9-01", "type": "case", "fields": {"action": "a"}},
             "S9-01", "an add with no oracle"),
            ({"op": "add", "item": "F:9", "type": "finding", "fields": {"title": "t"}},
             "F:9", "an id containing a colon"),
            ({"op": "add", "item": "S9-02", "type": "case",
              "fields": {"action": "a", "oracle": "o", "guards": "prose ceiling critical"}},
             "S9-02", "a prose guards value"),
            ({"op": "add", "item": "F-8", "type": "finding",
              "fields": {"title": "t", "severity": "P0"}},
             "F-8", "a severity outside the vocabulary"),
        ]
        for i, (payload, item_id, label) in enumerate(cases):
            hub = os.path.join(tmp, "hw%d" % i, "hub")
            cli(hub, "q", "QA", "init", "--engagement", "hw")
            seq = 90 + i
            payload.update({"v": 1, "event_id": "QA/q#%d" % seq, "seq": seq, "actor": "q",
                            "role": "QA", "ts": "2026-11-04T23:00:00.000000Z"})
            write_line(os.path.join(hub, "events", "QA", "q.jsonl"), payload)
            folded = H.Hub(hub)
            check("[REGRESSION] %s is a problem on replay" % label,
                  bool(folded.problems), "problems=%r" % folded.problems[:1])
            check("   and %s is not folded in" % item_id, item_id not in folded.items)

        print("\nHA-13 round 2 -- the path is the attribution")
        hub = os.path.join(tmp, "mis", "hub")
        cli(hub, "q", "QA", "init", "--engagement", "mis")
        cli(hub, "q", "QA", "add", "finding", "F-1",
            "-f", "title=t", "-f", "severity=critical")
        write_line(os.path.join(hub, "events", "DEV", "ghost.jsonl"),
                   {"v": 1, "event_id": "QA/ghost#1", "seq": 1, "actor": "ghost", "role": "QA",
                    "ts": "2026-11-04T23:00:00.000000Z", "op": "move", "item": "F-1",
                    "to": "WITHDRAWN", "fields": {"reason": "x"}})
        h = H.Hub(hub)
        check("[REGRESSION] a misattributed line is reported as a problem",
              any("MISATTRIBUTED" in p for p in h.validate()), h.validate()[:1])
        check("   and is applied as the path says, so the claimed role gains nothing",
              h.items["F-1"]["state"] == "NEW", "state=%s" % h.items["F-1"]["state"])

        hub = os.path.join(tmp, "orphan", "hub")
        cli(hub, "q", "QA", "init", "--engagement", "o")
        write_line(os.path.join(hub, "events", "loose.jsonl"),
                   {"v": 1, "event_id": "QA/x#1", "seq": 1, "actor": "x", "role": "QA",
                    "ts": "2026-11-04T23:00:00.000000Z", "op": "add", "item": "F-9",
                    "type": "finding", "fields": {"title": "t"}})
        h = H.Hub(hub)
        check("[REGRESSION] a log outside events/<ROLE>/ is not folded at all",
              "F-9" not in h.items, sorted(h.items))
        check("   and says why",
              any("events/<ROLE>/<actor>.jsonl" in p for p in h.validate()),
              h.validate()[:1])

        print("\nempty strings must not satisfy a required field")
        hub = os.path.join(tmp, "empty", "hub")
        cli(hub, "q", "QA", "init", "--engagement", "e")
        cli(hub, "q", "QA", "add", "cleanup", "C-9", "-f", "title=cluster")
        rc = cli(hub, "q", "QA", "move", "C-9", "TORN_DOWN", "-f", "verified_by=")
        check("[REGRESSION] an empty verified_by is refused", rc != 0, "rc=%r" % rc)
        rc = cli(hub, "q", "QA", "add", "case", "S9-9", "-f", "action=a", "-f", "oracle=")
        check("[REGRESSION] an empty oracle is refused", rc != 0, "rc=%r" % rc)
        rc = cli(hub, "q", "QA", "move", "C-9", "TORN_DOWN",
                 "-f", "verified_by=re-listed instances: NONE")
        check("   and a real one is accepted", rc == 0, "rc=%r" % rc)

        print("\nHA-12 round 2 -- the view body, not just the event ids")
        hub = os.path.join(tmp, "view", "hub")
        cli(hub, "q", "QA", "init", "--engagement", "v")
        cli(hub, "q", "QA", "add", "finding", "F-1",
            "-f", "title=t", "-f", "severity=critical")
        cli(hub, "q", "QA", "views")
        view_path = os.path.join(os.path.dirname(hub), "qa-state.json")
        with io.open(view_path, "r", encoding="utf-8") as fh:
            view = json.load(fh)
        view["findings"][0]["severity"] = "polish"      # header deliberately left intact
        with io.open(view_path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(view, fh, indent=1)
        h = H.Hub(hub)
        check("[REGRESSION] a hand-edited view with an intact header is caught",
              any("does not match what the hub would generate" in p for p in h.validate()),
              h.validate()[:1])
        cli(hub, "q", "QA", "views")
        # Asserts the VIEW problem is gone, not that the hub is problem-free: this probe's hub
        # holds a finding with no scope and no cases, which case-first now reports, and that is
        # a different subject.
        check("   and regenerating clears it",
              not any("does not match what the hub would generate" in p
                      for p in H.Hub(hub).validate()),
              H.Hub(hub).validate()[:1])

        print("\nMG-3 round 2 -- a gate row with no recorded build is not agreement")
        hub = os.path.join(tmp, "stamp", "hub")
        cli(hub, "q", "QA", "init", "--engagement", "s")
        cli(hub, "q", "QA", "add", "case", "S1-00a", "-f", "scope=p", "-f", "graded_by=p",
            "-f", "action=smoke", "-f", "oracle=first success")
        cli(hub, "q", "QA", "move", "S1-00a", "PASS", "-f", "evidence=ok")
        cli(hub, "q", "QA", "add", "case", "S1-00b", "-f", "scope=p", "-f", "graded_by=p",
            "-f", "action=inject", "-f", "oracle=reports one")
        cli(hub, "q", "QA", "move", "S1-00b", "PASS", "-f", "evidence=one")
        cli(hub, "dm", "DELIVERY", "add", "release", "REL-1", "-f", "title=r")
        cli(hub, "d", "DEV", "move", "REL-1", "CANDIDATE", "-f", "build=sha256:abc")
        _label, _gap, conditions = D.verdict(H.Hub(hub))
        row = [(n, ok, ev) for n, ok, ev in conditions if "ran on the build" in n]
        check("[REGRESSION] an unstamped gate row fails the build condition",
              row and not row[0][1], row)
        check("   and the message names the rows",
              row and ("ran_under.build" in row[0][2] or "no smoke row" in row[0][2]), row)

        print("\nfix RETURNED must be resumable")
        hub = os.path.join(tmp, "ret", "hub")
        cli(hub, "q", "QA", "init", "--engagement", "r")
        cli(hub, "d", "DEV", "add", "fix", "FIX-1", "-f", "root_cause=x")
        cli(hub, "d", "DEV", "move", "FIX-1", "TEST_FAILS_FIRST",
            "-f", "test=t", "-f", "evidence=fails on the unfixed build")
        cli(hub, "d", "DEV", "move", "FIX-1", "DELIVERED",
            "-f", "commit=abc", "-f", "build=sha256:abc")
        cli(hub, "q", "QA", "move", "FIX-1", "RETURNED", "-f", "reason=no digest")
        rc = cli(hub, "d", "DEV", "move", "FIX-1", "DELIVERED",
                 "-f", "commit=def", "-f", "build=sha256:def")
        check("[REGRESSION] a returned handback can be redelivered under the same id", rc == 0,
              "rc=%r" % rc)

        print("\nHA-8 round 2 -- a cleanup item the operator owns reaches their queue")
        hub = os.path.join(tmp, "cl", "hub")
        cli(hub, "q", "QA", "init", "--engagement", "c")
        cli(hub, "q", "QA", "add", "cleanup", "C-1", "-f", "title=cluster", "-f", "cost=hourly")
        cli(hub, "q", "QA", "move", "C-1", "OPERATORS", "-f", "reason=only they can delete it")
        h = H.Hub(hub)
        check("[REGRESSION] it is listed as waiting on the operator",
              "OPERATOR" in h.waiting_on(h.items["C-1"]), h.waiting_on(h.items["C-1"]))
        _l, _g, conds = D.verdict(h)
        check("   and it still denies the verdict",
              any("billing or exposed" in n and not ok for n, ok, _ in conds),
              [n for n, ok, _ in conds if not ok])
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
