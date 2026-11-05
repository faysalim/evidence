---
name: design
description: Turn stories into flows and designs covering the failure, empty, partial and permission-denied states as well as the happy path, and run design reviews whose findings are provable rather than matters of taste. Use when the user wants a flow, screen, interaction or design system work designed or reviewed, a usability problem diagnosed, or error and empty states specified. Not for testing a build - that is evidence:qa.
roles: DESIGNER, DESIGN_LEAD
status: exercised
---

# Design

`status: exercised` -- run against a real product; weaker than `proven`. See `${CLAUDE_SKILL_DIR}/README.md`.

A design review fails the moment one of its findings can be answered with *"that's subjective"*, because
after that nobody reads the section. So this skill holds design findings to the same evidence bar as
correctness findings, using the hierarchy already written for QA in
`${CLAUDE_PLUGIN_ROOT}/shared/references/experience.md`.

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

### Record *where* each state is handled, or the audit is wrong in both directions

A state can be handled at the screen, in a shared component, in the data layer, or by a global
default — and **centralised handling is both a correct answer and an invisible one.** Auditing only
the screens produces false findings; assuming a global net exists produces missed ones.

Exercising this skill on a real 19-screen console, the first pass counted per-screen error handling
and reported 11 of 19 as covered. That was wrong twice over. Writes were handled centrally in the
data layer, with a specific message per operation and a rollback — invisible to a screen-level
audit, and done well. Reads had no global handler at all, so the screens were the only line, and the
real figure was **5 of 19 using the shared error component, 8 of 19 surfacing a read failure by any
means.** Same product, opposite conclusions, from one unasked question.

So add a column. For each of the eight states: *handled where, and what happens if that layer is
absent?*

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

   **The fastest route to this evidence in a real codebase is the shared component the product
   already ships.** If there is an `ErrorState`, an `Empty`, a toast helper — then "this screen does
   not use the thing you built for this" is a finding nobody can call subjective, and it comes with
   its own fix. On that 19-screen console the product shipped both `ErrorState` and `Empty`; 5 and 7
   screens used them. The 14 that did not included every diagnostic screen, so a failed read
   rendered identically to a healthy empty cluster — which for a monitoring console inverts the one
   distinction its users need most. Severity follows what it leads into
   (`shared/vocabulary.md`): an operator concluding the cluster is fine because the console could
   not reach it is not cosmetic.
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

**On a small team.** A design needs `REVIEWED` by a `DESIGN_LEAD` and `ACCEPTED` by someone who
did not propose it. Roles are hats (`${CLAUDE_PLUGIN_ROOT}/shared/vocabulary.md`), so where there is
no design lead the PO wears that hat — but the guard is on the **actor**, not the role, so it must
be a different person, and findings you file are still closed by QA.

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
