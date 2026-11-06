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
| `obfuscator-tooling.md` | Obfuscator / compiler / SDK tooling: semantic preservation, determinism, self-certification |
| `data-pipeline.md` | ETL / streaming: sources and sinks, schema drift, backfills, exactly-once claims |
| `file-sync-storage.md` | Files synced across devices: conflict, quota, share links, deletion |
| `collaboration.md` | Real-time co-editing: convergence, lost updates, offline reconcile, live revocation |
| `cms.md` | Content platform: authoring vs published surface, embargo leaks, schema migration |
| `feature-flags.md` | Flag / experiment service: wrong variant, default-when-unreachable, exposure counts |
| `backup-and-recovery.md` | Backups and restores: chain integrity, retention, immutability, RTO |
| `search-and-ranking.md` | Index freshness, relevance as a measured claim, facet counts, permission-aware results |

**Applications**

| File | Product class |
|---|---|
| `multi-tenant-saas.md` | One deployment, many organizations: tenant isolation, roles, quotas |
| `crm.md` | Multi-user business application with roles, import/export, automation, audit |
| `mobile-app.md` | Store-distributed app: permissions, offline, device fragmentation, policy gates |
| `desktop-app.md` | Installed app: installer, auto-update, code signing, OS integration, CLI beside GUI |
| `ai-product.md` | Model-backed feature: nondeterminism, injection, tool privilege, cost, eval denominators |
| `scheduling-and-booking.md` | Availability, recurrence, DST, double-booking under concurrency, reminders |

**Education**

| File | Product class |
|---|---|
| `ai-tutor.md` | Model-backed tutor across levels: subject accuracy, answer leakage, level fit, safety for minors |
| `education-platform.md` | LMS / courseware: gradebook arithmetic, deadlines, accommodations, roster integration |

**Money and commerce**

| File | Product class |
|---|---|
| `payments.md` | Checkout, refunds, processor integration — the money rail |
| `billing-and-metering.md` | Plans, usage, proration, invoices, tax, dunning — the money arithmetic |
| `ecommerce-marketplace.md` | Catalog, inventory under concurrency, order state machine, fulfilment, payout |
| `licensing-server.md` | Entitlement issuing and validation, SaaS and self-hosted |

**Platform and infrastructure**

| File | Product class |
|---|---|
| `api-platform.md` | Public/partner API: spec as contract, idempotency, scopes, webhooks, versioning |
| `identity-provider.md` | Auth and SSO: sessions, tokens, MFA, federation, revocation, recovery |
| `secrets-and-pki.md` | Secret storage, dynamic credentials, key rotation, certificate renewal and revocation |
| `messaging-delivery.md` | Email, SMS and push: deliverability, suppression, bounces, template rendering |
| `workflow-engine.md` | Durable execution: replay determinism, duplicated side effects, in-flight deploys |
| `observability-platform.md` | Metrics, logs, alerts: a product whose job is to tell the truth about something else |
| `infra-operator.md` | Kubernetes operator / IaC provider: reconcile idempotency, drift, CRD upgrade |
| `embedded.md` | Firmware and devices: OTA under power loss, no-screen failure indication, soak |

Twenty-seven files. Several products are more than one of them at once: a licensing platform with a public
API is `licensing-server.md` **and** `api-platform.md`; a SaaS CRM is `crm.md` **and**
`multi-tenant-saas.md`; a subscription product is `payments.md` **and** `billing-and-metering.md`; a
storefront with real search is `ecommerce-marketplace.md` **and** `search-and-ranking.md`; an AI tutor
inside a school product is `ai-tutor.md`, `education-platform.md` and `multi-tenant-saas.md` together.

Read each one that applies, take the **union of the fault catalogues**, and reconcile the scope maps
**once** — not once per file — against the 11-agent cap. Two files that each claim family 8 get one
family-8 agent briefed from both, never two.

## Not yet written

Each of these is a distinct defect population that the families alone will under-serve. If you run one,
write the file afterwards — the next person in your field will need it.

**Closest to earning a file:** real-time collaboration (concurrent edit convergence, presence, offline
merge, undo across users) · compiler, obfuscator and SDK tooling (semantic preservation under
transformation, semver and packaging, deterministic output) · analytics and BI (aggregate consistency
across filters, row-level security, export fidelity) · data warehouse and query engine (partition pruning,
runaway query cost, time travel, concurrent writers on object storage) · feature flags and experimentation
(evaluation consistency across SDKs, sticky bucketing, sample-ratio mismatch, kill-switch latency) ·
network gateway, proxy and CDN (request smuggling, header mangling, cache keys, config reload under load) ·
CI/CD platform (hermeticity, cache poisoning, secrets in logs, artifact provenance) · CMS and publishing
(draft versus live, scheduled publish, cache invalidation, multi-locale).

**Also distinct, narrower audience:** video and media (transcode matrix, playback across devices, DRM,
captions) · regulated records in healthcare and finance (audit immutability, retention mandates, consent,
erasure versus retention conflict) · browser extension (permission scope, host-page breakage, store
review) · game client and backend (cheat surface, matchmaking state, save integrity) · scientific and
numerical tooling (floating-point reproducibility, unit errors) · payroll and tax calculation
(jurisdiction rules, effective dates, retroactive correction) · VPN and remote access (split tunnel, DNS
leak, kill switch) · document generation (font embedding, pagination, barcode scannability).

**Do not write these as domain files.** Accessibility, localization, privacy and performance are
cross-cutting and already live in the families and in `experience.md`. A domain file earns its place only
when it has a distinct **oracle**, a fault catalogue not already written down, and a severity mapping that
differs from the generic one. Anything that fails all three belongs in a family.

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

A file may add **one** domain-specific section, placed directly after *Do the thing*, when the domain has a
structure the seven headings cannot hold: `payments.md` adds *The test-mode trap* because the safe way to
test is also the way that hides the bugs, and `ai-tutor.md` adds *The level axis* because level is a test
matrix rather than a setting. One extra, for a stated reason. Nothing else is optional — in particular
*Defect classes to look for by name*, which is the heading that does the most work.

## Writing a new one

Copy the headings, fill them from a real engagement rather than from first principles, and keep it to
60–110 lines — or up to about 150 when the domain carries a **test matrix of its own** that the families
cannot express, as `mobile-app.md` does for devices and `ai-tutor.md` does for learner levels. That is the
only accepted reason to run long; a longer file for any other reason is padding. The value is in
specificity: "three nodes formed and one write acknowledged and read back from a different node" is
useful; "the product works" is not.
