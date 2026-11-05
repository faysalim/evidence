---
name: requirements
description: Turn a PRD and stakeholder input into numbered requirements traceable to the PRD, map the real business process including its exceptions, capture the business rules, and route every conflict to the operator as a decision memo instead of picking one reading. Use when the user wants requirements elicited or documented, a business process mapped, business rules captured, a legacy system specified, or conflicting stakeholder input resolved. Not for stories with acceptance criteria - that is evidence:backlog.
---

# Requirements

`status: draft` — see `${CLAUDE_SKILL_DIR}/README.md`.

A BA's characteristic failure is a reasonable one: two stakeholders say incompatible things, and the
document records a blend that neither asked for and neither will accept at review. The blend is invisible —
it reads like a requirement.

So the governing rule here is `shared/principles.md` §10 — **reality beats paperwork** — with a specific
procedural consequence: **a conflict becomes a `decision` item for the operator, never a silent pick.** In
the origin engagement 11 of 37 findings were decisions, and written as memos with options and a
recommendation, all 11 were answered in one message. The same device works for requirements.

Items move only through `python "${CLAUDE_PLUGIN_ROOT}/shared/scripts/hub.py"`.

## What this skill produces

| Hub item | Note |
|---|---|
| `requirement` | `SPECIFIED` → `AGREED` by a different role (PO, PM, sponsor or operator), or → `CONFLICTED` with a reason |
| `decision` | One per conflict or ambiguity. `OPEN` until the operator answers, and `OPEN` is a real status to report |

Every requirement links `refines` to the `prd` it comes from. **A requirement with no PRD link is
unattached**: either the PRD is missing something, or the requirement is scope nobody approved. Both are
worth saying out loud, and the dashboard's traceability view lists them.

## The requirement contract

```
id           REQ-14
statement    One testable sentence. "The system shall..." is fine; vagueness is not
rationale    Why. Without it, the next person deletes it as redundant
source       Who said it, and when. A role and a date, never just "the business"
rule         The business rule in full, with its boundaries and its units
exceptions   What happens in the cases the happy path ignores
conflicts    Other REQ ids this contradicts, if any
```

**`exceptions` is the field that earns this skill.** A requirement without them is the happy path wearing
formal language, and the exceptions are where the money is: what happens on the last day of the month, for
a customer in two regions, when the amount is zero, when the record was deleted, when two people act at
once. Ask for each explicitly — stakeholders do not volunteer them, because to them the exception is
obvious and rare.

**`source` must be a person and a date.** "The business requires" cannot be re-asked. "Finance lead,
2026-11-04, in the pricing review" can, and will be, when it turns out to conflict with something.

## Eliciting

1. **Ask what happens today, step by step, including who does it.** The documented process and the real one
   differ; the real one is the requirement baseline. The workaround people have built is the measure of the
   current gap.
2. **Ask for the last exception they remember handling.** More productive than asking what the exceptions
   are.
3. **Get the numbers with their units and their boundaries.** "Within 30 days" — of what event, inclusive
   or exclusive, in whose timezone? Unit and boundary ambiguity is the single largest source of defects
   this skill can prevent, and it costs one question each.
4. **Ask who else is affected.** The second stakeholder is usually the one who vetoes at review.
5. **Write down what nobody could answer.** That is a `decision`, not a gap in your notes.

## Process maps

A map is useful only if it shows the exceptions. A happy-path diagram tells the team what they already
assume.

Keep them textual, so they live in version control and diff:

```
Order placed
  -> payment authorised          [exception: declined -> notify, hold 24h, release stock]
  -> stock reserved              [exception: insufficient -> partial ship? BACKORDER decision D-7]
  -> fulfilment requested        [exception: address invalid -> support queue]
  -> shipped                     [exception: carrier rejects -> re-pick, no re-charge]
  -> delivered
  -> return window opens (30d from DELIVERY, not from order -- REQ-22)
```

Each bracket is either a requirement or a `decision`. **An exception with no stated handling is a
`decision`**, and leaving it as a note in a diagram is how it reaches production as a support ticket.

## Legacy systems

For an existing product or a system being replaced, the specification is the behaviour, not the
documentation. `/evidence:orient`'s capability inventory is the starting point; where behaviour is
undocumented:

- **Observe it, and say that you observed it.** Mark the requirement `provenance: reconstructed`. A
  reconstructed requirement is honest; one presented as agreed intent is not.
- **Find the boundary by probing, not by reading.** What the code does at zero, at the limit, on the
  boundary date is a measurement.
- **Where the legacy behaviour looks wrong, do not quietly specify the correct version.** Record both: what
  it does, and what the stakeholder believes it does. That gap is a finding, and it is often the reason the
  replacement was commissioned.
- **Two near-identical rules usually exist on purpose.** Read the history before calling one a mistake —
  in the origin engagement two similarly named variables turned out to be a deliberate split between two
  consumers, which changed the finding entirely.

## Conflicts

```
hub.py add decision D-7 -f title="Partial shipment when stock is short" \
   -f options="[ship partial + backorder | hold whole order | cancel line]" \
   -f recommendation="ship partial; it matches what support already does by hand" --role BA
hub.py move REQ-31 CONFLICTED -f reason="contradicts REQ-14 on the return window start" --role BA
```

Write the memo with **options and a recommendation**. A conflict presented as a question gets a meeting; a
conflict presented as options with a recommendation gets an answer. Only the operator moves it to
`ANSWERED`, and the answer is recorded in their words, not summarised into something tidier.

## For the lead

Two checks. **Does every requirement have a source that is a person and a date?** — anything else cannot
be re-asked when it conflicts. And **does every process map show its exceptions?** A map with none has not
been elicited, it has been drawn.

Then look at the `decision` list: `hub.py list --type decision --state OPEN`. A long list is not a failure
of this skill, it is its output. A list of zero on a non-trivial domain means conflicts were resolved
silently, which is the one thing the skill is for preventing.

## Open questions

- Whether `requirement` should require a linked `prd` to reach `SPECIFIED`. It would catch unattached
  scope immediately; it would also block legitimate compliance requirements that precede any PRD.
- No template ships for the process map. The textual form above is the convention; whether teams want a
  diagram format is unknown.
- The elicitation heuristics are reasoned. The ones with real evidence behind them are the unit/boundary
  question and the near-identical-rules caution, both from the origin engagement.

| File | Read it when |
|---|---|
| `${CLAUDE_PLUGIN_ROOT}/shared/principles.md` | First. §10 governs this skill |
| `${CLAUDE_PLUGIN_ROOT}/shared/domains/` | The product class, for the exceptions it is known to have |
| `${CLAUDE_PLUGIN_ROOT}/shared/references/docs-conformance.md` | Specifying a legacy system from its real surface |
