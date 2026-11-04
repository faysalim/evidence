---
name: hub
description: Answer status questions from the shared work-item hub and render its dashboard: what is the status, what is waiting on me or on a role, what is blocked, show the traceability, validate the hub, and create items for roles with no skill of their own. Use when the user asks where something stands, what is waiting on whom, or wants the dashboard. Not for doing a role's work - use that role's skill, and a question the hub cannot answer gets a plain does-not-know.
---

# Hub

Everyone's skill. It answers *where things stand* and renders the dashboard, and it is the only place that
creates items for roles with no skill of their own — a sponsor approving a PRD, an operator answering a
decision, a stakeholder agreeing a requirement.

One rule governs every answer here: **the hub is the source of truth, and what it does not know, you do not
know.** If the fold has no event for it, the answer is "the hub has no record of that", followed by the
command that would record it. An invented status is worse than no status, because it gets planned against.

Read `${CLAUDE_PLUGIN_ROOT}/shared/principles.md` and `${CLAUDE_PLUGIN_ROOT}/shared/vocabulary.md` for the
item types, states and roles.

## Everything goes through the CLI

```
python "${CLAUDE_PLUGIN_ROOT}/shared/scripts/hub.py" <command>
```

Never hand-edit a file under the hub, and never hand-edit `qa-state.json` or `fix-state.json` — those are
**generated views** carrying a `generated_from` header, and a view that disagrees with the hub is not a
second opinion, it is a stale artifact. `hub.py validate` says so.

| Question | Command |
|---|---|
| Is there a hub at all, and which iteration is this? | `status` |
| What is waiting on me? | `list --mine --role <ROLE>` |
| What is waiting on a role? | `list --waiting-on PO` |
| What is open of a kind? | `list --type finding --state NEW` |
| Everything about one item, with its history | `show K1` |
| Is the hub internally consistent? | `validate` |
| Show me the dashboard | `dashboard` then open the printed path |
| Regenerate the compatibility views | `views` |

`--hub DIR` overrides the location; the default is `./qa-reports/hub`, checked first so an ordinary run
costs no question. Writes need `--actor NAME --role ROLE`, because **a claim is attributable or it is
anonymous** — that is the same rule as evidence on a finding.

## Answering a status question

Four steps, in order. The order is what stops a confident wrong answer:

1. **`status` first.** No hub → say so, and offer `init` (new work) or `import <dir>` (an existing product
   with prior artifacts). Do not describe work you have not read.
2. **`validate`.** If it reports problems, say that *before* the status. A hub with a stale view or an
   unknown finding id can produce a tidy, wrong summary, and the reader cannot tell.
3. **Read, then answer.** `list` and `show` for the specific question. Quote states and ids; do not
   paraphrase a state into a feeling. "`K4` is `FIXED`, waiting on QA" — not "the fix is nearly done".
4. **Name what is waiting on a human.** Finish with what is blocked on the operator, because that is the
   only part the team cannot unblock itself. `list --waiting-on OPERATOR`.

**Never answer a "are we ready to ship" question in prose.** Render the dashboard and report the computed
verdict with the condition that failed. `NO VERDICT` is a real answer and usually the honest one.

## Creating items for roles with no skill

A sponsor, a stakeholder and the operator do not get skills — they get decisions to make. Record their
answers as events so the trail survives the conversation:

```
hub.py move PRD-1 APPROVED --actor <name> --role HEAD_OF_PRODUCT
hub.py move D-3 ANSWERED -f answer="ship with the manual step; automate in 2.6" \
        --actor <name> --role OPERATOR
hub.py move REQ-7 AGREED --actor <name> --role PO
```

Two cautions, both of which have a cost:

- **Record what they actually decided, not what you inferred.** Quote them in the `answer` field. A
  decision summarised into something tidier is how a team ends up building the summary.
