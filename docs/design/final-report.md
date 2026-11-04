# product-suite — final report

Branch `plugin-suite`, 19 commits past the snapshot. **Nothing pushed, nothing merged, no PR, no
history rewritten.**

---

## 1. What's done

**Complete against the definition of done, with two exceptions, both yours to decide.**

| | |
|---|---|
| 15 skills | built, all ≤300 lines; `qa` trimmed 470 → 263 |
| `shared/` | principles, vocabulary, 2 contracts, templates, 4 references, 27 domains, hub model, 7 scripts |
| Hub | `hub.py` — one append-only log per actor, deterministic fold, generated views with a digest |
| Dashboard | computed verdict, 12 conditions, `NO VERDICT` default, verdict now printed to stdout too |
| Marketplace manifest | `.claude-plugin/{plugin,marketplace}.json`, `claude plugin validate` passes |
| README, CONTRIBUTING, migration | written; migration says to delete the old standalone skill |
| Fixtures | 2 engagements, 24 and 10 items, built through `hub.py` only, dashboards committed |
| Council | 5 reviewers, 59 findings, 8 critical — applied, then independently verified |

**The two exceptions:** the plugin cannot be installed the way its README says (`PE-1`), and in a
real session 7 of its 15 skills have no description (`PE-2`). Both are in §4.

## 2. Tests and evals

| Suite | Count | Result |
|---|---|---|
| `shared/scripts/test_hub.py` | 70 | **PASS** |
| `shared/scripts/test_safe_edit.py` | 25 | **PASS** |
| `shared/scripts/test_qa_dashboard.py` | 25 | **PASS** |
| `tests/test_fixtures.py` | 24 | **PASS** |
| `tests/test_enforcement_claims.py` | 30 | **PASS** |
| `tests/test_round2_regressions.py` | 36 | **PASS** |
| `tests/triggers/check_overlap.py` | overlap + corpus | **PASS** |
| `shared/scripts/check_repo.py` | 7 checks | **PASS** |
| `claude plugin validate .` | — | **PASS** (one warning: no icon) |
| `tests/fixtures/build.py --all` | both fixtures | **PASS**, validate clean |
| `tests/test_description_budget.py` | 6 | **FAILS, deliberately** — see `PE-2` |

**215 checks across six suites, plus 7 repo checks.** The one failure is real and intended: the
test used to measure this plugin's own always-on cost and printed `ok` while half the suite's
descriptions were being dropped. It now measures the actual skill-listing budget and fails at
7,442 chars against a 4,000 allowance.

**Evals:** 6 cases, run 4 times, ~$10. The result that holds up: **no skill fires on ordinary
debugging**, proven from the tool calls rather than from prose, in all six runs. Which skill fires
on the *hit* cases is **not established** — the deterministic grader counts any skill including
other plugins', and the prose judge is unreliable. Graders have since been rewritten to
`tool_used` + `input_match`, which the platform reviewer found does decide it; **NOT RUN** since,
on cost.

**NOT RUN, with reasons:**

| What | Why |
|---|---|
| 144 of the 150 trigger-corpus cases | each is a full Claude child on your credential; ~$80 to run all |
| Eval re-run with the corrected graders | ~$3; the graders are read-reviewed, not executed |
| Any Linux execution | no Linux host here. Paths were read, not run |
| Copy semantics on a copied install | a local-path marketplace loads in place; needs a git-sourced marketplace |
| Permission-prompt behaviour in default mode | observed only under `--permission-mode acceptEdits` |
| `HA-9` cross-item clock skew, re-verified | partially fixed; the reviewer's own `b6_skew.py` is the test |

## 3. Council findings

**59 findings from 5 cold reviewers, 8 critical.** Full consolidation with repros in
`docs/design/council-review.md`.

**The headline:** the adversary found **seven independent ways to get GREEN out of a hub that
should not be green**, two available to DEV alone. All seven are closed. And the method guardian
found that three of the ten principles claimed *"Enforced: X"* where X did not enforce it — the
exact failure this method exists to prevent, in the commit that claimed to make it enforceable.

