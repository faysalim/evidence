#!/usr/bin/env python3
"""A green verdict is no longer computable from QA evidence alone.

    python -I tests/test_release_readiness.py
    python -I tests/test_release_readiness.py -v

Why this exists. An independent review found the largest gap in the suite: the go/no-go was computed
entirely from QA rows, so **"ready to ship" meant "QA found nothing"** and said nothing about
whether the rollback had been rehearsed, an alert would fire, anyone was on call, or privacy had
signed off. Roughly the operational half of release readiness had no owner, no role and no items.

The fix is three roles (DEVOPS, SECURITY, SUPPORT), a `readiness` item type they own, and one
verdict condition that reads it. This asserts the behaviour that makes that real, including the
parts most likely to be got wrong later:

  - no readiness rows yields NO VERDICT, not NOT GREEN -- a refusal to call green on absent
    evidence, not a claim the release is unsafe
  - MET needs evidence, because "we can roll back" is a document and not a rehearsal
  - only the OPERATOR may WAIVE, because shipping without a rehearsed rollback is a decision
  - a role cannot mark its own checkpoint waived to get past the gate
"""

from __future__ import annotations

import io
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


def run(hub, *args):
    p = subprocess.run([sys.executable, "-I", "-B", HUB, "--hub", hub] + [str(a) for a in args],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def check(label, cond, detail=""):
    if cond:
        if VERBOSE:
            print("  ok   %s" % label)
    else:
        print("  FAIL %s%s" % (label, (" -- " + detail) if detail else ""))
        FAILURES.append(label)


def release(hub, rid="REL-1", build="sha256:abc"):
    """Readiness is scoped to a release and a build, so the probes need both."""
    run(hub, "add", "release", rid, "-f", "title=%s" % rid, "--actor", "d1", "--role", "DELIVERY")
    run(hub, "move", rid, "CANDIDATE", "-f", "build=%s" % build,
        "--actor", "v1", "--role", "DEV")
    return rid, build


def verdict_of(hub):
    import hub as H           # noqa: N813
    import dashboard as D
    return D.verdict(H.Hub(hub))


def main():
    import hub as H           # noqa: F401  (import here so a bad path fails loudly)

    m = json.loads(io.open(os.path.join(ROOT, "shared", "hub", "model.json"),
                           encoding="utf-8").read())
    for role in ("DEVOPS", "SECURITY", "SUPPORT"):
        check("the model declares role %s" % role, role in m["roles"])
    check("the model declares the readiness type", "readiness" in m["types"])
    if "readiness" not in m["types"]:
        print("\n%d failure(s)" % len(FAILURES))
        return 1

    tmp = tempfile.mkdtemp(prefix="relready_")
    try:
        # --- the condition exists, and an empty hub is silent about it rather than green -------
        hub = os.path.join(tmp, "empty")
        run(hub, "init", "--actor", "h1", "--role", "HEAD_OF_PRODUCT")
        label, _first, conds = verdict_of(hub)
        names = [n for n, _ok, _d in conds]
        row = [(n, ok, d) for n, ok, d in conds if "readiness" in n.lower()]
        check("the verdict has a readiness condition", bool(row),
              "conditions: %s" % "; ".join(names))
        if row:
            _n, ok, detail = row[0]
            check("with no rows it does not hold", not ok, detail[:160])
            check("and the detail explains why it cannot speak",
                  "release" in detail.lower() and "build" in detail.lower(), detail[:200])
        check("an empty hub is NO VERDICT, never GREEN", label != "GREEN within stated bounds",
              label)

        # --- MET needs evidence ---------------------------------------------------------------
        hub = os.path.join(tmp, "met")
        run(hub, "init", "--actor", "h1", "--role", "HEAD_OF_PRODUCT")
        rc, out = run(hub, "add", "readiness", "RD-1", "-f", "title=rollback rehearsed",
                      "--actor", "o1", "--role", "DEVOPS")
        check("DEVOPS cannot create a checkpoint with no owner_role", rc != 0,
              "exit %d: %s" % (rc, out.strip()[:140]))
        rc, out = run(hub, "add", "readiness", "RD-1", "-f", "title=rollback rehearsed",
                      "-f", "owner_role=DEVOPS", "--actor", "o1", "--role", "DEVOPS")
        check("with a title and owner_role it is created", rc == 0, out.strip()[:140])
        rc, out = run(hub, "move", "RD-1", "MET", "--actor", "o1", "--role", "DEVOPS")
        check("MET with no evidence is REJECTED", rc != 0, "exit %d: %s" % (rc, out.strip()[:140]))
        check("the refusal names evidence", "evidence" in out, out.strip()[:140])
        rc, out = run(hub, "move", "RD-1", "MET",
                      "-f", "evidence=rehearsed 2026-03-04, 41s, 0 rows lost",
                      "--actor", "o1", "--role", "DEVOPS")
        check("MET with evidence but no build is REJECTED", rc != 0, out.strip()[:140])
        rc, out = run(hub, "move", "RD-1", "MET",
                      "-f", "evidence=rehearsed 2026-03-04, 41s, 0 rows lost",
                      "-f", "build=sha256:abc",
                      "--actor", "o1", "--role", "DEVOPS")
        check("MET with evidence and a build is accepted", rc == 0, out.strip()[:140])

        # --- only the operator waives ---------------------------------------------------------
        for role in ("DEVOPS", "SECURITY", "SUPPORT", "DELIVERY", "QA"):
            hub2 = os.path.join(tmp, "waive-%s" % role)
            run(hub2, "init", "--actor", "h1", "--role", "HEAD_OF_PRODUCT")
            run(hub2, "add", "readiness", "RD-9", "-f", "title=alert fires",
                "-f", "owner_role=DEVOPS", "--actor", "o1", "--role", "DEVOPS")
            rc, out = run(hub2, "move", "RD-9", "WAIVED", "-f", "reason=no time",
                          "-f", "build=sha256:abc", "--actor", "x1", "--role", role)
            check("%s may not waive a checkpoint" % role, rc != 0,
                  "exit %d: %s" % (rc, out.strip()[:130]))
        hub3 = os.path.join(tmp, "waive-op")
        run(hub3, "init", "--actor", "h1", "--role", "HEAD_OF_PRODUCT")
        rid, _b = release(hub3)
        run(hub3, "add", "readiness", "RD-9", "-f", "title=alert fires",
            "-f", "owner_role=DEVOPS", "--actor", "o1", "--role", "DEVOPS")
        run(hub3, "link", "RD-9", "gates", rid, "--actor", "o1", "--role", "DEVOPS")
        rc, out = run(hub3, "move", "RD-9", "WAIVED", "--actor", "op", "--role", "OPERATOR")
        check("even the operator needs a reason", rc != 0, "exit %d: %s" % (rc, out.strip()[:140]))
        rc, out = run(hub3, "move", "RD-9", "WAIVED",
                      "-f", "reason=shipping for the customer deadline, rollback is manual",
                      "-f", "build=sha256:abc", "--actor", "op", "--role", "OPERATOR")
        check("the operator may waive with a reason", rc == 0, out.strip()[:140])
        _label, _f, conds = verdict_of(hub3)
        row = [(n, ok, d) for n, ok, d in conds if "readiness" in n.lower()][0]
        check("a waived checkpoint satisfies the condition", row[1], row[2][:160])
        check("and the waived id is named in the verdict, so the green stays readable",
              "RD-9" in row[2], row[2][:160])

        # --- an OPEN checkpoint denies, naming the id -----------------------------------------
        hub4 = os.path.join(tmp, "open")
        run(hub4, "init", "--actor", "h1", "--role", "HEAD_OF_PRODUCT")
        rid4, _b4 = release(hub4)
        run(hub4, "add", "readiness", "RD-5", "-f", "title=on-call named",
            "-f", "owner_role=DEVOPS", "--actor", "o1", "--role", "DEVOPS")
        run(hub4, "link", "RD-5", "gates", rid4, "--actor", "o1", "--role", "DEVOPS")
        _label, _f, conds = verdict_of(hub4)
        row = [(n, ok, d) for n, ok, d in conds if "readiness" in n.lower()][0]
        check("an OPEN checkpoint denies the condition", not row[1], row[2][:160])
        check("and the failing id is named", "RD-5" in row[2], row[2][:160])

        # --- re-opening on a new build needs a reason, and QA may do it -----------------------
        rc, out = run(hub, "move", "RD-1", "OPEN", "--actor", "o1", "--role", "DEVOPS")
        check("re-opening a MET checkpoint needs a reason", rc != 0,
              "exit %d: %s" % (rc, out.strip()[:140]))
        rc, out = run(hub, "move", "RD-1", "OPEN",
                      "-f", "reason=candidate moved to sha256:def; rehearsal was on abc",
                      "--actor", "q1", "--role", "QA")
        check("QA may re-open one -- QA is often who discovers the evidence is stale", rc == 0,
              out.strip()[:140])

        # --- the three skills exist and declare the three roles -------------------------------
        import re
        want = {"DEVOPS": "ops-readiness", "SECURITY": "security-review",
                "SUPPORT": "support-readiness"}
        for role, skill in want.items():
            p = os.path.join(ROOT, "skills", skill, "SKILL.md")
            check("skills/%s exists" % skill, os.path.isfile(p))
            if os.path.isfile(p):
                text = io.open(p, encoding="utf-8").read()
                end = text.find("\n---", 3)
                fm = text[4:end] if text.startswith("---\n") and end != -1 else ""
                check("skills/%s declares roles: %s" % (skill, role),
                      bool(re.search(r"^roles:\s*%s\s*$" % role, fm, re.M)), fm[:120])
        contract = os.path.join(ROOT, "shared", "contracts", "release-readiness.md")
        check("the handoff contract exists", os.path.isfile(contract))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILURES:
        print("%d failure(s)" % len(FAILURES))
        return 1
    print("  ok   readiness outside QA is owned, evidenced, and read by the verdict")
    return 0


if __name__ == "__main__":
    sys.exit(main())
