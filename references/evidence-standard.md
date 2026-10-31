# Evidence standard

What counts as proof, per surface. The test for every line of a report: **could a sceptical engineer
re-run this from what I wrote, and would they get the same result — or, for a probabilistic failure, the
same rate at the same N?** If not, it is an impression, and impressions belong in a "worth a look"
section, not in a ranked finding.

## Contents

- [The universal rules](#the-universal-rules)
- [Web pages and static sites](#web-pages-and-static-sites)
- [HTTP APIs](#http-apis)
- [CLI tools](#cli-tools)
- [GUI applications](#gui-applications)
- [Shipped binaries and archives](#shipped-binaries-and-archives)
- [Email](#email)
- [Containers and self-hosted deployments](#containers-and-self-hosted-deployments)
- [Stateful systems under fault](#stateful-systems-under-fault)
- [Migrations, upgrades and restores](#migrations-upgrades-and-restores)
- [Data pipeline runs](#data-pipeline-runs)
- [Mobile builds on a device matrix](#mobile-builds-on-a-device-matrix)
- [Authorization and permission matrices](#authorization-and-permission-matrices)
- [Background and scheduled work](#background-and-scheduled-work)
- [Experience findings](#experience-findings)
- [Telemetry and privacy](#telemetry-and-privacy)
- [Decompilers, compilers, transformers](#decompilers-compilers-transformers)
- [Evidence that looks strong and is not](#evidence-that-looks-strong-and-is-not)

## The universal rules

**Drive the artifact, not the source.** Build it, then exercise what a user receives. Source inspection
generates *hypotheses*; running the artifact generates *findings*. Report the hypothesis only when you
could not run it, and label it as such.

**Prove negatives through a positive measurement.** "The stale price is gone" is proved by grepping the
rendered output for the old string and showing a zero count. Reading the template and believing it is not
proof — a stale value survived in three rendered files after a commit that "fixed" it.

**Count; don't infer.** Browser APIs, server logs and proxies will tell you exactly how many times
something happened. Retry logic was proved by counting network attempts — exactly 2 on failure, exactly 1
on success — not by reading the retry code.

**Isolate one variable.** The most airtight finding of the prior run was three runs of the same container
image where only an environment variable's *name* differed. Nothing else could explain the difference.

**Stub the dependency to reach the branch.** Failure paths are where products lie to users. Inject a
deterministic stub — a 404, a `provider:null`, a `created:false` — into the built output and drive the
branch. This is how "shows success regardless of outcome" bugs get proved rather than suspected. This is
the right tool for a *stateless* failure path; for a stateful product it is not a substitute for the real
fault, because a stub reaches the branch while a kill, a partition and a pause reach the recovery and
timing logic the branch exists for, and each finds different bugs.

**Record the exact invocation.** Command, URL, payload, host, build identifier, and the time. A finding
without its invocation is a rumour.

**Grade the product against your ledger, never against its own counters.** Health pages, lag metrics, row
counts, "completed" statuses and seat counts are the thing under test. Keep an independent record of every
acknowledgement you received and reconcile the product's state against that.

**Inject the fault; don't stub it, when the product is stateful.** A stub reaches a code branch. A real
kill, partition or pause reaches the timing and recovery logic the branch was written for. Kill, partition
and pause are three different tests with three different bug populations.

**Run it twice at once, then move the clock.** Sequential repetition finds non-idempotency; concurrent
repetition finds races; a moved clock finds everything with a lifetime.

**A nondeterministic result is a result — report the rate.** "Reproduced in 3 of 50 runs under fault
schedule X" is a finding. "Could not reproduce in one attempt" is not a pass. And to verify a fix you need
at least as many runs as it originally took to see the failure, with zero recurrences.

## Web pages and static sites

Build first (`npm ci` then the real build — never a globally-resolved toolchain, which pulls a different
version and fails on config it cannot see), then serve the built output and drive it in a real browser.

- **Rendered output, not templates.** Grep `dist/` for the claim. Page count from the build is a useful
  sanity figure to quote.
- **The browser console is a required reading.** A syntax error in an inline script silently kills every
  behaviour on the page while the build stays green and the page renders normally. Always read the console.
- **Structured data separately from visible copy.** JSON-LD drifts from the heading above it. Stale
  structured prices are a blocker: crawlers publish them as the offer. Extract and compare both.
- **Failure branches.** Unconfigured provider, network 404, empty API response. Confirm the user sees an
  honest, visible error — not a silent redirect, not a success panel.
- **Query strings and hash survive redirects.** A locale redirect built on a path-only map silently
  dropped `?product=` and every `utm_*` parameter. Test with parameters attached, not bare paths.
- **Locale parity.** Build the alternate locale and assert that no English string from the source grid
  appears in its visible markup. Then check number and currency formatting against the locale's actual
  rules — es-ES does not group four-digit numbers (`1490`, but `15.000`), per CLDR
  `minimumGroupingDigits=2`. Confirm before "fixing" something that looks wrong.
- **Both widths.** Desktop and mobile. Layout breakage is a finding.

## HTTP APIs

- Exercise the documented example **verbatim**. A canonical documented call returned 400 in production
  because an implicit parameter had become mandatory — the published example simply did not work.
- Compare the response's actual shape to the documented shape. One doc promised fields production never
  returned, and its own sample code would have printed `undefined` to users.
- **Idempotency and uniqueness:** try the same request twice and read both responses *and* both side
  effects. Then try the near-miss that should collide but might not — case, whitespace, `+tag`
  subaddressing, Unicode-normalised equivalents.
- **Rate limiting:** establish the real limit by hitting it, and check what partitions it. If it partitions
  on a header a client controls, it does not limit anything.
- **Enumeration:** a public endpoint that answers differently for "exists" and "does not exist" is an
  oracle. The correct shape is a byte-identical response on every path, including the capped and
  not-found paths.
- **Auth:** call every admin route with no token, a malformed token, and a valid token for the *wrong*
  tenant. Cross-tenant acceptance is the finding that matters.
- Check response headers, not just bodies: CORS, cache, and the security headers (`HSTS`,
  `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, CSP).

## CLI tools

- Run `--help`, `-h`, `--version`, a bare invocation, a nonsense subcommand, and a valid one. Record the
  **exit code** for each, because that is what CI consumes. A GUI that launches on an unrecognised
  argument and never exits hangs a headless CI agent forever.
- Check the stream each message goes to. Diagnostics on stdout instead of stderr corrupt piped output.
- Exercise the documented examples from the shipped README, exactly as written.

## GUI applications

- Launch the real binary on the real OS and screenshot it. Then exercise the primary workflow end to end —
  open, act, export — and inspect the output file, not just the dialog.
- Check version/about text against the binary's own metadata and the published release.
- After testing, confirm no stray process is left behind. A detached GUI process holds file locks and
  poisons later measurements.

## Shipped binaries and archives

Artifact-level checks are possible for **every** platform regardless of what you can execute, so there is
no excuse for skipping them:

- Download each platform's artifact through the real public path (including redirects) and record size and
  checksum.
- List archive contents; confirm the expected executable is present and plausibly sized.
- Read embedded metadata: company, product, version, copyright. One product stamped `1.0.0` when it was
  really `1.1.2`, with an empty copyright field and the wrong company — while its sibling product stamped
  all of them correctly, so the pattern already existed in the org.
- Check code signing. On Windows, signed vs `NotSigned`. On macOS, ad-hoc vs Developer ID *and* the
  Gatekeeper verdict (`spctl`), because Gatekeeper rejecting outright is a harder failure than a SmartScreen
  warning and users experience it differently.

## Email

Email is where "it works" claims die, because nobody reads the raw message.

- Receive it in a real mailbox you control. Then read the **raw source**: headers, MIME structure, the
  envelope sender, `Reply-To`, and any BCC behaviour you can observe.
- Validate the MIME structure mechanically. One trial email's `multipart/alternative` had the boundary
  delimiter and the first part's headers sharing a line, so a strict parser saw no plaintext alternative
  at all — in a message carrying the customer's licence key.
- Check branding, the tier or plan label, and whether the stated entitlement matches what was actually
  issued.
- Check what is *not* sent as carefully as what is. "Trials no longer get renewal emails" is a claim about
  absence; prove it by reaching the trigger condition and showing nothing arrived.

## Containers and self-hosted deployments

- Pull the published image by tag **and** record its digest. Then prove what code it contains by grepping
  for a string you know changed — that is how an image was shown to predate its own release branch.
- Run it the way the docs tell a customer to run it. Then run it the way the code actually wants. If those
  differ, you have a blocker, not a documentation nit.
- `/health` returning `200 {"status":"ok"}` while the service cannot perform its core function is itself a
  finding: every uptime check in the customer's monitoring is green.
- Test fail-closed behaviour, offline/air-gapped validation, and expiry/grace with a clock you control.

## Stateful systems under fault

Every run records: build **per node**, topology (nodes, replication factor, partitions), workload (ops/s,
key space, value size, duration), the exact fault schedule, the convergence signal observed and how long
it took, reconciliation as Missing / Stale / Wrong over N, the harness self-test result, and the no-fault
baseline result. A run missing any of these cannot be compared to the next one.

- **Durability:** acknowledged-write ledger against a full read-back after convergence. Read from every
  replica the product promised, not the one that answers fastest.
- **Split-brain:** partition the network — do not kill. The ledger shows acknowledgements from two
  acceptors during the partition; after heal, one set is gone or both are present. Show the ledger lines.
- **Replica staleness:** write a marker at T, poll the replica until it appears, report the distribution
  of δ. The product's lag metric is a claim about the same quantity, not evidence of it.
- **Consistency contract:** the documented model is a docs-conformance claim. Test the wording —
  read-your-writes from the same client across a failover, monotonic reads; for a linearizability claim,
  record the history and run a checker over it.
- **Change feed / CDC:** events produced == ledger, in order, no gaps or duplicates across the failover;
  a consumer resuming from a saved offset gets exactly what the docs promise and nothing else.
- **Rebalance / migration:** key count and checksum per partition before and after, and reads *during*
  the move — "available but missing" for the duration of a migration is a finding.

## Migrations, upgrades and restores

Row or key count and checksum per table or partition, before and after, plus the duration on realistic
volume. For online migrations, write continuously during the window and show the in-window writes are
present afterwards. A restore is reconciled against a snapshot taken at backup time, not against "the file
exists"; a point-in-time restore shows rows with timestamp ≤ T present and > T absent. Then open the UI on
the migrated data — a row that exists but no longer renders is still lost to the customer.

## Data pipeline runs

Reconcile source and sink per partition: counts, sum of a numeric column, hash of sorted keys.
Rerun-equivalence: run the same window twice and diff the sink (zero changed rows if the pipeline claims
idempotency). Kill-resume: kill at a recorded offset, resume, reconcile. Drift: mutate the source schema —
add, rename, retype, nullability — and show the sink schema, the sink data and the log. Late data: inject
a record whose event time falls in a closed window and show where it landed. Dead-letter: count what went
there and state whether anyone would know. Record per run: pipeline version, source snapshot id, config
hash, time window, and checkpoint state before and after.

## Mobile builds on a device matrix

Install the **store or track** artifact, not the debug build. Deliver a matrix — device × OS version ×
check — with every cell PASS / FAIL / NOT RUN, and record the invocation for each. Upgrade over the
previous store version with data created. Kill the process from the background and restore. Revoke a
granted permission at runtime. Force Doze and prove the background job ran — or correctly did not — by its
side effect, not by the scheduler's state. Verify app links. Attach accessibility-scanner output.

## Authorization and permission matrices

A table of role × operation × **channel** — UI, API, search index, report, export, webhook payload,
notification email — with every cell exercised using that role's real session. The leaks live in the
channels nobody put on the settings page.

## Background and scheduled work

Proved by side effect and by count: exactly one execution per schedule slot, missed-slot catch-up
behaviour, overlap when a run exceeds its interval, the DST transition, and which timezone the schedule is
actually interpreted in.

## Telemetry and privacy

- Capture actual egress from the client — host, path, payload — and read it. Do not rely on the privacy
  policy or the code comments.
- Enumerate every route the telemetry host serves. One host branded `telemetry` also handled identified
  sales leads and download redirection, so it observed name, email, company, free text, visitor id *and*
  IP against product and platform.
- Exercise consent and opt-out, then confirm by observing egress — not by reading the setting.
- State clearly what you cannot see. Without a backend read key, you can prove the *surface* and must not
  claim anything about what is stored or how it is tagged.

## Experience findings

A usability finding needs evidence too, or it is answered with "that's subjective" and the section becomes
decoration. The hierarchy and the severity scale live in `references/experience.md`; in one line, the four
admissible kinds, strongest first, are: the product **already does it right somewhere else** (its own two
surfaces disagreeing, which removes taste from the argument); a **blocked or abandoned goal**, stated as a
goal; a **measurement** — time, steps, exits from the product, time-to-diagnose, or a count of conditions
against distinguishable signals; and a **convention violation with a named cost**. Aesthetic preference
with no nameable cost is polish.

## Decompilers, compilers, transformers

- Build a **purpose-made fixture** containing exactly the construct in question, then compare input to
  output. A fixture turns "output looks poor" into a measurement: 40 lines versus 27 lines, with the
  construct reconstructed or not.
- Decide empirically whether a defect is yours or upstream: run the same input through the upstream tool's
  own defaults, and through two upstream versions. Do not assert "upstream, not fixable" — the prior run
  did, and one of three such findings was a single wrong line of its own code.
- When a defect genuinely is upstream, **write a test asserting the defect is still present**. If a future
  version fixes it, the suite tells you and the finding can be closed. That turns a permanent footnote
  into a tracked item.

## Evidence that looks strong and is not

| Not evidence | What to do instead |
|---|---|
| HTTP 200 / page renders | Complete the transaction the page exists for |
| `/health` is green | Perform the service's core function |
| The build passed | Run the artifact and read the browser or runtime console |
| Tests pass | Confirm a new test *fails* before the fix; otherwise it asserts nothing |
| The code says it retries | Count the attempts |
| The template has the right value | Grep the rendered output |
| The release notes claim a version | Read the binary's embedded metadata |
| The docs describe the response | Call it and diff the actual shape |
| An image tag says `2.5.0` | Grep the image for a string you know changed |
| Upstream's fault, surely | Run upstream's defaults, and a second version |
| The write returned OK | Read it back after the fault, from every replica the product promised |
| The cluster / dashboard says healthy | Reconcile your acknowledged-write ledger against the data |
| Replication lag metric reads 0 | Write a marker and time its arrival on the replica |
| The backup job succeeded | Restore it and count the rows |
| The pipeline run is green | Reconcile source and sink counts and checksums |
| The role matrix is configured | Exercise each cell as that role — via API, search and export too |
| The migration ran without error | Count and checksum before and after; open the UI on the result |
| It works on the emulator | Install the store build on the oldest supported device, over the previous version |
| The job is scheduled | Count executions and check the side effect after Doze or a missed slot |
| Could not reproduce once | Run it as many times as it took originally; report the rate |
