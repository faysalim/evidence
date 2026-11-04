# QA and Dev as two sessions

A QA session and the dev session that fixes what it found share no conversation, no memory and often no
machine. Everything that passes between them has to exist as an artifact on disk, or it does not exist.

That constraint is not a limitation to work around — it is the corporate arrangement, and it is better than
one session doing both. **A fix is never verified by the author of the fix.** When one session finds, fixes
and closes, the tightest evidence standard in the world is being applied by the party motivated to believe
it worked. Two sessions make that structural instead of aspirational.

What goes wrong between QA and Dev is well known and this file exists to make each one mechanically
impossible rather than culturally discouraged:

| The failure | What prevents it here |
|---|---|
| Findings that are neither accepted nor rejected; they rot | `NEW` is not a resting state. Every finding carries a triage decision with a reason |
| Dev marks it fixed; it ships broken | Dev may claim `FIXED`. Only QA may `CLOSE` |
| "Works as designed" ends the conversation | A design claim must cite documentation. If it is undocumented, that is a doc finding |
| The fix handles the reported input only | The acceptance criterion is published with the ticket, and it is a class of input, not one value |
| QA re-tests a build that does not contain the fix | The handback is rejected unless it names the build. Phase 0 then proves it independently |
| Both sessions edit one ledger and lose each other's work | Two files, one writer each, joined by finding id |

## Declare your role before anything else

Step 0 of `SKILL.md` establishes the iteration and the mandate. In a two-session engagement it also
establishes **which side of the handoff you are**, because the same skill serves both and the two roles
have opposite permissions:

```
Role:  QA  — I find, rank, verify and close. I do not write product code.
       DEV — I triage, fix and hand back. I do not grade my own fix, and I never close a finding.
```

Read it off the mandate, and if the operator has not said, ask — one question. A session that assumes it is
DEV when it is QA will start editing a repository under a report-only mandate, which is the single
unforgivable error in this method.

A DEV session reads this file and `${CLAUDE_PLUGIN_ROOT}/skills/dev/references/fix-phase.md`. Everything
in `fix-phase.md` — worktree
isolation, one finding one branch, test-first with proof it fails, deliberate exclusions — applies
unchanged. This file adds only what the second session makes necessary.

## One log per actor, and two generated views

Do not share a ledger. Two sessions writing one file lose each other's edits, and a locking
protocol between two agents that may be hours apart is a fiction. The hub's answer:

| Path | Written by | Holds |
|---|---|---|
| `<hub>/events/<ROLE>/<actor>.jsonl` | that actor, append-only | every state change, timestamped and attributed |
| `<report-dir>/qa-state.json` | **generated** | QA's compatibility view |
| `<report-dir>/fix-state.json` | **generated** | DEV's compatibility view |

**No two writers ever share a file**, so there is no lock and a git merge of two actors' work is a
concatenation rather than a conflict. State is a deterministic fold over every event, ordered by
`(ts, actor, seq)` and applied in causal order via explicit `after` links -- `ts` is advisory,
because two machines' clocks disagree and a QA session can legitimately stamp its answer before the
DEV event it answers.

**Neither side hand-writes anything.** Every change goes through
`python "${CLAUDE_PLUGIN_ROOT}/shared/scripts/hub.py"`, which refuses the transitions this contract
forbids -- so the invariants below are enforced rather than agreed. The two state files are
**generated views**: they carry a `generated_from` header with a digest of the events they were
built from, and a view that disagrees with the hub is a stale artifact, not a second opinion.
`hub.py validate` reports it; `hub.py views` regenerates it.

Keep the hub under version control if the operator has a repo for reports. The history then shows
who changed what and when, which is the audit trail a procurement review asks for and nobody can
reconstruct afterwards.

Every event carries `ts`, `actor`, `role` and the item it concerns, and `event_id` is
`<role>/<actor>#<seq>` so one person wearing two hats cannot collide with themselves. `actor` names
the agent or session, because "who ran it" is part of the evidence: a `PASS` is attributable or it
is anonymous.

**The dashboard is generated from the hub**, never authored:
`hub.py dashboard` prints the computed verdict and its condition table and writes a
self-contained local site -- the lifecycle of every finding as a QA/DEV swimlane, time-in-state,
and reopen counts. If it is not in the logs it is not on the page.

## The defect lifecycle, and who may move it

