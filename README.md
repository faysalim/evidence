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

> **Known limitation, measured.** Claude Code gives the whole skill listing a character budget of 1% of the
> model's context window, **shared across every skill you have** — 8,000 characters on a 200k-token model.
> This plugin's 15 descriptions are ~7,300 of that on their own, and when the listing overflows Claude Code
> **drops descriptions**, starting with the least-invoked skills. In a session with other plugins installed,
> 7 of these 15 had no description at all, and auto-triggering worked reliably only for `qa`, `dev`, `hub`
> and `orient`. Until that is resolved, **invoke the other eleven explicitly.**
> `tests/test_description_budget.py` fails on purpose until it is fixed, rather than reporting green over
> it.

### Migrating from the standalone `product-qa` skill

**If you installed the old skill at `~/.claude/skills/product-qa`, remove it.**

```bash
rm -rf ~/.claude/skills/product-qa
```

On Windows, delete `%USERPROFILE%\.claude\skills\product-qa`.

Both will load — the names differ (`product-qa` versus `evidence:qa`), so they do not collide outright,
which is the problem: their **descriptions** overlap heavily, so a request like "QA this release" can route
to either, and you cannot tell from the answer which version of the method you got. The old skill's content
is all still here: the QA method is `skills/qa/`, and what more than one role needs moved to `shared/`.

Your existing report directories still work. `python shared/scripts/hub.py import <report-dir>` reads an
old `qa-state.json`, **preserves every finding id**, and marks everything `provenance: reconstructed` — it
does not inherit the old verdicts, because nobody verified them here.

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

## The 15 skills

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
| `release` | EM, QA lead, PM | the computed go/no-go, release notes |
| `docs-authoring` | technical writer | docs written from behaviour, then verified claim by claim |
| `launch` | PMM | positioning and copy where every claim links to a passing case |
| `analytics` | analyst | metric readings, the post-launch review |

`qa` and `dev` carry the original engagement's provenance. **The other thirteen are marked
`status: draft`** in their own README, because they were written from first principles — which is exactly
what `CONTRIBUTING.md` warns against. The warning is on the tin rather than hidden.

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
  domains/             27 product classes + index
  hub/model.json       item types, states, who may move them
  scripts/             hub.py, dashboard.py, safe_edit.py, check_repo.py, tests
skills/                the 15 skills
evals/                 trigger evals for the built-in harness
tests/                 fixtures, trigger corpus, budget test
docs/design/           design doc, decisions, progress, final report
```

## License

Apache-2.0 — see `LICENSE` and `NOTICE`. Use it commercially, adapt the domain files to your own product,
keep your adaptations private. The only obligation is attribution.

## Provenance

Distilled from a four-repo, full-business QA engagement, then reviewed adversarially against product
classes the original engagement never touched, then restructured into a plugin covering the whole
lifecycle. Each review changed the design rather than decorating it: the state, upgrade and experience
scopes exist because the first version had no concept of whether data was still correct after a fault; the
computed verdict and the calibration row exist because a later review showed that a register nothing can
refuse is decoration.
