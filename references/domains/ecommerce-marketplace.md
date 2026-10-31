# Domain: e-commerce and marketplace

Catalog, inventory, cart and checkout, fulfilment and returns — and on a marketplace, two sides with
opposite interests plus a payout. `payments.md` tests the money rail; this tests whether you can sell
something you actually have.

## Do the thing

> The order confirms and the dashboard shows one sale. Have two buyers purchase the last unit at the same
> instant, change the price while a cart is holding it, and then reconcile the stock count, the order, the
> payment and the payout against each other. **An order confirmation is this domain's HTTP 200 — and
> overselling one unit is a promise you cannot keep.**

## Scope map

| Family | In this domain | Agent | Notes |
|---|---|---|---|
| 1 Acquisition | catalog, search, product pages, cart | own | pair with `search-and-ranking.md` when search is substantial |
| 2 Primary product | checkout and **the order state machine** | own | |
| 3 Control plane | seller console, inventory, orders, fulfilment, returns | own ×2 | on a marketplace, split: seller tools vs operations and moderation |
| 4 Deployment | SaaS | N/A | |
| 5 Entitlement | seller plans and limits | →3 | |
| 6 Secondary | processor, tax, shipping-rate and fulfilment integrations | own | four third parties, four sets of wrong answers |
| 7 Telemetry | analytics on pages carrying payment data | →8 | |
| 8 Security | price and quantity tampering, buyer/seller isolation, PII in exports | own | |
| 9 Documentation | shipping, returns and payout policy **as published** | own | a published policy is a promise with a price |
| 10 State under fault | **inventory under concurrency**, abandoned carts, payment timeout, partial fulfilment | own | |
| 11 Upgrade | catalog and price migration, tax-rule change with open orders | own | |
| 12 Experience | the ambiguous post-payment state, and the seller's trust in the numbers | own | |

**Usual set: 1,2,3×2,6,8,9,10,11,12 own + 4 N/A, 5→3, 7→8 = 10 agents.**

## Failure catalogue

Two buyers, one unit, simultaneously · a price changed while the item sits in a cart · a coupon applied
twice, stacked, after expiry, and by someone it was not issued to · a cart held for a week · tax recomputed
when the address changes at the last step · a shipping quote for an unserviceable address · a partial
fulfilment and a partial refund · a return **after** the seller was paid out · a cancellation after the
shipping label was bought · a currency with no minor unit · one item in two concurrent orders where one
payment fails · stock corrected by hand while orders are in flight · a seller deleting a listing with open
orders · a payout period spanning a refund · a fraud hold released late · price and quantity fields
tampered with in the request.

## Defect classes to look for by name

**Overselling** — stock checked and decremented with no reservation and no constraint. It is this domain's
canonical critical defect and it is invisible without genuine concurrency · **the price charged differing
from the price displayed**, including a cart that silently reprices · coupon logic that can be stacked,
replayed or used after expiry · tax or shipping computed on the wrong address or at the wrong moment · an
order state machine with an unreachable or dead-end state — paid and unfulfillable, cancelled and shipped ·
**a refund that does not restock, or restocks twice** · a payout computed before refunds and chargebacks
settle · inventory and the ledger diverging with no reconciliation anywhere in the product · another buyer's
PII in a seller-facing export · price or quantity accepted from the client.

## Evidence and severity

Reconcile **four ledgers against each other, per order**: stock movements, the order record, the payment as
the processor reports it, and the payout. Agreement between any two is not enough — the defects live where
three agree and the fourth does not, which is why this domain needs four and not two.

Overselling is proved by genuine simultaneity (the "run twice at once" rule) and then **counted**: two
confirmations, one unit. Record catalog and price-list version, exact timestamps, the concurrency method,
and the processor's own record.

`evidence-standard.md` → *Stateful systems under fault*, *Authorization and permission matrices* (buyer,
seller, operator — and buyer against buyer), *Background and scheduled work* (cart expiry, payout runs,
fraud holds).

| Observation | Severity |
|---|---|
| Overselling, or a wrong amount charged | **critical** |
| A refund that does not restock, or restocks twice | **critical** |
| A payout wrong | **critical** — it is someone's income |
| Price or quantity accepted from the client | **critical** |
| Another buyer's PII in a seller export | **critical** |
| An order reaching a dead-end state | **blocker** |
| Coupon stacking or replay | **blocker** |
| Tax or shipping wrong | **blocker** |

## Experience

**Who the user is:** the buyer at the moment of payment — and, on a marketplace, the seller whose income
depends on numbers they did not compute. Two users, and the seller is the one nobody tests.

**Where it lives:** total, currency and delivery promise shown before commitment; **the ambiguous state
after a payment timeout**; order tracking; the returns path; and, for the seller, whether a payout can be
traced to the orders that make it up.

**First success is:** a purchase whose order, charge, stock movement and receipt all agree — and, for a
seller, a payout they can reconcile unaided.

**Do the thing, for experience:**

> Buy the last unit, cut the connection before the confirmation arrives, and read what the buyer sees. Then,
> as the seller, try to explain one payout using the product alone.

**Defect classes:** **the ambiguous post-payment state that invites a second order** — inherited from
`payments.md`, and here it also oversells · a delivery promise the fulfilment chain cannot keep · a returns
policy that is published but unreachable inside the product · **a payout statement that cannot be traced to
orders**, the seller-side diagnosability defect that generates the most expensive support tickets in the
business · stock numbers the seller does not trust, after which they keep their own spreadsheet and the
product has already lost.

**Evidence note:** severity inheritance is explicit here. An experience defect that causes a second order
inherits `critical` from the overselling and double charge it creates — not `minor` from the dialog it lives
in.

## Domain gotchas

- **Test mode only, never real payment details** — the hard rule from `payments.md`, and its evidence
  caveat carries too: test mode does not exercise declines, 3DS or processor latency, so say so in Not
  Verified.
- Overselling cannot be found sequentially. If you cannot generate genuine concurrency, the core scope is
  `BLOCKED` — and that is the finding, not a gap to paper over.
- A marketplace needs **two sellers and two buyers** as a fixture, for the same reason multi-tenant SaaS
  needs two tenants.
- Never place an order that triggers real fulfilment or a real payout. Confirm with the operator which
  environment ships nothing and pays nobody.
- Shipping and tax engines are third parties with their own test modes and their own wrong answers. Prove a
  baseline before filing against them.
- Inventory in shared staging is somebody's test data; moving it breaks their run. Create your own catalog.
