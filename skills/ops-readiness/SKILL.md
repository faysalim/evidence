---
name: ops-readiness
description: Establish that a release can actually be operated - rollback rehearsed not merely documented, an alert proven to fire, on-call named, the runbook walked by someone who did not write it, certificates and quotas good past the date - each a readiness checkpoint the release verdict reads. Use when the user asks whether something is safe to deploy, wants rollback, alerting, on-call, runbook, SLO or capacity readiness. Not for testing the product - that is evidence:qa. Not for security or privacy sign-off - that is evidence:security-review. Not for known issues or the watch plan - that is evidence:support-readiness. Not for calling the release - that is evidence:release.
roles: DEVOPS
status: draft
---

# Ops readiness

`status: draft` — see `${CLAUDE_SKILL_DIR}/README.md`.

This skill exists because of a specific, measurable hole. Until it did, the go/no-go was computed
entirely from QA evidence — so **"ready to ship" meant "QA found nothing"** and said nothing about
whether the rollback had ever been run, whether a single alert would fire, or whether anyone was on
call that weekend. An independent review named it the largest gap in the suite, and it was right:
roughly the operational half of release readiness had no owner, no role and no items.

The rule that makes this skill worth running is `shared/principles.md` §1 — **the artifact is the
evidence.** A rehearsed rollback is evidence. A documented rollback is a document.

Items move only through `python "${CLAUDE_PLUGIN_ROOT}/shared/scripts/hub.py"`.

## Before you start: read the profile

```
hub.py status          # mode, the product class, and what orient could not establish
hub.py profile         # the full profile, including their domains and acceptance requirements
```

If there is no profile, stop and run `/evidence:orient` — without it this skill guesses the product
class, the deploy branch and what the team calls things, and a guess here is wrong in a way nobody
notices until the first handoff is rejected on vocabulary.

Read `<report-dir>/conventions.md` too, and **use their words, their ids and their templates.** If
they number requirements `CR-4` or call a story an MMF, so does this skill; existing ids are
preserved, never renumbered. The ten principles in `${CLAUDE_PLUGIN_ROOT}/shared/principles.md` are
the only thing here that is not theirs to set — and `status` prints what orient could not establish,
which you must read before assuming anyone looked.

## Import their checklist; do not adopt this one

**Most teams that need this already have a list** — a deploy checklist, a change-management form, a
production-readiness review. `/evidence:orient` Step 5 maps runbooks and SLOs in as acceptance
requirements; the same rule applies here. Import theirs, keep their ids, and add only what is
missing.

The checkpoints below are what to look for when a team has none. They are **not** a standard and
this skill does not claim they are complete for your product — read the domain file in
`${CLAUDE_PLUGIN_ROOT}/shared/domains/` for the failure modes your product class is known for, and
add a checkpoint per fault that has no owner.

## What this skill produces

| Hub item | Note |
|---|---|
| `readiness` | `OPEN` → `MET` with **evidence of the thing having happened**. Only the operator may `WAIVE` one, with a reason |
| `risk` | Where a checkpoint cannot be met before the date and nobody is mitigating it |
| `finding` | Where readiness work uncovers a defect — a rollback that loses data is a `finding`, not an open checkpoint |
| `cleanup` | Every environment, certificate, quota increase or test tenant you touch, from minute one |

```
hub.py add readiness RD-1 -f title="rollback rehearsed on the candidate build" \
       -f owner_role=DEVOPS --role DEVOPS
hub.py move RD-1 MET -f evidence="rehearsed 2026-03-04 14:10Z, 41s to the previous digest, \
       0 rows lost, log at <path>" --role DEVOPS
```

`MET` requires `evidence`, and the hub refuses it otherwise. **`title` and `owner_role` are
required at creation** so a checkpoint can never sit in the hub without someone's name against it.

## The checkpoints that earn their place

Each of these is here because its absence has a specific cost, and each is phrased so that a
different person can grade it.

