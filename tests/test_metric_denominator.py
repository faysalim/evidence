#!/usr/bin/env python3
"""A metric cannot exist without a denominator.

    python -I tests/test_metric_denominator.py
    python -I tests/test_metric_denominator.py -v

Why this exists. `skills/prd` says of the items it produces:

    `metric` | One per success criterion, each `DEFINED` with its denominator before anything
              is built

and, in section 4, "Create each as a `metric` item now, so /evidence:analytics inherits a
definition rather than inventing one after launch."

Exercising `prd` against a real product, `add metric M-1 -f name=activation` was accepted into
`DEFINED` with no denominator at all. The claim was false in the one place it is load-bearing:
`skills/analytics` opens by reading "metrics against the denominator and baseline the PRD stated",
so a bare `DEFINED` metric hands it exactly the nothing it is written to avoid inventing.

The denominator is definitional, not measured -- "% of signups completing first success within
7 days, over signups in the period excluding internal accounts" is sayable before any data exists.
That is why it is required here while `baseline` is not: prd's own example records the baseline as
"unknown -- measuring is in scope", and the move to BASELINED already demands a real one.

The precedent is exact: `case` requires `action` and `oracle` at creation, and the model's own note
on that type reads "principles.md claimed this was enforced before it was". Same defect, same fix.
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


def fresh(tmp, name):
    hub = os.path.join(tmp, name)
    run("--hub", hub, "init", "--actor", "p1", "--role", "PM")
    return hub


def main():
    tmp = tempfile.mkdtemp(prefix="metricdenom_")
    try:
        hub = fresh(tmp, "m")

        rc, out = run("--hub", hub, "add", "metric", "M-1", "-f", "name=activation",
                      "--actor", "p1", "--role", "PM")
        check("a metric with no denominator is REJECTED", rc != 0,
              "exit %d: %s" % (rc, out.strip()[:170]))
        check("the refusal names the field", "denominator" in out, out.strip()[:170])

        rc, out = run("--hub", hub, "add", "metric", "M-2", "-f", "denominator=signups",
                      "--actor", "p1", "--role", "PM")
        check("a metric with no name is REJECTED too", rc != 0,
              "exit %d: %s" % (rc, out.strip()[:170]))

        # A blank denominator is the obvious way round a required field, and it is the same gap.
        rc, out = run("--hub", hub, "add", "metric", "M-3", "-f", "name=activation",
                      "-f", "denominator=", "--actor", "p1", "--role", "PM")
        check("an empty denominator is not a denominator", rc != 0,
              "exit %d: %s" % (rc, out.strip()[:170]))

        # Both present: accepted, and the baseline is NOT required here -- prd's own example
        # records it as unknown with the measuring in scope.
        rc, out = run("--hub", hub, "add", "metric", "M-4", "-f", "name=trial-to-paid",
                      "-f", "denominator=trials started, excluding internal",
                      "-f", "baseline=unknown -- measuring is in scope",
                      "--actor", "p1", "--role", "PM")
        check("name + denominator is accepted", rc == 0, out.strip()[:170])
        check("and an unknown baseline does not block creation",
              rc == 0 and "DEFINED" in out, out.strip()[:170])

        # The move to BASELINED still demands a measured baseline. Unchanged, asserted so that
        # tightening creation cannot quietly loosen the later gate.
        rc, out = run("--hub", hub, "move", "M-4", "BASELINED", "--actor", "a2",
                      "--role", "ANALYST")
        check("BASELINED still requires the values on the move", rc != 0,
              "exit %d: %s" % (rc, out.strip()[:170]))

        # prd's own documented example must satisfy the rule it documents. If this fails, the
        # skill is now telling readers to run a command the tool refuses.
        text = io.open(os.path.join(ROOT, "skills", "prd", "SKILL.md"), encoding="utf-8").read()
        examples = re.findall(r"^hub\.py add metric .*(?:\\\n.*)*$", text, re.M)
        check("prd documents at least one metric creation", bool(examples),
              "found none to check")
        for ex in examples:
            flat = ex.replace("\\\n", " ")
            check("prd's own example passes the required fields",
                  "-f name=" in flat and "-f denominator=" in flat, flat[:170])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILURES:
        print("%d failure(s)" % len(FAILURES))
        return 1
    print("  ok   a metric carries its denominator from the moment it exists")
    return 0


if __name__ == "__main__":
    sys.exit(main())
