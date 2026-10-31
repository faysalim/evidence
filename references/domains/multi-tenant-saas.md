# Domain: multi-tenant SaaS

One deployment serving many organizations: tenant isolation, role matrices, seats and quotas, per-tenant
configuration, noisy neighbours, and the export path.

## Do the thing

> Create two tenants, A and B, with objects of the same name. Then, as A's admin, try to reach B's data by
> every route the product has: direct id, search, export, report, webhook, audit log, error message, and
> the endpoint the UI does not use. **A correct permissions screen is this domain's HTTP 200 — the export,
> the search index and the stack trace are where tenant B's data comes out.**

## Scope map

| Family | In this domain | Agent | Notes |
|---|---|---|---|
| 1 Acquisition | funnel, trial signup, tenant creation | own | tenant provisioning is where the isolation starts |
| 2 Primary product | the application, as an ordinary member | own | |
| 3 Control plane | tenant admin, users, roles, SSO config, audit | own | |
| 4 Deployment | SaaS | N/A | |
| 5 Entitlement | seats, plan limits, **quota enforcement** | own | a quota is a billing control, so it is correctness |
| 6 Secondary | public API, webhooks, integrations, mobile | own | the API is where UI-only enforcement is exposed |
| 7 Telemetry | per-tenant usage records | →8 | |
| 8 Security | **tenant isolation** and the authorization matrix | own ×2 | split: cross-tenant reachability vs role × action |
| 9 Documentation | plan limits, role descriptions, data-residency claims | own | role descriptions are behavioural claims |
| 10 State under fault | background jobs, cache, concurrent edit, tenant deletion | own | |
| 11 Upgrade | per-tenant migration, mixed-version window | own | tenants migrate at different times — that window is a scope |
| 12 Experience | invitation, role naming, hitting a quota | lead | |

**Usual set: 1,2,3,5,6,8×2,9,10,11 own + 4 N/A, 7→8, 12→lead = 10 agents.**

## Failure catalogue

Identical object names in two tenants · one user who belongs to two tenants · a tenant deleted while its
users have live sessions · a quota at exactly the limit and one over · one tenant generating 100× the load
of the others · a background job iterating every tenant · a search reindex spanning tenants · an export
requested by a read-only role · a cache key missing the tenant prefix · a feature flag flipped mid-request ·
a migration applied to tenant A and not tenant B · a webhook configured by tenant A pointed at a URL that
logs the payload · an invitation sent to an email that already belongs to another tenant.

## Defect classes to look for by name

**Cross-tenant leak through a cache key that omits the tenant** · leak through the search index · leak
through an export, report or CSV · leak through an error message, stack trace or id in a URL · a guessable
id that is not scope-checked (the ordinary object-level authorization defect, which in this domain is a
tenancy breach) · **a role matrix enforced in the UI only**, with the API ungoverned · a quota counted
per node, so N nodes grant N× the limit · a background job that iterates all tenants holding one tenant's
permissions · per-tenant configuration that silently falls back to a global default · tenant deletion that
leaves data, or that deletes a shared record.

## Evidence and severity

**The two-tenant fixture is the harness.** Tenants A and B, identical in shape, each containing distinct
sentinel values that exist nowhere else. Then every isolation finding reduces to one sentence: *sentinel
B appeared in A's output, here it is.* A single-tenant environment cannot produce that evidence, so
standing up the second tenant is the first task of the scope, not a refinement.

`evidence-standard.md` → *Authorization and permission matrices* (run it per tenant, not once),
*Background and scheduled work*, *Stateful systems under fault* for the cache and concurrency cases.

| Observation | Severity |
|---|---|
| Any cross-tenant data visibility, by any route | **critical** |
| Role matrix enforced in the UI but not the API | **critical** — the API is the product |
| Quota not enforced where it is a billing control | **blocker** |
| One tenant able to degrade the service for others | **blocker** |
| Per-tenant config silently falling back to a global default | **major**, **critical** if the setting is a security control |

## Experience

**Who the user is:** the tenant administrator onboarding a team on day one, and the member who was given
a restricted role and does not know it.

**Where it lives:** invitation and onboarding; whether role names mean what they grant; what happens at
the quota boundary; discoverability of per-tenant configuration; and what a user without permission
actually sees.

**First success is:** the tenant admin invites a second user, who signs in and completes the core task
under a restricted role.

**Do the thing, for experience:**

> Hit the quota deliberately. See whether the product names the limit, the cost, and the way to raise it —
> or just fails.

**Defect classes:** role names that do not describe what they grant · a permission denial rendered as a
`500` or a blank screen, so it looks like an outage · quota failures that name no limit · an invitation
that dead-ends for someone who already has an account in another tenant · an audit log the admin cannot
actually read.

**Evidence note:** the "actively misled" clause carries this domain. A permissions screen that shows a
capability the role does not have, or a quota display that disagrees with enforcement, is a product bug and
an experience defect under one id — and it inherits the severity of what it leads the admin to do.

## Domain gotchas

- A single-tenant test environment finds none of this domain's real defects. Two tenants is the minimum
  viable harness.
- Shared staging usually already contains other people's tenants. Treat every id you did not create as
  production data: never write to it, and never include it in the report.
- Several leaks appear only *after* a reindex, a cache warm or a nightly job. The finding therefore has a
  latency — record when you looked as well as what you saw, and re-check after the job runs.
- **Admin impersonation ("view as user") usually bypasses the checks you are testing.** Run the matrix as
  a real session of a real restricted user.
- Load-testing one tenant to prove noisy-neighbour behaviour degrades the environment for every other
  tenant in it. Only do it where you own the whole deployment, and ledger it.
