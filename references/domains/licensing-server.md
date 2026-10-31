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

## What the origin engagement still missed

- **Client clock rollback.** Set the *client's* clock back a month after a trial expires. If the trial
  resumes, every expiry is advisory. The server-clock test does not cover this, and it is the oldest
  licensing attack there is.
- **Tamper and replay.** Flip one byte of a signed key — validation must *reject*, not merely fail to
  parse. Present a revoked key offline. Present a key issued for product A to product B **through the
  API**, not only the GUI.
- **Concurrent activation against the seat cap.** Two activations racing one seat; both succeeding is the
  finding. Sequential "try it twice" does not find this.
- **Seat release.** Deactivate, uninstall, change hardware: is the seat returned? Seats consumed by your
  own testing go in the ledger — and whether they *can* be released is itself a test.
- **Revocation propagation.** Revoke on the server; time until a connected client stops. An offline client
  never learns — is that documented?
- **Entitlement enforced on every channel.** A feature gated in the GUI but reachable from the CLI, the
  API or the SDK is a bypass. Drive each channel as an unlicensed caller.
- **Fail-closed meets durability.** The self-hosted server's own key database: back it up, restore it,
  upgrade it with keys in place. Losing the key DB locks out every customer at once — the only `critical`
  here that is not revenue-shaped.
- **Validation under load.** A client that polls validation aggressively, plus a rate limit, equals the
  vendor fail-closing its own customers. Find the limit, then ask what the client does when it hits it.
- **Expiry at the boundary.** 23:59 in which timezone; DST; leap day; a 30-day trial issued on the 31st.
- **Email deliverability.** Reading the raw source is already in the standard; SPF, DKIM and DMARC
  alignment of the sending domain is not. A licence key in spam is a lost customer.
- **Billing webhooks replayed.** A processor webhook delivered twice must not grant twice.
- **Trial → paid transition.** Supersede or stack? And if the product self-destructs under a trial
  licence, prove the self-destruct **never fires on a paid build** — the time bomb is a test, not only a
  hazard.

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
