#!/usr/bin/env python3
"""Every "Enforced:" claim in shared/principles.md must be true.

    python -I tests/test_enforcement_claims.py

This test exists because of the council. Three of the ten principles said *"Enforced: X"* where X
did not enforce it -- the oracle requirement, the computed verdict, and the dashboard's derivation
counts -- and `check_repo.py` could not see any of it, because it validates paths rather than
promises. The method's own first rule is that an unverified claim poisons the report; the restructure
shipped three unverified claims about its own enforcement, in the commit that said it had made the
method enforceable.

So each claim gets a probe that *attempts the forbidden thing* and asserts a refusal. A principle
whose probe cannot be written is a principle that is not enforced, and it should say so instead.

The probes run against a scratch hub through the CLI, exactly as a skill would.
"""

from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HUB_PY = os.path.join(ROOT, "shared", "scripts", "hub.py")
PRINCIPLES = os.path.join(ROOT, "shared", "principles.md")

FAILURES = []
HUB = None


def check(label, condition, detail=""):
    if condition:
        print("  ok   %s" % label)
    else:
        print("  FAIL %s %s" % (label, detail))
        FAILURES.append(label)


def run(*args, **kw):
    actor = kw.pop("actor", "qa1")
    role = kw.pop("role", "QA")
    cmd = [sys.executable, "-I", "-B", HUB_PY, "--hub", HUB, "--actor", actor, "--role", role]
    cmd += [str(a) for a in args]
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def refused(label, *args, **kw):
    needle = kw.pop("needle", None)
    code, text = run(*args, **kw)
    ok = code != 0 and "REJECTED" in text
    if ok and needle:
        ok = needle.lower() in text.lower()
    check(label, ok, "code=%r out=%r" % (code, text.strip()[:150]))


def allowed(label, *args, **kw):
    code, text = run(*args, **kw)
    check(label, code == 0, "code=%r out=%r" % (code, text.strip()[:150]))


