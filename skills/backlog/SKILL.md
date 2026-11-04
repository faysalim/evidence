---
name: backlog
description: Turn a PRD and requirements into stories whose acceptance criteria are oracles - each gradeable the same way by a different person, so QA can turn it straight into a test case. For an existing product it imports the backlog, adds missing criteria and flags untestable stories. Use when the user wants stories or tickets written, a backlog groomed or prioritised, or acceptance criteria written or reviewed. Not for deciding what to build - that is product-suite:prd.
---

# Backlog

`status: draft` — see `${CLAUDE_SKILL_DIR}/README.md`.

This skill exists for one sentence: **an acceptance criterion a different person cannot grade the same way
is not a criterion, it is a hope.** That is `shared/principles.md` §3 — the oracle rule — applied before any
code is written, which is the cheapest place to apply it.

The consequence is the thing that makes this plugin hang together: a criterion written as an oracle becomes
a QA case with no translation step. `/product-suite:qa` derives cases from the story's criteria as a
derivation source, and a story cannot be `ACCEPTED` until its linked cases pass. So a vague criterion is not
merely untidy — it blocks acceptance, by construction.

Items move only through `python "${CLAUDE_PLUGIN_ROOT}/shared/scripts/hub.py"`.

## The criterion test

Before a criterion goes in, it must survive four questions:

1. **What exactly is done?** An action someone could repeat from the text alone.
2. **What independently says pass or fail?** Not the product's own report of itself — not "the status shows
   complete", not "no errors in the log". `shared/principles.md` §3.
3. **What is the input that would make this fail?** If you cannot name one, the criterion asserts nothing.
4. **Could a stranger grade it without asking you?** If not, rewrite it.

| Not a criterion | A criterion |
|---|---|
| The export works | Exporting 500 rows as a user with the `viewer` role produces a file whose row count equals the row count that role sees in the UI, and contains no row from another tenant |
| Errors are handled gracefully | With the provider returning 503, the user sees a visible error naming the retry option; nothing is written to the orders table; the request appears once in the provider log, not three times |
| The page is fast | The pricing page's largest-contentful-paint is under 2.5 s at the 75th percentile on a throttled 4G profile, measured on the built output |
| Users can reset their password | A reset link sent to a real mailbox is single-use: the second use shows an expiry message, and the old password no longer authenticates |

The right-hand column is longer. That is the cost, and it is paid once here instead of repeatedly in
every argument about whether something is done.

## What this skill produces

| Hub item | Note |
|---|---|
| `story` | `DRAFT` → `READY` (requires `acceptance_criteria`) → `IN_PROGRESS` → `DONE` by DEV → `ACCEPTED` **by the PO, and only when linked cases pass** |
| `decision` | Where two requirements conflict, or where a slice needs an operator call |

```
hub.py add story S-12 -f title="Viewer-role export respects row visibility" --role PO
hub.py link S-12 realizes REQ-4
hub.py move S-12 READY -f acceptance_criteria="<the oracle text>" --role PO
```

The hub refuses `READY` without criteria. That is the gate, and it is why this skill cannot be skipped
quietly.

**There is a second gate, and it will surprise you.** A story cannot be `ACCEPTED` until a `case`
linked `verifies` is `PASS` — and **a PO may not create a case** (QA, DEV, designers and analysts
may). So when DEV marks a story `DONE` before QA has written anything, your move is *not*
`REJECTED`: that records a reason against DEV's work for QA's absence. Ask for the case.
`hub.py list --type story --state DONE` is exactly the list of stories waiting on one. And if a
case was linked by mistake and now blocks acceptance, `hub.py unlink <case> verifies <story>
--reason "..."` retracts it as an attributed event rather than an erasure.

## Slicing

A story is a slice through the whole product, not a layer of it. "Build the API" and "build the UI" are
two half-stories that cannot be accepted independently, because neither delivers anything a user can do.

- **Slice by what a user can do afterwards**, even if narrowly: one role, one path, one format.
- **Keep the failure path in the same story as the happy path.** They get separated, the happy path ships,
  and the failure path becomes a finding. The origin engagement's worst findings were all failure paths
  that looked finished.
- **Split on data shape, not on code structure:** "export for a viewer" and "export for an admin" are two
  stories with two different oracles; "export backend" and "export frontend" are not stories.
- **If a story needs a migration, the migration is in it** — with its own criterion about the data that
  existed before.

## Existing product: import, then flag

Do not rewrite someone's backlog. `/product-suite:orient` maps their tracker onto `story` items with
`provenance: reconstructed`. Then do three things, in this order:

1. **Import as-is.** Ids preserved, titles unchanged. Their words, not yours
   (`conventions.md` from orient).
2. **Add the missing criteria** for stories that are about to be worked. Not for the whole backlog — most
   of a backlog is never built, and writing oracles for it is waste.
3. **Flag the untestable ones, do not fix them silently.** A story whose criterion cannot be made into an
   oracle is usually a story whose *goal* nobody agreed. Mark it, and raise a `decision`. Rewriting it
   yourself picks an interpretation on the team's behalf, which is the failure
   `shared/principles.md` §10 names.

A useful number to report, with its denominator: *"of 34 stories in the next two sprints, 11 have criteria
that can be graded by someone other than their author; 23 do not."* That is a measurement of the backlog,
and it is usually the most surprising thing this skill produces.

## Prioritising

This skill does not rank the backlog — the PO and the operator do. What it supplies is the inputs, from the
hub rather than from opinion: which stories realise an approved PRD, which are blocked by an open
`decision`, which carry an open `risk`, and which have no criteria yet and therefore cannot be started.
`hub.py list --type story --state DRAFT` is that last list.

Where a ranking is requested, record it as a profile field or a `decision` with the reasoning, not as the
order of a file — a file order is a ranking nobody can disagree with later, because nobody can see who set
it.

## For the lead

Read three criteria at random from the next sprint and try to grade them without asking the author. That
is the whole review. If you cannot, the sprint will end in a conversation about what "done" meant, and the
cost lands on QA and DEV rather than here.

Second check: **does every story have a failure path in it?** A sprint of happy paths produces a demo that
works and a product that does not.

## Open questions

- Whether `story` should carry its criteria as structured rows (one per criterion, each becoming one case)
  rather than one `acceptance_criteria` text field. Structured would make coverage computable directly;
  it is also more ceremony per story.
- No estimation model here at all, deliberately — but teams will ask, and the right answer may be to record
  their estimate as a field rather than stay silent.
- The slicing heuristics are reasoned, not measured. The "failure path in the same story" rule is the one
  with real evidence behind it, from the origin engagement's findings.

| File | Read it when |
|---|---|
| `${CLAUDE_PLUGIN_ROOT}/shared/principles.md` | First. §3 is the whole skill |
| `${CLAUDE_PLUGIN_ROOT}/shared/references/evidence-standard.md` | What an oracle looks like per surface — web, API, email, binary |
| `${CLAUDE_PLUGIN_ROOT}/shared/domains/` | The product class, for the failure modes a criterion should cover |
