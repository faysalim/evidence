# Iteration cycles

A QA engagement is rarely one pass. Findings go to the team, a build comes back, and the next iteration
has to answer three different questions in a specific order. Running them out of order is the most common
way a second iteration wastes its whole budget.

## Knowing which iteration you are in

This cannot come from memory. A later iteration usually runs in a **new session** with no recollection of
the first, and the operator will often just say "we fixed those, have another look" — which does not say
whether three findings were fixed or thirty, or which build is now live.

So iteration state lives **on disk**, and reading it is the lead's first action of the run:

**`<report-dir>/qa-state.json`** — small, authoritative for state. The markdown reports stay the human
deliverable; this file is what makes the run resumable.

```json
{
  "engagement": "acme-full-business",
  "report_dir": "<report-dir>",
  "iteration": 2,
  "mandate": {
    "role": "QA",
    "report_only": true,
    "owned_environments": ["the three-node cluster I stood up", "test tenant <id>"],
    "out_of_bounds": ["deploys", "merges", "production config", "the shared staging cluster"],
    "credentials": "test tenant only; no production token was supplied",
    "time_bombs": ["Release builds self-obfuscate under a trial licence"],
    "acceptance_requirements": "<path to the operator's written requirements>"
  },
  "scopes": ["website", "app-windows", "saas", "selfhosted", "licensing",
             "secondary", "telemetry", "security", "docs", "state", "upgrade",
             "experience"],
  "builds_tested": {
    "1": { "website": "dfd358b", "service": "2.5.0-ui6 @ faec816" },
    "2": { "website": "a1b2c3d", "service": "2.5.1 @ 9f8e7d6" }
  },
  "findings": [
    { "id": "K1", "title": "Self-hosted activation names the wrong env var",
      "severity": "blocker", "scope": "selfhosted",
      "status": { "1": "OPEN", "2": "VERIFIED FIXED" }, "closed_in": 2 },
    { "id": "L5", "title": "+subaddressing defeats one-trial-per-email",
      "severity": "major", "scope": "licensing",
      "status": { "1": "OPEN", "2": "PARTIAL" }, "closed_in": null }
  ],
  "cases": [
    { "id": "S5-01", "scope": "licensing",
      "action": "POST /v1/trial with the documented payload, verbatim",
      "oracle": "a usable key arrives in the real mailbox and activates a real binary",
      "result": { "1": "FAIL", "2": "PASS" }, "finding": "K1" },
    { "id": "S5-03", "scope": "licensing",
      "action": "tag-only local part, e.g. +tag@example.com",
      "oracle": "whether a second trial mints for the same mailbox",
      "result": { "2": "FAIL" }, "finding": "L5",
      "note": "adversarial variant of L5; permanent from iteration 2" },
    { "id": "S10-04", "scope": "state",
      "action": "partition one node for 60s under write load, heal, read back both sides",
      "oracle": "both sides agree with my own acknowledged-write ledger after heal",
      "guards": { "class": "divergence after heal", "ceiling": "critical" },
      "touches": ["membership", "replication"],
      "provenance": "derived", "source": "fault-catalogue",
      "ran_under": { "topology": "3 nodes listed, RF2, 64 partitions", "n": 20000,
                     "duration": "20m", "load": "2k ops/s",
                     "ran_by": "scope-10-agent", "at": "2026-11-04T09:12:00Z" },
      "result": { "1": "NOT RUN", "2": "NOT RUN" },
      "blocked_by": "only two hosts available on this machine" }
  ],
  "not_verified": [
    { "what": "macOS installer and Gatekeeper", "why": "no macOS host in this engagement",
      "unblocked_by": "any current macOS host", "cases": ["S2-11"], "since_iteration": 1 }
  ],
  "cleanup": [
    { "item": "3-node cluster, region <r>", "created_by": "iteration 1",
      "removable_by": "me", "cost": "billing per hour", "status": "TORN DOWN",
      "verified_by": "re-listed instances: NONE" },
    { "item": "test tenant <id>", "created_by": "iteration 1",
      "removable_by": "operator", "cost": "consumes a seat", "status": "OPEN" }
  ],
  "stopped": null
}
```

Four of those fields exist because a resumed run cannot work without them and nothing else carries them:

