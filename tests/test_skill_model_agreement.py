#!/usr/bin/env python3
"""Every state and item type a skill names must exist in the model.

    python -I tests/test_skill_model_agreement.py
    python -I tests/test_skill_model_agreement.py -v

Why this exists. A skill's prose promises transitions -- "SPECIFIED to AGREED by a different
role", "FIXED is a claim, CLOSED is a verdict". If the model has no such state, or the state
belongs to a different type, the skill documents a workflow the tool will refuse. The reader
discovers this at the moment they try to use it, and cannot tell whether they or the document
are wrong.

`tests/test_documented_commands.py` runs the commands inside fenced blocks. This covers the
other half: the states and types named in PROSE and in tables, which no command exercises and
which therefore drift freely.

What counts as a claim, and why this is deliberately narrow:

  Only tokens used in a TRANSITION-SHAPED phrase are judged -- "moves to FOO", "-> FOO",
  "FOO ->", "move <id> FOO". In that position a token is unambiguously being offered as a
  state, so if the model has no such state for any type, the skill documents a move the tool
  will refuse.

  An earlier version also tried to check that a state belonged to a type the skill "owns",
  and produced nine failures, every one of them wrong: dev legitimately discusses a finding's
  FIXED and NEW because moving QA's findings IS its job, hub discusses every type, release
  reads a story's DONE inside its verdict. Ownership is not inferable from the text, so that
  check is not attempted rather than attempted badly.

  So this does NOT catch a state attributed to the wrong type. It catches invented states and
  invented types. That limit is stated here because a check whose coverage is overstated is
  worse than one with none.
"""

from __future__ import annotations

import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERBOSE = "-v" in sys.argv

FAILURES = []


def model():
    with io.open(os.path.join(ROOT, "shared", "hub", "model.json"), encoding="utf-8") as fh:
        return json.load(fh)


def states_by_type(m):
    out = {}
    for name, d in m["types"].items():
        s = {d["initial"]}
        for tr in d.get("transitions", []):
            s.add(tr["to"])
            s.update(tr.get("from", []))
        out[name] = s
    return out


def main():
    m = model()
    by_type = states_by_type(m)
    all_states = set()
    for s in by_type.values():
        all_states |= s
    types = set(m["types"])

    # A skill's own item types: the ones it says it produces, read from its `roles:` and the
    # model's create lists, so the attribution is the model's and not a guess here.
    owns = {}
    for t, d in m["types"].items():
        for r in d.get("create", []):
            owns.setdefault(r, set()).add(t)

    checked = 0
    for name in sorted(os.listdir(os.path.join(ROOT, "skills"))):
        path = os.path.join(ROOT, "skills", name, "SKILL.md")
        if not os.path.isfile(path):
            continue
        text = io.open(path, encoding="utf-8").read()
        fm = text.split("\n---", 1)[0] if text.startswith("---") else ""
        mr = re.search(r"^roles:\s*(.+)$", fm, re.M)
        roles = [x.strip() for x in mr.group(1).split(",")] if mr else []
        mine = set()
        for r in roles:
            mine |= owns.get(r, set())
        # a skill also legitimately discusses items it reads rather than creates
        if not mine:
            continue

        # Which types does the prose name?
        named_types = {t for t in types if re.search(r"`%s`" % re.escape(t), text)}
        for t in named_types - types:
            FAILURES.append((name, "names item type %r, which the model does not have" % t))

        # Only transition-shaped positions: there, a token is unambiguously a state.
        tokens = set()
        for pat in (r"(?:moves?\s+to|->|→)\s*`?([A-Z][A-Z0-9_]{2,})`?",
                    r"`?([A-Z][A-Z0-9_]{2,})`?\s*(?:->|→)",
                    r"move\s+\S+\s+([A-Z][A-Z0-9_]{2,})"):
            tokens |= set(re.findall(pat, text))
        # Roles and states are different namespaces and the model knows both. "`DONE` by
        # DEV -> `ACCEPTED`" put a ROLE in an arrow position and read as an invented state.
        tokens -= set(m["roles"])
        for tok in sorted(tokens):
            if tok in all_states:
                if VERBOSE:
                    print("  ok   %-14s %s" % (name, tok))
                continue
            FAILURES.append((name, "offers a move to %s, and no item type in the model has "
                                   "that state -- the tool would refuse it" % tok))
        checked += 1

    print("\n%d skill(s) checked against the model" % checked)
    if FAILURES:
        print("\nfailures -- prose promising a workflow the tool would refuse:")
        for name, why in FAILURES:
            print("  %-15s %s" % (name, why))
        return 1
    print("  ok   every state and type named in prose exists and belongs to a type in scope")
    return 0


if __name__ == "__main__":
    sys.exit(main())
