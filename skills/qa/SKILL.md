---
name: qa
description: Evidence-first end-to-end QA: prove every finding by doing the thing rather than checking that it responds, publish the test cases and the coverage denominator, and compute a bounded release verdict instead of asserting one. Use when the user wants a product, release, website, app, API, SaaS or deployment tested or QA'd; bugs found, verified or ranked before shipping; test cases or a test matrix written; or the docs checked against the product. Not for fixing what QA found - that is evidence:dev. Not for writing acceptance criteria (evidence:backlog) or authoring documentation (evidence:docs-authoring).
roles: QA
status: proven
---

# QA

A QA run is worth exactly as much as the weakest claim in it. One unverified "works fine" poisons the whole
report, because the reader can no longer tell which lines you proved and which you assumed.

Read `${CLAUDE_PLUGIN_ROOT}/shared/principles.md` first — the ten rules that hold across every skill here.
This file is the QA method on top of them. All items are created and moved **only** through
`python "${CLAUDE_PLUGIN_ROOT}/shared/scripts/hub.py"`; nothing is hand-edited.

## The prime directive

**Do the thing. Don't check that the thing responds.**

A real prior run declared **"0 bugs"** after checking status codes, page loads and link resolution. At that
moment the entire trial-key flow was broken: the issuing endpoint returned 403, the email was malformed,
there was no sales copy, and a deploy pin meant the new code was not serving. All of it was reachable in
minutes by *requesting a key*. None was reachable by *checking that the page loads*.

**Then go back and check the thing is still there.** For anything that keeps data this is only half the
directive. A write that returned OK is a *response*; the thing is the value being present — on every
replica the product promised, after the failure the docs say it survives, after the upgrade. The database
version of the "0 bugs" report is a cluster where every node is green, every write was acknowledged, and a
read-back after one restart finds tens of thousands of acknowledged keys missing.

If you cannot execute something, that is a legitimate outcome — say so in the not-verified list. An honest
gap is useful. A silent gap dressed as a pass is the thing this skill exists to prevent.

## Step 0 — Which iteration is this, then pin the mandate

**The hub is the source of truth, and reading it is your first action.** It cannot come from memory: a later
iteration usually runs in a new session, and the operator will just say "we fixed those, take another
look".

```
python "${CLAUDE_PLUGIN_ROOT}/shared/scripts/hub.py" status
```

| What you find | What it means |
|---|---|
| A hub | this is `iteration + 1` → `${CLAUDE_SKILL_DIR}/references/iteration-cycles.md` |
| No hub, but an old `qa-state.json` or prior reports | still a later iteration → `hub.py import <dir>`. Items arrive `provenance: reconstructed` and **the report says the register was reconstructed** |
| Nothing, and no prior run described | iteration 1 → `hub.py init --engagement "<product and date>"`, as your first write, before testing |
| Ambiguous — "re-test the bugs" but no register anywhere | **ask.** One question is far cheaper than a sweep that re-reports known findings as new |

The iteration number is an explicit hub event (`hub.py iteration <n>`), never inferred. A generated view
(`qa-state.json`) whose `generated_from` header does not match the hub is **not truth** — that is the
import branch, and `hub.py validate` flags it.

`status` also prints the product class and, critically, **what `/evidence:orient` could not establish** —
the environment nobody reached, the component whose build is unknown. Read that list before assuming
anyone looked. Read `<report-dir>/conventions.md` with it and **use their words and their ids**: their
severity scale, their name for a story, their existing finding ids preserved rather than renumbered. The
ten principles are the only thing here that is not theirs to set.

Then pin the mandate, in writing, into the hub profile:

- **Which role are you?** `QA` finds, ranks, verifies and closes, and writes no product code. If a separate
  session fixes what you find, read `${CLAUDE_PLUGIN_ROOT}/shared/contracts/qa-dev.md` — it defines the two
  ledgers, the lifecycle and who may move it. **You never grade your own fix.**
- **Report-only, or fix?** If fix, the delivery mode. Default to the least irreversible option and confirm.
- **What is out of bounds?** Deploys, merges, production config, and destructive operations against state
  you did not create. **Destructive is defined by whose state it destroys, not by the verb.** Killing a
  node, partitioning a network or wiping a device in an environment *you stood up, with data you
  generated* is testing — and for a stateful product it is the only testing that matters. Establish in
  writing which environments are yours to break, and put that answer in every brief.
