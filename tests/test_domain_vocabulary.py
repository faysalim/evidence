#!/usr/bin/env python3
"""A product class the suite has no file for must be refused, not stored.

    python -I tests/test_domain_vocabulary.py
    python -I tests/test_domain_vocabulary.py -v

Why this exists. `skills/orient` Step 2 says "Pick from shared/domains/ -- twenty-seven classes".
`skills/architecture` and `skills/prd` both then say to READ the chosen domain file: it carries the
fault catalogue and the load-bearing contracts for the class, and it is the most valuable thing the
domain layer provides.

Exercising those two skills against a real product, the profile was set to
`domains=["distributed-database","self-hosted-deployment"]` and the hub stored both without a word.
There is no `self-hosted-deployment.md`. A skill told to read the domain file for it finds nothing,
and nothing anywhere says the class was never recognised -- so the fault catalogue for a class the
product really is simply never gets read, and the omission is invisible.

This is worse since `status` began printing `domains` to the eleven skills that read it first: an
unrecognised name now propagates to all of them with the authority of the profile.

A class the suite genuinely lacks is a real case -- orient says to work from the scope families and
write the missing file afterwards. So the refusal names `domains_other` as the place to record it,
and that field is kept and surfaced. What must never happen is a typo being indistinguishable from
a deliberate choice.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HUB = os.path.join(ROOT, "shared", "scripts", "hub.py")
DOMAINS = os.path.join(ROOT, "shared", "domains")
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
    run("--hub", hub, "init", "--actor", "h1", "--role", "HEAD_OF_PRODUCT")
    return hub


def set_domains(hub, value):
    return run("--hub", hub, "profile", "--set", "domains=" + value,
               "--actor", "h1", "--role", "HEAD_OF_PRODUCT")


def profile_of(hub):
    rc, out = run("--hub", hub, "profile")
    try:
        return json.loads(out)
    except ValueError:
        return {}


def main():
    known = sorted(f[:-3] for f in os.listdir(DOMAINS)
                   if f.endswith(".md") and f != "README.md")
    print("%d domain file(s) on disk" % len(known))
    if "distributed-database" not in known:
        print("  FAIL shared/domains/distributed-database.md is gone -- this test needs a real one")
        return 1

    tmp = tempfile.mkdtemp(prefix="domvocab_")
    try:
        # A real class is accepted.
        hub = fresh(tmp, "good")
        rc, out = set_domains(hub, '["distributed-database"]')
        check("a class with a file is accepted", rc == 0, out.strip()[:160])
        check("and is stored", profile_of(hub).get("domains") == ["distributed-database"],
              "got %r" % (profile_of(hub).get("domains"),))

        # An invented class is refused, and the refusal is useful.
        hub2 = fresh(tmp, "typo")
        rc2, out2 = set_domains(hub2, '["distributed-database","self-hosted-deployment"]')
        check("a class with no file is REJECTED", rc2 != 0, "exit %d: %s" % (rc2, out2.strip()[:160]))
        check("the refusal names the unrecognised class",
              "self-hosted-deployment" in out2, out2.strip()[:200])
        check("the refusal points at the escape hatch for a class the suite lacks",
              "domains_other" in out2, out2.strip()[:200])
        check("nothing was stored -- a rejected write leaves no half-set profile",
              not profile_of(hub2).get("domains"),
              "profile holds %r" % (profile_of(hub2).get("domains"),))

        # The escape hatch works and survives to `status`, so "no class fits" stays sayable.
        hub3 = fresh(tmp, "hatch")
        rc3, out3 = run("--hub", hub3, "profile",
                        "--set", 'domains=["distributed-database"]',
                        "--set", 'domains_other=["self-hosted-deployment: no file; worked from '
                                 'the scope families"]',
                        "--actor", "h1", "--role", "HEAD_OF_PRODUCT")
        check("a class recorded as unmatched is accepted", rc3 == 0, out3.strip()[:160])
        rc4, out4 = run("--hub", hub3, "status")
        try:
            body = json.loads(out4)
        except ValueError:
            body = {}
        check("status surfaces the unmatched class rather than hiding it",
              any("self-hosted-deployment" in str(v) for v in body.values()),
              "status keys: %s" % ", ".join(sorted(body)))

        # A single string, not a list, is the other way people write this field.
        hub5 = fresh(tmp, "scalar")
        rc5, out5 = set_domains(hub5, "not-a-real-class")
        check("a bare string naming no file is refused too", rc5 != 0,
              "exit %d: %s" % (rc5, out5.strip()[:160]))

        # The suggestion must be right or absent. The first version of this refusal answered
        # "self-hosted-deployment -- did you mean payments?", which is worse than no hint: a
        # reader who accepts it ends up reading the fault catalogue for the wrong class, and the
        # tool sounded confident. A real typo is suggested; an unrelated name gets nothing.
        hub6 = fresh(tmp, "typo2")
        _, out6 = set_domains(hub6, '["distributed-databse"]')
        check("a one-character typo is corrected", "distributed-database" in out6,
              out6.strip()[:200])
        hub7 = fresh(tmp, "unrelated")
        _, out7 = set_domains(hub7, '["self-hosted-deployment"]')
        check("an unrelated name is told 'nothing close', not given a wrong guess",
              "nothing close" in out7, out7.strip()[:240])
        check("and no unrelated class is named as a suggestion",
              "payments" not in out7, out7.strip()[:240])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILURES:
        print("%d failure(s)" % len(FAILURES))
        return 1
    print("  ok   the product-class vocabulary is closed, and 'no class fits' is still sayable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
