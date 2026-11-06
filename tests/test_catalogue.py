#!/usr/bin/env python3
"""The domain catalogues are enumerable, so a case set is generated rather than invented.

    python -I tests/test_catalogue.py
    python -I tests/test_catalogue.py -v

Why this exists. An engagement on a real product produced ~50 cases. The operator's reaction was
that this is not expert work, and they were right -- but the cause was mechanical, not attitude.

The 31 domain files name **413 failure-catalogue conditions** between them. `desktop-app.md` alone
names 18: install as non-administrator, over an existing version, on a clean VM with no runtime, a
path with non-ASCII characters, a roaming profile, offline, SmartScreen or Gatekeeper, an update
interrupted mid-download, the oldest supported OS, 125% and 150% scaling, mixed-scaling
multi-monitor, a comma-decimal locale, antivirus quarantine, disk full while saving, the process
killed with unsaved work, two instances at once, a file on a network share.

Every one of those is a case. None was written -- because they are middot-separated prose, so no
tool could enumerate them and the agent had to remember them from reading. A reviewer named this
exactly: "ship the per-domain fault catalogues so 'one case per entry' has something to enumerate."

So `hub.py catalogue` parses them and emits case material. Both shapes in the wild are handled:
middot-separated prose, and bullet lists. Defect-class tables too, which are the named classes QA
must look for by name.
"""

from __future__ import annotations

import io
import os
import re
import subprocess
import sys

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


def run(*args):
    p = subprocess.run([sys.executable, "-I", "-B", HUB] + [str(a) for a in args],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main():
    import hub as H

    # ---- the parser, over every domain file ------------------------------------------
    total = 0
    thin = []
    for f in sorted(os.listdir(os.path.join(ROOT, "shared", "domains"))):
        if not f.endswith(".md") or f == "README.md":
            continue
        name = f[:-3]
        entries = H.catalogue_entries(name)
        total += len(entries)
        if len(entries) < 5:
            thin.append((name, len(entries)))
    check("the catalogues parse across every domain file", total > 350,
          "%d entries parsed; expected 400+" % total)
    check("no domain file parses as thin -- that means the parser missed its shape",
          not thin, "thin: %r" % (thin[:6],))

    # ---- middot prose: desktop-app, the shape that defeated the first parser ---------
    da = H.catalogue_entries("desktop-app")
    check("desktop-app yields its 18 conditions", len(da) == 18, "got %d" % len(da))
    dc = H.defect_classes("desktop-app")
    check("  and its 11 named defect classes, which are middot prose not a table",
          len(dc) == 11, "got %d" % len(dc))
    joined = " | ".join(e["condition"].lower() for e in da)
    for want in ("non-administrator", "clean vm", "roaming", "smartscreen",
                 "scaling", "antivirus", "two instances", "network share"):
        check("  it names %r" % want, want in joined, joined[:160])

    # ---- bullet lists: the other shape ----------------------------------------------
    ff = H.catalogue_entries("feature-flags")
    check("a bullet-list catalogue parses too", len(ff) >= 9, "got %d" % len(ff))
    check("  and keeps the bold lead-in as the condition",
          any("default" in e["condition"].lower() for e in ff),
          str([e["condition"][:50] for e in ff][:3]))

    # ---- defect classes, which QA must look for BY NAME -----------------------------
    cls = H.defect_classes("feature-flags")
    check("named defect classes parse", len(cls) >= 6, "got %d" % len(cls))
    check("  with a name and what makes it that class",
          bool(cls and cls[0].get("name") and cls[0].get("test")), str(cls[:1]))

    # ---- the command: a list, and runnable case stubs -------------------------------
    rc, out = run("catalogue", "desktop-app")
    check("`hub.py catalogue <domain>` lists them", rc == 0, out.strip()[:140])
    check("  numbered, so a reader can count what they owe",
          re.search(r"^\s*1[.)]", out, re.M) is not None, out.strip()[:200])
    check("  and it reports the total", "18" in out, out.strip()[:200])

    rc, out = run("catalogue", "desktop-app", "--as-commands", "--scope", "install")
    check("--as-commands emits runnable `add case` lines", rc == 0, out.strip()[:140])
    lines = [l for l in out.splitlines() if l.startswith("hub.py add case")]
    # one per condition AND one per named class: both are things QA must go and do
    check("  one per condition and one per named class", len(lines) == 29,
          "got %d" % len(lines))
    check("  each carrying the required action and oracle",
          all("-f action=" in l and "-f oracle=" in l for l in lines),
          str(lines[:1]))
    # quoted, because the stub has to survive copy-paste into a shell
    check("  each scoped as asked",
          all('-f scope="install"' in l for l in lines), str(lines[:1]))
    check("  with distinct ids", len({l.split()[3] for l in lines}) == 29,
          "ids collide: %d distinct" % len({l.split()[3] for l in lines}))

    # the emitted stubs must be ACCEPTED by the hub -- a generator that emits commands the
    # tool refuses is worse than no generator.
    import shutil
    import tempfile
    tmp = tempfile.mkdtemp(prefix="cat_")
    try:
        hub = os.path.join(tmp, "h")
        run("--hub", hub, "init", "--actor", "h1", "--role", "HEAD_OF_PRODUCT")
        bad = 0
        for l in lines[:6]:
            argv = H.shlex_split(l)[1:]        # drop the leading `hub.py`
            rc2, out2 = run("--hub", hub, *(argv + ["--actor", "q1", "--role", "QA"]))
            if rc2 != 0:
                bad += 1
                if VERBOSE:
                    print("      rejected: %s" % out2.strip()[:110])
        check("the emitted commands are accepted by the hub as printed", bad == 0,
              "%d of 6 rejected" % bad)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # ---- no argument: use the profile's domains -------------------------------------
    rc, out = run("catalogue")
    check("with no domain it says what to do rather than guessing",
          rc != 0 or "domain" in out.lower(), out.strip()[:160])

    rc, out = run("catalogue", "not-a-domain")
    check("an unknown domain is refused, listing what exists", rc != 0 and "distributed" in out,
          out.strip()[:170])

    print()
    if FAILURES:
        print("%d failure(s)" % len(FAILURES))
        return 1
    print("  ok   %d catalogue conditions are enumerable, and emit cases the hub accepts" % total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
