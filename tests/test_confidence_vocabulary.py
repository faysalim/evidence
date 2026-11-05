#!/usr/bin/env python3
"""An insight's `confidence` is declared, required, and closed.

    python -I tests/test_confidence_vocabulary.py
    python -I tests/test_confidence_vocabulary.py -v

Why this exists. `skills/discovery` says of its insight contract: "`confidence` is the field that
does the most work, because the values are routinely blurred", and names the failure it prevents --
"a synthesis that presents inferred as observed is the research equivalent of a PASS with no
evidence".

Nothing declared the field and nothing required it. An `insight` reached `EVIDENCED` on `evidence`,
`sample_size` and `does_not_show` alone, then `ACCEPTED` by a second role, with **no confidence value
at all** -- so the failure the skill names was not merely unprevented, it was undetectable, because a
reader cannot distinguish "observed" from "nobody said".

This is the third field found declared-in-prose and enforced-nowhere, after `domains`
(`test_domain_vocabulary.py`) and `link_types` (`test_link_vocabulary.py`). The fix follows
`severity`, which has been a closed vocabulary checked on every write path all along.

`authored` is in the vocabulary because exercising `discovery` against 158 user-authored artifacts
showed the original three were written for interviews: a public, timestamped, unprompted forum post
is not `observed` -- you were not there -- and calling it `reported` understates it, since nobody
elicited it and a third party can re-read it.
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

EXPECTED = ("observed", "authored", "reported", "inferred")

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


def evidenced(hub, iid, *extra):
    argv = ["--hub", hub, "move", iid, "EVIDENCED",
            "-f", "evidence=r/dotnet thread, u/handle, 2025-04-20, <url>",
            "-f", "sample_size=26 of 158 collected items, 6 platforms, 17 queries",
            "-f", "does_not_show=prevalence among .NET developers generally; the frame is my queries"]
    return run(*(argv + list(extra)))


def main():
    model = json.loads(io.open(os.path.join(ROOT, "shared", "hub", "model.json"),
                               encoding="utf-8").read())
    # The vocabulary moved into  when the sweep put all four in one place.
    # Two declarations of one vocabulary is the defect this file is about, so there is only one.
    declared = tuple((model.get("field_vocabularies") or {}).get("confidence") or ())
    print("model declares confidence levels: %s" % (", ".join(declared) or "NONE"))
    check("the vocabulary is declared in the model", set(declared) == set(EXPECTED),
          "declared %r, expected %r" % (declared, EXPECTED))

    tmp = tempfile.mkdtemp(prefix="confvocab_")
    try:
        hub = os.path.join(tmp, "h")
        run("--hub", hub, "init", "--actor", "r1", "--role", "RESEARCHER")

        # EVIDENCED must require confidence.
        run("--hub", hub, "add", "insight", "I-1", "-f", "claim=latency is the raised pain",
            "--actor", "r1", "--role", "RESEARCHER")
        rc, out = evidenced(hub, "I-1", "--actor", "r1", "--role", "RESEARCHER")
        check("EVIDENCED without confidence is REJECTED", rc != 0,
              "exit %d: %s" % (rc, out.strip()[:170]))
        check("the refusal names confidence", "confidence" in out, out.strip()[:170])

        # Each declared value is accepted.
        for i, level in enumerate(EXPECTED, start=2):
            iid = "I-%d" % i
            run("--hub", hub, "add", "insight", iid, "-f", "claim=a claim",
                "--actor", "r1", "--role", "RESEARCHER")
            rc, out = evidenced(hub, iid, "-f", "confidence=%s" % level,
                                "--actor", "r1", "--role", "RESEARCHER")
            check("confidence=%s is accepted" % level, rc == 0, out.strip()[:170])

        # An undeclared value is refused, not stored. "high"/"medium"/"low" is the most likely
        # wrong answer, because every other tracker in the world uses it.
        run("--hub", hub, "add", "insight", "I-9", "-f", "claim=a claim",
            "--actor", "r1", "--role", "RESEARCHER")
        rc, out = evidenced(hub, "I-9", "-f", "confidence=high",
                            "--actor", "r1", "--role", "RESEARCHER")
        check("an undeclared confidence value is REJECTED", rc != 0,
              "exit %d: %s" % (rc, out.strip()[:170]))
        check("the refusal lists the real vocabulary",
              all(v in out for v in EXPECTED), out.strip()[:200])

        # Case and padding are the same value, as with severity.
        run("--hub", hub, "add", "insight", "I-10", "-f", "claim=a claim",
            "--actor", "r1", "--role", "RESEARCHER")
        rc, out = evidenced(hub, "I-10", "-f", "confidence= Authored ",
                            "--actor", "r1", "--role", "RESEARCHER")
        check("the value is case- and space-insensitive, like severity", rc == 0,
              out.strip()[:170])

        # A hand-written log line must not do what the CLI refuses.
        logs = os.path.join(hub, "events", "RESEARCHER")
        log = os.path.join(logs, sorted(os.listdir(logs))[0])
        with io.open(log, "a", encoding="utf-8", newline="") as fh:
            fh.write(json.dumps({
                "v": 1, "event_id": "RESEARCHER/r1#9000", "seq": 9000,
                "ts": "2026-11-05T23:59:59.000000Z", "actor": "r1", "role": "RESEARCHER",
                "op": "add", "type": "insight", "item": "I-99", "owner": "RESEARCHER",
                "provenance": None, "state": "DRAFT",
                "fields": {"claim": "planted", "confidence": "vibes"}}) + "\n")
        rc, out = run("--hub", hub, "validate")
        check("a planted undeclared value is a problem on replay",
              rc != 0 and "vibes" in out, "exit %d: %s" % (rc, out.strip()[:200]))

        # The skill's documented vocabulary must match the model's, or the doc lies.
        text = io.open(os.path.join(ROOT, "skills", "discovery", "SKILL.md"),
                       encoding="utf-8").read()
        documented = set(re.findall(r"^- \*\*(observed|authored|reported|inferred)\*\*",
                                    text, re.M))
        check("discovery documents exactly the declared vocabulary",
              documented == set(EXPECTED),
              "documents %r, model declares %r" % (sorted(documented), sorted(declared)))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILURES:
        print("%d failure(s)" % len(FAILURES))
        return 1
    print("  ok   confidence is declared, required and closed on every write path")
    return 0


if __name__ == "__main__":
    sys.exit(main())
