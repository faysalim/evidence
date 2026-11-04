#!/usr/bin/env python3
"""The description budget, measured rather than argued.

    python -I tests/test_description_budget.py

Why this exists. Every enabled plugin puts the name plus the description (and when_to_use) of
every skill it ships into the context of EVERY session. With 15 skills that is a real standing
cost, and the failure mode is not truncation: when the skill listing overflows its budget,
Claude Code DROPS descriptions, starting with the least-invoked skills. For this plugin the
least-invoked skills are the new drafts -- so going over budget silently deletes the triggers of
exactly the skills that most need them, and nothing says it happened.

So the limit is a measurement, not a style rule. The threshold below was chosen from the
documented budget (1% of the model's context window, shared across ALL skills the user has, not
just ours) with room left for the other plugins a real user has installed. We take roughly a
quarter of a 200k-token window's 1%.

Measured history:
  15 skills, original descriptions (8,869 chars)  ->  ~2,773 tok   OVER
  15 skills, trimmed descriptions  (6,899 chars)  ->  ~2,207 tok   ok

If this test fails, trim descriptions -- do not raise the threshold. The threshold is the point.

Requires the plugin to be installed and `claude` on PATH. Without either it reports NOT RUN and
exits 0, because a check that cannot run must say so rather than pass quietly.
"""

from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN = "product-suite"

ALWAYS_ON_CEILING = 2500      # tokens, measured by `claude plugin details`
PER_SKILL_CHAR_CEILING = 700  # characters per description; docs/design/plugin.md D-8
TOTAL_CHAR_CEILING = 7500     # characters across all descriptions

FAILURES = []
NOT_RUN = []


def check(label, condition, detail=""):
    if condition:
        print("  ok   %s" % label)
    else:
        print("  FAIL %s %s" % (label, detail))
        FAILURES.append(label)


def descriptions():
    out = {}
    sk = os.path.join(ROOT, "skills")
    for name in sorted(os.listdir(sk)):
        path = os.path.join(sk, name, "SKILL.md")
        if not os.path.isfile(path):
            continue
        text = io.open(path, encoding="utf-8").read()
        m = re.search(r'(?<=\ndescription: ).*?(?=\n---\n)', text, re.S)
        out[name] = m.group(0).strip() if m else ""
    return out


def main():
    desc = descriptions()
    print("static limits (%d skills)" % len(desc))
    check("every skill has a description", all(desc.values()),
          [k for k, v in desc.items() if not v])

    over = {k: len(v) for k, v in desc.items() if len(v) > PER_SKILL_CHAR_CEILING}
    check("no description over %d chars" % PER_SKILL_CHAR_CEILING, not over, over)

    total = sum(len(v) for v in desc.values())
    check("descriptions total <= %d chars" % TOTAL_CHAR_CEILING,
          total <= TOTAL_CHAR_CEILING, "total=%d" % total)

    missing_not_for = [k for k, v in desc.items() if "not for" not in v.lower()]
    check("every description has a \"Not for\" line", not missing_not_for, missing_not_for)

    # Every "Not for ... product-suite:X" must name a skill that exists, or the boundary
    # it draws points nowhere.
    bad_refs = []
    for name, text in desc.items():
        for ref in re.findall(r'product-suite:([a-z-]+)', text):
            if ref not in desc:
                bad_refs.append("%s -> %s" % (name, ref))
    check("every product-suite:X cross-reference names a real skill", not bad_refs, bad_refs)

    print("\nmeasured always-on cost")
    if not shutil.which("claude"):
        NOT_RUN.append("always-on token cost: `claude` is not on PATH")
        print("  NOT RUN  always-on token cost -- `claude` is not on PATH")
    else:
        try:
            proc = subprocess.run(["claude", "plugin", "details", PLUGIN],
                                  capture_output=True, text=True, timeout=120)
            out = (proc.stdout or "") + (proc.stderr or "")
        except (OSError, subprocess.SubprocessError) as exc:
            out = ""
            NOT_RUN.append("always-on token cost: could not run claude (%s)" % exc)
        m = re.search(r'Always-on:\s*~?([\d,]+)\s*tok', out)
        if not m:
            NOT_RUN.append("always-on token cost: plugin not installed, or the output format "
                           "of `claude plugin details` changed")
            print("  NOT RUN  always-on token cost -- is the plugin installed?")
        else:
            tokens = int(m.group(1).replace(",", ""))
            check("always-on cost %d tok <= %d" % (tokens, ALWAYS_ON_CEILING),
                  tokens <= ALWAYS_ON_CEILING,
                  "trim descriptions; do not raise the ceiling")
            per = dict(re.findall(r'^\s{2}([a-z-]+)\s+~(\d+)\s+', out, re.M))
            if per:
                worst = max(per.items(), key=lambda kv: int(kv[1]))
                print("       heaviest skill: %s at ~%s tok always-on" % worst)

    print()
    for n in NOT_RUN:
        print("NOT RUN: %s" % n)
    if FAILURES:
        print("%d check(s) FAILED: %s" % (len(FAILURES), ", ".join(FAILURES)))
        return 1
    print("all checks passed%s" % (" (%d NOT RUN)" % len(NOT_RUN) if NOT_RUN else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
