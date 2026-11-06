#!/usr/bin/env python3
"""A scope with findings and no designed case set has no coverage denominator, and the hub says so.

    python -I tests/test_case_first.py
    python -I tests/test_case_first.py -v

Why this exists, in the reviewer's words and they are right:

    "This plugin already knows how to enforce. Its hub.py rejects an undeclared role, a finding
    with no title, a severity outside the vocabulary, an out-of-order causal chain. It hardened all
    the cheap invariants and left the single most important, most expensive one -- case-first, the
    thing that guarantees a real coverage denominator -- as prose only. That inconsistency is the
    bug. An agent will reliably skip the one gate that costs an hour and isn't checked, precisely
    because everything around it is checked and that one isn't."

A real engagement produced 20 findings and 0 cases, and `validate` reported clean. The lead said
plainly that they ran findings-first and backfilled; the point stands either way, because an
instruction with no consequence for ignoring it is a suggestion.

What is enforced, and the shape matters:

  - **Per SCOPE, not per finding.** `skills/qa` says a finding stumbled on while doing something
    else needs no case of its own, and that stays true: a scope that was genuinely tested may hold
    extra findings freely. What is refused is a scope that produced findings and never recorded a
    single thing it tried.
  - **`validate` fails**, so the loudest signal is not a missing dashboard section but a hub that
    reports itself invalid.
  - **The verdict denies**, naming the scopes, so GREEN cannot be reached by skipping the step.
  - **Filing the finding is never blocked.** Refusing `add finding` would make hiding a defect the
    cheaper path, which is the opposite of the point.
"""

from __future__ import annotations

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


def check(label, cond, detail=""):
    if cond:
        if VERBOSE:
            print("  ok   %s" % label)
    else:
        print("  FAIL %s%s" % (label, (" -- " + detail) if detail else ""))
        FAILURES.append(label)


def sh(hub, actor, role, *args):
    return subprocess.run([sys.executable, "-I", "-B", HUB, "--hub", hub]
                          + [str(a) for a in args] + ["--actor", actor, "--role", role],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


def fresh(tmp, name):
    hub = os.path.join(tmp, name)
    sh(hub, "h1", "HEAD_OF_PRODUCT", "init")
    return hub


def validate(hub):
    p = sh(hub, "h1", "HEAD_OF_PRODUCT", "validate")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def readiness_free_verdict(hub):
    """The case-first condition only."""
    import hub as H           # noqa: N813
    import dashboard as D
    _l, _f, conds = D.verdict(H.Hub(hub))
    for n, ok, d in conds:
        if "case set" in n.lower():
            return ok, d
    return None, "no case-set condition in the verdict"


def main():
    tmp = tempfile.mkdtemp(prefix="casefirst_")
    try:
        # ---- the real engagement's state: findings, no cases at all --------------------
        hub = fresh(tmp, "nocases")
        for i in range(1, 4):
            p = sh(hub, "q1", "QA", "add", "finding", "F-%d" % i, "-f", "title=defect %d" % i,
                   "-f", "severity=major", "-f", "scope=licensing")
            check("filing finding F-%d is NOT blocked" % i, p.returncode == 0,
                  ((p.stdout or "") + (p.stderr or "")).strip()[:120])

        rc, out = validate(hub)
        check("validate FAILS on findings with no case set", rc != 0,
              "exit %d: %s" % (rc, out.strip()[:170]))
        check("  and it names the scope", "licensing" in out, out.strip()[:200])
        check("  and says what is missing: a coverage denominator",
              "denominator" in out.lower(), out.strip()[:220])

        ok, detail = readiness_free_verdict(hub)
        check("the verdict has a case-set condition", ok is not None, detail[:140])
        check("  and it denies", ok is False, detail[:170])
        check("  naming the scope", "licensing" in (detail or ""), (detail or "")[:170])

        # ---- a scope that WAS tested may hold extra findings freely --------------------
        hub2 = fresh(tmp, "tested")
        sh(hub2, "q1", "QA", "add", "case", "S1-01", "-f", "action=do the thing",
           "-f", "oracle=an independent ledger", "-f", "scope=licensing")
        sh(hub2, "q1", "QA", "move", "S1-01", "PASS", "-f", "evidence=observed")
        for i in range(1, 4):
            sh(hub2, "q1", "QA", "add", "finding", "G-%d" % i, "-f", "title=stumbled on %d" % i,
               "-f", "severity=minor", "-f", "scope=licensing")
        rc, out = validate(hub2)
        check("a tested scope may hold findings with no case of their own", rc == 0,
              "exit %d: %s" % (rc, out.strip()[:170]))
        ok, _d = readiness_free_verdict(hub2)
        check("  and the condition holds", ok is True)

        # ---- a finding with NO scope, in a hub with no cases at all --------------------
        # The nebula hub's exact shape for most of its rows. Unscoped must not be a loophole.
        hub3 = fresh(tmp, "unscoped")
        sh(hub3, "q1", "QA", "add", "finding", "F-9", "-f", "title=no scope recorded",
           "-f", "severity=blocker")
        rc, out = validate(hub3)
        check("an unscoped finding in a hub with no cases still fails", rc != 0,
              "exit %d: %s" % (rc, out.strip()[:170]))
        check("  and the message does not pretend to know a scope",
              "no scope" in out.lower() or "unscoped" in out.lower(), out.strip()[:200])

        # ---- one scope good, another bad: only the bad one is named --------------------
        hub4 = fresh(tmp, "mixed")
        sh(hub4, "q1", "QA", "add", "case", "S1-01", "-f", "action=a", "-f", "oracle=b",
           "-f", "scope=docs")
        sh(hub4, "q1", "QA", "move", "S1-01", "PASS", "-f", "evidence=ok")
        sh(hub4, "q1", "QA", "add", "finding", "F-1", "-f", "title=in a tested scope",
           "-f", "severity=minor", "-f", "scope=docs")
        sh(hub4, "q1", "QA", "add", "finding", "F-2", "-f", "title=in an untested scope",
           "-f", "severity=major", "-f", "scope=security")
        rc, out = validate(hub4)
        check("the untested scope is named", "security" in out, out.strip()[:200])
        check("  and the tested one is not blamed",
              out.count("docs") == 0 or "docs" not in out.split("security")[0][-80:],
              out.strip()[:200])

        # ---- a DESIGNED case counts: the lock is "something was recorded as tried" -----
        hub5 = fresh(tmp, "designed")
        sh(hub5, "q1", "QA", "add", "case", "S1-01", "-f", "action=a", "-f", "oracle=b",
           "-f", "scope=licensing")
        sh(hub5, "q1", "QA", "add", "finding", "F-1", "-f", "title=x", "-f", "severity=major",
           "-f", "scope=licensing")
        rc, out = validate(hub5)
        check("a DESIGNED but unrun case satisfies case-first -- it is the denominator",
              rc == 0, "exit %d: %s" % (rc, out.strip()[:170]))

        # ---- an empty hub is not in violation -----------------------------------------
        hub6 = fresh(tmp, "empty")
        rc, _out = validate(hub6)
        check("an empty hub is not in violation -- no findings, no claim", rc == 0)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILURES:
        print("%d failure(s)" % len(FAILURES))
        return 1
    print("  ok   case-first is a lock, not a suggestion, and the stumbled-on finding survives")
    return 0


if __name__ == "__main__":
    sys.exit(main())
