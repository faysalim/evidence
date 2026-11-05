#!/usr/bin/env python3
"""A baseline needs its evidence at least as much as a reading does.

    python -I tests/test_baseline_evidence.py
    python -I tests/test_baseline_evidence.py -v

Why this exists. `skills/analytics` tells you to "**Compare to the stated baseline**, not to last
week and not to a recollection". The hub enforced the opposite asymmetry:

    DEFINED -> BASELINED   requires denominator, baseline            (no evidence)
    BASELINED -> READ      requires value, denominator, evidence

So a *reading* had to be sourced and the *baseline* did not -- and the baseline is the comparison
point for every reading that ever follows it. An unsourced baseline silently poisons all of them,
and `analytics` cannot tell one from a recollection because nothing recorded where it came from.

Found by being its victim. Exercising `prd` against a real product, this baseline was written:

    baseline = "49 of 512 at checkpoint 49"

The 512 was inferred, not read. The product states its own denominator in
`replica-validation.json`: *"Bounded to latest 128 keys per validation pass."* The real reading is
49 of **128** -- 38%, not 9.6%. A factor of four, from a number nothing required me to source.

`metric` already requires fields on a transition, and `READ` already requires `evidence`. This is
that same rule moved to the transition that needed it first.
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
    tmp = tempfile.mkdtemp(prefix="baseev_")
    try:
        hub = os.path.join(tmp, "h")
        run("--hub", hub, "init", "--actor", "p1", "--role", "PM")
        run("--hub", hub, "add", "metric", "M-1", "-f", "name=replica read failures",
            "-f", "denominator=keys checked per validation pass",
            "--actor", "p1", "--role", "PM")

        rc, out = run("--hub", hub, "move", "M-1", "BASELINED",
                      "-f", "denominator=keys checked per validation pass",
                      "-f", "baseline=49 of 512", "--actor", "an1", "--role", "ANALYST")
        check("a baseline with no evidence is REJECTED", rc != 0,
              "exit %d: %s" % (rc, out.strip()[:170]))
        check("the refusal names evidence", "evidence" in out, out.strip()[:170])

        rc, out = run("--hub", hub, "move", "M-1", "BASELINED",
                      "-f", "denominator=keys checked per validation pass",
                      "-f", "baseline=49 of 128",
                      "-f", "evidence=replica-validation.json ValidationMode: bounded to latest "
                            "128 keys per validation pass",
                      "--actor", "an1", "--role", "ANALYST")
        check("a baseline with evidence is accepted", rc == 0, out.strip()[:170])

        # An empty evidence string is the obvious way round a required field.
        hub2 = os.path.join(tmp, "h2")
        run("--hub", hub2, "init", "--actor", "p1", "--role", "PM")
        run("--hub", hub2, "add", "metric", "M-2", "-f", "name=x", "-f", "denominator=y",
            "--actor", "p1", "--role", "PM")
        rc, out = run("--hub", hub2, "move", "M-2", "BASELINED", "-f", "denominator=y",
                      "-f", "baseline=0", "-f", "evidence=",
                      "--actor", "an1", "--role", "ANALYST")
        check("blank evidence is not evidence", rc != 0, "exit %d: %s" % (rc, out.strip()[:170]))

        # A baseline of 0 is a real reading and must still be accepted -- falsy, not absent.
        rc, out = run("--hub", hub2, "move", "M-2", "BASELINED", "-f", "denominator=y",
                      "-f", "baseline=0", "-f", "evidence=counted the rows, there were none",
                      "--actor", "an1", "--role", "ANALYST")
        check("a baseline of 0 with evidence is still a baseline", rc == 0, out.strip()[:170])

        # READ still requires its own evidence, supplied on the move. Asserted so that adding the
        # earlier gate cannot be mistaken for satisfying the later one by inheritance.
        rc, out = run("--hub", hub2, "move", "M-2", "READ", "-f", "value=3",
                      "-f", "denominator=y", "--actor", "an1", "--role", "ANALYST")
        check("READ still demands evidence of its own", rc != 0,
              "exit %d: %s" % (rc, out.strip()[:170]))

        # analytics documents the contract; its own example must satisfy the rule it documents.
        text = io.open(os.path.join(ROOT, "skills", "analytics", "SKILL.md"),
                       encoding="utf-8").read()
        check("analytics states that a baseline carries its source",
              re.search(r"baseline.*(evidence|measured|source|where)", text, re.I) is not None,
              "the skill does not say a baseline must be sourced")

        model = json.loads(io.open(os.path.join(ROOT, "shared", "hub", "model.json"),
                                   encoding="utf-8").read())
        tr = [t for t in model["types"]["metric"]["transitions"] if t["to"] == "BASELINED"]
        check("the model records the requirement, not just the CLI",
              tr and "evidence" in (tr[0].get("requires_fields") or []),
              "BASELINED requires %s" % (tr[0].get("requires_fields") if tr else "no transition",))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILURES:
        print("%d failure(s)" % len(FAILURES))
        return 1
    print("  ok   a baseline is sourced before anything is compared against it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
