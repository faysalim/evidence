# Domain: embedded / firmware and devices

Field-installed hardware with firmware updates, no keyboard, often no screen, and a recovery story that
has to work in someone's basement with a quickstart card.

## Do the thing

> The OTA reported 100% and the device rebooted into the new version. Now pull the power at 60% and boot
> it — then hand it to someone holding only the card that shipped in the box. **"Update complete" is this
> domain's HTTP 200, and the only interesting question is what happens when it is not.**

## Scope map

| Family | In this domain | Agent | Notes |
|---|---|---|---|
| 1 Acquisition | product page, spec claims | N/A | |
| 2 Primary product | the device, per hardware revision | own | revisions diverge more than OS versions do |
| 3 Control plane | fleet management, OTA campaign console | own (if one exists) | |
| 4 Deployment | provisioning, pairing, factory flashing | own | |
| 5 Entitlement | if features are licensed per device | →4 | |
| 6 Secondary | companion app, local API, cloud bridge | own | |
| 7 Telemetry | what the device phones home, and whether a customer can see it | →8 | |
| 8 Security | debug ports left open, firmware signature verification, secrets in the image, local network surface | own | signature verification is the one that matters most |
| 9 Documentation | quickstart card, recovery procedure, spec sheet | own | the card is the entire support channel |
| 10 State under fault | **OTA under power loss**, A/B slots, watchdog, soak | own | the core |
| 11 Upgrade | N-2 → N, rollback, settings and pairing survival | own | |
| 12 Experience | state legibility without a screen | lead | |

**Usual set: 2,3,4,6,8,9,10,11 own + 5→4, 7→8, 12→lead = 8 agents.**

## Failure catalogue

Power pulled at 10 / 50 / 90% of an OTA · power pulled during the first boot after an OTA · network lost
mid-download · a corrupted or truncated image · an image signed with the wrong key · brownout and
repeated power cycling · watchdog triggered · flash wear and a full filesystem · clock lost on power
cycle · a downgrade attempt · **30-day soak** for memory leaks and handle exhaustion · factory reset with
a pairing active.

## Defect classes to look for by name

Bricking on interrupted OTA (A/B slots absent or rollback not actually wired) · firmware signature not
verified, or verified only on the happy path · **indistinguishable states** (one blink pattern for
"updating" and "failed") · settings or pairing lost on upgrade · watchdog masking a crash loop so the
device appears alive · slow memory leak surfacing only after weeks · recovery procedure requiring tooling
the field does not have · debug interface shipped enabled.

## Evidence and severity

`evidence-standard.md` → *Migrations, upgrades and restores* (the OTA is an upgrade with data in it), plus
*Stateful systems under fault* for the power-loss schedule. Record the exact interruption point as a
percentage *and* as the phase (download, verify, write, swap, first boot) — the phase is what determines
the bug.

The long soak is the purest case of the two-speed verification rule in `iteration-cycles.md`: a short form
with a hard cutoff and a stall detector gates progress, and the 30-day run is a background job with its
own status, never an agent waiting.

| Observation | Severity |
|---|---|
| Interrupted OTA bricks the device | **critical** — unrecoverable in the field, and a truck roll per unit |
| Firmware signature not verified | **critical** |
| Settings or pairing lost on upgrade | **blocker** |
| Indistinguishable failure and progress states | **blocker** — the user cannot tell a working device from a dead one |
| Leak surfacing after weeks | **major** |

## Experience

**Who the user is:** the field installer, and an end user with an LED and a card.

**Where it lives:** provisioning (pairing, network setup); update progress and "do not power off"
communication; failure indication **without a screen**; whether the recovery procedure is reachable from
the device plus whatever shipped in the box; and field log retrieval.

**First success is:** the device provisioned, paired, and performing its core function once — then still
doing so after a power cycle.

**Do the thing, for experience:**

> Pull the power during the OTA at 60%, then hand the device to someone with only the quickstart card: can
> they tell it is recoverable, and recover it?

**Defect classes:** indistinguishable states · no indication of duration or whether interruption is safe ·
recovery needing tooling the field does not have · a quickstart card that assumes a phone app the
installer has not got.

**Evidence note:** this domain needs one measurement the others do not — **state legibility**. Enumerate
the states the device can actually be in, against the distinguishable signals it can emit. A many-to-one
mapping is the finding, and it is a count rather than a taste. It generalises: a health enum with three
values for twelve conditions is the same defect in a cluster.

## Domain gotchas

- **Interrupting an OTA can brick hardware you do not own.** Confirm with the operator which units are
  expendable, and ledger them — this is the one domain where a test consumes physical inventory.
- Hardware revisions diverge silently. Record the revision on every finding; a bug on rev B may not exist
  on rev C.
- Serial console output is often the only diagnostic channel, and it is frequently disabled in production
  images — establish early whether you can see anything at all, or the whole scope is `BLOCKED`.
- Timing-dependent power-loss bugs need many repetitions: report the rate, per the nondeterminism rule.
