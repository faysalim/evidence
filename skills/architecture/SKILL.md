---
name: architecture
description: Document the architecture a product actually has before changing it, then write the technical design as a change against that, recording each consequential choice as an ADR with the options rejected and what would prove it wrong. Covers the durability, consistency and failure-mode contracts the product class implies. Use when the user wants a technical design, ADR, system diagram, or an existing system's architecture documented. Not for product scope - that is evidence:prd.
roles: TECH_LEAD
status: exercised
---

# Architecture

`status: exercised` -- run against a real product; weaker than `proven`. See `${CLAUDE_SKILL_DIR}/README.md`.

Two rules govern this skill, and both come from the same place.

**Document what is, before designing what changes.** For an existing product the architecture in anyone's
head is a few years stale, and a design written against it specifies a system that does not exist.
`/evidence:orient` establishes which build is live and what the product really exposes; this skill
turns that into a current-state architecture and then designs the delta.

**State the contracts, especially the ones nobody has written down.** What consistency does the store
promise? What happens to an acknowledged write when a node dies? Is delivery at-least-once or
exactly-once? The product class in `${CLAUDE_PLUGIN_ROOT}/shared/domains/` tells you which contracts are
load-bearing. **An absent contract is the first finding, not a gap to fill with an assumption** — because
`/evidence:qa` will grade the behaviour at the severity its consequence earns regardless, and
customers will too.

Items move only through `python "${CLAUDE_PLUGIN_ROOT}/shared/scripts/hub.py"`.

## Before you start: read the profile

```
hub.py status          # mode, the product class, and what orient could not establish
hub.py profile         # the full profile, including their domains and acceptance requirements
```

If there is no profile, stop and run `/evidence:orient` — without it this skill guesses the product
class, the deploy branch and what the team calls things, and a guess here is wrong in a way nobody
notices until the first handoff is rejected on vocabulary.

Read `<report-dir>/conventions.md` too, and **use their words, their ids and their templates.** If
they number requirements `CR-4` or call a story an MMF, so does this skill; existing ids are
preserved, never renumbered. The ten principles in `${CLAUDE_PLUGIN_ROOT}/shared/principles.md` are
the only thing here that is not theirs to set — and `status` prints what orient could not establish,
which you must read before assuming anyone looked.

## What this skill produces

| Hub item | Note |
|---|---|
| `adr` | `PROPOSED` → `ACCEPTED` by a tech lead who is **not the author** |
| `decision` | Where a choice needs the operator: cost, vendor, a deadline trade |
| `risk` | Where a design has a known failure mode nobody is mitigating yet |

Link each `adr` to the `story` or `prd` it serves. An ADR attached to nothing is a preference.

## The ADR

**If they already keep decision records, theirs win — read them before this section.** An existing
`docs/decisions/`, `adr/` or wiki category is a convention, and `conventions.md` is where it is
recorded. Exercising this skill against a real product found five records named
`NNNN-kebab-title.md`, titled `# Decision NNNN — <sentence>`, each with a companion sketchnote, a
free-prose `**Status:**` line, and sections `Problem` / `Root cause` / `Decision` / `Why not the
alternatives` / `Tests` / `Validation` / dated `Addendum`. The team calls them **Decisions**, not
ADRs. Imposing `ADR-4` and the six-field block below on that would renumber their records and rename
their artifact — the same imposition-over-adoption failure that `requirements` committed with a
hard-coded `REQ-14`, and the one `/evidence:orient`'s "For the lead" section exists to catch.

So: keep their ids, their filename pattern, their title form and their section names. Add only what
is **missing** from their template, and only where it earns its place. In that engagement the answer
was one field — see `falsifier` below — because they were already doing `rejected` well, under the
heading `## Why not the alternatives`.

The six fields below are the template when a team has none, and the checklist for what to look for
when they do.

Six fields. The last two are the ones usually missing and the ones that make it useful later.

```
id            ADR-4
context       The forces. What makes this a decision rather than an obvious choice
decision      What we are doing, in one sentence, present tense
consequences  What this makes easy, and what it makes hard or expensive later
rejected      The options not taken, each with the reason. Name them even if obvious
falsifier     What we would observe that would mean this was wrong
```

**`rejected` is what stops the ADR being re-litigated every six months.** "We did not use a queue because
the ordering guarantee we need is per-tenant and the broker gives us per-partition" closes a conversation
permanently; omitting it means having it again.

**`falsifier`** is the oracle rule (`shared/principles.md` §3) applied to a decision. "If p99 write latency
under the migration path exceeds 200 ms at 3× current volume, this was the wrong call." Without it an ADR
can never be shown to have been a mistake, so nothing is learned and the next one is no better.

This field was the suite's own invention and was marked untested. Exercising the skill is what
settled it, and the evidence came from the team's own records rather than from argument: none of
their five Decisions stated a falsifier, and **two carried a dated `## Addendum` recording that the
decision had later been found wrong or incomplete** — "the fence had a hole: a Handoff→Recovering
bounce", and a regression-and-revert of half a fix. Those addenda are falsifiers, written after the
fact at the cost of a failed run. Proposing the field is therefore adoption of a practice the team
already has, moved earlier; that is the argument to make to them, not a template preference.

## A decision that is accepted but only half-built

The `adr` lifecycle is `PROPOSED → ACCEPTED → SUPERSEDED`, and it is about the **decision**, not the
build. One of the five real Decisions read `Status: Partial (instrumentation + safety net
implemented; core transport fix pending next-run pinpoint)` — a state the lifecycle cannot express.
`ACCEPTED` overstates it and `PROPOSED` is false, so mapping it either way loses the fact that half
of a shipped decision is still outstanding.