def main():
    global HUB
    tmp = tempfile.mkdtemp(prefix="enforce-")
    HUB = os.path.join(tmp, "hub")
    try:
        text = io.open(PRINCIPLES, encoding="utf-8").read()
        claims = re.findall(r"\*Enforced:\*", text)
        print("shared/principles.md makes %d enforcement claim(s)" % len(claims))
        check("every claim below has a probe", len(claims) == 7,
              "found %d; add a probe for any new one, or it is unverified" % len(claims))

        allowed("setup", "init", "--engagement", "enforce")

        print("\nprinciple 2 -- every number has a denominator")
        # The gate used to start at BASELINED, so `add metric -f name=activation` was accepted
        # into DEFINED with no denominator at all -- which is what skills/analytics then reads.
        # Exercising `prd` found it; the denominator is now required from the moment the metric
        # exists, and this probe asserts the earlier gate rather than the weaker one.
        refused("a metric cannot be defined without a denominator",
                "add", "metric", "M-0", "-f", "name=activation",
                actor="an1", role="ANALYST", needle="denominator")
        allowed("a metric can be defined with one", "add", "metric", "M-1",
                "-f", "name=activation", "-f", "denominator=signups, excluding internal",
                actor="an1", role="ANALYST")
        refused("a metric cannot be BASELINED without a denominator",
                "move", "M-1", "BASELINED", "-f", "baseline=7.9%",
                actor="an1", role="ANALYST", needle="denominator")

        print("\nprinciple 3 -- an oracle exists outside the product and your own judgement")
        refused("a case cannot be created without an oracle",
                "add", "case", "S1-01", "-f", "action=post the form", needle="oracle")
        allowed("with one it can", "add", "case", "S1-01", "-f", "action=post",
                "-f", "oracle=a key arrives in a real mailbox")
        refused("a PASS needs evidence", "move", "S1-01", "PASS", needle="evidence")

        print("\nprinciple 4 -- every claim states what it does NOT claim")
        allowed("an insight can be drafted", "add", "insight", "I-1", "-f", "claim=x",
                actor="r1", role="RESEARCHER")
        refused("an insight cannot be EVIDENCED without does_not_show",
                "move", "I-1", "EVIDENCED", "-f", "evidence=6 of 9", "-f", "sample_size=9",
                actor="r1", role="RESEARCHER", needle="does_not_show")

        print("\nprinciple 6 -- verdicts are computed, never written; NO VERDICT is the default")
        allowed("a release can be planned", "add", "release", "REL-1", "-f", "title=1.0",
                actor="dm1", role="DELIVERY")
        allowed("and reach candidate", "move", "REL-1", "CANDIDATE", "-f", "build=sha256:abc",
                actor="dev1", role="DEV")
        refused("GREEN cannot be written while the computed verdict disagrees",
                "move", "REL-1", "GREEN", "-f", "bounds=1 node", "-f", "does_not_cover=none",
                needle="computed verdict")
        allowed("NO_VERDICT can be recorded", "move", "REL-1", "NO_VERDICT",
                "-f", "reason=acceptance requirements have no rows")
        refused("only the operator may ship against a non-green verdict",
                "move", "REL-1", "SHIPPED", "-f", "reason=business call",
                actor="dev1", role="DEV", needle="belongs to OPERATOR")
        refused("and only with a reason supplied on that move",
                "move", "REL-1", "SHIPPED", actor="faisal", role="OPERATOR",
                needle="requires")

        print("\nprinciple 7 -- the producer claims; a different role accepts")
        allowed("file a finding", "add", "finding", "F-1", "-f", "title=acked writes lost",
                "-f", "severity=critical")
        allowed("DEV accepts it", "move", "F-1", "ACCEPTED", actor="dev1", role="DEV")
        allowed("DEV claims FIXED", "move", "F-1", "FIXED", "-f", "commit=abc",
                "-f", "build=sha256:abc", actor="dev1", role="DEV")
        refused("DEV may not CLOSE", "move", "F-1", "CLOSED", actor="dev1", role="DEV",
                needle="cannot move to CLOSED")
        refused("the author may not verify their own fix, even wearing the QA hat",
                "move", "F-1", "VERIFIED", "-f", "evidence=x", "-f", "variant_used=y",
                actor="dev1", role="QA", needle="does not grade their own work")
        refused("DEV may not re-grade severity, on any write path",
                "move", "F-1", "NOT_IN_BUILD", "-f", "evidence=x", "-f", "severity=polish",
                actor="dev1", role="DEV", needle="belongs to")
        refused("QA may not set priority", "set", "F-1", "-f", "priority=P3",
                needle="belongs to OPERATOR")

        print("\nprinciple 9 -- the cleanup ledger, verified by re-listing")
        allowed("open a cleanup item", "add", "cleanup", "C-1", "-f", "title=3-node cluster")
        refused("it cannot be torn down without a verified_by",
                "move", "C-1", "TORN_DOWN", needle="verified_by")

        print("\nprinciple 8 -- never put a secret in an artifact")
        code, out = subprocess.run(
            [sys.executable, "-I", "-B",
             os.path.join(ROOT, "shared", "scripts", "check_repo.py"), "examples"],
            capture_output=True, text=True).returncode, ""
        check("check_repo.py examples runs and passes", code == 0, "rc=%r" % code)

        print("\nthe guards that are not principles but are claimed in the skills")
        refused("a forbidden state cannot be reached at creation",
                "add", "finding", "F-9", "--state", "CLOSED", "-f", "title=x",
                needle="created in NEW")
        refused("an unknown severity is refused rather than ignored",
                "add", "finding", "F-8", "-f", "title=x", "-f", "severity=P0",
                needle="not a severity")
        refused("a prose guards value is refused rather than crashing the verdict",
                "add", "case", "S1-02", "-f", "action=a", "-f", "oracle=o",
                "-f", "guards=ceiling critical", needle="guards must be an object")
        allowed("file a fresh finding for the duplicate probe", "add", "finding", "F-7",
                "-f", "title=same root cause", "-f", "severity=major")
        refused("a duplicate must name a finding that exists",
                "move", "F-7", "DUPLICATE", "-f", "duplicate_of=F-NOPE",
                actor="dev1", role="DEV", needle="does not exist")
        refused("and not itself", "move", "F-7", "DUPLICATE", "-f", "duplicate_of=F-7",
                actor="dev1", role="DEV", needle="duplicate of itself")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILURES:
        print("%d claim(s) NOT enforced: %s" % (len(FAILURES), ", ".join(FAILURES)))
        print("Either make the claim true, or delete it from shared/principles.md. An unverified "
              "claim of enforcement is worse than no claim.")
        return 1
    print("every enforcement claim in shared/principles.md is backed by a refusal")
    return 0


if __name__ == "__main__":
    sys.exit(main())
