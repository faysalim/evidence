# Domain: licensing / entitlement server

Issuing and validation of entitlements, usually as a SaaS control plane plus a self-hosted mode and client
SDKs. This is the origin domain of the skill, so the core playbooks already cover it well — this file is
mostly what the origin engagement still **missed**.

## Do the thing

> The trial endpoint returns 200 and the dashboard shows the licence. Now read the email it was supposed
> to send, activate the key in the real product, roll the *client's* clock back a month, and try to use
> the feature from the CLI instead of the GUI. **A 200 from the issuing endpoint is the one thing a
> customer never sees.**

## Scope map

Every family applies here — this is the shape the cap was calibrated on, and it lands at exactly 11.

| Family | In this domain | Agent | Notes |
|---|---|---|---|
| 1 Acquisition | pricing, funnel, trial request, checkout | own | the funnel *is* the product |
| 2 Primary product | the licensed application itself, per platform | own | SDKs merge in here |
| 3 Control plane | dashboard, tenants, products, editions, signing keys | own | |
| 4 Deployment | self-hosted container, activation, fail-closed | own | |
| 5 Entitlement | the full lifecycle | own | |
| 6 Secondary | client SDKs per language | →2 | |
| 7 Telemetry | phone-home, lead capture | →8 | |
| 8 Security | admin auth, rate limits, enumeration oracles, tamper | own | |
| 9 Documentation | activation variables, API contracts, SDK quickstarts | own | |
| 10 State under fault | concurrent activation, clock movement, key-DB durability | own | |
| 11 Upgrade | self-hosted upgrade with existing keys; key-DB migration | own | |
| 12 Experience | the funnel, and whether every failure path reaches a human | own | |

**Usual set: 11 agents.** At the cap, with no spare — if a fault class needs splitting, something merges.

## Failure catalogue

Everything below was a blind spot of the engagement this skill was distilled from, which is why the list is
specific rather than tidy.

**Set the *client's* clock back a month** after a trial expires · flip one byte of a signed key · present a
revoked key while offline · present a key issued for product A to product B **through the API**, not only
the GUI · race two activations against one remaining seat · deactivate, uninstall, and change hardware, then
look for the seat · revoke on the server and time the connected client · drive every channel — GUI, CLI,
API, SDK — as an unlicensed caller · back up, restore and upgrade the self-hosted server's **own key
database** · poll validation aggressively until the rate limit answers · issue a 30-day trial on the 31st,
expire it at 23:59 across a DST change and a leap day · read the delivery email's raw source and check SPF,
DKIM and DMARC alignment of the sending domain · deliver the same billing webhook twice · take a trial
through to paid.

## Defect classes to look for by name

**Expiry that is advisory** — a trial that resumes after a client clock rollback, which is the oldest attack
in this domain and which a server-clock test cannot see · **tamper tolerated**: validation that fails to
parse rather than *rejecting*, or that accepts a key issued for another product on a channel the GUI does
not use · **seat overrun under concurrency** — two activations, one seat, both succeeding; sequential
retries never find it · a seat that cannot be released at all, so a customer's own hardware change costs
them a licence · revocation that propagates only at renewal, and an offline client that never learns —
undocumented · **entitlement enforced per channel**, so a feature gated in the GUI is reachable from the
CLI, the API or the SDK · **key-database loss locking out every customer at once**, the one `critical` here
that is not revenue-shaped · the vendor fail-closing its own customers when an aggressive client meets a
rate limit · expiry arithmetic at the boundary — timezone, DST, leap day, a 30-day trial issued on the 31st ·
a licence key delivered into spam, which is a lost customer and invisible to both sides · a billing webhook
replayed and granting twice · a trial-to-paid transition that stacks when it should supersede — and, where
the product self-destructs under a trial licence, **a self-destruct that must be proved never to fire on a
paid build.**

## Evidence and severity

`evidence-standard.md` → *HTTP APIs*, *Email*, *Containers*, plus *Stateful systems under fault* for the
concurrent and clock cases.

Severity needs the **blocker amendment**: "the business's control over its own revenue or obligations is
defeated". An entitlement bypass blocks no customer and is still a blocker — the customer-centric rubric
alone has nowhere to put it. Key-DB loss is `critical`. A public endpoint that re-sends mail on every
request is a `major` abuse vector even with no data at risk.

## Experience

**Who the user is:** three. The **prospect** (wanting → working key), the **integrating developer** (SDK
quickstart, validation errors), and the **vendor admin** (who has activated what, and can I tell).

**Where it lives:** the acquisition funnel, which *is* the product here.

**First success is:** a key in hand that validates inside the real product — not a key issued, not an
email sent.

**Do the thing, for experience:**

> Time yourself from "I want to try this" to a key that validates inside the product. Then make the key
> fail five ways — expired, wrong product, tampered, clock rolled back, seat cap hit — and read each
> message as the customer who just paid.

**Defect classes:** a failure path that reaches **no human** (a 403 with no sales or support route — the
origin engagement's own case) · *one message for five causes* ("invalid licence" identical for expired,
wrong product and clock skew, so the customer cannot self-serve and every one becomes a ticket) ·
*entitlement opacity* (a feature silently absent on the free tier rather than visibly gated with "requires
Pro", so the user concludes the product lacks it) · no vendor-side view of consumed seats without the
database.

**Evidence note:** the blocked goal dominates — the goal is "have a working key". The measurement is
funnel time and **exits from the product** (to email, to a dashboard, to support).

## Domain gotchas

- Trials are usually idempotent per email per product, so **you get one shot per address.** Plan the test
  matrix before burning addresses.
- Testing "does every failure path reach a human" means submitting real enquiries to a real sales team.
  Mark each as a test in the free-text field, warn the operator first, and ledger it.
- Production trial rows and issued keys are production data. They go in the cleanup ledger with who can
  remove them.
- Attack uniqueness with the *neighbours* of the input — case, whitespace, `+tag` subaddressing — not the
  input itself.
