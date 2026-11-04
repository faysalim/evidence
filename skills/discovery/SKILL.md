---
name: discovery
description: Run product discovery as a researcher or PM: write interview guides, synthesise what users actually said into insight items that each carry their evidence, sample size and what they do not show, and separate what was observed from what was inferred. Use when the user wants user research planned or synthesised, interviews or usability sessions prepared, findings turned into insights, or a demand or problem validated before a PRD. Not for writing the PRD itself - that is product-suite:prd. Not for measuring a shipped product - that is product-suite:analytics.
---

# Discovery

`status: draft` — see `${CLAUDE_SKILL_DIR}/README.md`.

Discovery's characteristic failure is not a bad interview. It is an insight nobody can argue with because
nobody can see what it rests on: *"users want simpler onboarding"*, with no sample, no quote and no
statement of what the research did not look at. Then a quarter of engineering is spent on it.

So the whole skill reduces to applying two principles to research. `shared/principles.md` §2 — **every
number has a denominator** — and §4 — **every claim states what it does NOT claim.** An insight that
cannot pass those two is a hypothesis, which is fine, as long as it is labelled one.

Items move only through `python "${CLAUDE_PLUGIN_ROOT}/shared/scripts/hub.py"`.

## What this skill produces

| Hub item | When |
|---|---|
| `insight` | One per thing you learned. Not one per interview |
| `decision` | A conflict between what two user groups need, routed to the operator rather than averaged |
| `metric` | Where an insight implies something measurable, so the PRD inherits it already defined |

An `insight` reaches `EVIDENCED` only with `evidence`, `sample_size` and `does_not_show` — the hub refuses
it otherwise. Then **someone else accepts it**: the PM or Head of Product, not its author
(`shared/principles.md` §7).

## The insight contract

```
id            I-7
claim         One sentence. What is true, not what to build
evidence      Quotes, observed behaviour, counts. Verbatim where it is a quote
sample_size   n, and WHO: "6 of 9 admins at 3 customers; no end users"
method        Interview / observed session / support-ticket read / analytics pull
does_not_show The boundary. What a reader must not conclude from this
confidence    observed | reported | inferred
```

`confidence` is the field that does the most work, because the three are routinely blurred:

- **observed** — you watched it happen. Strongest, and rarest.
- **reported** — someone told you. Useful, and people misremember their own behaviour, especially about
  frequency and about why they did something.
- **inferred** — you concluded it from something else. Legitimate, and it is *your* claim rather than the
  user's, so it is labelled as yours.

A synthesis that presents inferred as observed is the research equivalent of a `PASS` with no evidence.

## Writing an interview guide

Short, because the value is in what you do not ask:

1. **Open on the last time, not the general case.** "Walk me through the last time you had to do X" beats
   "how do you usually do X" — the general case is a reconstruction, the last time is a memory.
2. **Ask about the workaround.** What people have built around a gap tells you the gap's real cost, and
   they will not volunteer it because it has stopped feeling like a problem.
3. **Never ask whether they would use a feature.** Everyone says yes. Ask what they do today, what it
   costs them, and what they have already paid to avoid it.
4. **Ask what they tried and abandoned.** Including your product, if they did.
5. **Leave the solution out.** Describing it contaminates everything after, so if you must show something,
   do it last and record that the session was contaminated from that point.
6. **Record the no-shows and refusals.** Who you could not reach is part of the denominator.

Template at `${CLAUDE_SKILL_DIR}/templates/interview-guide.md`.

## Synthesis

Read everything, then write insights — not the reverse. The common failure is writing the insight after
two interviews and spending the rest confirming it.

- **Group by what people were trying to do**, not by feature mentioned. Feature requests are a user's
  guess at a solution; the goal underneath is the finding.
- **Count.** "4 of 9 mentioned it unprompted; 2 more agreed when asked" is a result. "Several users felt"
  is not, and the difference between unprompted and agreed-when-asked is most of the signal.
- **Keep the disconfirming cases.** The two people for whom it was not a problem belong in the insight,
  with what made them different. An insight with no counter-case usually means you stopped looking.
- **A conflict is a `decision`, not an average.** When admins need control and end users need it gone,
  recording "users want balance" serves nobody. Write both positions and a recommendation, and let the
  operator choose — `shared/principles.md` §7.

## New product and existing product

| | New | Existing |
|---|---|---|
| Who to talk to | People with the problem, who have never seen your product. Hardest part is finding them honestly rather than finding people who will agree | Your own users first, then churned users — who are the highest-signal and the least interviewed |
| Free evidence already in the building | None. Say so | Support tickets, sales-loss reasons, the first-run trace in the product profile, and `/product-suite:analytics` readings |
| The trap | Validating a solution you already chose. Record the solution you had in mind *before* starting, so the contamination is visible | Assuming the current product shapes the problem. Your users have adapted to it; their workarounds are evidence about your product, not about the need |

For an existing product, **read the support tickets before writing the guide.** They are a free, large,
already-sampled corpus of real failures, and they will change what you ask.

## For the lead

Two checks. **Does every insight name a denominator and a `does_not_show`?** — if not, the report will be
quoted as certainty by someone who never reads this far. And **is the sample's shape stated, not just its
size?** Nine admins at three customers is not nine users, and a PRD built on it will miss every end user.

## Open questions

- No template ships for the synthesis document itself, only for the interview guide. One engagement's
  shape is not yet a pattern.
- Whether `insight` needs a `supersedes` link for when later research contradicts earlier research. Today
  you would withdraw the old one with a reason, which loses the arc.
- This skill has no worked example from a real engagement. It is reasoned from the principles, and the
  parts most likely to be wrong are the interview-guide heuristics.

| File | Read it when |
|---|---|
| `${CLAUDE_PLUGIN_ROOT}/shared/principles.md` | First. §2 and §4 govern this skill |
| `${CLAUDE_PLUGIN_ROOT}/shared/references/experience.md` | Observing a session, and what counts as evidence of harm |
| `${CLAUDE_SKILL_DIR}/templates/interview-guide.md` | Preparing sessions |
