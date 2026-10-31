# Domain: scheduling, calendar and booking

Availability, recurrence, reservations and reminders — the domain where almost every defect is arithmetic
on time, and where the worst one lets two people take the same slot.

## Do the thing

> The booking confirms and the calendar shows the slot. Now have two people book the last slot at the same
> instant, and move the host to a timezone that changes to summer time on a different date from the guest's.
> **A confirmation screen is this domain's HTTP 200 — the oracles are an independent date library and a
> count of how many bookings exist for one slot.**

## Scope map

| Family | In this domain | Agent | Notes |
|---|---|---|---|
| 1 Acquisition | the public booking page | own | it is the product for most visitors |
| 2 Primary product | availability and booking | own ×2 | split: availability computation vs the reservation write |
| 3 Control plane | calendars, resources, staff, rules, overrides | own | |
| 4 Deployment | SaaS | N/A | |
| 5 Entitlement | plan limits on resources or bookings | →3 | |
| 6 Secondary | calendar integrations, video links, payment at booking | own | |
| 7 Telemetry | generic | →8 | |
| 8 Security | whose calendar is visible, booking on another's behalf, detail leakage on the public page | own | |
| 9 Documentation | **timezone and recurrence behaviour**, cancellation policy | own | these are behavioural guarantees |
| 10 State under fault | **double-booking under concurrency**, reminder jobs, integration outage | own | |
| 11 Upgrade | a rule change applied to existing bookings, recurrence redefinition | own | |
| 12 Experience | the person booking on a phone, in a hurry | own | |

**Usual set: 1,2×2,3,6,8,9,10,11,12 own + 4 N/A, 5→3, 7→8 = 10 agents.**

## Failure catalogue

Two concurrent bookings for the last slot · a booking at the exact minute a slot opens and closes ·
**daylight-saving transitions**: a recurring 09:00 appointment across spring-forward and fall-back, a slot
in the local hour that does not exist, and one in the hour that happens twice · host and guest in different
zones, and one in a half-hour or 45-minute offset · a zone whose rules changed since your tzdata was built ·
a recurrence with an exception, a deleted occurrence, and an edited occurrence · "last Monday of the month"
in a five-Monday month · the 29th, 30th and 31st as a monthly anniversary · a recurrence with no end · a
cancellation after a reminder was queued · an expired integration token · the external calendar edited
directly · a resource deleted with future bookings · a buffer rule meeting a back-to-back booking · a
booking spanning midnight, and one spanning the transition itself.

## Defect classes to look for by name

**Double-booking under concurrency** — availability checked and the slot written with no lock and no
unique constraint. It is this domain's canonical critical defect and it is invisible to sequential testing ·
**availability computed in one timezone and displayed in another** · daylight-saving errors: a recurring
appointment drifting by an hour, an occurrence created in a nonexistent local time, an occurrence
duplicated in the repeated hour · recurrence expansion diverging from the standard, especially **exceptions
lost when a series is edited** · stale tzdata, so a changed zone is confidently wrong · reminders fired at
the wrong time, twice, or never · a cancellation that does not release the slot — or releases someone
else's · buffer rules applied on one side only · an external-calendar sync that loses or duplicates events,
or treats the external copy as authoritative and overwrites yours · the timezone of a **resource** (a room)
conflated with the timezone of a **person**.

## Evidence and severity

Two oracles, and neither of them is the product. **First, an independent date library**: compute the
expected local times and UTC instants yourself from tzdata, and never grade the product's expansion against
its own expansion. **Second, a count**: how many confirmed bookings exist for one slot. Double-booking is
proved by two confirmations and one unit of capacity — a count, not a judgement.

Concurrency must be genuinely simultaneous (the "run twice at once" rule in `evidence-standard.md`); two
sequential requests prove nothing here. Record the zone of every actor, the **tzdata version**, the
recurrence rule verbatim, and UTC instants alongside local times on every finding.

`evidence-standard.md` → *Stateful systems under fault* (concurrency and the clock), *Background and
scheduled work* (reminders are scheduled work and are proved by their side effect), *Migrations, upgrades
and restores* for rule changes against existing bookings.

| Observation | Severity |
|---|---|
| Double-booking a person or a resource | **critical** |
| A booking moved or lost by an hour across a DST change | **critical** — someone misses a flight, a shift, an operation |
| Recurrence exceptions lost on an edit | **critical** — silent data loss |
| A reminder not fired for a paid or clinical appointment | **blocker** |
| Availability displayed in the wrong zone | **blocker** |
| Buffer rules applied asymmetrically | **major** |

## Experience

**Who the user is:** someone booking on a phone, in their own timezone, in under a minute — and the staff
member whose day it rearranges.

**Where it lives:** whether a time is shown in the user's zone **with the zone named**; reschedule and
cancel without an account; what a double-booking looks like to the two people who made it; the reminder's
content; and whether add-to-calendar produces the right instant.

**First success is:** a booking made on a phone that appears at the correct time in the booker's own
calendar app.

**Do the thing, for experience:**

> Book from a phone set to a different timezone from the host, then open the calendar invite and check that
> the time is the one you agreed.

**Defect classes:** **a time shown without its zone** — the commonest and most expensive wording defect in
the domain · a reschedule link that demands an account · an invite whose attached time disagrees with the
confirmation page · a reminder arriving after the appointment · no indication that a slot was taken while
the form was open.

**Evidence note:** the "actively misled" clause is operative — a displayed local time that differs from the
stored instant is a product bug as well as an experience defect, under one id, and it inherits the severity
of the missed appointment rather than the severity of a label.

## Domain gotchas

- **Never test daylight saving by waiting for October.** Find the clock-control mechanism — a fake clock, a
  settable clock in a container — or family 10 is `BLOCKED` beyond the current moment. Test both
  spring-forward and fall-back, and in both hemispheres.
- Half-hour and 45-minute offsets (India, Nepal, parts of Australia) break assumptions that whole-hour
  zones hide. Put one in the matrix permanently.
- **tzdata is a versioned dependency.** Record the version, and establish whether the product ships its own
  copy or uses the host's — a stale copy is a real finding with a real wrong answer behind it.
- Calendar integrations need real provider accounts, and their own misconfiguration will masquerade as a
  product bug. Prove the baseline sync first.
- Writing to a real calendar and sending a real confirmation are both outward-facing. Use accounts you own,
  and treat the confirmation as a send (see `messaging-delivery.md`).
