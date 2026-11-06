#!/usr/bin/env python3
"""An existing product must have its surface counted, and the case set is measured against it.

    python -I tests/test_coverage_floor.py
    python -I tests/test_coverage_floor.py -v

Why this exists. An engagement on a real product wrote ~50 cases, and every check in the suite
passed. The operator said that is not expert work. The cause was mechanical and had three links:

  1. `orient` Step 4 calls the capability inventory "the heart of the skill" -- enumerate the real
     surface from code, record the method as a re-runnable command. **It was never built**, and
     nothing demanded it. So nobody knew how big the job was.
  2. **No expected-case count exists anywhere in the suite.** With no surface count there is
     nothing for 30 cases to be 30 *of*, so 30 passed honestly.
  3. Case-first was prose, so even zero cases passed. (Fixed separately.)

So: the inventory is mandatory for an existing product, and the hub computes a FLOOR from data it
already has -- the capability inventory plus the catalogue conditions and named defect classes of
the declared domains -- and reports the case set against it.

A floor, not a target. It is the arithmetic the engagement's own profile implies, and the point is
that 30-against-a-floor-of-103 is visible where bare 30 was not.
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


def sh(hub, *args, **kw):
    role = kw.get("role", "HEAD_OF_PRODUCT")
    actor = kw.get("actor", "h1")
    p = subprocess.run([sys.executable, "-I", "-B", HUB, "--hub", hub] + [str(a) for a in args]
                       + ["--actor", actor, "--role", role],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main():
    import hub as H

    tmp = tempfile.mkdtemp(prefix="floor_")
    try:
        # ---- an existing product with no inventory is refused -------------------------
        hub = os.path.join(tmp, "noinv")
        sh(hub, "init")
        sh(hub, "profile", "--set", "mode=existing", "--set", 'domains=["desktop-app"]')
        rc, out = sh(hub, "validate")
        check("an existing product with no capability inventory FAILS validate", rc != 0,
              "exit %d: %s" % (rc, out.strip()[:170]))
        check("  and the message names the inventory", "capability_inventory" in out,
              out.strip()[:220])
        check("  and says why: there is nothing to measure coverage against",
              "coverage" in out.lower() or "denominator" in out.lower(), out.strip()[:240])

        rc, out = sh(hub, "status")
        check("status names it as the next step", "capability_inventory" in out,
              out.strip()[:260])

        # a NEW product is not asked for one -- there is no surface to enumerate yet
        hub2 = os.path.join(tmp, "new")
        sh(hub2, "init")
        sh(hub2, "profile", "--set", "mode=new")
        rc, out = sh(hub2, "validate")
        check("a NEW product is not asked for an inventory", rc == 0,
              "exit %d: %s" % (rc, out.strip()[:170]))

        # the method must be a command, not prose -- the lesson of the irreproducible denominator
        hub3 = os.path.join(tmp, "prose")
        sh(hub3, "init")
        sh(hub3, "profile", "--set", "mode=existing", "--set", 'domains=["desktop-app"]',
           "--set", "capability_inventory=60 settings")
        rc, out = sh(hub3, "validate")
        check("an inventory with no re-runnable method still FAILS", rc != 0,
              "exit %d: %s" % (rc, out.strip()[:170]))
        check("  naming capability_inventory_method", "capability_inventory_method" in out,
              out.strip()[:220])

        # ---- the floor, computed ------------------------------------------------------
        hub4 = os.path.join(tmp, "floor")
        sh(hub4, "init")
        sh(hub4, "profile", "--set", "mode=existing",
           "--set", 'domains=["desktop-app","licensing-server"]',
           "--set", "capability_inventory=60",
           "--set", "capability_inventory_method=grep -roh ... | sort -u | wc -l")
        h = H.Hub(hub4)
        floor = H.coverage_floor(h)
        check("the floor is computed from the profile and the domains", floor["floor"] > 0,
              json.dumps(floor)[:200])
        check("  it counts the capability inventory", floor["inventory"] == 60,
              json.dumps(floor)[:200])
        check("  and the catalogue conditions of BOTH declared domains",
              floor["domain_conditions"] >= 55,
              "got %d; desktop-app is 29 and licensing-server 26" % floor["domain_conditions"])
        check("  and shows its arithmetic rather than one number",
              set(floor) >= {"inventory", "domain_conditions", "floor", "per_domain"},
              sorted(floor))

        rc, out = sh(hub4, "status")
        check("status reports cases against the floor", "floor" in out.lower(),
              out.strip()[:300])

        # with 0 cases against a floor of 80+, status must say so plainly
        check("  and names the shortfall when nothing is written",
              "0 of" in out or "0 case" in out.lower(), out.strip()[:300])

        # ---- the floor rises with the inventory, which is the point ------------------
        sh(hub4, "profile", "--set", "capability_inventory=600")
        f2 = H.coverage_floor(H.Hub(hub4))
        check("a bigger surface implies a bigger floor", f2["floor"] > floor["floor"],
              "%d vs %d" % (f2["floor"], floor["floor"]))

        # ---- an unknown domain cannot silently contribute zero ----------------------
        hub5 = os.path.join(tmp, "unknowndom")
        sh(hub5, "init")
        sh(hub5, "profile", "--set", "mode=existing",
           "--set", 'domains_other=["obfuscator-like, no file"]',
           "--set", 'domains=["desktop-app"]',
           "--set", "capability_inventory=10",
           "--set", "capability_inventory_method=a command")
        f3 = H.coverage_floor(H.Hub(hub5))
        check("a domain recorded in domains_other is reported, not silently worth zero",
              f3.get("unmatched_domains"), json.dumps(f3)[:200])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILURES:
        print("%d failure(s)" % len(FAILURES))
        return 1
    print("  ok   the surface is counted, and the case set is measured against what it implies")
    return 0


if __name__ == "__main__":
    sys.exit(main())
