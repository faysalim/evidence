# Domain: relational database / transactional store

Schema migrations, transactions and isolation levels, constraints, a query planner, backup and
point-in-time restore, and an upgrade path customers actually follow.

## Do the thing

> The backup job has logged "completed successfully" every night for a year and the restore has never been
> run. Restore it — to a point in time — and count the rows. Then: `COMMIT` returned, `kill -9` the
> server, and the row is gone. **"Completed successfully" is this domain's HTTP 200.**

## Scope map

| Family | In this domain | Agent | Notes |
|---|---|---|---|
| 1 Acquisition | docs / download site | N/A | |
| 2 Primary product | CLI / shell / client per OS | own | |
| 3 Control plane | management console, if any | N/A | often none |
| 4 Deployment | package, container, cluster | own | |
| 5 Entitlement | if licensed | →4 | |
| 6 Secondary | drivers and ORMs | own | the driver's behaviour on a mid-transaction disconnect is the seam |
| 7 Telemetry | generic | →8 | |
| 8 Security | authz per object, injection surfaces, TLS, at-rest | own | |
| 9 Documentation | **every documented function, statement, config knob and isolation guarantee** | own | the strongest scope here |
| 10 State under fault | isolation, constraints, crash recovery, planner correctness | own ×2 | split: isolation/constraints vs crash/recovery |
| 11 Upgrade | schema migration, in-place binary upgrade, dump/restore across versions | own | |
| 12 Experience | error-message precision, failed-migration legibility | lead | |

**Usual set: 2,4,6,8,9,10×2,11 own + 5→4, 7→8, 12→lead = 9 agents.**

## Fault catalogue

`kill -9` immediately after `COMMIT` returned · power-loss simulation mid-checkpoint · full disk during a
write · fsync lying (test the claim, not the setting) · connection dropped mid-transaction · two sessions
racing a unique insert · a foreign key with a concurrent delete · long-running read against a concurrent
schema change · migration failing partway on a populated table · replica promoted while behind · clock
change during a time-stamped transaction.

**Isolation anomalies get their own scripted runs**, one per anomaly the documented level claims to
prevent: dirty read, non-repeatable read, phantom, lost update, write skew. Two sessions with a recorded
interleaving, and the anomaly shown in the second session's output.

## Defect classes to look for by name

Durability loss after acknowledged `COMMIT` · an isolation level that does not prevent the anomalies its
documentation claims · **silent coercion or truncation on insert** (the database said OK and changed your
data) · constraint bypass under concurrency · planner returning different rows with and without an index ·
collation, encoding and timezone edge behaviour · a migration that fails with the resulting state
undefined · restore that completes and reconciles to the wrong point in time.

## Evidence and severity

`evidence-standard.md` → *Migrations, upgrades and restores*, *Stateful systems under fault*. Record crash
recovery as "ack at T, kill at T+ε, row present/absent on restart". Record isolation anomalies as the two
sessions' statements in interleaved order with the observed output.

| Observation | Severity |
|---|---|
| Silent corruption or coercion (undetected, and it propagates into backups) | **critical** — ranks above loss, because loss is at least discoverable |
| Durability loss after `COMMIT` returned | **critical** |
| An isolation level missing its documented anomaly set, silently | **critical** |
| Constraint bypass under concurrency | **critical** |
| Planner returning different rows with and without an index | **critical** |
| Restore reconciling to the wrong point | **critical** |
| Migration that fails loudly and rolls back cleanly | **major** |

## Experience

**Who the user is:** the DBA and the application developer.

**Where it lives:** error-message precision on constraint, migration and syntax failures; what a failed
migration tells you about the state you are now in; the defaults a newcomer inherits; `EXPLAIN` legibility.

**First success is:** server running, a table created, a row written, and that row read back in a new
session.

**Do the thing, for experience:**

> Run a migration that fails on row 4,000,001 of a populated table and read the error as the person on
> call: does it name the row, the constraint and the column — and does it tell you whether the database is
> now half-migrated, and how to get back?

**Defect classes:** constraint errors naming an internal identifier instead of the column and offending
value · a failed migration with undefined resulting state and no rollback instruction · performance-first
defaults that trade durability (`fsync` off) without saying so at install · `EXPLAIN` output that cannot
be read without reading the source.

**Evidence note:** internal inconsistency is the workhorse — one error path names the column and its
sibling does not. The measurement is time-to-diagnose from the error text alone.

## Domain gotchas

- **Test the durability claim, not the setting.** `fsync=on` is a configuration; surviving `kill -9` is a
  measurement.
- A planner test needs the *same* query and the *same* data, with only the index differing — otherwise you
  are measuring two things.
- Isolation tests need a deterministic interleaving (locks or sleeps), or a pass is luck.
- Restore onto a *clean* host. Restoring over the original hides the half of the bugs that live in what
  the backup did not contain.
