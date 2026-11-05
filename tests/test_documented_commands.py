#!/usr/bin/env python3
"""Every hub.py command the skills document is RUN, not just parsed.

    python -I tests/test_documented_commands.py
    python -I tests/test_documented_commands.py -v    # show every command, not just failures

Why this exists. A review round checked that the documented `hub.py` examples *parse*. Parsing
is not running: exercising skills/orient against a real product found that `hub.py status` on an
empty hub told the reader to run `hub.py init`, which is rejected outright for missing
--actor/--role. That example parsed perfectly. It just did not work. A skill's worth to a new
reader is its commands, and one that fails on first paste reads as a tool that does not work.

How a document is exercised, and why this shape:

  One hub per FILE, commands in document order. The first version gave every command a fresh
  hub and reported 9 failures, all of them its own fault: a document's examples are a
  SEQUENCE -- `add PRD-1` then `link PRD-1 measures M-1` then `move PRD-1 REVIEW` -- and
  judging the second line against a hub where the first never ran tests nothing but the
  harness. Sequencing is what makes a failure here mean something.

  Inline comments are stripped, `${CLAUDE_PLUGIN_ROOT}` is substituted, and backslash
  continuations are joined, because all three are things a reader's shell does too.

  TEMPLATE lines -- those with <angle brackets>, bare UPPER placeholders or `...` -- are
  counted and listed, never silently dropped. "Most of the examples work" is the claim this
  file exists to prevent, so what was not run is always on screen.

A rejection the DOCUMENT is responsible for is a defect: an unknown field, a state that does
not exist, a role that may not do that, an id used before it is created. The seed is deliberately
generous so that anything left is the document's fault, and every failure prints the command and
the first line of the refusal.
"""

from __future__ import annotations

import os
import re
import io
import shlex
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HUB = os.path.join(ROOT, "shared", "scripts", "hub.py")
VERBOSE = "-v" in sys.argv

# A placeholder is a thing the reader must replace. Running it verbatim proves nothing.
PLACEHOLDER = re.compile(r"<[^>]+>|\.\.\.|\$\{(?!CLAUDE_PLUGIN_ROOT)[^}]+\}|\$[A-Z_]{3,}"
                         r"|\b(?:NAME|ROLE|PATH|DIR|FILE|REPORT_DIR)\b")

FAILURES = []
TEMPLATES = []
RAN = 0


def md_files():
    for base in ("skills", "shared"):
        for dirpath, _dirs, names in os.walk(os.path.join(ROOT, base)):
            if "__pycache__" in dirpath:
                continue
            for n in sorted(names):
                if n.endswith(".md"):
                    yield os.path.join(dirpath, n)


def commands_in(path):
    """The hub.py invocations in one file, in document order."""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    out = []
    for block in re.findall(r"```[a-z]*\n(.*?)```", text, re.S):
        block = re.sub(r"\\\s*\n\s*", " ", block)            # join continuations
        # A quoted string may legally span lines in a shell; join those too.
        block = re.sub(r"(?<=[,\[])\s*\n\s*(?=\")", " ", block)
        for line in block.split("\n"):
            line = line.strip()
            if not line or line.startswith("#") or "hub.py" not in line:
                continue
            line = re.sub(r"\s+#(?![0-9]).*$", "", line)     # strip a trailing comment
            line = line.replace('"${CLAUDE_PLUGIN_ROOT}/shared/scripts/hub.py"', "hub.py")
            line = line.replace("${CLAUDE_PLUGIN_ROOT}/shared/scripts/hub.py", "hub.py")
            line = line.replace("${CLAUDE_PLUGIN_ROOT}", ROOT)
            m = re.search(r"hub\.py\s*(.*)$", line)
            if m:
                out.append((line, m.group(1).strip()))
    return out


def sh(argv, hub, actor="ex1", role="QA"):
    cmd = [sys.executable, "-I", "-B", HUB, "--hub", hub] + argv
    if not any(a == "--actor" for a in argv):
        cmd += ["--actor", actor]
    if not any(a == "--role" for a in argv):
        cmd += ["--role", role]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def type_for_state(state):
    """Which item type owns this state, from the model -- so a missing upstream item can be
    seeded as the right type instead of guessed. The model is the oracle; nothing is invented."""
    import json
    model = json.loads(io.open(os.path.join(ROOT, "shared", "hub", "model.json"),
                               encoding="utf-8").read())
    for name, d in model["types"].items():
        for tr in d.get("transitions", []):
            if tr["to"] == state or state in tr.get("from", []):
                return name, d.get("create", ["QA"])[0]
    return None, None


def creator_role(itype):
    import json
    model = json.loads(io.open(os.path.join(ROOT, "shared", "hub", "model.json"),
                               encoding="utf-8").read())
    c = model["types"].get(itype, {}).get("create") or ["QA"]
    return c[0]


