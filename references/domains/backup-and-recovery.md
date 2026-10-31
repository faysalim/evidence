# Domain: backup and disaster recovery

Scheduled backups, incremental chains, retention, immutability claims and restores. The one domain whose
entire purpose is a path almost nobody exercises until the day it is the only thing that matters.

## Do the thing

> Every job reports `success` and the retention report is green. Now **restore** — to a clean machine, from
> the oldest retained copy, and then from the middle of an incremental chain — and open the restored data
> with the application that created it. **`Backup completed successfully` is this domain's HTTP 200. The
> restore is the entire product.**

## Scope map

| Family | In this domain | Agent | Notes |
|---|---|---|---|
| 1 Acquisition | RPO, RTO and immutability claims | →9 | |
| 2 Primary product | backup and **restore** | own ×2 | split: backup and chain integrity vs the restore paths |
| 3 Control plane | schedules, retention policy, catalog, reporting | own | |
| 4 Deployment | agents across target types, repository storage | own | |
| 5 Entitlement | per-agent or per-terabyte licensing | →4 | |
| 6 Secondary | application-aware plugins (database, mail, VM) | own | each plugin is its own bug population |
| 7 Telemetry | job reporting | →3 | and see the gotcha: the report is self-report |
| 8 Security | **repository immutability**, encryption at rest, key custody, who can delete a copy | own | |
| 9 Documentation | RPO/RTO, what is **not** captured, the restore runbook | own | |
| 10 State under fault | interrupted backup, interrupted restore, corrupted chain, full repository | own | |
| 11 Upgrade | product upgrade with existing chains; **restoring a backup taken by an older version** | own | |
| 12 Experience | the restore under pressure | own | |

**Usual set: 2×2,3,4,6,8,9,10,11,12 own + 1→9, 5→4, 7→3 = 10 agents.**

## Failure catalogue

Kill the backup at 50% · **kill the restore at 50%** · corrupt one block in the middle of a chain · delete
one incremental from the middle · fill the repository · restore the oldest retained copy · restore to a
different machine, a different OS version, different hardware · restore a single file, and a whole system ·
restore while a new backup is running · restore an application-consistent backup of a database and then run
that database's own integrity check · rotate the encryption key and restore · restore a backup taken by the
previous product version · a retention run that should delete versus a legal hold that should prevent it ·
a clock change on the agent · an agent offline for a week, then reconnecting · and, with written
authorisation, an attacker holding admin credentials attempting to delete the repository.

## Defect classes to look for by name

**A backup that cannot be restored** — the chain verifies and the restore fails. It is the only truly
critical class here and it is the reason verification-by-metadata is not evidence · **crash-consistent
presented as application-consistent**, so a database restores corrupt · a retention run deleting a copy a
legal hold protected, or **keeping copies that a privacy obligation required purging** — both directions are
critical · an incremental chain broken by one missing link, undetected until a restore · **a restore that
succeeds and silently omits things**: sparse files, hard links, ACLs, extended attributes, alternate data
streams · **permissions and ownership not restored**, so the data is present and unusable · immutability
that can be configured away by the same credential an attacker would steal · encryption keys stored
alongside the backups they protect · a restore nobody can perform from the documented runbook · **an RTO
far longer than claimed**, measured for the first time during the incident.

## Evidence and severity

**The only evidence in this domain is a restore that the originating application accepts.** A green job, a
"verified" backup, a checksum of the archive and a successful catalog read all belong in
`evidence-standard.md`'s list of evidence that looks strong and is not: they prove the bytes are readable,
not that the data is usable.

The oracle is a **pre-backup fingerprint of the source** — file count, per-file hashes, permissions, and
the application's own integrity check — reconciled after restore into Missing / Stale / Wrong /
Permissions-wrong. Measure **RTO with a stopwatch**, from decision to usable data, and report it against
the documented claim.

`evidence-standard.md` → *Migrations, upgrades and restores* in full, *Stateful systems under fault* for the
interruption schedule, *Background and scheduled work* for schedules and retention runs.

| Observation | Severity |
|---|---|
| A backup that cannot be restored | **critical** — the product did not work; nothing else matters |
| Silent omission from a restore | **critical** |
| Crash-consistent sold as application-consistent | **critical** |
| Retention deleting held data, or failing to purge | **critical** — legally wrong in both directions |
| Immutability bypassable with stolen admin credentials | **critical** — it is the only control that matters against ransomware |
| Permissions or ownership not restored | **blocker** |
| RTO materially longer than claimed | **blocker** — it is a documented guarantee |

## Experience

**Who the user is:** someone restoring at 4am under pressure, who did not configure the system and may not
be the person who left.

**Where it lives:** whether the runbook is executable by that person; whether the product says **what it is
about to overwrite**; progress and an estimate on a long restore; and how one file is found in a catalog of
millions.

**First success is:** a restore completed by someone following the written runbook, with no access to the
person who set it up.

**Do the thing, for experience:**

> Hand the runbook to someone who has never restored this system, and time them. Count every question they
> have to ask.

**Defect classes:** a restore wizard that does not state what it will overwrite — the dangerous-affordance
class, and here the consequence is destroying the surviving copy · a runbook assuming credentials or tools
the restorer has not got · no progress or estimate, so a slow restore is indistinguishable from a hung one ·
a catalog that cannot find a file by name · a job report that says `success` with warnings nobody surfaces.

**Evidence note:** that question count is this domain's first-run measurement, and it is unusually
load-bearing: **the person restoring is cold by definition**, because the warm person is the one who is
unavailable. This is the one domain where the perishability argument in `experience.md` is not a
methodological nicety but the realistic scenario.

## Domain gotchas

- **Restore into an environment you created, never over live data.** This is the clearest case in the skill
  of an operation that is destructive by nature and is nonetheless the core test.
- Restores consume real storage and real hours: background jobs on the two-speed ladder, never an agent
  waiting.
- An immutability or ransomware test uses credentials deliberately. Get written authorisation, ledger it,
  and never attempt it against a repository you do not own.
- The product's own verification feature is the component under test reporting on itself. Run it, and never
  cite it as evidence.
- A restore from yesterday and a restore from the oldest retained copy are different tests, and only the
  second one tests retention.
- **Ask when the last real restore happened.** If the answer is "never", that is finding number one, and it
  is not a defect in the code.
