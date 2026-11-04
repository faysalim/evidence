# Ranked index template

The single ranked view. Per-scope files hold the detail; this is what the operator reads first and plans
from. Keep ids stable across iterations and keep closed findings in the table — the arc matters, and a
finding that re-opens three builds later is information a fresh report would hide.

**The report is a product too, and it has users.** If the operator cannot act on it, the run failed
regardless of what it found. So: lead with what to do, not with what you did. Compress each finding's
proof into one sentence, so the index is usable alone by someone who will never open a detail file.
Separate "needs your decision" from "needs a diff" — a decision memo with options and a recommendation
gets answered, while the same content written as a bug report gets argued with (in the origin engagement,
11 of 37 findings were decisions; written as a memo, all 11 were answered in one message). Put the
corrections where they will be read, because they are what tells a reader the rest can be trusted. And
give every number its denominator, so a reader who disagrees with your enumeration can say so.

---

# `<business>` — QA — ranked master index

**Iteration:** `<N>` · **Run date:** `<date>` · **Severity order, most severe first** ·
**De-duplicated across `<n>` scopes**
**Builds under test:** `<component: commit/digest>` … and how each was established — **per node** for a
cluster
**Scope families applied:** `<the applicable ones>` · **N/A:** `<family — one line of reasoning each>`
No secrets anywhere in this set; keys, tokens and passwords are referred to by role only.

**Status key:** `CODE` needs a diff · `DEPLOY` code is right, production is behind · `RELEASE` needs a
build/publish · `DATA` a production data operation · `PROCURE` needs a certificate or account ·
`DECIDE` needs an operator call · `INVESTIGATE` root cause not established ·
`FIXED` fix delivered (see the fix log)

## Verdict

**`<GREEN within stated bounds | NOT GREEN | NO VERDICT>`** for builds `<component: digest>` … on
`<topology / tenant shape / dataset size, as listed by the harness — not as configured>`.

`GREEN` is **computed from the register, never written by hand.** All of the following must hold, each
naming the rows that satisfy it. Any row empty → `NO VERDICT`, and the first line of this report says which
condition failed.

| Condition | Holds? | Rows |
|---|---|---|
| No open `critical` or `blocker`, including any held at `DECIDE` | | |
| Every defect class the applicable domain files mark `critical` or `blocker` has at least one `PASS` case **in a scope whose calibration row passed** | | |
| No `LONG` row unreconciled; none past its cutoff | | |
| No `BLOCKED` or `NOT RUN` row guarding a `critical` or `blocker` class | | |
| Build identity established per component (per node for a cluster) and unchanged since the last case ran | | |
| Smoke row `S<n>-00a` passed on the build and environment this verdict names | | |
| Every operator acceptance requirement (`R-<n>`) has a `PASS`, or the verdict says green is against the docs only | | |

**Any other digest, topology, tenant shape or dataset size than the one named above is untested by this
run.**

### What `GREEN` does not cover

- Scope 8 was `<n>` hours of a bored attacker, not a penetration test.
- Payments ran in test mode: `<declines / 3DS / webhook signature failure>` not exercised.
- `<the N/A families, one line of reasoning each>`
- `<every NOT RUN row, by guarded class>`
- `<author and verifier were the same party — where no separate dev session existed>`

*An unbounded green is the claim this skill exists to prevent. The bounds are the verdict.*

## Iteration summary

*(omit on iteration 1)*

| Phase | Result |
|---|---|
| Case review | cases `<prev>` → `<now>`: `+<n>` from the diff, `+<n>` promoted from `discovered`, `+<n>` adversarial variants made permanent; `<n>` `NOT RUN` re-checked, `<n>` now unblocked |
| 0 — Build identity | `<n>` of `<m>` fixes present and testable; `<list>` not in this build |
| 1 — Fix verification | `<n>` VERIFIED FIXED · `<n>` VERIFIED (SHORT), long form running · `<n>` PARTIAL · `<n>` STILL PRESENT · `<n>` CANNOT RETEST |
| 2 — Regression | `<n>` new findings introduced by fixes: `<ids>` |
| **Gate** | **PASSED → full sweep below** / **FAILED → sweep not run; see "what the next build needs"** |
| 3 — Full sweep | `<n>` new findings |

## Fix verification detail

*(omit on iteration 1)*

| id | Finding | Severity | Status this iteration | Evidence |
|---|---|---|---|---|
| `K1` | Self-hosted activation names the wrong env var | blocker | `VERIFIED FIXED` | 3 runs, only the var name differing; now issues |
| `L5` | `+subaddressing` defeats one-trial-per-email | major | `PARTIAL` | tag stripped on `@a.com`; tag-only local part still mints |

`PARTIAL` means the reported repro passes and the adversarial variant still fails — the approach was right
and the coverage was wrong. It does not pass the gate.

## Product bugs

### Blockers

