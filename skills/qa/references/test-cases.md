# Test cases: design them, prove the harness, then publish them

A report that lists only findings tells the reader what broke and nothing about what held. They cannot
tell a surface that was exercised hard and passed from one nobody opened, so they cannot trust the
silence — and silence is most of any report. The test-case register is what makes the silence mean
something.

This skill already refuses a documentation-coverage number without its denominator. **The register is the
same rule applied to the whole run.** Without it, "we tested the product" is exactly the claim the prime
directive exists to destroy: it sounds like a result and carries no information.

It is also the thing the verdict is computed from
(`${CLAUDE_PLUGIN_ROOT}/skills/qa/assets/ranked-index.md`). A register nothing can refuse
is decoration; this file is mostly about what can refuse it.

## The row

| Field | Content |
|---|---|
| `id` | Stable, scope-prefixed — `S10-07`. Its own namespace, never a finding id. Never renumbered. |
| `scope` | The family, journey or requirement it belongs to. |
| **action** | The exact thing done: command, request with payload, UI sequence, fault injected. Copy-pasteable, one variable at a time. |
| **oracle** | What independently answers PASS or FAIL, and **where that answer comes from**. |
| **guards** | The defect class this row would catch, and that class's severity ceiling from the domain file. |
| **ran under** | Build per component; topology, tenant shape or device **as listed by the harness, not as configured**; N, duration, load; who or which agent ran it, and when. |
| `touches` | Component, route, surface or file set — what Phase 2 selects on. |
| `result` | `PASS` · `PASS (SHORT)` · `FAIL` · `BLOCKED` · `NOT RUN` · `LONG` |
| `evidence` | The raw artifact, or a pointer to it. On `FAIL`, also the finding id. |
| `provenance` | `derived` (existed before execution) or `discovered` (found during it), plus which source. |

Four of those do real work and each is here because its absence is a documented way a broken product ships.

### The oracle

> **A case whose oracle is the product's own report of itself is not a case.**

That is the register-level form of "status 200 is not a passing test". `/health: ok` is not an oracle. The
cluster's own `missing: 0` counter is not an oracle; your own ledger of what the product acknowledged,
diffed against what you can read back, is. "The settings page shows the role is restricted" is not an
oracle; the export taken as that role is. A green build is not an oracle for anything at all.

And the independent thing must **predate the run and exist outside both the product and your own
judgement**: the operator's price list, the curriculum's answer key, your ledger written at ack time, the
published spec, a pre-backup fingerprint, a count. *"Looks right"*, *"renders correctly"* and *"behaves as
expected"* name no reference and are not oracles — they are the agent's eyes, which is the same failure one
level up. A pricing row whose oracle was "the three tiers display 49/149/449" passed while the page's
structured data said 39/119/249 and search engines published that as the offer. The row must say what was
compared against what, and if there are three places a price lives, all three are in the action.

Second hard rule, which kills more decoration than any other:

> **A `PASS` with no evidence is a `NOT RUN`.** Record it as `NOT RUN`.

### `guards`, and the order of execution

One defect class per row, with that class's severity ceiling. A row that guards nothing nameable is
padding and does not go in.

**Execute in descending severity ceiling.** An agent with ninety-six equal-looking rows and a budget runs
the sixty cheap ones and marks thirty-six `NOT RUN — out of time`: honest, and still a false green,
because the thirty-six were the fault runs. The `NOT RUN` list is sorted the same way, and **a `NOT RUN`
guarding a `critical` class is reported above the first finding, not below the last.**

### `ran under`, and why a bare `PASS` is not enough

A row that records no environment, scale or duration makes a thirty-second run at RF1 on one node the same
`PASS` as a twelve-hour run at RF3. Seventeen fault-catalogue entries, each run for thirty seconds, each
`PASS`, against a convergence defect whose window was measured at 88–122 seconds: that is the purest false
green available, and it costs nothing to prevent.

