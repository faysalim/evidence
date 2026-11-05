#!/usr/bin/env python3
"""A link type the model does not declare must be refused, not stored.

    python -I tests/test_link_vocabulary.py
    python -I tests/test_link_vocabulary.py -v

Why this exists. `shared/hub/model.json` declares `link_types` -- thirteen of them -- and nothing
checked a link against that list at write time. `hub.py link A blocked_by B` printed
`A --blocked_by--> B` and exited 0. `validate` then mentioned it as a **note**, which does not fail,
so a run could carry invented link types indefinitely.

Found by introducing one. Exercising `architecture` against a real product, this went into the skill
as the prescribed way to record a decision's unfinished half:

    hub.py link <the adr> blocked_by <the risk carrying the unfinished half>

`blocked_by` is not a link type. The real one is `blocks`, in the other direction. So the skill was
telling readers to run a command that succeeds and records something the hub does not understand --
worse than one that fails, because nothing tells them.

The vocabulary is closed and declared, exactly like `domains`, and it is enforced the same way: at
write time, naming the near misses. `validate` keeps its note so that a hand-written log carrying an
old bad link still reports rather than crashing.
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


def main():
    model = json.loads(io.open(os.path.join(ROOT, "shared", "hub", "model.json"),
                               encoding="utf-8").read())
    declared = model["link_types"]
    print("%d link type(s) declared: %s" % (len(declared), ", ".join(sorted(declared))))

    tmp = tempfile.mkdtemp(prefix="linkvocab_")
    try:
        hub = os.path.join(tmp, "h")
        run("--hub", hub, "init", "--actor", "t1", "--role", "TECH_LEAD")
        run("--hub", hub, "add", "adr", "ADR-1", "-f", "title=a decision",
            "--actor", "t1", "--role", "TECH_LEAD")
        run("--hub", hub, "add", "risk", "RISK-1", "-f", "title=a risk", "-f", "severity=major",
            "--actor", "t1", "--role", "TECH_LEAD")

        rc, out = run("--hub", hub, "link", "ADR-1", "blocked_by", "RISK-1",
                      "--actor", "t1", "--role", "TECH_LEAD")
        check("an undeclared link type is REJECTED", rc != 0,
              "exit %d: %s" % (rc, out.strip()[:170]))
        check("the refusal names the bad type", "blocked_by" in out, out.strip()[:200])
        check("and suggests the real one", "blocks" in out, out.strip()[:200])

        rc, out = run("--hub", hub, "validate")
        check("nothing was stored, so validate is clean",
              "blocked_by" not in out, out.strip()[:200])

        # The declared direction works.
        rc, out = run("--hub", hub, "link", "RISK-1", "blocks", "ADR-1",
                      "--actor", "t1", "--role", "TECH_LEAD")
        check("a declared link type is accepted", rc == 0, out.strip()[:170])

        # Every declared type must be spellable -- otherwise this check would pass by refusing
        # everything, which is the failure mode a closed vocabulary invites.
        for lt in declared:
            rc, out = run("--hub", hub, "link", "ADR-1", lt, "RISK-1",
                          "--actor", "t1", "--role", "TECH_LEAD")
            if rc != 0 and "not a link type" in out:
                check("declared type %r is accepted by the checker" % lt, False,
                      out.strip()[:140])

        # Every link type used in a skill's documented commands must be declared. This is what
        # would have caught `blocked_by` in review rather than in a hub three steps later.
        # `<angle bracket>` placeholders contain spaces, so a naive \S+ for the subject silently
        # skips exactly the lines most likely to be wrong -- the generic templates. Collapse them
        # to one token first. The first version of this check passed while the defect that
        # prompted it, `link <the adr> blocked_by <the risk ...>`, sat two files away.
        def normalise(s):
            return re.sub(r"<[^>]*>", "PLACEHOLDER", s)

        bad = []
        for name in sorted(os.listdir(os.path.join(ROOT, "skills"))):
            path = os.path.join(ROOT, "skills", name, "SKILL.md")
            if not os.path.isfile(path):
                continue
            text = normalise(io.open(path, encoding="utf-8").read())
            for m in re.finditer(r"hub\.py\s+link\s+\S+\s+([a-z_]+)\b", text):
                if m.group(1) not in declared:
                    bad.append((name, m.group(1)))
        check("every link type documented in a skill is declared in the model", not bad,
              "; ".join("%s uses %r" % (n, t) for n, t in bad))

        # Same for the reference files, which readers paste from just as readily.
        bad2 = []
        for root, _dirs, files in os.walk(os.path.join(ROOT, "shared")):
            for f in files:
                if not f.endswith(".md"):
                    continue
                text = normalise(io.open(os.path.join(root, f), encoding="utf-8").read())
                for m in re.finditer(r"hub\.py\s+link\s+\S+\s+([a-z_]+)\b", text):
                    if m.group(1) not in declared:
                        bad2.append((f, m.group(1)))
        check("and every one documented under shared/", not bad2,
              "; ".join("%s uses %r" % (n, t) for n, t in bad2))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILURES:
        print("%d failure(s)" % len(FAILURES))
        return 1
    print("  ok   the link vocabulary is closed, and every documented link type is in it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