- **`mandate`** — otherwise iteration 2 re-asks the operator what it may touch, or worse, guesses. Which
  environments are *yours to break* is the field that decides whether the state scope can run at all.
- **`cleanup`** — this is the one that bills money if a run dies mid-sweep. A ledger that lives only in a
  markdown report is a ledger nobody inherits. Status stays `OPEN` until a **re-listing** verifies it.
- **`not_verified`** — Phase 3 calls these the highest-value targets of the next iteration, so they have to
  survive the session that found them. `since_iteration` is what makes "this has been blocked for three
  rounds" visible, which is itself a `PROCURE` finding.
- **`findings[].status_action`** — the closing action (`CODE` / `DEPLOY` / `RELEASE` / `DATA` / `PROCURE` /
  `DECIDE` / `INVESTIGATE`), because "22 bugs" of which nine are deploy lag is not a plan.

The `cases` array is the run's denominator and carries forward exactly as `findings` does: ids are names,
never positions, and a case is never retired for passing — it is the regression suite.
`references/test-cases.md` has the contract. Phase 2's selection is computed from this array, which is why
it is cheap: the `PASS`
cases whose subject falls in the diff's blast radius, rather than a guess at what the fix might have
disturbed. A `NOT RUN` row whose `blocked_by` has not changed in three iterations is itself a finding about
the test environment, usually `PROCURE`; promote it into `findings` rather than letting it ride.

**The lead's decision procedure, in order:**

1. Look for `qa-state.json`. Check `./qa-reports/` first — that is the default convention, so an
   ordinary first run costs no question — then anywhere the operator has named. Ask only if neither exists
   and the operator has described a prior run.
2. **Found it** → this is `iteration + 1`. Run Phases 0–2 before anything else.
3. **Not found, but prior report files exist** (ranked index, findings files) → this is still a later
   iteration. Reconstruct the register from those reports, write `qa-state.json` from it, and say in the
   report that you reconstructed it — the operator needs to know the ids came from parsing, not from state.
4. **Nothing found, and the operator describes no prior run** → iteration 1. Create `qa-state.json` as
   your first write, before testing, so an interrupted run is still resumable.
5. **Ambiguous** — the operator says "re-test the bugs" but you can find no register at all. Ask. One
   question costs far less than a sweep that re-reports known findings as new.

Update the file at the end of every phase, not just at the end of the run. A run that dies mid-sweep
should leave behind enough state for the next session to resume rather than restart.

## Agents never infer the iteration — they are told

A scope agent has no view of the engagement, so asking it to work out which round it is in invites it to
guess wrong and sweep when it should be verifying. The lead puts the round and the phase in the brief,
explicitly, along with that scope's open findings. `assets/agent-brief.md` is the template; the fields
that matter here:

```
Iteration: 3 of an ongoing engagement
Phase:     FIX VERIFICATION  (not a sweep — do not look for new issues yet)
Build:     website a1b2c3d — Phase 0 confirmed it contains the fixes for W5, W7
Your open findings: W5 (major), W7 (major)  — full text below
Deliverable: a status per finding, from the status vocabulary, with evidence
Out of scope this phase: anything not in the list above
```

The "out of scope this phase" line matters more than it looks. An agent briefed on a verification phase
that finds a new unrelated issue should **report it as an observation, not chase it** — otherwise the
cheap phase quietly becomes a sweep and the gate's cost asymmetry is lost. Observations get triaged by the
lead and go into Phase 3's target list.

## The case review — the lead's first act of every iteration

Before Phase 0, and before anyone is briefed, the lead revisits the case set. Zero agents, minutes of work,
and it is not optional: **there is always more to add, and the previous round is what generates it.**
`references/test-cases.md` has the contract; the five steps are:

1. **Promote last round's `discovered` cases** to permanent `derived` ones, and ask which source should
   have predicted each. Where the answer is a domain file's fault catalogue, that file is wrong — a PR to
   the skill is part of this engagement's output.
2. **Add every new finding's repro** as a permanent case, plus every adversarial variant Phase 1 will
   require as a separate permanent case. This is how last round's missing coverage stops being missing.
3. **Derive against the diff.** Fixes create surface — new environment variables, flags, endpoints, config
   keys, migration paths. Re-run the reverse enumeration over the changed components and add a case per new
   thing; a fix is the most common way untested surface enters a product.
