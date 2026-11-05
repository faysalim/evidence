# evidence

A Claude Code plugin for product development: **one skill per deliverable, every role covered, all sharing
one work-item hub and one dashboard.** Evidence-first, and honest about what it did not check.

It exists because of a measurement. The QA run immediately before the engagement this was distilled from
reported **zero bugs**. It had checked HTTP status codes, that pages loaded, and that links resolved, and
every check passed. At that moment the product's entire trial-key flow was broken: the issuing endpoint
returned 403, the delivery email was mis-branded plain text, there was no sales copy at all, and a deploy
pin meant new code was not serving. Every one of those was reachable in minutes by *requesting a key*.
None was reachable by *checking that the page loads*. The re-run using this method produced **37 ranked
findings**, two of them blockers.

That is a QA story, but the failure is not QA's. A PRD whose success metric has no denominator, an
acceptance criterion nobody else can grade, a design that specifies only the happy path, a launch claim
nobody measured, and a status report written by the person whose work it describes are all the same
mistake: **a response mistaken for the thing.** So the method was generalised across the lifecycle, and
the rules are stated once in `shared/principles.md` rather than fifteen times.

## Install

```
/plugin marketplace add faysalim/evidence
/plugin install evidence@evidence-market
```

Skills are then invoked as `/evidence:qa`, `/evidence:dev`, `/evidence:hub` and so on. **Always use the
namespaced form.** The bare form does resolve to these skills today — that was measured, not assumed — but
it resolves by an origin order this plugin does not control, so which skill you get depends on what else
you have installed. `docs` already collides with a skill that ships by default, which is why the writer
skill here is `docs-authoring`.

Much of the time you will not invoke anything: the descriptions are written to trigger on ordinary requests
like "QA this release", "write acceptance criteria for this story", or "what is waiting on me".

> **Read this before you rely on auto-triggering.** Claude Code gives the whole skill listing a
> character budget — 1% of the model's context window by default, **shared across every skill you
> have**, not just this plugin's. When it overflows, Claude Code *drops descriptions*, starting with
> the least-invoked skills, and nothing tells you it happened. On the machine this was built on the
> listing was 37,942 characters against a 30,000 budget, and 7 of these skills had no description
> at all.
>
> **One line fixes it, for every plugin you have:**
>
> ```json
> { "skillListingBudgetFraction": 0.02 }
> ```
>
> in `~/.claude/settings.json` — or, **for a team, in managed settings rather than left to each
> person**, which is the right place for it: the setting is per-machine, so one engineer applying it
> does nothing for the rest and the failure is silent for everyone else.
>
> That was measured, not guessed: the default `0.01` overflowed, `0.013`
> was the first value that fit, and `0.02` leaves 22,000 characters of headroom. `/skills` to disable
> what you do not use works too.
>
> This plugin is 9,579 characters of that listing across 18 skills — a fifth of the problem on that
> machine, and **removing it entirely would still leave the listing over budget.** The full
> measurement, including the two remedies that did not work, is in `docs/design/listing-budget.md`.
> `tests/test_description_budget.py` fails on purpose against the tighter 200k-window figure, because
> a plugin this size should keep paying attention to what it costs everyone else.

### Contributor install

```bash
git clone https://github.com/faysalim/evidence.git
claude --plugin-dir ./evidence
```

That loads the plugin in place for one session, which is the right loop for editing it. It is **not** the
way to use it day to day: a `--plugin-dir` plugin is read in place while a marketplace install is copied,
so a path that escapes the plugin root works for you and breaks for everyone else. `check_repo.py lint`
exists to catch exactly that.

## The ten principles

Stated once in `shared/principles.md`, linked from every skill, and most of them enforced rather than
encouraged:

1. **Do the thing. Don't check that the thing responds.** Then go back and check it is still there.
2. **Every number has a denominator.**
3. **An oracle exists outside the product and outside your own judgement** — and predates the run.
4. **Every finding and claim states what it does NOT claim.**
5. **Corrections go in writing.**
6. **Verdicts are computed, never written. `NO VERDICT` is the default.**
7. **The producer claims; a different role accepts.**
8. **Never put a secret in an artifact.**
9. **The cleanup ledger**, verified by re-listing rather than by a delete call's exit code.
10. **Reality beats paperwork** — when docs, tickets and code disagree, report the disagreement.

Each one says what enforces it. Principle 7 is `shared/hub/model.json`; principle 6 is the dashboard's
verdict function; principle 8 is a repo check that has already caught a live violation.

## The 18 skills

