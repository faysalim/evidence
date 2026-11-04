# Domain: file storage and sync

Files uploaded, synced across devices, shared by link, versioned, counted against a quota, and deleted —
where "deleted" and "synced" are both claims that need proving.

## Do the thing

> The upload completes and the file appears in the list with a green tick. Edit the same file on two
> devices while both are offline, reconnect both, and account for **both** versions. Then delete a file
> and fetch its direct URL. **A green sync tick is this domain's HTTP 200.**

## Scope map

| Family | In this domain | Agent | Notes |
|---|---|---|---|
| 1 Acquisition | pricing, storage claims, signup | own | storage and retention claims are measurable |
| 2 Primary product | the clients | own ×2 | split: sync engine vs web browse / share |
| 3 Control plane | admin, sharing policy, audit, **quota** | own | |
| 4 Deployment | SaaS | N/A | `own` if self-hostable |
| 5 Entitlement | plan storage limits | →3 | |
| 6 Secondary | mobile client, public API, third-party integrations | own | |
| 7 Telemetry | what file metadata is collected | →8 | |
| 8 Security | link permissions, at-rest encryption, **deleted-but-reachable** | own | |
| 9 Documentation | sync behaviour, conflict policy, retention and deletion claims | own | the conflict policy is a behavioural guarantee |
| 10 State under fault | the core | own ×2 | split: offline & conflict vs durability & deletion |
| 11 Upgrade | client upgrade with a local cache, server-side format migration | own | |
| 12 Experience | what "synced" and "deleted" appear to mean | lead | |

**Usual set: 1,2×2,3,6,8,9,10×2,11 own + 4 N/A, 5→3, 7→8, 12→lead = 10 agents.**

## Failure catalogue

The same file edited offline on two devices · a rename on one device and an edit on the other · a
case-only rename on a case-insensitive filesystem · unicode normalization differences between clients
(NFC vs NFD) · a path longer than the OS limit · reserved characters in a filename · a file deleted on one
device while open on another · quota exceeded mid-upload · an upload interrupted at 90% · a very large
single file · a hundred thousand small files · a shared link used after the sharer loses access to the
file · a folder shared and then moved · trash emptied · clock skew on modification times · a symbolic
link · a file locked by another application.

## Defect classes to look for by name

**Silent conflict resolution that discards one side** with no conflict copy · unicode normalization
producing two files that look identical, or losing one of them · **deleted content still reachable by its
direct or CDN URL** · a share link that outlives the sharer's own access, or grants more than the dialog
said · a quota that counts versions and trash without telling the user, so they cannot free space · a
modification time or version that goes backwards, producing a sync loop · **a partial upload exposed as a
complete file** · case-insensitivity collisions on cross-platform sync · a trash that is a hard delete,
or a delete that is recoverable when the UI said it was gone.

## Evidence and severity

The oracle is **your own content hashes, per path, per device.** Reconcile into four buckets — Missing,
Stale, Wrong, Duplicated — because a file that is *present with the wrong content* is the defect that
counting files cannot find, and it is the one that matters most.

`evidence-standard.md` → *Stateful systems under fault* for the offline and concurrency schedule,
*Migrations, upgrades and restores* for the local-cache upgrade. Record per run: client version per
device, filesystem and its case sensitivity, OS, the exact offline window, and the order of reconnection —
which determines the result.

| Observation | Severity |
|---|---|
| A user's edit silently discarded | **critical** |
| Deleted content still reachable by URL | **critical** |
| A share link granting more than it stated | **critical** |
| A partial upload served as complete | **critical** |
| A quota the user cannot free | **blocker** |
| A sync loop | **major** — bandwidth and battery — **critical** if it corrupts |

## Experience

**Who the user is:** someone who does not know what "synced" means technically and is relying on it
completely, plus the administrator setting a sharing policy for people they cannot see.

**Where it lives:** what the sync indicator actually claims; how a conflict is presented; what "delete"
means and where the file went; whether the share dialog's wording matches what it grants; and progress on
a long upload.

**First success is:** a file created on device A opens with identical content on device B — and the user
can *tell* that it did.

**Do the thing, for experience:**

> Create a conflict deliberately. See whether the user can tell what happened, find both versions, and
> choose between them.

**Defect classes:** a green tick that means "uploaded" when the user reads it as "safe" · conflict copies
named so the user cannot tell which one is theirs · a share dialog whose wording does not match the
permission it grants · no progress or estimate on a long upload · a delete with no statement of where the
file went or for how long.

**Evidence note:** the "actively misled" clause is this domain's spine. A sync indicator that claims a
state the system is not in is a product bug, not a wording preference, and it inherits the severity of what
the user does next — which is usually to delete their local copy.

## Domain gotchas

- Test across **different filesystems** (case sensitivity, unicode normalization, path limits) or none of
  the interesting defects will appear. One OS is one data point.
- The order of reconnection decides the outcome in almost every conflict test. Fix it, record it, and run
  both orders.
- CDN caching means a deleted file can remain reachable for the cache lifetime. That latency is part of
  the finding — record when you checked, and check again after the TTL.
- Your test files consume a shared quota and may be scanned by data-loss-prevention tooling. Ledger them.
- Deleting test content may be irreversible. Only empty a trash you filled.
- Large-file and many-file runs take real time and bandwidth: background jobs, not an agent waiting
  (`iteration-cycles.md`, two-speed verification).
