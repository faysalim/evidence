# Domain: CRM / multi-user business application

Roles and record-level permissions, import and export, deduplication and merge, workflow automation, audit
trail, data residency and erasure obligations, integrations and webhooks, email sync.

## Do the thing

> The permissions page says the sales rep cannot see Finance's accounts. Log in **as the rep** and run a
> report, use global search, and export to CSV — the accounts are in the file. Then: erasure returned
> "Contact deleted"; search the index, the exports and the integration payloads — the contact is still
> there. **The role matrix is correct on the settings page; the export is where the data leaks.**

## Scope map

| Family | In this domain | Agent | Notes |
|---|---|---|---|
| 1 Acquisition | marketing site, trial signup, onboarding | own | |
| 2 Primary product | web app; mobile app if one ships | own (or N/A) | |
| 3 Control plane | admin: roles, record permissions, fields, automation, invitations | own | the current playbook tests *role*-level only; record-level is the gap |
| 4 Deployment | SaaS only, usually | N/A | |
| 5 Entitlement | seats and plan gating | →3 | |
| 6 Secondary | public API, webhooks, integrations, email sync | own | |
| 7 Telemetry | analytics, **data residency** | own | observe the egress *region*, not the settings page |
| 8 Security | cross-tenant, injection, session, export authz | own | |
| 9 Documentation | API reference, admin guide, field semantics | own | |
| 10 State under fault | concurrent edit, erasure-as-state, audit-as-ledger, bulk ops | own | |
| 11 Upgrade | tenant migration, field/schema change with data, recycle-bin retention | own | |
| 12 Experience | permission opacity, import errors, merge review, automation debuggability | own | |

**Usual set: 1,2,3,6,7,8,9,10,11,12 own + 5→3 = 9–10 agents.**

## Failure catalogue

Two users editing one record simultaneously · an import interrupted halfway · a merge of two records with
conflicting field values · erasure of a contact referenced by an open deal · an automation whose trigger
fires during a bulk import · a webhook endpoint returning 500, then recovering · email sync reconnecting
after a token expiry · a role changed while a user holds an open session · a report run as one role and
scheduled by another · deduplication across 10,000 near-identical records.

## Defect classes to look for by name

**Cross-role leakage through a non-UI channel** (report, global search, export, webhook payload,
notification email) · incomplete erasure (present in the search index, an export, or an already-sent
integration payload) · silent last-write-wins on concurrent edit · automation double-fire to customers ·
audit-trail gaps (a change made via API, import, merge or automation that never appears) · irreversible
bulk operation with no preview or recycle bin · report totals that disagree with the records a role can
see · import that partially applies and cannot be resumed or rolled back.

## Evidence and severity

`evidence-standard.md` → *Authorization and permission matrices* (the **channel** column is the whole
point), *Background and scheduled work*, *Stateful systems under fault* for concurrency.

Erasure is proved by a **positive search for the identifier in every reachable store**, with the
unreachable ones — backups, integrations already delivered — stated under "what this finding does NOT
claim". Automation is proved by **counting** side effects: importing 10,000 rows must not send 10,000
emails. Audit completeness is proved by performing one edit through *each* channel and showing each
appears.

| Observation | Severity |
|---|---|
| Cross-role or cross-tenant leak through any channel | **critical** |
| Incomplete erasure | **blocker** (legal) |
| Automation double-fire to real customers | **blocker** |
| Silent lost update on concurrent edit | **major** |
| Audit-trail gap | **major** (compliance) |

## Experience

**Who the user is:** the rep, the admin, the importer, the auditor. Four different products sharing a
database.

**Where it lives:** permission opacity above all — can a user tell what they are *not* allowed to see, or
does a restricted record look like a record that does not exist? Then bulk-import error reporting, the
dedup/merge review flow and its undo, audit-trail legibility for the person who will be asked about it,
and automation debuggability ("why did this email go out?").

**First success is:** a contact created, found by search, and appearing in a report — by a non-admin user.

**Do the thing, for experience:**

> Import a 10,000-row CSV containing 37 bad rows and fix them using only the import report. Then merge two
> contacts and try to undo it.

**Defect classes:** import reports that **count but do not locate** (37 errors, no row numbers, no
downloadable reject file) · **permission-induced duplicates** — search returns nothing for a restricted
record, the rep concludes it does not exist and creates another, so a UX defect *manufactures* a data
defect, which is the single best argument for why experience belongs in a QA run · irreversible bulk
operations with no preview · automation with no "why did this fire" trace.

**Evidence note:** internal inconsistency is very strong — the list view shows "restricted" while global
search shows nothing, two answers to the same question. A useful measurement is duplicates created per
hundred searches.

## Domain gotchas

- **Test as the role, not as an admin impersonating the role** where the product offers both; impersonation
  frequently uses a different code path.
- Export and report engines often bypass the UI's permission layer entirely — they are separate services.
- Erasure "completed" is a self-report. Search for the identifier.
- A test tenant's automations can email real addresses. Point them at mailboxes you control and check
  before enabling.
- Record-level permissions interact with sharing rules, ownership and hierarchy; test the *combination*,
  because each alone usually works.
