#!/usr/bin/env python3
"""One checkpoint does not satisfy a release. The required set does.

    python -I tests/test_required_checkpoints.py
    python -I tests/test_required_checkpoints.py -v

Why this exists. With ownership and build-scoping enforced, a release could still go green on a
**single** readiness row: one rehearsed rollback and the gate was satisfied, with nothing said about
alerting, on-call, privacy or support. The gate counted rows instead of covering checkpoints.

So there is a required set. `shared/hub/model.json: default_checkpoints` holds this suite's own,
keyed by owning role; `skills/orient` imports the team's set into the profile as
`required_checkpoints`, which **overrides it entirely** -- adopt, never impose. Each `readiness` row
names the key it satisfies in `checkpoint`, and the condition fails naming every required key with
no `MET` or `WAIVED` row on this release's build.

The two halves that matter and are easy to get wrong:

  - A team's own set must *replace* the defaults, not add to them. A team that gates on three
    things should not be told it is missing twenty-eight.
  - A key with a WAIVED row is covered. The operator deciding to ship without a rehearsed rollback
    is a decision, and the gate's job is to make it visible, not to forbid it.
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
sys.path.insert(0, os.path.join(ROOT, "shared", "scripts"))
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


def readiness_row(hub):
    import hub as H           # noqa: N813
    import dashboard as D
    _l, _f, conds = D.verdict(H.Hub(hub))
    for n, ok, d in conds:
        if "readiness" in n.lower():
            return ok, d
    return None, "no readiness condition"


def setup(tmp, name, required=None):
    hub = os.path.join(tmp, name)
    run(hub, "init", "--actor", "h1", "--role", "HEAD_OF_PRODUCT")
    if required is not None:
        run(hub, "profile", "--set", "required_checkpoints=%s" % json.dumps(required),
            "--actor", "h1", "--role", "HEAD_OF_PRODUCT")
    run(hub, "add", "release", "REL-1", "-f", "title=2.5.1", "--actor", "d1", "--role", "DELIVERY")
    run(hub, "move", "REL-1", "CANDIDATE", "-f", "build=sha256:abc",
        "--actor", "v1", "--role", "DEV")
    return hub


def meet(hub, cid, key, owner="DEVOPS", state="MET"):
    run(hub, "add", "readiness", cid, "-f", "title=%s" % key, "-f", "owner_role=%s" % owner,
        "-f", "checkpoint=%s" % key, "--actor", "c1", "--role", "DELIVERY")
    run(hub, "link", cid, "gates", "REL-1", "--actor", "c1", "--role", "DELIVERY")
    if state == "MET":
        return run(hub, "move", cid, "MET", "-f", "evidence=done, 2026-03-04",
                   "-f", "build=sha256:abc", "--actor", "a1", "--role", owner)
    return run(hub, "move", cid, "WAIVED", "-f", "reason=operator call",
               "-f", "build=sha256:abc", "--actor", "op", "--role", "OPERATOR")


def main():
    m = json.loads(io.open(os.path.join(ROOT, "shared", "hub", "model.json"),
                           encoding="utf-8").read())
    defaults = m.get("default_checkpoints") or {}
    check("the model ships a default checkpoint set", bool(defaults))
    for role in ("DEVOPS", "SECURITY", "SUPPORT"):
        check("defaults cover %s" % role, bool(defaults.get(role)),
              "roles present: %s" % ", ".join(sorted(k for k in defaults if k != "doc")))
    # item 5's additions, asserted by key so they cannot quietly disappear
    for key, role in (("canary-staged-rollout", "DEVOPS"), ("kill-switch", "DEVOPS"),
                      ("status-page", "DEVOPS"), ("dns-email-auth", "DEVOPS"),
                      ("consent-and-telemetry-observed", "SECURITY"),
                      ("support-trained", "SUPPORT"), ("sales-cs-briefed", "SUPPORT")):
        check("default %r is present under %s" % (key, role),
              key in (defaults.get(role) or {}),
              "keys: %s" % ", ".join(sorted(defaults.get(role) or {})))

    tmp = tempfile.mkdtemp(prefix="reqchk_")
    try:
        # --- one row no longer satisfies a release -----------------------------------------
        hub = setup(tmp, "one", required=["rollback-rehearsed", "alert-fired", "watch-plan"])
        meet(hub, "RD-1", "rollback-rehearsed")
        ok, detail = readiness_row(hub)
        check("one met checkpoint of three does not satisfy the gate", not ok, detail[:200])
        check("  and the missing keys are named",
              "alert-fired" in detail and "watch-plan" in detail, detail[:220])
        meet(hub, "RD-2", "alert-fired")
        meet(hub, "RD-3", "watch-plan", owner="SUPPORT")
        ok, detail = readiness_row(hub)
        check("with all three, the gate holds", ok, detail[:200])

        # --- a WAIVED key is covered -------------------------------------------------------
        hub = setup(tmp, "waived", required=["rollback-rehearsed", "alert-fired"])
        meet(hub, "RD-1", "rollback-rehearsed")
        meet(hub, "RD-2", "alert-fired", state="WAIVED")
        ok, detail = readiness_row(hub)
        check("a waived required key is covered -- the operator's call is visible, not forbidden",
              ok, detail[:200])
        check("  and the waiver is named in the detail", "RD-2" in detail, detail[:200])

        # --- the team's set REPLACES the defaults ------------------------------------------
        hub = setup(tmp, "theirs", required=["our-only-gate"])
        meet(hub, "RD-1", "our-only-gate")
        ok, detail = readiness_row(hub)
        check("a team's own set replaces the defaults rather than adding to them", ok,
              detail[:240])
        ndef = sum(len(v) for k, v in defaults.items() if k != "doc")
        check("  so a 1-checkpoint team is not told it is missing %d" % (ndef - 1),
              "missing" not in detail.lower(), detail[:200])

        # --- no profile set: the defaults apply, and the gate says so ---------------------
        hub = setup(tmp, "defaults")
        meet(hub, "RD-1", "rollback-rehearsed")
        ok, detail = readiness_row(hub)
        check("with no team set, the defaults are required", not ok, detail[:200])
        check("  and the detail says the set is this suite's default, not theirs",
              "default" in detail.lower(), detail[:220])

        # --- a row naming no checkpoint still has to be MET, and is named ------------------
        hub = setup(tmp, "nokey", required=["rollback-rehearsed"])
        meet(hub, "RD-1", "rollback-rehearsed")
        run(hub, "add", "readiness", "RD-X", "-f", "title=an extra gate",
            "-f", "owner_role=DEVOPS", "--actor", "c1", "--role", "DELIVERY")
        run(hub, "link", "RD-X", "gates", "REL-1", "--actor", "c1", "--role", "DELIVERY")
        ok, detail = readiness_row(hub)
        check("an extra OPEN row still denies, even though it is not in the required set",
              not ok, detail[:200])
        check("  and it is named", "RD-X" in detail, detail[:200])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILURES:
        print("%d failure(s)" % len(FAILURES))
        return 1
    print("  ok   a release is gated on a covered checkpoint set, theirs by preference")
    return 0


if __name__ == "__main__":
    sys.exit(main())
