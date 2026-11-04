# Domain: API / developer platform

A public or partner HTTP or GraphQL API with keys, scopes, rate limits, webhooks, SDKs in several
languages, and a version policy that other people's production systems are built on.

## Do the thing

> Every endpoint returns `200 OK` on the happy path and the status page is green. Generate a client from
> the **published** spec, call every endpoint in it with the documented required fields *only*, send one
> write twice with the same idempotency key, and fetch an object by an id belonging to another account.
> **A 200 on the happy path is this domain's HTTP 200 — literally — and the spec is a set of claims, not
> documentation.**

## Scope map

| Family | In this domain | Agent | Notes |
|---|---|---|---|
| 1 Acquisition | docs site, pricing, self-serve key signup | own | time-to-first-call starts here |
| 2 Primary product | the API itself | own | |
| 3 Control plane | developer portal, key and scope management, usage dashboard | own | |
| 4 Deployment | SaaS | N/A | `own` if it is also self-hostable |
| 5 Entitlement | plan limits, rate limits, quota enforcement, metering | own | metering is billing input, so it is correctness not telemetry |
| 6 Secondary | SDK per language, CLI, webhook receiver | own | the spare agent goes here when there are more than two SDKs |
| 7 Telemetry | usage records | →5 | |
| 8 Security | authn per endpoint, **object-level authorization**, key scopes, CORS | own | |
| 9 Documentation | **the spec is the product** — every field is a claim | own | |
| 10 State under fault | idempotency, partial writes, async jobs, webhook delivery | own | |
| 11 Upgrade | version deprecation, breaking-change policy, SDK majors | own | |
| 12 Experience | error bodies, developer experience | own | |

**Usual set: 1,2,3,5,6,8,9,10,11,12 own + 4 N/A, 7→5 = 10 agents.**

## Failure catalogue

A request at the rate limit, and one over · the same write twice with the same idempotency key · the same
key with a *different* body · a key revoked mid-session · a token with the wrong scope · a pagination
cursor used after the underlying row is deleted, and during a concurrent insert · a body at the size limit
and one byte over · unicode, empty string and null in every string field · a documented-optional field
omitted · an undocumented extra field sent · clock skew on a signed request · a webhook endpoint that
returns 500, then times out, then succeeds · a webhook delivered twice and out of order · an async job
polled after its record expires · concurrent `PATCH` on one resource · a compressed body that expands
enormously.

- **Published performance claim under saturation** (scope 8b): reproduce the claimed number on a
  stated rig, then measure the degradation curve at 10x and 100x that load. At saturation, establish
  whether it sheds load, queues unboundedly or loses data — queueing to out-of-memory is a
  durability defect wearing a performance costume.

## Defect classes to look for by name

**Object-level authorization missing** — another account's object readable by its id · idempotency honoured
at the gateway but not at the write · pagination that loses or duplicates rows under concurrent insert · a
documented field the API silently ignores · a response field the spec does not document, which clients
bind to and you then break · error bodies whose *shape* differs per endpoint · a rate limit that counts
differently than documented, or returns `200` past the limit · webhooks with no signature or no replay
protection · a breaking change shipped inside a stable version · SDK and API disagreeing on a default · a
`500` where the contract promises `4xx`, so every client retries a permanent failure.

## Evidence and severity

Generate the client from the published spec: that makes the docs executable and forward coverage falls out
for free. Deliver two numbers with denominators — **spec conformance** (endpoints × documented fields
exercised / total) and the **authorization matrix** (role × endpoint × object owner). Record the exact
request per finding: method, path, headers with secrets replaced by their role, body, and the raw response.

`evidence-standard.md` → *Authorization and permission matrices*, *Stateful systems under fault* (for
idempotency and concurrent writes), *Background and scheduled work* (async jobs, webhook retries).

| Observation | Severity |
|---|---|
| Another account's data readable by object id | **critical** |
| Idempotency not honoured on a billable or money-moving write | **critical** |
| Pagination losing rows | **critical** |
| Undocumented breaking change in a stable version | **blocker** — it breaks other people's production |
| Metering wrong | **blocker** — it is the invoice |
| Error-body shape inconsistent across endpoints | **major** |
| Rate-limit headers wrong or absent | **major** |

## Experience

**Who the user is:** an integrating developer in a different codebase, at midnight, reading your error
body — plus their end user, who never sees you.

**Where it lives:** time-to-first-successful-call from a cold signup; whether an error body names the
**field** and the fix; agreement between spec, SDK and guide; the changelog; request ids for support.

**First success is:** a developer who has never seen the product makes one authenticated write and reads
it back, using only the published docs.

**Do the thing, for experience:**

> Hand the published quickstart to someone who has never seen the product and time them to their first
> successful authenticated write. Then make them trigger an error and see whether the body names the field.

**Defect classes:** "invalid request" with no field named · a quickstart that assumes a key already exists ·
`401` where `403` is meant, so a scope problem looks like a bad key · no sandbox or test mode · no request
id, so support cannot correlate anything.

**Evidence note:** time-to-first-call is this domain's first-run baseline. The error-message audit has an
unusually hard pass criterion here — the body must name the field and the fix, because the reader cannot
see your code and is not going to read it.

## Domain gotchas

- If the spec is **generated from the code** it cannot contradict the code, so forward coverage proves
  little. Reverse-enumerate from the router and from the SDK's surface instead, and say which you did.
- Your key almost certainly has broader scopes than a customer's. Get a least-privilege key or every
  authorization finding is invisible to you.
- Rate-limit and quota tests consume a shared allowance and can throttle the rest of the run. Ledger them.
- Webhook testing needs a publicly reachable URL; a tunnel changes the timing, which changes retry
  behaviour. Record which you used.
- A gateway, CDN or WAF in front of the service may answer before the product does. Establish which layer
  produced a response before filing it as a product defect.
