# Release-checklist map

Which skill owns which release-readiness checkpoint, so an unowned one is visible rather than
assumed. Generated against `shared/hub/model.json: default_checkpoints`; regenerate rather than
edit rows.

---

## The 100-checkpoint list was not supplied, and this document does not pretend otherwise

The review asked for all **100 release checkpoints** to be mapped to an owning skill or to N/A with
a reason, and for the unowned count to be reported. **That list has never reached this repository or
this session.** It is not in `docs/`, not in the git history, and not in any message here.

So the honest report is: **the unowned count against that list is UNKNOWN, not zero.** Writing a
hundred plausible checkpoints and mapping those would produce a coverage number whose denominator I
invented, presented as a measurement against someone else's list -- which is the exact defect this
suite exists to catch, committed in the one document whose whole job is to state a denominator.
`shared/principles.md` §2 and §4.

**What would close it:** the list, in any form. The mapping below is already structured to take it,
and the work is an afternoon once the denominator exists.

## What IS mapped: the 31 default checkpoints

These are this suite's own defaults -- the fallback when a team has none of their own. Every one has
a named owning role and skill, which is what makes an unowned checkpoint visible.

| Key | Owning role | Skill | What MET requires |
|---|---|---|---|
| `rollback-rehearsed` | DEVOPS | `ops-readiness` | Rollback run on the candidate build, and timed |
| `rollback-data-path` | DEVOPS | `ops-readiness` | What happens to writes made after deploy and before rollback |
| `alert-fired` | DEVOPS | `ops-readiness` | An alert was deliberately triggered and the page arrived on-call |
| `on-call-named` | DEVOPS | `ops-readiness` | A named person and a backup, for the release window |
| `runbook-walked` | DEVOPS | `ops-readiness` | Walked by someone who did not write it, with where they stopped |
| `certs-quotas-secrets` | DEVOPS | `ops-readiness` | Expiry past the release horizon, rotation path tested |
| `capacity-limits` | DEVOPS | `ops-readiness` | Headroom at expected load, and the behaviour at the limit |
| `backup-restored` | DEVOPS | `ops-readiness` | A backup restored somewhere and the data read, not merely taken |
| `observability-new-surface` | DEVOPS | `ops-readiness` | The shipped surface is visible: metric, log or trace |
| `one-person-deploy` | DEVOPS | `ops-readiness` | Reversible by one person at 2 a.m., with access and no laptop dependency |
| `canary-staged-rollout` | DEVOPS | `ops-readiness` | Staged exposure defined: cohort, duration, and the promote/halt rule |
| `kill-switch` | DEVOPS | `ops-readiness` | The new behaviour can be turned off without a deploy, and that was exercised |
| `status-page` | DEVOPS | `ops-readiness` | Who updates it, with what wording, and the trigger to do so |
| `dns-email-auth` | DEVOPS | `ops-readiness` | DNS, SPF, DKIM and DMARC correct for any new sending or serving name |
| `data-classification` | SECURITY | `security-review` | What classes of data the change touches, from schema and code |
| `privacy-signoff` | SECURITY | `security-review` | Named signer, date and scope where personal data is touched |
| `legal-signoff` | SECURITY | `security-review` | Where a term, licence or customer contract is implicated |
| `dependency-check` | SECURITY | `security-review` | Run against the candidate digest, with the result |
| `secrets-check` | SECURITY | `security-review` | No credential in the artifact, image, logs or client bundle |
| `authz-new-surface` | SECURITY | `security-review` | Every new route, flag or field exercised as a role that must not reach it |
| `audit-trail` | SECURITY | `security-review` | A new privileged action is attributable afterwards |
| `threat-model` | SECURITY | `security-review` | Updated, or explicitly stated unchanged |
| `consent-and-telemetry-observed` | SECURITY | `security-review` | Consent honoured and telemetry observed ON THE WIRE, not from the product's own setting |
| `known-issues-published` | SUPPORT | `support-readiness` | Generated from open and DECIDE findings, each with symptom and workaround |
| `answers-prepared` | SUPPORT | `support-readiness` | The questions this change predictably causes, answered in advance |
| `escalation-path` | SUPPORT | `support-readiness` | Who support reaches by name in the window, and what they may do |
| `support-surfaces-updated` | SUPPORT | `support-readiness` | Macros, canned replies and help-centre entries the change makes wrong |
| `watch-plan` | SUPPORT | `support-readiness` | What, who, how long, and what would make us act |
| `volume-expectation` | SUPPORT | `support-readiness` | Plausible effect on ticket volume, and whether the rota covers it |
| `support-trained` | SUPPORT | `support-readiness` | Support walked the change themselves, not just read about it |
| `sales-cs-briefed` | SUPPORT | `support-readiness` | Sales and customer success told what changed and what not to promise |
**31 of 31 mapped. 0 unowned.** That is a complete statement about *this* set and says nothing about
the 100-item list above.

## The QA-side half, for completeness

Release readiness is not only the three roles above. The verdict's other conditions are QA's, and
they map to the twelve scope families in `skills/qa/references/scope-playbooks.md`:

| Verdict condition | Owner |
|---|---|
| No open `critical` or `blocker`, including any held at `DECIDE` | `qa` |
| Every blocking defect class has a `PASS` in a calibrated scope | `qa` |
| No unreconciled `LONG` row | `qa` |
| No `BLOCKED` or `NOT RUN` row guarding a blocking class | `qa` |
| Build identity established per component | `release`, from DEV's candidate |
| Smoke and calibration rows ran on the build the verdict names | `qa` |
| Every acceptance requirement has a `PASS` | `qa`, against source 0 from `orient` |
| No story `DONE` but unaccepted; no decision awaiting the operator; no open risk; cleanup empty | `backlog`, `delivery`, `hub` |
| Every release-readiness checkpoint `MET` or waived, on this release's build | `ops-readiness`, `security-review`, `support-readiness` |

## Areas this suite does NOT own, with reasons

Named rather than left as a silent gap. Each is a deliberate N/A, not an oversight.

| Area | Why N/A |
|---|---|
| Financial sign-off, pricing approval, revenue recognition | Finance owns these and they are not release-readiness in the engineering sense. An operator `decision` is the right vehicle where one is needed |
| Contract and procurement workflow | `security-review` covers the sign-off *existing*; negotiating it is not a product-team activity |
| Marketing campaign scheduling, press and analyst timing | `launch` owns the claims and their evidence, deliberately not the calendar |
| Training content for end users | `docs-authoring` owns documentation; curriculum design is a different discipline |
| Localisation sign-off per market | No domain file covers it and inventing one would be imposing. A real engagement in a localised product should add the domain |
| Accessibility audit | `design` owns it as a section of its own in a review, and says it has its own owner and its own fixes. A full audit against a standard is specialist work this suite does not claim |
| Incident-response process itself | `ops-readiness` checks that on-call and escalation exist for the window. Designing the IR process is an ops discipline, not a release gate |

## How to regenerate

```
python -I -B -c "import json,io; d=json.load(io.open('shared/hub/model.json',encoding='utf-8'))['default_checkpoints']; print(sum(len(v) for k,v in d.items() if k!='doc'))"
```

The count in the heading above must match that number. `check_repo.py` does not yet enforce it,
which is the kind of hand-maintained count this repo has already been bitten by three times --
recorded here as the next cheap check to add.