- **Applied and independently verified:** 51 council findings plus 8 round-2 fixes.
- **Applied but NOT verified:** 4, found by round-2 verification after the round limit was reached.
- **Rejected or reclassified:** 6, with reasons — including `PP-12` (1 of 8 prompts triggering),
  reclassified as evidence for `PE-2` rather than a separate defect, because in that environment
  the descriptions were absent so the prompts *could not* route.
- **Open and documented:** 3 LOW defects plus 4 design limits.
- **NEEDS FAISAL:** 2 blockers and 5 smaller items.

Counting honestly: **66 defects found, 63 fixed, 3 left open.** Of the 63, four have no
independent verification.

The durable fix for the worst cluster is `tests/test_enforcement_claims.py`: every "Enforced:" line
now has a probe that attempts the forbidden thing and asserts the refusal. Verified both ways — it
passes, and breaking one enforcement makes it fail.

Three fixes needed fixes of their own, all caught by tests rather than by me:

- Gating `GREEN` on the computed verdict ran during **replay**, where a mid-fold hub looks stale to
  its own view — making a recorded GREEN permanently unreplayable. It is a write-time precondition,
  not a replay-time invariant.
- Accepting `--role` after the subcommand needed `argparse.SUPPRESS`; a plain `None` default had
  the subparser overwrite a value given before it.
- The must-not-trigger eval grader used `max: 0` with no `min`, yielding the impossible range
  `1..0` — so it failed exactly when the behaviour was correct.

## 4. NEEDS FAISAL

### `PE-2` — the plugin is over the skill-listing budget · **decide this first**

In a real session with your other plugins installed, **7 of the 15 skills have no description at
all.** The listing is 38,132 chars against a 30,000 budget on the default model and **8,000 on a
200k-window model** — this plugin's descriptions alone are ~96% of that before anything else
exists. Overflow drops descriptions starting with the least-invoked skills, which here are the
drafts. The README's primary promise — "most of the time you will not invoke anything" — is false
for half the suite, and that is also why only 1 of 8 natural prompts routed.

I measured one option and it does not work: `disable-model-invocation: true` leaves the description
in the listing (always-on stayed at 2,349 tok).

**My recommendation: ship fewer always-on skills.** Keep `qa`, `dev`, `hub` and `orient` — the two
with real provenance plus the two every other skill calls — as a plugin that auto-triggers, and
move the 11 drafts behind explicit invocation in a second plugin (`product-suite-roles`) that a
team enables when it wants them. That halves the listing cost, matches their draft status, and
costs nothing in capability. The alternatives are cutting every description to ~265 characters,
which guts the triggers and the "Not for" lines, or documenting `skillListingBudgetFraction` and
accepting that users with many plugins silently lose the drafts.

### `PE-1` — the README's install path cannot work · **one push**

`origin/main` is still the old standalone skill with no `.claude-plugin/`, and `plugin-suite` is
unpushed, so both documented install paths fail at step one. The install the council reviewed used
`claude plugin marketplace add E:\Personal\projects\product-qa`, which appears nowhere in the
README. **This is exactly the "README that only works for its author" defect the plugin's own
principles name.** Pushing was forbidden for this run, so it is yours:

```
git push -u origin plugin-suite
```

Then re-run the README's two commands on a clean machine and paste the output into the README,
which is the only way to know the GitHub-sourced path works — copy semantics are untested because a
local-path marketplace loads in place.

### Smaller ones

- **`MG-9`** — "NEW is not a resting state" has a `validate` check that keys on a field nothing
  ever sets. *Recommendation: add `hub.py handover <id>` and key the check on it.*
- **`HA-11`** — `import` is not atomic: a malformed file leaves a partial hub, and the retry is
  poisoned permanently because the log is append-only. *Recommendation: validate the whole file
  before appending anything.*
- **`PP-11`** — no skill says where its document artifact lives; the hub holds a one-line summary,
  so the launch claims table "the artifact this skill is built around" exists nowhere in either
  fixture. *Recommendation: one convention — `<hub-parent>/<type>/<id>.md`, path in a field.*
- **`D-11`** — plugin-directory submission wants a square PNG icon, and it is **fixed at first
  submission and cannot be changed later**. *Recommendation: choose it deliberately before you ever
  submit.*
- **`D-12`** — run the probe once in default permission mode to confirm reading a shared file
  prompts for nothing.
