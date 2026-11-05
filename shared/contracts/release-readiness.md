# Release readiness: the handoff into the go/no-go

Who this is between: `/evidence:ops-readiness` (DEVOPS), `/evidence:security-review` (SECURITY) and
`/evidence:support-readiness` (SUPPORT) on one side, `/evidence:release` (DELIVERY, PM, TECH_LEAD)
and the operator on the other.

Why it exists: until these three skills did, the go/no-go was computed entirely from QA evidence, so
**"ready to ship" meant "QA found nothing."** An independent review named that as the largest gap in
the suite. The fix is not a longer checklist — it is three owners, items they create, and one
verdict condition that reads them.

---

## The contract, in four sentences

1. **Each readiness role creates its own `readiness` items** and moves them to `MET` with evidence.
   Nobody creates a checkpoint on another role's behalf and marks it met.
2. **`MET` means it happened**, with a time and a result. Not that it is documented, planned or
   possible. `shared/principles.md` §1.
3. **Only the operator may `WAIVE`**, with a reason in their own words. Shipping without a rehearsed
   rollback is a legitimate decision and must be visible and attributed.
4. **The release skill does not override a checkpoint.** It computes; the condition either holds or
   it does not, and the operator's `SHIPPED` against a non-green is the recorded override.

## What the verdict does with them

One condition: **every readiness checkpoint `MET`, or waived by the operator.**

| Hub state | Verdict effect |
|---|---|
| No `readiness` rows at all | `NO VERDICT`, with the detail line naming what the verdict is silent about — rollback, alerting, on-call, runbooks, certificates, privacy, legal, support |
| Any row `OPEN` | Condition fails, naming the ids |
| All `MET` | Condition holds |
| Some `WAIVED` by the operator | Condition holds, and the waived ids are named in the verdict detail so the green is readable as "green with these waived" |

**No rows yields `NO VERDICT` rather than `NOT GREEN`.** That is not a claim the release is unsafe;
it is a refusal to call green on evidence nobody supplied, and it is the same treatment every other
condition with no rows gets (§6). A team whose ops checklist lives in a change-management system
imports it the way `/evidence:orient` Step 5 imports their runbooks and SLOs.

## The packet: readiness → release

What the release skill needs from each readiness role, per release candidate.

```
Build this covers        the digest, per component. Evidence is about a build, not a branch
Checkpoints MET          id, title, owner_role, and the evidence line for each
Checkpoints still OPEN   id, why, who owns it, and the date it could be met
Waived                   id, the operator's reason, verbatim
What this does NOT cover the boundary, in writing, before anyone asks
Expiry                   anything whose evidence goes stale -- a certificate date, a sign-off
                         scoped to a build, a rota that ends on a date
```

**`What this does NOT cover` is the field that makes the rest usable.** A rollback rehearsed on a
single-node staging cluster is real evidence about a single node and no evidence about three. Say
which.

## Re-opening on a new build

A candidate changes; evidence does not travel with it. Re-open any checkpoint whose evidence was
about the old digest:

```
hub.py move <the checkpoint> OPEN -f reason="candidate moved to <new digest>; the rehearsal was on <old>" --role DEVOPS
```

The transition requires a reason, so a re-opened checkpoint carries why rather than looking like a
regression nobody explained. **QA may also re-open one** — if QA finds the rollback loses data, the
checkpoint is no longer met and QA is the role that discovered it.

## Where a vulnerability goes, and where it does not

A vulnerability is a `finding` with a severity, never a `readiness` item. Readiness checkpoints
record whether the *process* that should have caught it ran; findings record what it found.
Collapsing the two hides defects inside a checklist, and the verdict's blocking-severity condition
stops seeing them.

Same for a rollback that loses data: the checkpoint is `OPEN`, and the data loss is a `finding` at
the severity its consequence earns.

## What this contract does not settle

- **Whether a `readiness` item should link to the `release` it gates.** Today the verdict reads all
  of them, which is conservative in the right direction and will eventually read a stale checkpoint
  from two releases ago. Recorded as an open question in `skills/ops-readiness`.
- **Who owns capacity.** It is a checkpoint here and a performance case in `/evidence:qa`. Two
  owners for one number is a known risk of this split.
- **The checkpoint lists themselves.** Each skill ships what to look for when a team has none. They
  are not a standard and do not claim completeness for any product class.
