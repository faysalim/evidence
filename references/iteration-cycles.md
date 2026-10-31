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
  "report_dir": "E:/Personal/projects/progress-reports",
  "iteration": 2,
  "scopes": ["website", "app-windows", "saas", "selfhosted", "licensing",
             "secondary", "telemetry", "security", "docs"],
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
  "stopped": null
}
```

**The lead's decision procedure, in order:**

1. Look for `qa-state.json` in the report directory. Ask the operator where reports live if you do not
   know; do not assume the working directory.
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

```
Iteration N (N > 1)
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

For each fix you are about to verify, establish that its code is present:

- Compare the deployed build's commit or digest against the commit that carried the fix.
- Or grep the artifact for a string the fix introduced — the most reliable check, because it tests the
  bytes you are about to exercise rather than a label attached to them.
- For a website, grep the served/built output. For a container, grep the image. For a binary, read its
  metadata and any changed string.

Classify anything not present as `NOT IN BUILD` and exclude it from the Phase 1 pass/fail arithmetic — it
is a deploy question, not a fix question. Say so explicitly so the number is honest: "7 of 9 fixes were
present and testable; 2 are not in this build."

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

**Probabilistic findings** verify at the original rate's denominator or more: a finding reproduced at 3/50
needs at least 50 clean runs — preferably 150 — before `VERIFIED FIXED`. One clean verbatim run is
`VERIFIED (SHORT)` at best, because a single pass of a 3-in-50 bug proves nothing.

**Phase 0 for a cluster is per node.** Treat a mixed-version cluster as `NOT IN BUILD` for fix
verification — it is a legitimate scope-11 target and an illegitimate verification target.

**Phase 2 for a stateful fix** always includes the no-fault baseline reconciliation. The most expensive
regression available is a fix for failover that quietly costs durability in the steady state, and only the
baseline catches it.

## Phase 3 — Full sweep

Past the gate, run the full nine-scope sweep from `scope-playbooks.md` as if it were iteration 1, with two
differences:

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
| 0 — Build identity | 0 | A handful of greps and digest comparisons. Do it inline. |
| 1 — Fix verification | 0–3 | One per repo or per surface family. Often inline for fewer than ten findings. |
| 2 — Regression | 1–3 | Scoped by blast radius, so it is small by construction. |
| 3 — Full sweep | up to the 9-scope / 11-agent budget | Only past the gate. |

A failed gate therefore costs a small fraction of a full iteration. That is the design.

## When to stop iterating

Convergence, not perfection. Stop when any of these is true, and say which:

- A full sweep comes back with no blockers and no majors, and the minors are accepted or scheduled.
- The finding count stops falling across two iterations — that is thrash, and it means something
  structural needs discussion, not another cycle.
- Everything still open is `DECIDE`, `PROCURE`, `DEPLOY`, `RELEASE` or `DATA` — none of which a QA
  iteration can close, because they need the operator, a certificate, or a production action.
- The operator stops it. Their call, always.

State the stopping reason in the final report. "We stopped because everything open needs you" is a real
result and tells the operator exactly what to do next.
