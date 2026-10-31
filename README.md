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
git clone https://github.com/<you>/product-qa.git ~/.claude/skills/product-qa

# or project-level — checked in with one repo's code
git clone https://github.com/<you>/product-qa.git .claude/skills/product-qa
```

On Windows the user-level path is `%USERPROFILE%\.claude\skills\product-qa`.

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
| **3 — Test by doing** | Per-surface evidence standards. Status 200, a green build and `/health: ok` are listed as evidence that looks strong and is not. |
| **4 — Write each finding** | Exact repro, raw evidence, build identity, and a closing action: `CODE / DEPLOY / RELEASE / DATA / PROCURE / DECIDE / INVESTIGATE`. |
| **5 — Rank and consolidate** | Severity by worst consequence, not by the section it was filed in. |
| **6 — Correct yourself in writing** | Retractions belong in the report, with what was wrong and how it was found. |
| **7 — Cleanup ledger** | Every account, key, container and shared quota you touched, and its disposition. |

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
`references/domains/` carries that for seventeen classes:

**Data and state** — distributed database · relational database · message broker / streaming · ETL
pipeline · file sync and storage

**Applications** — multi-tenant SaaS · CRM · mobile app · desktop app · AI / model-backed feature

**Platform and infrastructure** — API platform · identity and SSO · licensing server · payments ·
observability platform · infrastructure operator / IaC · embedded and firmware

Each file names that domain's version of the directive. A sample:

- *"'Available' is this domain's HTTP 200."* — distributed database
- *"'Run succeeded' is this domain's HTTP 200."* — data pipeline
- *"`lag: 0` is this domain's HTTP 200 — and it is also exactly what a consumer that has skipped records
  reports."* — message broker
- *"A good answer to the demo prompt is this domain's HTTP 200 — and here a single passing run is not weak
  evidence, it is no evidence at all."* — AI feature
- *"A connected agent is this domain's HTTP 200 — and a false green here is not a defect in the product, it
  is the product failing at its only job."* — observability

Each also lists its **defect classes by name**, because an unnamed defect class is one nobody looks for,
and declares its usual agent count so the budget is checked before the operator is asked for more.

## Later iterations

A second run is not a second first run. `references/iteration-cycles.md` defines the gate:

```
Phase 0  build identity  →  Phase 1  verify the reported fixes  →  Phase 2  regression
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

## Repository layout

```
SKILL.md                           the method — read first
references/
  evidence-standard.md             what counts as proof, per surface
  scope-playbooks.md               the twelve families, with steps
  docs-conformance.md              two-way documentation coverage
  iteration-cycles.md              phases, the gate, the finding register
  experience.md                    UX as a measurement, not a taste
  gotchas.md                       traps that each cost a cycle
  fix-phase.md                     when report-only is lifted
  case-file.md                     one worked engagement, with real numbers
  domains/                         seventeen product classes + README index
assets/
  finding.md                       the finding template
  ranked-index.md                  the report template
  agent-brief.md                   what a scope agent is told
scripts/
  safe_edit.py                     byte-safe anchored edits (newline- and BOM-preserving)
```

## Writing a new domain file

`references/domains/README.md` lists the classes that are missing and worth writing. Copy the seven fixed
headings, fill them **from a real engagement rather than from first principles**, and keep it to 60–110
lines. The value is entirely in specificity: "three nodes formed and one write was acknowledged and read
back from a different node after the leader was killed" is useful; "the product works" is not.

## Provenance

Distilled from a four-repo, full-business QA engagement, then reviewed adversarially against product
classes the original engagement never touched. That review changed the design rather than decorating it —
the state, upgrade and experience families (10, 11, 12) exist because the first version had no concept of
whether data was still correct after time, concurrency, a fault or an upgrade, and the destructive-operations
rule was rewritten after it was found to forbid exactly the testing that stateful products need most.