| Skill | Role | Produces |
|---|---|---|
| `hub` | everyone | status answers, the dashboard |
| `orient` | any lead | the product profile and baseline, `conventions.md` |
| `discovery` | researcher, PM | insights with evidence, sample size, and what they do not show |
| `prd` | PM, Head of Product | the PRD, and metrics defined with denominators |
| `requirements` | BA | numbered requirements, process maps with exceptions, decisions |
| `backlog` | PO | stories whose acceptance criteria are oracles |
| `delivery` | delivery manager | generated status, milestones, the RAID log |
| `design` | designer, design lead | flows and every state, provable review findings |
| `architecture` | tech lead | technical design, ADRs with a falsifier |
| `dev` | engineers | code, fixes, handback packets |
| `qa` | QA | test cases, findings, the coverage denominator |
| `ops-readiness` | DevOps / platform / SRE | rollback rehearsed, alerts proven, on-call named — checkpoints the verdict reads |
| `security-review` | security, privacy, compliance | the sign-offs a release needs, each with a named signer and a stated boundary |
| `support-readiness` | support / customer success | known issues from the findings nobody fixed, and the post-launch watch plan |
| `release` | EM, QA lead, PM | the computed go/no-go, release notes |
| `docs-authoring` | technical writer | docs written from behaviour, then verified claim by claim |
| `launch` | PMM | positioning and copy where every claim links to a passing case |
| `analytics` | analyst | metric readings, the post-launch review |

Every skill declares `roles:` and `status:` in its own frontmatter, and `check_repo.py coverage`
enforces all of it: that every role in `shared/hub/model.json` has a skill, that no skill claims a role
the model does not have, that no skill omits either field, and that **any count stated in this README
matches the declarations.** Three levels, and a skill may not claim more than it has earned:

| Status | Means | Skills |
|---|---|---|
| `proven` | Carries a real engagement's provenance, where its absence cost something | `qa`, `dev` |
| `exercised` | Run against a real product by its author, defects found and fixed. **Weaker than proven** — principle 7 says the author does not grade their own work | `hub`, `orient`, `delivery`, `release`, `docs-authoring`, `launch`, `requirements`, `architecture`, `prd`, `analytics`, `backlog`, `design`, `discovery` |
| `draft` | Written from first principles, never run. Exactly what `CONTRIBUTING.md` warns against | **None.** All fifteen have been run against a real product |

That last count is checked, not asserted. It had to be: this README claimed thirteen, was corrected to
eleven, and both were wrong, because `orient` carried no marker at all and so was invisible to a hand
count. A reader infers "proven" from the absence of a warning, which is why the absence is now a
build failure. The check also compares each skill's frontmatter against the status banner in its own
body, after five files were found claiming `exercised` in one and `draft` in the other.

**What `exercised` actually bought.** Running them against a live codebase — a real distributed data
store, its real docs, its real public comparison page and its own certification artifacts — found
twenty defects in the skills themselves, including the largest one in the suite: `orient` promised
that *every* downstream skill reads the profile and `conventions.md`, and two of fifteen did. Five
referenced neither, which are exactly the skills that would otherwise guess the product class and
impose vocabulary on a team. Every defect is listed in `docs/design/exercise.md` with what it broke.

The two drafts are not untested — every documented command in all fifteen is executed by
`tests/test_documented_commands.py`, every state they name is checked against the model, and the
profile contract is enforced for all of them. They have simply never been pointed at a real product,
and that is a different claim.

Leads do not get separate skills; each skill has a short "for the lead" section.

## The hub

Every skill reads and writes one work-item hub, through one CLI, and nothing else:

```bash
python shared/scripts/hub.py status                     # which iteration is this?
python shared/scripts/hub.py list --waiting-on OPERATOR # what only a human can unblock
python shared/scripts/hub.py validate                   # is the hub internally consistent?
python shared/scripts/hub.py dashboard                  # render the local HTML dashboard
```

Those four are read commands. Writing needs an actor and a role, because a claim is attributable
or it is anonymous:

```bash
python shared/scripts/hub.py --actor you --role QA init --engagement my-product
python shared/scripts/hub.py --actor you --role QA iteration 1
python shared/scripts/hub.py --actor you --role QA add case S1-01 -f action="..." -f oracle="..."
```

`/evidence:hub` has the six-command first engagement and the conventions the verdict reads.
The options work before or after the subcommand.

**Storage is one append-only log per actor** — `hub/events/<role>/<actor>.jsonl` — so no two writers ever
share a file. State is a deterministic fold over every event. There is no lock, because a locking protocol
between two agents working hours apart is a fiction, and a git merge of two appends is a concatenation
rather than a conflict. `qa-state.json` and `fix-state.json` survive as **generated views** carrying a
`generated_from` header; a view that disagrees with the hub is not a second opinion, it is a stale
artifact, and `validate` says so.

