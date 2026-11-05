#!/usr/bin/env python3
"""A readiness checkpoint is met by the role that owns it, and by nobody else.

    python -I tests/test_readiness_ownership.py
    python -I tests/test_readiness_ownership.py -v

Why this exists. The readiness gate was added so a green verdict would stop meaning "QA found
nothing" -- and it shipped with no ownership enforcement at all. A review found three ways through
it, all reproduced before this file was written:

  1. DEVOPS created a row with `owner_role=SECURITY`, and **SUPPORT** moved it to MET with
     `evidence="trust me"`. Any readiness role could sign off any other's gate.
  2. TECH_LEAD -- a release-side role -- created a row AND met it. The role computing the go/no-go
     was manufacturing its own gate inputs, which is principle 7 inverted: the producer accepting
     their own work, on the one condition that exists to bring an outside voice in.
  3. `owner_role=BANANA` was stored without a word. A fourth field declared in prose and enforced
     nowhere -- written *during* the sweep whose entire purpose was closing that class.

So: `owner_role` is a closed vocabulary; only the role it names may move the row to MET; release-side
roles may create rows and never meet them; and the operator alone waives.
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

READINESS_ROLES = ("DEVOPS", "SECURITY", "SUPPORT")
RELEASE_SIDE = ("DELIVERY", "TECH_LEAD", "OPERATOR")

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


def fresh(tmp, name):
    hub = os.path.join(tmp, name)
    run(hub, "init", "--actor", "h1", "--role", "HEAD_OF_PRODUCT")
    return hub


def main():
    m = json.loads(io.open(os.path.join(ROOT, "shared", "hub", "model.json"),
                           encoding="utf-8").read())
    vocab = (m.get("field_vocabularies") or {}).get("owner_role")
    check("owner_role is a declared closed vocabulary", bool(vocab),
          "field_vocabularies has %s" % ", ".join(sorted(m.get("field_vocabularies") or {})))
    check("and it is exactly the readiness roles",
          tuple(vocab or ()) == READINESS_ROLES, "declared %r" % (vocab,))

    tmp = tempfile.mkdtemp(prefix="rdown_")
    try:
        # --- (3) an owner_role that is not a role is refused -------------------------------
        hub = fresh(tmp, "vocab")
        rc, out = run(hub, "add", "readiness", "RD-X", "-f", "title=x",
                      "-f", "owner_role=BANANA", "--actor", "o1", "--role", "DEVOPS")
        check("owner_role=BANANA is REJECTED", rc != 0, "exit %d: %s" % (rc, out.strip()[:150]))
        check("the refusal names the real values",
              all(r in out for r in READINESS_ROLES), out.strip()[:180])
        # A role that exists but is not a readiness role is also wrong.
        rc, out = run(hub, "add", "readiness", "RD-Y", "-f", "title=x",
                      "-f", "owner_role=QA", "--actor", "o1", "--role", "DEVOPS")
        check("owner_role=QA is REJECTED -- QA owns cases, not readiness", rc != 0,
              "exit %d: %s" % (rc, out.strip()[:150]))

        # --- (1) only the owning role may MET ---------------------------------------------
        for owner in READINESS_ROLES:
            for actor_role in READINESS_ROLES:
                hub = fresh(tmp, "own-%s-%s" % (owner, actor_role))
                run(hub, "add", "readiness", "RD-1", "-f", "title=a gate",
                    "-f", "owner_role=%s" % owner, "--actor", "c1", "--role", "DEVOPS")
                rc, out = run(hub, "move", "RD-1", "MET",
                              "-f", "evidence=it happened, 2026-03-04",
                              "-f", "build=sha256:abc",
                              "--actor", "a1", "--role", actor_role)
                if actor_role == owner:
                    check("%s may meet its own %s checkpoint" % (actor_role, owner), rc == 0,
                          out.strip()[:140])
                else:
                    check("%s may NOT meet a %s checkpoint" % (actor_role, owner), rc != 0,
                          "exit %d: %s" % (rc, out.strip()[:140]))
                    check("  and the refusal names the owner %s" % owner,
                          rc != 0 and owner in out, out.strip()[:160])

        # --- (2) release-side roles may create, never meet --------------------------------
        for role in RELEASE_SIDE:
            hub = fresh(tmp, "rel-%s" % role)
            rc, out = run(hub, "add", "readiness", "RD-2", "-f", "title=rollback rehearsed",
                          "-f", "owner_role=DEVOPS", "--actor", "r1", "--role", role)
            check("%s may create a checkpoint" % role, rc == 0, out.strip()[:140])
            rc, out = run(hub, "move", "RD-2", "MET", "-f", "evidence=we can roll back", "-f", "build=sha256:abc",
                          "--actor", "r1", "--role", role)
            check("%s may NOT meet one -- it computes the verdict it would be feeding" % role,
                  rc != 0, "exit %d: %s" % (rc, out.strip()[:140]))

        # --- the operator still waives, and only the operator -----------------------------
        hub = fresh(tmp, "waive")
        run(hub, "add", "readiness", "RD-3", "-f", "title=alert fires",
            "-f", "owner_role=DEVOPS", "--actor", "o1", "--role", "DEVOPS")
        rc, _ = run(hub, "move", "RD-3", "WAIVED", "-f", "reason=no time", "-f", "build=sha256:abc",
                    "--actor", "o1", "--role", "DEVOPS")
        check("the owning role may not waive its own checkpoint", rc != 0)
        rc, out = run(hub, "move", "RD-3", "WAIVED",
                      "-f", "reason=shipping for the deadline; rollback stays manual",
                      "-f", "build=sha256:abc",
                      "--actor", "op", "--role", "OPERATOR")
        check("the operator may waive with a reason", rc == 0, out.strip()[:140])

        # --- a hand-written log must not do what the CLI refuses --------------------------
        hub = fresh(tmp, "replay")
        run(hub, "add", "readiness", "RD-4", "-f", "title=on-call named",
            "-f", "owner_role=SECURITY", "--actor", "o1", "--role", "DEVOPS")
        import glob
        logs = glob.glob(os.path.join(hub, "events", "SUPPORT", "*.jsonl"))
        d = os.path.join(hub, "events", "SUPPORT")
        os.makedirs(d, exist_ok=True)
        with io.open(os.path.join(d, "planted.jsonl"), "w", encoding="utf-8", newline="") as fh:
            fh.write(json.dumps({
                "v": 1, "event_id": "SUPPORT/planted#1", "seq": 1,
                "ts": "2026-11-05T23:00:00.000000Z", "actor": "planted", "role": "SUPPORT",
                "op": "move", "item": "RD-4", "to": "MET",
                "fields": {"evidence": "trust me"}}) + "\n")
        rc, out = run(hub, "validate")
        check("a planted cross-role MET is a problem on replay",
              rc != 0 and "RD-4" in out, "exit %d: %s" % (rc, out.strip()[:200]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILURES:
        print("%d failure(s)" % len(FAILURES))
        return 1
    print("  ok   a checkpoint is met by its owner, and the verdict's own roles cannot feed it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