def seed(hub):
    """Generous context, with ids unlikely to collide with a document's own examples."""
    sh(["init"], hub)
    sh(["profile", "--set", "mode=existing", "--set", 'domains=["payments"]'],
       hub, role="HEAD_OF_PRODUCT")
    for t, i, f, actor, role in [
        ("case", "SEED-C1", ["action=do the thing", "oracle=the operator's ledger"], "qa1", "QA"),
        ("finding", "SEED-F1", ["title=a seeded finding", "severity=major"], "qa1", "QA"),
        ("story", "SEED-S1", ["title=a seeded story"], "po1", "PO"),
        ("prd", "SEED-P1", ["title=a seeded prd"], "pm1", "PM"),
        ("release", "SEED-R1", ["title=a seeded release"], "dm1", "DELIVERY"),
        ("requirement", "SEED-RQ1", ["title=a seeded requirement"], "ba1", "BA"),
        ("metric", "SEED-M1", ["title=a seeded metric"], "an1", "ANALYST"),
        ("insight", "SEED-I1", ["title=a seeded insight"], "re1", "RESEARCHER"),
        ("adr", "SEED-A1", ["title=a seeded adr"], "tl1", "TECH_LEAD"),
        ("design", "SEED-D1", ["title=a seeded design"], "de1", "DESIGNER"),
        ("doc", "SEED-DOC1", ["title=a seeded doc"], "wr1", "WRITER"),
        ("risk", "SEED-RK1", ["title=a seeded risk"], "dm1", "DELIVERY"),
        ("cleanup", "SEED-CL1", ["title=a seeded resource"], "qa1", "QA"),
        ("fix", "SEED-FX1", ["title=a seeded fix"], "dv1", "DEV"),
        ("launch", "SEED-L1", ["title=a seeded launch"], "mk1", "PMM"),
        ("initiative", "SEED-IN1", ["title=a seeded initiative"], "pm1", "PM"),
        ("decision", "SEED-DC1", ["title=a seeded decision"], "ba1", "BA"),
    ]:
        argv = ["add", t, i]
        for kv in f:
            argv += ["-f", kv]
        sh(argv, hub, actor=actor, role=role)


def skill_role(path):
    """Run a skill's own examples as the role that skill declares. The dev skill's commands
    are DEV's commands; judging them as QA tested the harness, not the document."""
    d = os.path.dirname(path)
    sk = os.path.join(d, "SKILL.md")
    for cand in (path, sk, os.path.join(os.path.dirname(d), "SKILL.md")):
        if os.path.isfile(cand) and cand.endswith("SKILL.md"):
            # The file BEGINS with `---`, so splitting on "\n---" yields two parts and the
            # frontmatter is part 0, not part 1. Getting this wrong made every skill read as
            # QA and hid the one real defect in this run behind a wrong-role rejection.
            text = io.open(cand, encoding="utf-8").read()
            fm = text.split("\n---", 1)[0] if text.startswith("---") else ""
            m = re.search(r"^roles:\s*([A-Z_]+)", fm, re.M)
            if m:
                return m.group(1)
    return "QA"


def main():
    tmp = tempfile.mkdtemp(prefix="doccmd_")
    global RAN
    files = 0
    inherited = []
    try:
        for path in md_files():
            cmds = commands_in(path)
            if not cmds:
                continue
            rel = os.path.relpath(path, ROOT).replace("\\", "/")
            files += 1
            hub = os.path.join(tmp, "h%d" % files)
            seed(hub)
            if VERBOSE:
                print("\n%s" % rel)
            for line, tail in cmds:
                if not tail or PLACEHOLDER.search(tail):
                    TEMPLATES.append((rel, line))
                    if VERBOSE:
                        print("  tmpl %s" % tail[:66])
                    continue
                try:
                    argv = shlex.split(tail)
                except ValueError as exc:
                    FAILURES.append((rel, line, "unparseable: %s" % exc))
                    continue
                role = skill_role(path)
                rc, out = sh(argv, hub, role=role)
                # An example may legitimately reference an item an earlier SESSION created --
                # a DEV fix names the finding QA filed. Seed it as the type the model says
                # owns the state in play, retry once, and REPORT it, so the inheritance is
                # visible rather than hidden behind a pass.
                m_missing = re.search(r"no item ([A-Za-z0-9._-]+) in the hub", out)
                if m_missing:
                    mid = m_missing.group(1)
                    itype = None
                    if argv and argv[0] == "move" and len(argv) > 2:
                        itype, _ = type_for_state(argv[2])
                    if not itype:
                        itype = "finding"
                    sh(["add", itype, mid, "-f", "title=inherited upstream item",
                        "-f", "severity=major", "-f", "action=x", "-f", "oracle=y"],
                       hub, actor="up1", role=creator_role(itype))
                    inherited.append((os.path.relpath(path, ROOT).replace("\\", "/"),
                                      mid, itype))
                    rc, out = sh(argv, hub, role=role)
                RAN += 1
                bad = rc != 0 or "REJECTED" in out
                if VERBOSE or bad:
                    print("  %s %s" % ("FAIL" if bad else "ok  ", tail[:66]))
                if bad:
                    FAILURES.append((rel, line, out.strip().split("\n")[0][:200]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n%d file(s): ran %d command(s), %d template(s) not runnable as printed, "
          "%d failure(s)" % (files, RAN, len(TEMPLATES), len(FAILURES)))
    if FAILURES:
        print("\nfailures -- each is a command a reader would paste and watch fail:")
        for rel, line, why in FAILURES:
            print("\n  %s" % rel)
            print("    $ %s" % line[:150])
            print("    %s" % why)
        return 1
    print("  ok   every runnable documented command works, in document order")
    return 0


if __name__ == "__main__":
    sys.exit(main())
