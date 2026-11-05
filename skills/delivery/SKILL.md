---
name: delivery
description: Generate delivery status from the work-item hub instead of collecting it, maintain the RAID risk log, surface what is blocked and on whom, and plan milestones against dependencies the hub already knows. Use when the user wants a status report, delivery plan or milestones, a RAID or risk log, cross-team dependencies tracked, or an answer to why something is late. Not for prioritising the backlog - that is evidence:backlog.
roles: DELIVERY
status: draft
---

# Delivery

`status: draft` — see `${CLAUDE_SKILL_DIR}/README.md`.

A status report that people write about their own work is a report of how they feel about their work. It is
optimistic in a predictable direction, it costs everyone an hour a week to produce, and it is wrong in the
one place it matters — the thing that is stuck, which is the thing nobody wants to write down.

So this skill has one rule above the others: **status is generated, never authored.** Everything in a
report here comes from `hub.py`, and the parts that are judgement are labelled as judgement and attributed.
That is `shared/principles.md` §6 — a verdict is computed — applied to delivery.

Items move only through `python "${CLAUDE_PLUGIN_ROOT}/shared/scripts/hub.py"`.

## What this skill produces

| Hub item | Note |
|---|---|
| `risk` | `OPEN` → `MITIGATED` (requires a mitigation **and its evidence**) → `CLOSED` by a different actor; or `ACCEPTED` by the operator; or `REALIZED` |
| `decision` | Where a delivery trade needs the operator: scope, date, people, cost |
| `initiative` | The container the work hangs from, if it has a name |

## Generating a status report

Four commands, and the report is their output:

```
hub.py status
hub.py list --waiting-on OPERATOR     # the team cannot unblock these at all
hub.py list --type finding --state NEW # nobody has triaged these; NEW is not a resting state
hub.py list --type risk --state OPEN
hub.py dashboard                       # the computed verdict, if a release is in flight
```

Then the report, in this order — which is the order of what a reader can act on:

```
Blocked on a human        every item waiting on the operator or a sponsor, with how long
Blocked on each other     cross-team dependencies, from the hub's links
Open risks                severity-ordered, each with its mitigation or its absence
Moving                    items that changed state since the last report
Not moving                items that did NOT change state, and for how long
Verdict, if shipping      from the dashboard, never paraphrased
Judgement                 labelled as such, attributed to you, three lines maximum
```

**"Not moving" is the section that earns the report.** Everything else is visible in the board. An item
that has not changed state in three weeks is either finished and unrecorded, blocked and unreported, or
abandoned and unadmitted, and all three are worth a question. `hub.py` records every transition's
timestamp, so this section is computable rather than remembered.

**There is no percent-complete, anywhere.** A percentage of an unknown total is the denominatorless number
§2 forbids, and in delivery it is the specific number that lets a project be 90% complete for a quarter.
Report counts with their denominators — "11 of 34 stories accepted" — and the lifecycle board.

## The risk log

Ids are global across the hub, and QA owns three prefixes: `R-` for acceptance requirements, `J-`
for journeys, `S<n>-` for scope cases. Use `RISK-<n>` here, or the verdict's requirement row and
your risk log fight over the same name.

RAID, with one addition that changes how it is used: **a mitigation needs evidence, and the hub enforces
it.**

```
hub.py add risk RISK-3 -f title="single supplier for the signing certificate" \
  -f impact="cannot ship a signed build; blocks every desktop release" \
  -f likelihood="low" -f owner=TECH_LEAD --role DELIVERY
hub.py move RISK-3 MITIGATED -f mitigation="second CA account provisioned" \
  -f evidence="test build signed with the backup CA, 2026-11-04, sha256:..." --role TECH_LEAD
```

"We have a plan" is not a mitigation; a test build signed with the backup certificate is. Without that
rule a risk log becomes a list of risks with the word "monitoring" next to them, which is a record of
having noticed rather than of having acted. A risk may also be **accepted** — that is the operator's call,
in writing, and it is an honest outcome.

Carry `REALIZED` honestly too. A risk that happened and was quietly re-labelled an issue teaches the team
nothing; a `REALIZED` risk with its impact recorded is the most useful row in the next project's log.

## Planning and dependencies

Milestones come from what must be true, in order, not from dividing a date range:

1. **Read the chain.** The dashboard's traceability view shows initiative → prd → requirement → story →
   case → release. A milestone is a point on it where something becomes usable.
2. **Find the dependencies the hub already knows.** `blocks` links, and stories whose branch depends on
   another's — `/evidence:dev` states branch dependencies, and they are real schedule constraints.
3. **Name the external dependencies as risks**, with an owner and a date. A certificate, an account, a
   vendor, a partner's API. These are `PROCURE`-class in QA's taxonomy and they are the ones that cannot be
   worked around by trying harder.
4. **Put the unblocking work before the work it unblocks.** A `NOT RUN` case blocked on a missing test
   environment for three iterations is a procurement item, not a QA backlog item, and it should appear on
   the plan as one.
5. **State what the plan assumes.** Dates rest on assumptions — a team size, an unblocked decision, an
   environment arriving. Record them; when one breaks, the plan changes for a stated reason rather than
   slipping for an unclear one.

## Existing product and ongoing delivery

For work already in flight, do not re-plan from scratch. Import what exists
(`/evidence:orient` maps their tracker), then report the two things their current process almost
certainly does not: **how long each item has sat in its current state**, and **what is waiting on a human
outside the team**. Those two are usually new information even to a team that has been running standups
for a year, because neither is visible in a board.

## For the lead

Read "not moving" and "blocked on a human" first; the rest is context. Then ask the question a status
report cannot ask itself: **what is the oldest thing here, and why is it still here?** Age is the signal
that survives everyone's optimism.

Two queries weekly: `hub.py list --type cleanup --state OPEN` (what is still billing or exposed — real
money, and it is nobody's job by default) and `hub.py validate` (a hub with integrity problems produces
tidy, wrong reports).

## Open questions

- Whether `list` needs `--stale <days>` so "not moving" is one command rather than a read of history. The
  data is there; the CLI does not expose it.
- No template ships for the status report; the section order above is it. That order is the opinionated
  part and the part most likely to need adapting to a team's existing rhythm from `conventions.md`.
- Nothing here models capacity, velocity or estimates, deliberately. Teams will ask. The honest position is
  that this suite has no evidence about estimation, so it offers none.

| File | Read it when |
|---|---|
| `${CLAUDE_PLUGIN_ROOT}/shared/principles.md` | First. §6 governs this skill |
| `${CLAUDE_PLUGIN_ROOT}/shared/vocabulary.md` | Item states, severities, closing actions |
