---
name: product-qa
description: Evidence-first end-to-end QA of a real product: prove every finding by doing the thing rather than checking that it responds, publish the test cases and the coverage denominator, and compute a bounded release verdict instead of asserting one. Use whenever the user wants a product, release, website, app, API, SaaS or deployment tested or QA'd; wants bugs found, verified or ranked before shipping; wants test cases, a test plan or a test matrix written; wants the docs checked against what the product really does; mentions QA agents or a multi-agent test sweep; wants a findings or bug report written up; or asks to fix, triage or hand back what a QA run found. Use it even for "test my product", "check everything works", "give it a full QA pass" or "find what's broken". Not for a single function or a unit-test question - that is ordinary debugging.
---

# Product QA

A QA run is worth exactly as much as the weakest claim in it. One unverified "works fine" poisons the
whole report, because the reader can no longer tell which lines you proved and which you assumed. This
skill exists to make every line provable.

## The prime directive

**Do the thing. Don't check that the thing responds.**

This is not a stylistic preference — it is the single failure mode that makes QA worthless. A real prior
run on a real business declared **"0 bugs"** after checking HTTP status codes, page loads and link
resolution. At that moment the entire trial-key flow was broken: the issuing endpoint returned 403, the
email was plain-text and mis-branded, there was no sales copy at all, and a deploy pin meant the new code
was not even serving. Every one of those was reachable in minutes by *requesting a key*. None was
reachable by *checking that the page loads*.

So: request the real key. Activate the real licence. Run the real binary. Submit the real form and read
the real email. Decompile with the real tool. Deploy the real image. **Status 200 is not a passing test.**
A green build is not a passing test either — see `references/gotchas.md`, where a green build shipped a JS
syntax error that made a form do nothing at all.

**Then go back and check the thing is still there.** For anything that keeps data, the sentence above is
only half the directive. A write that returned OK is a *response*; the thing is the value being present —
on every replica the product promised, after the failure the docs say it survives, after the upgrade, a
week later. The database version of the "0 bugs" report is a cluster where every node is green, every
write was acknowledged, and a read-back after one node restart finds tens of thousands of acknowledged
keys missing. The pipeline version is three weeks of green scheduler runs over a sink that has been
receiving NULLs since the source added a column. The CRM version is a role matrix that is correct on the
settings page and an export containing the records that role cannot see. None of those is reachable by
exercising the request. All of them are reachable by exercising the request *and then measuring the state
it was supposed to produce, graded against your own record of what the product acknowledged — never
against the product's own counters.* An acknowledged write is not a durable write until you have read it
back after the failure.

If you cannot execute something, that is a legitimate outcome — say so explicitly in the not-verified
list. An honest gap is useful. A silent gap dressed as a pass is the thing this skill is built to prevent.

## Step 0 — Find out which iteration this is, then pin the mandate

**Before anything else, establish whether this is a first run or a later one**, because the answer changes
the entire shape of the work — a later iteration starts with verification and regression behind a gate,
not with a sweep. It cannot come from memory: later iterations usually run in a new session, and the
operator will often just say "we fixed those, take another look".

Read it off disk. Look for `<report-dir>/qa-state.json`; ask where reports live rather than assuming the
working directory. Found it → this is `iteration + 1`, go to `references/iteration-cycles.md`. Prior
report files but no state file → still a later iteration; reconstruct the register from them and say that
you did. Nothing at all and no prior run described → iteration 1, and write `qa-state.json` before you
start testing so an interrupted run is resumable. Genuinely ambiguous → ask; one question is far cheaper
than a sweep that re-reports known findings as new.

Then pin the mandate:

Ambiguity here is expensive in both directions: fixing under a report-only mandate is unforgivable, and
reporting a one-line fix you were authorised to make wastes the operator's time. Establish, in writing:

- **Which role are you?** If a separate dev session or team fixes what this run finds, say which side you
  are on, because the two have opposite permissions: `QA` finds, ranks, verifies and closes, and writes no
  product code; `DEV` triages, fixes and hands back, and **never closes a finding or grades its own fix**.
  A session that assumes it is `DEV` when it is `QA` starts editing a repository under a report-only
  mandate, which is the one unforgivable error here. Not stated → ask. Then read
  `references/dev-handoff.md`, which defines the ledger each side owns, the defect lifecycle and who may
  move it, and how a dispute resolves instead of continuing.
