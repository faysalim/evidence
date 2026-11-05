#!/usr/bin/env python3
"""Readiness evidence is about a build, and about the release it gates.

    python -I tests/test_readiness_build.py
    python -I tests/test_readiness_build.py -v

Why this exists. The readiness gate shipped unbound to anything. Reproduced before this file was
written: one row, `MET` with no build, linked to no release, satisfied the condition for a hub
holding **two** separate releases on two different digests.

That is the defect `dashboard.py` already names for QA's gate rows, in a comment written the last
time it happened: *"asking only 'is this row's build some release's build' let a fresh candidate
inherit the previous release's gate rows -- so 'the build this verdict names' quietly became 'any
build in the hub'."* Readiness simply did not follow the pattern that comment established.

So: `build` is required on `MET` and on `WAIVED`, each row is linked to the release it gates, and the
condition counts only rows linked to the release being judged **whose build matches that release's
build**. Everything else is stale, and stale rows are named rather than silently ignored.

The regression the review asked for is `test_a_does_not_green_b`.
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


def readiness_row(hub):
    """The readiness condition: (ok, detail)."""
    import hub as H           # noqa: N813
    import dashboard as D
    _label, _first, conds = D.verdict(H.Hub(hub))
    for n, ok, d in conds:
        if "readiness" in n.lower():
            return ok, d
    return None, "no readiness condition found"


def release(hub, rid, build):
    run(hub, "add", "release", rid, "-f", "title=%s" % rid, "--actor", "d1", "--role", "DELIVERY")
    run(hub, "move", rid, "CANDIDATE", "-f", "build=%s" % build, "--actor", "v1", "--role", "DEV")


def checkpoint(hub, cid, rel, build=None, owner="DEVOPS", state="MET"):
    run(hub, "add", "readiness", cid, "-f", "title=rollback rehearsed",
        "-f", "owner_role=%s" % owner, "-f", "checkpoint=rollback-rehearsed",
        "--actor", "c1", "--role", "DELIVERY")
    if rel:
        run(hub, "link", cid, "gates", rel, "--actor", "c1", "--role", "DELIVERY")
    if state == "MET":
        argv = ["move", cid, "MET", "-f", "evidence=rehearsed 2026-03-04, 41s"]
        if build:
            argv += ["-f", "build=%s" % build]
        return run(hub, *(argv + ["--actor", "a1", "--role", owner]))
    return 0, ""


def fresh(tmp, name):
    hub = os.path.join(tmp, name)
    run(hub, "init", "--actor", "h1", "--role", "HEAD_OF_PRODUCT")
    # This file is about build and release scoping, not about set coverage, so the required set
    # is the one key these probes create. test_required_checkpoints.py covers the set itself.
    run(hub, "profile", "--set", 'required_checkpoints=["rollback-rehearsed"]',
        "--actor", "h1", "--role", "HEAD_OF_PRODUCT")
    return hub


def main():
    m = json.loads(io.open(os.path.join(ROOT, "shared", "hub", "model.json"),
                           encoding="utf-8").read())
    check("`gates` is a declared link type", "gates" in (m.get("link_types") or []),
          "declared: %s" % ", ".join(sorted(m.get("link_types") or [])))
    rd = m["types"]["readiness"]
    met = [t for t in rd["transitions"] if t["to"] == "MET"]
    waived = [t for t in rd["transitions"] if t["to"] == "WAIVED"]
    check("MET requires a build", met and "build" in (met[0].get("requires_fields") or []),
          "requires %s" % (met[0].get("requires_fields") if met else None))
    check("WAIVED requires a build too -- a waiver is about a candidate, not forever",
          waived and "build" in (waived[0].get("requires_fields") or []),
          "requires %s" % (waived[0].get("requires_fields") if waived else None))

    tmp = tempfile.mkdtemp(prefix="rdbuild_")
    try:
        # --- MET and WAIVED demand a build ------------------------------------------------
        hub = fresh(tmp, "needsbuild")
        release(hub, "REL-A", "sha256:aaa")
        rc, out = checkpoint(hub, "RD-1", "REL-A", build=None)
        check("MET with no build is REJECTED", rc != 0, "exit %d: %s" % (rc, out.strip()[:150]))
        check("the refusal names build", "build" in out, out.strip()[:150])
        rc, out = checkpoint(hub, "RD-2", "REL-A", build="sha256:aaa")
        check("MET with a build is accepted", rc == 0, out.strip()[:150])

        hub = fresh(tmp, "waivebuild")
        release(hub, "REL-A", "sha256:aaa")
        run(hub, "add", "readiness", "RD-9", "-f", "title=alert fires",
            "-f", "owner_role=DEVOPS", "-f", "checkpoint=rollback-rehearsed",
            "--actor", "c1", "--role", "DELIVERY")
        run(hub, "link", "RD-9", "gates", "REL-A", "--actor", "c1", "--role", "DELIVERY")
        rc, out = run(hub, "move", "RD-9", "WAIVED", "-f", "reason=deadline",
                      "--actor", "op", "--role", "OPERATOR")
        check("WAIVED with no build is REJECTED", rc != 0, "exit %d: %s" % (rc, out.strip()[:150]))
        rc, out = run(hub, "move", "RD-9", "WAIVED", "-f", "reason=deadline",
                      "-f", "build=sha256:aaa", "--actor", "op", "--role", "OPERATOR")
        check("WAIVED with a build is accepted", rc == 0, out.strip()[:150])
        ok, detail = readiness_row(hub)
        check("a waived row scoped to this build satisfies the condition", ok, detail[:170])

        # --- THE REGRESSION: MET for release A must not make release B green --------------
        hub = fresh(tmp, "ab")
        release(hub, "REL-A", "sha256:aaa")
        release(hub, "REL-B", "sha256:bbb")
        checkpoint(hub, "RD-A", "REL-A", build="sha256:aaa")
        ok, detail = readiness_row(hub)
        check("[REGRESSION] A's checkpoint does not green B", not ok, detail[:200])
        check("  and B is named as the release with nothing", "REL-B" in detail, detail[:200])
        checkpoint(hub, "RD-B", "REL-B", build="sha256:bbb")
        ok, detail = readiness_row(hub)
        check("with its own checkpoint, both hold", ok, detail[:200])

        # --- a row on a superseded build is stale, and named -----------------------------
        hub = fresh(tmp, "stale")
        release(hub, "REL-A", "sha256:aaa")
        checkpoint(hub, "RD-1", "REL-A", build="sha256:old")
        ok, detail = readiness_row(hub)
        check("a row whose build is not the release's does not count", not ok, detail[:200])
        check("  and it is named as stale, not silently ignored",
              "RD-1" in detail and "stale" in detail.lower(), detail[:200])

        # --- an unlinked row counts for nothing ------------------------------------------
        hub = fresh(tmp, "unlinked")
        release(hub, "REL-A", "sha256:aaa")
        checkpoint(hub, "RD-1", None, build="sha256:aaa")
        ok, detail = readiness_row(hub)
        check("a row linked to no release does not satisfy anything", not ok, detail[:200])
        check("  and the unlinked row is named", "RD-1" in detail, detail[:200])

        # --- re-openable, and re-opening drops it back out of the count ------------------
        hub = fresh(tmp, "reopen")
        release(hub, "REL-A", "sha256:aaa")
        checkpoint(hub, "RD-1", "REL-A", build="sha256:aaa")
        ok, _ = readiness_row(hub)
        check("green before the re-open", ok)
        rc, out = run(hub, "move", "RD-1", "OPEN",
                      "-f", "reason=candidate moved to sha256:bbb",
                      "--actor", "q1", "--role", "QA")
        check("QA may re-open a met checkpoint", rc == 0, out.strip()[:150])
        ok, detail = readiness_row(hub)
        check("and the condition stops holding", not ok, detail[:170])

        # --- no releases at all: the condition is still silent rather than green ---------
        hub = fresh(tmp, "norelease")
        ok, detail = readiness_row(hub)
        check("an empty hub is not green on readiness", not ok, detail[:170])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILURES:
        print("%d failure(s)" % len(FAILURES))
        return 1
    print("  ok   readiness is scoped to a release and a build; stale rows are named")
    return 0


if __name__ == "__main__":
    sys.exit(main())
