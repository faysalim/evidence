# Agent brief template

Copy this per scope agent. An agent only knows what the brief tells it — it cannot see the engagement, the
other scopes, or which round this is. Everything it needs to avoid guessing goes here.

**Fill in `<ABSOLUTE PATH>` before you send this.** The brief is copied *verbatim* into an agent
that has no plugin context: `${CLAUDE_PLUGIN_ROOT}` is substituted only into a skill's own text at
load, so it will arrive at the agent as literal characters and every path in the brief will resolve
nowhere. The lead reads the expanded root from its own SKILL.md and pastes it here. This is the one
artifact in the method where a variable cannot do the work for you.

The two fields people leave out are the two that cause the most waste: **Phase** (an agent that thinks it
is sweeping will sweep) and **Out of scope this phase** (without it, a verification agent drifts into a
sweep and the gate's cost advantage evaporates).

The field that must not be softened is **Cases**. The scope's finalized case set is the agent's first
deliverable and a gate on it starting — an agent that is merely encouraged to keep a register will produce
one from memory at the end, which defaults to green and loses every `NOT RUN` row.

---

## Iteration and phase

```
Iteration:  <N> of an ongoing engagement   |   first iteration
Phase:      FIX VERIFICATION | REGRESSION | FULL SWEEP
Build under test:
  <component>: <commit / digest / version>  — Phase 0 confirmed it contains <fix ids>
Out of scope this phase:
  <explicitly: anything not listed below. Report new issues as one-line OBSERVATIONS; do not chase them.>
```

## Mandate

```
Report only, or fix?    <report-only | fix, delivered as ...>
Out of bounds:          <deploys, merges, production config, destructive ops against state
                         you did not create>
Environment ownership:  <this cluster / tenant / device / dataset is YOURS — kill, partition,
                         delete, upgrade it freely>
                        | <shared or production — read-only, non-destructive>
Credentials:            <test tenant only; which ones you have; which you do not>
Known time bombs:       <self-obfuscating builds, seat consumption, per-hour billing, ...>
Long-running checks:    <short form: N=…, cutoff=…, stall-exit=…>
                        | <long form: START it and return; do not wait on it>
```

**Environment ownership is the field that decides whether you can test at all.** Destructive is defined by
whose state it destroys, not by the verb: killing a node in a cluster you stood up is testing; restarting
a shared one is not. If no owned environment is available, say so and mark that work `BLOCKED` — that is a
result, not a failure.

## Business context

```
Products and what they are:        <one line each>
Live hosts and deployment modes:   <...>
Which branch actually deploys:     <per repo — from hosting config, not the repo default>
Which build is currently live:     <per component, with the commit delta from the branch tip>
Recently changed, re-verify:       <claims the team believes are already fixed>
```

## Your scope

```
Scope:           <name, e.g. "Entitlement lifecycle">
Domain file:     <ABSOLUTE PATH>/shared/domains/<domain>.md   — read this first; it maps
                 onto this product class and defines what "first success" means here
Playbook:        <ABSOLUTE PATH>/skills/qa/references/scope-playbooks.md §<n>
Standard:        <ABSOLUTE PATH>/shared/references/evidence-standard.md
Cases:           <ABSOLUTE PATH>/skills/qa/references/test-cases.md
                 YOUR FIRST DELIVERABLE, before any test runs:
                 the finalized case set for this scope, each case with its action and its
                 ORACLE. Derive it from the domain file's fault catalogue (one case per
                 entry), its named defect classes (each needs a case that would catch it, or
                 say so), and your playbook's steps. Return the set, then execute it. Cases
                 you find during execution are added and marked `discovered`; none is ever
                 deleted — an inapplicable one resolves as NOT RUN with that reason.
                 Then run `S<n>-00a` (smoke: first success, no faults, real client) and
                 `S<n>-00b` (calibration: inject ONE known defect, show the oracle reports
                 exactly one) BEFORE any other row. A scope without a passed `00b` has no
                 PASS rows — every PASS in it is NOT RUN (uncalibrated).
                 Execute in DESCENDING severity ceiling of the class each row guards, so a
                 budget that runs out leaves cheap rows undone rather than fault runs.
                 When something smells wrong, follow it BEFORE finishing the list, then add
                 the row as `discovered`. The list is the floor, not the ceiling
Docs rule:       read your surface's documentation and run what it tells a customer to run,
                 verbatim. Report divergences to the docs owner (scope 9), do not file them.
First contact:   <YES — you are the first to touch this surface. Time and trace the path to
                  first success, per milestone, before reading more than the quickstart;
                  return the trace to the experience owner (scope 12)>
                 | <WARM — another scope already installed this; skip the first-run, keep
                  the error inventory>
Error inventory: <return every error message, WARN-or-above log line and exit code you
                  provoked, verbatim, with the action that caused it>
```

You are the coldest party available for your surface and nobody can retake that measurement later — which
is why the first-run trace is delegated to you rather than to a dedicated experience agent, who would be
warm by definition. You are **agent-cold**, not a genuine first-time user: you already know this class of
product. Say so in the trace.

**The trace is exempt from the case gate and precedes it.** On `First contact: YES`, take it with the
quickstart only and record it as a row, *then* read the domain file and finalize your set. An agent that
has just read a fault catalogue is no longer discovering anything.

## Open findings in your scope (verification and regression phases only)

```
<id> — <severity> — <title>
  Original repro, verbatim:  <steps / command / payload / URL>
  Expected:                  <...>
  Previously observed:       <...>
```

For each: run the original repro **verbatim**, then **one adversarial variant** — the neighbours of the
reported input, not the input itself. Return a status per finding from this vocabulary:

`VERIFIED FIXED` · `PARTIAL` (original fixed, variant still fails) · `STILL PRESENT` ·
`NOT IN BUILD` · `CANNOT RETEST` (say what would unblock it) · `FIXED DIFFERENTLY` ·
`VERIFIED (SHORT)` (short form reconciled, long form still running — passes the gate for
proceeding, does not close the finding)

Report the variant you actually used, **verbatim**, with your verdict. A `PARTIAL` the other side cannot
reproduce becomes an argument instead of a status.

## What to return

```
FIRST, before you execute anything:     the finalized case set — id, action, oracle, and
                                        which source each case was derived from. This is a
                                        gate on starting, not a formality
THEN, the same rows filled in:          result (PASS / FAIL / BLOCKED / NOT RUN / LONG),
                                        evidence, and `derived` or `discovered` per case.
                                        A PASS with no evidence is a NOT RUN — write NOT RUN.
                                        An oracle that is the product's own report of itself
                                        (health endpoint, green build, the product's own
                                        counters) is not an oracle; the row is not a case
Per finding (verification/regression):  id, status, evidence, the exact invocation used
Per new finding (sweep):                the finding template named in your brief
First-run trace (first contact only):   time and steps per milestone, exits from the product,
                                        concepts before first success, guesses, doc round-trips,
                                        empty states, the call-someone point
Error inventory:                        verbatim, with the action that caused each
Not verified:                           every platform × check you could not execute, and why
Observations:                           one line each, un-chased
```

Rank most severe first. Severity is by consequence, not by effort — a one-line fix can be a blocker.
Never put a secret in your output; refer to credentials by role.

## Prime directive, repeated because it is the thing that fails

Do the thing. Don't check that the thing responds. Request the real key, run the real binary, submit the
real form, read the real email, deploy the real image. Status 200 is not a passing test, a green build is
not a passing test, and `/health` returning `ok` is not a passing test.

**Then go back and check the thing is still there.** If your surface keeps data, the operation returning
OK is a *response* — the thing is the state it was supposed to produce, measured independently after the
failure the docs say is survived, graded against your own ledger of what the product acknowledged and
never against the product's own counters.

If you could not execute something, say so — an honest gap is useful; a silent gap dressed as a pass is
the failure this whole engagement exists to avoid.