- **Report-only, or fix?** If fix, what is the delivery mode — pushed branches, PRs, commits in place?
  Default to the least irreversible option available and confirm it.
- **What is out of bounds?** Deploys, merges, production config, and any destructive operation against
  state you did not create. **Destructive is defined by whose state it destroys, not by the verb.** Killing
  a node, partitioning a network, dropping a table or wiping a device in an environment *you stood up, with
  data you generated* is testing — and for a stateful product it is the only testing that matters.
  Revoking a real licence, deleting a production row or restarting a shared cluster is not. Establish in
  writing which environments are yours to break, and put that answer in every brief.
- **What must be true for this release to ship?** Get the operator's **acceptance requirements** in
  writing — SLAs, contractual guarantees, regulatory obligations, the release's own exit criteria —
  each as a sentence that can fail. These become cases *ahead of* the domain file (`references/test-cases.md`,
  source 0), because a product can be green against its own documentation and red against the purchase
  order: docs promising "survives loss of a single node" are satisfied by a single-node kill while a
  contractual RPO of zero across an availability zone was never a case. Where the operator has none, say so
  in the verdict — green is then green against the docs only.
- **Which credentials, and which tenant?** Admin and licensing APIs get a *test* tenant's token, never a
  production one. Ask for what you need; if it does not arrive, state the blocked test rather than
  improvising around it. **If any test environment is seeded from production data, that data is production
  data**: no copying it out, no pasting it into a provider, and it goes in the cleanup ledger.
- **Where do the credential values live?** Real values go in one gitignored directory — `.qa-secrets/` by
  convention — referenced from briefs and reports **by role only** ("the test tenant's admin token"). An
  agent is told the role and the path, never the value, because a value in a brief is a value in a
  transcript and in every report that quotes it. The directory goes in the cleanup ledger as plaintext
  credentials, which is the second thing the ledger is ordered by.
- **Any time bombs?** Products that self-destruct, self-obfuscate, consume seats, or bill per hour. Ask
  directly: "is there anything that breaks if I build, activate or run it?" The prior run surfaced a
  self-obfuscating Release build that bakes a self-destruct when built under a trial licence — producing a
  distributable would have shipped a bomb to customers.
- **Who pays for infrastructure you spin up?** If you start cloud resources, you own the teardown. Open
  the cleanup ledger at minute one (Step 7), not at the end when you have forgotten half of it.

Exercising flows with test data you create is testing. Injecting faults into, scaling, upgrading or wiping
an environment you created is testing. Changing the product's code, or the deployment customers use, is
fixing. When genuinely unsure which side of that line something sits on, document it instead of doing it.

## Step 1 — Establish ground truth before you test against it

This step produces more real findings per minute than any other, and skipping it makes findings
unclassifiable. The question is not "does the code do the right thing" but **"which code is actually
serving, and is it the code I am reading?"**

Build this table before writing a single finding:

| What to establish | How, and why it bites |
|---|---|
| Which branch actually deploys | Read the hosting config, not the repo's default branch. One repo's `master` was **a month stale** while the live line was `release/2.5.0`; a fix worktree was created from the wrong one and caught only just before editing. |
| Which build is live | A version endpoint, image digest, or a string you can grep in the served asset. Compare to the branch tip and record the commit delta. |
| Docs vs code | Grep the identifier the docs tell customers to use against what the code actually reads. A blocker came from exactly this: the site said `KEYRIGHT_LICENSE`, the service read `KEYRIGHT_SELF_LICENSE`, and `/health` returned `200 {"status":"ok"}` throughout — so every uptime check was green on an instance that could not issue a single licence. |
| Published artifact vs its own branch | A `2.5.0` image predated its own `release/2.5.0` tip. Tags lie; digests and greppable strings do not. |

Then classify each finding by **what action actually closes it**, because "bug" collapses the distinction
the operator needs to plan:

- `CODE` — the code is wrong. Closing it is a diff.
- `DEPLOY` — the code is right, production is behind. Closing it is a deploy.
- `RELEASE` — needs a build or publish action (a stale bundle, an unbuilt tag).
- `DATA` — a production data operation (duplicate rows, orphaned records).
- `PROCURE` — needs a certificate, licence or account nobody has yet.
- `DECIDE` — intentional-but-arguable. Write it as a decision memo with options and a recommendation, not
  as a bug. Operators answer memos; they argue with bug reports.
