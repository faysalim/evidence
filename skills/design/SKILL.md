---
name: design
description: Turn stories into flows and designs covering the failure, empty, partial and permission-denied states as well as the happy path, and run design reviews whose findings are provable rather than matters of taste. Use when the user wants a flow, screen, interaction or design system work designed or reviewed, a usability problem diagnosed, or error and empty states specified. Not for testing a build - that is product-suite:qa.
---

# Design

`status: draft` — see `${CLAUDE_SKILL_DIR}/README.md`.

A design review fails the moment one of its findings can be answered with *"that's subjective"*, because
after that nobody reads the section. So this skill holds design findings to the same evidence bar as
correctness findings, using the hierarchy already written for QA in
`${CLAUDE_PLUGIN_ROOT}/shared/references/experience.md`.

Items move only through `python "${CLAUDE_PLUGIN_ROOT}/shared/scripts/hub.py"`.

## What this skill produces

| Hub item | Note |
|---|---|
| `design` | `PROPOSED` → `REVIEWED` by the design lead → `ACCEPTED` by the PO. **Never by its author** |
| `finding` | Design-review findings, same template and same evidence bar as QA's |
| `decision` | Where a design trade needs the operator — a cost, a platform convention, a deadline |

A `design` links `realizes` to its story. A design attached to no story is either missing a story or is
scope nobody approved.

## Every state, not just the happy one

The deliverable is not a screen. It is **every state that screen can be in**, and the ones that get
skipped are the ones users actually hit:

| State | The question it answers |
|---|---|
| Empty | First run, and after the user deletes everything. What tells them what to do? |
| Loading | And what happens when it is slow rather than instant |
| Partial | Some data arrived, some failed. Most designs pretend this does not exist |
| Error, per cause | Not one generic error. Network, permission, validation, and the provider being down are four different messages with four different next actions |
| Permission-denied | What a role that cannot do this sees. Hiding the control and showing a disabled control are different decisions |
| Too much data | 10,000 rows, a 200-character name, a 50 MB upload |
| Offline | If the product claims to work offline, design the reconciliation, not just the banner |
| Success | Including what it says when the thing succeeded but something downstream has not happened yet |

**A design that specifies only the happy path has specified the part that was never in doubt.** The origin
engagement's worst findings were all failure paths that looked finished: a form that showed success
regardless of outcome, a success panel over a swallowed submission.

## Error messages are a product surface

`experience.md` has the full method. The part that belongs in a design deliverable: each message names
**what happened**, **what it means for the user's goal**, and **the next action they can take**. A message
that names only the condition — "Error 4201" — pushes the diagnosis onto the user, and a message with no
action pushes it onto support.

**Silent failure is the worst possible message.** A swallowed exception is a design finding, not only an
engineering one, because the design is what decided the user should see nothing.

## Making a design finding provable

Four kinds of evidence, strongest first. Anything below these is polish, and padding a review with polish
is what teaches people to skip the section.

1. **The product already does it right somewhere else.** Removes taste from the argument entirely — it is
   the product's own two surfaces disagreeing. Cite both.
2. **A blocked or abandoned goal**, stated as a goal: "a viewer cannot find how to request access; the
   path exists only in an email they no longer have."
3. **A measurement**: time, steps, exits from the product, doc round-trips, or a count of distinct
   conditions mapped to a single indistinguishable signal.
4. **A convention violation with a named cost**: "the destructive action is where Save is on every other
   screen, so a reflexive click deletes" — and note that this inherits the severity of the action it leads
   into (`shared/vocabulary.md`), so this one is `critical`, not cosmetic.

**Not evidence:** aesthetic preference with no nameable cost. If you cannot name the user goal it damages,
it is polish — label it as such and rank it last.

## Reviewing a build rather than a mock

When the thing exists, review the thing. `shared/principles.md` §1 — a mock is a response; the built
surface is the thing. Drive the real build, at both widths, with the real data volumes, and read the
console. And take the **first-run trace** if nobody has: time and steps to first success, with every guess
and backtrack. It is perishable, you get one, and it is the baseline every later iteration is measured
against.

Accessibility has its own owner and its own fixes; it is a section of its own in the review, never folded
into general polish. `experience.md` has the checks.

## New product and existing product

| | New | Existing |
|---|---|---|
| Start from | The flows the PRD's first-success milestones imply | What users do **now**, from the product itself and from support tickets |
| The trap | Designing the system's model rather than the user's task | Designing against the design system rather than the product — the shipped product has drifted from it, and the drift is a finding |
| Free evidence | None | The first-run trace in the product profile, the error inventory from QA, and churned-user research |

For an existing product, **inventory the inconsistencies before proposing anything.** Two date formats,
three button styles for the same action, two words for the same object. Each is a finding of kind 1 above
— the strongest kind — and together they are usually a bigger win than any new screen.

## For the lead

Review the state list before the visuals: if empty, partial, error-per-cause and permission-denied are
missing, the design is not reviewable yet. Then check that every finding in a review names which of the
four evidence kinds it rests on, and send back any that rest on none — one unprovable finding is enough to
let a team dismiss the rest.

## Open questions

- Whether `design` should require the state list as a structured field, so a design cannot reach
  `PROPOSED` with only a happy path. It is the strongest candidate for enforcement in this skill.
- No template ships for the design review itself; it uses `shared/templates/finding.md`. Whether design
  reviews need their own shape is unknown.
- The state table is drawn from the origin engagement's findings, so it has provenance. The rest is
  reasoned.

| File | Read it when |
|---|---|
| `${CLAUDE_PLUGIN_ROOT}/shared/principles.md` | First |
| `${CLAUDE_PLUGIN_ROOT}/shared/references/experience.md` | **The method for this skill.** Evidence hierarchy, error messages, first-run, accessibility |
| `${CLAUDE_PLUGIN_ROOT}/shared/templates/finding.md` | Writing a review finding |
| `${CLAUDE_PLUGIN_ROOT}/shared/vocabulary.md` | Severity, and how an experience defect inherits it |
