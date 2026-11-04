"""One-shot: rewrite the eval graders to use the deterministic tool_used grader where it can
decide, and to be honest about where it cannot.

Kept in docs/design so the choice is auditable.

What was learned by probing the harness (the schema rejects unknown keys, which makes probing
free):

  type: tool_used      a free, deterministic grader. Runs even when a cost ceiling skips the
                       paid llm/baseline graders.
  tool: Skill          which tool to count.
  min: / max:          bounds on the call count. `max: 0` asserts the tool was NEVER called.
  name:                accepted; it is the grader's label, not a skill matcher.

So `tool_used` can prove that *a* skill fired, or that *none* did -- but not *which* one. For the
must-not-trigger case that is the whole question, and the assertion is decisive and costs nothing.
For "the right skill fired" it is only half the answer, and the other half falls to an llm grader
reading the response prose, which is weak evidence for a tool call. That limitation is recorded in
evals/README.md rather than papered over: a judge inferring tool use from prose is the product
reporting on itself, which principle 3 does not accept as an oracle.
"""
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVALS = os.path.join(ROOT, "evals")
CORPUS = os.path.join(ROOT, "tests", "triggers", "corpus.json")


def grader(path, body, **fm):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    head = "\n".join("%s: %s" % (k, v) for k, v in fm.items())
    io.open(path, "w", encoding="utf-8", newline="\n").write(
        "---\n%s\n---\n\n%s\n" % (head, body))


def main():
    corpus = json.loads(io.open(CORPUS, encoding="utf-8").read())
    expect = {}
    for case in corpus["cases"]:
        for p in case["hits"]:
            expect[p.strip().lower()] = case["expect"]
        for nm in case["near_misses"]:
            expect[nm["prompt"].strip().lower()] = nm["expect"]

    n = 0
    for name in sorted(os.listdir(EVALS)):
        d = os.path.join(EVALS, name)
        prompt_path = os.path.join(d, "prompt.md")
        if not os.path.isfile(prompt_path):
            continue
        prompt = io.open(prompt_path, encoding="utf-8").read()
        body = prompt.split("---", 2)[-1].strip().lower()
        # The case name encodes its target -- `trigger-<target>-...` -- which is more reliable
        # than matching the prompt text, because the committed subset paraphrases the corpus.
        target = expect.get(body)
        if target is None and name.startswith("trigger-"):
            target = name.split("-")[1]
        if target == "none":
            pass
        elif target and target not in {c["expect"] for c in corpus["cases"]}:
            raise SystemExit("case %s implies target %r, which is not a skill" % (name, target))
        gdir = os.path.join(d, "graders")
        for f in os.listdir(gdir):
            os.remove(os.path.join(gdir, f))

        if target == "none":
            grader(os.path.join(gdir, "no-skill-fires.md"),
                   "This prompt is ordinary work that no skill in this suite should claim. A "
                   "15-skill always-on plugin that fires on unrelated requests is worse than one "
                   "that under-fires: the user gets confidently wrong guidance instead of none.\n\n"
                   "Deterministic and free: the Skill tool must not be called at all.",
                   **{"type": "tool_used", "tool": "Skill", "max": 0, "weight": 2})
        else:
            grader(os.path.join(gdir, "a-skill-fires.md"),
                   "Some skill in the suite must fire. Deterministic and free: this counts the "
                   "actual tool call rather than believing the prose.",
                   **{"type": "tool_used", "tool": "Skill", "min": 1, "weight": 1})
            if target:
                grader(os.path.join(gdir, "the-right-skill.md"),
                       "The work must be routed to `product-suite:%s`, and not to a neighbouring "
                       "skill. Judge from what the response actually does and names.\n\n"
                       "KNOWN WEAKNESS: this grader reads the response prose, so it is weak "
                       "evidence for which tool fired. The deterministic half is the sibling "
                       "grader; see evals/README.md." % target,
                       **{"type": "llm", "weight": 1})
        n += 1
    print("rewrote graders for %d case(s)" % n)


if __name__ == "__main__":
    main()