4. **Re-check every `NOT RUN`** for access that has since arrived. Known blind spots are the round's
   highest-value targets.
5. **Never prune.** `PASS` cases are the regression suite, `NOT RUN` cases are the blind-spot list, and a
   case removed for tidiness is coverage silently withdrawn.

Report the growth: `cases 214 → 238 (+19 from the diff, +5 promoted)`. A set that stops growing while
findings keep arriving means the findings come from somewhere the set cannot see — a conversation, not
another cycle.

```
Iteration N (N > 1)
  Case review                   — the denominator, before anything else
  Phase 0   Build identity      — does this build actually contain the fixes?
  Phase 1   Fix verification    — does each reported finding now behave correctly?
  Phase 2   Regression          — did the fixes break anything adjacent?
  ── GATE ── all of Phase 1 verified AND Phase 2 clean?
  Phase 3   Full sweep          — only past the gate
```

## Why the gate exists

A full sweep against a build with unverified fixes produces a report the operator cannot act on: it is
dominated by findings they already know about, new issues are buried among re-reported old ones, and
nobody can tell which is which. Worse, it spends the expensive phase — the sweep is the bulk of the agent
budget — to learn something Phase 1 could have told you in a fraction of the time.

So when the gate fails, **stop and report**. A short, fast "three of nine fixes did not hold, and here is
exactly how each one still fails" is far more useful on the day than a 40-page sweep. The team fixes the
three, ships another build, and the next iteration starts again at Phase 0.

The only legitimate reason to sweep anyway is the operator explicitly asking for it — they may have
business reasons to want breadth now and depth later. Record that it was their call.

## Phase 0 — Prove the build contains the fixes

Never skip this, and never infer it from a version number. Verifying a fix against a build that does not
contain it produces a **false FAIL**, which is worse than no test at all: the team re-fixes working code,
and trust in the whole report drops.

The prior engagement is the cautionary tale in both directions: a merged fix was absent from the serving
image, and a published `2.5.0` image predated its own `release/2.5.0` branch tip. Had the next iteration
trusted the tag, it would have reported a correct fix as broken.

**When a separate dev session delivered the build, Phase 0 has a cheaper predecessor:** check the handback
packet is complete before briefing anyone. No build digest per component, any finding still `NEW`, or
missing fail-first evidence → return it unread (`references/dev-handoff.md`). A returned handback costs one
message; the alternative is a verification round whose result is `NOT IN BUILD` for half the register.
Phase 0 still runs — the handback is a claim about which build contains what, and Phase 0 is the
independent check of that claim. A complete handback does not excuse it.

For each fix you are about to verify, establish that its code is present:

- Compare the deployed build's commit or digest against the commit that carried the fix.
- Or grep the artifact for a string the fix introduced — the most reliable check, because it tests the
  bytes you are about to exercise rather than a label attached to them.
- For a website, grep the served/built output. For a container, grep the image. For a binary, read its
  metadata and any changed string.

Classify anything not present as `NOT IN BUILD` and exclude it from the Phase 1 pass/fail arithmetic — it
is a deploy question, not a fix question. Say so explicitly so the number is honest: "7 of 9 fixes were
present and testable; 2 are not in this build."

Where a dev session claims a test automates a case, Phase 0 also **greps the build for that test**. A named
test that is not in the artifact is `NOT IN BUILD` like any other claim.

## Phase 0b — Prove the build serves

Build identity says the right bytes are deployed. It does not say the product starts, and nothing else here
checks before three agents enter Phase 1 and discover it one finding at a time — recording `STILL PRESENT`
against every fix when the real answer is that the build is dead.

So after Phase 0 and **before anyone is briefed**: one smoke row per component, `S0-<component>`, whose
oracle is that component's first-success milestone through the real client. Zero agents, minutes.

A `FAIL` here briefs nobody. Classify it `DEPLOY` / `RELEASE` / `INVESTIGATE`, deliver a one-page
turnaround, and stop — it is not a finding against the product until the environment has been shown to be
what the brief says it is. Re-run it after any environment reschedule: a pod that moved can lose the config
that made the listing true, and an environment addressed by the wrong name reports zero instances with no
error at all. Three and a half hours of a churn test were once spent on an environment that was not what it
was believed to be.

## Phase 1 — Fix verification

