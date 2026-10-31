---
name: product-qa
description: Evidence-first methodology for end-to-end QA of a real product, release, or whole business — orienting on what is actually deployed before testing it, splitting scopes across parallel agents, proving every finding by exercising the flow rather than checking that it responds, verifying the documentation claim by claim in both directions for a defensible coverage number, ranking findings with exact repro and evidence, and (if the operator lifts report-only) fixing in isolated worktrees behind tests that fail first. Use this whenever the user wants a product, release, website, desktop app, API, SaaS or self-hosted deployment tested or QA'd; asks to find, verify or rank bugs before shipping; wants the docs checked against what the product really does, or asks about documentation coverage or gaps; mentions QA agents or a multi-agent test sweep; wants a findings or bug report written up; or asks to fix what a QA run found. Use it even when they only say "test my product", "check everything works", "give it a full QA pass", "make sure the docs are right" or "find what's broken", without the word QA.
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

- **Report-only, or fix?** If fix, what is the delivery mode — pushed branches, PRs, commits in place?
  Default to the least irreversible option available and confirm it.
- **What is out of bounds?** Deploys, merges, production config, and any destructive operation against
  state you did not create. **Destructive is defined by whose state it destroys, not by the verb.** Killing
  a node, partitioning a network, dropping a table or wiping a device in an environment *you stood up, with
  data you generated* is testing — and for a stateful product it is the only testing that matters.
  Revoking a real licence, deleting a production row or restarting a shared cluster is not. Establish in
  writing which environments are yours to break, and put that answer in every brief.
- **Which credentials, and which tenant?** Admin and licensing APIs get a *test* tenant's token, never a
  production one. Ask for what you need; if it does not arrive, state the blocked test rather than
  improvising around it.
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
and the defects live in the seams. There are twelve scope *families*. Which apply is a per-product
decision made in Step 0 — a database has no acquisition funnel, a static site has no durability scope —
and the inapplicable ones are listed in the report as N/A with one line of reasoning, so a reader can see
the omission was chosen rather than missed.

1. Acquisition surface (website, store listing, funnel) · 2. Primary product, per platform or device ·
3. Control plane (SaaS, console, admin / management API) · 4. Deployment (container, Helm, cluster,
install) · 5. Entitlement lifecycle · 6. Secondary products, SDKs, compatibility layers ·
7. Telemetry & privacy · 8. Security & abuse · 9. Documentation conformance ·
**10. State: correctness and durability under fault, time and concurrency** ·
**11. Upgrade, migration and rollback** · **12. Experience & diagnosability**

`references/scope-playbooks.md` has the generic playbook per family. `references/domains/` maps the
families onto nineteen product classes, grouped in its README as data and state, applications, education,
and platform and infrastructure — each file carrying that domain's version of "do the thing", its fault
catalogue, the evidence it needs, and its severity notes. **Read the closest one before briefing, and read
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

**Agent budget: one agent per *applicable* scope family, 11 maximum.** The cap is on agents, not on
families. Three rules keep it honest as scopes grow: inapplicable families cost zero agents and are listed
as N/A rather than silently absent; long-running runs (a durability certification, a backfill, a
device-matrix sweep) are background jobs the lead starts and reads back — never an agent sitting idle on a
12-hour wait, which is billed and holds a slot a scope needs; and when scope 10 is the core of the product
it is the usual recipient of the spare agents, split by fault class (kill/partition vs
membership/migration), not by product. Each domain file declares its usual applicable set and default
merges; the sum must fit the cap before the operator is asked for more.

Name up front every platform × scope cell you cannot execute on this machine. That list is a deliverable,
not an apology.

## Step 3 — Test by doing

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
experience agent who would be warm by definition. A freshly briefed scope agent is a genuine first-time
user by construction; the lead, warm from Step 1's hosting config and code greps, is not. So in a parallel
sweep every scope captures its own first-run trace and error inventory on first contact and returns them
to family 12's owner, who holds the baseline across iterations and runs the deliberate audits. In a solo
run, do the primary surface's first run *before* Step 1, or label the trace warm.

For operator-facing products the sibling measurement matters more: **time to diagnose**. Every fault run
in scope 10 supplies it for free — inject the fault, then time how long until someone reading only the
product's own output could name the condition and the action. "Never, the condition was invisible until
reconciliation" is a usability blocker that is also an outage.

## Step 5 — Rank, de-duplicate, consolidate

One ranked index, most severe first, product bugs separated from usability, each row carrying a Step 1
status and a pointer to the per-scope detail. Template in `assets/ranked-index.md`.

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

Carry **one finding register with stable ids** across every iteration. Ids are names, not positions —
never reuse or renumber them, or nothing can be discussed across builds. Regressions get new ids, with the
causal link in the body ("introduced by the fix for K1"). And if the same finding fails verification twice,
escalate the root cause instead of running a third cycle of the same patch — including the possibility
that your own original diagnosis was the thing that was wrong.

## If the mandate becomes "fix"

Read `references/fix-phase.md`. It covers worktree isolation so the operator's own checkouts are never
written to, writing the test first and **proving it fails against the unfixed code** (a test that passes
before the fix is testing nothing), one branch per finding so the operator can take them independently,
declaring merge-order dependencies between branches, and what to deliberately leave alone — legal text,
registered identities, registry paths, anything where a rename is really a migration.

## Files in this skill

| File | Read it when |
|---|---|
| `references/evidence-standard.md` | Before the first finding. What counts as proof, per surface. |
| `references/scope-playbooks.md` | Splitting scopes or briefing an agent. The twelve families, with steps, and the agent budget. |
| `references/domains/` | **First, every time.** Nineteen product classes — its README indexes them and says which pair up. Each maps the families onto that class, declares its applicable set and agent count, defines what "first success" means, and lists the fault catalogue and defect classes by name. |
| `references/docs-conformance.md` | Scope 9. Claim extraction, two-way coverage, and what a 100% claim requires. |
| `references/experience.md` | Usability and UX. The first-run measurement, making a UX finding provable, error messages, accessibility. |
| `references/iteration-cycles.md` | Any iteration after the first. Phases, the gate, the finding register, when to stop. |
| `references/fix-phase.md` | Report-only has been lifted. |
| `references/gotchas.md` | Before heavy local work — builds, edits at scale, containers, browser automation. Traps that each cost a cycle. |
| `references/case-file.md` | You want a worked end-to-end example with real numbers. |
| `scripts/safe_edit.py` | Any scripted edit to source files. Byte-safe, newline- and BOM-preserving, aborts unless every anchor matches exactly once. |
| `assets/agent-brief.md` | Briefing a scope agent — or yourself, when working a scope solo. |
| `assets/finding.md`, `assets/ranked-index.md` | Writing up. |
