# Eval suite

Trigger evals, run with the built-in harness:

```bash
claude plugin eval evidence --eval-dir evals --trust-plugin
```

**This directory ships a representative subset, not the whole corpus.** The full corpus —
15 skills × 5 hits × 5 near-misses — lives as data in `tests/triggers/corpus.json`, and
`python -I tests/triggers/check_overlap.py --emit-evals` writes all 150 cases here. It is not
committed in full because each case is a full Claude child running on the operator's own
credential and rate limit. The six committed cases cost **$3.25 per run**; 150 would be roughly
$80, which is not a cost to incur on someone's behalf without asking.

The six are chosen for the boundaries the corpus says are most confusable: `qa` vs `dev`
(fixing), `qa` vs `release` (the ship decision), `qa` vs `backlog` (acceptance criteria),
`hub` vs `delivery` (a direct status query), plus one case that must trigger **nothing**.

## What the graders are, and what each can actually decide

Two kinds, and the difference matters more than the scores:

| Grader | What it proves | Cost |
|---|---|---|
| `tool_used` (`tool: Skill`, with `min`/`max`) | A skill was called, or was not, counted from the actual tool calls | free, deterministic |
| `llm` | A judge's reading of the **response prose** | paid, and weak for this question |

**The `llm` grader is weak evidence for which tool fired**, and the runs bear that out: three of the
five skill-firing cases scored `FAIL FAIL FAIL` on "the right skill" even where the right skill
plausibly did fire. Asking a judge to infer a tool call from prose is the product reporting on
itself, which `shared/principles.md` §3 does not accept as an oracle. It is kept because it is the
only signal available for *which* skill, and it is labelled in the grader file itself as a known
weakness rather than quietly trusted.

**`tool_used: Skill` counts any skill, including other plugins'.** It cannot tell this plugin's
skills from another's. Evidence: `trigger-qa-hit` scored 1.00 **with** and 1.00 **without** the
plugin — in the no-plugin arm the agent still called some other installed skill, so the
deterministic grader passed for the wrong reason. Read a `with`/`without` delta of 0.00 on a hit
case as "inconclusive", not "no benefit".

## Results, as measured

Three runs, and the first two failed for reasons that were mine rather than the plugin's:

| Run | Config | Outcome |
|---|---|---|
| 1 | `max_turns: 2` | Every skill-firing case hit the turn limit: a skill loads and there are no turns left to answer. A config bug, not a trigger result |
| 2 | `max_turns: 6`, `llm` graders only | mean Δ +0.22. `hub` 1.00 vs 0.00 baseline. The near-misses scored 0.00 on prose judging |
| 3 | `max_turns: 6`, `tool_used` + `llm` | mean Δ +0.22. `release` near-miss 1.00 vs 0.00 (Δ +1.00). `qa` hit inconclusive per the note above |

And the result that matters most, after fixing one more grader bug of mine — `max: 0` alone yields
the impossible range `1..0`, because `min` defaults to 1, so the grader failed exactly when the
behaviour was correct:

```
✓ no-skill-fires (weight 2): Skill called 0x (expected 0..0)
  trigger-none-ordinary-debugging   with 1.00   without 1.00
```

**No skill fires on ordinary debugging, in all six runs, proven from the tool calls rather than
from prose.** For a plugin that puts 15 skill descriptions into every session, that is the
important direction: a suite which claims unrelated work is worse than one that under-triggers,
because the user gets confidently wrong guidance instead of none.

## What is NOT established

- **Which** skill fires, for the hit and near-miss cases. The deterministic grader cannot see it
  and the prose judge is unreliable. Resolving this needs a grader that matches the skill name;
  probing the schema found `min`, `max` and `name` (a label, not a matcher) and nothing that
  filters by skill.
- The other 144 corpus cases. NOT RUN, on cost.
- Anything about routing when other plugins are installed, beyond the one observation above.

The cheap half of trigger testing needs no agent at all and runs in a second:

```bash
python -I tests/triggers/check_overlap.py
```

It measures description overlap and asserts that every pair the corpus names as confusable is
guarded by a "Not for" line. It found eight unguarded pairs on its first run, including the
corpus's most-confused pair — `delivery` vs `hub` — which had slipped under the vocabulary
threshold at 0.119.