| # | id | Finding | Product / area | Status | Detail |
|---|---|---|---|---|---|
| 1 | `<id>` | `<one sentence, with the proof compressed into it>` | `<area>` | `<status>` | `<file> §<id>` |

### Majors

| # | id | Finding | Product / area | Status | Detail |
|---|---|---|---|---|---|

### Minors / polish

| # | id | Finding | Status |
|---|---|---|---|

## Experience

*Kept separate from product bugs, because they are a different conversation with a different owner.
Severity here is consequence × reach; anything that tells the user something false appears in both
sections under one shared id.*

### First-run baseline

| Surface | Iter 1 — time / steps / exits | Iter N — time / steps / exits | Call-someone point | Trend |
|---|---|---|---|---|

*Per milestone, not one total. A milestone that got slower, or a step count that grew after a fix, is a
regression no correctness test can see.*

### Error-message audit

`<n>` messages provoked; `<n>` name the specific thing to change (`<pct>`); `<n>` unreachable or swallowed.

### Findings

| # | id | Finding | Area | Reach | Status |
|---|---|---|---|---|---|

### Assessment

*Expert judgement, labelled as judgement: not ranked, not counted in the finding totals, no ids. Three to
five observations, each with its reasoning and a recommendation, routed as `DECIDE`. The test for
inclusion is that the operator can say "no, because…" and have that end it.*

### Accessibility

*Its own subsection because the owner and the fix differ from everything else — or one line: "N/A — no UI;
terminal output checked for colour-only signalling and `NO_COLOR`".*

## Test coverage — what was exercised

Full register in `<report-dir>/test-case-register.md`. This is the denominator for everything above: the
findings are the numerator, and without this section a reader cannot tell a surface that was exercised
hard from one nobody opened.

| | n |
|---|---|
| Cases | `<total>` |
| `PASS` | `<n>` |
| `FAIL` | `<n>` → `<finding ids>` |
| `BLOCKED` · `NOT RUN` | `<n>` · `<n>` — listed under *Not verified* below |
| `LONG` still running | `<n>`, read back at `<when>` |

**Derived from:** `<n>` fault-catalogue entries across `<domain files>` · `<n>` named defect classes ·
`<n>` playbook steps over `<n>` applicable families · `<n>` doc claims (adopted from the claim ledger,
not double-counted) · `<n>` from reverse coverage of `<route table / env reads / option parser>` ·
`<n>` regression cases carried from iteration `<N-1>`.

**Defect classes declared unexercised:** `<name>` — `<why no case could reach it this run>`. Naming these
is the honest version of what otherwise happens silently.

*A bare case count is a boast. With the derivation a reader who disagrees with the enumeration can say so,
which is the point — the same standard this report applies to documentation coverage below.*

## Documentation coverage

| Direction | Coverage | Detail |
|---|---|---|
| Forward — documented claims exercised | `<n>/<n>` (`<pct>`) | PASS `<n>` · FAIL `<n>` · BLOCKED `<n>` |
| Reverse — product surface documented | `<n>/<n>` (`<pct>`) | undocumented: `<n>` env vars, `<n>` routes, `<n>` flags |

**Denominators:** claims extracted from `<list the doc surfaces>`; surface enumerated from
`<route table / env-read grep / parser definitions / config schema>`.

A coverage figure without its denominator and enumeration method is not a result. Undocumented items are
listed individually in the docs scope file, not just counted here.

## Closed in earlier iterations

| id | Finding | Severity | Closed in | How verified |
|---|---|---|---|---|

## Corrections to this report

Where later access — code, a key, a working deployment — disproved something reported earlier. State
plainly which part was right and which was wrong. This section is usually the most-read in the document,
because it is what tells the reader the rest can be trusted.

## Not verified

| What | Why | What would unblock it |
|---|---|---|

Every platform × scope cell that was not executed, every `NOT RUN` and `BLOCKED` register row, every
`BLOCKED` doc claim, every `CANNOT RETEST` finding. A `NOT RUN` row that has survived three iterations is
itself a finding about the test environment — usually `PROCURE` — and belongs in the tables above,
not here.

This is a deliverable, not an apology — and on the next iteration it is the highest-value target list,
so check first whether the access that blocked it has since arrived.

## What the next build needs

*(when the gate failed — this replaces the sweep, and should be short)*

| id | Still wrong | What specifically to change |
|---|---|---|

## Cleanup ledger

Ordered by what is billing or exposed **now**.

| # | Item | Created by | Who can remove it | Cost/exposure until then |
|---|---|---|---|---|

Verify teardown by re-listing resources, not by trusting a delete call's exit code.

## Still the operator's

Deploys, releases, certificates, DNS, production data operations, and decisions. Nothing a QA iteration
can close.

## Stopping reason

*(final iteration only)* Which convergence condition was met: clean sweep · finding count stopped falling
across two iterations (thrash — something structural needs discussion) · everything open needs the
operator · the operator stopped it.
