#!/usr/bin/env python3
"""Static trigger analysis: where will two skills compete for the same prompt?

    python -I tests/triggers/check_overlap.py            # report + corpus consistency
    python -I tests/triggers/check_overlap.py --emit-evals  # write evals/ cases from the corpus

This is the cheap half of trigger testing, and it runs in a second. The expensive half is
actually firing an agent per prompt; see NOT RUN at the bottom of this docstring.

Two things are measured:

1. **Description overlap.** Two skills whose descriptions share the same distinctive vocabulary
   will compete, and the loser is decided by something we do not control. The report ranks every
   pair by shared distinctive terms, and flags a pair that overlaps strongly while NEITHER names
   the other in a "Not for" line -- that combination is the actual defect, because the "Not for"
   line is the only thing in a description that pushes a prompt away.

2. **Corpus consistency.** Every `expect` names a real skill; no prompt appears as a hit for one
   skill and a hit for another; every near-miss names a different skill than the one it is filed
   under. A corpus that contradicts itself cannot grade anything.

NOT RUN here, deliberately: the 150-case agent run. Each `claude plugin eval` case is a full
Claude child on the operator's own credential and rate limit, and 15 skills x 10 prompts is a
large unrequested spend. `--emit-evals` writes the cases so the operator can run as many as they
want; `evals/` ships a representative subset that proves the harness works end to end.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CORPUS = os.path.join(ROOT, "tests", "triggers", "corpus.json")

# Words that carry no routing signal: every description has them.
STOP = set("""a an and are as at be been before but by can covers do does for from has have
how in into is it its not of on once only or our over per so than that the their them then there
these they this to use used user users want wants was what when where which who will with would
your not-for product suite skill use when the user wants rather instead each every both
something anything nothing work works working make makes made write writes written run runs
first also more most other another same new existing real actual actually just only still
after against about across already always any because" """.split())


