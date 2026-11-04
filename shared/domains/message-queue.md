# Domain: message broker / event streaming

Topics and partitions, producers and consumer groups, offsets, retention and compaction, and a
delivery-semantics claim that every downstream system has been built on top of.

## Do the thing

> The broker is up, every consumer reports `running`, and lag is zero. Publish a numbered sequence, kill
> the partition leader mid-publish, restart, and reconcile what the consumer received against what you
> acknowledged sending. **`lag: 0` is this domain's HTTP 200 — and it is also exactly what a consumer that
> has skipped records reports.**

## Scope map

| Family | In this domain | Agent | Notes |
|---|---|---|---|
| 1 Acquisition | docs / download | N/A | |
| 2 Primary product | publish and consume | own ×2 | split: producer ack path vs consumer offset path |
| 3 Control plane | admin API, topic management, ACLs, metrics | own | |
| 4 Deployment | cluster, replication factor, storage class | own | storage class is a durability decision disguised as config |
| 5 Entitlement | if licensed | →4 | |
| 6 Secondary | client libraries per language | own | defaults differ per client and that is a bug source |
| 7 Telemetry | lag and throughput metrics | →8 | the lag metric itself is tested in family 10 |
| 8 Security | per-topic ACLs, auth, in-transit and at-rest encryption | own | |
| 9 Documentation | **the delivery-guarantee wording** | own | "at-least-once" and "exactly-once" are different pass criteria |
| 10 State under fault | the core | own ×2 | split: ordering & duplication under fault vs retention, compaction, rebalance |
| 11 Upgrade | rolling upgrade, mixed broker versions, log-format change | own | |
| 12 Experience | operator diagnosability | lead | |

**Usual set: 2×2,3,4,6,8,9,10×2,11 own + 5→4, 7→8, 12→lead = 10 agents.**

## Failure catalogue

Kill the leader of one partition mid-publish · partition the network between brokers · fill the disk ·
retention expiring while a consumer is behind · a consumer-group rebalance during consumption · a consumer
that processes and then dies before committing · a consumer that commits and then dies before processing ·
duplicate publish with the same key · compaction with tombstones · a slow consumer and growing lag · clock
skew against time-based retention · an ACL revoked mid-stream · a rolling upgrade with mixed versions · a
consumer group reset to earliest and to latest · a producer with `acks=1` against a documented durability
claim.

- **Published performance claim under saturation** (scope 8b): reproduce the claimed number on a
  stated rig, then measure the degradation curve at 10x and 100x that load. At saturation, establish
  whether it sheds load, queues unboundedly or loses data — queueing to out-of-memory is a
  durability defect wearing a performance costume.

## Defect classes to look for by name

**An acknowledged publish lost on leader failover** · ordering broken within a partition or key under
rebalance · at-least-once behaviour where exactly-once is documented — and the reverse, silent
deduplication that hides a producer bug · **an offset committed past records that were never processed** ·
retention deleting data a lagging consumer had not read, with nothing raised · a rebalance storm in which
consumers never stabilise · compaction losing the final value for a key · a group reset that silently
reprocesses or silently skips · **a lag metric computed from the wrong watermark, so it reads zero while
the consumer is behind.**

## Evidence and severity

The oracle is a **numbered sequence per key and per partition**, produced by your own generator and
reconciled at the consumer. Report **Missing, Duplicated and Out-of-order as three separate counts over
the same denominator**: a matching total hides offsetting loss and duplication, which is the single most
common false pass in this domain.

`evidence-standard.md` → *Stateful systems under fault* (the fault schedule), *Data pipeline runs* (the
reconciliation method), *Background and scheduled work* (retention and compaction are scheduled work).
Record per run: broker version per node, client library and version, `acks` and `enable.auto.commit`
settings, replication factor, min in-sync replicas, and the fault with its timestamp.

| Observation | Severity |
|---|---|
| An acknowledged publish lost | **critical** |
| Offset advanced past unprocessed records | **critical** |
| Ordering broken where the docs guarantee it | **critical** |
| Retention silently deleting unread data | **blocker** |
| Lag metric reading zero while the consumer is behind | **blocker** — it is the control every operator watches |
| Rebalance storm | **major**, **blocker** if it never converges |

## Experience

**Who the user is:** the platform operator during an incident, and the application developer who has to
know where their message went.

**Where it lives:** whether a consumer's position is legible at all; what the operator sees during a
rebalance; whether an offset reset can be previewed before it is applied; dead-letter visibility; and
time-to-diagnose "one message is missing".

**First success is:** one message published, consumed, and its position committed — verified from the
broker's own record *and* from the consumer side, not from either alone.

**Do the thing, for experience:**

> Make one consumer in a group of three fail permanently. From the product's output alone, name which
> records are stuck and the exact command that skips or replays them.

**Defect classes:** position and lag presented as a number with no denominator · an offset reset with no
preview of what will be reprocessed · a dead-letter destination nothing surfaces · a rebalance that looks
indistinguishable from an outage.

**Evidence note:** record time-to-diagnose, and alongside it **alert latency** — the gap between the
failure and the operator's first opportunity to know. A silent retention deletion that nobody learns about
for a day is a diagnosability defect whose consequence is data loss, and it inherits that severity.

## Domain gotchas

- Single-broker testing finds nothing that matters here. The replication factor is the test.
- **Many brokers acknowledge at the leader before replication completes.** The default is not the
  documented guarantee; read the acks setting before concluding anything about durability.
- "Exactly-once" is almost always scoped to one specific producer→broker→consumer path. Read which path,
  then test that claim and no other.
- Disk-full is a distinct and usually worse failure mode than broker-down. Test it separately.
- Client defaults vary by language and version. Record both on every finding, or the result is not
  reproducible by the person fixing it.
- Consumer-group ids are global state in a shared cluster: using an existing one moves somebody's offsets.
  Generate your own and ledger them.