- **What must be true for this release to ship?** The operator's **acceptance requirements** — SLAs,
  contractual guarantees, regulatory obligations — each as a sentence that can fail. These become cases
  *ahead of* the domain file, because a product can be green against its own docs and red against the
  purchase order. Where the operator has none, the verdict says green is against the docs only.
- **Which credentials, and which tenant?** Test tenant tokens only, never production. Values live where
  `shared/principles.md` §8 says; you are told the role and the path, never the value.
- **Any time bombs?** Products that self-destruct, self-obfuscate, consume seats or bill per hour. Ask
  directly: "is there anything that breaks if I build, activate or run it?"
- **Who pays for infrastructure you spin up?** Open the cleanup ledger at minute one (Step 7), as `cleanup`
  items in the hub — not at the end when you have forgotten half of it.

## Step 1 — Establish ground truth before you test against it

This produces more real findings per minute than any other step, and skipping it makes findings
unclassifiable. The question is not "does the code do the right thing" but **"which code is actually
serving, and is it the code I am reading?"**

| What to establish | How, and why it bites |
|---|---|
| Which branch actually deploys | Read the hosting config, not the repo default. One repo's `master` was **a month stale** while the live line was `release/2.5.0` |
| Which build is live | A version endpoint, image digest, or a string you can grep in the served asset. Record the commit delta |
| Docs vs code | Grep the identifier the docs tell customers to use against what the code reads. A blocker came from exactly this: the site said one variable name, the service read another, and `/health` returned `200 {"status":"ok"}` throughout |
| Published artifact vs its own branch | A `2.5.0` image predated its own `release/2.5.0` tip. Tags lie; digests and greppable strings do not |

Then classify each finding by **what action actually closes it** — the taxonomy is in
`${CLAUDE_PLUGIN_ROOT}/shared/vocabulary.md`. A report that says "22 bugs" when nine are deploy lag and two
need a certificate has told the operator nothing about what to do on Monday.

## Step 2 — Split the scopes

Scope by **surface the user touches**, not by repository, because a single customer journey crosses repos
and the defects live in the seams. **So the seams get owners:** the journeys in
`${CLAUDE_SKILL_DIR}/references/test-cases.md` (source 7) are cases in their own right, each run end to end
by one actor with no operator-supplied shortcut at any step. The origin engagement's trial flow was broken
while every individual surface on it passed.

Twelve families: 1. Acquisition surface · 2. Primary product, per platform · 3. Control plane ·
4. Deployment · 5. Entitlement lifecycle · 6. Secondary products and SDKs · 7. Telemetry & privacy ·
8. Security & abuse, **with performance, capacity and degradation (8b)** · 9. Documentation conformance ·
**10. State: correctness and durability under fault, time and concurrency** · **11. Upgrade, migration and
rollback** · **12. Experience & diagnosability**

Which apply is decided **provisionally in Step 0 and re-confirmed after Step 1**, because the hosting
config and the route table are where a "stateless" surface turns out to write to a CRM — one marketing
site's lead POST was the only fulfilment trigger for a product and ended in `.catch(() => {})`. Any agent
may contest an `N/A` with a one-line observation; the lead answers it in the index. Inapplicable families
are listed as N/A with one line of reasoning, so a reader sees the omission was chosen rather than missed.

`${CLAUDE_SKILL_DIR}/references/scope-playbooks.md` has the playbook per family and what extra agents buy.
`${CLAUDE_PLUGIN_ROOT}/shared/domains/` maps the families onto thirty-one product classes. **Read the
closest one before briefing, and every file that applies when the product is two things at once** — take
the union of the fault catalogues and reconcile the scope maps once.

Brief each scope from `${CLAUDE_SKILL_DIR}/assets/agent-brief.md`. An agent given a scope but no context
reports that the page loads; an agent not told which phase it is in sweeps when it should be verifying.

**Agent budget: one agent per applicable family, 11 as the default ceiling.** An agent is added only for a
named journey, a fault-class split, or an un-merge whose coverage loss is named — never for breadth. Every
agent in the run is named in the index with its family, fault class or journey; an agent with none is
unaccountable. Long-running work is a background job the lead starts and reads back, never an agent idling
on a 12-hour wait.

## Step 3 — Design the cases first, then test by doing

**Generate the case set; do not invent it.** The suite ships **744 enumerable case candidates** across
its 31 domain files — every condition in each `## Failure catalogue` and every entry in each
`## Defect classes to look for by name`. Enumerate them rather than remembering them:

```
hub.py catalogue <domain>                                      # what it names, numbered
hub.py catalogue <domain> --as-commands --scope <s> --prefix S1 # ready to run, one per condition
```

