# product-qa

A Claude Code skill for end-to-end QA of a real product — evidence-first, multi-iteration, and honest
about what it did not test.

It exists because of a measurement. The QA run immediately before the engagement this was distilled from
reported **zero bugs**. It had checked HTTP status codes, that pages loaded, and that links resolved, and
every check passed. At that moment the product's entire trial-key flow was broken: the issuing endpoint
returned 403, the delivery email was mis-branded plain text, there was no sales copy at all, and a deploy
pin meant new code was not serving. Every one of those was reachable in minutes by *requesting a key*.
None was reachable by *checking that the page loads*.

The re-run using this method produced **37 ranked findings**, two of them blockers.

## The prime directive

> **Do the thing. Don't check that the thing responds.**

And for anything that keeps data, that sentence is only half of it:

> **Then go back and check the thing is still there.** A write that returned OK is a *response*; the thing
> is the value being present — on every replica the product promised, after the failure the docs say it
> survives, after the upgrade, a week later. An acknowledged write is not a durable write until you have
> read it back after the failure.

Everything else in this repository is machinery for making those two sentences enforceable by someone who
is not you.

## Install

The skill is self-contained: Markdown plus one Python script, no dependencies to install.

```bash
# user-level — available in every project on the machine
git clone https://github.com/faysalim/product-qa-skill.git ~/.claude/skills/product-qa

# or project-level — checked in with one repo's code
git clone https://github.com/faysalim/product-qa-skill.git .claude/skills/product-qa
```

On Windows the user-level path is `%USERPROFILE%\.claude\skills\product-qa`. **The destination
directory must be `product-qa`**, not the repository name — Claude Code matches it against `name:` in
`SKILL.md`'s frontmatter, which is why the commands above name their destination explicitly.

Update with `git -C ~/.claude/skills/product-qa pull`.

Claude Code discovers it from `SKILL.md`'s frontmatter and loads it on its own when a request looks like
product testing — "QA this release", "test my product before I ship", "check the docs match what it
actually does", "find what's broken". `/product-qa` invokes it explicitly.

## What it actually does

Eight steps, in `SKILL.md`:

| Step | What it forces |
|---|---|
| **0 — Iteration and mandate** | Which round is this, what is in bounds, what is explicitly not. Read from on-disk state, never guessed. |
| **1 — Ground truth** | What is *actually deployed* — build ids, image digests, per-node versions — before a single test. A finding against the wrong build is noise. |
| **2 — Split the scopes** | Twelve scope families, applicability declared per product, one agent per applicable family, capped at 11. |
| **3 — Design the cases, then do them** | Every case carries an **oracle** — and a case whose oracle is the product's own report of itself is not a case. Per-surface evidence standards: status 200, a green build and `/health: ok` are listed as evidence that looks strong and is not. |
| **4 — Write each finding** | Exact repro, raw evidence, build identity, and a closing action: `CODE / DEPLOY / RELEASE / DATA / PROCURE / DECIDE / INVESTIGATE`. |
| **5 — Rank and consolidate** | Severity by worst consequence, not by the section it was filed in. |
| **6 — Correct yourself in writing** | Retractions belong in the report, with what was wrong and how it was found. |
| **7 — Cleanup ledger** | Every account, key, container and shared quota you touched, and its disposition. |

## What was tested, not only what broke

A report of findings alone tells you what broke and nothing about what held, so you cannot tell a surface
that was exercised hard from one nobody opened. Every run therefore publishes a **test-case register** —
one row per thing that can independently break, each with the action, its oracle, its result
(`PASS / FAIL / BLOCKED / NOT RUN / LONG`) and its evidence.

Two rules keep it from becoming a wall of green checkboxes, which would be the "0 bugs" report with a
bigger table:

- **A case whose oracle is the product's own report of itself is not a case.** `/health: ok` grades
  nothing, a green build grades nothing, and the cluster's own `missing: 0` grades nothing — your own
  ledger of what the product acknowledged, diffed against what you can read back, does.
- **A `PASS` with no evidence is a `NOT RUN`**, and gets written as one.

