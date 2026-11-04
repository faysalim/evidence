# Test-case register template

The run's denominator, and what the verdict is computed from. One row per thing that can independently
break. **Each scope's case set is finalized before that scope executes anything**, and its smoke and
calibration rows run before any other. `${CLAUDE_PLUGIN_ROOT}/skills/qa/references/test-cases.md` is the
method; this is the shape.

Three rules decide whether this file is worth anything:

- **A case whose oracle is the product's own report of itself is not a case** — and the oracle must predate
  the run and exist outside both the product and your own judgement.
- **A `PASS` with no evidence is a `NOT RUN`.**
- **A scope whose calibration row did not run has no `PASS` rows.**

---

# `<business>` — QA — test-case register

**Iteration:** `<N>` · **Run date:** `<date>` · **Builds under test:** `<component: digest>` …
Evidence manifest: `<path>` · sha256 `<hash over the evidence directory>`
No secrets in this file; credentials by role only. It is the most-forwarded file in the set.

## Totals, with the derivation

| | n |
|---|---|
| Cases | `<total>` |
| `PASS` | `<n>` |
| `PASS (SHORT)` | `<n>` — below the domain's short form; satisfies nothing in the verdict |
| `FAIL` | `<n>` → findings `<ids>` |
| `BLOCKED` · `NOT RUN` | `<n>` · `<n>` — listed below, ordered by guarded severity |
| `LONG` | `<n>` running; read back at `<when>` — **the report carries no verdict while any is open** |
| `derived` / `discovered` | `<n>` finalized before execution · `<n>` found during it |
| Scopes calibrated | `<n>` of `<n>` — **uncalibrated scopes contribute no `PASS`** |