Record the topology **as the harness lists it, not as you configured it.** A console-mode certification
addressed its workspace by loopback, got zero instances with no error, and every read-back diffed 0 against
0. The configuration said three nodes. The listing said none.

> **A `PASS` below the domain's short form is `PASS (SHORT)`.** Every fault catalogue implies a minimum N,
> duration and load. A row run under that is honest and cheap and is not a pass: it satisfies nothing in
> the verdict until its long form reads back.

## The gate: the set, plus two rows that run

**Every scope's first deliverable is its finalized case set**, written before the first test. Not a sketch,
not an intention to keep notes — the set, each case with its action, oracle and guarded class. An agent
that has not produced it has not started.

It is the method's only **entry criterion**, and the method needs one. Everything else here gates an
*exit*: the evidence standard gates a finding, the iteration gate gates the sweep. Nothing gated the
beginning, so a scope's coverage was whatever it turned out to be by the time the agent stopped — which is
unfalsifiable, and the unfalsifiable is what the prime directive exists to eliminate.

But a finalized set proves only that you know what you intend to test. **It does not prove your oracle can
say `FAIL`.** Two real durability certifications passed with harnesses that could not have detected a loss
— one reading back through a client with a local cache, one addressing the wrong host entirely. Both had
textbook oracles, well-formed as sentences. So the gate is the set **plus two executed rows per scope**,
ids `S<n>-00a` and `S<n>-00b`, run before any other row:

- **`00a` — smoke.** The scope's first-success milestone as its domain file defines it, with no fault and
  no adversarial input, through the real client. Its `ran under` is the listing every later row cites.
  `FAIL` here **stops the scope and briefs nobody**: it goes to the lead as `DEPLOY` / `RELEASE` /
  `INVESTIGATE`, and it is not a finding against the product until the build and the environment have been
  shown to be what the brief says they are.
- **`00b` — calibration.** Inject one known defect and show the oracle reports exactly one. Delete one
  acknowledged key by hand. Plant one wrong price in a fixture page. Send one mail to the wrong mailbox.
  Put one deliberately false claim in a scratch doc. Corrupt one byte of one backup segment. The row
  records what was injected and what the harness said.

> **A scope whose `00b` did not run has no `PASS` rows** — every `PASS` in it is `NOT RUN (uncalibrated)`
> until it does. This is the oracle rule applied to the harness: a harness that has never failed has never
> been shown to work.

That pair is what turns the gate from self-certified paperwork into a criterion, because it produces
evidence an agent cannot write its way around. Re-run `00a` after any environment reschedule — a pod that
moved lost the config that made the listing true.

**One exemption, and only one: the first-run trace precedes the gate.** On first contact the agent takes
it with the quickstart only and records it as a row (oracle: time, steps and exits against the docs' own
claimed duration), *then* reads the domain file and finalizes the set. An agent that has just read a fault
catalogue is no longer discovering anything, so this is the only order in which the trace is cold at all.

**Keep the oracle prose cheap.** Seventeen catalogue entries across three defect classes and two fault
flavours is a hundred oracle sentences before a single run. Declare a **scope-level shared oracle** once
and let rows cite it — `oracle: §10 ledger diff (Missing / Stale / Wrong)` — rather than restating it.

## Where the cases come from

Do not invent them. A register of invented cases is long, green, and worthless — it is the "0 bugs" report
with a bigger table. Every case is **derived**, and the derivation is published with the count so a reader
who disagrees with your enumeration can say so. Eight sources, in order of authority:

0. **The operator's acceptance requirements.** What must be true for this release to ship: SLAs,
   contractual guarantees, regulatory obligations, the release's own exit criteria. Ids `R-<n>`. These come
   *before* the domain file, because a product can be green against its own documentation and red against
   the purchase order — docs promising "survives loss of a single node" are satisfied by a single-node kill
   while a contractual RPO of zero across an availability zone was never a case. Where the operator has
   none, the verdict says green is green against the docs only. These rows are also the
   requirements-traceability matrix an audit asks for, produced as a side effect rather than as a document.
