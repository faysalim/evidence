# Domain: feature flags / experimentation

A flag service decides what every other system does. Its failure mode is not downtime — it is
**serving the wrong variant confidently**, which looks exactly like normal operation and corrupts
every experiment reading from it.

## Do the thing

> Create a flag with a 50/50 split, targeted at one attribute. Call the SDK a thousand times for the
> same user id and confirm you get the same answer every time. Then change the flag and confirm the
> change arrives — and time it. Then **kill the flag service** and call the SDK again.
> **The default-when-unreachable is this domain's real behaviour**, and it is the one nobody tests:
> a product that silently serves "off" for every user during a flag-service outage has just shipped
> a global feature rollback that nobody authorised and no alert noticed.

## Scope map

| Family | In this domain | Agent | Notes |
|---|---|---|---|
| 1 Acquisition | docs, SDK install per language | N/A | |
| 2 Primary product | flag evaluation through each SDK | own ×2 | split: server SDK vs client/browser SDK — they have different trust models |
| 3 Control plane | flag CRUD, targeting rules, rollout percentages, environments | own | |
| 4 Deployment | relay/proxy, local evaluation, streaming vs polling | own | |
| 5 Entitlement | seats, MAU or flag-count limits | →3 | |
| 6 Secondary | audit log, approval workflow, scheduled rollouts | own | |
| 7 Telemetry | exposure events — the input to every experiment result | own | wrong exposures invalidate the analysis silently |
| 8 Security | who may change a production flag; client-side key exposure | own | a client key that can read every flag leaks the roadmap |
| 9 Documentation | **the default-when-unreachable claim, per SDK** | own | the single most consequential sentence in the docs |
| 10 State under fault | service unreachable, stale cache, mid-rollout change, clock skew | own ×2 | split: unreachable/stale vs rule-change propagation |
| 11 Upgrade | SDK version skew, rule-schema change, flag archival | own | old SDKs evaluating new rule types is the trap |
| 12 Experience | can an operator tell which variant a given user is getting, and why | lead | |

**Usual set: 2×2,3,4,6,7,8,9,10×2,11 own + 5→3, 12→lead = 11 agents.**

## Failure catalogue

- **Default-on-unreachable is undocumented or wrong per SDK.** The server SDK falls back to the last
  cached value; the browser SDK falls back to the code default. Same flag, two behaviours, one
  sentence in the docs.
- **Evaluation is not deterministic for the same key.** Bucketing that depends on anything but a
  stable hash of (flag, key) reassigns users between calls, which destroys both the experience and
  the experiment.
- **Exposure events fire when the flag is evaluated, not when the user saw it.** Every result built
  on that denominator is wrong, and `/evidence:analytics` will read it as real.
- **Targeting-rule order changes meaning.** Overlapping rules evaluated in a different order on a
  different SDK version give different variants for the same user.
- **A percentage rollout that is not sticky across a deploy.** Users flip variant when the pod
  restarts, which users experience as the product breaking intermittently.
- **Archived or deleted flag still referenced in code.** Now serving the code default forever, with
  nobody watching.
- **Client-side keys expose unreleased flag names.** The roadmap leaks through the bundle.
- **Clock skew on scheduled rollouts.** A rollout that starts early in one region.
- **Flag-change audit missing the before value.** You know who changed it and not what it was, so a
  bad rollout cannot be reversed from the record.

## Defect classes to look for by name

| Class | What makes it this class |
|---|---|
| **Wrong variant served** | The user got a variant their targeting says they should not — the core defect |
| **Non-deterministic bucketing** | Same key, different answers across calls or instances |
| **Fallback divergence** | The documented default-on-unreachable is not what the SDK does |
| **Exposure mismeasurement** | Exposure events do not correspond to what a user saw |
| **Propagation lag beyond the stated bound** | A rule change that takes longer than documented to reach evaluation |
| **Unauthorised production change** | Someone changed a production flag who should not have, or without record |

## Evidence and severity

**A wrong variant inherits the severity of the feature it gates.** This is the rule that matters
here and it is the one most often got wrong: a flag defect is treated as `minor` because the flag
service is fine, when the flag was gating a payment path. Grade by consequence
(`shared/vocabulary.md`), not by the component that failed.

Evidence for this domain is a **pair**: the targeting rule as configured, and the variant actually
served for a named key, captured from the SDK rather than from the control-plane preview. The
control plane's own preview is the product reporting on itself (`shared/principles.md` §3) — it
evaluates the rule with its own engine, not the SDK's, and the two disagreeing is a real and common
defect.

For an experiment result, the denominator is the **exposure count, not the assignment count.**
Report both; they differ, and the difference is usually the finding.

## Experience

The operator question this domain lives or dies on: **"why is this user getting that variant?"**
A flag service that cannot answer it for a named user id, with the rule that decided it, turns every
support ticket into an investigation. Check for a per-user evaluation explainer, and check it agrees
with the SDK.

Second: can someone tell, from the product, which flags are currently affecting them? A long-lived
flag nobody can enumerate becomes permanent undocumented behaviour.

Time to first success here is **create a flag and see it change behaviour** — if that takes more
than a few minutes through the real SDK, the product has an onboarding problem that no amount of
docs fixes.

## Domain gotchas

- **The control plane's preview and the SDK are two evaluation engines.** Test the SDK.
- **Local-evaluation mode changes the fault model entirely**: the SDK holds a rule set and evaluates
  offline, so propagation delay and stale rules replace network failure as the risk.
- **Never test a flag by reading it back from the control plane.** That is reading your own write.
- **Clean up flags you create**, in the cleanup ledger from minute one: a test flag left in a
  production environment is a live change to the product.
- **Experiment analysis belongs to `/evidence:analytics`**, and it inherits this domain's
  denominators. If exposures are wrong, say so there before anyone reads a result.