def read(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


def descriptions():
    out = {}
    sk = os.path.join(ROOT, "skills")
    for name in sorted(os.listdir(sk)):
        path = os.path.join(sk, name, "SKILL.md")
        if os.path.isfile(path):
            m = re.search(r'(?<=\ndescription: ).*?(?=\n---\n)', read(path), re.S)
            out[name] = m.group(0).strip() if m else ""
    return out


def terms(text):
    words = re.findall(r"[a-z][a-z-]{3,}", text.lower())
    return {w for w in words if w not in STOP and not w.startswith("evidence")}


def not_for_targets(text):
    """Which skills a description pushes away.

    Every `evidence:X` reference in a description counts, wherever it sits. The earlier
    version anchored on "not for ... evidence:X" within one sentence, which captured only
    the FIRST target per clause and so reported four pairs as unguarded when the boundary was
    plainly written. Capturing all references is sound because a description only ever names
    another skill in order to push work towards it -- there is no positive cross-reference in a
    description, and `check_repo.py skills` requires the "Not for" line to exist separately.
    """
    return set(re.findall(r'evidence:([a-z-]+)', text.lower()))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit-evals", action="store_true",
                    help="write evals/trigger-*/ cases from the corpus")
    ap.add_argument("--top", type=int, default=12)
    args = ap.parse_args(argv)

    desc = descriptions()
    corpus = json.loads(read(CORPUS))
    failures = []

    # ---- 1. overlap ------------------------------------------------------
    tset = {k: terms(v) for k, v in desc.items()}
    nf = {k: not_for_targets(v) for k, v in desc.items()}
    pairs = []
    names = sorted(desc)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            shared = tset[a] & tset[b]
            if not shared:
                continue
            # Jaccard, so a long description is not penalised for being long
            score = len(shared) / float(len(tset[a] | tset[b]))
            guarded = (b in nf[a]) or (a in nf[b])
            pairs.append((score, len(shared), a, b, guarded, sorted(shared)))
    pairs.sort(reverse=True)

    print("description overlap, highest first (guarded = at least one names the other in Not for)")
    for score, n, a, b, guarded, shared in pairs[:args.top]:
        print("  %5.3f  %-14s %-14s  %-9s  %s"
              % (score, a, b, "guarded" if guarded else "UNGUARDED",
                 ", ".join(shared[:7])))

    # The defect: strong overlap with no "Not for" pointing either way.
    THRESHOLD = 0.12
    for score, n, a, b, guarded, shared in pairs:
        if score >= THRESHOLD and not guarded:
            failures.append("%s and %s overlap at %.3f (%d shared terms: %s) and neither names "
                            "the other in a Not-for line -- the only device that pushes a prompt "
                            "away" % (a, b, score, n, ", ".join(shared[:6])))

    # ---- 2. corpus consistency -------------------------------------------
    print("\ncorpus consistency")
    hits = defaultdict(list)
    total_hits = total_misses = 0
    for case in corpus["cases"]:
        skill = case["expect"]
        if skill not in desc:
            failures.append("corpus expects skill %r, which does not exist" % skill)
        for p in case["hits"]:
            hits[p.strip().lower()].append(skill)
            total_hits += 1
        for nm in case["near_misses"]:
            total_misses += 1
            target = nm["expect"]
            if target != "none" and target not in desc:
                failures.append("near-miss in %s expects %r, which does not exist"
                                % (skill, target))
            if target == skill:
                failures.append("near-miss in %s expects %s -- a near-miss must route "
                                "ELSEWHERE, or it is a hit" % (skill, target))
            if not nm.get("why"):
                failures.append("near-miss %r in %s has no `why`" % (nm["prompt"][:40], skill))

    for prompt, owners in sorted(hits.items()):
        if len(set(owners)) > 1:
            failures.append("prompt %r is a hit for %s -- a prompt cannot belong to two skills"
                            % (prompt[:50], " and ".join(sorted(set(owners)))))

    print("  %d skills, %d hit prompts, %d near-misses" % (len(corpus["cases"]),
                                                           total_hits, total_misses))
    missing = sorted(set(desc) - {c["expect"] for c in corpus["cases"]})
    if missing:
        failures.append("no corpus entry for: %s" % ", ".join(missing))
    thin = [c["expect"] for c in corpus["cases"]
            if len(c["hits"]) < 5 or len(c["near_misses"]) < 5]
    if thin:
        failures.append("fewer than 5 hits or 5 near-misses for: %s" % ", ".join(thin))

    # which neighbours the corpus says a skill is most confusable with
    confusable = Counter()
    for case in corpus["cases"]:
        for nm in case["near_misses"]:
            if nm["expect"] != "none":
                confusable[tuple(sorted((case["expect"], nm["expect"])))] += 1
    # The vocabulary threshold above is a heuristic; the corpus is stronger evidence. A pair the
    # corpus itself names as confusable twice or more must be guarded whatever its Jaccard score.
    # The first version of this check used the threshold alone, and delivery/hub slipped under it
    # at 0.119 while being the most-confused pair in the corpus by a clear margin.
    print("\nmost-confused pairs, by the corpus")
    CONFUSABLE_MIN = 2
    for (a, b), n in confusable.most_common(10):
        guarded = (b in nf.get(a, set())) or (a in nf.get(b, set()))
        print("  %2d  %-14s %-14s  %s" % (n, a, b, "guarded" if guarded else "UNGUARDED"))
        if n >= CONFUSABLE_MIN and not guarded:
            failures.append("the corpus names %s and %s as confusable %d times, and neither "
                            "description names the other in a Not-for line. Corpus evidence "
                            "outranks the vocabulary threshold." % (a, b, n))

    if args.emit_evals:
        n = emit(corpus)
        print("\nwrote %d eval case(s) under evals/" % n)

    print()
    for f in failures:
        print("  FAIL %s" % f)
    if failures:
        print("\n%d failure(s)" % len(failures))
        return 1
    print("  ok   no unguarded strong overlap; corpus is self-consistent")
    print("\nNOT RUN: the agent-fired half of trigger testing. Each case is a full Claude child "
          "on your credential;\n         15 skills x 10 prompts is a large spend. "
          "`--emit-evals` writes them; evals/ ships a subset.")
    return 0


def emit(corpus):
    base = os.path.join(ROOT, "evals")
    count = 0
    for case in corpus["cases"]:
        skill = case["expect"]
        for kind, items in (("hit", [{"prompt": p, "expect": skill} for p in case["hits"]]),
                            ("miss", case["near_misses"])):
            for i, item in enumerate(items, 1):
                name = "trigger-%s-%s-%d" % (skill, kind, i)
                d = os.path.join(base, name)
                os.makedirs(os.path.join(d, "graders"), exist_ok=True)
                io.open(os.path.join(d, "prompt.md"), "w", encoding="utf-8",
                        newline="\n").write(
                    "---\nmax_turns: 2\nallowed_tools: [Skill]\n---\n\n%s\n" % item["prompt"])
                target = item["expect"]
                crit = ("The response must invoke the `evidence:%s` skill and no other "
                        "evidence skill." % target) if target != "none" else (
                    "The response must NOT invoke any evidence skill: this prompt is "
                    "ordinary work that no skill in the suite should claim.")
                io.open(os.path.join(d, "graders", "criteria.md"), "w", encoding="utf-8",
                        newline="\n").write(
                    "---\ntype: llm\nweight: 1\n---\n\n%s\n%s\n" % (
                        crit, "" if "why" not in item else "Reason: %s" % item["why"]))
                count += 1
    return count


if __name__ == "__main__":
    sys.exit(main())