1. **The domain file's fault catalogue.** One case per entry, each under load, each its own run. For a
   stateful product this is the bulk of the register and it is not optional.
2. **The domain file's "defect classes to look for by name".** Each class needs at least one case that
   *would catch it*. A class with no such case is declared unexercised in the register — the honest version
   of what otherwise happens silently.
3. **The scope playbook steps** for each applicable family
(`${CLAUDE_PLUGIN_ROOT}/skills/qa/references/scope-playbooks.md`).
4. **The documentation claims.** Scope 9's claim ledger *is* a case ledger of one kind; adopt its rows by
   reference rather than duplicating them, so the denominator does not double-count.
5. **The product's own enumerated surface**, from reverse coverage: route table, every environment-variable
   read, the option parser, the config schema. Surface found this way and not exercised is a `NOT RUN` row,
   not an absence.
6. **Every prior finding.** Its repro is a permanent case. See *Across iterations*.
7. **The journeys.** Two to four end-to-end paths, each ending at a domain file's *first success* and
   crossing at least two families — prospect → key → email → activated product; sign-up → invite →
   restricted role → export; order → charge → webhook → entitlement → refund → revoked. Each is one case,
   id `J-<n>`, owned by **one** agent or the lead, run as a single actor with **no operator-supplied
   shortcut at any step**. Per-family `PASS` rows do not sum to a journey: the origin engagement's trial
   flow was broken end to end while the form, the issuing API and the activation each passed in isolation.
8. **The story's acceptance criteria, one row per gradeable clause.** `/product-suite:backlog`
   writes them as oracles precisely so they arrive here needing no translation — but a criterion
   with three clauses is three cases, not one. The fixture's own story asked for delivery within
   five minutes, offline activation, and a 14-day expiry, and the single linked case covered one
   of the three; the story was accepted on it. Decompose, and name the case per clause, or the
   gate passes on a case weaker than the criterion.
9. **The client's incident history.** Every production incident and escaped defect from their tracker over
   the last few releases becomes a permanent case. Nothing predicts a product's next failure like its last
   one, and this is field evidence for correctness, not only for the UX use `experience.md` already makes
   of it.

Publish the derivation beside the number, because a bare count is a boast and a derived one is checkable.

**Scope 9 is the one scope whose set cannot be finalized before it starts**, since extracting claims *is*
the work. Its gate is the **surface inventory** — the list of documentation surfaces with page counts from
`docs-conformance.md` Step 1 — plus the reverse-enumeration plan. Its claims are `discovered` by
construction, and that is not a weakness of anyone's catalogue.

## Derived and discovered

Finalizing first must not become a cage. A product teaches you things no derivation predicts, and
exploratory testing finds what case design cannot imagine — that is a feature of testing, not a failure of
planning. **When something smells wrong, follow it before finishing the list.** The list is the floor, not
the ceiling, and a scope that discovered nothing on a first iteration is as suspect as a register with no
`NOT RUN` rows.

So the set is **closed to deletion and open to addition**:

- Cases present before execution are `derived`, and name their source.
- Cases added during execution are `discovered`, and say what prompted them.
- **No case is deleted** once execution has begun. One that turns out to be inapplicable resolves as
  `NOT RUN` with that reason; one you can no longer state a failing input for resolves as
  `NOT RUN — no failing input`. "We decided this did not apply" is information; a deleted row is not. (The
  rule that a case which cannot fail does not go in applies *at design time* — after the gate, resolve, do
  not delete.)
- **Two agents running the same action with the same oracle is one case with two results, not two cases.**
  A disagreement between them is a finding about the harness. Without this rule the denominator inflates
  with every agent added.

Carry the split in the totals, and then **triage each `discovered` row** rather than reading the ratio as a
verdict: a `discovered` case is either a **catalogue gap**, in which case the domain file is wrong and a PR
to this skill is part of the engagement's output, or **product-specific** — this product's own routes,
config and quirks — which no class-level catalogue should have predicted and which stays local. Most are
the second kind, so the raw ratio measures product idiosyncrasy more than test-design quality.

