#!/usr/bin/env python3
"""Every field a skill's `hub.py status` comment claims must appear in status's output.

    python -I tests/test_status_contract.py
    python -I tests/test_status_contract.py -v

Why this exists. Eleven skills open with the same block:

    hub.py status          # mode, the product class, and what orient could not establish

That comment is a promise about a command's output, made in the one place every downstream skill
reads first. Exercising `architecture` and `prd` against a real product showed the middle claim
was false: `status` printed `profile_mode` and `not_established` and no product class at all, so
a skill that trusted the comment either guessed the class or made a second call nobody documented.

The block was added to thirteen skills as the fix for E-6 -- which makes an inaccurate claim inside
it worse than one anywhere else, because E-6 was precisely "a promise about what downstream reads".

What is checked: the claim phrases in the comment are mapped to the JSON keys status must emit,
and status is RUN over a hub whose profile sets all of them. A claimed key that is absent fails.
The reverse is not required: status may print more than it advertises.
"""

from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HUB = os.path.join(ROOT, "shared", "scripts", "hub.py")
VERBOSE = "-v" in sys.argv

# A claim in the comment -> the JSON key that claim is about. Keep this table small and literal:
# it is the mapping a reader of the comment would make, and the test is only meaningful if it is
# the obvious one.
CLAIMS = (
    ("mode", "profile_mode"),
    ("the product class", "domains"),
    ("what orient could not establish", "not_established"),
)

FAILURES = []


def run(*args):
    p = subprocess.run([sys.executable, "-I", "-B", HUB] + [str(a) for a in args],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def check(label, cond, detail=""):
    if cond:
        if VERBOSE:
            print("  ok   %s" % label)
    else:
        print("  FAIL %s%s" % (label, (" -- " + detail) if detail else ""))
        FAILURES.append(label)


def seeded_hub(tmp):
    """A hub whose profile sets every field the comment claims, so an absent key is the tool's."""
    hub = os.path.join(tmp, "contract")
    run("--hub", hub, "init", "--engagement", "contract probe", "--actor", "h1",
        "--role", "HEAD_OF_PRODUCT")
    run("--hub", hub, "profile",
        "--set", "mode=existing",
        "--set", 'domains=["distributed-database"]',
        "--set", 'not_established=["a gap, recorded"]',
        "--actor", "h1", "--role", "HEAD_OF_PRODUCT")
    return hub


def status_json(hub):
    rc, out = run("--hub", hub, "status")
    if rc != 0:
        return None, out
    try:
        return json.loads(out), out
    except ValueError as exc:
        return None, "%s: %s" % (exc, out[:200])


def main():
    tmp = tempfile.mkdtemp(prefix="statusc_")
    try:
        hub = seeded_hub(tmp)
        body, raw = status_json(hub)
        if body is None:
            print("  FAIL status did not return JSON -- %s" % raw[:300])
            return 1

        # Which skills make the claim, and in what words?
        claimed_by = {}
        skills_dir = os.path.join(ROOT, "skills")
        for name in sorted(os.listdir(skills_dir)):
            path = os.path.join(skills_dir, name, "SKILL.md")
            if not os.path.isfile(path):
                continue
            text = io.open(path, encoding="utf-8").read()
            for m in re.finditer(r"^\s*(?:python\s+)?.*hub\.py\s+status\b[^\n#]*#\s*(.+)$",
                                 text, re.M):
                claimed_by.setdefault(m.group(1).strip(), []).append(name)

        if not claimed_by:
            print("  FAIL no skill documents `hub.py status` with a comment -- "
                  "this test has lost its subject")
            return 1

        print("%d distinct status comment(s) across %d skill reference(s)"
              % (len(claimed_by), sum(len(v) for v in claimed_by.values())))

        for comment, skills in sorted(claimed_by.items()):
            for phrase, key in CLAIMS:
                if phrase not in comment:
                    continue
                check("%s -> status emits %r" % (phrase, key), key in body,
                      "claimed by %d skill(s) (%s); status emitted %s"
                      % (len(skills), ", ".join(skills[:3]),
                         ", ".join(sorted(body)) or "nothing"))

        # The claimed keys must carry the value the profile set, not merely exist as null -- a key
        # printed as null is indistinguishable to a reader from a field nobody filled in.
        if "domains" in body:
            check("the product class carries the profile's value",
                  body.get("domains") == ["distributed-database"],
                  "got %r" % (body.get("domains"),))
        check("mode carries the profile's value", body.get("profile_mode") == "existing",
              "got %r" % (body.get("profile_mode"),))
        check("the gap list carries the profile's value",
              body.get("not_established") == ["a gap, recorded"],
              "got %r" % (body.get("not_established"),))

        # A hub with a profile that set no domains must not claim a class it does not have.
        bare = os.path.join(tmp, "bare")
        run("--hub", bare, "init", "--actor", "h1", "--role", "HEAD_OF_PRODUCT")
        run("--hub", bare, "profile", "--set", "mode=existing",
            "--actor", "h1", "--role", "HEAD_OF_PRODUCT")
        body2, raw2 = status_json(bare)
        if body2 is None:
            check("status over a profile with no domains returns JSON", False, raw2[:200])
        else:
            check("no domains set -> the field is empty, never invented",
                  not body2.get("domains"), "got %r" % (body2.get("domains"),))
            # An empty class is not a neutral default. Eleven skills say their behaviour depends
            # on it, and orient Step 2 requires choosing one; silence here reads to each of them
            # as "no class applies", which is the guess the block exists to prevent.
            warn = " ".join(str(v) for k, v in body2.items() if "warn" in k or k == "next")
            check("no domains set -> status says so rather than passing it over",
                  "class" in warn.lower() or "domain" in warn.lower(),
                  "status emitted no warning naming the product class: %r" % (warn[:160],))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILURES:
        print("%d failure(s) -- a skill's comment promises output the command does not produce"
              % len(FAILURES))
        return 1
    print("  ok   every field the status comment claims is a field status prints")
    return 0


if __name__ == "__main__":
    sys.exit(main())
