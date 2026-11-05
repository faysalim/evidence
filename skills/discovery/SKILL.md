---
name: discovery
description: Plan and synthesise product research from whatever real evidence exists - user-authored forum threads and issue trackers, support tickets, observed sessions, analytics, interviews - into insight items that each carry their evidence, sampling frame and what they do not show, separating observed from authored from reported from inferred. Never invents a user. Use when the user wants user research planned or synthesised, interviews or usability sessions prepared, findings turned into insights, or a problem validated before a PRD. Not for writing the PRD - that is evidence:prd.
roles: RESEARCHER
status: exercised
---

# Discovery

`status: exercised` -- run against a real product; weaker than `proven`. See `${CLAUDE_SKILL_DIR}/README.md`.

Discovery's characteristic failure is not a bad interview. It is an insight nobody can argue with because
nobody can see what it rests on: *"users want simpler onboarding"*, with no sample, no quote and no
statement of what the research did not look at. Then a quarter of engineering is spent on it.

So the whole skill reduces to applying two principles to research. `shared/principles.md` §2 — **every
number has a denominator** — and §4 — **every claim states what it does NOT claim.** An insight that
cannot pass those two is a hypothesis, which is fine, as long as it is labelled one.

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

## Evidence sources: interviews are one, and rarely the first available

**Research is not blocked on access to people.** This skill was written interview-first and treated
everything else as a warm-up, which made it unrunnable for exactly the products where discovery
matters most: infrastructure, developer tools, anything self-hosted where you cannot reach your
users, anything pre-launch. That framing was a defect, not a limitation of research.

What is never acceptable is *inventing* a user, a quote, a persona or a count. Independence from
interviews, not independence from evidence. If no evidence of any kind exists, the deliverable is
saying so.

| Source | What it can support | Watch for |
|---|---|---|
| **Observed sessions** | Strongest claims about behaviour | Small n; the observer changes the behaviour |
| **User-authored public artifacts** — forum threads, issue trackers, Q&A sites, review sites, competitors' issues | Unprompted, timestamped, attributable, re-readable by a third party. **Often the largest corpus available and the only one for a pre-launch product** | The sampling frame is yours, not theirs — see below |
| **Support tickets, sales-loss reasons** | Real failures, already sampled | Skewed to users who bothered to write |
| **Interviews** | Depth, and the *why* behind a behaviour | Elicited; people misremember frequency and motive |
| **Analytics** | What happened, at scale | No *why*; and see `/evidence:analytics` on denominators |
| **Nothing** | Nothing. Say so, and say what you tried to find | Do not fill it with a persona |

A new product has no users and that does not mean no evidence: **the problem exists in public before
your product does.** Competitors' issue trackers, the forum threads where people describe the
workaround, the questions asked on Q&A sites — all of it is user-authored and none of it needs your
product to exist.

### State the sampling frame, not just the sample size

For interviews the shape is who you spoke to. For an artifact corpus **the shape is the query set and
the platforms**, and it is part of the denominator. Without it a prevalence figure means nothing,
because *you* chose what to go and look for.

Exercising this skill on 158 user-authored items across 6 platforms and 17 search queries, that
mattered more than any other single step — see the next section.

### The elicitation line, for a corpus

"Count" below says the difference between *unprompted* and *agreed-when-asked* is most of the
signal. In a corpus the elicitation is **the search query that found the item**, not a question in a
room, and the same rule applies: an item whose theme was already named by the query that surfaced it
is elicited, not unprompted.

This is not a technicality. On that corpus, "the Redis licence change matters to people" read as 24
of 158 items — and **9 of 158 once the items found by queries containing "licen" were separated
out.** Fifteen of the twenty-four were my own search terms coming back to me. A corpus assembled
from your own hypothesis will confirm it, which is the "validating a solution you already chose"
trap arriving through the sampling frame rather than through a leading question.

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

`confidence` is the field that does the most work, because the values are routinely blurred:

- **observed** — you watched it happen. Strongest, and rarest.
- **authored** — the user wrote it down themselves, unprompted, in public, with a timestamp and an
  attributable handle, and a third party can go and re-read it. Not *observed* — you were not there —
  but stronger than *reported* in the ways that usually matter: nobody elicited it, no interviewer
  shaped it, and it is independently checkable rather than resting on your notes. This value exists
  because the original three were written for interviews, and classing a forum thread as "reported"
  understated it while "observed" overstated it.
- **reported** — someone told you, in response to your asking. Useful, and people misremember their own
  behaviour, especially about frequency and about why they did something.
- **inferred** — you concluded it from something else. Legitimate, and it is *your* claim rather than the
  user's, so it is labelled as yours.

An **authored** item that your own query named is not unprompted — see the elicitation line above.
The handle, the date and the URL go in `evidence`, so the claim can be re-read rather than trusted.

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
| Free evidence already in the building | **Not none.** The problem predates your product: competitors' issue trackers, the forum threads where people describe the workaround, Q&A sites. User-authored, unprompted, and available before you have a single user | All of the above, plus support tickets, sales-loss reasons, the first-run trace in the product profile, and `/evidence:analytics` readings |
| The trap | Validating a solution you already chose. Record the solution you had in mind *before* starting, so the contamination is visible | Assuming the current product shapes the problem. Your users have adapted to it; their workarounds are evidence about your product, not about the need |

For an existing product, **read the support tickets before writing the guide.** They are a free, large,
already-sampled corpus of real failures, and they will change what you ask.

**On a small team.** An insight is `ACCEPTED` by someone other than whoever evidenced it. A PM
doing their own research hands acceptance to the sponsor (`HEAD_OF_PRODUCT`).

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
