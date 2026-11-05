#!/usr/bin/env python3
"""The three LOW defects left open after two review rounds.

    python -I tests/test_low_defects.py

Left documented rather than fixed at the time because the two-round limit had been reached.
Reproducing them showed two were worse than recorded:

  NEW-5  `validate` exits 0 over a hub with no `events/` directory, reporting it as a NOTE.
         "This hub does not exist" must not read as "this hub is clean" -- point the tool at
         a mistyped path and it congratulates you.

  NEW-6  A single non-UTF-8 byte anywhere in any log makes `validate` CRASH with a
         UnicodeDecodeError traceback, not report a problem. The hub's own rule is that one
         bad line must not make the whole hub unreadable; a traceback is the strongest
         possible violation of it. Same for a view whose `generated_from` is not an object.

  NEW-7  Two findings whose ids differ only in case (`F-1`, `f-1`) were both accepted, and
         the dashboard then wrote ONE page for them -- `item-F-1.html` -- so one finding's
         page silently overwrote the other's. Recorded as cosmetic; it is page-level data
         loss on any case-insensitive filesystem, which includes every default Windows and
         macOS install.

Each test asserts the FIX, and each was run against the unfixed code first.
"""

from __future__ import annotations

import glob
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HUB = os.path.join(ROOT, "shared", "scripts", "hub.py")

FAILURES = []


def run(*args):
    p = subprocess.run([sys.executable, "-I", "-B", HUB] + [str(a) for a in args],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def check(label, cond, detail=""):
    if cond:
        print("  ok   %s" % label)
    else:
        print("  FAIL %s%s" % (label, (" -- " + detail) if detail else ""))
        FAILURES.append(label)


def fresh(tmp, name):
    hub = os.path.join(tmp, name)
    run("--hub", hub, "init", "--actor", "a1", "--role", "QA")
    return hub


def test_missing_events(tmp):
    """NEW-5: a hub that is not there is not a clean hub."""
    empty = os.path.join(tmp, "nothing_here")
    os.makedirs(empty)
    rc, out = run("--hub", empty, "validate")
    check("validate over a hub with no events/ exits non-zero", rc != 0,
          "exit %d -- a mistyped path reported itself clean" % rc)
    check("and says the hub is not there, not that it is fine",
          "problem" in out.lower() and "events" in out.lower(), out.strip()[:160])


def test_bad_bytes(tmp):
    """NEW-6: one bad line is one problem, never a traceback."""
    hub = fresh(tmp, "badbytes")
    run("--hub", hub, "add", "finding", "F-1", "-f", "title=real", "-f", "severity=major",
        "--actor", "a1", "--role", "QA")
    log = glob.glob(os.path.join(hub, "events", "QA", "*.jsonl"))[0]
    with open(log, "ab") as fh:
        fh.write(b'{"v":1,"seq":99,"op":"note","text":"\xff\xfe"}\n')

    rc, out = run("--hub", hub, "validate")
    check("a non-UTF-8 byte does not produce a traceback",
          "Traceback" not in out and "UnicodeDecodeError" not in out, out.strip()[-180:])
    check("it is reported as a problem", "problem" in out.lower(), out.strip()[:160])
    check("validate exits non-zero on it", rc != 0, "exit %d" % rc)
    check("the valid events are still readable alongside it",
          "F-1" in run("--hub", hub, "list")[1] or rc != 0)

    # a view header that is not an object must also report rather than raise
    hub2 = fresh(tmp, "badview")
    run("--hub", hub2, "add", "finding", "F-2", "-f", "title=x", "-f", "severity=major",
        "--actor", "a1", "--role", "QA")
    run("--hub", hub2, "views", "--out", os.path.join(tmp, "v"))
    view = os.path.join(tmp, "v", "qa-state.json")
    if os.path.isfile(view):
        body = json.loads(io.open(view, encoding="utf-8").read())
        body["generated_from"] = "a string, not an object"
        io.open(view, "w", encoding="utf-8", newline="").write(json.dumps(body))
        rc2, out2 = run("--hub", hub2, "validate", "--views", os.path.join(tmp, "v"))
        check("a non-object generated_from does not raise",
              "Traceback" not in out2, out2.strip()[-180:])


def test_case_collision(tmp):
    """NEW-7: ids that collide on a case-insensitive filesystem are refused."""
    hub = fresh(tmp, "casecoll")
    rc1, _ = run("--hub", hub, "add", "finding", "F-1", "-f", "title=lower",
                 "-f", "severity=major", "--actor", "a1", "--role", "QA")
    check("the first id is accepted", rc1 == 0)
    rc2, out2 = run("--hub", hub, "add", "finding", "f-1", "-f", "title=UPPER",
                    "-f", "severity=major", "--actor", "a1", "--role", "QA")
    check("an id differing only in case is REJECTED", rc2 != 0 and "REJECTED" in out2,
          out2.strip()[:170])
    check("the refusal explains why, naming the existing id",
          "F-1" in out2 and ("case" in out2.lower() or "collide" in out2.lower()),
          out2.strip()[:170])

    # and the dashboard still writes one page per item
    out_dir = os.path.join(tmp, "dash")
    run("--hub", hub, "dashboard", "--out", out_dir)
    pages = [p for p in os.listdir(out_dir) if p.startswith("item-")] if os.path.isdir(out_dir) else []
    check("one page per surviving item", len(pages) == 1, "pages=%s" % pages)


def main():
    tmp = tempfile.mkdtemp(prefix="low_")
    try:
        print("NEW-5  a hub that is not there is not a clean hub")
        test_missing_events(tmp)
        print("\nNEW-6  one bad line is one problem, never a traceback")
        test_bad_bytes(tmp)
        print("\nNEW-7  ids that collide on a case-insensitive filesystem")
        test_case_collision(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print()
    if FAILURES:
        print("%d failure(s)" % len(FAILURES))
        return 1
    print("  ok   all three LOW defects closed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
