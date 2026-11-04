# Progress — plugin-suite restructure

**If context has reset: read this file, then `git log --oneline plugin-suite`, then continue from "Next".
Do not restart.**

Branch `plugin-suite`. Snapshot of the pre-restructure state is `306816a`. Never push, merge, open a PR,
rewrite history or delete branches.

---

## Where we are

**Step 2 of 9 complete.** (Step numbering follows the brief's "Order of work".)

| Step | What | State |
|---|---|---|
| 1 | Snapshot commit | **DONE** — `306816a`, 24 files, +2901/−93, clean tree |
| 2 | `docs/design/plugin.md` | **DONE** — approval stop replaced by its Decisions section |
| 3 | `shared/hub` + `hub.py` + dashboard + tests | **NEXT** |
| 4 | File moves and splits; migrate `qa`, trim SKILL.md to ≤300 | not started |
| 5 | `skills/dev` | not started |
| 6 | `skills/hub`, `skills/orient` | not started |
| 7 | The remaining 11 skills, lifecycle order | not started |
| 8 | Trigger evals + both fixtures | not started |
| 9 | README, CONTRIBUTING, manifest; full test and cross-reference run | not started |
| 10 | 5-agent review council, consolidate, apply, fresh verification agent (max 2 rounds) | not started |
| 11 | `docs/design/final-report.md` | not started |

## Next

Build `shared/hub/` and `shared/scripts/hub.py`: item model, ownership table, append-only per-actor event
logs, deterministic fold, generated views with `generated_from`, `validate`. Then port the dashboard onto
the hub, keeping `qa_dashboard.py`'s computed-verdict logic, its `NO VERDICT` default and its 25 tests.

## Test status

| Suite | Count | State |
|---|---|---|
| `scripts/test_safe_edit.py` | 25 checks | PASS (at `306816a`) |
| `scripts/test_qa_dashboard.py` | 25 checks | PASS (at `306816a`) |
| hub tests | — | not written |
| cross-reference / domain-registry / variables / description-budget checks | — | not written |
| `claude plugin validate` | — | passes on the throwaway scaffold only |
| `claude plugin test` / `claude plugin eval` | — | not run |

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
