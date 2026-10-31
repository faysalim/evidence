# Domain: distributed database / clustered store

Replicated, partitioned key-value or document store with failover, rebalance and migration, cluster
membership, change feeds, and one or more client SDKs or wire-compatibility layers.

## Do the thing

> Every write was acknowledged and the cluster reports every node healthy. Now read every one of them
> back — after the owner node was killed mid-stream, after the partition map changed, from the replica
> that just took over. A cluster can be available, green, and have lost tens of thousands of acknowledged
> keys. **"Available" is this domain's HTTP 200.**

## Scope map

| Family | In this domain | Agent | Notes |
|---|---|---|---|
| 1 Acquisition | docs / download site, if any | N/A | usually nothing to buy |
| 2 Primary product | admin shell / CLI / console, per OS | own | exit codes; machine-name vs loopback addressing |
| 3 Control plane | management API, console, workspace / store / token / roles | own | console "healthy" is cross-checked by scope 10, never trusted |
| 4 Deployment | Docker, Helm/k8s, bare metal | own | scale-out and scale-in *with data*; pod reschedule; advertised addresses for out-of-cluster clients; RF vs pod-count placement |
| 5 Entitlement | if licensed: fail-closed on expiry **under load**; dependency-expiry time bombs | →4 | |
| 6 Secondary | client SDKs, wire-compat layer, CDC consumers | own | retries counted *during* faults; is a retried write applied once? |
| 7 Telemetry | generic | →8 | |
| 8 Security | data-plane authz on **every node**, not only the manager; unauthenticated destructive commands on the compat layer; TLS on management, cluster and client planes; token scope | own | |
| 9 Documentation | consistency and durability wording as claims; every env var; every cmdlet and flag; Helm values; port tables | own | |
| 10 State under fault | **the core of the product** | own ×2 | takes the spare agents, split by fault class: kill/partition vs membership/migration |
| 11 Upgrade | rolling upgrade, mixed version, wire-version negotiation, on-disk format | own | does the server reject old clients — intended, and documented? |
| 12 Experience | operator diagnosability | lead | consolidation and the diagnosability clock are reading work |

**Usual set: 2,3,4,6,8,9,10×2,11 own + 5→4, 7→8, 12→lead = 10 agents.** Fits the cap with one spare.

## Fault catalogue — each under load, each its own run

Owner or primary kill · graceful stop · pause (SIGSTOP) · slow disk · full disk · symmetric partition ·
**asymmetric partition** (A→B passes, B→A dropped) · half-open TCP (peer gone, socket not closed) · node
join · leave · rejoin with stale state · two nodes restarting together · leader or manager restart ·
rebalance during writes · migration cutover while a replica is behind · clock skew between nodes · client
reconnect mid-batch · client retry of a write whose first attempt was already applied.

A kill does not stand in for a partition. They have different bug populations, and the asymmetric
partition is the one most products have never been tested against.

## Defect classes to look for by name

Acknowledged-write loss · split-brain (two acceptors during a partition) · replica staleness after
cutover · ownership-convergence latency (the available-but-failing window) · available-but-missing during
migration · version regression (an older value wins after reconcile) · lease or TTL not honoured
cluster-wide after owner change · change-feed gaps or duplicates across failover · watermark or offset
stall · **self-report lies** (healthy / in-sync / lag=0 while reconciliation fails).

## Evidence and severity

`evidence-standard.md` → *Stateful systems under fault*, *Migrations, upgrades and restores*. Additionally,
domain-specific: ownership/epoch convergence time per key after a fault, reported as a **distribution, not
a mean**; the client-observed error window counted per key; lease expiry honoured on every node after an
owner change.

| Observation | Severity |
|---|---|
| Missing or Wrong > 0 on acknowledged writes under a documented-survivable fault | **critical** |
| Two acceptors during a partition | **critical** |
| Available but stale beyond the documented contract | **blocker** |
| Convergence latency beyond the docs or a client's retry budget, with no loss | **major**, and the first line must say "availability, not loss" |
| The contract is undocumented | file the missing contract as a scope-9 finding *first*; hold the data finding at `DECIDE` |

You cannot grade a product against a promise it never made — which is why the undocumented contract is
the first finding, not a footnote.

## Experience

**Who the user is:** two, never one. The **operator** (bring-up, scale, upgrade, incident) and the
**integrating developer** (first write-and-read-back, and the exceptions the SDK throws during a failover).

**Where it lives:** the quickstart-to-formed-cluster path, the CLI and console, and above all in what the
product *emits during a fault*. There are no screens worth testing; there are states worth being able to
see.

**First success is:** three nodes formed, one write acknowledged, and that write read back from a
*different* node than the one that accepted it.

**Do the thing, for experience:**

> The cluster formed and the console is green. Kill a node, then ask the question the pager will ask at
> 3 a.m.: could an operator who did *not* kill it tell what happened, and what to do, from the product's
> own output alone? **Time to diagnose an injected condition is this domain's time to first success.**

**Defect classes:** *silent-config no-op* (a mistyped variable or unsupported value accepted without
error, producing "0 instances" or a default nobody chose — also a scope-9 finding, filed once under a
shared id) · *undiagnosable degradation* (replica behind, rebalance stalled, serving stale — the condition
exists, a metric may even exist, but nothing names or thresholds it) · *internal vocabulary in
client-facing errors* (an SDK throwing `OwnershipEpochMismatch` at a developer who has no action
available, and never saying the one thing they need: **is this safe to retry?**) · *dangerous defaults*
(RF=1, auth off, bind-to-loopback, no TLS — the configuration most users will actually run).

**Evidence note:** internal inconsistency is unusually strong here, because console, CLI and metric
routinely disagree about the same node. The measurement unit is **time-to-diagnose**, not time-to-click,
and the blocked goal is "find out why". Convergent cold runs matter more than in any other domain, because
operator skill varies enormously and a single tester's trace is least representative exactly here.

## Domain gotchas

`gotchas.md` → *Stateful and clustered testing*. Plus:

- Never run a fault test against anything holding data you did not create.
- A certification that counts presence only cannot see Stale or Wrong.
- Every node has its own build; Phase 0 is a per-node table, and a mixed-version cluster is an
  illegitimate fix-verification target.
- Config on ephemeral storage resets on reschedule — re-apply and re-verify before trusting the run.
