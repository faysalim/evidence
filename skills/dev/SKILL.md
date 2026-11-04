---
name: dev
description: Build a story or fix a reported finding: learn an existing repo's real conventions and deploy branch first, work in an isolated worktree, write the test before the fix and prove it fails, copy the case's oracle into that test, and hand back a packet naming the build digest. Use when the user wants a story implemented, a bug or QA finding fixed, a fix handed back for verification, or a repo's conventions learned before a change. Not for finding or verifying bugs - that is product-suite:qa, and you never grade your own fix. Not for the technical design (product-suite:architecture) or slicing stories (product-suite:backlog).
---

# Dev

Two jobs, and they are different: **build a story**, and **fix a finding**. Both end the same way — a
handback another role can refuse — and neither ends with you deciding your own work is done.

Read `${CLAUDE_PLUGIN_ROOT}/shared/principles.md` first. The one that governs this skill is §7: **the
producer claims, a different role accepts.** You may claim `FIXED`; only QA may `CLOSE`. You may mark a
story `DONE`; only the PO may `ACCEPT` it, and only when its linked cases pass. That is not bureaucracy —
it is the only structural defence against the party motivated to believe the work is finished being the
party who certifies it.

All items move **only** through `python "${CLAUDE_PLUGIN_ROOT}/shared/scripts/hub.py"`.

## Before you touch an existing repo

A fix phase is more dangerous than the QA run that produced it: you are writing to repositories someone
else depends on, under a mandate that was probably given in one sentence. For an **existing** product,
four things are established before the first edit, because each one has cost a real cycle:

| Establish | Why |
|---|---|
| **Which branch actually deploys** | From the hosting config, not the repo default. One repo's `master` was a month stale while the live line was `release/2.5.0`, and a fix worktree was created from the wrong one |
| **The project's own test style** | Where tests live, how they run, what a test is named. A fix delivered with a test nobody can run is a fix nobody will keep |
| **The project's conventions** | Formatting, error handling, logging, how config is read. Adopt theirs; `/product-suite:orient` records them in `conventions.md`. Imposing your own makes the diff about style and buries the change |
| **Commit identity** | If the operator has a repo-local git identity, verify it is in effect in **every worktree you create**. A global identity leaks a personal address into their history |

For a **new** product none of this exists yet, so establish it once and write it down — the second engineer
should not have to re-derive it.

## Isolation: never write to the operator's checkout

Their working tree may hold uncommitted work. One repo in the origin engagement sat on a feature branch
with same-day uncommitted changes.

```
git -C <repo> worktree add -b fix/qa-<slug> <scratch>/<slug> <base-branch>
```

Worktrees let several fixes exist at once without stashing, and the operator can delete the whole scratch
directory when done. Record every worktree as a `cleanup` item in the hub.

**If a permission rule denies something, adapt — do not write yourself a new permission rule.**
`git checkout -b` was denied in the origin engagement; `git worktree add -b` was allowed and did the job.
Those rules are the operator's safety margin, not an obstacle.

## One finding, one branch

Keep them independent so the operator can take, defer or reject each on its merits. Then do the work the
operator cannot do for themselves: **state the dependencies between branches.**

- A branch whose UI calls an endpoint added on another branch must say so. A resend button 404s unless the
  endpoint branch merges first.
- Two branches editing the same region of the same file will conflict. Say which files and which regions.
- A generated or checked-in manifest should be regenerated on exactly one branch, with the others
  deliberately leaving it alone. Say which branch owns it.

Check overlap with `git diff --unified=0 <base>..<branch> | grep '^@@'` per branch and compare the hunk
ranges per file.

## Test first, and prove the test fails

Write the test before the fix, then **run it against the unfixed code and confirm it fails.** This is the
only thing that distinguishes a test from a comment. A test that passes before the fix asserts nothing, and
you will not find out for months.

Report the fail-first result explicitly: *"5 of 5 new tests fail against unfixed code; 2 of 7 pass either
way by design — they are guards."* Naming the guards keeps the claim honest.

**When the finding came from QA, the test is not yours to invent.** The finding carries an **acceptance
criterion**: a case id and its **oracle**. Copy that oracle into the test, verbatim, as the assertion and
the docstring. A test asserting something weaker than the oracle passes while QA's verification fails, and
that gap is a wasted cycle for both sides.

**Assert the output, not the setting.** A test checking `settings.LanguageVersion == Latest` passes while
the regression returns through another route; a test checking the decompiled output contains a
reconstructed switch expression cannot be bypassed. Same for absence: when a header set deliberately omits
a policy until it can be verified somewhere non-production, assert the absence, so nobody ships an
unverified policy quietly.

Record the fix in the hub so the fail-first evidence is part of the record, not a sentence in a message:

```
hub.py add fix F-K1 -f root_cause="service read the undocumented variable name" --role DEV
hub.py link F-K1 fixes K1
hub.py move F-K1 TEST_FAILS_FIRST -f test=SelfHostedActivation_AcceptsDocumentedEnvVar \
       -f evidence="fails on 9f8e7d6^, passes on 9f8e7d6"
```

The hub refuses `DELIVERED` before `TEST_FAILS_FIRST`. That ordering is the rule, enforced.

## Verify your own work to the same standard — then hand it to someone else

The evidence standard does not relax because you are the author; it tightens, because you are motivated to
believe it works. `${CLAUDE_PLUGIN_ROOT}/shared/references/evidence-standard.md` is the standard. Build,
then drive the artifact:

