# Domain: identity, authentication and SSO

Sign-up, sign-in, MFA, sessions and tokens, federation with external identity providers, password reset,
and the account-recovery path that is simultaneously the least-tested flow and the real attack surface.

## Do the thing

> The login page works and the token validates. Now sign in on two devices, change the password from one,
> and check whether the other session is still alive. Then revoke a user and time how long their token
> keeps working. **A token that validates is this domain's HTTP 200 — the only interesting question is
> whether it should still validate.**

## Scope map

| Family | In this domain | Agent | Notes |
|---|---|---|---|
| 1 Acquisition | signup funnel, plan selection | →2 | |
| 2 Primary product | sign-up, sign-in, sign-out, reset, MFA enrolment | own | |
| 3 Control plane | admin console, users, roles, orgs, **audit log** | own | |
| 4 Deployment | self-hosted IdP, config, key material | own | `N/A` if SaaS only |
| 5 Entitlement | seats, org membership, plan → feature | →3 | |
| 6 Secondary | SDKs, mobile, **OIDC / SAML federation** | own | |
| 7 Telemetry | what the auth logs record, PII in them | →8 | |
| 8 Security | the core | own ×2 | split: session & token lifecycle vs enumeration, brute force, injection |
| 9 Documentation | integration guide, claim mapping, token lifetimes | own | lifetimes are behavioural guarantees |
| 10 State under fault | session store down, clock skew, revocation propagation | own | |
| 11 Upgrade | signing-key rotation, session-format change, password-hash migration | own | |
| 12 Experience | recovery, MFA lockout, expiry mid-work | own | |

**Usual set: 2,3,4,6,8×2,9,10,11,12 own + 1→2, 5→3, 7→8 = 11 agents** (10 when there is no self-hosted
deployment). This domain sits at the cap: if federation covers more than one external IdP, that is the
first thing to hand back to the operator as a budget request.

## Failure catalogue

Password changed from another session · logout-everywhere invoked · MFA device lost · a reset link used
twice · a reset link used after the email address changed · session store unavailable for 60s · signing key
rotated with tokens in flight · clock skew ±10 minutes against `exp` and `nbf` · concurrent logins from
two devices · account locked, then unlocked · a SAML assertion replayed · an assertion with one attribute
altered · IdP-initiated vs SP-initiated flow · a user deleted at the external IdP while their session is
live · 10,000 login attempts · an org admin demoted mid-session · a tenant inferred from a claim the
client supplied.

## Defect classes to look for by name

**Session not invalidated on password change, or "log out everywhere" that does not** · revocation that
only takes effect at natural token expiry · a reset token that is reusable, long-lived, or not bound to
the current email · **MFA bypassed through a secondary path** (reset, SDK, legacy endpoint, remember-this-
device) · account enumeration through different error text, different status code, or response timing · a
role change not enforced until re-login, so privilege is held too long · SAML signature unverified, or
verified on the envelope rather than the assertion · JWT algorithm confusion, or an unvalidated `kid` ·
tenant or role read from a client-supplied claim · audit log missing the sensitive events, or missing the
actor on them.

## Evidence and severity

The oracle is **your own ledger of sessions and tokens** — each one you created, each one you revoked, and
when. Grade the product against that ledger, never against what the admin console displays. Revocation
findings have a latency: record the time between the revoke and the successful request that followed it.

`evidence-standard.md` → *Authorization and permission matrices*, *Stateful systems under fault*
(revocation propagation, store outage), *Background and scheduled work* (session reaping, lockout expiry).

| Observation | Severity |
|---|---|
| Session survives a password change or an explicit revoke | **critical** |
| MFA bypassable by any path | **critical** |
| Tenant or role taken from a client-supplied claim | **critical** |
| Reset token reusable or not bound to the current email | **critical** |
| Role change not enforced until re-login | **blocker** |
| Account enumeration | **major** |
| Audit log missing the actor on a sensitive event | **major**, **blocker** where compliance is claimed |

## Experience

**Who the user is:** someone locked out of their own account, and the IT administrator wiring up the
integration — two users with opposite needs.

**Where it lives:** the recovery path, which is the most-used and least-tested flow in the product; MFA
enrolment and device loss; error text that must not leak and must still help; and session expiry landing
in the middle of unsaved work.

**First success is:** a new user signs in with MFA, loses the device, and recovers the account unaided.

**Do the thing, for experience:**

> Enrol MFA, then throw the device away. Recover the account using only what the product offers.

**Defect classes:** expiry that discards unsaved work · "something went wrong" on the one screen where the
user cannot retry · MFA enrolment with no backup codes · recovery that requires support with no route to
support · a logout that does not log out.

**Evidence note:** this domain has a genuine tension — a helpful error message and a non-enumerable one
pull in opposite directions. Report the harm *and* the constraint, and route it as a `DECIDE` with options
rather than a bug, unless the product already claims one side of it.

## Domain gotchas

- Never test with a real personal or work account you depend on; create disposable ones and ledger them. A
  lockout test on your own account ends the run.
- Brute-force and enumeration tests trip real WAF and fraud rules, and can block your source IP for hours.
  Warn the operator first, and ledger it.
- Federation testing needs a second IdP. A dev tenant of a real one is the usual route, and **its own
  misconfiguration will masquerade as a product bug** — prove the baseline flow works before filing
  anything.
- Token lifetimes mean some findings need a wait. Use the short form with a hard cutoff and run the long
  one as a background job (`iteration-cycles.md`, two-speed verification).
- Password-hash migration is not reversible. Test it on a copy, and never on a store you do not own.