The repro you wrote in iteration 1 **is** the verification test. This is the practical reason findings need
an exact, re-runnable repro: a vague finding cannot be verified, so it stays open forever and the register
never converges.

For each finding, run two things:

1. **The original repro, verbatim.** Same inputs, same command, same payload. Anything else is a different
   test.
2. **One adversarial variant.** Fixes that handle only the exact reported case are extremely common,
   because the reported case is what the author tested against. If the finding was `+tag` subaddressing
   defeating per-email uniqueness, the variant is a different domain, a tag-only local part, mixed case,
   and whitespace — the neighbours of the reported input, not the input itself.

Assign one status per finding:

| Status | Meaning |
|---|---|
| `VERIFIED FIXED` | Original repro and the adversarial variant both behave correctly |
| `PARTIAL` | Original repro fixed, variant still fails — the fix is too narrow |
| `STILL PRESENT` | Original repro still reproduces |
| `NOT IN BUILD` | Phase 0 showed the code is absent; not a fix failure |
| `CANNOT RETEST` | Access, platform or credential gap — say what would unblock it |
| `VERIFIED (SHORT)` | Short-form run reconciled; long form started, not yet complete. Passes the gate for proceeding; does not close the finding |
| `FIXED DIFFERENTLY` | The behaviour is now correct but by another route than expected; verify the new route and note it |

`PARTIAL` is the status people skip, and it is the one that matters most: it tells the team the fix
approach was right and the coverage was wrong, which is a different conversation from "it still fails".

**If the same finding fails verification twice across iterations, escalate rather than loop.** Two failed
cycles mean the fix approach is wrong or the root cause was misdiagnosed, and a third round of the same
patch will not change that. Re-open the root-cause question explicitly — and check whether your own
iteration-1 diagnosis was the thing that was wrong.

## Phase 2 — Regression

Regression is scoped by **blast radius**, not by re-running everything — that is what Phase 3 is for.
Derive the radius from the actual diff between the previous build and this one:

- Every surface the changed files render, serve or control.
- Every caller of a changed function, and every consumer of a changed response shape or schema.
- Shared infrastructure the fixes touched: layouts, middleware, base templates, shared config, generated
  manifests, build pipeline.
- The **other** locales, platforms and deployment modes of anything that changed. A fix verified in English
  on Windows is not verified in Spanish on macOS.
- The paths the fixes route *through* rather than the paths they changed. This is where the subtle ones
  live: a locale redirect built on a path-only map silently dropped the query string, which would have
  reintroduced the exact defect a fix had just removed, one redirect later. The fix was correct; the
  surrounding path undid it.

Also re-run every previously `PASS` check that touches a changed surface. A fix that repairs one finding
and breaks a neighbouring behaviour is the single most expensive outcome of a fix phase, because it ships
with the team's confidence behind it.

Regression findings are **new findings** and get new ids — never recycle the id of the finding whose fix
caused them. The causal link goes in the body: "introduced by the fix for K1".

## The gate

Pass requires **both**: every Phase 1 finding is `VERIFIED FIXED`, or `VERIFIED (SHORT)` with its long
form running (or `NOT IN BUILD` / `CANNOT RETEST`, which are not fix failures but must be listed), and
Phase 2 is clean.

`PARTIAL` does not pass the gate. A too-narrow fix is an open finding.

When the gate fails, deliver: build identity, the per-finding status table, every regression with its
repro, and what the next build needs to contain. Nothing else. Keep it short — it is a turnaround
document, not a report.

## When a verification run takes hours

The gate's economics assume Phases 0–2 are cheap. A durability certification, a full backfill, a
device-matrix sweep or a soak run is not, and holding the sweep hostage to a 12-hour run wastes the day in
the other direction. Two changes, and only two:

1. **Two speeds of verification.** Every long check has a short form — same procedure, small N, short
   duration, hard cutoff, stall detector — and a long form. The gate runs on the short form. The long form
   runs in the background as a job you start and return to, never an agent that waits. The finding stays
   at `VERIFIED (SHORT)` until the long form reconciles, when it becomes `VERIFIED FIXED`. A finding never
   closes on the short form alone, and the report says which it is.
2. **Ladder, don't leap.** 1h → 3h → 12h, each stage only after the previous reconciles. A run that fails
   at hour eleven on what the one-hour run would have shown cost eleven hours; a run that stalls at hour
   two unnoticed until morning cost more. Every long run has a progress signal and exits itself when that
   signal freezes.
