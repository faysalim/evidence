# Domain: observability and alerting platform

Agents and ingest, metrics, logs and traces, retention and downsampling, queries, dashboards and alerts —
a product whose entire value is that it tells the truth about something else.

## Do the thing

> The dashboard is green and every agent reports `connected`. Stop sending data entirely and see whether
> anything notices. Then cause the condition an alert exists to catch, and time how long until a human is
> told. **A connected agent is this domain's HTTP 200 — and a false green here is not a defect in the
> product, it is the product failing at its only job.**

## Scope map

| Family | In this domain | Agent | Notes |
|---|---|---|---|
| 1 Acquisition | pricing model, retention and cardinality claims | own | the pricing model *is* a limits claim |
| 2 Primary product | ingest and query | own ×2 | split: agent & ingest pipeline vs query, dashboards, alert evaluation |
| 3 Control plane | admin, retention config, access, **ingest quota** | own | |
| 4 Deployment | agent across target types | →2 | |
| 5 Entitlement | ingest limits, cardinality billing | →3 | |
| 6 Secondary | exporters, OpenTelemetry compatibility, integrations | own | |
| 7 Telemetry | its own self-monitoring | →8 | and see the gotcha below |
| 8 Security | PII in logs, per-team access, query-level authorization | own | |
| 9 Documentation | retention, resolution, alert-latency and SLO claims | own | |
| 10 State under fault | ingest outage, gaps, late data, clock skew, backfill | own | |
| 11 Upgrade | agent version skew, schema or index migration | own | |
| 12 Experience | **zero versus no data** | own | central in this domain, not cross-cutting |

**Usual set: 1,2×2,3,6,8,9,10,11,12 own + 4→2, 5→3, 7→8 = 10 agents.**

## Failure catalogue

Stop the agent entirely — does anything alert on *absence*? · cut the network between agent and ingest ·
clock skew of ±1 hour on the sending host · a metric with a million label values · a one-megabyte log line ·
out-of-order and late data · a query window straddling a retention or downsampling boundary · an alert
condition that flaps · an alert evaluated **during** an ingest outage · a p99 queried at a long range
where data has been downsampled · a scheduled report across a DST change · a team member removed while
their dashboard is shared · ingest quota exceeded.

## Defect classes to look for by name

**Missing data treated as "condition not met", so an outage silences the alert that should catch it** —
the absence of a no-data clause is this domain's canonical critical defect · **gaps rendered as zeroes**,
so a chart reads 0 requests per second instead of "unknown" · silent drops at a cardinality or quota
limit, with no user-visible counter · downsampling that changes an aggregate, so a long-range percentile
is simply wrong · late data never backfilled into an already-evaluated window · alert latency far longer
than documented · timezone and DST errors in scheduled reports · access control enforced at the dashboard
but not at the underlying query · PII ingested from logs with no redaction and unbounded retention.

## Evidence and severity

The oracle is **what you sent**: a generator with a known rate and known values, run against the product.
Grade the product's numbers against your generator and **never against the product's own ingest counters**
— the self-report rule from `evidence-standard.md` is not a caution in this domain, it is the whole
method, because the counters are themselves the thing under test.

Record per query: agent version, ingest endpoint, exact time window, retention tier and resolution served.
`evidence-standard.md` → *Background and scheduled work* (alert evaluation is scheduled work), *Stateful
systems under fault*, *Data pipeline runs* for ingest reconciliation.

| Observation | Severity |
|---|---|
| An alert that cannot fire for the condition it claims to watch | **critical** |
| Missing data rendered as zero | **critical** — it causes confidently wrong decisions |
| Access control at the dashboard but not the query | **critical** |
| Silent drops at a limit | **blocker** |
| Downsampling misreporting a percentile | **blocker** |
| Alert latency exceeding the documented SLO | **blocker** |

## Experience

**Who the user is:** the on-call engineer at three in the morning, who will act on whatever this product
says and has no second source.

**Where it lives:** whether a chart distinguishes zero from no-data; whether an alert names the resource,
the threshold and a next step; time from signup to a useful dashboard; how an alert is silenced without
silencing it forever; and whether the product admits when it has dropped your data.

**First success is:** a generated signal visible in a chart, and an alert on that signal firing to a real
destination — inside one session.

**Do the thing, for experience:**

> Make the signal stop. Count the minutes before the product tells anyone, and read exactly what it says
> when it does.

**Defect classes:** zero and no-data indistinguishable — an experience defect whose consequence is a wrong
operational decision, so it **inherits `critical`** · alert bodies with no resource and no next step ·
silencing with no expiry · onboarding that ends at "agent connected" instead of at a useful chart.

**Evidence note:** **state legibility**, borrowed from `embedded.md`, applies literally here. Enumerate the
states a signal can be in — present, genuinely zero, absent, dropped at a limit, delayed — against the
renderings the product can distinguish. A many-to-one mapping is a count, not a matter of taste.

## Domain gotchas

- You cannot test an alerting product without a **destination you own** — a test channel, a test mailbox,
  a test webhook. Arrange it first or the alert scope is `BLOCKED` and should be reported as such.
- Alert evaluation is on a schedule, so findings here have minutes of built-in latency. Use the short form
  with a hard cutoff, and run the long one as a background job.
- Cardinality and quota tests cost real money and can degrade a shared environment for everyone else in
  it. Warn the operator and ledger them.
- Your test data pollutes someone's dashboards and someone's bill. Use a dedicated namespace or tenant.
- **The product's own status page and self-monitoring are the least trustworthy evidence available**, for
  the same reason a cluster's own health endpoint is: it is the component under test reporting on itself.