- `INVESTIGATE` — real symptom, root cause not established. Say so; never guess in a status column.

A report that says "22 bugs" when nine are deploy lag and two need a certificate has told the operator
nothing about what to do on Monday.

## Step 2 — Split the scopes

Scope by **surface the user touches**, not by repository, because a single customer journey crosses repos
and the defects live in the seams. **So the seams get owners**: the journeys in `references/test-cases.md`
(source 7) are cases in their own right, each run end to end by one actor with no operator-supplied
shortcut at any step. This is what a spare agent buys before any family is un-merged — the origin
engagement's trial flow was broken while every individual surface on it passed.

There are twelve scope *families*. Which apply is decided **provisionally in Step 0 and re-confirmed after
Step 1**, because the hosting config and the route table are where a "stateless" surface turns out to write
to a CRM — one marketing site's lead POST was the only fulfilment trigger for a product and ended in
`.catch(() => {})`, which is a durability defect on a surface declared N/A for durability. Any agent may
contest an `N/A` with a one-line observation, and the lead answers it in the index. Inapplicable families
are listed as N/A with one line of reasoning, so a reader can see the omission was chosen rather than
missed.

1. Acquisition surface (website, store listing, funnel) · 2. Primary product, per platform or device ·
3. Control plane (SaaS, console, admin / management API) · 4. Deployment (container, Helm, cluster,
install) · 5. Entitlement lifecycle · 6. Secondary products, SDKs, compatibility layers ·
7. Telemetry & privacy · 8. Security & abuse, **with performance, capacity and degradation (8b)** ·
9. Documentation conformance ·
**10. State: correctness and durability under fault, time and concurrency** ·
**11. Upgrade, migration and rollback** · **12. Experience & diagnosability**

`references/scope-playbooks.md` has the generic playbook per family. `references/domains/` maps the
families onto twenty-seven product classes, grouped in its README as data and state, applications,
education, money and commerce, and platform and infrastructure — each file carrying that domain's
version of "do the thing", its fault catalogue, the evidence it needs, and its severity notes. **Read the
closest one before briefing, and read
every file that applies when the product is two things at once** — a SaaS CRM, an API-fronted licensing
platform, an AI tutor inside a school platform. Take the union of the fault catalogues and reconcile the
scope maps once against the cap. If none is close, say so in the report, work from the families, and write
the missing file afterwards.

Run them in parallel when subagents are available **and the user has actually asked for a multi-agent
sweep**; otherwise work the scopes yourself in severity-likelihood order. Either way, brief each scope
from `assets/agent-brief.md` — business context, playbook, evidence standard, safety rules, and (after
iteration 1) the round, the phase and that scope's open findings. An agent given a scope but no context
reports that the page loads; an agent not told which phase it is in will sweep when it should be
verifying.

**Agent budget: one agent per *applicable* scope family, 11 as the default ceiling.** The cap is on agents,
not on families, and it is a budget rather than a boundary — but **an agent is added only for a named
journey, a fault-class split, or an un-merge whose coverage loss is named; never for breadth.** Three rules
keep it honest as scopes grow: inapplicable families cost zero agents and are listed as N/A rather than
silently absent; long-running runs (a durability certification, a backfill, a device-matrix sweep) are
background jobs the lead starts and reads back — never an agent sitting idle on a 12-hour wait, which is
billed and holds a slot a scope needs; and **every agent in the run is named in the index with its family,
fault class or journey — an agent with none is unaccountable.** Each domain file declares its usual
applicable set and default merges; `references/scope-playbooks.md` says what the next three agents buy, in
order, when the ceiling is raised.

Name up front every platform × scope cell you cannot execute on this machine. That list is a deliverable,
not an apology.

## Step 3 — Design the cases, then test by doing

### Design the cases first, and publish the register

A report of findings alone tells the reader what broke and nothing about what held, so they cannot tell a
surface that was exercised hard from one nobody opened. This skill refuses a documentation-coverage number
without its denominator; **the register is that rule applied to the whole run**, and it is what makes a
multi-agent sweep auditable rather than a pile of opinions. `references/test-cases.md` carries the field
list, the eight derivation sources and the honesty rules; `assets/test-case-register.md` is the template.
Four things must survive any summary of it:

