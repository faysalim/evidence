---
name: architecture
description: Document the architecture a product actually has before changing it, then write the technical design as a change against that, recording each consequential choice as an ADR with the options rejected and what would prove it wrong. Covers the durability, consistency and failure-mode contracts the product class implies. Use when the user wants a technical design, ADR, system diagram, or an existing system's architecture documented. Not for product scope - that is evidence:prd.
roles: TECH_LEAD
status: draft
---

# Architecture

`status: draft` — see `${CLAUDE_SKILL_DIR}/README.md`.

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

## What this skill produces

| Hub item | Note |
|---|---|
| `adr` | `PROPOSED` → `ACCEPTED` by a tech lead who is **not the author** |
| `decision` | Where a choice needs the operator: cost, vendor, a deadline trade |
| `risk` | Where a design has a known failure mode nobody is mitigating yet |

Link each `adr` to the `story` or `prd` it serves. An ADR attached to nothing is a preference.

## The ADR

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

Then ask the question the design most often cannot answer: **what does this promise that nothing
enforces?** A replication factor set in config but not asserted anywhere, a documented consistency model
with no test, an at-most-once claim over an at-least-once transport. Those gaps become `case` items for QA
if they are real, and `adr` corrections if they are not.

## Open questions

- Whether `adr` should require `falsifier` to reach `PROPOSED`, the way a story requires criteria. It would
  be consistent with the rest of the suite; it may be too strict for a small reversible choice.
- No diagram format is prescribed. Textual component lists diff well in version control; teams may want
  something renderable, and a textual format that renders is probably the answer.
- The current-state table is QA's Step 1 generalised, which has real provenance. The ADR field list is
  conventional, and the `falsifier` field is this suite's own addition — untested.

| File | Read it when |
|---|---|
| `${CLAUDE_PLUGIN_ROOT}/shared/principles.md` | First. §3 and §10 govern this skill |
| `${CLAUDE_PLUGIN_ROOT}/shared/domains/` | **Before designing.** The fault catalogue the class is known for |
| `${CLAUDE_PLUGIN_ROOT}/shared/references/evidence-standard.md` | Establishing the current state from artifacts |
| `${CLAUDE_PLUGIN_ROOT}/shared/references/gotchas.md` | Repository, branch and build traps |