## Cases and findings are different objects

| | Test case | Finding |
|---|---|---|
| Namespace | `S10-07` | `K1` |
| Counts | the denominator | the numerator |
| Lives | forever, as the regression suite | until closed, then stays listed as closed |
| De-duplicated | never | by root cause |

Every `FAIL` row names its finding. The reverse is not required: a finding stumbled on while doing
something else is legitimate and common. But **back-fill it as a case**, or the next iteration has no way
to regress it. One finding may span several cases; one case produces at most one finding.

## Across iterations

The register carries with stable ids, exactly as the finding register does, in the same `qa-state.json`,
and every state change is appended to the event log that
`${CLAUDE_PLUGIN_ROOT}/shared/contracts/qa-dev.md` defines — which is
what makes the lifecycle reconstructable and the dashboards possible.

- **Phase 0** — build identity, and the per-component smoke row. Preconditions, not cases.
- **Phase 1** — fix verification is **the failed cases re-run verbatim**. The adversarial variant each one
  requires becomes a *new, permanent* case — that is how the coverage that was missing stops being missing.
- **Phase 2** — regression is **the `PASS` cases whose `touches` intersects the diff's blast radius**. That
  is a selection rather than a guess, and it is most of the gate's cost advantage. Without the `touches`
  field it would be a guess wearing the word "computed".
- **Phase 3** — new cases, appended. Never renumbered.

A `PASS` case is not retired because it passed. `NOT RUN` rows carry forward until they are run or the
reason they cannot be is fixed; a `NOT RUN` row whose blocker has not changed in three iterations is itself
a finding about the test environment, usually `PROCURE`, and gets promoted into the findings rather than
riding along.

### The case review, every iteration

The set is revisited at the start of **every** iteration, by the lead, before Phase 0 — there is always
more to add, and the previous round generates it. Zero agents, minutes of work, not optional:

1. **Triage last round's `discovered` cases** into catalogue gaps and product-specific ones; promote both
   to permanent `derived`, and raise a PR against the domain file for the first kind.
2. **Add every new finding's repro**, plus every adversarial variant Phase 1 required, as separate
   permanent cases.
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

## What an honest register looks like

- **`NOT RUN` and `BLOCKED` are first-class results**, and in a real run they are not zero. A register with
  no `NOT RUN` rows over a product of any size was filled in from memory.
- **One case, one variable.** The environment-variable blocker was proved by three runs of the same image
  differing only in the variable's name — three rows, not one.
- **Do not merge cases to improve the count.** De-duplication by root cause applies to *findings*.
- **Long runs are `LONG`, not `PASS`**, and a `LONG` row is a lien on the report: it can be delivered open,
  but the report carries no verdict while one is.
- **Granularity:** one case per thing that can independently break. Not one per assertion (padding), not
  one per feature (hides which input was tried).
- **No secrets in the register.** It is the most-forwarded file in the set. Credentials by role only.

## Deliverable

One register per run in the report directory, template in
`${CLAUDE_PLUGIN_ROOT}/skills/qa/assets/test-case-register.md`. Per-scope agents
return their own rows; the lead concatenates them and resolves the overlap with scope 9's claim ledger.

**The lead re-runs a sample of every agent's `PASS` rows** — three per agent, highest severity ceiling
first, run by the lead or by a different agent. The register is otherwise each agent's report of itself,
which by this file's own central rule is not an oracle, and agents do produce evidence-shaped text. A
disagreement is a finding about the harness and downgrades that scope to uncalibrated.

The evidence directory ships with a **manifest** — path, size, sha256 per artifact — generated after the
last row and referenced by hash in the index, so the bundle cannot be edited after the verdict.

The ranked index carries the totals, the derivation, the `NOT RUN` list ordered by guarded severity, and
the verdict computed from all of it.