| Checkpoint | What `MET` requires — evidence, not assurance |
|---|---|
| **Rollback rehearsed** | You ran it, on the candidate build, and timed it. Not "we can roll back" |
| **Rollback data path** | What happens to writes made after the deploy and before the rollback. If the answer is "they are lost", that is a `decision` for the operator, not a checkpoint you quietly mark `MET` |
| **An alert actually fired** | You broke the thing deliberately and the page arrived, at the destination that is on call. An alert nobody has seen fire is a config file |
| **On-call named, for the window** | A person and a backup, for the specific days around the release. "The team" is not on call |
| **Runbook walked by someone who did not write it** | The author cannot find the gaps; that is the whole point. Record who walked it and where they stopped |
| **Certificates, licences, quotas and secrets** | Expiry dates past the release horizon, and the rotation path tested. A certificate expiring mid-quarter is an outage with a date on it |
| **Capacity and limits** | The headroom at the expected load, and what happens at the limit — refusal, degradation or collapse |
| **Backups restored, not just taken** | A backup nobody has restored is a hypothesis. Restore it somewhere and read the data |
| **Observability for the new surface** | The thing you are shipping is visible: a metric, a log line, a trace. Otherwise nobody can tell it is broken |
| **The deploy is reversible by one person at 2 a.m.** | Steps, access, and no dependency on someone's laptop |

**An absent answer is a finding, not a blank.** If nobody knows what happens to in-flight writes
during a rollback, that is the most valuable thing you will learn this week, and it is a `risk` with
an owner rather than a checkbox left unticked.

## The verdict reads these

`/evidence:release` computes the go/no-go, and one of its conditions is now **every readiness
checkpoint `MET`, or waived by the operator**. Three consequences worth knowing before you start:

- **A hub with no readiness rows yields `NO VERDICT`**, not `NOT GREEN`. That is not a claim the
  release is unsafe; it is a refusal to call green on evidence nobody supplied, and the condition
  says in as many words that the verdict covers QA evidence only.
- **You cannot mark your own checkpoint waived.** Waiving is the operator's, with a reason, because
  shipping without a rehearsed rollback is a decision and should be visible and attributed rather
  than absorbed into a summary.
- **Re-opening a `MET` checkpoint needs a reason** and is the right move when the candidate build
  changes. Evidence is about a build; a new build invalidates it.

## For the lead

Read the `evidence` field on three `MET` checkpoints at random and ask: *does this describe something
that happened, with a time and a result, or something that is true in principle?* "Rollback
documented in the runbook" is the failure mode, and it passes a glance.

Then ask the question this skill exists for: **which of the ten checkpoints above has no owner on
this team?** That one is the gap, and it is usually alerting or the rollback data path.

## Open questions

- Whether `readiness` should require a link to the `release` it gates, so a stale checkpoint from
  two releases ago cannot satisfy today's verdict. Today the verdict reads all of them, which is
  conservative in the right direction but will eventually read a checkpoint nobody meant.
- The ten checkpoints are reasoned from common production failure modes, not measured against an
  engagement. The rollback and alerting ones have the strongest case; the rest are conventional.
- No template ships for a production-readiness review document. The table above is the checklist.
- Whether capacity belongs here or with `/evidence:qa`'s performance scope. Today it is a
  checkpoint here and a case there, which risks two owners for one number.

| File | Read it when |
|---|---|
| `${CLAUDE_PLUGIN_ROOT}/shared/principles.md` | First. §1 and §6 govern this skill |
| `${CLAUDE_PLUGIN_ROOT}/shared/domains/` | **Before writing checkpoints.** The fault catalogue the class is known for |
| `${CLAUDE_PLUGIN_ROOT}/shared/references/evidence-standard.md` | What counts as evidence that a thing happened |
| `${CLAUDE_PLUGIN_ROOT}/shared/contracts/release-readiness.md` | The handoff into `/evidence:release` |
