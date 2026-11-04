# Progress — plugin-suite restructure

**If context has reset: read this file, then `git log --oneline plugin-suite`, then continue from "Next".
Do not restart.**

Branch `plugin-suite`. Snapshot of the pre-restructure state is `306816a`. Never push, merge, open a PR,
rewrite history or delete branches.

---

## Where we are

**Steps 1-9 complete. All 15 skills built. The 5-agent review council is running.**

| Step | What | Commit |
|---|---|---|
| 1 | Snapshot | `306816a` |
| 2 | `docs/design/plugin.md` | `e5dc138` |
| 3 | hub, hub.py, dashboard, tests | `ead6091` |
| 4 | File moves and splits; QA trimmed 470 -> 263 | `624cc2e` |
| 5 | `skills/dev` | `b31b755` |
| 6 | `skills/hub`, `skills/orient` | `3a61b17` |
| 7a | discovery, prd, backlog | `7d4fbd6` |
| 7b | requirements, architecture, design | `877eb52` |
| 7c | release, docs-authoring, launch, analytics, delivery | `1339e02` |
| 7d | descriptions trimmed to the measured budget | `26232d5` |
| 8a | both fixtures + dashboards | `fa352e0` |
| 8b/9 | trigger evals, fixture test, README, CONTRIBUTING | `43695c0` |
| 10 | 5-agent council -> consolidate -> apply -> verify | **IN PROGRESS** |
| 11 | `final-report.md` | not started |

## Next

The council's five reports arrive as task notifications. Then: consolidate into
`docs/design/council-review.md` de-duplicated by root cause and ranked; apply or reject each with
a reason; anything that would change a product-qa rule goes to NEEDS FAISAL rather than being
applied; commit fixes in groups referencing finding ids; then ONE fresh verification agent re-runs
every applied finding's repro. At most two rounds. Then the final report.

## Test status

| Suite | Count | State |
|---|---|---|
| `shared/scripts/test_hub.py` | 70 | PASS |
| `shared/scripts/test_safe_edit.py` | 25 | PASS |
| `shared/scripts/test_qa_dashboard.py` | 25 | PASS |
| `shared/scripts/check_repo.py` | 7 checks | PASS |
| `tests/test_fixtures.py` | 24 | PASS |
| `tests/test_description_budget.py` | 6 (+1 measured) | PASS — 2,349 tok of 2,500 |
| `tests/triggers/check_overlap.py` | overlap + corpus | PASS — found 8 unguarded pairs, all now guarded |
| `claude plugin validate .` | — | PASS (one warning: no icon) |
| `claude plugin eval` (6 cases) | — | MIXED, see below |

**~160 automated checks passing.**

### Eval results, honestly

Run 1 (`max_turns: 2`): every skill-firing case hit the turn limit — my config bug, not a trigger
result. The one case that must trigger NOTHING scored 1.00 with and without.

Run 2 (`max_turns: 6`): mean delta +0.22. `hub` hit 1.00 with vs 0.00 without. Ordinary debugging
still correctly fired nothing. `qa` hit 0.33. The three near-miss cases scored 0.00 — but the
grader was an `llm` judge reading response prose, which is weak evidence for which tool fired.

Run 3 (in flight) uses the `tool_used` grader found by probing the harness: free, deterministic,
and `max: 0` proves no skill fired at all. That makes the must-not-trigger case decisive. Which
skill fired is still judged from prose — recorded as a known weak oracle in `evals/README.md`.

Cost so far: ~$6 of eval runs.

## Scaffold evidence (kept — the design rests on it)

Proved in a **cold** `claude -p` session against a marketplace install:

1. `${CLAUDE_PLUGIN_ROOT}/shared/x.md` **arrives expanded** in SKILL.md body text. PASS.
2. No permission prompt on reading it — **but** under `--permission-mode acceptEdits`. Partial.
3. A shared script runs from the expanded path via model-run Bash. PASS on Windows.
4. `claude plugin details`: `~79 tok` always-on for one skill; `~80`/`~280` per component. PASS.

Throwaway scaffold lives at `E:/Personal/projects/product-suite-scaffold` and is installed at user scope as
`product-suite-scaffold@product-suite-scaffold-market`. **Clean-up at the end:**

```bash
claude plugin uninstall product-suite-scaffold@product-suite-scaffold-market
claude plugin marketplace remove product-suite-scaffold-market
rm -rf /e/Personal/projects/product-suite-scaffold
```

## NOT RUN — carried to the final report, never silently passed

| What | Why | What would unblock it |
|---|---|---|
| Linux path handling for `hub.py` and the lint | No Linux host in this environment | Any Linux host or container |
| Permission-prompt behaviour in **default** mode | A human has to observe the prompt; `claude -p` was run with `acceptEdits` | Faisal runs the probe once |
| Copy semantics on a **copied** install | A local-path marketplace loads in place, so `../` escapes would pass locally and fail for real users | A git-sourced marketplace, or accept the lint as the guard |

## Permission denials hit

| Command | Result | Worked around by |
|---|---|---|
| `git checkout -b plugin-suite` | denied | `git branch` (allowed) |
| `git switch plugin-suite` | denied | Faisal ran it in his terminal |
| `git commit` | **allowed** | — |

Not worked around, by instruction: nothing. Recorded and continued.

## Open questions

- Whether `claude plugin test` / `claude plugin eval` cover trigger evals in the shape the brief wants, or
  need a thin wrapper. Resolve during step 8.
- Whether 15 skills survive the listing budget on a smaller context window. The budget test is the gate.
- Whether the three next-up domain files belong in this restructure. Current plan: no — the restructure
  should not also grow the method.

## NEEDS FAISAL (full list with recommendations in `plugin.md` §8)

- **D-11** plugin-directory submission needs a README ≥40 words and a one-shot square PNG icon.
- **D-12** proof 2 was run under `acceptEdits`, not default mode.
- **D-13** copy semantics unproven.
