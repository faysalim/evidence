# Progress — plugin-suite restructure

**If context has reset: read this file, then `git log --oneline plugin-suite`, then continue from "Next".
Do not restart.**

Branch `plugin-suite`. Snapshot of the pre-restructure state is `306816a`. Never push, merge, open a PR,
rewrite history or delete branches.

---

## Where we are

**DONE.** Build complete, two council-and-verify rounds complete, final report written.

Read `docs/design/final-report.md` first. `council-review.md` has all 66 defects with repros and
dispositions; `plugin.md` has the design and its 13 decisions; `round1-changelog.md` holds the
message that commit `0d4c25f` lost to shell quoting.

**Published 2026-11-05** at https://github.com/faysalim/evidence — `main` at `063e563`,
212 files, Apache-2.0 detected. Renamed `product-suite` → `evidence` first, and the repo was
created with an MIT default that the push replaced.

**`PE-1` is CLOSED.** The README's two install commands were run verbatim against the real remote,
and then the whole suite was run from the resulting install: 8 of 9 suites pass from
`~/.claude/plugins/marketplaces/evidence-market`, `check_repo.py` 7/7, both fixtures rebuild with
`validate` clean. That is what proves the `${CLAUDE_PLUGIN_ROOT}` paths resolve as installed.

**One thing still needs Faisal:**

- `PE-2` — the plugin exceeds the skill-listing budget, so 7 of 15 descriptions are dropped in a
  real session. Needs a product decision; `disable-model-invocation` was measured and does not
  help. Recommendation: ship `qa`, `dev`, `hub`, `orient` as `evidence` and move the 11 drafts to a
  second plugin.

The old `product-qa-skill` repo and this repo's `origin` are untouched, and the local directory is
still named `product-qa`. The remote `plugin-suite` branch duplicates `main` and can be deleted.

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

Throwaway scaffold lives at `E:/Personal/projects/evidence-scaffold` and is installed at user scope as
`evidence-scaffold@evidence-scaffold-market`. **Clean-up at the end:**

```bash
claude plugin uninstall evidence-scaffold@evidence-scaffold-market
claude plugin marketplace remove evidence-scaffold-market
rm -rf /e/Personal/projects/evidence-scaffold
```

## Self-found, to fix in the post-council apply pass

Found by inspection while the council ran. Held rather than fixed mid-review, so the reviewers'
reads stay valid. All three are mine.

| id | Defect | Fix |
|---|---|---|
| `SF-1` | **`.gitignore:8` (`qa-state.json`) silently excluded both fixtures' generated view.** `fix-state.json` is committed, `qa-state.json` is not, so a clone gets half a fixture — and `tests/test_fixtures.py` cannot catch it because it rebuilds from scratch rather than reading the committed copy. The ignore rule was written for a QA repo where `qa-state.json` held real engagement data; it is now also a legitimate committed artifact under `tests/fixtures/`. | Scope the ignore to the repo root, or negate it under `tests/fixtures/`. **And add a check** that every file the fixtures' README claims is committed, is committed — the durable fix, since the rule is "the repo cannot lie about itself" |
| `SF-2` | **`evals/results/` is committed** — 14 files of run reports including HTML. Run artefacts, not source, and the same class as the existing ignore rule about QA run artefacts. | gitignore it and remove it from the index |
| `SF-3` | **`NOTICE` still names `product-qa`.** | Rename to `evidence` |

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
