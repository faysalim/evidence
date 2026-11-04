#!/usr/bin/env python3
"""Self-test for hub.py and dashboard.py. Standard library only, no network.

    python -I shared/scripts/test_hub.py

Uses tempfile rather than /tmp: on Windows, a Git-Bash /tmp path is invisible to the native
Python interpreter, which is one of the traps in shared/references/gotchas.md.

The checks marked [INVARIANT n] are the four invariants of shared/contracts/qa-dev.md, mapped
onto the hub exactly as the brief requires. The checks marked [REGRESSION] fail against the
version of hub.py whose fold ordered events by (ts, actor, seq) with second-granularity
timestamps -- two actors writing inside the same clock tick folded in actor-name order, so a DEV
move was applied before the QA add that created the item.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hub as H          # noqa: E402
import dashboard as D    # noqa: E402

FAILURES = []
HUB = None


def check(label, condition, detail=""):
    if condition:
        print("  ok   %s" % label)
    else:
        print("  FAIL %s %s" % (label, detail))
        FAILURES.append(label)


def run(*argv, **kw):
    """Invoke the CLI. Returns (exit_code, stderr_text)."""
    actor = kw.pop("actor", "qa1")
    role = kw.pop("role", "QA")
    args = ["--hub", HUB, "--actor", actor, "--role", role] + list(argv)
    err = io.StringIO()
    out = io.StringIO()
    real_err, real_out = sys.stderr, sys.stdout
    sys.stderr, sys.stdout = err, out
    try:
        code = H.main(args)
    finally:
        sys.stderr, sys.stdout = real_err, real_out
    return code, err.getvalue() + out.getvalue()


def rejected(label, *argv, **kw):
    needle = kw.pop("needle", None)
    code, text = run(*argv, **kw)
    ok = code == 1 and "REJECTED" in text
    if ok and needle:
        ok = needle.lower() in text.lower()
    check(label, ok, "code=%r text=%r" % (code, text.strip()[:160]))


def accepted(label, *argv, **kw):
    code, text = run(*argv, **kw)
    check(label, code == 0, "code=%r text=%r" % (code, text.strip()[:160]))


def state(hub_state, iid):
    item = hub_state.items.get(iid)
    return item["state"] if item else None


def main():
    global HUB
    tmp = tempfile.mkdtemp(prefix="hub-test-")
    HUB = os.path.join(tmp, "qa-reports", "hub")
    try:
        print("setup")
        accepted("init", "init", "--engagement", "fixture")
        accepted("iteration is an explicit event", "iteration", "1",
                 "--note", "first run")

        print("\ncreation authority")
        accepted("QA may create a finding", "add", "finding", "K1",
                 "-f", "title=wrong env var", "-f", "severity=blocker")
        rejected("DEV may not create a finding", "add", "finding", "K2",
                 actor="dev1", role="DEV", needle="may not create")
        rejected("an unknown type is refused", "add", "nonsense", "N1",
                 needle="unknown item type")
        rejected("an id is never reused", "add", "finding", "K1",
                 needle="never reuse")

        print("\n[INVARIANT 2] DEV claims FIXED; only QA may CLOSE")
        rejected("a finding cannot jump NEW -> CLOSED", "move", "K1", "CLOSED",
                 needle="cannot move to CLOSED")
        accepted("DEV accepts", "move", "K1", "ACCEPTED", actor="dev1", role="DEV")
        rejected("FIXED requires a commit and a build", "move", "K1", "FIXED",
                 actor="dev1", role="DEV", needle="requires")
        accepted("DEV claims FIXED with both", "move", "K1", "FIXED",
                 "-f", "commit=abc123", "-f", "build=2.5.1", actor="dev1", role="DEV")
        rejected("DEV may not CLOSE", "move", "K1", "CLOSED",
                 actor="dev1", role="DEV", needle="cannot move to CLOSED")

        print("\n[INVARIANT: the producer claims, a different role accepts]")
        rejected("the actor who claimed FIXED may not verify it",
                 "move", "K1", "VERIFIED", "-f", "evidence=x", "-f", "variant_used=y",
                 actor="dev1", role="QA", needle="does not grade their own work")
        accepted("a different QA actor may verify", "move", "K1", "VERIFIED",
                 "-f", "evidence=three runs", "-f", "variant_used=tag-only local part")
        accepted("QA closes", "move", "K1", "CLOSED")

        print("\n[INVARIANT 3] a reopen keeps its id; a regression gets a new one")
        accepted("QA reopens the same id", "move", "K1", "REOPENED", "-f", "evidence=again")
        accepted("a regression is a new id", "add", "finding", "K9",
                 "-f", "title=introduced by the fix for K1", "-f", "severity=major")
        accepted("linked introduced_by", "link", "K9", "introduced_by", "K1")
        h = H.Hub(HUB)
        check("the reopened finding kept its id and history",
              state(h, "K1") == "REOPENED" and len(h.items["K1"]["history"]) >= 6,
              "state=%r history=%d" % (state(h, "K1"), len(h.items["K1"]["history"])))

        print("\n[INVARIANT 4] severity is QA's; priority is the operator's")
        rejected("DEV may not set severity", "set", "K1", "-f", "severity=minor",
                 actor="dev1", role="DEV", needle="belongs to QA")
        accepted("QA may set severity", "set", "K1", "-f", "severity=critical")
        rejected("QA may not set priority", "set", "K1", "-f", "priority=P3",
                 needle="belongs to OPERATOR")
        accepted("the operator may set priority", "set", "K1", "-f", "priority=P1",
                 actor="faisal", role="OPERATOR")

        print("\n[INVARIANT 1] NEW is not a resting state")
        accepted("file a finding and hand it over", "add", "finding", "K5",
                 "-f", "title=left untriaged", "-f", "severity=major",
                 "-f", "handed_over=true")
        h = H.Hub(HUB)
        problems = h.validate()
        check("validate flags a handed-over finding still NEW",
              any("still NEW" in p and "K5" in p for p in problems),
              "; ".join(problems)[:200])

        print("\nstory acceptance needs its linked cases to pass")
        accepted("PO creates a story", "add", "story", "S1", "-f", "title=trial key flow",
                 actor="po1", role="PO")
        rejected("READY requires acceptance criteria", "move", "S1", "READY",
                 actor="po1", role="PO", needle="requires")
        accepted("READY with criteria", "move", "S1", "READY",
                 "-f", "acceptance_criteria=a key arrives and activates a real binary",
                 actor="po1", role="PO")
        accepted("DEV picks it up", "move", "S1", "IN_PROGRESS", actor="dev1", role="DEV")
        accepted("DEV claims DONE", "move", "S1", "DONE", "-f", "commit=def456",
                 actor="dev1", role="DEV")
        rejected("a story with no linked case cannot be accepted", "move", "S1", "ACCEPTED",
                 actor="po1", role="PO", needle="no linked cases")
        accepted("QA designs the case", "add", "case", "S5-01",
                 "-f", "scope=licensing", "-f", "action=POST /v1/trial verbatim",
                 "-f", "oracle=a usable key arrives in a real mailbox and activates a binary")
        accepted("case verifies the story", "link", "S5-01", "verifies", "S1")
        accepted("case FAILs", "move", "S5-01", "FAIL", "-f", "evidence=403 from the endpoint")
        rejected("a story cannot be accepted while its case FAILs", "move", "S1", "ACCEPTED",
                 actor="po1", role="PO", needle="not PASS")
        accepted("re-arm the case", "move", "S5-01", "DESIGNED")
        accepted("case PASSes", "move", "S5-01", "PASS", "-f", "evidence=key activated")
        # Order matters here: once the PO has accepted, ACCEPTED -> ACCEPTED is simply not a
        # transition, so a later attempt is refused for the wrong reason and proves nothing.
        rejected("the DEV who claimed DONE may not accept it, even wearing the PO hat",
                 "move", "S1", "ACCEPTED", actor="dev1", role="PO",
                 needle="does not grade their own work")
        accepted("a different actor as PO may accept", "move", "S1", "ACCEPTED",
                 actor="po1", role="PO")

        print("\nconcurrency, duplicates and fold stability")
        # [REGRESSION] two actors inside one clock tick: a DEV move must not fold before the
        # QA add that created the item.
        burst = os.path.join(tmp, "burst", "hub")
        os.makedirs(os.path.join(burst, "events"), exist_ok=True)
        H.append_event(burst, "QA", "aaa_qa", {"op": "init", "engagement": "burst"})
        # Actor names chosen so the QA add sorts AFTER the DEV move on the (ts, actor, seq) key;
        # only the `after` link can order them correctly. Roles must be real ones: creation
        # authority is now enforced on replay too, so a synthetic role name is refused.
        add = H.append_event(burst, "QA", "zzz_qa",
                             {"op": "add", "item": "B1", "type": "finding",
                              "fields": {"title": "t", "severity": "major"}})
        H.append_event(burst, "DEV", "aaa_dev",
                       {"op": "move", "item": "B1", "to": "ACCEPTED",
                        "after": [add["event_id"]]})
        hb = H.Hub(burst)
        check("[REGRESSION] a move from another actor folds after the add that created the item",
              state(hb, "B1") == "ACCEPTED" and not hb.problems,
              "state=%r problems=%r" % (state(hb, "B1"), hb.problems[:2]))

        # duplicate event_id
        dup_path = H.actor_log_path(burst, "DEV", "aaa_dev")
        with io.open(dup_path, "r", encoding="utf-8") as fh:
            last = fh.readlines()[-1]
        with io.open(dup_path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(last)
        hb = H.Hub(burst)
        check("a duplicate event_id is ignored and reported",
              state(hb, "B1") == "ACCEPTED"
              and any("duplicate event_id" in p for p in hb.problems),
              "state=%r problems=%r" % (state(hb, "B1"), hb.problems[:2]))

        # fold stability: shuffle file read order by renaming actors, state must match
        h1 = H.Hub(HUB)
        snapshot1 = {i: h1.items[i]["state"] for i in h1.items}
        h2 = H.Hub(HUB)
        snapshot2 = {i: h2.items[i]["state"] for i in h2.items}
        check("the fold is stable across runs", snapshot1 == snapshot2)

        # an event that waits forever is reported, not silently dropped
        orphan = os.path.join(tmp, "orphan", "hub")
        os.makedirs(os.path.join(orphan, "events"), exist_ok=True)
        H.append_event(orphan, "QA", "q", {"op": "add", "item": "O1", "type": "finding",
                                           "fields": {"title": "t"}})
        H.append_event(orphan, "QA", "q", {"op": "move", "item": "O1", "to": "ACCEPTED",
                                           "after": ["nobody#99"]})
        ho = H.Hub(orphan)
        check("an event waiting on an absent event is reported",
              any("never arrive" in p for p in ho.problems), "%r" % ho.problems[:2])

        print("\nclock skew is reported, never reordered")
        skewed = os.path.join(tmp, "skew", "hub")
        os.makedirs(os.path.join(skewed, "events"), exist_ok=True)
        a = H.append_event(skewed, "QA", "q", {"op": "add", "item": "C1", "type": "finding",
                                               "fields": {"title": "t", "severity": "major"},
                                               "ts": "2026-11-04T12:00:00.000000Z"})
        H.append_event(skewed, "DEV", "d", {"op": "move", "item": "C1", "to": "ACCEPTED",
                                            "after": [a["event_id"]],
                                            "ts": "2026-11-04T11:00:00.000000Z"})
        hs = H.Hub(skewed)
        check("a backwards timestamp is skew, and causal order still wins",
              state(hs, "C1") == "ACCEPTED" and any("clock skew" in s for s in hs.skew),
              "state=%r skew=%r" % (state(hs, "C1"), hs.skew[:2]))

        print("\nimport keeps ids and marks provenance")
        old_dir = os.path.join(tmp, "old-reports")
        os.makedirs(old_dir, exist_ok=True)
        with io.open(os.path.join(old_dir, "qa-state.json"), "w", encoding="utf-8") as fh:
            json.dump({"engagement": "legacy", "iteration": 3,
                       "findings": [{"id": "K1", "title": "old blocker", "severity": "blocker",
                                     "status": {"1": "OPEN", "3": "VERIFIED FIXED"},
                                     "closed_in": 3},
                                    {"id": "L5", "title": "subaddressing", "severity": "major",
                                     "status": {"3": "PARTIAL"}, "closed_in": None}],
                       "cases": [{"id": "S5-01", "scope": "licensing", "action": "POST",
                                  "oracle": "a real key", "finding": "K1"}]}, fh)
        imp = os.path.join(tmp, "imported", "hub")
        code, text = H.main(["--hub", imp, "--actor", "lead", "--role", "QA",
                             "import", old_dir]), ""
        hi = H.Hub(imp)
        check("import preserves ids unchanged",
              {"K1", "L5", "S5-01"} <= set(hi.items), sorted(hi.items))
        check("imported items are marked reconstructed",
              all(hi.items[i]["provenance"] == "reconstructed" for i in ("K1", "L5", "S5-01")))
        check("import does not inherit the old verdict",
              state(hi, "K1") == "NEW" and any("re-triage" in n["text"]
                                               for n in hi.items["K1"]["notes"]),
              "state=%r" % state(hi, "K1"))
        check("import records the iteration as an event", hi.meta.get("iteration") == 3,
              "%r" % hi.meta.get("iteration"))
        check("import preserves the case -> finding link",
              any(l["target"] == "K1" and l["rel"] == "verifies"
                  for l in hi.items["S5-01"]["links"]))

        print("\ngenerated views")
        accepted("views are generated", "views")
        view_path = os.path.join(os.path.dirname(HUB), "qa-state.json")
        with io.open(view_path, "r", encoding="utf-8") as fh:
            view = json.load(fh)
        check("the view carries a generated_from header",
              "generated_from" in view and "event_count" in view["generated_from"])
        check("the view warns it is generated",
              "never hand-edit" in view["generated_from"].get("warning", "").lower())
        check("the view has the old shape: findings and cases arrays",
              isinstance(view.get("findings"), list) and isinstance(view.get("cases"), list))
        check("a view finding carries id, title, severity, status",
              all(k in view["findings"][0] for k in ("id", "title", "severity", "status")),
              sorted(view["findings"][0]))
        check("a view case carries id, oracle, result",
              all(k in view["cases"][0] for k in ("id", "oracle", "result")),
              sorted(view["cases"][0]))
        check("not_verified is projected from NOT_RUN/BLOCKED cases",
              isinstance(view.get("not_verified"), list))

        # a stale view is flagged
        accepted("add an item after generating the view", "add", "risk", "R9",
                 "-f", "title=stale view probe", actor="dm1", role="DELIVERY")
        h = H.Hub(HUB)
        check("validate flags the now-stale view",
              any("stale" in p and "qa-state.json" in p for p in h.validate()),
              "; ".join(h.validate())[:200])
        accepted("regenerating clears it", "views")
        h = H.Hub(HUB)
        check("no stale-view problem after regeneration",
              not any("stale" in p for p in h.validate()), "; ".join(h.validate())[:160])

        print("\ndashboard")
        out = os.path.join(tmp, "dash")
        pages = D.render(H.Hub(HUB), out)
        index = io.open(os.path.join(out, "index.html"), encoding="utf-8").read()
        check("renders a page per item plus type pages", pages >= len(H.Hub(HUB).items) + 1,
              "pages=%d" % pages)
        check("self-contained: no external resources",
              "https://" not in index and "http://" not in index)
        check("no script tags", "<script" not in index.lower())
        check("required views are present",
              all(s in index for s in ("All items by type and state", "Per role",
                                       "Awaiting the operator", "Traceability",
                                       "Time in state")))
        label, first_fail, conditions = D.verdict(H.Hub(HUB))
        check("the verdict is not GREEN while a critical finding is open",
              label != "GREEN within stated bounds", label)
        check("a first failing condition is always named", bool(first_fail), repr(first_fail))
        check("the condition table is non-trivial", len(conditions) >= 10, len(conditions))

        print("\nGREEN is reachable, and only when everything holds")
        green = os.path.join(tmp, "green", "hub")

        def g(*argv, **kw):
            actor = kw.pop("actor", "qa1")
            role = kw.pop("role", "QA")
            return H.main(["--hub", green, "--actor", actor, "--role", role] + list(argv))

        devnull = io.StringIO()
        real = sys.stdout
        sys.stdout = devnull
        try:
            g("init", "--engagement", "green")
            g("iteration", "1")
            # A gate row records the build it ran on. Without that the row cannot be shown to
            # have run on the build the verdict names, which is the whole point of the condition
            # -- and an unstamped row used to read as agreement.
            g("add", "case", "S5-00a", "-f", "scope=licensing", "-f", "action=smoke",
              "-f", "oracle=first success through the real client",
              "-f", 'ran_under={"build":"sha256:abc"}')
            g("move", "S5-00a", "PASS", "-f", "evidence=ok")
            g("add", "case", "S5-00b", "-f", "scope=licensing", "-f", "action=inject one",
              "-f", "oracle=reports exactly one", "-f", "graded_by=licensing",
              "-f", 'ran_under={"build":"sha256:abc"}')
            g("move", "S5-00b", "PASS", "-f", "evidence=exactly 1")
            g("add", "case", "R-1", "-f", "scope=requirements", "-f", "graded_by=licensing",
              "-f", "action=contract 4.2", "-f", "oracle=independent recompute")
            g("move", "R-1", "PASS", "-f", "evidence=ok")
            g("add", "release", "REL-1", "-f", "title=2.5.1", actor="dm1", role="DELIVERY")
            g("move", "REL-1", "CANDIDATE", "-f", "build=sha256:abc", actor="dev1", role="DEV")
            g("move", "REL-1", "GREEN", "-f", "bounds=1 node, 20k keys",
              "-f", "does_not_cover=scope 8 was one hour, not a pen test")
            g("views")
        finally:
            sys.stdout = real
        hg = H.Hub(green)
        label, first_fail, _ = D.verdict(hg)
        check("a complete hub computes GREEN", label == "GREEN within stated bounds",
              "%s / %s" % (label, first_fail))
        gi = D.render_index(hg)
        check("GREEN still states its bounds", "is untested by this run" in gi)
        check("GREEN still states what it does not cover",
              "not a pen test" in gi)

        # and one broken thing takes it away again
        sys.stdout = devnull
        try:
            g("add", "finding", "Z1", "-f", "title=late blocker", "-f", "severity=critical")
        finally:
            sys.stdout = real
        label2, ff2, _ = D.verdict(H.Hub(green))
        check("one open critical removes GREEN", label2 == "NOT GREEN", label2)
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
