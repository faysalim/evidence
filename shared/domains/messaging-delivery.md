# Domain: email, SMS and push delivery

Templates, sending, deliverability, bounces and complaints, suppression, unsubscribe, and the reputation of
a sending domain that is usually shared with other people.

## Do the thing

> The API returned `202 Accepted` and the dashboard says `delivered`. Open the message in a real mailbox at
> three different providers, read the headers for SPF, DKIM and DMARC alignment, and then unsubscribe and
> send again. **`202 Accepted` is this domain's HTTP 200 — and `delivered` means a receiving server took
> it, not that a human will ever see it.**

## Scope map

| Family | In this domain | Agent | Notes |
|---|---|---|---|
| 1 Acquisition | deliverability and rate claims | →9 | |
| 2 Primary product | the send path | own ×2 | split by channel: email vs SMS/push — they share almost nothing |
| 3 Control plane | templates, campaigns and journeys, suppression list, logs | own | |
| 4 Deployment | SaaS | N/A | |
| 5 Entitlement | send quotas and rate caps | →3 | |
| 6 Secondary | SDKs, event webhooks (delivered / bounce / complaint), inbound parsing | own | |
| 7 Telemetry | open and click tracking | own | a tracking pixel is a privacy claim, not instrumentation |
| 8 Security | sending-domain authentication, spoofing, **unauthorized send**, link wrapping | own | |
| 9 Documentation | retry, bounce and suppression semantics; **compliance claims** | own | CAN-SPAM, CASL and GDPR obligations are documented claims |
| 10 State under fault | retry, receiver throttling, bounce handling, provider outage, duplicate send | own | |
| 11 Upgrade | template versioning mid-campaign, sending-domain migration, IP warmup | own | |
| 12 Experience | the recipient, and the operator diagnosing non-delivery | own | |

**Usual set: 2×2,3,6,7,8,9,10,11,12 own + 1→9, 4 N/A, 5→3 = 10 agents.**

## Failure catalogue

A send to a hard-bounced address, and to a complaint address · a send after an unsubscribe · the same
message twice with the same idempotency key · a template with a missing variable, a null, a very long
value, right-to-left text, emoji, and an unescaped `<script>` · a receiving server that 4xx-throttles then
accepts · one that times out · a cold sending IP · a DKIM key rotated mid-flight · a message over the size
limit, and one with a large attachment · an SMS over 160 characters and one containing unicode (segment
counting) · an SMS to a landline, a disconnected number, and across a country code · a push to an expired
token and to an uninstalled app · a timezone-aware or quiet-hours send · a 100,000-recipient campaign
paused mid-send.

## Defect classes to look for by name

**Suppression not honoured** — a send to a hard bounce or an unsubscribe, which is a legal violation and a
reputation event rather than a bug · **an unsubscribe that does not unsubscribe**, or that applies to one
list where the claim was global · SPF, DKIM or DMARC misalignment, so mail is filtered while the dashboard
reports success · **template injection** — recipient-supplied data rendered unescaped into HTML or into a
link · a missing variable rendering as `{{first_name}}` or `undefined` to a real customer · duplicate send
on retry · **bounce misclassification**, where a soft bounce is treated as hard and a good address is
suppressed permanently · **SMS segment miscount**, so a message is truncated or charged twice · a push to
an expired token counted as delivered · quiet-hours and timezone errors — the 3am message · link wrapping
that breaks the link or trips phishing filters · a tracking pixel leaking recipient identity to a third
party · a plain-text alternative missing or disagreeing with the HTML.

## Evidence and severity

**Real mailboxes at three or more providers are the harness.** The dashboard is the component under test
reporting on itself, and `delivered` is a statement about the receiving MTA, not the inbox. Read the raw
headers: SPF result, DKIM verification, DMARC alignment, and whatever spam scoring the receiver added. SMS
needs a real handset or a per-country test number; push needs a real device.

Record per finding: message id, sending domain and IP, receiving provider, the raw headers, and the body as
the client actually rendered it.

`evidence-standard.md` → *Email* in full, plus *Stateful systems under fault* for retry and suppression and
*Background and scheduled work* for campaigns and scheduled sends. **The silence multiplier applies harder
here than anywhere else in the skill:** a delivery failure is invisible to the sender *and* the recipient,
because nobody reports a message they never received.

| Observation | Severity |
|---|---|
| A send to a suppressed, unsubscribed or hard-bounced address | **critical** — legal, reputational, and not undoable |
| Template injection into a message or a link | **critical** |
| Unsubscribe not honoured | **critical** |
| DMARC misalignment filtering legitimate mail | **blocker** |
| Duplicate send | **blocker** |
| Bounce misclassification suppressing good addresses | **blocker** |
| SMS truncation or double-charging | **blocker** |
| A message delivered at 3am by a timezone error | **major** |

## Experience

**Who the user is:** the recipient, who did not ask to be here — and the operator who has to answer "did
they get it, and if not, why".

**Where it lives:** the message as a real client renders it (dark mode, images blocked, narrow screen,
plain-text fallback); whether the sender is recognisable; one-click unsubscribe; and the operator's ability
to diagnose a single non-delivery.

**First success is:** a transactional message reaches the inbox of a fresh mailbox at a major provider,
renders correctly **with images blocked**, and its unsubscribe works.

**Do the thing, for experience:**

> Open it on a phone, in dark mode, with images blocked. Then unsubscribe, and send again.

**Defect classes:** a message illegible with images off or in dark mode · an unsubscribe that requires a
login · "do not reply to this email" with no route to a human · an operator log that says `delivered` and
nothing else, so non-delivery cannot be diagnosed · a sender name the recipient does not recognise.

**Evidence note:** diagnosability is directly measurable here as **time to answer "why did this one not
arrive"** from the product's own logs. A product that can only say `delivered` has a diagnosability defect
whose consequence is a support ticket nobody can ever close.

## Domain gotchas

- **Never send to an address you do not own.** A test blast to sample or scraped addresses is a real spam
  incident with a permanent reputation cost. Use your own mailboxes and the providers' seed addresses.
- **Sending reputation is shared infrastructure.** A careless test degrades deliverability for every other
  sender on that IP pool, the customer included. Warn the operator and ledger the volume.
- Deliverability varies by provider and by day. A single-provider result is a data point, not a finding —
  always report which provider.
- IP warmup means a new sending domain legitimately performs worse at first. Do not file that as a defect.
- **Suppression lists are usually irreversible by design**, so adding a test address can block it forever.
  Use addresses you can afford to lose.
- Inbound and reply testing needs a mailbox you control with a catch-all, arranged before the scope starts.
