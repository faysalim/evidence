# Domain: billing, subscriptions and metering

Plans, usage aggregation, proration, invoices, tax, dunning and revenue recognition. Where `payments.md`
tests the money **rail**, this tests the money **arithmetic** — and read both, because a correct charge of
a wrong amount is still a wrong amount.

## Do the thing

> The invoice renders and the card was charged. Recompute that invoice by hand from the usage records and
> the plan rules — the mid-cycle upgrade, the proration, the tiered overage, the credit, the tax — and see
> whether you get the same number. Then replay the usage for a period that has already been invoiced.
> **An invoice that renders is this domain's HTTP 200, and the only oracle is arithmetic you did
> yourself.**

## Scope map

| Family | In this domain | Agent | Notes |
|---|---|---|---|
| 1 Acquisition | **the pricing page is a contract** | →9 | `own` when pricing is a live self-serve funnel |
| 2 Primary product | the metered product | N/A or →own | it is tested by its own domain file |
| 3 Control plane | plan management, subscriptions, credits, invoices | own | |
| 4 Deployment | SaaS | N/A | |
| 5 Entitlement | plan → feature gates, behaviour at the limit | →3 | |
| 6 Secondary | processor, tax engine, accounting export | own | three third parties, three sets of wrong answers |
| 7 Telemetry | **usage records are the billing input** | own | not telemetry in this domain — it is correctness |
| 8 Security | who can issue a credit or change a plan; invoice access across accounts | own | |
| 9 Documentation | the pricing page, and **what counts as one unit** | own | "an API call" is a definition, and definitions are claims |
| 10 State under fault | period boundary, duplicate usage, retroactive events | own ×2 | split: usage aggregation vs subscription lifecycle |
| 11 Upgrade | price changes with existing subscribers, grandfathering, plan migration | own | |
| 12 Experience | the surprise bill | own | |

**Usual set: 3,6,7,8,9,10×2,11,12 own + 1→9, 2 N/A, 4 N/A, 5→3 = 10 agents.**

## Failure catalogue

A mid-cycle upgrade **and** a mid-cycle downgrade — different code paths · a plan change on the first and
the last day of a period · usage submitted twice with the same idempotency key, and without one · usage
arriving after the period closed · usage spanning the boundary · a tiered price at the exact tier edge · a
currency with three decimals and one with none · a 31st-of-the-month anniversary in a 30-day month, and
29 February · a trial converting · a cancellation mid-period and a reactivation · a credit larger than the
invoice · a refund after revenue was recognised · a customer moving tax jurisdiction · a failed payment
and the whole dunning sequence · a paused subscription · concurrent plan changes from the UI and the API ·
clock skew between the metering service and the billing service.

## Defect classes to look for by name

**Proration arithmetic wrong on a mid-cycle change** — the most common defect in the domain, and upgrade
and downgrade must be counted separately · **usage double-counted or lost at the period boundary** · late
events silently dropped, or retroactively altering a closed invoice · **an invoice mutated after issue** —
it must be immutable, and a correction is a credit note, not an edit · a tier boundary off by one ·
rounding applied per line where it should be per invoice or the reverse, so the total differs from the sum
of the lines · currency minor-unit errors · **entitlement granted before payment, or revoked before the
period ends** · dunning that cancels a paying customer, or never cancels a non-paying one · a
grandfathered price lost through an unrelated change · revenue recognised at the wrong time · a credit
that can be applied twice.

## Evidence and severity

The oracle is a **hand-built expected invoice** — a spreadsheet computed from the usage ledger and the
published rules, before you look at what the product produced. Almost nobody builds one, which is exactly
why these defects survive to production and are found by a customer.

Record per run: plan version, price-list version, period boundaries **with timezone**, the usage ledger,
the tax jurisdiction, and the full sequence of lifecycle events with timestamps.

`evidence-standard.md` → *Stateful systems under fault* (boundaries and concurrency), *Background and
scheduled work* (invoice generation, renewal, dunning), *Data pipeline runs* (usage aggregation reconciles
exactly like a pipeline, per partition and not in total).

| Observation | Severity |
|---|---|
| Any wrong amount invoiced or charged | **critical** |
| Usage lost or double-counted | **critical** |
| An invoice mutated after issue | **critical** — it is an audit record |
| Entitlement granted before payment, or revoked early | **blocker** |
| Dunning cancelling a paying customer | **blocker** |
| A grandfathered price silently lost | **blocker** |
| Rounding inconsistent between lines and total | **major** — and it is the first thing finance will find |

## Experience

**Who the user is:** a customer opening a bill they did not expect, and the finance person who has to
explain it.

**Where it lives:** whether the current period's accruing usage is visible *before* the invoice; whether a
plan change shows its prorated cost before it is confirmed; whether an invoice line can be traced back to
usage; the tone and clarity of dunning; and the cancellation path.

**First success is:** a customer can predict their next invoice from what the product shows them, and be
right.

**Do the thing, for experience:**

> Run up usage, then ask the product what the next bill will be. Compare that with the invoice when it
> arrives, and report the gap as a number.

**Defect classes:** **no visibility of accruing usage until the invoice** — the surprise bill, which is a
churn event rather than a complaint · a plan change with no preview of the charge · invoice lines that
cannot be traced to anything · dunning that reads as a threat · a cancellation flow that takes one more
period without saying so.

**Evidence note:** **predictability** is this domain's first-run measurement — the gap between what the
product said the bill would be and what it was. When that gap is the product's error rather than the
customer's usage, it is the wrong-amount class and inherits its severity.

## Domain gotchas

- **A controllable clock is the whole scope.** Every defect here lives at a period boundary, and real time
  gives you one boundary per month. Find the product's clock-advance mechanism or report family 10 as
  `BLOCKED` beyond a single period.
- Processor **test mode** and a tax engine's test mode only; never real payment details, per the hard rule
  in `payments.md`. State in Not Verified what test mode does not exercise.
- Tax engines are third parties with their own rates and their own test behaviour; their
  misconfiguration will masquerade as a product defect. Prove a baseline before filing.
- **Ask finance for a reconciliation report and diff it.** It is faster than any test you can write, and
  it is the only evidence the business already trusts.
- Never issue a real credit, refund or plan change on an account you do not own.
- Usage ledgers are often append-only in production and mutable in staging. Know which you are on, because
  the mutable one hides the defect you are hunting.
