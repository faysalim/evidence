# Domain: mobile app (store-distributed)

Store release and staged rollout, runtime permissions, OS and device fragmentation, offline-first and sync
conflict, background work under power restrictions, upgrade of local data, deep links, accessibility, and
platform policy gates that affect visibility.

## Do the thing

> It runs on the emulator you built it on and the console shows zero crashes on the internal track.
> Install the **store** build of the *previous* release on the oldest supported real device, create data,
> upgrade in place, kill it from the background, revoke a permission, and open your data.
> **"Zero crashes on the internal track" is this domain's HTTP 200.**

## Scope map

| Family | In this domain | Agent | Notes |
|---|---|---|---|
| 1 Acquisition | **store listing and staged rollout** | own | listing claims, screenshots, version, rollout %, halt plan |
| 2 Primary product | the app, **per device × OS version** | own ×2 | the device matrix is the usual recipient of the spare agent |
| 3 Control plane | backend console, if any | N/A or →own | |
| 4 Deployment | release tracks, signing, versionCode monotonicity | →1 | |
| 5 Entitlement | in-app purchase, subscription restore | →2 | restore-after-reinstall is the test people skip |
| 6 Secondary | SDKs, widgets, watch or TV companions | →2 | |
| 7 Telemetry | analytics **and the store data-safety declaration vs observed egress** | own | a docs claim with store-policy consequence |
| 8 Security | exported components, intent injection, deep-link hijack, storage at rest, backup flag, cert pinning | own | |
| 9 Documentation | store listing copy, in-app help, support articles | own | |
| 10 State under fault | offline and sync conflict, process death, Doze, low storage | own | |
| 11 Upgrade | **install previous store build, create data, upgrade** | own | local-schema migration; downgrade |
| 12 Experience | permissions, offline ambiguity, jank, accessibility | own | accessibility here has legal weight |

**Usual set: 1,2×2,7,8,9,10,11,12 own + 4→1, 5→2, 6→2 = 10 agents.**

## Failure catalogue

Permission denied · permission revoked *after* being granted · "only this time" · permanently denied ·
notification permission refused · airplane mode mid-operation · flaky network (high latency, packet loss) ·
process killed from the background and restored · low storage · Doze and App Standby · OEM background
killers · rotation and configuration change · locale change · dark mode · split-screen · upgrade over the
previous store build · downgrade · clock change · interrupted in-app purchase.

## Defect classes to look for by name

**Data loss on upgrade** (local schema migration) · offline ambiguity (did it save? spinner forever?) ·
**sync conflict resolved silently in favour of the wrong device** · ANR and jank above the platform's
vitals thresholds · permission asked at launch with no rationale, so denial rate kills the feature and the
OS stops asking · background job that silently never runs under Doze · deep link landing on the wrong
screen or hijackable by another app · state lost on process death · unlabelled controls under a screen
reader · store-listing claim the app does not deliver.

## Evidence and severity

`evidence-standard.md` → *Mobile builds on a device matrix* in full, plus *Stateful systems under fault*
for sync conflict and process death.

Deliver a **matrix** — device × OS version × check — with every cell `PASS` / `FAIL` / `NOT RUN`, and the
exact invocation recorded per cell. Prove background work by its **side effect**, never by the scheduler's
reported state. Install the store or track artifact, never the debug build.

| Observation | Severity |
|---|---|
| Data loss on upgrade | **critical** |
| Sync conflict silently discarding a device's work | **critical** |
| A policy violation that removes or suppresses the listing | **blocker** — business-side consequence |
| Crash on one OEM or OS version | **major** |
| Missing accessibility | **major**, and legal exposure in several markets |
| ANR or jank above the vitals threshold | **major** — it is a visibility gate, not a feel |

## Experience

**Who the user is:** the end user, and — uniquely to this domain — the **platform reviewer and the vitals
thresholds**, which turn conventions into enforced gates.

**Where it lives:** permission-request timing and rationale; offline state and how sync conflicts are
surfaced; jank on a low-end device; whether an upgrade *feels* like it preserved data; deep-link landing;
store-listing accuracy; accessibility.

**First success is:** the core task completed on a real device, and still there after the process is
killed and the app reopened.

**Do the thing, for experience:**

> On a cheap phone at 200% font scale, turn on airplane mode, do the core task, turn it off, and watch
> what the app tells you happened to your work.

**Defect classes:** permission asked at launch with no rationale · offline ambiguity · ANR and jank above
threshold · unlabelled controls under a screen reader · a notification permission burned by asking too
early.

**Evidence note:** **kind 4 is unusually strong here.** Platform design guidelines, store policy and
vitals thresholds are *enforced*, so a convention violation carries a named cost by construction —
reduced visibility or a rejected release. The general rule that "a convention cited without a cost is a
preference" has its exception in this domain.

## Domain gotchas

- **The emulator is not a device.** Memory, thermal behaviour, OEM modifications and real network
  conditions are where the findings are.
- The debug build has different signing, different obfuscation, debuggable flags and often different
  endpoints. Test the track artifact.
- `versionCode` must increase monotonically; a test upload can burn a number you then cannot reuse.
- Store review and staged rollout are irreversible-ish: halting a rollout is possible, un-publishing a
  bad build's install base is not. Treat any upload as outward-facing and confirm first.
- Battery and background behaviour cannot be measured in a few minutes — these are soak tests, and the
  two-speed verification rule in `iteration-cycles.md` applies.