| State | Meaning | Who may set it |
|---|---|---|
| `NEW` | QA has filed it; DEV has not yet looked | QA |
| `ACCEPTED` | DEV agrees it is a defect and owns it | DEV |
| `REJECTED` | DEV says not a defect — needs a reason and, for a design claim, a citation | DEV |
| `DEFERRED` | Real, not this build — needs the build or milestone it is deferred to | DEV, with the operator |
| `DUPLICATE` | Same root cause as another id — names it | DEV |
| `IN PROGRESS` | Being worked | DEV |
| `FIXED` | DEV claims the defect is gone and has delivered a build that contains the fix | DEV |
| `VERIFIED` / `PARTIAL` / `STILL PRESENT` / `NOT IN BUILD` / `CANNOT RETEST` | QA's verdict from Phase 1 | **QA only** |
| `CLOSED` | Verified fixed, and the case that proves it passes | **QA only** |
| `REOPENED` | Was closed; fails again. Same id, never a new one | QA |

Four invariants. Each exists because its absence is a way a broken product ships:

1. **`NEW` is not a resting state.** Every finding leaves it with a decision and a reason. A finding nobody
   accepted and nobody rejected is the most common way a blocker reaches production — not disagreement,
   just silence. The handback is incomplete while any finding is still `NEW`.
2. **DEV claims, QA closes.** `FIXED` is a claim about the code; `CLOSED` is a verdict about the product.
   They are different statements made by different parties on different evidence, and collapsing them is
   what "we fixed it" means in a post-mortem.
3. **A reopen keeps its id.** A finding that fails again is the same finding, and the register must show the
   arc. A *regression* — new breakage introduced by the fix — gets a **new** id with the causal link
   in the body ("introduced by the fix for K1"). Never recycle an id, never renumber.
4. **Severity is QA's call; the business priority is the operator's.** DEV may dispute severity and that
   dispute is recorded, but DEV does not overwrite it. "Severe but not urgent" is a legitimate and common
   position, and it is the operator's to take.

## QA → DEV: the ticket packet

The finding template in `${CLAUDE_PLUGIN_ROOT}/shared/templates/finding.md` is already most of it. A
two-session handoff adds one field,
and it is the field that changes dev behaviour most:

> **Acceptance criterion.** The case id and its **oracle**, stated plainly: this is what your fix will be
> graded against, and by whom.

Publish the oracle, because a fix written against a known oracle is a fix aimed at the defect rather than
at the symptom. But state the adversarial variant as a **class of input, not a value**:

> `S5-02` will be re-run verbatim, plus one unspecified neighbour of the reported input — a different
> domain, a different case, a tag-only local part, surrounding whitespace. A fix that special-cases the
> exact reported string will be returned as `PARTIAL`.

Naming the exact neighbour invites a fix that handles that neighbour too and nothing else; naming the
class tells DEV to fix the class, which is what was wanted. It is also honest — DEV is told the standard
in advance and cannot be ambushed by it.

**But the class is withheld, not the result.** Publish the **value QA actually used** with the verdict,
after the fact. Phase 1's variant is a permanent register case with a copy-pasteable action, and a
`PARTIAL` that DEV cannot reproduce turns the status this method says matters most into an argument.
Specification first, reproducible result second.

The packet is complete when a stranger could start work from it alone: id, severity, status
(`CODE / DEPLOY / …`), the verbatim repro, build identity under which it reproduced, the environment and
topology, expected vs actual with raw evidence, **what the finding does NOT claim**, and the acceptance
criterion. Template in `${CLAUDE_PLUGIN_ROOT}/shared/contracts/handoff-packet.md`.

A `DECIDE` finding is not a ticket and must not be handed over as one. It goes to the operator as a memo
with options and a recommendation. Handing a decision to DEV as a bug is how you get an unauthorised
product change made by whoever read it first.

## DEV → QA: the handback packet

QA's Phase 0 exists because handbacks lie about which build contains what. The mechanism is to make the
handback rejectable before a single agent is briefed:

**A handback is incomplete, and QA returns it unread, if it lacks any of:**

- **The build**, per component — commit, digest or version — that QA should test. Not a branch name, not
  "latest". A branch tip moves; a digest does not.
- **A finding id QA actually issued**, for every entry. The two ledgers join on that id, and the drift is
  in the key's existence rather than its value: an id in `fix-state.json` that is absent from
  `qa-state.json`, or a `FIXED` naming a digest Phase 0 cannot find, **rejects the handback unread** exactly
  as a finding still `NEW` does. The join then self-verifies every iteration, with no shared file and no
  lock. A regression filed under the old id is the common form of this.
- **A state for every finding handed over.** None left `NEW`.
- **Per `FIXED` finding: the branch, the commit, the root cause in one sentence, and the case ids it
  claims to satisfy.**