- **13 of 15 skills are `status: draft`**, written from first principles — which `CONTRIBUTING.md`
  warns against. *Recommendation: correct them from real engagements as you run them; that is the
  highest-value contribution in the repo and each lists its open questions.*

## 5. Blocks and permission denials

| What | Result | What I did |
|---|---|---|
| `git checkout -b` | denied | used `git branch` |
| `git switch` | denied | you ran it |
| `git commit --amend` | denied | **correctly** — history rewriting was forbidden. So commit `0d4c25f` keeps a mangled message (backticks in `-m` were read as command substitution and captured an environment dump); the intended text is `docs/design/round1-changelog.md`. The commit's *contents* are fine |
| push / merge / PR | not attempted | forbidden |

Shell quoting corrupted content three times in this run — two heredocs and one commit message. The
repo's own `gotchas.md` names the class; I should have used a file-writing tool each time rather
than re-learning it.

## 6. Independent verification — two rounds, and it earned its keep both times

**Round 1.** A fresh agent re-ran all 25 applied fixes with adversarial neighbours. Most verified.
Nine came back PARTIAL or STILL PRESENT — **including a new critical defect my own fix had
created**: marking two findings as duplicates *of each other* took two open criticals out of the
verdict and produced GREEN, in two legal DEV commands. It also found that my `HA-12` fix had
digested the wrong thing entirely (event ids, not the view body), so the reported hand-edit still
validated clean. All nine were fixed.

**Round 2.** A second fresh agent re-ran those eight fixes: **all eight verified.** It then
attacked the new code and found **seven more defects**, one HIGH — `set duplicate_of` bypassed the
round-1 duplicate fix completely, because the check lived in only one write path. That is the same
shape as the very first critical I fixed, which is the lesson: a guard belongs in a function every
write path calls, not at a call site.

**Four of those seven are fixed and three are open**, because the two-round limit was reached.
**The four fixes are NOT independently verified** — stating that plainly rather than letting the
"215 checks passing" line imply otherwise. They have regressions, and the regressions run against
a genuinely green base, but no cold agent has tried to break them.

The single most useful line in either report was about my tests, not my code:

> `test_round2_regressions.py`'s HA-3 check only asserts `label != GREEN` on a hub that is not
> otherwise green, so it would pass even if the duplicate condition were missing.

Correct, and a worse failure than the defect it covered — it is the "test that passes before the
fix" this method names explicitly. Every regression now builds a green base and asserts it is
green before attacking it.

**Still open after two rounds**, all LOW, all documented in `council-review.md`: `validate` exits 0
over a hub with no `events/` directory; a view whose header is not an object and a non-UTF-8 byte
in a log both raise rather than report; ids differing only in case collide on NTFS. Plus four
design limits recorded rather than fixed, the most notable being that a hand-written `GREEN` line
replays without a problem — the computed-verdict check is a write-time precondition and cannot be
re-evaluated later, though the dashboard still shows `NOT GREEN` so the disagreement is visible.

## 7. Install and try it

The plugin is already installed on this machine from the working tree, so you can use it now:

```bash
claude plugin list                       # product-suite@product-suite-market, enabled
claude plugin details product-suite      # 15 skills, ~2,349 tok always-on
```

Open the two worked engagements — these are the fastest way to see what it does:

```
tests/fixtures/existing/dashboard/index.html     # 24 items, verdict NOT GREEN, operator shipped anyway
tests/fixtures/new/dashboard/index.html          # 10 items, critical cross-team leak in an export
```

Run a real one:

```bash
cd <your project>
python <this repo>/shared/scripts/hub.py --actor you --role QA init --engagement my-product
python <this repo>/shared/scripts/hub.py --actor you --role QA iteration 1
# then, in a Claude session:  /product-suite:orient
```

Or just type what you want — "QA this release", "write acceptance criteria for this story", "what
is waiting on me" — and the descriptions should route it. Bearing `PE-2` in mind: today that works
reliably for `qa`, `dev`, `hub` and `orient`, and unreliably for the rest.

To see everything at once:

```bash
python <this repo>/shared/scripts/hub.py --hub <your hub> dashboard
```

Full detail: `docs/design/plugin.md` (design and 13 decisions), `council-review.md` (the 59
findings), `progress.md` (the build log), `round1-changelog.md`.
