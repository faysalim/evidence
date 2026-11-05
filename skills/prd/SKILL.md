---
name: prd
description: Write a product requirements document: the problem, who has it, success metrics measurable with a stated denominator and baseline, and an explicit non-scope. For an existing product it reconstructs a current-state PRD from what the product does, then states the change as a delta. Use when the user wants a PRD, product brief, spec or one-pager written or reviewed, scope defined, or success criteria agreed before build. Not for stories - that is evidence:backlog.
---

# PRD

`status: draft` — see `${CLAUDE_SKILL_DIR}/README.md`.

A PRD fails in one of two ways, and both are invisible at the time. It describes a solution without ever
stating the problem, so nobody can later tell whether it worked. Or it has a success metric with no
denominator — *"increase activation"* — which cannot be read, only asserted.

So this skill enforces three things from `shared/principles.md`: **every number has a denominator** (§2),
**an oracle exists outside your own judgement** (§3 — a success metric a different person cannot read the
same way is not a metric), and **what this does not claim** (§4 — here it is the non-scope, and it is the
most-read section of any PRD).

Items move only through `python "${CLAUDE_PLUGIN_ROOT}/shared/scripts/hub.py"`.

## What this skill produces

| Hub item | Note |
|---|---|
| `prd` | `DRAFT` → `REVIEW` → `APPROVED` by the sponsor or Head of Product — **never by its author** |
| `metric` | One per success criterion, each `DEFINED` with its denominator before anything is built |
| `decision` | Where scope needs an operator call rather than a PM's preference |

Link `prd` back to the insights it rests on (`derived_from`) and forward to nothing — stories come later,
and a PRD that already lists its stories has skipped the problem.

## The document

Nine sections. Each is here because its absence has a specific cost.

```
1  Problem            Whose problem, what it costs them today, how you know
2  Users              Who, with the second user named (there is rarely one)
3  Current state      What happens today, including the workaround people use
4  Success metrics    Measurable, each with its denominator and its baseline
5  Scope              What this does
6  Non-scope          What this deliberately does not do, and why
7  Constraints        Regulatory, contractual, technical, deadline
8  Risks              What would make this not work
9  Open decisions     Routed to the operator as decision items, not guessed
```

**§1 Problem.** One paragraph, no solution in it. "How you know" links to `insight` items — a problem with
no evidence behind it is a hypothesis, and the PRD says so rather than quietly promoting it.

**§2 Users.** Name the second user. A feature for an end user is almost always also a feature for the admin
who configures it and the support agent who explains it when it breaks. The one you forget is the one who
files the complaint.

**§4 Success metrics.** The section that decides whether this PRD can ever be assessed. Each metric needs:

```
name          Activation rate
definition    % of signups that complete first success within 7 days
denominator   signups in the period, excluding internal and test accounts
baseline      current value, measured — not estimated
target        value, and by when
instrumented  yes / no / NOT YET — if no, that is work in scope
```

**A target with no baseline is not a target.** If the baseline is unknown, the first deliverable is
measuring it, and that goes in scope. Create each as a `metric` item now, so
`/evidence:analytics` inherits a definition rather than inventing one after launch.

**§6 Non-scope.** Write what a reader would reasonably assume is included and is not, with the reason.
"Not doing SSO, because the three named customers asking for it are all on the smaller plan" is useful; an
empty non-scope section means the PRD has no edges and every reviewer will imagine different ones.

## Existing product: reconstruct first, then state the delta

This is the part that separates this skill from a template. For an existing product, **do not write a PRD
for the change.** Write two things:

1. **A current-state PRD**, reconstructed from `/evidence:orient`'s capability inventory — which was
   enumerated from the product, not from its documents. Mark it `provenance: reconstructed`. It will be
   uncomfortable: it records what the product *does*, including the parts nobody designed and the parts the
   docs describe differently.
2. **The change, as a delta against it.** What moves, what is removed, what is left alone.

Why this order, and it is not ceremony: a change described against an imagined current state silently
re-specifies behaviour nobody intended to touch, and engineering then discovers it as a regression.
`shared/principles.md` §10 — when docs, tickets and code disagree, the disagreement is the finding, and the
current-state PRD is where you write it down.

For a new product there is no current state. Say that explicitly rather than leaving §3 blank.

## Review

A PRD is `APPROVED` by the sponsor, not its author, and the hub enforces it. Before sending it:

- Every metric has a denominator and a measured baseline, or is flagged `NOT YET` with that measurement in
  scope.
- The non-scope is non-empty.
- Every open question is a `decision` item, not a parenthesis in the text. Operators answer memos with
  options and a recommendation; they argue with prose.
- For an existing product, the current-state PRD exists and is linked.

```
hub.py add prd PRD-1 -f title="Self-serve trials" --role PM
hub.py add metric M-1 -f name="trial-to-paid" -f denominator="trials started, excluding internal" \
       -f baseline="unknown -- measuring is in scope" --role PM
hub.py link PRD-1 measures M-1
hub.py move PRD-1 REVIEW --role PM
```

## For the lead

Read §4 and §6 first, in that order, and nothing else at first. If the metrics have no denominators or the
non-scope is empty, the rest of the document cannot be reviewed — send it back on those two alone. Then ask
the question a PRD most often cannot answer: **what would we see if this did not work?** A PRD whose
success and failure look identical in the data is not reviewable, and that is the cheapest thing to catch
now rather than a quarter later.

## Open questions

- Whether `prd` should require a linked `metric` to reach `REVIEW`, the way `story` requires linked cases
  to be accepted. It would be consistent; it may be too strict for a one-page brief.
- No template file ships yet — the nine sections above are the template. If two teams shape it
  differently, add one.
- The current-state-PRD-then-delta pattern is reasoned from the origin engagement's Step 1 lessons, but has
  not itself been run on an engagement.

| File | Read it when |
|---|---|
| `${CLAUDE_PLUGIN_ROOT}/shared/principles.md` | First. §2, §3, §4 and §10 govern this skill |
| `${CLAUDE_PLUGIN_ROOT}/shared/domains/` | The product class, for what "first success" means here |
| `${CLAUDE_PLUGIN_ROOT}/shared/references/experience.md` | Defining first success concretely, per milestone |