3. **A `LONG` row is a lien on the report.** The report may be *delivered* with `LONG` rows open; it cannot
   carry a verdict while one is, and its first line says how many are open and when they read back. A
   `LONG` row past its cutoff with no read-back is **not** `NOT RUN` — it is `FAIL → INVESTIGATE` against
   the harness or the environment, because a run that cannot finish is a result. Whoever reads the long
   form back amends the verdict in writing under *Corrections*, even when the answer is "still green". The
   12-hour run that would have shown 39,760 missing keys was started, never read back, and the index said
   no blockers.

**Probabilistic findings** verify at the original rate's denominator or more: a finding reproduced at 3/50
needs at least 50 clean runs — preferably 150 — before `VERIFIED FIXED`. One clean verbatim run is
`VERIFIED (SHORT)` at best, because a single pass of a 3-in-50 bug proves nothing.

**Phase 0 for a cluster is per node.** Treat a mixed-version cluster as `NOT IN BUILD` for fix
verification — it is a legitimate scope-11 target and an illegitimate verification target.

**Phase 2 for a stateful fix** always includes the no-fault baseline reconciliation. The most expensive
regression available is a fix for failover that quietly costs durability in the steady state, and only the
baseline catches it.

## Phase 3 — Full sweep

Past the gate, run the full sweep over every applicable family from `scope-playbooks.md` as if it were
iteration 1, with two differences:

- **Carry the register forward.** Previously-closed findings stay in the document as closed, with the
  iteration that closed them. The operator needs to see the arc, and a finding that re-opens three
  iterations later is important information that a fresh report would hide.
- **Bias toward what changed and what you could not reach last time.** Previously `BLOCKED` and
  `CANNOT RETEST` items are the highest-value targets, because they are the known blind spots. Check at the
  start of the iteration whether the access that blocked them has since arrived.

Documentation conformance (scope 9) deserves specific attention in later iterations: fixes change
behaviour, and the docs that described the old behaviour are now wrong. Re-run the forward claim set for
every surface the fixes touched, and redo the reverse enumeration — fixes add environment variables,
flags and endpoints, and a new undocumented surface is created by the very act of fixing.

## The finding register

One register across all iterations, with **stable ids that are never reused or renumbered**. An id is a
name, not a position; renumbering between iterations destroys the ability to discuss anything across
builds. Prefix by scope so the id says where it came from (`K1`, `L5`, `T1`, `G2`, `W7`), and keep the
numbering sparse so later findings in the same scope can slot in.

Per finding, carry forward: id, title, severity, scope, status per iteration, and the iteration that
closed it. Template in `assets/ranked-index.md`.

## Agent budget per phase

Phases 0–2 are narrow, so they are cheap, which is the other half of the gate's value:

| Phase | Agents | Why |
|---|---|---|
| Case review | 0 | The lead updates the denominator. Minutes, inline, never skipped. |
| 0b — Build serves | 0 | One smoke row per component, through the real client. A `FAIL` here briefs nobody. |
| 0 — Build identity | 0 | A handful of greps and digest comparisons. Do it inline. |
| 1 — Fix verification | 0–3 | One per repo or per surface family. Often inline for fewer than ten findings. |
| 2 — Regression | 1–3 | Scoped by blast radius, so it is small by construction. |
| 3 — Full sweep | up to the applicable-family / 11-agent ceiling | Only past the gate. |

A failed gate therefore costs a small fraction of a full iteration. That is the design.

## When to stop iterating

Convergence, not perfection. Stop when any of these is true, and say which:

- The verdict computes to `GREEN within stated bounds` and the minors are accepted or scheduled. A sweep
  with no blockers but with a `critical` class unexercised, a `LONG` row still open, or a data finding held
  at `DECIDE` has not converged — it has stopped looking.
- The finding count stops falling across two iterations — that is thrash, and it means something
  structural needs discussion, not another cycle.
- Everything still open is `DECIDE`, `PROCURE`, `DEPLOY`, `RELEASE` or `DATA` — none of which a QA
  iteration can close, because they need the operator, a certificate, or a production action.
- The operator stops it. Their call, always.

State the stopping reason in the final report. "We stopped because everything open needs you" is a real
result and tells the operator exactly what to do next.
