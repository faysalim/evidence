#!/usr/bin/env python3
"""A role that the model does not declare cannot write anything, and cannot hide in a replay.

    python -I tests/test_role_vocabulary.py
    python -I tests/test_role_vocabulary.py -v

Why this exists. A real engagement's hub was found with four events written under the role `LEAD`.
`LEAD` is not one of the eighteen roles. The events were `init`, the `iteration` marker, and **both
`profile` writes** -- so the profile every downstream skill reads to learn the product class and the
team's vocabulary was authored by a role that does not exist, and `hub.py validate` reported
**0 problems**.

The cause: `identity()` checked that a role was *present*, never that it *existed*, and the only
role check in the codebase was per-transition. So `init`, `profile`, `iteration`, `note` and `link`
accepted any string at all. `add` and `move` were covered only because their type declares who may
create or transition.

This is the FIFTH closed vocabulary found declared-and-unenforced, after `domains`, `link_types`,
`confidence` and `owner_role`. The sweep that was supposed to end that class checked *field*
vocabularies and never checked the role on the event itself -- which is the one that carries the
whole attribution model, because the path IS the attribution.

Enforced at `append_event`, the single choke point every write passes through, and on the fold, so a
hand-written log cannot do what the CLI refuses.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HUB = os.path.join(ROOT, "shared", "scripts", "hub.py")
VERBOSE = "-v" in sys.argv

FAILURES = []


def run(hub, *args):
    p = subprocess.run([sys.executable, "-I", "-B", HUB, "--hub", hub] + [str(a) for a in args],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def check(label, cond, detail=""):
    if cond:
        if VERBOSE:
            print("  ok   %s" % label)
    else:
        print("  FAIL %s%s" % (label, (" -- " + detail) if detail else ""))
        FAILURES.append(label)


def main():
    model = json.loads(io.open(os.path.join(ROOT, "shared", "hub", "model.json"),
                               encoding="utf-8").read())
    roles = sorted(model["roles"])
    print("%d declared role(s)" % len(roles))

    tmp = tempfile.mkdtemp(prefix="rolevocab_")
    try:
        # --- every op that used to accept any string -------------------------------------
        # These are the ones that bit a real engagement: none involves a type or a transition,
        # so neither the `create` list nor the transition `roles` list ever saw them.
        hub = os.path.join(tmp, "init")
        rc, out = run(hub, "init", "--actor", "claude-lead", "--role", "LEAD")
        check("init under an undeclared role is REJECTED", rc != 0,
              "exit %d: %s" % (rc, out.strip()[:150]))
        check("the refusal names the role", "LEAD" in out, out.strip()[:170])
        check("and lists what is declared", "TECH_LEAD" in out, out.strip()[:200])
        check("nothing was created", not os.path.isdir(os.path.join(hub, "events")),
              "an events dir exists despite the refusal")

        hub = os.path.join(tmp, "ops")
        run(hub, "init", "--actor", "h1", "--role", "HEAD_OF_PRODUCT")
        for op_args, label in (
            (["profile", "--set", "mode=existing"], "profile"),
            (["iteration", "1"], "iteration"),
        ):
            rc, out = run(hub, *(op_args + ["--actor", "claude-lead", "--role", "LEAD"]))
            check("%s under an undeclared role is REJECTED" % label, rc != 0,
                  "exit %d: %s" % (rc, out.strip()[:130]))

        # note and link need an item, so make one legitimately first
        run(hub, "add", "finding", "F-1", "-f", "title=real", "-f", "severity=major",
            "--actor", "q1", "--role", "QA")
        run(hub, "add", "finding", "F-2", "-f", "title=real too", "-f", "severity=minor",
            "--actor", "q1", "--role", "QA")
        for op_args, label in (
            (["note", "F-1", "a note"], "note"),
            (["link", "F-1", "duplicate_of", "F-2"], "link"),
        ):
            rc, out = run(hub, *(op_args + ["--actor", "claude-lead", "--role", "LEAD"]))
            check("%s under an undeclared role is REJECTED" % label, rc != 0,
                  "exit %d: %s" % (rc, out.strip()[:130]))

        # --- every declared role still works ---------------------------------------------
        for role in roles:
            hub2 = os.path.join(tmp, "ok-%s" % role)
            rc, out = run(hub2, "init", "--actor", "a1", "--role", role)
            check("declared role %s may still init" % role, rc == 0, out.strip()[:120])

        # --- a near-miss gets a useful refusal, not a bare rejection ---------------------
        hub3 = os.path.join(tmp, "nearmiss")
        rc, out = run(hub3, "init", "--actor", "a1", "--role", "TECHLEAD")
        check("a near-miss role is refused", rc != 0, "exit %d" % rc)
        check("  and the refusal suggests the real one", "TECH_LEAD" in out, out.strip()[:200])
        rc, out = run(hub3, "init", "--actor", "a1", "--role", "qa")
        check("a lowercase role is refused rather than silently accepted", rc != 0,
              "exit %d: %s" % (rc, out.strip()[:130]))
        check("  and QA is suggested", "QA" in out, out.strip()[:170])

        # --- the fold must flag one that is already in a log -----------------------------
        hub4 = os.path.join(tmp, "replay")
        run(hub4, "init", "--actor", "h1", "--role", "HEAD_OF_PRODUCT")
        d = os.path.join(hub4, "events", "LEAD")
        os.makedirs(d, exist_ok=True)
        with io.open(os.path.join(d, "claude-lead.jsonl"), "w", encoding="utf-8",
                     newline="") as fh:
            fh.write(json.dumps({
                "v": 1, "event_id": "LEAD/claude-lead#1", "seq": 1,
                "ts": "2026-11-05T10:00:00.000000Z", "actor": "claude-lead", "role": "LEAD",
                "op": "profile", "fields": {"mode": "existing"}}) + "\n")
        rc, out = run(hub4, "validate")
        check("a planted undeclared role is a problem on replay", rc != 0,
              "exit %d: %s" % (rc, out.strip()[:200]))
        check("  and the problem names the role", "LEAD" in out, out.strip()[:200])

        # The real hub's symptom, restated as the assertion that would have caught it: a profile
        # written by a role that does not exist must never read as clean.
        check("  so a profile authored by a nonexistent role cannot report 0 problems",
              "0 problem" not in out, out.strip()[:200])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILURES:
        print("%d failure(s)" % len(FAILURES))
        return 1
    print("  ok   the role vocabulary is closed on every write path and on the fold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
