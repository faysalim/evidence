# Domain: ETL / data pipeline

Sources and sinks, transforms, schema drift, idempotency and delivery guarantees, backfills, late and
out-of-order data, partial failure and resumption, data-quality assertions, lineage, scheduling.

## Do the thing

> Every run is green in the scheduler. Count the rows at the source and the rows at the sink, and checksum
> a column. The DAG has been green for three weeks; the source added a column in week one and the sink has
> been receiving NULLs ever since. **"Run succeeded" is this domain's HTTP 200.**

## Scope map

| Family | In this domain | Agent | Notes |
|---|---|---|---|
| 1 Acquisition | docs / download site | N/A | |
| 2 Primary product | orchestration CLI, authoring UI | own | |
| 3 Control plane | scheduler, run history, connection management | own | |
| 4 Deployment | container, k8s, managed runtime | own | |
| 5 Entitlement | if licensed | →4 | |
| 6 Secondary | connectors per source and sink | own | each connector is its own bug population |
| 7 Telemetry | generic | →8 | |
| 8 Security | credential storage, connection secrets, PII in logs | own | pipeline logs are where PII leaks |
| 9 Documentation | **every connector config option is a claim** | own | |
| 10 State under fault | the core | own ×2 | split: transform/drift vs resume/delivery |
| 11 Upgrade | pipeline version change with in-flight state; checkpoint format | own | |
| 12 Experience | operator experience under partial failure | lead | |

**Usual set: 2,3,4,6,8,9,10×2,11 own + 5→4, 7→8, 12→lead = 10 agents.**

## Failure catalogue

Kill mid-run at a recorded offset · sink unavailable for one batch of a thousand · source schema change
(add, rename, retype, widen, narrow, nullability) · a record whose event time falls in an already-closed
window · duplicate source records · a backfill overlapping a scheduled run · two runs of the same window
concurrently · credential expiry mid-run · a run exceeding its interval so the next one overlaps · DST
transition on the schedule · source available but returning an empty set.

## Defect classes to look for by name

Silent row loss · silent row duplication (the at-least-once claim met, the idempotency claim not) ·
**silent column drop or coercion on drift** · checkpoint advancing past records that never landed ·
backfill double-counting aggregates · a data-quality assertion that never fires · late data silently
discarded · dead-letter queue nobody reads and nothing reports · "succeeded" with zero rows · lineage that
does not match what actually ran.

## Evidence and severity

`evidence-standard.md` → *Data pipeline runs* in full. Record per run: pipeline version, source snapshot
id, config hash, time window, and checkpoint state before and after.

The **fixture method** from the decompiler section generalises directly: build a small input containing
exactly the construct in question — the null, the unicode, the out-of-range date, the renamed column — and
diff input against output. That turns "the transform looks right" into a measurement.

| Observation | Severity |
|---|---|
| Silent row loss or duplication | **critical** |
| Silent column drop or coercion on drift | **critical** |
| Checkpoint advancing past unlanded records | **critical** |
| A quality assertion that never fires | **blocker** — the control the customer relies on does not exist |
| Loud failure with a correct checkpoint | **major** |
| Late data discarded without notice | **major** |

The delivery guarantee is a documentation claim: test the **exact wording**. "At-least-once" and
"exactly-once" are different pass criteria, and if the docs state neither, the missing contract is the
first finding — **and the data finding is still filed at its consequence severity**, held at `DECIDE` with
the assumption named, open at that severity for the verdict.

## Experience

**Who the user is:** the data engineer on call, and the analyst downstream who trusts the numbers.

**Where it lives:** run status under partial failure; the logs' ability to name *which records* did not
land; schema-drift notification; backfill controls (dry-run, range preview, what will be overwritten);
and whether configuration errors surface at authoring time or at hour three of a run.

**First success is:** one batch landed in the sink with source and sink counts reconciled — not "the run
completed".

**Do the thing, for experience:**

> Break one of a thousand batches. From the product's output alone, name which records did not land, and
> the exact command that resumes without double-writing.

**Defect classes:** **"succeeded" with hidden caveats** (rows rejected or dead-lettered, counted nowhere
the operator looks — the experience half of the self-report finding) · config errors that could have been
caught at validation and surface at runtime instead · backfill with no dry-run or preview of the overwrite
range · drift handled "gracefully" with no notice, which is the worst outcome because it looks correct.

**Evidence note:** time-to-diagnose again, plus a second number worth recording — **time from failure to
the operator's first chance to know** (alert latency versus the next scheduled run). A pipeline that fails
at 02:00 and tells someone at 09:00 has a seven-hour experience defect.

## Domain gotchas

- Reconcile **per partition**, not in total. Equal totals hide an offsetting loss and duplication.
- A rerun-equivalence test needs a *frozen* source snapshot, or you are measuring the source's churn.
- "Idempotent" usually means idempotent per key, not per run. Read which, then test that one.
- Dead-letter queues are where evidence of failure goes to be forgotten: always count them and state
  whether anyone would ever know.
- Test data in a shared warehouse is production data to somebody. Use your own schema and ledger it.
