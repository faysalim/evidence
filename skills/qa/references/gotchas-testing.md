# Gotchas: testing

Traps specific to exercising a product rather than building one. The build, file-editing, repository and
reasoning traps are shared across every role and live in
`${CLAUDE_PLUGIN_ROOT}/shared/references/gotchas.md` — read both before heavy local work.

## Contents

- [Browser automation](#browser-automation)
- [Cloud teardown on a starved host](#cloud-teardown-on-a-starved-host)
- [Stateful and clustered testing](#stateful-and-clustered-testing)

## Browser automation

- **Returning a decoded URL containing query parameters can be blocked** by the tooling as cookie/query
  data. Return booleans, counts, or short fragments instead of whole URLs.
- **`window.open` is blocked.** Navigate one tab at a time.
- **Never trigger `alert`, `confirm` or `prompt`.** A modal blocks every subsequent automation event and
  the session goes unresponsive until a human dismisses it.
- **Hard-reload when checking a local build** — `localhost` caching will show you the previous build and
  you will debug a file that is no longer on disk.
- **Count network requests from inside the page** (`performance.getEntriesByType('resource')`) to prove
  retry behaviour. This turns "the code retries" into "exactly 2 attempts on failure, exactly 1 on
  success".
- **Close tabs and stop preview servers at the end.** A stray server serving a stale build is a landmine
  for the next iteration.

## Cloud teardown on a starved host

If you created cloud resources, teardown is yours, and it can fail in ways that look like success:

- A missing CLI fails before making any API call — nothing was destroyed, despite the command "running".
- An SDK client can hang in **construction**, before any network call, loading service models from disk on
  an I/O-starved host.
- What worked: stop compute immediately over SSH to halt billing, then call the provider's query API
  directly with hand-rolled request signing using only the standard library.

Either way, **verify by re-listing the resources**. `billable instances: NONE` is the deliverable; "I ran
the terminate command" is not.

## Stateful and clustered testing

- **A harness that has never failed has never been shown to work.** Inject one known loss and confirm the
  reconciliation reports exactly one. Two "passing" durability certifications in a real engagement were
  harness false-negatives — the run could not have detected a loss if there had been one.
- **Counting presence misses two of the three failures.** A reconciliation that checks "key exists" cannot
  see Stale or Wrong. Compare value and version, not just membership.
- **Loopback is not the machine.** A membership or workspace check that rejects `127.0.0.1` yields
  "0 instances" with no error at all. Address by machine name, and confirm the instance count before
  measuring anything.
- **Config on ephemeral storage resets on reschedule.** A pod rescheduled onto a fresh `emptyDir` silently
  forgets site and topology configuration; re-apply and re-verify before trusting a post-reschedule run.
- **Every node has its own build.** Phase 0 for a cluster is a per-node table. A mixed-version cluster
  during a rolling upgrade is a legitimate scope-11 target and an illegitimate fix-verification target.
- **Long runs fail at hour eleven on what the one-hour run would have shown.** Ladder 1h → 3h → 12h; every
  run has a progress signal and exits itself when that signal freezes. A stalled run nobody notices until
  morning costs more than the fault it was looking for.