The cases are **derived, not invented** — from the domain file's fault catalogue and its named defect
classes, the scope playbooks, the documentation claims, the surface enumerated from code, and every prior
finding's repro — and the derivation is published beside the count. `214 cases` is a boast; `214 cases: 96
fault-catalogue entries, 41 defect classes, 38 playbook steps, 27 doc claims, 12 from the route table and
env reads` is a number someone can argue with, which is the point.

The register also makes later iterations cheap: Phase 1 is the failed cases re-run verbatim, Phase 2 is the
passing cases inside the diff's blast radius. A case is never retired for passing — it is the regression
suite.

Plus a **documentation-conformance scope** that runs both directions — forward (every published claim
executed verbatim) and reverse (the product's surface enumerated from code and subtracted from the docs) —
because a coverage number without a stated denominator is not a number.

## Scope families

1. Acquisition surface · 2. Primary product, per platform · 3. Control plane · 4. Deployment ·
5. Entitlement lifecycle · 6. Secondary products and SDKs · 7. Telemetry and privacy · 8. Security and
abuse · 9. Documentation conformance · **10. State: correctness and durability under fault, time and
concurrency** · **11. Upgrade, migration and rollback** · **12. Experience and diagnosability**

Inapplicable families cost zero agents and are reported as `N/A` with one line of reasoning, so a reader
can see the omission was chosen rather than missed.

## Domain files

The method never changes between product classes. What changes is which families apply, what "do the
thing" means concretely, which faults are worth injecting, what first success is, and how severity maps.
`references/domains/` carries that for twenty-seven classes:

**Data and state** — distributed database · relational database · message broker / streaming · ETL
pipeline · file sync and storage · backup and recovery · search and ranking

**Applications** — multi-tenant SaaS · CRM · mobile app · desktop app · AI / model-backed feature ·
scheduling and booking

**Education** — AI tutor (across levels) · education platform / LMS

**Money and commerce** — payments · billing and metering · e-commerce and marketplace · licensing server

**Platform and infrastructure** — API platform · identity and SSO · secrets and PKI · messaging delivery ·
workflow engine · observability platform · infrastructure operator / IaC · embedded and firmware

Each file names that domain's version of the directive. A sample:

- *"'Available' is this domain's HTTP 200."* — distributed database
- *"'Run succeeded' is this domain's HTTP 200."* — data pipeline
- *"`lag: 0` is this domain's HTTP 200 — and it is also exactly what a consumer that has skipped records
  reports."* — message broker
- *"A good answer to the demo prompt is this domain's HTTP 200 — and here a single passing run is not weak
  evidence, it is no evidence at all."* — AI feature
- *"A connected agent is this domain's HTTP 200 — and a false green here is not a defect in the product, it
  is the product failing at its only job."* — observability
- *"A helpful-sounding reply is this domain's HTTP 200 — a tutor that gives answers is indistinguishable
  from one that teaches until you measure it."* — AI tutor
- *"`Backup completed successfully` is this domain's HTTP 200. The restore is the entire product."* —
  backup and recovery
- *"`202 Accepted` is this domain's HTTP 200 — and `delivered` means a receiving server took it, not that a
  human will ever see it."* — messaging delivery

Each also lists its **defect classes by name**, because an unnamed defect class is one nobody looks for,
and declares its usual agent count so the budget is checked before the operator is asked for more.

## Later iterations

A second run is not a second first run. `references/iteration-cycles.md` defines the gate:

```
Case review  →  Phase 0  build identity  →  Phase 1  verify the fixes  →  Phase 2  regression
                                                                               ↓
                                                                   all pass? ──┴── no → stop, report, no sweep
                                                                               │
                                                                              yes
                                                                               ↓
                                                               Phase 3  full sweep
