#!/usr/bin/env python3
"""Regressions for the defects that exercising skills/orient against a real product found.

    python -I tests/test_orient_exercise.py

Three defects, all found in the first twenty minutes of running the skill for real against
a live codebase rather than reading it:

  E-1  `status` on an empty hub ended its hint with "otherwise `hub.py init`", and that exact
       command is REJECTED for missing --actor/--role. The first thing a new engagement saw
       was advice that fails. Tested here by extracting every backticked command from the
       hint and RUNNING it -- asserting the text is not enough, since the old text also
       "contained a command".

  E-3  skills/orient Step 6 requires the orienting role to state what they could not
       establish, and warns that "every downstream skill reads the profile and will otherwise
       assume you looked". The profile accepted `not_established` and NOTHING read it. The
       safeguard against downstream silent assumption was prose with no consumer.

  E-2  is a skill-text fix (exclude build output when enumerating the capability inventory)
       and is checked by check_repo.py's own passes, not here.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HUB = os.path.join(ROOT, "shared", "scripts", "hub.py")

FAILURES = []


def run(*args, **kw):
    cmd = [sys.executable, "-I", "-B", HUB] + [str(a) for a in args]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=kw.get("cwd"))
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def check(label, cond, detail=""):
    if cond:
        print("  ok   %s" % label)
    else:
        print("  FAIL %s%s" % (label, (" -- " + detail) if detail else ""))
        FAILURES.append(label)


def test_empty_hub_hint_is_runnable(tmp):
    """E-1: every command the hint offers must actually run."""
    missing = os.path.join(tmp, "nohub")
    rc, out = run("--hub", missing, "status")
    check("status on a missing hub exits 0", rc == 0, out[:200])
    try:
        hint = json.loads(out)["next"]
    except Exception as exc:                                  # noqa: BLE001
        check("the hint is present and parseable", False, repr(exc))
        return

    cmds = re.findall(r"`([^`]+)`", hint)
    check("the hint offers at least one command", len(cmds) >= 1, hint)

    ran = 0
    for raw in cmds:
        if not raw.startswith("hub.py"):
            continue
        argv = raw.split()[1:]
        if any("<" in a for a in argv):      # a placeholder like <dir>; not runnable as printed
            continue
        argv = ["NAME" if a == "NAME" else a for a in argv]
        argv = [{"ROLE": "QA"}.get(a, a) for a in argv]
        target = os.path.join(tmp, "from_hint_%d" % ran)
        argv = [target if a == missing else a for a in argv]
        rc2, out2 = run(*argv)
        check("the hint's command runs: %s" % raw[:58],
              rc2 == 0 and "REJECTED" not in out2, out2[:160])
        ran += 1
    check("at least one offered command was executable as printed", ran >= 1)


def test_status_surfaces_unestablished(tmp):
    """E-3: what orient could not establish must reach the skills that read the hub."""
    hub = os.path.join(tmp, "hub")
    rc, out = run("--hub", hub, "init", "--actor", "a1", "--role", "HEAD_OF_PRODUCT")
    check("init succeeds", rc == 0, out[:160])

    rc, out = run("--hub", hub, "status")
    body = json.loads(out)
    check("status names a missing profile as the next step",
          "next" in body and "orient" in body["next"], out[:200])

    rc, out = run("--hub", hub, "profile", "--set", "mode=existing",
                  "--actor", "a1", "--role", "HEAD_OF_PRODUCT")
    check("profile can be set", rc == 0, out[:160])

    body = json.loads(run("--hub", hub, "status")[1])
    check("an EMPTY not_established is warned about, not passed over",
          "not_established_warning" in body,
          "an empty list reads as a complete orientation; a reader cannot tell the difference")

    gap = "deploy_branch: no deployment pipeline, only one CI workflow"
    rc, out = run("--hub", hub, "profile", "--set", "not_established=[\"%s\"]" % gap,
                  "--actor", "a1", "--role", "HEAD_OF_PRODUCT")
    check("not_established can be recorded", rc == 0, out[:160])

    body = json.loads(run("--hub", hub, "status")[1])
    check("status reports the recorded gap to every skill that reads it",
          body.get("not_established") == [gap], json.dumps(body.get("not_established")))
    check("the warning is withdrawn once a gap is recorded",
          "not_established_warning" not in body)
    check("status reports the profile mode", body.get("profile_mode") == "existing")


def main():
    tmp = tempfile.mkdtemp(prefix="orient_ex_")
    try:
        print("E-1  the empty-hub hint is a command you can paste")
        test_empty_hub_hint_is_runnable(tmp)
        print("\nE-3  what could not be established reaches downstream skills")
        test_status_surfaces_unestablished(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILURES:
        print("%d failure(s)" % len(FAILURES))
        return 1
    print("  ok   all orient-exercise regressions hold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