**Derived from:** `<n>` operator acceptance requirements (source 0) · `<n>` fault-catalogue entries across
`<domain files>` · `<n>` named defect classes · `<n>` playbook steps over `<n>` applicable families ·
`<n>` documentation claims (adopted from scope 9's ledger, not duplicated) · `<n>` from reverse coverage of
`<route table / env reads / option parser>` · `<n>` journeys · `<n>` from the client's incident history ·
`<n>` regression cases carried from iteration `<N-1>`.

**Growth this iteration:** `<prev>` → `<total>` (`+<n>` derived from the diff, `+<n>` promoted from
`discovered`, `+<n>` adversarial variants made permanent). The set only grows; nothing is pruned.

**`discovered` triage:** `<n>` catalogue gaps → PRs raised against `<domain file>` · `<n>`
product-specific, stay local. *(Triage each one. The raw ratio measures product idiosyncrasy more than
test-design quality.)*

**Defect classes declared unexercised:** `<name>` (`<ceiling>`) — `<why no case could reach it this run>`.
Naming these is the honest version of what otherwise happens silently.

**Lead re-verification:** `<n>` `PASS` rows re-run by the lead (`<ids>`); `<n>` disagreements →
`<harness findings>`.

## Gate rows — these run first, in every scope

| id | The thing done | Oracle | Result | Evidence |
|---|---|---|---|---|
| `S10-00a` | Form 3 nodes, write 1,000 keys, read every one back through the real client | The harness **lists** 3 instances and 1,000 keys are readable | `PASS` | `3 instances listed` (not configured); `evidence/S10-00a/` |
| `S10-00b` | Delete 7 acknowledged keys directly from one node's store, then run the read-back diff | The diff reports **exactly 7** Missing | `PASS` | `Missing=7 Stale=0 Wrong=0`; `evidence/S10-00b/` |

*`00a` failing stops the scope and briefs nobody — it goes to the lead as `DEPLOY` / `RELEASE` /
`INVESTIGATE`. `00b` failing means every later `PASS` in this scope is `NOT RUN (uncalibrated)`. Re-run
`00a` after any environment reschedule.*

## Cases

One table per scope family, journey or requirement. Ids stable forever; append, never renumber. Rows in
descending severity ceiling.

### Scope 10 — State: correctness and durability under fault, time and concurrency

**Shared oracle (§10):** the read-back diff over my own acknowledged-write ledger, reporting **Missing /
Stale / Wrong** — presence, value and version. *Counting presence alone misses two of the three failures.*

| id | The thing done | Oracle | Guards (ceiling) | Ran under | Result | Evidence |
|---|---|---|---|---|---|---|
| `S10-01` | 20k writes at RF2, `kill -9` the leader mid-stream, read back every key from a surviving node | §10 diff | acknowledged-write loss (`critical`) | 3 nodes listed, RF2, 64 parts; N=20k, 20m, 2k ops/s; `<agent>`, `<ts>` | `FAIL` | `K4`; Missing=39,760 Stale=0 Wrong=0; `evidence/S10-01/` |
| `S10-02` | Same, leader restarted cleanly rather than killed | §10 diff | acknowledged-write loss (`critical`) | as `S10-01` | `PASS` | Missing=0 Stale=0 Wrong=0; `evidence/S10-02/` |
| `S10-03` | 12h soak, churn every 90s; cutoff 12h, stall-exit on 10m of frozen progress | §10 diff at the end | loss under sustained churn (`critical`) | 3 nodes listed, RF2; 12h | `LONG` | started `<ts>`, reads back `<ts>` |
| `S10-04` | Partition one node for 60s under write load, heal, read back from **both** sides | §10 diff on each side | divergence after heal (`critical`) | — | `NOT RUN` | no third host on this machine — see the `NOT RUN` list |

### Scope 5 — Entitlement lifecycle

| id | The thing done | Oracle | Guards (ceiling) | Ran under | Result | Evidence |
|---|---|---|---|---|---|---|
| `S5-01` | `POST /v1/trial` with the payload the docs show, **verbatim** | A usable key arrives in the real mailbox and activates a real binary | documented path broken (`blocker`) | prod `<digest>`; `<agent>`, `<ts>` | `FAIL` | `K1`; 403 from the issuing endpoint; raw response in the finding |
| `S5-02` | Same image, `KEYRIGHT_LICENSE` set — **the documented variable name** | A licence is issued | documented path broken (`blocker`) | self-hosted `<digest>` | `FAIL` | `K1`; no licence issued |
| `S5-03` | Same image, `KEYRIGHT_SELF_LICENSE` set — the name the code reads | A licence is issued | — | self-hosted `<digest>` | `PASS` | issued; this row is what proves `K1` is a naming defect |
| `S5-04` | Same image, neither variable set | A clear error naming the variable it wants | silent misconfiguration (`major`) | self-hosted `<digest>` | `FAIL` | `K7`; `/health` returned `200 {"status":"ok"}` throughout |

*Four rows, one variable each. Collapsing them into "tried the env vars — `PASS`" is how the blocker was
missed for a month: `/health` was green the whole time.*

### Journeys

| id | The path, as one actor, no shortcut | Oracle | Guards (ceiling) | Result | Evidence |
|---|---|---|---|---|---|
| `J-1` | Prospect lands on the site → submits the form → receives the email → activates the product with the key from that email | A working product, reached only through artifacts the product itself produced | business cannot sell (`blocker`) | `FAIL` | `K1`, `K9`; the form POSTs to the 403 endpoint; the email is unbranded plain text |

*Every surface on `J-1` passed in isolation. The journey is what nobody owned.*

### Scope 9 — Documentation conformance

Adopted from the claim ledger in `${CLAUDE_PLUGIN_ROOT}/shared/references/docs-conformance.md` by
reference — `D1`–`D<n>`,
`<n>` `PASS`, `<n>` `FAIL`, `<n>` `BLOCKED`. **Not re-listed here**, so the denominator does not
double-count. Scope 9's gate is the surface inventory, not a finalized claim list.

### `R` — Operator acceptance requirements

| id | The requirement, as a sentence that can fail | Oracle | Result | Evidence |
|---|---|---|---|---|
| `R-1` | "No acknowledged write is lost across the loss of one availability zone" (contract §4.2) | §10 diff after partitioning 3 of 9 nodes | `NOT RUN` | single-region test bed; see the `NOT RUN` list |

*Source 0 outranks the docs. A product can be green against its own documentation and red against the
purchase order.*

## `NOT RUN` and `BLOCKED` — ordered by the severity of what they guard

This list is a deliverable, not an apology, and **a row guarding a `critical` class is reported above the
first finding, not below the last.**

| id | Guards (ceiling) | What it would have exercised | Why not | What would unblock it |
|---|---|---|---|---|
| `R-1` | AZ-loss durability (`critical`) | The contractual RPO | Single-region test bed | Three nodes across two zones |
| `S10-04` | Divergence after heal (`critical`) | Partition healing with a witness | Two hosts on this machine | A third host, or a cloud trio |
| `S2-11` | Installer trust (`major`) | macOS installer and Gatekeeper | No macOS host in this engagement | Any current macOS host |

A `NOT RUN` row whose blocker has not changed in three iterations is itself a finding about the test
environment, usually `PROCURE`. Promote it rather than letting it ride.

## Carried forward

| id | Result last iteration | Result now | Note |
|---|---|---|---|
| `S5-01` | `FAIL` → `K1` | `PASS` | Phase 1 verification, repro run verbatim |
| `S5-05` | — | `FAIL` → `K1-v` | New permanent case: the adversarial variant the original fix did not cover |

Cases are never retired for passing — they are the regression suite, and the adversarial variant of every
verified fix enters the register permanently.