Do not resolve this by renaming their status. Resolve it by making the outstanding half a linked
item with its own owner — a `story` if it is planned, a `risk` if it is not — so the gap is visible
in the hub rather than buried in prose:

```
hub.py link <the risk or story carrying the unfinished half> blocks <the adr>
```

Note the direction: the model declares `blocks`, not `blocked_by`, and the vocabulary is closed —
writing this the other way round was the first thing exercising this skill got wrong, and the hub
accepted it silently until `link` learned to check.

An `adr` in `ACCEPTED` with nothing recording its unfinished half reads as done. That is a reporting
rule, not an enforced one: nothing checks it, which is why it is written here and in the lead's
review list rather than claimed as a guard.

## Current-state architecture, for an existing product

Build it from the artifact, and record how each line was established — the same discipline as QA's Step 1,
because a diagram nobody can source is a diagram nobody can correct.

| Establish | From |
|---|---|
| Components actually deployed | The deployment config and the running system, not the repo layout |
| Which build each runs | A version endpoint or an image digest, **per node** for a cluster |
| How they talk | Observed traffic and the route table; not the diagram on the wiki |
| Where state lives, and what it promises | The store's configuration, its replication factor, its documented contract — or the absence of one |
| What is scheduled | Cron, queues, workers, and what happens when one overlaps itself |
| What is shared | A database two services both write to is one component for failure purposes, whatever the org chart says |

Then write down the three things the diagram cannot show: **what fails when each component fails**, **what
is a single point of failure**, and **what the product promises that nothing enforces**. The last one is
usually the most valuable sentence in the document.

## Designing a change

A technical design is a delta against the current state:

1. **What moves, what is added, what is deleted.** Deletion is a design decision and needs its own ADR —
   nothing is harder to reverse.
2. **The migration, including the data that already exists.** Online or offline, reversible or not, and
   what happens to writes during the window. If the answer is "we take a maintenance window", that is a
   `decision` for the operator.
3. **The rollback.** What a bad deploy looks like and how it is undone. A design with no rollback has
   decided to roll forward under pressure, which is a choice that should be made deliberately rather than
   discovered at 2 a.m.
4. **What the change makes harder.** Every design does; writing it down is what distinguishes a design
   from a proposal.
5. **The failure modes the product class is known for.** Read the domain file and work its fault catalogue
   against the new design before anyone builds it — that is far cheaper than finding them in scope 10.

**On a small team.** An ADR is `ACCEPTED` by a tech lead who did not author it. Where there is
only one, a senior engineer wears `TECH_LEAD` for the acceptance — a different actor, not the same
person with a second `--role`.

## For the lead

Review the `falsifier` first. An ADR with no falsifier cannot be wrong, which means it cannot be assessed
and will be defended rather than revisited.

Then two questions the hub cannot ask for you, because neither is enforced:

- **Is this ADR linked to anything?** "An ADR attached to nothing is a preference" is stated above and
  checked nowhere — the hub will accept and accept an unlinked `adr` all the way to `ACCEPTED`.
- **Does an `ACCEPTED` decision have unfinished halves, and do they have items?** See the section above.

Then ask the question the design most often cannot answer: **what does this promise that nothing
enforces?** A replication factor set in config but not asserted anywhere, a documented consistency model
with no test, an at-most-once claim over an at-least-once transport. Those gaps become `case` items for QA
if they are real, and `adr` corrections if they are not.

## Open questions

- Whether `adr` should require `falsifier` to reach `PROPOSED`, the way a story requires criteria. It would
  be consistent with the rest of the suite; it may be too strict for a small reversible choice.
- Whether `adr` should require a link to reach `ACCEPTED`, given that this file says an unlinked ADR is a
  preference and nothing enforces it. Exercising the skill gave a reason to leave it unenforced:
  `/evidence:orient` Step 5 maps an existing `docs/decisions/` folder onto `adr` items *before* any
  `story` or `prd` exists, so a link requirement at creation would make importing five real records
  impossible. The cost is that the rule now lives only in the lead's review list.
- No diagram format is prescribed. Textual component lists diff well in version control; teams may want
  something renderable, and a textual format that renders is probably the answer.
- Whether the `adr` lifecycle needs a state between `ACCEPTED` and done, for a decision whose
  implementation is partial. One of five real Decisions was in exactly that state. Today the answer is
  a linked `story` or `risk`, which keeps the lifecycle about the decision; it also means the hub shows
  `ACCEPTED` for something half-built unless somebody remembers the link.
- The current-state table is QA's Step 1 generalised, which has real provenance. The ADR field list is
  conventional. The `falsifier` field was the suite's own untested addition until exercising the skill
  found two of a team's five Decisions carrying post-hoc addenda that were falsifiers in all but name.

| File | Read it when |
|---|---|
| `${CLAUDE_PLUGIN_ROOT}/shared/principles.md` | First. §3 and §10 govern this skill |
| `${CLAUDE_PLUGIN_ROOT}/shared/domains/` | **Before designing.** The fault catalogue the class is known for |
| `${CLAUDE_PLUGIN_ROOT}/shared/references/evidence-standard.md` | Establishing the current state from artifacts |
| `${CLAUDE_PLUGIN_ROOT}/shared/references/gotchas.md` | Repository, branch and build traps |
