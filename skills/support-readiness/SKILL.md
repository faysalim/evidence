---
name: support-readiness
description: Establish that whoever answers for a release after it ships is ready - known issues generated from the findings nobody fixed, answers for what this change will prompt, a named escalation path, and a watch plan saying who looks at what, for how long, and what would make them act - as readiness checkpoints the release verdict reads. Use when the user asks whether support is ready, wants a known-issues list, escalation path, post-launch monitoring or watch plan, or asks what customers will ask after a release. Not for user docs - that is evidence:docs-authoring. Not for deploy, rollback or alerting - that is evidence:ops-readiness. Not for calling the release - that is evidence:release.
roles: SUPPORT
status: draft
---

# Support readiness

`status: draft` — see `${CLAUDE_SKILL_DIR}/README.md`.

Support is where every unstated assumption in a release arrives, in the form of a person who is
confused and paying. And it is the role most often left out of readiness entirely, which produces a
specific and familiar failure: **the team knows about a defect, decided not to fix it, and the first
person to hear about it is a customer talking to someone who has never heard of it.**

So this skill turns the two things nobody writes down into items: **what we know is broken and are
shipping anyway**, and **what we will watch for and for how long.** Both come from evidence that
already exists in the hub — the findings that were not fixed, and the metrics the PRD defined.

Governed by `shared/principles.md` §4 — **every claim states what it does not claim.** A release note
that omits the known issues is a claim that there are none.

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

## What this skill produces

| Hub item | Note |
|---|---|
| `readiness` | One per checkpoint. `OPEN` → `MET` with evidence. Only the operator may `WAIVE` |
| `doc` | The known-issue list and the answers, as documents `/evidence:docs-authoring` verifies like any other |
| `risk` | Where the volume or the severity of what is shipping exceeds what support can absorb |
| `insight` | What the first week actually generated, fed back with `confidence: authored` — support tickets are user-authored evidence and `/evidence:discovery` treats them as such |

```
hub.py add readiness RD-3 -f title="known-issue list published for the candidate" \
       -f owner_role=SUPPORT --role SUPPORT
hub.py move RD-3 MET -f evidence="7 open findings not fixed in 2.5.1, each with a workaround \
       and an id; published to the support wiki 2026-03-05" --role SUPPORT
```

## The known-issue list is generated, not remembered

This is the part that makes the skill worth running rather than a meeting. The list comes from the
hub, so it cannot omit what was inconvenient:

```
hub.py list --type finding --state NEW
hub.py list --type finding --state DECIDE
```

Every finding still open at release, plus every one held at `DECIDE`, is a known issue. For each,
support needs three things and the first is the only one that is hard:

| | |
|---|---|
| **The symptom in the customer's words** | Not the defect's. "Export silently drops rows for viewer-role users" is the finding; "my CSV is missing rows" is what the ticket will say |
| **The workaround, or its absence** | "None" is a real answer and support must know it in advance rather than discover it live |
| **Who owns the fix, and when** | So the answer is "fixed in 2.5.2, early April" rather than "I'll find out" |

**A finding held at `DECIDE` is the one that matters most**, because somebody has already decided to
ship it. If support has not been told, that decision was taken on their behalf.

## The post-launch watch plan

A release with no watch plan has decided that the first signal will be a customer. Four fields, and
the last one is the one nobody writes:

```
what        the metric or signal, by name -- from the PRD's metric items where they exist
who         a person, for each signal
window       how long. "We will keep an eye on it" is not a window
what would make us act   the threshold, and the action -- roll back, hotfix, or accept
```

The last line is the oracle rule (`shared/principles.md` §3) applied to a watch: a plan whose
trigger is "if it looks bad" cannot be acted on by anyone but its author, at 3 a.m., under pressure.

`/evidence:analytics` reads the metrics afterwards and the **series**, not one run — so name the
baseline now, while it is still cheap.

## The checkpoints that earn their place

| Checkpoint | What `MET` requires |
|---|---|
| **Known-issue list published** | Generated from open and `DECIDE` findings, each with symptom, workaround and owner |
| **Answers for what this change will generate** | The two or three questions the change predictably causes, answered in advance |
| **Escalation path named** | Who support reaches, by name, in the release window — and what they are allowed to do |
| **Support surfaces updated** | Macros, canned replies, help-centre entries that the change makes wrong |
| **Post-launch watch plan** | The four fields above, with a named owner per signal |
| **Volume expectation** | What this release plausibly does to ticket volume, and whether the rota covers it |

## For the lead

One question, and it is the whole review: **take the three most recently closed `DECIDE` findings and
ask whether support can answer a customer about each of them.** If not, the team has shipped a known
defect without telling the people who will be blamed for it.

Second: **does the watch plan name a threshold and an action?** A watch with no trigger is a hope,
and it will be read as coverage.

## Open questions

- Whether the known-issue list should be a generated artifact from `hub.py` rather than a `doc` a
  person assembles. Generating it would guarantee it is complete; it would also lose the
  customer's-words translation, which is the valuable part and cannot be generated.
- Whether post-launch watch belongs here or in `/evidence:analytics`. It is here because the watch
  is an operational commitment with an owner; the reading afterwards is analytics'. That split is
  reasoned, not tested.
- No template ships for the known-issue list. The three columns above are it.
- Support tickets are the richest user-authored corpus most products have, and this skill only
  gestures at feeding them to `/evidence:discovery`. That handoff deserves a contract.

| File | Read it when |
|---|---|
| `${CLAUDE_PLUGIN_ROOT}/shared/principles.md` | First. §3 and §4 govern this skill |
| `${CLAUDE_PLUGIN_ROOT}/shared/vocabulary.md` | `DECIDE` — the closing action that means somebody chose to ship it |
| `${CLAUDE_PLUGIN_ROOT}/shared/references/experience.md` | Writing a symptom in the customer's words |
| `${CLAUDE_PLUGIN_ROOT}/shared/contracts/release-readiness.md` | The handoff into `/evidence:release` |