`desktop-app` alone yields 29. Four domains for one product yielded **103 before a single line of
the product's own surface was considered.** An engagement that worked from memory wrote 50 cases for
a whole product and every check in this suite passed, because nothing counted what it owed.

**`hub.py status` now reports the case set against a floor** computed from the capability inventory
plus those catalogue conditions. It is a floor, not a target, and it is the engagement's own
arithmetic — argue with it by changing the inventory, not by ignoring it.

`${CLAUDE_SKILL_DIR}/references/test-cases.md` carries the row fields, the nine derivation sources and the
honesty rules. Four things must survive any summary of it:

- **A case is an action, an oracle, a result and its evidence**, and the oracle rule from
  `shared/principles.md` §3 applies: the product's own report of itself is not an oracle, and the
  independent thing must predate the run.
- **A `PASS` with no evidence is a `NOT RUN`.** `NOT RUN` and `BLOCKED` are first-class results; in an
  honest run they are not zero, and they are ordered by the severity of the class each guards.
- **Each scope's finalized case set is its first deliverable, and it is a gate** — the method's only entry
  criterion. A list alone does not satisfy it: the scope's **smoke** row and its **calibration** row run
  before any other, and **a scope whose calibration did not run has no `PASS` rows.** A harness that has
  never failed has never been shown to work. Two real durability certifications passed with harnesses that
  could not have detected a loss.
- **Cases are derived, not invented**, and the derivation is published with the count. The set is closed to
  deletion and open to addition: `derived` before execution, `discovered` during it, nothing deleted.

Then read `${CLAUDE_PLUGIN_ROOT}/shared/references/evidence-standard.md` before the first finding. It
defines, per surface, what counts as proof. The short version: **drive the built output, not the source** ·
**prove a negative through its positive** · **count, don't infer** · **change exactly one variable** ·
**read the artifact's own metadata**.

### Test the documentation, in both directions

The docs are the contract, and a customer's first run is the documented path — so a documented path that
fails is a blocker regardless of how correct the product is underneath. No other scope finds this.
`${CLAUDE_PLUGIN_ROOT}/shared/references/docs-conformance.md` is the playbook.

- **Forward:** extract every executable claim and run it **verbatim**, copy-pasted rather than paraphrased.
  Paraphrasing silently repairs the doc's bug in your head.
- **Reverse:** enumerate what the product exposes *from the code* — route table, every environment-variable
  read, the option parser, the config schema — and subtract what is documented. The remainder is
  undocumented surface, and nothing else finds it.

Report both numbers with their denominators and how you enumerated them. Claims you could not exercise stay
in the denominator as `BLOCKED` rows; dropping them is how a coverage number becomes a lie.

## Step 4 — Write each finding as you find it

`${CLAUDE_PLUGIN_ROOT}/shared/templates/finding.md`, filed as a `finding` item in the hub. The parts people
skip: **expected vs actual with evidence inline** so the reader can re-run you · **"what this finding does
NOT claim"** · **severity by consequence, not by effort** · and the **acceptance criterion**, which names
the case and oracle a fix will be graded against, with the adversarial variant published as a *class of
input, not a value*.

### Experience is half the product

A correct product with a bad experience fails anyway, and it fails quietly — nobody files a bug saying "I
gave up". `${CLAUDE_PLUGIN_ROOT}/shared/references/experience.md` is the playbook. The discipline that
belongs here: **a usability finding has to be as provable as a correctness finding**, or it gets answered
with "that's subjective" and the whole section becomes decoration. Four kinds of evidence, strongest first:
the product **already does it right somewhere else** · a **blocked or abandoned goal**, stated as a goal · a
**measurement** · a **convention violation with a named cost**. Aesthetic preference with no nameable cost
is polish.

One measurement is perishable: **time and steps to first success**, with every guess, backtrack and doc
round-trip, taken before you read more than a customer would. You get exactly one genuine first encounter.
It belongs to **whoever arrives at a surface first** — a freshly briefed scope agent is **agent-cold**, not
a genuine first-time user, and says so in the trace. The trace is **exempt from the case gate and precedes
it**; an agent that has just read a fault catalogue is no longer discovering anything. In a solo run the
step order genuinely conflicts, so take the primary surface's first run immediately after the Step 0 safety
questions and before Step 1, or label the trace warm and say which.

For operator-facing products the sibling measurement matters more: **time to diagnose**. Every fault run in
scope 10 supplies it free — inject the fault, then time how long until someone reading only the product's
own output could name the condition and the action.

