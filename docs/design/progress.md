# Progress — plugin-suite restructure

**If context has reset: read this file, then `git log --oneline plugin-suite`, then continue from "Next".
Do not restart.**

Branch `plugin-suite`. Snapshot of the pre-restructure state is `306816a`. Never push, merge, open a PR,
rewrite history or delete branches.

---

## Where we are

**Steps 1-6 complete.** 4 of 15 skills built.

| Step | What | State |
|---|---|---|
| 1 | Snapshot commit | **DONE** `306816a` |
| 2 | `docs/design/plugin.md` | **DONE** `e5dc138` |
| 3 | `shared/hub` + `hub.py` + dashboard + tests | **DONE** `ead6091` |
| 4 | File moves, splits, QA trimmed 470 -> 263 | **DONE** `624cc2e` |
| 5 | `skills/dev` | **DONE** `b31b755` |
| 6 | `skills/hub`, `skills/orient` | **DONE** `3a61b17` |
| 7 | The remaining 11 skills | **IN PROGRESS** |
| 8 | Trigger evals + both fixtures | not started |
| 9 | README, CONTRIBUTING, migration; full run | not started |
| 10 | 5-agent council, apply, verify (max 2 rounds) | not started |
| 11 | `final-report.md` | not started |

Skills built: `qa` (263 lines), `dev`, `hub`, `orient`.
Remaining: `discovery` `prd` `requirements` `backlog` `delivery` `design` `architecture`
`release` `docs-authoring` `launch` `analytics`.

## Next

Write the remaining 11 skills in lifecycle order, each <=300 lines, `status: draft` in its own
README, concrete field lists and templates, open questions at the end. Commit in small groups.

## Test status

| Suite | Count | State |
|---|---|---|
| `shared/scripts/test_safe_edit.py` | 25 checks | PASS |
| `shared/scripts/test_qa_dashboard.py` | 25 checks | PASS |
| `shared/scripts/test_hub.py` | 70 checks | PASS |
| `shared/scripts/check_repo.py` | 7 checks | PASS |
| `claude plugin validate .` | — | PASS (warns: no icon; README rewrite due in step 9) |
| trigger evals / `claude plugin test` | — | not written (step 8) |
| description-budget test | — | not written (step 8) |

**120 automated checks passing.**

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
