# product-suite — plugin design

Restructuring `product-qa` into a Claude Code plugin carrying one skill per deliverable, all sharing one
work-item hub and one dashboard.

**Status:** design approved to build unattended. The approval stop was replaced by the *Decisions* section
at the end of this document: every choice that would normally have been approved is recorded there with its
reason and the rejected alternative. Items marked `NEEDS FAISAL` are decisions taken to keep moving that
should be reviewed.

**Source of truth for the existing method:** commit `306816a` — *Snapshot product-qa before plugin
restructure*, on branch `plugin-suite`. Every claim below about "what product-qa does today" is against
that commit.

---

## 1. Platform facts, and what was proved rather than assumed

The layout rests on one claim: that a skill can read a file outside its own folder. That was verified
before anything was built, because the whole design collapses differently depending on the answer.

### Scaffold evidence

A throwaway plugin (`product-suite-scaffold`: one skill, one shared file, one shared script, its own
marketplace manifest) was built, validated, installed through the marketplace route, and probed from a
**cold session** (`claude -p`, which starts fresh and therefore loads the newly installed plugin — the
authoring session's skill listing is fixed at startup and cannot see it).

| # | Claim under test | Result | Evidence |
|---|---|---|---|
| 1 | `${CLAUDE_PLUGIN_ROOT}/shared/x.md` is **expanded in SKILL.md body text, for the model** | **PASS** | Cold session reported the text arrived as `E:/Personal/projects/product-suite-scaffold`, not as the literal `${CLAUDE_PLUGIN_ROOT}`; it read the file and quoted the marker line |
| 2 | Reading it prompts for permission | **No prompt** | Same run. **Caveat:** run with `--permission-mode acceptEdits`, so this does not prove the default mode is silent. See NOT RUN below |
| 3 | A shared script runs from the expanded path, via a model-run Bash command | **PASS** (Windows) | `HUB_OK_7Q4F argv=['probe','--from-skill'] file=E:\…\shared\scripts\hub.py`, invoked by the cold session itself |
| 4 | Always-on listing cost is measurable | **PASS** | `claude plugin details`: `Always-on: ~79 tok`; per-component `~80` always-on, `~280` on-invoke |

`claude plugin validate` exits 0 on the scaffold. `claude 2.1.318` is installed, which clears every version
floor in the platform docs (highest relevant: `--marketplace` on the shell, 2.1.292+).

### Two things the scaffold could not prove, and one it disproved

**Copy semantics are NOT exercised by a local-path marketplace.** `claude plugin list` reports
`Read from: E:\Personal\projects\product-suite-scaffold` — the plugin loads **in place**. The platform docs
say marketplace and cache installs *copy* the plugin directory, and that a script reading `../shared` from
inside a copied plugin "doesn't find them". So our own dev loop will happily resolve paths that break for
every user installing from GitHub. **This is the single most dangerous failure shape in the project**: it
passes locally and fails only for other people. It is why the variables lint (§6) is a hard gate rather
than a nicety.

**Validation surfaced two requirements the platform docs did not.** `claude plugin validate` refuses a
plugin-directory submission without a **README.md of at least 40 words** in the plugin folder
(`README_MISSING`), and warns on a missing **icon** — a square PNG, 512–2048 px, under 2 MB, SVG and WebP
not accepted. The icon has a trap worth recording: it "may become the listing icon only once: the first
time the plugin is saved or submitted… Adding or changing it later does not change the icon." Validation
also confirmed that `marketplace.json` and `plugin.json` may share one `.claude-plugin/` directory, and
that such a folder is treated as a plugin — which is what makes the single-repo install story work.

### NOT DOCUMENTED / UNVERIFIED

Carried verbatim from the platform verification. The three that bite hardest are marked **◀**.

1. Whether `${CLAUDE_PLUGIN_ROOT}` expands in SKILL.md frontmatter other than `allowed-tools` (e.g.
   `hooks:`, `paths:`, `shell:`). Only the body and allowed-tools are documented.
2. Whether `${CLAUDE_PLUGIN_ROOT}` expands in agent frontmatter or command frontmatter.
3. Whether the model auto-reads an inlined shared file, or what permission a Read of a plugin-path file
   needs. Docs only say the path is inlined. **◀** *(partially answered by scaffold proof 2, under
   `acceptEdits` only)*
4. Whether `../` relative paths from a SKILL.md body resolve to sibling directories. Not documented;
   loading.md says files outside a copied plugin are not present. **◀**
5. Whether a SKILL.md can reference `${CLAUDE_SKILL_DIR}/../../shared` (not documented; `CLAUDE_SKILL_DIR`
   is the skill subfolder).
6. A canonical JSON Schema URL for plugin.json or marketplace.json. Only the `$schema` key is documented.
   **◀**
7. A maximum skill name length. Charset rules are listed; length is not.
8. A 1024-character description limit. Only 1,536 (description + when_to_use) is documented.
9. Any maximum number of skills, agents, or commands per plugin.
10. Whether the listing budget is per plugin or global. Documented as global: 1% of the context window
    across all skills.
11. The Claude Code version that introduced `${CLAUDE_PLUGIN_ROOT}` in skill content, and the version that
    introduced the 1% listing budget.
12. A supported way to install a plugin directly from a GitHub repo with no marketplace. Not documented;
    `/plugin install owner/repo` fails.
13. Whether `claude plugin test` and `claude plugin tag` do what we need.
14. Whether plugin skill names are globally unique across marketplaces. Only conflict-resolution order is
    documented.
15. Whether the `/skill-doctor` listing fits 15 skills without description truncation at the default
    budget. Depends on the user's context window.

Also unverified by us: the platform facts came via doc fetches returning model-produced extracts, so quoted
wording is not byte-exact. `claude plugin validate` is the authoritative check and is wired into the test
suite for exactly this reason.

---

## 2. Layout

`shared/` sits **inside** the plugin root. This is forced, not chosen: anything outside the root is not
copied on a marketplace install.

```
product-suite/
  .claude-plugin/
    plugin.json                  the manifest
    marketplace.json             the marketplace, same repo, listing this plugin at "./"
  README.md  CONTRIBUTING.md  LICENSE  NOTICE
  shared/
    principles.md                the cross-skill rules, stated once
    vocabulary.md                severity, statuses, closing actions, roles, item types
    contracts/                   qa-dev.md, po-dev.md, pm-ba.md, …
    templates/                   finding.md, and the shared item templates
    references/                  evidence-standard.md, experience.md, docs-conformance.md, gotchas.md
    domains/                     the 27 domain files + README
    hub/                         item model, ownership table, schema, lifecycles
    scripts/                     hub.py, dashboard.py, safe_edit.py, checks, and their tests
  skills/
    hub/ orient/ discovery/ prd/ requirements/ backlog/ delivery/ design/
    architecture/ dev/ qa/ release/ docs-authoring/ launch/ analytics/
  docs/design/                   this document, progress.md, council-review.md, final-report.md
  tests/
    fixtures/                    the two worked engagements
    triggers/                    trigger evals per skill
```

Skills are referenced as `/product-suite:<name>` — namespaced invocation only (§6).

---

## 3. What happens to each existing file

Settled by the brief and the five decisions. `→` means the file moves intact unless noted.

### Stays in `skills/qa/`

| File | Note |
|---|---|
| `SKILL.md` | trimmed **470 → ≤300 lines**. Keeps the prime directive, Steps 0–7, the iteration-gate summary, the computed verdict. The DEV role text, the two-session section and the credentials rules become one-line pointers |
| `references/scope-playbooks.md` | intact, incl. §8b performance |
| `references/test-cases.md` | intact |
| `references/iteration-cycles.md` | phases and gate **word for word**; the register and `qa-state.json` become hub items and generated views (§4, Decision D-5) |
| `references/case-file.md` | intact |
| `assets/*` → `skills/qa/assets/` | agent-brief, ranked-index, test-case-register |
| `references/gotchas.md` | **split**: browser automation, cloud teardown, stateful/clustered testing stay |

### Moves to `shared/`

| From | To | Why |
|---|---|---|
| `references/evidence-standard.md` | `shared/references/` | QA, DEV, design review and analytics all grade evidence |
| `references/experience.md` | `shared/references/` | design and QA both use it |
| `references/docs-conformance.md` | `shared/references/` | QA scope 9 and `docs-authoring` both use it |
| `references/domains/*` (28 files) | `shared/domains/` | PRD, architecture, DEV and QA all need the product class |
| `assets/finding.md` | `shared/templates/` | **split** — severity table extracted to `vocabulary.md` (Decision D-2) |
| `assets/handoff-packet.md` | `shared/contracts/` | it is a contract between two skills |
| `scripts/safe_edit.py` + test | `shared/scripts/` | every skill that edits files |
| `scripts/qa_dashboard.py` + test | `shared/scripts/` | rebuilt on the hub, one dashboard for all skills |
| `gotchas.md`: file-editing, build/toolchain, "builds that pass while shipping a broken artifact", locale, repos/branches, reasoning traps | `shared/references/gotchas.md` | DEV needs these more than QA does |

### Splits

**`references/dev-handoff.md` (290 lines)** → the contract (lifecycle, four invariants, ownership, ticket
and handback packets, disputes, live-session rules, the event log) to `shared/contracts/qa-dev.md`; the DEV
procedure (how to triage, fix, hand back) to `skills/dev/`.

**`assets/finding.md` (115 lines)** → template to `shared/templates/finding.md`; the severity table and the
closing-action taxonomy to `shared/vocabulary.md`. Retargeted references: `experience.md:214` ("the rule
under `finding.md`'s table") and the severity-inheritance rule. A grep for other by-name references to "the
table" runs as part of the cross-reference check.

### Moves to `skills/dev/`

`references/fix-phase.md` in full, plus the DEV half of `dev-handoff.md`.

---

## 4. The hub

Built first; everything depends on it.

### Item types

`initiative` · `insight` · `prd` · `requirement` · `decision` · `story` · `design` · `adr` · `case` ·
`finding` · `fix` · `release` · `doc` · `launch` · `metric` · `risk` · `cleanup`

Every item carries: a stable id never reused or renumbered · type · state · owner role ·
`provenance: authored | derived | reconstructed` · links · full history.

Traceability chain:

```
initiative → prd → requirement → story → design/adr → case → finding → fix → release → metric
```

### The general invariant

**The producer claims; a different role accepts.** This is product-qa's `FIXED`/`CLOSED` rule generalised,
and it is the hub's reason for existing. Instances:

| Producer claims | Acceptor decides |
|---|---|
| DEV: `FIXED` | QA: `CLOSED` |
| DEV: story `DONE` | PO: `ACCEPTED`, and only when its linked cases pass |
| PM: PRD `DRAFTED` | sponsor / Head of Product: `APPROVED` |
| QA: severity | operator: priority |
| BA: requirement `SPECIFIED` | stakeholder: `AGREED` |
| designer: design `PROPOSED` | design lead + PO: `ACCEPTED` |
| analyst: metric `READ` | PM: `INTERPRETED` |

`shared/hub/ownership` maps role → item types it may create → transitions it may make. Adding a role is
new rows, never new code paths. The qa-dev contract's states and four invariants map onto this exactly;
one test per invariant.

### Storage and concurrency

Many writers: parallel agents, sessions hours apart, different machines via git.

- **One append-only event file per actor:** `hub/events/<role>/<actor>.jsonl`. No two writers ever share a
  file, so there is no lock and a git merge of two appends is trivial.
- **State is a fold** over all events, ordered by `(ts, actor, seq)` with `seq` a per-actor monotonic
  counter. Ties break on `actor` then `seq`, so the fold is deterministic regardless of file read order.
- **Clock skew:** `ts` is advisory. Causality comes from `seq` per actor and from explicit `after` links on
  transitions. A transition whose `ts` precedes the event it depends on is applied in causal order and
  flagged by `validate` as skew, not reordered silently.
- **Duplicates:** every event has an `event_id` (actor + seq). A repeated `event_id` is ignored by the fold
  and reported by `validate`. Replaying an import twice is therefore a no-op.
- **Schema version** on every event; the fold refuses an unknown major.
- **Generated views** (`qa-state.json`, `fix-state.json`) carry a `generated_from` header naming the hub
  state they were built from. A view without a matching hub is **not truth** — that is the import branch.
  `hub.py validate` flags stale views. This is Phase 0 applied to artifacts: a view whose header does not
  match is the same class of error as a build that does not contain the fix it claims.

### `shared/scripts/hub.py` — the only write path

Stdlib only, Windows and Linux. `init` · `profile` · `add` · `move` · `link` · `note` · `show` · `list`
(`--mine`, `--waiting-on <role>`, `--type`, `--state`) · `validate` · `import` (old report dirs, ids
unchanged) · `dashboard` · `status`.

Forbidden transitions are rejected with the rule that refused them. Skills update items **only** through
this CLI, and every SKILL.md says so.

### Dashboard

Generated, self-contained HTML, works over `file://`, read-only, no authored content. Views: all items by
type and state · per role "mine" and "waiting on me" · lifecycle board · traceability story → release ·
time-in-state and reopen counts · risks and decisions awaiting the operator · the release verdict.

Reuses `qa_dashboard.py`'s computed-verdict logic, its `NO VERDICT` default and its 25 tests. An adapter
interface for Jira / Azure DevOps / GitHub Issues is defined as an interface only.

---

## 5. The skills

15 skills. Names drop the `product-` prefix since invocation is namespaced. Each ≤300 lines, detail in its
own `references/`, a role, the hub items it reads and writes, behaviour for **new** and **existing**
products, a template where it produces a document, and a contract in `shared/contracts/` where it feeds
another skill.

| Skill | Role(s) | Reads | Produces |
|---|---|---|---|
| `hub` | everyone | hub | status answers, dashboard |
| `orient` | lead of any skill | repo, docs, live product | product profile + baseline, `conventions.md` |
| `discovery` | UX researcher, PM | initiative | `insight`, interview guides, synthesis |
| `prd` | PM, Head of Product | insights, profile | `prd`, `metric` |
| `requirements` | BA | prd, legacy systems, stakeholders | `requirement`, process maps, `decision` |
| `backlog` | PO | prd, requirements | `story` with acceptance criteria as oracles |
| `delivery` | delivery manager, leads | whole hub | plan, milestones, `risk`, status reports |
| `design` | designer, design lead | stories | `design`, flows, design-review findings |
| `architecture` | tech lead, EM | stories, profile, domains | tech design, `adr` |
| `dev` | engineers | stories, findings, adrs | code, `fix`, handback packets |
| `qa` | QA, QA lead | story criteria, builds | `case`, `finding`, verdict |
| `release` | EM, QA lead, PM | hub verdict, open items | go/no-go memo, release notes, `release` |
| `docs-authoring` | technical writer | stories, release, product | `doc`, user/admin docs |
| `launch` | PMM, content writers | prd, release | positioning, launch plan, copy, `launch` |
| `analytics` | data/product analyst | metrics, release | metric readings, post-launch review |

Leads get no separate skills; each skill carries a short "for the lead" section covering review, approval
and team-level views.

**Quality bar.** Only `qa` and the DEV procedure come from real engagements. The other 13 are written from
first principles, which `CONTRIBUTING.md` warns against — so each is marked `status: draft` in its own
README, made concrete (field lists, templates, worked mini-examples) rather than generic, and ends with its
open questions.

### Description budget

Measured, not guessed. The scaffold showed ~80 tokens always-on for a skill with a 15-character
description. The documented cap is 1,536 characters for `description` + `when_to_use` combined, but the
binding constraint is the **global listing budget of 1% of the context window**, which on overflow *drops
descriptions* — starting with the least-invoked skills, i.e. exactly the new drafts.

**Ceiling: 600 characters per description**, each keeping its "not for…" line. Justification: 15 × 600 ≈
9,000 characters ≈ 2,300 tokens always-on, which is ~1.2% of a 200k window — under the 1% budget only if
other plugins are modest, so the test asserts the measured figure rather than the arithmetic.
`tests/test_description_budget.py` runs `claude plugin details` and fails if always-on exceeds **2,500
tokens**.

---

## 6. Hard rules for this plugin

**The variables rule.** SKILL.md body text may contain `${CLAUDE_PLUGIN_ROOT}/…`, because it is expanded at
load (proved, §1). **No skill may ever tell the model to type `$CLAUDE_PLUGIN_ROOT` into a shell** — the
variable is not in the environment of model-run Bash. A lint fails on `$CLAUDE_PLUGIN_ROOT` inside any
shell code block, and on any `../` path escaping a skill or the plugin root.

**Namespaced invocation only.** Documentation never shows the bare `/qa` form. Bare names work only "unless
another command already uses that name", resolved by an origin order we do not control — and `docs` already
collides with `anthropic-skills:docs` in a default install, which is why that skill is named
`docs-authoring` (Decision D-7). The lint fails on a bare-form invocation in our own docs.

**The repo cannot lie about itself.** Replacing the old "update N places" rule: `shared/scripts/check_*.py`
assert that every domain file is registered everywhere it must be, that counts in prose match the actual
file listing, that every cross-reference resolves **as the installed plugin sees it**, that every domain
file has its seven headings, that no prose line exceeds 110 columns, and that no real hostname, path,
tenant id or key appears in an example. That last check has already caught a live violation
(`E:/Personal/projects/progress-reports` in the state example).

**Evals use the built-in harness.** `claude plugin validate`, `claude plugin test` and `claude plugin eval`
(with `claude plugin eval init`) for trigger and behaviour evals. Python tests are kept only for `hub.py`,
the dashboard and `safe_edit.py`. Trigger evals cover auto-triggering from natural prompts *and*, as a
separate case, explicit `/product-suite:<skill>` invocation.

---

## 7. Install and migration

One repo is both marketplace and plugin:

```bash
/plugin marketplace add faysalim/<repo>
/plugin install product-suite@product-suite-market
```

`--plugin-dir` is documented as the **contributor route only**. There is no documented way to install from
a GitHub repo without a marketplace (NOT DOCUMENTED #12).

**Migration is mandatory reading in the README.** Anyone who installed the old skill at
`~/.claude/skills/product-qa` must remove it: a plugin skill and a standalone skill of the same name
**both load**, so the two copies will both trigger and the method will be read twice, from two versions.

---

## 8. Decisions

Every choice that would normally have been approved. `NEEDS FAISAL` means review it.

| id | Decision | Reason | Rejected alternative |
|---|---|---|---|
| D-1 | `shared/` inside the plugin root, referenced as `${CLAUDE_PLUGIN_ROOT}/shared/…` | Proved in a cold session (§1). Anything outside the root is not copied on marketplace install | Sync-copy fallback — unnecessary; relative `../` — undocumented and breaks on copied installs |
| D-2 | `finding.md` split; severity table canonical in `vocabulary.md` | One definition used by every skill and the dashboard | Duplicating the table — guarantees drift |
| D-3 | "Update N places" replaced by executable checks | The repo should be unable to lie about itself, not merely told not to | A longer CONTRIBUTING list |
| D-4 | `gotchas.md` "builds that pass…" and "reasoning traps" → `shared/` | Both are about build artifacts and debugging; DEV needs them more than QA | Leaving them in QA |
| D-5 | Step 0 reads the hub, not `qa-state.json`; all five branches re-pointed; iteration number is an explicit hub event; views carry `generated_from` | The hub is the source of truth, and a view without a matching hub is a Phase 0 error | Keeping the file as truth — two sources of truth |
| D-6 | Skill names drop `product-` | Invocation is namespaced; auto-trigger depends on descriptions | Keeping the prefix — redundant with the namespace |
| D-7 | `docs` → **`docs-authoring`** | `docs` collides with `anthropic-skills:docs` today, not hypothetically | `docs` — a user typing `/docs` gets Anthropic's skill |
| D-8 | Description ceiling 600 chars, tested at ≤2,500 tokens always-on | The listing budget silently drops descriptions of least-used skills | The documented 1,536 cap — not the binding constraint |
| D-9 | Marketplace and plugin manifests share one `.claude-plugin/` | Confirmed working by `claude plugin validate` | Two repos — defeats single-repo distribution |
| D-10 | Event `seq` per actor + `event_id` for dedupe; `ts` advisory | Clock skew across machines must not reorder causality | Timestamp ordering alone — reorders under skew |
| D-11 | **`NEEDS FAISAL`** — a README of ≥40 words and a square PNG icon are needed for plugin-directory submission; the icon is fixed at first submission and cannot be changed later | Surfaced by `claude plugin validate`, not in the platform docs | — *Recommendation: write the README now; defer the icon until you choose one, since it is one-shot* |
| D-12 | **`NEEDS FAISAL`** — proof 2 (no permission prompt) was run under `--permission-mode acceptEdits` | A cold run in default mode needs a human to observe the prompt | — *Recommendation: you run the probe once in the morning; command in the final report* |
| D-13 | **`NEEDS FAISAL`** — copy semantics unproven; a local-path marketplace loads in place | Would need a git-sourced marketplace to exercise | — *Recommendation: accept the lint as the guard; or push a throwaway repo and install from it* |

---

## 9. Open questions

- Whether `claude plugin test` and `claude plugin eval` cover trigger evals in the shape Step 6 wants, or
  whether a thin wrapper is needed. Resolved during the eval build; recorded in `progress.md`.
- Whether 15 skills in one plugin survives the listing budget on a smaller context window. Measured, not
  predicted — the budget test is the gate.
- Whether the three next-up domain files (real-time collaboration, CMS, feature flags) belong in this
  restructure or a later one. Current plan: not in this one; the restructure should not also grow the
  method.