- **A case is an action, an oracle, a result and its evidence — and a case whose oracle is the product's
  own report of itself is not a case.** `/health: ok`, a green build and the cluster's own `missing: 0`
  grade nothing. The oracle must **predate the run and exist outside both the product and your own
  judgement**: the operator's price list, your ledger written at ack time, the published spec, a count.
  "Looks right" names no reference and is not an oracle.
- **A `PASS` with no evidence is a `NOT RUN`**, and is recorded as one. `NOT RUN` and `BLOCKED` are
  first-class results; in an honest run they are not zero, and they are ordered by the severity of the
  class each one guards, not by scope.
- **Each scope's finalized case set is its first deliverable, and it is a gate** — the method's only entry
  criterion, since everything else here gates an exit. A list alone does not satisfy it: the scope's smoke
  row and its **calibration row** run before any other, and **a scope whose calibration did not run has no
  `PASS` rows.** A harness that has never failed has never been shown to work.
- **Cases are derived, not invented**, and the derivation is published with the count, because a bare count
  is a boast. The set is then closed to deletion and open to addition — `derived` before execution,
  `discovered` during it, and nothing is ever deleted.

Read the matching `references/domains/` file first — it names this product class's fault catalogue and its
defect classes, and an unnamed defect class is one nobody looks for. Then read
`references/evidence-standard.md` before the first finding. It defines, per surface — web page, CLI,
GUI binary, HTTP API, email, container, telemetry, decompiler — what counts as proof and what is merely
suggestive. The short version:

- **Drive the built output, not the source.** Build it, then exercise the artifact a user actually receives.
- **Prove a negative through its positive.** "No stale price remains" means grepping the rendered output
  for the old string and showing zero hits — not reading the template and believing it.
- **Count, don't infer.** Retry logic is proved by counting network attempts, not by reading the code.
- **Change exactly one variable.** The env-var blocker was proved by three runs of the same image with
  only the variable's name different.
- **Read the artifact's own metadata.** PE/Mach-O company and version strings, signatures, zip contents,
  checksums. Those are facts; release notes are claims.

### Test the documentation, in both directions

The docs are the contract, and a customer's first run is the documented path — so a documented path that
fails is a blocker regardless of how correct the product is underneath. No other scope finds this, because
an agent testing the product the way the product wants to be used never discovers that the docs say
something else.

`references/docs-conformance.md` is the playbook. The irreducible part:

- **Forward (docs → product):** extract every executable claim — each command, endpoint and payload,
  environment variable, config key and default, flag, stated limit, version, platform list and price —
  and run it **verbatim**, copy-pasted rather than paraphrased. Paraphrasing silently repairs the doc's
  bug in your head: you supply the parameter the example omits.
- **Reverse (product → docs):** enumerate what the product actually exposes *from the code* — route
  table, every environment-variable read, the option parser, the config schema — and subtract what is
  documented. The remainder is undocumented surface. Nothing else finds it, and an undocumented
  environment variable is a support ticket with a long fuse.

Report both numbers with their denominators and how you enumerated them. **"100% coverage" with no stated
denominator is the same empty claim as "0 bugs"** — it sounds like a result and carries no information.
With the denominator stated it is strong and checkable, and a reader who disagrees with your enumeration
can say so, which is the point. Claims you could not exercise stay in the denominator as `BLOCKED` rows;
dropping them is how a coverage number becomes a lie.

## Step 4 — Write each finding as you find it

Use `assets/finding.md`. The parts people skip, and why they matter:

- **Expected vs actual, with evidence inline.** The reader must be able to re-run you.
- **"What this finding does NOT claim."** Often the most valuable line in a report. A privacy finding
  proved that customer PII was POSTed to a host branded "telemetry" — directly observable — while
  explicitly *not* claiming the PII landed in the usage store, because establishing that needed a read key
  nobody had supplied. Stating the boundary is what made the claim trustworthy instead of merely alarming.
- **Severity by consequence, not by effort.** A one-line fix can be a blocker. Stale structured data that
  undercut real prices by up to 45% was a blocker because search engines publish it as the offer.