```

Phases 0–2 are cheap and Phase 3 is not; that asymmetry is the whole design. Iteration state lives in a
`qa-state.json` finding register on disk, and **agents are told which phase they are in — they never infer
it**, because an agent that guesses wrong sweeps when it should be verifying.

## QA and Dev as two sessions

A QA session and the dev session that fixes what it found share no conversation, no memory and often no
machine — so everything between them is an artifact on disk. That is not a limitation to work around; it is
the corporate arrangement, and it is better than one session doing both, because **a fix is never verified
by the author of the fix.**

`references/dev-handoff.md` defines the mechanism. The same skill serves both sides; Step 0 establishes
which role you are, since they have opposite permissions.

| The classic failure | What makes it mechanically impossible |
|---|---|
| Findings that are neither accepted nor rejected; they rot | `NEW` is not a resting state — every finding leaves it with a reason |
| Dev marks it fixed; it ships broken | Dev may claim `FIXED`. **Only QA may `CLOSE`** |
| "Works as designed" ends the conversation | A design claim must cite documentation; if undocumented, the finding converts to a doc finding rather than closing |
| The fix handles the reported input only | The acceptance criterion ships with the ticket — and the adversarial variant is named as a *class of input, not a value* |
| QA re-tests a build that does not contain the fix | The handback is returned unread unless it names a digest per component |
| Both sessions edit one ledger and lose each other's work | Two files, one writer each (`qa-state.json` is QA's, `fix-state.json` is Dev's), joined by finding id |

The link that pays twice: **QA's case is the spec, Dev's regression test is its automation**, with the
oracle copied into the test verbatim. Cases Dev has automated stop needing a human run, so the engagement
gets cheaper every round instead of more expensive.

## Repository layout

```
SKILL.md                           the method — read first
references/
  evidence-standard.md             what counts as proof, per surface
  test-cases.md                    what a case is, where cases come from, the denominator
  scope-playbooks.md               the twelve families, with steps
  docs-conformance.md              two-way documentation coverage
  iteration-cycles.md              phases, the gate, the finding register
  dev-handoff.md                   QA and Dev as two sessions: roles, ledgers, lifecycle
  experience.md                    UX as a measurement, not a taste
  gotchas.md                       traps that each cost a cycle
  fix-phase.md                     when report-only is lifted
  case-file.md                     one worked engagement, with real numbers
  domains/                         twenty-seven product classes + README index
assets/
  test-case-register.md            what was exercised, its oracle, its result
  handoff-packet.md                QA -> Dev ticket, Dev -> QA handback
  finding.md                       the finding template
  ranked-index.md                  the report template
  agent-brief.md                   what a scope agent is told
scripts/
  safe_edit.py                     byte-safe anchored edits, validated against the original
  qa_dashboard.py                  the local HTML dashboard generator
  test_safe_edit.py                self-tests (25 checks)
  test_qa_dashboard.py             self-tests (25 checks)
```

## Writing a new domain file

`references/domains/README.md` lists the classes that are missing and worth writing. Copy the seven fixed
headings — *Do the thing · Scope map · Failure catalogue · Defect classes to look for by name · Evidence
and severity · Experience · Domain gotchas* — fill them **from a real engagement rather than from first
principles**, and keep it to 60–110 lines. The value is entirely in specificity: "three nodes formed and one
write was acknowledged and read
back from a different node after the leader was killed" is useful; "the product works" is not.

## The dashboard

The lifecycle is logged, not narrated. Each side appends to its own log — `qa-events.jsonl` and
`fix-events.jsonl`, one JSON object per line, never rewritten — so two sessions hours apart cannot clobber
each other and a git merge of two appends is trivial. `scripts/qa_dashboard.py` reads both logs and both
ledgers and writes a self-contained local site, one page per release:

```bash
python scripts/qa_dashboard.py ./qa-reports            # writes ./qa-reports/dashboard/
python scripts/qa_dashboard.py ./qa-reports --serve    # and serves it on 127.0.0.1:8711
```

Every page carries the **computed verdict** and its condition table, the findings ranked by severity with
their dev triage and commit, case coverage per scope, and for each finding a QA/DEV swimlane of its whole
life — filed, handed over, triaged, fixed, verified, closed or reopened — with time-in-state derived from
the timestamps. Plain HTML, inline CSS, no scripts and no external resources, so it works over `file://`.

**Nothing on the page is authored.** If it is not in the ledgers or the logs it is not there, and where a
page would have to guess it prints `NO VERDICT` and names the condition that had no rows. The generator
also enforces the handoff invariants and exits non-zero when one is violated: an `id` in `fix-state.json`
that QA never issued, a DEV session claiming `CLOSED`, a journey or acceptance requirement not linked to a
calibrated scope. Those appear on the page as integrity problems that invalidate the verdict.

## Contributing

`main` is protected and takes changes only through pull requests. `CONTRIBUTING.md` has the bar a new
domain file has to clear and the four places a new domain has to be registered.

## License

Apache-2.0 — see `LICENSE` and `NOTICE`. Use it commercially, adapt the domain files to your own product,
keep your adaptations private. The only obligation is attribution.

## Provenance

Distilled from a four-repo, full-business QA engagement, then reviewed adversarially against product
classes the original engagement never touched. That review changed the design rather than decorating it —
the state, upgrade and experience families (10, 11, 12) exist because the first version had no concept of
whether data was still correct after time, concurrency, a fault or an upgrade, and the destructive-operations
rule was rewritten after it was found to forbid exactly the testing that stateful products need most.
