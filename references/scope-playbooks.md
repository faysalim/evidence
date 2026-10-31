# Scope playbooks

Twelve scope families. Which apply is decided per product in Step 0, and `references/domains/` maps them
onto specific product classes. Adapt the names; keep the shape. Each playbook lists what to *do*, because
a scope described as a noun ("website") gets tested as a noun ("the website loads").

Inapplicable families are listed in the report as **N/A with one line of reasoning** — a database has no
acquisition funnel, a static site has no durability scope — so a reader can see the omission was chosen
rather than missed.

Brief every scope — your own or an agent's — with four things: the business context, this playbook, the
evidence standard, and the Step 0 safety rules. A scope without context reports that the page loads.

**Agent budget: one agent per *applicable* family, 11 maximum.** The cap is on agents, not families.
Inapplicable families cost zero. Long-running runs are background jobs the lead starts and reads back,
never an agent idling on a 12-hour wait. Where scope 10 is the core of the product it takes the spare
agents, split by fault class rather than by product. Default merges when a product does not justify a
separate agent: **7 → 8** where there is no telemetry gateway of its own (both are "observe egress, probe
authz"), **5 → 4** where licensing is an activation step rather than a product, **6 → 2** where the SDKs
*are* the primary product, and **12 → the lead** for operator-facing products. Each domain file declares
its usual applicable set, its merges and the resulting agent count; the sum must fit the cap before the
operator is asked for more.

**Every scope carries two cross-cutting rules**, both reporting to a single owner so the matrix stays in
one place:

- **Documentation (scope 9):** as you test your surface, read its documentation and run what it tells a
  customer to run, verbatim. Report divergences to scope 9's owner rather than filing them yourself.
- **Experience (scope 12):** if you are the first agent to touch a surface, time and trace the path to
  first success *before* reading more than a customer would. Then keep an **error inventory** for your
  whole scope — every error message, WARN-or-above log line and exit code you provoked, verbatim, with the
  action that caused it. Return both to scope 12's owner. You are the only cold party; nobody can retake
  that measurement later.

## Contents

- [1. Website and acquisition funnel](#1-website-and-acquisition-funnel)
- [2. Desktop or CLI application, per platform](#2-desktop-or-cli-application-per-platform)
- [3. SaaS / multi-tenant control plane](#3-saas--multi-tenant-control-plane)
- [4. Self-hosted / container deployment](#4-self-hosted--container-deployment)
- [5. Licensing and entitlement lifecycle](#5-licensing-and-entitlement-lifecycle)
- [6. Secondary and free products](#6-secondary-and-free-products)
- [7. Telemetry and privacy](#7-telemetry-and-privacy)
- [8. Security and abuse, non-destructive](#8-security-and-abuse-non-destructive)
- [9. Documentation conformance](#9-documentation-conformance)
- [10. State: correctness and durability under fault, time and concurrency](#10-state-correctness-and-durability-under-fault-time-and-concurrency)
- [11. Upgrade, migration and rollback](#11-upgrade-migration-and-rollback)
- [12. Experience and diagnosability](#12-experience-and-diagnosability)
- [Platform coverage](#platform-coverage)

## 1. Website and acquisition funnel

Walk the path a buyer walks, then walk every path a buyer might fall off.

- Complete the **whole funnel** on the built output: land → compare → choose → submit → receive. The
  handoffs between pages are where context gets dropped.
- **Every acquisition form, actually submitted.** Then check the thing it was supposed to trigger actually
  happened. A lead POST ending in `.catch(() => {})` showed "Request received, we'll email your key" on
  every failure — and for one product that POST was the *only* fulfilment trigger, so a failure lost the
  customer silently.
- **Pass product/plan context through navigation.** An enquiry about product B arriving titled "product A
  licence request" is a real lost sale. Test with the parameter attached and follow it through every
  redirect, including locale redirects.
- **Prices in three places must agree**: visible copy, client-rendered values, and structured data
  (JSON-LD). They drift independently. Stale structured data is a blocker.
- **Client-rendered content is invisible to crawlers and to no-JS users.** A pricing grid that ships as
  the literal string "Loading plans…" publishes no prices at all. Check what the HTML contains before
  scripts run.
- **Dropdowns and switchers populated by fetch**: break the fetch and see what the user gets. Empty
  selects hide purchasable options.
- **Download matrix**: every platform link resolves to the correct artifact for that platform. Follow
  redirects to the final file and check it.
- **Locale parity**: the acquisition flow in alternate locales usually lags English. Diff it.
- Console errors, broken images, dead links, and accessibility basics (landmarks, labels, contrast,
  keyboard reachability of the funnel).

## 2. Desktop or CLI application, per platform

- Download from the real public path, install the way a user installs.
- **CLI**: `--help`, `-h`, `--version`, bare invocation, nonsense subcommand, each documented example.
  Record exit codes. Verify diagnostics go to stderr.
- **GUI**: launch, screenshot, complete the primary workflow, inspect the produced file.
- **Entitlement tiers**: run the free/unlicensed path, then the paid/trial path. Activate through *every*
  documented mechanism (a register command, an environment variable, a file) — they are separate code
  paths and they drift. Confirm feature gating actually differs between tiers.
- **Bad input**: expired key, malformed key, key for another product. The error message is the product
  here; a cryptic failure is a finding.
- **Round-trip the core transformation.** If the product transforms user artifacts, run the output and
  confirm it behaves identically to the input. This is the one test that cannot be faked.
- Binary metadata and signing: see the evidence standard.

## 3. SaaS / multi-tenant control plane

- Sign up as a new customer would. Note every point of friction; the funnel is the product.
- Create the full object graph a real customer needs, in order, through the UI — not the API — then verify
  each object through the API.
- **Exercise the whole lifecycle of the primary entity**: create → issue → use → inspect → suspend →
  resume → revoke, on data you created and marked as test.
- Customer-facing portal flows (magic links, password reset) end to end, including the email.
- Team, roles and invitations: confirm a lower role genuinely cannot perform a higher role's action.
- **Cross-tenant isolation**: with tenant A's token, request tenant B's objects. Expect refusal.
- Billing and upgrade paths in test mode only, never with real payment details — and say so in Not
  Verified, because test mode does not exercise declines, 3DS challenges, webhook signature failures or
  processor latency. It is the right call for safety and it is not evidence of a working checkout.
- Each shipped SDK, integrated against your test tenant, using the published quickstart verbatim.
- Security headers on authenticated pages, and where the session token is stored.

## 4. Self-hosted / container deployment

- Pull the published image by tag, record the digest, and prove which code it contains.
- **Deploy following the customer-facing docs literally.** Then deploy the way the code actually wants.
  Divergence here is a blocker, because the customer's first experience is the documented path.
- Activate with the licence mechanism as documented, including inline-value and file-path variants.
- Confirm `/health` reflects the ability to do real work, not just process liveness.
- Fail-closed: no licence, expired licence, unreachable upstream. Confirm it refuses rather than silently
  degrading.
- Offline/air-gapped validation and any export/report feature.
- Compare the self-hosted version against the SaaS version. The self-hosted bundle is routinely several
  releases stale while the SaaS runs current code — then **upgrade the stale one, with data in it**, to
  current (scope 11). Comparison finds the gap; the upgrade finds what the gap costs a customer.

## 5. Licensing and entitlement lifecycle

The cross-product scope, and historically the richest. Run the whole arc on a test tenant:

- Request → **email arrives** (sender, branding, tier label, MIME structure, reply-to, BCC) → activate →
  use → approach expiry → expire → grace. Verify both what is sent and what is deliberately *not* sent.
- **Uniqueness and idempotency**: request twice. Then attack uniqueness with the near-misses — case,
  whitespace, `+tag` subaddressing. One mailbox minting unlimited stacked 30-day Enterprise trials, each
  with a fresh clock, came from subaddressing being unnormalised while case was normalised.
- **Does a repeat request re-send?** If yes, a public CORS-open endpoint is an unauthenticated mailer
  pointed at arbitrary third parties — and if sales is BCC'd, at the business's own inbox, with the
  sending domain's reputation as collateral.
- **Gates that are not controls**: a hardcoded free-email denylist with no MX or DNS validation filters
  casual signups and nothing else. Report it as friction, and move the abuse argument to the mechanisms
  that actually bound loss.
- Activation semantics: node locking, seat counting, reactivation after hardware change, concurrent
  activation.
- Validate/verify endpoints: expired, revoked, wrong product, wrong tenant.
- Count seats consumed by your own testing and put it in the cleanup ledger.

## 6. Secondary and free products

Free products get the least QA and carry the most reputational weight, because they are the first contact.

- The core function on representative real-world inputs, not toy ones. Framework assemblies, large files,
  obfuscated inputs — whatever is hard.
- Output fidelity measured, not eyeballed: build a fixture, count lines, diff before and after.
- Any export feature: open the exported artifact in its native toolchain and confirm it builds or runs.
- Version metadata, signing, and the shipped README's accuracy. READMEs on free products routinely
  document no CLI that exists and list shipped features as "next milestones".
- Pricing and marketing pages for a free product: check they do not offer editions, quotes or comparisons
  that do not exist.

## 7. Telemetry and privacy

- Trigger real client events from each product and capture the actual egress.
- Enumerate every route the telemetry host serves, including `OPTIONS`. Check the advertised CORS headers
  for what other authenticated surfaces that gateway fronts.
- Look for PII in payloads *and* in the hostname's other duties. Download redirectors observe IP against
  product and platform, which combined with a lead sink on the same host is a privacy architecture
  finding even when storage is separate.
- Consent and opt-out, verified by observing egress afterwards.
- Per-brand or per-tenant separation, if claimed.
- State the boundary of what you could verify without backend read access.

## 8. Security and abuse, non-destructive

Read-only and non-destructive throughout. The aim is to find what a bored attacker finds in an hour.

- Input handling on every public form: script payloads, template syntax, SQL metacharacters, oversized
  input, Unicode. Check reflection in the response *and* in whatever downstream artifact it reaches
  (email, dashboard, log).
- Auth on admin endpoints: absent, malformed, wrong-tenant tokens.
- Rate limits: find the real limit, and find what partitions it.
- Enumeration oracles on public endpoints.
- Secrets in responses, page source, bundled JS, source maps and container layers.
- Security headers on authenticated surfaces, and session token storage.
- Artifact integrity: are the downloads the expected files, correctly signed.

Stop at proof of reachability. Do not escalate, pivot, or exfiltrate; report the surface.

## 9. Documentation conformance

Its own agent and its own deliverable: the coverage matrix and the two coverage numbers. The full playbook
is `references/docs-conformance.md`; read it before extracting a single claim. In outline:

- **Inventory every doc surface** — docs site, every README, `--help` output, API reference and schema
  files, quickstarts, sample repos, changelog, marketing and pricing claims, `llms.txt`, container labels
  and compose/Helm examples, docstrings, tooltips, and error messages that name a variable or path. The
  scattered duplicate copies are the ones that have gone stale.
- **Extract every executable claim** with a source location, then **run it verbatim** — copy-pasted, never
  paraphrased, because paraphrasing supplies the parameter the example omits and silently repairs the bug.
- **Enumerate the real surface from code** — route registrations, every environment-variable read, the
  option parser, the config schema, exported symbols, container env/ports/labels — and subtract what is
  documented. The remainder is undocumented surface, and nothing else in the run finds it.
- **Judge which side is the defect** for each divergence, with reasoning. Sometimes the doc is right and
  the product is the bug; read the commit that introduced the divergence before deciding.
- **Report both numbers with denominators** and keep unexercised claims visible as `BLOCKED` rows.

Pay particular attention to **multi-mode products** — SaaS vs self-hosted, CLI vs GUI, cloud vs air-gapped.
They accumulate near-identical identifiers whose differences only matter in one mode, and the docs for the
less-travelled mode are the ones nobody has ever run. That is exactly where the prior run's worst blocker
lived: the self-hosting page named the client SDK's environment variable instead of the service's, so
following the documentation was identical to supplying no licence, with a green `/health` the whole time.

## 10. State: correctness and durability under fault, time and concurrency

The scope for anything that keeps data. Its question is never "did the operation succeed" but "is the
result still correct after the thing the product claims to survive". Run it in an environment you created
and own, under load that resembles use — a system idle during a fault proves nothing about one that is busy.

- **Keep your own ledger of what the product acknowledged.** Every write the client got an ack for: key,
  value, version or sequence, time, node that answered. The ledger is the oracle. The product's own state
  is the thing under test and cannot grade itself.
- **Baseline first.** Run the workload with no fault and reconcile ledger against read-back. If the
  baseline does not reconcile, stop: either the harness is wrong or the product loses data without help,
  and you need to know which before injecting anything.
- **Prove the harness can see a loss.** Delete one acknowledged key by hand, or corrupt one row, and
  confirm reconciliation reports exactly one Missing. A certification that has never failed has never been
  shown to detect anything — durability "passes" built on harness false-negatives are why this bullet
  exists.
- **Inject the real fault class, one at a time, under load.** Process kill, graceful stop, paused or slow
  process, network partition (symmetric and asymmetric), half-open connection, full disk, clock skew, DNS
  failure, dependency down. These are different failures with different bug populations; a kill does not
  stand in for a partition. Record the schedule exactly: what, which node, at what second, for how long.
- **Wait for the product's own "converged" or "healthy" signal, record how long it took, then reconcile
  anyway.** Three numbers: Missing (acknowledged, now absent), Stale (present, old value), Wrong (a value
  never written). Convergence time is itself a finding when it exceeds the docs or a client's retry
  budget — file it as availability, not loss, so the operator triages it correctly.
- **Run it twice at once.** Two clients racing the same operation — two activations against one seat, two
  inserts of one unique key, two edits of one record, two consumers on one offset. Sequential "try it
  twice" finds non-idempotency; concurrent finds double-issue, double-charge and lost update, which are
  different bugs.
- **Move the clock.** Forward past expiry, backward past issuance, across a DST boundary, skewed between
  nodes. Anything with a TTL, lease, trial, schedule or token lifetime has a bug population reachable only
  this way.
- **Check what the product says about itself against what you measured.** "Healthy", "replicas in sync",
  "run succeeded", "sync complete", lag = 0, seats = 3. A self-report that disagrees with your ledger is
  its own finding, separate from the data defect, because every customer's monitoring is built on the
  self-report.
- **Stop fast, diagnose fast.** Small N and short duration first, with a hard cutoff and a stall detector
  that exits when progress freezes; scale up only after the short run reconciles. The long certification
  is a separate deliverable with its own status — see `iteration-cycles.md`, "When a verification run
  takes hours".

## 11. Upgrade, migration and rollback

The customer who upgrades has data the fresh install does not. Every other scope starts from empty; this
one starts from full.

- Install the **previous released** version from the real public path — the one customers actually have,
  which for a self-hosted product is often several releases behind the SaaS. Create representative data
  through the product. Record counts and checksums.
- Upgrade **the way the docs tell a customer to** — in place, rolling across nodes, package over package,
  migration command — then read the data back and reconcile. Then open the UI on it: a migrated row that
  exists but no longer renders is still lost to the customer.
- **Mixed-version is a state, not a transient.** For anything clustered or client/server, run with half
  the nodes upgraded, and an old client against a new server and the reverse, long enough to do real work,
  then reconcile. Wire-format and schema changes show up only here.
- **Roll back.** Downgrade onto the migrated data. If the product does not support it, the docs must say
  so and the upgrade must refuse to proceed without a backup — test that the refusal actually happens.
- **Restore.** Backup on old, restore onto new; backup on new, restore onto new; and point-in-time if
  claimed. "Backup completed" is a self-report; a restore that reconciles is evidence.
- **Config and identity survive.** Settings, credentials, registered identifiers, data-directory paths,
  licence state, site or geo config on ephemeral storage. `fix-phase.md` already tells the fixer that a
  rename is a migration; this is where the tester proves it.
- **Skip-version paths** the docs allow (N-2 → N) are exercised; paths the docs forbid are confirmed
  *refused*, not merely avoided.

## 12. Experience and diagnosability

Cross-cutting with an owner, like scope 9. Every other scope produces the raw material on first contact;
this scope's owner holds the baseline, runs the two deliberate audits, and keeps the usability section
from becoming decoration. Full playbook: `references/experience.md`.

A dedicated experience agent sweeping its own surfaces would be **warm by definition** — it arrives after
another agent has already installed the thing. That is why the perishable measurement is delegated outward
and only the consolidation is owned here.

The owner:

- **Consolidates the first-run baseline** — one row per surface per iteration: time, steps, exits from the
  product, gave-up point. A rising number after a fix is a regression no correctness test can see; it is
  this scope's equivalent of a reopened finding.
- **Audits the error inventory** against the five questions in `experience.md`: what happened, what to do,
  which specific thing to change, is it reachable at all, does it blame the user. Group by root cause —
  one bad message style across three surfaces is one finding. For operator-facing products, log lines and
  metric names *are* the error messages; audit them the same way.
- **Takes the diagnosability measurement from scope 10's runs.** For each injected fault, the time from
  injection to the moment an operator reading only the product's own output — status, console, CLI, logs,
  metrics, listing which were consulted — could name the condition and the action. This costs no extra
  run; it costs a clock and a list. "Never — the condition was invisible until reconciliation" is the
  finding that is also an outage.
- **Runs the accessibility minimum** on the core task where a UI exists. Where none does, write "N/A — no
  UI; terminal output checked for colour-only signalling and `NO_COLOR`" and move on. Report it as its own
  subsection either way.
- **Checks the defaults.** Install with nothing configured and list every default a newcomer inherits that
  is unsafe, slow, insecure or surprising, and which of them the quickstart silently relies on. Defaults
  are the experience most users will actually have, and nobody chose them.

Anything that **tells the user something false** — a success panel for a swallowed request, a green status
over stale data, "0 instances" with no error — is filed as a product bug *and* an experience finding under
one id. It is the one class that always belongs in both sections.

## Platform coverage

Execution coverage is limited by the host you are on; **artifact coverage is not**. Do download, archive
contents, checksum, metadata and signature checks for every platform regardless, then run natively what
you can, use containers or CI runners for what you can borrow, and list every remaining platform × scope
cell as not-verified with the reason. Hosted CI runners are a legitimate way to reach another OS — but
treat anything you push there as public, and never put real credentials in a CI run.
