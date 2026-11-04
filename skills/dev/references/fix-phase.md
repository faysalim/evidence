# Fix phase

Read this once the operator lifts report-only. A fix phase is more dangerous than the QA run that produced
it: you are now writing to repositories someone else depends on, under a mandate that was almost certainly
given in one sentence.

**If you are a separate dev session fixing what another session found, read
`${CLAUDE_PLUGIN_ROOT}/shared/contracts/qa-dev.md`
first.** Everything below applies to you unchanged; that file adds what the second session makes necessary
— the ledger you own and the one you must not write, the state you may set (`FIXED`) and the one you may
not (`CLOSED`), and what your handback must contain to be accepted at all.

## Confirm the delivery contract first

Get these four answers before the first edit, because each one changes the mechanics:

1. **Branches, PRs, or commits in place?** "Pushed branches, no PRs, no merges, no deploys" is a good
   default and was the prior run's contract. Branches let the operator take fixes independently and reject
   some.
2. **Base branch per repo.** Establish it from the hosting config, not the repo default (see Step 1 of
   SKILL.md — one repo's `master` was a month stale behind `release/2.5.0`).
3. **Branch naming.** Agree a prefix (`fix/qa-*` worked well) so the operator can see at a glance which
   branches came from this run, and so permission rules can be scoped to it.
4. **Commit identity.** If the operator has a repo-local git identity, verify it is in effect in every
   worktree you create. A global identity leaks a personal address into their history.

## Isolation: never write to the operator's checkout

Their working tree may hold uncommitted work — one repo in the prior run sat on a feature branch with
same-day uncommitted changes. Use a separate worktree per branch:

```
git -C <repo> worktree add -b fix/qa-<slug> <scratch>/<slug> <base-branch>
```

Worktrees also let several fixes exist simultaneously without stashing, and the operator can delete the
whole scratch directory when done. Record every worktree in the cleanup ledger, and note that removal is
`git worktree remove`, or deleting the directory and running `git worktree prune`.

If a permission ruleset denies something (`git checkout -b` was denied in the prior run), **adapt — do not
write yourself a new permission rule.** `git worktree add -b` was allowed and did the job. Those rules are
the operator's safety margin, not an obstacle.

## One finding, one branch

Keep them independent so the operator can take, defer or reject each on its own merits. Then do the work
the operator cannot do for themselves: **state the dependencies between branches.**

- A branch whose UI calls an endpoint added on another branch must say so. A resend button 404s unless the
  endpoint branch merges first.
- Two branches editing the same region of the same file will conflict. Say which files and which regions
  so the merge is deliberate rather than surprising.
- A generated or checked-in manifest (a parity matrix, a lockfile, a snapshot) should be regenerated on
  exactly one branch, with the others deliberately leaving it alone. Say which branch owns it.

Check for overlap with `git diff --unified=0 <base>..<branch> | grep '^@@'` per branch and compare the
hunk ranges per file. (`git merge-tree` is nicer when available; it was denied in the prior run.)

## Test first, and prove the test fails

Write the test before the fix, then **run it against the unfixed code and confirm it fails.** This is the
only thing that distinguishes a test from a comment. A test that passes before the fix asserts nothing,
and you will not find out for months.

Report the fail-first result explicitly: "5 of 5 new tests fail against unfixed code; 2 of 7 pass either
way by design (they are guards)". Naming the guards keeps the claim honest.

Assert the **output**, not the setting. A test that checks `settings.LanguageVersion == Latest` passes
while the regression returns through another route; a test that checks the decompiled output contains a
reconstructed switch expression cannot be bypassed. Same for absence: when a security header set
deliberately omits CSP until it can be verified somewhere non-production, assert the absence, so nobody
ships an unverified policy quietly and silently.

## Verify the fix the way QA verified the bug

The evidence standard does not relax because you are now the author — it tightens, because you are
motivated to believe it works. Build, then drive the artifact. Specifically:

- Website changes: build, then drive the built output in a real browser, including the failure branches
  with injected stubs. Read the console.
- Backend changes: the test suite, plus the fail-first evidence.
- Binaries: read the metadata off the rebuilt binary.
- Anything you claim is unaffected: prove it. "The export path is untouched" was proved by comparing
  export output byte-for-byte before and after.
- Fault and durability fixes: the fail-first test is the short-form fault run showing Missing > 0 on
  unfixed code and 0 after, **and** the no-fault baseline still reconciling. A failover fix that passes
  its fault run while quietly costing steady-state durability has made things worse, and only the baseline
  catches that.

## Decide deliberately what not to change

Scope discipline is part of the deliverable. Record each exclusion with its reason, because an unexplained
omission reads as an oversight. The classes that recur:

- **Legal text** — licence files, EULAs, agreements customers have already accepted. A brand rename does
  not extend to the contracting party.
- **Registered identities** — app store identity names, publisher CNs, package identifiers. These are
  registered with a third party; changing them breaks updates for existing installs.
- **Registry paths, install directories, data directories** — renaming one is a migration with an upgrade
  path, not a rename.
- **Security policies that need an environment to verify** — a CSP derived from guesswork and shipped to
  production is worse than no CSP.
- **Deliberate fire-and-forget calls** — a beacon sent with `keepalive` while the page navigates away is
  not the same bug as a swallowed form submission, even though the code looks identical. Read the intent
  before "fixing" the pattern.
- **Config the operator owns** — hostnames, provider credentials, DNS. Do the code half, leave the switch,
  and write down the ordered steps.

And when you find something *adjacent* while fixing — the prior run found two packaging scripts that
already disagreed about a publisher name, meaning one conflicted with the store registration — report it
rather than silently resolving it. That is a decision with external consequences.

## Deliver

A fix-phase report should let the operator act without asking a question:

- Branch, repo, commit, finding, base branch, build result, and how the output was verified — one row each.
- Merge order and expected conflicts.
- Corrections to the QA report that code access produced. Having the code almost always disproves
  something you reported from the outside; that section is the most valuable in the document.
- Deliberately not changed, with reasons.
- Still the operator's: deploys, releases, certificates, DNS, production data, decisions.
- The cleanup ledger.
