---
name: release
description: Call a release: compute the go/no-go from the hub rather than asserting it, state the bounds the verdict covers and what it does not, write release notes from what actually shipped, and record the operator's decision when they ship without a green. Use when the user asks whether something is ready to ship, or wants a go/no-go, release-readiness assessment or release notes. Not for testing the build - that is evidence:qa.
roles: DELIVERY, PM, TECH_LEAD
status: exercised
---

# Release

`status: exercised` -- run against a real product; weaker than `proven`. See `${CLAUDE_SKILL_DIR}/README.md`.

The go/no-go is the single most consequential sentence anyone in this suite writes, and it is the one most
often produced by looking at an empty bug list and feeling reassured. **This skill does not write a
verdict. It computes one, and `NO VERDICT` is the default** (`shared/principles.md` §6).

A run can show ten agents, 180 cases and zero blockers while the one row that would have caught a
cross-tenant data leak sits `BLOCKED` at the bottom because a second tenant was never provisioned. "No
blockers" and "we checked for blockers" are different claims, and only the second is a reason to ship.

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

## Computing the go/no-go

```
hub.py dashboard
```

That prints the verdict and the condition table to stdout, and exits non-zero if the hub has
integrity problems. **Read the table, not the headline** — the headline is derived from it.

**Two things this skill does not let you do, and you will meet both.** Recording the verdict is
**QA's transition**, not the PM's or the EM's: `move <release> GREEN | NOT_GREEN | NO_VERDICT`
belongs to QA, and the hub refuses anyone else. And `GREEN` is refused unless the *computed*
verdict already says `GREEN within stated bounds` — you cannot write a verdict the hub does not
compute. What this skill is for is reading the table, writing the memo, and getting the operator's
decision when the answer is "ship anyway".

**The conditions key on id conventions QA owns**, and nothing else states them in one place:
acceptance requirements are `case` items whose ids start **`R-`**; journeys start **`J-`**; a scope's
smoke row ends **`-00a`** and its calibration row **`-00b`**, matched to a scope by the case's
`graded_by` field. A hub where QA used plain ids will read "none recorded — green is against the
docs only", which is honest and means the requirement rows were never created.

Every condition names the rows that satisfy it, and a condition with **no rows at all** yields
`NO VERDICT`:

| Condition | Why it is a gate |
|---|---|
| No open `critical` or `blocker`, including any held at `DECIDE` | A `DECIDE` carrying blocker severity is still open at that severity |
| Every blocking defect class has a `PASS` **in a calibrated scope** | A harness that has never failed has never been shown to work |
| No unreconciled `LONG` row | A 12-hour run reported at hour one is the purest false green |
| No `BLOCKED` or `NOT RUN` row guarding a blocking class | The leak that nobody looked for |
| Build identity established per component | A verdict about a build you cannot name is about nothing |
| Smoke row passed on the build the verdict names | Right bytes deployed is not the same as serving |
| Every acceptance requirement has a `PASS` | Green against the docs is not green against the contract |
| No story `DONE` but unaccepted; no decision awaiting the operator; no open risk; cleanup ledger empty | Work nobody has accepted is not shipped work |

**You do not override a condition.** If one fails and the team ships anyway, that is the operator's
decision, recorded as such:

```
hub.py move REL-7 SHIPPED -f reason="<the operator's own words>" --role OPERATOR
```

The hub refuses anyone else that transition from `NOT_GREEN` or `NO_VERDICT`. That is the point: shipping
against the evidence is legitimate and common, and it should be visible and attributed rather than
absorbed into a summary.

## Bounds, and what the green does not cover

A green with no bounds is the claim this whole method exists to prevent. Every `GREEN` names:

- **The digests**, per component — not a version string, not a branch.
- **The topology, tenant shape and dataset size** it was exercised on, **as the harness listed them**, not
  as configured. Anything else is untested by this run.
- **What it does not cover**, in plain sentences: *"scope 8 was one hour of a bored attacker, not a
  penetration test"* · *"payments ran in test mode; declines, 3DS and webhook signature failure were not
  exercised"* · *"single-region only; the contractual RPO across an availability zone is `NOT RUN`"* ·
  *"author and verifier were the same party."*

The hub requires both fields before `GREEN`. The second one is what makes the first trustworthy: a reader
who can see the edges of a claim can rely on what is inside them.

## Release notes

Written from **what shipped**, which means from the hub, not from the plan:

```
hub.py list --type story --state ACCEPTED
hub.py list --type finding --state CLOSED
```

- **Group by what a user can now do**, not by component or by ticket number.
- **Name the fixes users noticed.** A closed finding that nobody outside the team ever hit does not need a
  line; one that generated support tickets does, and saying so retains more goodwill than silence.
- **State the breaking changes first**, with the migration step. A breaking change discovered in paragraph
  four has already broken someone.
- **Do not list what did not ship.** Deferred work goes in the plan, not the notes.
- **Every claim in the notes is checkable.** If a note says "export is now 3× faster", the measurement
  exists as a `case` or a `metric`, or the note does not go in. This is `shared/principles.md` §2 applied
  to customer-facing prose, and `/evidence:launch` enforces the same rule on marketing copy.

## New product and existing product

For a **first** release there is no baseline, so the verdict has fewer rows and more `NO VERDICT`
conditions. Say that rather than lowering the bar: a first release's honest verdict is usually
"`NO VERDICT`, shipping on the operator's call, here is exactly what was and was not exercised."

For an **existing** product the extra question is **what this release could break that it did not
touch** — regression scope from the diff's blast radius, and the upgrade path from the *oldest* supported
version, not from the previous one. Both are QA's scope 11; this skill's job is refusing to call a green
without them.

## For the lead

Ask for the condition table, never the summary. Then ask the two questions the table cannot answer by
itself: **what is the worst thing that is still true?** (usually a `NOT RUN` guarding something severe),
and **who would notice first if this is wrong?** If the answer to the second is "a customer", the
monitoring is the gap and that is a `risk` item before shipping, not after.

## Open questions

- Whether a `release` should require a linked `metric` with monitoring in place before `SHIPPED` — "who
  would notice first" made structural. Probably right; not yet enforced.
- No template ships for the go/no-go memo; the condition table from the dashboard is the artifact. A memo
  template may be redundant with it.
- The condition list is inherited from `qa_dashboard.py`'s verdict, which has real provenance, extended
  with the hub's cross-role conditions, which do not.

| File | Read it when |
|---|---|
| `${CLAUDE_PLUGIN_ROOT}/shared/principles.md` | First. §6 is this skill |
| `${CLAUDE_PLUGIN_ROOT}/shared/vocabulary.md` | Verdicts, severities, case results |
| `${CLAUDE_PLUGIN_ROOT}/shared/contracts/qa-dev.md` | Where fixes in this release came from |