- **The fail-first evidence** for each test added: the test, the case it automates, and confirmation it
  failed against the unfixed code. `fix-phase.md` requires this of the author; the handback is where it
  becomes checkable by someone else.
- **What was deliberately not changed, with reasons** — the exclusion classes in `fix-phase.md`. An
  unexplained omission reads as an oversight and QA will file it again.

Returning an incomplete handback is not obstruction, it is the cheapest possible intervention. The
alternative is a full verification round whose result is `NOT IN BUILD` for half the findings, which costs
the dev team another build and QA another cycle to learn something a missing field could have said.

### The case is the spec; the test is its automation

This is the load-bearing link between the two sessions, and it is what makes the register pay for itself
twice. QA's case already states an action and an **oracle**. DEV's regression test is that case, encoded:

**This link cannot rest on cooperation**, because a dev team that never read this file will still hand
back tests, and QA/Dev relations are precisely where "they promised" fails. So the link is something QA
**checks**, not something DEV **promises**:

- The handback names the automating test by case id; **Phase 0 greps the build for that test.** A named
  test absent from the artifact is `NOT IN BUILD` like any other missing claim.
- **Phase 1 runs DEV's test *and* QA's own row, and the two must agree.** A disagreement is a finding
  against the test — never a closure.
- A case is marked `automated` only once **QA has seen that test fail on the unfixed build.** That is
  `fix-phase.md`'s own fail-first rule applied to someone else's test, and it is the only form in which
  "the engagement gets cheaper each round" is not DEV's self-report.
- **Copy the oracle into the test**, verbatim, as its assertion and its docstring. A test asserting
  something weaker than the oracle passes while QA's verification fails, and that gap is pure wasted cycle.
- Assert the **output, not the setting** (`fix-phase.md`) — which is the same rule as the register's: an
  oracle that is the product's own report of itself is not an oracle.

The payoff is that the case set stops being a QA artifact and becomes the product's regression suite. A
case that DEV has automated no longer needs a human run every iteration; QA's Phase 2 selection narrows to
the cases that are not yet automated, and the engagement gets cheaper every round instead of more
expensive.

## Disputes have an outcome, not an argument

Two disputes recur, and each has a defined route:

**"Works as designed."** A design claim must cite where the design is written down — a doc page, a spec, an
ADR, a published contract. Then one of three things is true:

1. **The citation exists, the product matches it, and the operator has accepted that contract in writing**
   (source 0 — the acceptance requirements from Step 0). The finding is withdrawn by QA, in writing, under
   *Corrections*. QA was wrong; say so plainly, which is what makes the rest of the report trustworthy.
   **Without the operator's acceptance, a citation does not close it** — a doc stating a weak contract
   would otherwise close a finding while the product goes on losing acknowledged data. It converts to
   `DECIDE` **at its consequence severity**, not to a docs finding, and stays open for the verdict.
2. **The citation exists and the product does not match it.** The finding stands and gets sharper, because
   now it has a contract to violate.
3. **There is no citation.** Then the behaviour is undocumented, and the finding converts rather than
   closing: it becomes a scope 9 documentation finding against the same id. Undocumented intended behaviour
   is a real defect with a real cost — a support ticket with a long fuse — and this is the route that
   stops "it's intentional" from being unanswerable.

**Severity.** QA sets it by worst consequence; DEV may record `severity_agreed: false` with its own
proposal. Unresolved, it goes to the operator as a `DECIDE` memo with both positions and a recommendation.
It does not go to whoever writes last. In the origin engagement 11 of 37 findings were decisions, and
written as memos all 11 were answered in one message — the same mechanism works here.

## When both sessions are live at the same time

Live messaging between sessions is an optimisation, never the mechanism. Use it to say "handback is in" or
"K1's repro needs a credential you have" — short, factual, and always **after** the artifact is on disk,
never instead of it. Anything that exists only in a message is lost to the next session, to the operator,
and to the audit trail.

Two rules keep this from eroding the design: a verdict is never given in a message (it goes in the owning
file, then may be announced), and neither session asks the other to perform an action its own mandate
forbids. A QA session under report-only does not get code changed by asking DEV to make one it was not
briefed on; that is the mandate laundered through a second session, and the operator's "report only" meant
the engagement, not the session.

## When there is no DEV session

The roles collapse but the invariant does not. If you fix what you found, **the verification pass is still
a separate, cold pass**: finish the fixes, then run Phase 0 and Phase 1 against the built artifact from the
register, grading against the recorded oracle rather than against your memory of what you changed. Say in
the report that author and verifier were the same party. That sentence is a material limitation of the
evidence and the operator is entitled to know it — which is also the strongest argument for standing up the
second session next time.