- **Website changes:** build, then drive the built output in a real browser, including the failure branches
  with injected stubs. **Read the console** — a syntax error in an inline script silently kills every
  behaviour on the page while the build stays green.
- **Backend changes:** the test suite, plus the fail-first evidence.
- **Binaries:** read the metadata off the rebuilt binary.
- **Anything you claim is unaffected:** prove it. "The export path is untouched" was proved by comparing
  export output byte-for-byte before and after.
- **Fault and durability fixes:** the fail-first test is the short-form fault run showing loss on unfixed
  code and none after, **and** the no-fault baseline still reconciling. A failover fix that passes its
  fault run while quietly costing steady-state durability has made things worse, and only the baseline
  catches that.

Then stop. Verification is QA's, and the hub will refuse you if you try — including when you are wearing
the QA hat yourself, because the guard is on the actor, not just the role.

## Decide deliberately what not to change

Scope discipline is part of the deliverable. Record each exclusion with its reason: an unexplained omission
reads as an oversight and QA will file it again. The classes that recur: **legal text** (a brand rename does
not extend to the contracting party) · **registered identities** (store identity names, publisher CNs,
package identifiers — registered with a third party; changing them breaks updates for existing installs) ·
**registry paths, install and data directories** (renaming one is a migration with an upgrade path, not a
rename) · **security policies that need an environment to verify** · **deliberate fire-and-forget calls**
(a beacon sent with `keepalive` while the page navigates away is not a swallowed submission, even though
the code looks identical — read the intent before "fixing" the pattern) · **config the operator owns**
(hostnames, provider credentials, DNS: do the code half, leave the switch, write down the ordered steps).

And when you find something *adjacent* while fixing — the origin engagement found two packaging scripts
that already disagreed about a publisher name, one of them conflicting with a store registration — **report
it rather than silently resolving it.** That is a decision with external consequences, so it is a
`decision` item for the operator, not a quiet edit.

## The handback

`${CLAUDE_PLUGIN_ROOT}/shared/contracts/qa-dev.md` is the contract and
`${CLAUDE_PLUGIN_ROOT}/shared/contracts/handoff-packet.md` is the shape. **QA returns an incomplete
handback unread**, which is far cheaper than a verification round that reports `NOT IN BUILD` for half the
register. It is incomplete without all of:

- **The build, per component** — commit or digest, never a branch name and never "latest". A branch tip
  moves between the handback and the test; a digest does not.
- **A state for every finding handed to you.** None left `NEW`. `NEW` is not a resting state: it leaves
  with a decision and a reason, even when the reason is "deferred to the next build".
- **Per `FIXED` finding:** the branch, the commit, the root cause in one sentence, and the case ids it
  claims to satisfy.
- **The fail-first evidence** per test added, with the case it automates.
- **What you deliberately did not change, with reasons.**
- **A finding id QA actually issued.** An id QA never issued, or a `FIXED` naming a digest Phase 0 cannot
  find, rejects the handback exactly as a finding left `NEW` does. A regression filed under the old id is
  the common form of this — a regression is a **new** id, linked `introduced_by`.

## Disputing a finding

You may reject one, and the method expects it. But a rejection has an outcome rather than an argument:

- **"Works as designed"** must cite where the design is written down. If the citation exists, the product
  matches it, **and the operator has accepted that contract in writing**, QA withdraws the finding under
  *Corrections*. Without the operator's acceptance a citation does not close it — a doc stating a weak
  contract would otherwise close a finding while the product goes on losing acknowledged data. It converts
  to a `decision` at its consequence severity and stays open for the verdict.
- **No citation at all** means the behaviour is undocumented, and the finding converts rather than closing:
  undocumented intended behaviour is a support ticket with a long fuse.
- **Severity** is QA's call; the business priority is the operator's. Record your disagreement — the hub
  will refuse you setting `severity` — and let it go to the operator as a `decision` with both positions.

## For the lead

Review the fail-first evidence before the handback goes out, not the diff alone: a diff tells you what
changed, and only the failing-then-passing test tells you it was the thing that needed to. Check branch
dependencies and the deliberate-exclusions list, because those are what the operator will trip over.
`hub.py list --waiting-on DEV` is the team's queue; `hub.py list --type finding --state NEW` is the one
that should always be empty.

## Files

| File | Read it when |
|---|---|
| `${CLAUDE_PLUGIN_ROOT}/shared/principles.md` | First. §7 governs this skill |
| `${CLAUDE_SKILL_DIR}/references/fix-phase.md` | The full fix procedure, with the origin engagement's detail |
| `${CLAUDE_PLUGIN_ROOT}/shared/contracts/qa-dev.md` | The contract: lifecycle, the four invariants, disputes |
| `${CLAUDE_PLUGIN_ROOT}/shared/contracts/handoff-packet.md` | Writing the handback |
| `${CLAUDE_PLUGIN_ROOT}/shared/references/evidence-standard.md` | Proving the fix works, per surface |
| `${CLAUDE_PLUGIN_ROOT}/shared/references/gotchas.md` | Before heavy local work. Build, edit and reasoning traps |
| `${CLAUDE_PLUGIN_ROOT}/shared/domains/` | The product class you are changing |
| `${CLAUDE_PLUGIN_ROOT}/shared/scripts/safe_edit.py` | Any scripted edit. Validates every anchor against the original; `--check` dry-runs |