- **No secrets, ever.** Refer to them by role: "the test tenant's admin token". This holds in scratch files
  too — reports get forwarded.

### Experience is half the product

A correct product with a bad experience fails anyway, and it fails quietly — nobody files a bug saying "I
gave up". `references/experience.md` is the playbook; the part that belongs here is the discipline, because
this skill refuses a coverage number without its denominator and has to hold itself to the same standard.

**A usability finding has to be as provable as a correctness finding**, or it gets answered with "that's
subjective" and the whole usability section becomes decoration. Four kinds of evidence, strongest first:
the product **already does it right somewhere else** (which removes taste from the argument entirely — it
is the product's own two surfaces disagreeing); a **blocked or abandoned goal**, stated as a goal; a
**measurement** — time, steps, doc round-trips, recovery attempts; or a **convention violation with a
named cost**. Aesthetic preference with no nameable cost is polish, and padding the section with it is
what teaches people to ignore the section.

One measurement is perishable and has to be taken first, before you read more than a customer would —
which for an infrastructure product means the quickstart and nothing else — or ask the operator anything:
**time and steps to first success**, with every guess, backtrack, dead end and doc round-trip, and the
point where you would have given up if you were not being paid to continue. You get exactly one genuine
first encounter with a product. It is also a regression baseline — a rising time-to-first-success after a
fix is a finding that no correctness test can see.

Because it is perishable, the trace belongs to **whoever arrives at a surface first**, not to a dedicated
experience agent who would be warm by definition. A freshly briefed scope agent is **agent-cold** — not a
genuine first-time user, since any model knows a well-known product class before it arrives, but the
coldest party available; prefer a human where one is. The lead, warm from Step 1's hosting config and code
greps, is not even that. So in a parallel sweep every scope captures its own first-run trace and error
inventory on first contact and returns them to family 12's owner, who holds the baseline across iterations
and runs the deliberate audits. In a solo run the ordering is a real conflict: Step 0 asks the operator
several questions and Step 1 greps the
hosting config, so a solo run that follows the steps in order can never be cold. Resolve it explicitly —
**take the primary surface's first run immediately after the Step 0 safety questions and before Step 1**,
or label the trace warm and say which. Do not leave it implied.

**The trace is exempt from the case gate and precedes it.** On first contact the agent takes it with the
quickstart only, records it as a row (oracle: time, steps and exits against the docs' own claimed
duration), and *then* reads the domain file and finalizes its set. That order is the only one in which the
trace is cold at all — an agent that has just read a fault catalogue is no longer discovering anything.

For operator-facing products the sibling measurement matters more: **time to diagnose**. Every fault run
in scope 10 supplies it for free — inject the fault, then time how long until someone reading only the
product's own output could name the condition and the action. "Never, the condition was invisible until
reconciliation" is a usability blocker that is also an outage.

## Step 5 — Rank, de-duplicate, consolidate

One ranked index, most severe first, product bugs separated from usability, each row carrying a Step 1
status and a pointer to the per-scope detail. Template in `assets/ranked-index.md`. It also carries the
register's totals with their derivation and the `NOT RUN` list, because the operator plans from the index
and "what we did not test" belongs where it will actually be read.

### The verdict is computed, never written

The report's headline is a verdict, and `NO VERDICT` is the legal default. Without one the reader computes
a verdict themselves from an empty blocker table, which is the "0 bugs" report with better typography — a
run can show ten agents, 180 cases and zero blockers while the one row that would have caught a
cross-tenant data leak sits `BLOCKED` at the bottom because a second tenant was never provisioned.

So `GREEN within stated bounds` is **computed from the register**, and every condition must name the rows
that satisfy it: no open `critical` or `blocker`, including any held at `DECIDE` · every defect class the
applicable domain files mark `critical` or `blocker` has at least one `PASS` case **in a scope whose
calibration row passed** · no unreconciled `LONG` row · no `BLOCKED` or `NOT RUN` row guarding a
`critical` class · build identity established per component and unchanged since the last case ran · the
smoke row passed on the build and environment the verdict names. Any condition without rows → `NO VERDICT`,
and the first line of the report says which one failed.

The verdict is also **bounded in writing**: the digests, topology, tenant shape and dataset size it covers,
and a "what this does not cover" block — *scope 8 was one hour of a bored attacker, not a penetration
test* — because an unbounded green is the claim this skill exists to prevent. Template in
`assets/ranked-index.md`.

Every `FAIL` case names its finding. The reverse is not required — a finding stumbled on while doing
something else is legitimate, and exploratory testing finds what case design cannot imagine — but
**back-fill it as a case**, or the next iteration has no way to regress it. Cases are never de-duplicated;
findings are.

De-duplicate by **root cause**, not symptom. "Any unrecognised argument launches the GUI and never exits"
was reported independently by the Windows agent and the macOS agent against two different products. It is
one finding affecting two products cross-platform. Filing it twice would have doubled the apparent count
while halving its apparent severity.

## Step 6 — Correct yourself in writing

When fresh access — code, a key, a working deployment — disproves something you already reported, the
correction goes into the report under its own heading. This is not self-flagellation; it is the mechanism
that keeps the rest of the document trustworthy, and it is usually the most-read section.

The prior run's corrections included: the repo's default branch was not the development line; a finding
blamed on an unmerged PR was in fact merged and merely undeployed; a root cause cited by byte offset would
have sent a fixer to the wrong file; and one finding's arithmetic claim was **overstated and was withdrawn
before anything was changed**. A later session also corrected its own grouping — it had written off three
decompiler defects as "all upstream, not fixable in our code", and one turned out to be a single wrong
line in the product itself.

Say plainly which part was right and which was wrong. "That was right for G8 and wrong for G2" is worth
more than a paragraph of hedging.

## Step 7 — The cleanup ledger

Everything you create goes in a running ledger: cloud resources, test tenants, licence keys, production
rows, scratch repos, local worktrees, files holding credentials. For each, record who can remove it and
whether it costs money or stays exposed until they do.

Order the ledger by what is billing or exposed *now*: cloud compute first, plaintext credentials second,
cosmetic leftovers last. Verify teardown by **re-listing** the resources, not by trusting a delete call's
exit code — a final sweep printing `billable instances: NONE` is the deliverable; "I ran the terminate
command" is not.

## Later iterations: re-test, regress, then sweep

A second iteration — findings went to the team, a build came back — answers three questions in a fixed
order, and running them out of order wastes the budget. `references/iteration-cycles.md` has the detail.
The shape:

```
Case review                 — update the denominator first; the set only ever grows
Phase 0  Build identity     — does this build actually contain the fixes?
Phase 1  Fix verification   — original repro verbatim, plus one adversarial variant
Phase 2  Regression         — scoped by the blast radius of the diff
── GATE ── every fix verified AND regression clean?
Phase 3  Full sweep         — only past the gate
```

**Phase 0 is not optional.** Verifying a fix against a build that does not contain it produces a false
FAIL, and the team then re-fixes working code. Prove the fix's bytes are present — compare commits or
digests, or grep the artifact for a string the fix introduced — before testing it. Both failure directions
really happened: a merged fix absent from the serving image, and a published `2.5.0` image that predated
its own `release/2.5.0` tip.

**The gate is strict.** A too-narrow fix (`PARTIAL`: the reported repro passes, the adversarial variant
still fails) does not pass it. When the gate fails, stop and deliver a short turnaround document — build
identity, per-finding status, regressions with repros, what the next build needs. A full sweep over a
build with broken fixes is dominated by findings the operator already has, buries the new ones among them,
and spends the expensive phase to learn what the cheap one already knew. Phases 0–2 cost a small fraction
of a sweep; that asymmetry is the whole point.

The test-case register is what makes the cheap phases cheap. Phase 1 is **the failed cases re-run
verbatim**, and the adversarial variant each one requires becomes a *new, permanent* case rather than a
note in the margin — that is how the coverage that was missing last time stops being missing. Phase 2 is
**the `PASS` cases whose subject falls in the diff's blast radius**, which is a selection rather than a
guess, and that selection is most of the gate's cost advantage. A `PASS` case is never retired for
passing; it is the regression suite.

Carry **one finding register with stable ids** across every iteration. Ids are names, not positions —
never reuse or renumber them, or nothing can be discussed across builds. Regressions get new ids, with the
causal link in the body ("introduced by the fix for K1"). And if the same finding fails verification twice,
escalate the root cause instead of running a third cycle of the same patch — including the possibility
that your own original diagnosis was the thing that was wrong.

## If a separate dev session does the fixing

Read `references/dev-handoff.md`. The two sessions share no context, so everything between them is an
artifact: **two ledgers with one writer each** (`qa-state.json` is QA's, `fix-state.json` is DEV's, joined
by finding id — neither ever writes the other's fields), a defect lifecycle where `NEW` is not a resting
state, and the invariant that **DEV may claim `FIXED` while only QA may `CLOSE`**, because those are
different statements made by different parties on different evidence.

Two mechanisms do most of the work. The ticket publishes its **acceptance criterion** — the case id and its
oracle — plus the adversarial variant as a *class of input rather than a value*, so a fix is aimed at the
defect instead of the symptom and cannot be ambushed at verification. And the handback is **rejectable
before anyone is briefed**: no build digest per component, or any finding still `NEW`, or missing
fail-first evidence, and it comes back unread. That is far cheaper than a verification round that reports
`NOT IN BUILD` for half the register. Packets in `assets/handoff-packet.md`.

The link that pays twice: **QA's case is the spec, DEV's regression test is its automation**, with the
oracle copied into the test verbatim. Cases DEV has automated stop needing a human run, so the engagement
gets cheaper each round rather than more expensive.

## If the mandate becomes "fix"

Read `references/fix-phase.md`. If you are the author *and* the verifier, the invariant above still holds:
the verification pass is a separate cold pass against the built artifact, graded on the recorded oracle
rather than your memory of what you changed — and the report says that author and verifier were the same
party, because that is a material limitation of the evidence. It covers worktree isolation so the
operator's own checkouts are never written to, writing the test first and **proving it fails against the
unfixed code** (a test that passes
before the fix is testing nothing), one branch per finding so the operator can take them independently,
declaring merge-order dependencies between branches, and what to deliberately leave alone — legal text,
registered identities, registry paths, anything where a rename is really a migration.

## Files in this skill

| File | Read it when |
|---|---|
| `references/evidence-standard.md` | Before the first finding. What counts as proof, per surface. |
| `references/scope-playbooks.md` | Splitting scopes or briefing an agent. The twelve families, with steps, and the agent budget. |
| `references/domains/` | **First, every time.** Twenty-seven product classes — its README indexes them and says which pair up. Each maps the families onto that class, declares its applicable set and agent count, defines what "first success" means, and lists the fault catalogue and defect classes by name. |
| `references/test-cases.md` | Step 3, before running anything. What a test case is here, where cases are derived from, and why the register is the run's denominator. |
| `references/docs-conformance.md` | Scope 9. Claim extraction, two-way coverage, and what a 100% claim requires. |
| `references/experience.md` | Usability and UX. The first-run measurement, making a UX finding provable, error messages, accessibility. |
| `references/iteration-cycles.md` | Any iteration after the first. Phases, the gate, the finding register, when to stop. |
| `references/dev-handoff.md` | A separate dev session or team fixes what you found. Role declaration, the two ledgers, the defect lifecycle, the handback contract, disputes. |
| `references/fix-phase.md` | Report-only has been lifted. |
| `references/gotchas.md` | Before heavy local work — builds, edits at scale, containers, browser automation. Traps that each cost a cycle. |
| `references/case-file.md` | You want a worked end-to-end example with real numbers. |
| `scripts/safe_edit.py` | Any scripted edit to source files. Byte-safe, newline- and BOM-preserving, atomic; validates every anchor against the **original** before applying any, and aborts unless each matches exactly once. `--check` dry-runs anchors. |
| `scripts/qa_dashboard.py` | Generating the local HTML dashboard from the ledgers and event logs — verdict, per-finding QA/DEV lifecycle, coverage, time-in-state. One site per release. |
| `scripts/test_*.py` | The two scripts have self-tests. Run them after touching either; the regression cases fail against the versions that shipped with the bugs. |
| `assets/agent-brief.md` | Briefing a scope agent — or yourself, when working a scope solo. |
| `assets/test-case-register.md` | The register itself — what was exercised, its oracle, its result, what was not run. |
| `assets/handoff-packet.md` | Handing findings to a dev session, or handing a build back to QA. |
| `assets/finding.md`, `assets/ranked-index.md` | Writing up. |