## Step 5 — Rank, consolidate, and compute the verdict

One ranked index, most severe first, product bugs separated from usability, each row carrying a Step 1
status. Template in `${CLAUDE_SKILL_DIR}/assets/ranked-index.md`. De-duplicate by **root cause**, not
symptom: "any unrecognised argument launches the GUI and never exits" was reported by two agents against
two products and is one finding.

**The verdict is computed, never written, and `NO VERDICT` is the default** — `hub.py dashboard` computes it
from the register so the reader is not left inferring one from an empty blocker table. Every condition names
the rows that satisfy it, and the green states its bounds and what it does not cover. See
`shared/principles.md` §6.

Every `FAIL` case names its finding. The reverse is not required — a finding stumbled on while doing
something else is legitimate — but **back-fill it as a case**, or the next iteration cannot regress it.

## Step 6 — Correct yourself in writing

When fresh access disproves something you already reported, the correction goes in the report under its own
heading. Say plainly which part was right and which was wrong. It is usually the most-read section, and it
is what tells a reader the rest can be trusted.

## Step 7 — The cleanup ledger

Every account, key, container, worktree and shared quota you touched, as `cleanup` items, ordered by what is
billing or exposed **now**. **Verify teardown by re-listing**, not by trusting a delete call's exit code.

## Later iterations

A second run is not a second first run. `${CLAUDE_SKILL_DIR}/references/iteration-cycles.md` has the detail;
the shape is unchanged:

```
Case review               — update the denominator first; the set only ever grows
Phase 0  Build identity   — does this build actually contain the fixes?
Phase 0b Build serves     — one smoke row per component; a FAIL here briefs nobody
Phase 1  Fix verification — original repro verbatim, plus one adversarial variant
Phase 2  Regression       — scoped by the blast radius of the diff
── GATE ── every fix verified AND regression clean?
Phase 3  Full sweep       — only past the gate
```

**Phase 0 is not optional.** Verifying a fix against a build that does not contain it produces a false
FAIL, and the team then re-fixes working code. **The gate is strict:** a `PARTIAL` — reported repro passes,
adversarial variant still fails — does not pass it. When it fails, stop and deliver a short turnaround
document. Phases 0–2 cost a fraction of a sweep; that asymmetry is the whole design.

## For the lead

Reconcile the case sets across scopes before execution, not after: two domain files that each claim family
8 get one family-8 agent briefed from both, never two. Re-run **three `PASS` rows per agent**, highest
severity ceiling first — the register is otherwise each agent's report of itself, which by §3 is not an
oracle. A disagreement is a finding about the harness and downgrades that scope to uncalibrated.

## Files

| File | Read it when |
|---|---|
| `${CLAUDE_PLUGIN_ROOT}/shared/principles.md` | First. The ten rules every skill shares |
| `${CLAUDE_PLUGIN_ROOT}/shared/vocabulary.md` | Severity, closing actions, states, roles, case results, verdicts |
| `${CLAUDE_PLUGIN_ROOT}/shared/references/evidence-standard.md` | Before the first finding. What counts as proof, per surface |
| `${CLAUDE_SKILL_DIR}/references/scope-playbooks.md` | Splitting scopes. The twelve families, with steps |
| `${CLAUDE_SKILL_DIR}/references/test-cases.md` | Step 3, before running anything |
| `${CLAUDE_SKILL_DIR}/assets/test-case-register.md` | The register itself — the run's denominator |
| `${CLAUDE_PLUGIN_ROOT}/shared/contracts/handoff-packet.md` | Writing the ticket packet for a dev session |
| `${CLAUDE_PLUGIN_ROOT}/shared/domains/` | **First, every time.** Thirty-one product classes |
| `${CLAUDE_PLUGIN_ROOT}/shared/references/docs-conformance.md` | Scope 9, both directions |
| `${CLAUDE_SKILL_DIR}/references/iteration-cycles.md` | Any iteration after the first |
| `${CLAUDE_PLUGIN_ROOT}/shared/contracts/qa-dev.md` | A separate session fixes what you found |
| `${CLAUDE_PLUGIN_ROOT}/shared/references/gotchas.md` · `${CLAUDE_SKILL_DIR}/references/gotchas-testing.md` | Before heavy local work. Traps that each cost a cycle |
| `${CLAUDE_SKILL_DIR}/references/case-file.md` | A worked engagement with real numbers |
| `${CLAUDE_PLUGIN_ROOT}/shared/scripts/safe_edit.py` | Any scripted edit. Validates every anchor against the original; `--check` dry-runs |
