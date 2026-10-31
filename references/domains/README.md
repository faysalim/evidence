# Domain files

The core method never changes between domains. What changes is which scope families apply, what "do the
thing" means concretely, which faults are worth injecting, what counts as first success, and how severity
maps. That is what these files carry.

**Read the closest one before briefing anyone**, including yourself. If none is close, say so in the report
and work from the families in `scope-playbooks.md` — then consider writing the missing file, because the
next person in your field will need it.

**Data and state**

| File | Product class |
|---|---|
| `distributed-database.md` | Replicated/partitioned store: failover, rebalance, membership, change feeds |
| `relational-database.md` | Transactional store: schema migration, isolation, planner, backup/restore |
| `message-queue.md` | Broker / event streaming: offsets, ordering, retention, delivery semantics |
| `data-pipeline.md` | ETL / streaming: sources and sinks, schema drift, backfills, exactly-once claims |
| `file-sync-storage.md` | Files synced across devices: conflict, quota, share links, deletion |

**Applications**

| File | Product class |
|---|---|
| `multi-tenant-saas.md` | One deployment, many organizations: tenant isolation, roles, quotas |
| `crm.md` | Multi-user business application with roles, import/export, automation, audit |
| `mobile-app.md` | Store-distributed app: permissions, offline, device fragmentation, policy gates |
| `desktop-app.md` | Installed app: installer, auto-update, code signing, OS integration, CLI beside GUI |
| `ai-product.md` | Model-backed feature: nondeterminism, injection, tool privilege, cost, eval denominators |

**Platform and infrastructure**

| File | Product class |
|---|---|
| `api-platform.md` | Public/partner API: spec as contract, idempotency, scopes, webhooks, versioning |
| `identity-provider.md` | Auth and SSO: sessions, tokens, MFA, federation, revocation, recovery |
| `licensing-server.md` | Entitlement issuing and validation, SaaS and self-hosted |
| `payments.md` | Checkout, subscriptions, refunds, processor integration |
| `observability-platform.md` | Metrics, logs, alerts: a product whose job is to tell the truth about something else |
| `infra-operator.md` | Kubernetes operator / IaC provider: reconcile idempotency, drift, CRD upgrade |
| `embedded.md` | Firmware and devices: OTA under power loss, no-screen failure indication, soak |

Several products are two of these at once. A licensing platform with a public API is
`licensing-server.md` **and** `api-platform.md`; a SaaS CRM is `crm.md` **and**
`multi-tenant-saas.md`. Read both, take the union of the fault catalogues, and reconcile the scope maps
once — not twice — against the 11-agent cap.

## Not yet written

Each of these is a distinct defect population that the families alone will under-serve. If you run one,
write the file afterwards: **search and ranking** (relevance as a measurable claim, index staleness),
**video and media** (transcode matrix, playback across devices, DRM), **marketplace and multi-sided
commerce** (seller/buyer asymmetry, payout correctness), **regulated records** (healthcare, finance:
audit immutability, retention mandates, consent), **browser extension** (permission scope, host-page
breakage, store review), **game client and backend** (cheat surface, matchmaking state, save integrity),
**scientific or numerical tooling** (floating-point reproducibility, unit errors).

## Every file has the same seven headings

So a reader who knows one knows them all:

1. **Do the thing** — the domain's version of the prime directive, anchored by the specific thing that
   looks green and is catastrophically broken. This is the sentence that makes the directive bite for
   someone in that field; the generic version slides off.
2. **Scope map** — family → what it is in this domain → notes, plus an **Agent** column: `own`, `→N`
   (merged into family N), `lead`, or `N/A`. The file declares its usual applicable set and the resulting
   agent count, and that count must fit the 11-agent cap before the operator is asked for more.
3. **Fault / failure catalogue** — what to inject, each under load, each its own run.
4. **Defect classes to look for by name** — naming them is what lets an agent recognise one. An unnamed
   defect class is one nobody looks for.
5. **Evidence and severity** — which evidence-standard sections apply, and the severity mapping,
   including which defects reach `critical`.
6. **Experience** — who the user is (there is rarely only one), where the experience lives, what first
   success is *concretely* (the milestone sequence that ends the clock), the domain's experience defect
   classes, and which evidence kind carries the domain.
7. **Domain gotchas** — the traps specific to testing this class of product.

## Writing a new one

Copy the headings, fill them from a real engagement rather than from first principles, and keep it to
60–100 lines. The value is in specificity: "three nodes formed and one write acknowledged and read back
from a different node" is useful; "the product works" is not.
