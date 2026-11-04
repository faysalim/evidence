# Domain: secrets management and PKI

Secret storage, dynamic credentials, encryption keys, and certificate issuance and renewal. A product with
two failure modes: an outage at midnight, or a quiet loss of confidentiality nobody notices.

## Do the thing

> The secret reads back and the certificate is valid. Now **rotate** — the signing key, then the root, then
> the leaf — while clients are connected. Let a short-lived credential expire mid-request, and present a
> revoked certificate to see whether anything actually checks. **`200 {"value":"…"}` is this domain's HTTP
> 200; the product is what happens at rotation, expiry and revocation.**

## Scope map

| Family | In this domain | Agent | Notes |
|---|---|---|---|
| 1 Acquisition | docs | →9 | |
| 2 Primary product | read and write, dynamic credentials, encrypt and decrypt | own | |
| 3 Control plane | policies, roles, namespaces, **the audit log** | own | |
| 4 Deployment | HA, seal and unseal, storage backend, HSM | own | |
| 5 Entitlement | licensing | →4 | |
| 6 Secondary | agents, sidecars, CSI drivers, client libraries, ACME clients | own | the renewal client is where renewal actually fails |
| 7 Telemetry | what the audit log records — and what it must never record | →3 | |
| 8 Security | the entire point | own ×2 | split: policy and authorization vs key-material handling and escalation |
| 9 Documentation | rotation procedures, lease semantics, the unseal and recovery runbook | own | |
| 10 State under fault | **rotation and expiry**, storage backend down, clock skew, revocation propagation | own | |
| 11 Upgrade | key-format migration, root rollover, upgrade with sealed storage | own | |
| 12 Experience | the 3am expiry | own | |

**Usual set: 2,3,4,6,8×2,9,10,11,12 own + 1→9, 5→4, 7→3 = 10 agents.**

## Failure catalogue

Rotate a signing key with credentials in flight · **rotate the root CA** — the one nobody practises · let a
lease expire mid-request · renew at 1%, 50% and 99% of lifetime · a certificate that expired one second
ago, and one not yet valid · clock skew of ±1 hour on the client and on the server · present a revoked
certificate · make the storage backend unavailable · restart sealed, with a full unseal quorum and with one
key short · make the HSM unavailable · apply a deny policy while a session holds a cached token · a wildcard
and a case difference in a policy path · delete a secret while a consumer holds a lease · serve a chain
missing its intermediate · two clients renewing the same certificate concurrently · a key format from ten
years ago.

## Defect classes to look for by name

**Rotation that breaks live clients** because the old key was retired before the new one propagated — the
overlap window *is* the product · **a renewal that silently never runs**, discovered at expiry, and its
sibling, a renewal that runs and never installs or reloads · **revocation not actually checked**, so a
revoked credential keeps working · a secret or key in plaintext in a log, an audit entry, an error message
or a crash dump · an audit log that records the secret's **value**, or that omits reads · a policy that
denies in the console and allows via path traversal or a case difference · **unseal or recovery material
stored with the thing it unseals** · a lease that is not enforced, so a credential outlives its TTL · a
dynamic credential never revoked at lease end, accumulating in the target system · encryption without
authentication, so ciphertext is malleable · a key version still decryptable after it was reported
destroyed.

## Evidence and severity

The oracle is **the credential's own lifecycle, timed**. Every finding carries three timestamps: issue,
rotation or revocation, and the request that should have failed and did not. A revocation finding without
those three is not reproducible and should not be filed.

For certificates, read the chain **as the client's TLS stack validates it**, never as the product's
dashboard describes it. Make expiry testable by issuing deliberately short-lived material — a 60-second
certificate rather than a year's wait.

`evidence-standard.md` → *Authorization and permission matrices* (per policy path, including traversal and
case variants), *Stateful systems under fault*, *Background and scheduled work* — renewal is scheduled work
and is proved by its side effect: the new certificate installed **and being served**.

| Observation | Severity |
|---|---|
| A secret or key in a log, anywhere | **critical** |
| Revocation not enforced | **critical** |
| Policy bypass by path or case | **critical** |
| Unseal or recovery material stored with the sealed data | **critical** |
| Rotation breaking live clients | **blocker** — an outage, in the operation the product exists to make safe |
| A renewal that never runs, or runs without installing | **blocker** |
| A lease not enforced, or credentials accumulating | **blocker** |
| An audit log that omits reads | **blocker** |

## Experience

**Who the user is:** the engineer woken by an expiry they did not know existed, and the one performing a
rotation for the first time from a document.

**Where it lives:** whether anything warns before an expiry, with how much notice, and to whom; whether the
rotation runbook is executable on the first attempt; whether an error distinguishes "denied by policy" from
"does not exist" — and whether it should; and whether the audit log can answer "who read this".

**First success is:** a client authenticating with a dynamically issued credential, and continuing to work
across one full rotation of it.

**Do the thing, for experience:**

> Perform a signing-key or root rotation from the documentation alone, on a system you did not set up, with
> a client connected. Count the outages.

**Defect classes:** no advance warning of expiry, or a warning sent to a mailbox nobody owns any more · a
runbook that assumes state the operator cannot see · "permission denied" indistinguishable from "not found"
at the moment the operator needs to know which · an audit log that cannot answer who read a secret and when.

**Evidence note:** **time-to-expiry visibility** is this domain's measurement. Enumerate every credential,
key and certificate the system holds, against those whose remaining lifetime is visible somewhere a human
actually looks. The gap is a count, not a taste, and it is the whole of this domain's experience failure.

## Domain gotchas

- **Generate test key material; never handle production secrets.** The skill's no-secrets rule applies to
  the test as well as the report — reading a production secret "to check it works" *is* the breach.
- Never rotate or revoke in an environment you do not own: rotation is destructive to every client of it.
- Prefer **short lifetimes over clock skew** where you can. Skewing the clock also changes the product's own
  behaviour, which muddies the finding.
- HSM and cloud-KMS backends behave differently from the software backend. A finding is scoped to the
  backend you used — record it.
- A failed unseal can leave a system down with no route back without the key quorum. Establish who holds the
  keys **before** you restart anything.
- Audit logs are themselves sensitive. Quote structure, never contents, and never paste one into a report.