- **Do not move an item on someone's behalf without their decision.** The hub's whole value is that a
  state means a named party said so. If the operator has not answered, the item stays `OPEN` and the status
  report says it is waiting on them — that *is* the useful answer.

## Validating, and what the problems mean

`validate` reports structural problems the fold found. The ones with real consequences:

| Problem | What it means |
|---|---|
| duplicate `event_id` | A log was replayed or concatenated twice. Harmless to state (the fold ignores it) but it means someone copied a log rather than appending |
| an event waiting on events that never arrive | A log is missing — usually one actor's file was not committed or merged |
| a view is stale, or has no `generated_from` | `qa-state.json` no longer matches the hub. Run `views`. If it never had a header, someone hand-edited it: treat it as an import source, not as truth |
| links to an item that does not exist | Either a typo, or an id one side invented. On the QA↔DEV boundary this rejects a handback |
| a finding still `NEW` after being handed over | `NEW` is not a resting state. Somebody owes a triage decision |
| clock skew | Two machines' clocks disagree. Reported, never acted on: causal order already won |

A hub with problems can still answer questions. It cannot carry a verdict, and the dashboard says so.

## Importing an existing product's artifacts

For an existing product there is usually a prior register — an old `qa-state.json`, a report directory, a
spreadsheet someone kept.

```
hub.py import <report-dir>
```

**Ids are preserved unchanged**, because an id is a name and renumbering destroys the ability to discuss
anything across builds. Everything arrives `provenance: reconstructed` and in its initial state, **not**
in its old state — the old verdict is not inherited, because nobody verified it here. Each imported
finding carries a note saying so, and the report says the register was reconstructed rather than implying
it was authored. That is not pedantry: an imported "VERIFIED FIXED" that nobody re-checked is exactly the
unearned pass this whole method exists to prevent.

Where the prior artifacts are not a `qa-state.json` — a tracker export, a wiki, a spreadsheet — map them by
hand with `add --provenance reconstructed`, and have `/product-suite:orient` record the mapping in the
product profile so the next person does not invent a different one.

## The dashboard

```
hub.py dashboard
```

Self-contained HTML, works over `file://`, read-only, nothing authored. One page per item, a board per
type, and on the index: the computed verdict with its condition table, all items by type and state, per
role "waiting on them", the operator's queue, traceability from initiative to metric, and time-in-state
with reopen counts.

Exit code is 2 when the hub has integrity problems, so it can gate a pipeline.

**What the dashboard is for, and what it is not.** It is for seeing where work is stuck and whether a
release can be called. It is not a progress bar: there is no percent-complete anywhere, because a
percentage of unknown total is the denominatorless number `shared/principles.md` §2 forbids. If someone
wants "how far along are we", the answer is the lifecycle board and the operator's queue.

## For the lead

`list --waiting-on <ROLE>` per role is the standup, and it is generated rather than reported — nobody
describes their own status. Two queries are worth running every day: `list --type finding --state NEW`
(nobody has triaged these, and `NEW` is not a resting state) and `list --waiting-on OPERATOR` (the team
cannot unblock these at all). A third weekly: `list --type cleanup --state OPEN`, which is what is still
billing or exposed.

## Open questions

- Whether `list` needs a `--since <iteration>` filter for "what changed this round". The event log can
  answer it; the CLI does not expose it yet.
- Whether a `blocked_by` link type would be better than today's `blocks`, which reads backwards in the
  dashboard's traceability tree.
- The tracker adapter interface in `shared/scripts/dashboard.py` is an interface only. Nobody has written
  an implementation, and the comment there explains the three rules one would have to honour.

| File | Read it when |
|---|---|
| `${CLAUDE_PLUGIN_ROOT}/shared/principles.md` | First |
| `${CLAUDE_PLUGIN_ROOT}/shared/vocabulary.md` | Item types, states, roles, severities, verdicts |
| `${CLAUDE_PLUGIN_ROOT}/shared/hub/model.json` | The machine-readable lifecycles `hub.py` enforces |
