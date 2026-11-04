# Domain: payments and checkout

Checkout, subscriptions, refunds, and integration with a processor. The domain where a single defect moves
money, and where the safe way to test is also the way that hides the bugs.

## Do the thing

> Checkout shows "Payment successful". Reconcile your own ledger against the processor's record of the same
> attempt — they disagree by one charge. **A success page is this domain's HTTP 200, and the processor's
> ledger is the only source of truth.**

## The test-mode trap

`scope-playbooks.md` §3 says to use test mode only and never real payment details. That is correct as
**safety** and misleading as **evidence**: test mode does not exercise declines, 3DS challenges, webhook
signature failures, processor latency, or the processor's own outages. Keep the rule, and say so in Not
Verified — "test mode does not exercise X, Y, Z" — so nobody reads a clean test-mode run as a working
checkout.

## Scope map

| Family | In this domain | Agent | Notes |
|---|---|---|---|
| 1 Acquisition | pricing, cart, checkout flow | own | |
| 2 Primary product | the purchased thing | N/A or →own | depends on the product |
| 3 Control plane | subscription management, invoices, dunning | own | |
| 4 Deployment | SaaS | N/A | |
| 5 Entitlement | what the payment grants, and when it is revoked | →3 | |
| 6 Secondary | processor SDK, webhook receiver | own | |
| 7 Telemetry | analytics on a page that carries payment data | →8 | |
| 8 Security | PCI surface, card data never touching your logs, webhook signature verification | own | |
| 9 Documentation | API, webhook contract, refund policy as published | own | |
| 10 State under fault | timeout, retry, double-submit, webhook replay | own | the core |
| 11 Upgrade | processor API version migration; stored-payment-method migration | own | |
| 12 Experience | the ambiguous post-timeout state | own | |

**Usual set: 1,3,6,8,9,10,11,12 own + 5→3, 7→8 = 9 agents.**

## Failure catalogue

Connection cut after submit, before the response · the same payment submitted twice concurrently · a
retried request carrying the same idempotency key · a retried request carrying a *different* key · webhook
delivered twice · webhook delivered out of order · webhook with an invalid signature · processor returning
a soft decline, then succeeding · 3DS challenge abandoned mid-flow · refund issued while a dispute is open ·
currency with three decimal places · subscription renewal on 29 February · a card expiring between
authorization and capture.

## Defect classes to look for by name

Double charge on client retry (idempotency key absent or not honoured) · charge captured with no order
created, or an order created with no charge · **the amount displayed differing from the amount charged** ·
webhook replay granting entitlement twice · refund that does not revoke entitlement · currency rounding
error · a subscription that keeps billing after cancellation, or stops billing without cancelling · raw
processor decline codes shown to the buyer.

## Evidence and severity

Reconcile **your own ledger against the processor's API or dashboard, per attempt** — including the retried
and abandoned ones, which is where the discrepancies are. `evidence-standard.md` → *Stateful systems under
fault* for the concurrency and timeout cases, *Background and scheduled work* for renewals and dunning.

Specific proofs: idempotency honoured on client retry (two concurrent submits, exactly one charge);
webhook replay granting nothing twice; the refund path revoking what the charge granted; rounding verified
on a three-decimal currency.

| Observation | Severity |
|---|---|
| **Any wrong money movement** — double charge, charge without order, wrong amount | **critical** |
| Refund not revoking entitlement | **blocker** (revenue) |
| Billing after cancellation | **blocker** |
| Raw decline codes shown to the buyer | **major** |

## Experience

**Who the user is:** the buyer, at the moment of maximum anxiety, plus finance and support afterwards.

**Where it lives:** checkout clarity (total, currency, when they will be charged), decline messages, **the
ambiguous state after a timeout**, receipts, refund visibility, and the 3DS handoff.

**First success is:** a completed purchase whose charge, order and receipt all agree.

**Do the thing, for experience:**

> Submit the payment and cut the connection before the response arrives. Read what the buyer sees: do they
> know whether they were charged, and what to do next?

**Defect classes:** **the ambiguous post-timeout state that invites a second submit** — an experience
defect that *causes* the double charge, so it belongs to scope 10 and 12 under one id and inherits
`critical` · raw processor decline codes shown to a buyer who cannot act on them · a total or currency
that changes at the final step · a receipt that never arrives.

**Evidence note:** the "actively misled" clause carries this domain — a displayed amount that differs from
the charged amount is always a product bug as well. Severity inherits the consequence of the action the
user is invited into, which is why the ambiguous dialog is critical rather than minor.

## Domain gotchas

- **Never enter real payment details.** This is a hard rule from the skill's safety section, not a
  preference; the test-mode qualifier above exists because of it.
- A processor's test mode has its own documented test cards for declines and 3DS — use those rather than
  concluding the paths are untestable.
- Idempotency keys are usually scoped per endpoint and per time window. Read the window before concluding
  a key was ignored.
- Webhook endpoints must be tested for signature verification by sending an *unsigned* request; many
  accept it.
- Reconciliation needs the processor's view. Without read access to it, say so and mark the scope
  `BLOCKED` — your own ledger alone cannot find a discrepancy with the processor.
