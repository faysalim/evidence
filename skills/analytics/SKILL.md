---
name: analytics
description: Read product metrics against the denominator and baseline the PRD stated, compare to that baseline rather than a feeling, write the post-launch review including the metrics that did not move, and feed findings back as insights. Use when the user wants metrics read or defined, a launch or experiment assessed, a funnel or retention analysed, or a post-launch review. Not for defining success criteria - that is evidence:prd. Not for instrumenting code - that is evidence:dev. Not for qualitative research - that is evidence:discovery.
roles: ANALYST
status: exercised
---

# Analytics

`status: exercised` -- run against a real product; weaker than `proven`. See `${CLAUDE_SKILL_DIR}/README.md`.

Analytics is where a denominatorless number does the most damage, because a number looks like evidence
even when it is not. *"Activation is up 12%"* — of what, measured how, compared to when, excluding which
accounts? Each of those four questions can reverse the conclusion, and none of them is visible in the
sentence.

So this skill is `shared/principles.md` §2 — **every number has a denominator** — plus §3's oracle rule
applied to measurement: **a metric whose definition lives only in the query you ran is not a metric.** If a
different analyst cannot reproduce your number from the written definition, it is an artifact of your SQL.

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
| `metric` | `DEFINED` → `BASELINED` (requires `denominator` and `baseline`) → `READ` (requires `value`, `denominator`, `evidence`) → `INTERPRETED` **by the PM, not by you** |
| `insight` | What the reading taught you, feeding back into discovery with its own evidence and `does_not_show` |
| `finding` | When the data shows the product is broken — a funnel step with a 100% drop is a bug, not a conversion problem |

The last transition matters: **the analyst reads, a different role interprets.** That is §7. A reading and
its interpretation are different claims on different evidence, and collapsing them is how "the feature
failed" becomes consensus when what happened was that the instrumentation shipped two weeks late.

## The metric contract

Inherited from the PRD, which defined it before anything was built. If a metric arrives without this, it
is not ready to read, and saying so is the deliverable:

```
name          Activation rate
definition    % of signups completing first success within 7 days
denominator   signups in the period, EXCLUDING internal, test and reactivated accounts
baseline      measured value, with the window it was measured over
evidence      WHERE the baseline came from -- the artifact, query or document, quoted
              Required to reach `BASELINED`. A reading already had to be sourced; the
              baseline every reading is later compared against did not, which is backwards
target        value and date, from the PRD
instrumented  which events, since when -- and whether the window predates instrumentation
window        the period this reading covers, and why that period
```

**`instrumented ... since when` is the field that prevents the most common wrong conclusion.** A metric
compared against a baseline from before its events existed is not a comparison. If the instrumentation is
younger than the window, the honest reading is "not measurable yet", which the hub has a state for:
`NOT_MEASURABLE`.

## Reading a metric

1. **Read the definition first, then write the query.** The reverse — query first, definition reconstructed
   from it — is how exclusions get forgotten.
2. **State the denominator in the result, every time.** `1,240 of 9,870 signups (12.6%)`, not `12.6%`. The
   percentage alone cannot be sanity-checked by anyone.
3. **Compare to the stated baseline**, not to last week and not to a recollection. If the baseline was
   never measured, say that — the comparison does not exist and no amount of analysis creates it. And
   **read the denominator off the instrument, never off the PRD's recollection of it.** Exercising this
   skill, a baseline inherited as "49 of 512" turned out to be 49 of **128** — the product states its
   own bound in the validation artifact — so the rate was 38%, not 9.6%. A factor of four, from one
   number nobody had to source. That is why `evidence` is now required to reach `BASELINED`.
4. **For a product with repeated acceptance runs, the unit of analysis is the series, not the run.**
   Reading the latest run — or the one that happens to be open — is a selection effect with the same
   shape as reporting only the metrics that improved. Exercising this skill against three
   certification rungs of one product: the 4-hour run was clean on durability (0 missing of 3.1M
   keys) and the 3-hour run had **lost two acknowledged keys**. A confident "durability is clean,
   this is an availability problem" came from reading one of the three. List the runs you read *and
   the ones you did not*, the way you list the metrics that did not move.
5. **Segment before concluding.** An aggregate that did not move often hides two segments moving in
   opposite directions, which is a different finding with a different action.
6. **Check the instrumentation against reality.** Count the events, then count the thing they claim to
   count, independently. A funnel step that reports zero is usually a tracking bug; this is §3 — the
   product's own counters are the thing under test, not the oracle.
7. **Report what did not move.** A post-launch review listing only the metrics that improved is a selection
   effect, and everyone reading it knows that, which is why they stop trusting the reviews.

## The post-launch review

```
What shipped          the release id, and the date it reached users
Metrics, each with    definition, denominator, baseline, reading, delta, window
What moved            and whether the window is long enough to say so
What did not move     including the ones you hoped for. This section is not optional
What we cannot tell   instrumentation gaps, windows too short, confounds (a price change,
                      a seasonal effect, another release in the same week)
Insights              fed back as insight items, with evidence and does_not_show
Recommendation        and who owns the decision it implies
```

**"What we cannot tell" is the section that makes the rest credible** (§4). A review with no uncertainty
section is asserting precision it does not have, and the confounds are usually easy to list and genuinely
change the reading — another release in the same week is the most common and the most ignored.

Resist attributing a change to the release when you cannot separate it from everything else that happened.
"Activation rose 4 points; a pricing change landed in the same window, so this cannot be attributed" is a
real result and a more useful one than a confident wrong attribution.

## New product and existing product

| | New | Existing |
|---|---|---|
| Baseline | There isn't one. The first reading **is** the baseline — say so, and do not compare it to anything | Exists, or should. If the PRD claimed one that was never measured, that is the first finding |
| Instrumentation | Usually ships with the feature, so the window starts at launch | Already there, and probably measures something subtly different from what the PRD assumed. Verify before trusting |
| Denominator risk | Small n. Report the n, not just the rate | Historical definition drift: the same metric name meaning different things across two years |

For an existing product, **check whether the metric's definition changed during the comparison window.**
A redefinition mid-window produces a step change that looks like a product effect and is an accounting
change. This is the analytics version of "which build is actually serving".

## For the lead

Read the denominator and the window before the number. If either is missing, the number is not reviewable
and sending it back costs less than a quarter of decisions built on it.

Then ask the two questions that most often change a conclusion: **what else shipped in this window?** and
**is the instrumentation older than the baseline?** And check that the "what did not move" section exists —
its absence is the most reliable sign of a review written to confirm something.

## Open questions

- Whether `metric` should carry the query or definition as a required field so a reading is reproducible
  from the hub alone. Strongest enforcement candidate here; the obstacle is that queries contain
  connection details that must not land in an artifact (§8).
- No template ships for the post-launch review; the field list above is it.
- Whether experiment design (sample-ratio mismatch, sequential testing, stopping rules) belongs here or in
  its own skill. It is a distinct discipline with its own failure modes, and this skill currently only
  gestures at it.

| File | Read it when |
|---|---|
| `${CLAUDE_PLUGIN_ROOT}/shared/principles.md` | First. §2 and §3 govern this skill |
| `${CLAUDE_PLUGIN_ROOT}/shared/references/evidence-standard.md` | Verifying instrumentation independently of the product's own counters |
| `${CLAUDE_PLUGIN_ROOT}/shared/references/experience.md` | Where a metric meets a usability measure: time to first success |