Seventeen item types form one traceability chain:

```
initiative → prd → requirement → story → design/adr → case → finding → fix → release → metric
```

### What the hub refuses

The reason it is a hub and not a folder of markdown. All of this is enforced in `shared/hub/model.json`
and covered by tests:

- **DEV may claim `FIXED`; only QA may `CLOSE`.** Two different claims, two parties, two kinds of evidence.
- **The author does not grade their own work** — and the guard is on the *actor*, not the role, so wearing
  the other hat does not help.
- **A PO cannot accept a story whose linked cases have not passed.**
- **`NEW` is not a resting state.** A finding handed over and left untriaged is reported.
- **Severity is QA's field; priority is the operator's.** Each refuses the other.
- **A mitigation needs its evidence**; "we have a plan" is not a mitigation.
- **Cleanup is only torn down with a re-listing** to prove it.

## The dashboard

```bash
python shared/scripts/hub.py dashboard
```

Self-contained HTML, works over `file://`, read-only, **nothing authored**. Per release: the computed
verdict with its condition table, every item by type and state, per-role "waiting on them", the operator's
queue, traceability from initiative to metric, and time-in-state with reopen counts.

If it is not in the event logs it is not on the page, and where a verdict cannot be computed it prints
`NO VERDICT` and names the condition that had no rows. There is **no percent-complete anywhere**: a
percentage of an unknown total is the denominatorless number principle 2 forbids, and in delivery it is
the specific number that lets a project be 90% done for a quarter.

## Two worked engagements

`tests/fixtures/` holds two complete engagements, built **only** through `hub.py` and committed with their
rendered dashboards — so they are a worked example and an integration test at once.

`existing/` is the full arc on a product that already has customers: 24 items, 86 events, orient through
to a metric reading. Its verdict is **NOT GREEN**, on three conditions, and that is the point: a `NOT RUN`
case guards a critical class, so the absence denies the verdict instead of being invisible. The operator
then ships anyway, in their own words, recorded and attributed — because shipping and being green are two
different facts.

`new/` is a greenfield tool where most states are honestly "not measured yet", and QA finds a critical
cross-team leak in the CSV export that the UI correctly hides.

## Tests

```bash
python -I shared/scripts/test_hub.py            # 70 checks: the hub, its invariants, the fold
python -I shared/scripts/test_safe_edit.py      # 25 checks
python -I shared/scripts/test_qa_dashboard.py   # 25 checks
python -I shared/scripts/check_repo.py          # 7 repo self-checks
python -I tests/test_enforcement_claims.py      # every "Enforced:" claim is backed by a refusal
python -I tests/test_description_budget.py      # the measured always-on cost
python -I tests/triggers/check_overlap.py       # trigger overlap, from the descriptions
python -I tests/fixtures/build.py --all         # rebuild both fixtures end to end
claude plugin validate .
claude plugin eval evidence --eval-dir evals
```

The repo checks replace the old "a PR must update these four places" rule. A rule that depends on
remembering four places fails silently; a check fails loudly. They assert that every
`${CLAUDE_PLUGIN_ROOT}` path resolves as an installed plugin would see it, that no shell block uses a
variable absent from the shell's environment, that every domain file is registered everywhere, that counts
in prose match the file listing, and that no real hostname or path appears in an example.

## Repository layout

```
.claude-plugin/        plugin.json and marketplace.json -- this repo is both
shared/
  principles.md        the ten rules, each saying what enforces it
  vocabulary.md        severity, closing actions, states, roles, verdicts
  contracts/           qa-dev.md, the handoff packets
  templates/           the finding template
  references/          evidence-standard, experience, docs-conformance, gotchas
  domains/             30 product classes + index
  hub/model.json       item types, states, who may move them
  scripts/             hub.py, dashboard.py, safe_edit.py, check_repo.py, tests
skills/                the 15 skills
evals/                 trigger evals for the built-in harness
tests/                 fixtures, trigger corpus, budget test
docs/design/           design doc, decisions, progress, final report
```

## License

MIT — see `LICENSE`. Use it commercially, adapt the domain files to your own product,
keep your adaptations private. The only obligation is attribution.

## Provenance

Distilled from a four-repo, full-business QA engagement, then reviewed adversarially against product
classes the original engagement never touched, then restructured into a plugin covering the whole
lifecycle. Each review changed the design rather than decorating it: the state, upgrade and experience
scopes exist because the first version had no concept of whether data was still correct after a fault; the
computed verdict and the calibration row exist because a later review showed that a register nothing can
refuse is decoration.
