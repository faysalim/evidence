# Case file: a four-repo, full-business QA run

The engagement this skill was distilled from, with real numbers. Read it when you want to see the method
produce a result, or to calibrate what a thorough run actually yields.

**One engagement, of one shape.** `${CLAUDE_PLUGIN_ROOT}/shared/domains/` exists because of what this
file does not contain:
no cluster under fault, no migration with data in it, no device matrix, no pipeline reconciliation. Scopes
10, 11 and 12 were all blind spots of this run, which is why they are now families rather than footnotes.

**Shape:** one business, three products (an obfuscator with GUI + CLI, a licensing platform with SaaS and
self-hosted modes and four client SDKs, a free decompiler), one marketing site in four locales, a telemetry
gateway. Four repositories. Eight scopes, run as parallel agents. Report-only, then the mandate was lifted
to fix, delivered as pushed branches with no PRs and no merges.

**Outcome:** **37 ranked findings** — 2 blockers, 20 majors, 15 minors/polish — of which 14 were fixed
across 20 pushed branches, 11 required an operator decision (answered and implemented in a later session),
and the rest were deploy, release, procurement, data or investigation items that no QA pass could close.

The immediately prior QA run on the same business had reported **"0 bugs"**.

## What the previous run did, and why it found nothing

It checked HTTP status codes, that pages loaded, and that links resolved. Every check passed. At that
moment the entire trial-key flow was broken: the issuing endpoint returned 403, the delivery email was
plain text and mis-branded, there was no sales copy at all, and a deploy pin meant new code was not
serving.

Every one of those was reachable in minutes by *requesting a key*. None was reachable by *checking that
the page loads*. That gap is the whole reason this skill exists.

## The two blockers, and how each was proved

**The documented install instruction was a silent no-op.** The website told self-hosting customers to set
`KEYRIGHT_LICENSE`; the service read `KEYRIGHT_SELF_LICENSE`. Following the documentation was
byte-for-byte identical to supplying no licence — and `/health` returned `200 {"status":"ok"}` throughout,
so every uptime check in a customer's monitoring would report a healthy instance that could not issue a
single licence.

Proved by **three runs of the same published container image, changing only the variable's name.** Nothing
else could explain the difference. Then the commit history settled *which side was the defect*: the author
had deliberately introduced two similarly-named variables for two different consumers — the client SDK
reads one, the issuing service the other — so the product was right and the docs had named the wrong
consumer's variable in a self-hosting context. A one-sentence fix, still a blocker.

**Published structured data undercut the real prices by up to 45%.** JSON-LD on the pricing page advertised
39/119/249 against real prices of 49/149/449, with the aggregate ceiling wrong too — while the same page's
visible heading contradicted its own structured data. Search engines publish the structured value as the
offer. Found by extracting and comparing the structured data separately from the visible copy, which is
the only way to find this class: both halves look right in isolation.

## Findings that only a real flow produces

- **`+tag` subaddressing defeated one-trial-per-email.** Case was normalised, subaddressing was not, so one
  mailbox could mint unlimited stacked 30-day *Enterprise* trials, each with a fresh clock. Found by
  attacking uniqueness with the near-misses of the reported input rather than the input itself.
- **Every repeat trial POST re-sent the email** — an unauthenticated mailer on a public, CORS-open
  endpoint, aimable at arbitrary third parties. Sales was BCC'd on each, so an attacker could bomb the
  business's own sales inbox using the business's own endpoint, with the sending domain's reputation for
  *genuine* keys as collateral.
- **The sales-lead POST was fire-and-forget** (`.catch(() => {})`), while the prospect was shown "Request
  received — we'll email your key" regardless. For the self-hosted product that POST was the *only*
  fulfilment trigger, so a failure lost the customer silently and nobody was notified.
- **The trial email's MIME was malformed** — boundary delimiter and the first part's headers sharing a
  line, so a strict parser saw no plaintext alternative at all, in a message carrying the customer's
  licence key. Found only by reading the raw message source.
- **Any unrecognised argument launched the GUI and never exited** — `--help`, `--version`, everything. A
  `--version` probe in CI hangs forever on a headless agent. Reported independently by the Windows and
  macOS agents against two different products: **one finding**, de-duplicated by root cause.
- **Cloud pricing shipped as the literal string "Loading plans…"** — no prices for crawlers or no-JS
  users, and the failure fallback showed neither prices nor a sales link.
- **Customer PII flowed through the telemetry-branded host.** `telemetry.example/lead` received name,
  email, company, free text and a visitor id; the same host was also the download redirector, so it
  observed IP against product and platform. The finding explicitly **did not claim** the PII landed in the
  usage store — that needed a backend read key nobody supplied. Stating the boundary is what made it
  credible.
- **Binary metadata was wrong on one product and right on its sibling** — `ProductVersion 1.0.0` for a
  1.1.2 release, company "Glass", empty copyright — so the correct pattern already existed in the org.
  Read off the built binary, not the release notes.

## The corrections, which were the most-read section

Code access disproved six things the black-box report had asserted. All six went into the report under
their own heading:

1. The repo's default branch `master` was **a month stale**; the live line was `release/2.5.0`. A fix
   worktree was created from the wrong one and caught just before editing.
2. A finding blamed on an unmerged PR was in fact **merged** — production was simply one commit behind. A
   deploy item, not a code item.
3. A root cause given by byte offset in rendered HTML would have **sent a fixer to the wrong file**. The
   real cause was an unfiltered loop plus a pre-existing hardcoded panel — and the *other* locale's page
   already had the correct filter and served as the reference implementation.
4. A finding's arithmetic claim was **overstated** — "about 20%" was defensible at 19.35% — and was
   withdrawn before anything was changed.
5. The published `2.5.0` image **predated its own `2.5.0` branch tip**, which broadened a release finding.
6. A later session corrected its own grouping: three decompiler defects had been written off as "all
   upstream, not fixable in our code". One was **a single wrong line in the product itself** — settings
   were constructed at the oldest language version and then passed to a method that only ever turns
   features *off*, so the apparent upgrade was a no-op and the decompiler ran with **70 of 111 feature
   flags false**. The product's main deliverable had been rendering all modern language constructs in
   lowered form. The other two were genuinely upstream, now *measured* across two upstream versions rather
   than assumed.

Point 6 is the one to remember: "it must be upstream" is a hypothesis, and it was wrong one time in three.

## What the fix phase added

- All work in **git worktrees**; the operator's four checkouts were never written to — one of them held
  same-day uncommitted work on a feature branch.
- **One branch per finding**, 20 in total, so each could be taken or rejected independently, with merge
  order and expected conflicts stated.
- Every new test **verified to fail against the unfixed code** first: 5 of 5 for one change, 5 of 7 for
  another, with the two guards named as passing either way by design.
- Website changes **driven in a real browser against the built output** (890 pages), with deterministic
  stubs injected to reach failure branches — checkout failure, lead POST 404 vs 200 with attempts counted
  via `performance.getEntriesByType('resource')`, both trial outcomes.
- A **regression found during fix verification**: a locale redirect using `location.replace()` on a
  path-only map dropped the query string, so `/order?product=keyright` landed on `/es/order/` with the
  product gone — silently reintroducing the exact defect the fix had just removed, one redirect later. It
  was also discarding `utm_*` parameters before analytics saw them.
- A **non-bug confirmed before being "fixed"**: `$1490/año` with no separator is correct `es-ES` under
  CLDR `minimumGroupingDigits=2`. Fixing it would have introduced a defect while closing nothing.
- One **own-goal worth repeating**: a newline escape flattened into a real newline inside an inline script,
  leaving an unterminated string literal. The build was green and the page rendered; the form did nothing
  at all. Only opening the page caught it.

## Calibration

| | |
|---|---|
| Scopes | 8 (this skill now has 9 — documentation conformance was a cross-cutting afterthought and should have owned a scope) |
| Ranked findings | 37 — 2 blockers, 20 majors, 15 minors/polish |
| Fixed in the fix phase | 14, across 20 pushed branches |
| Needed an operator decision | 11, delivered as a decision memo with options and a recommendation |
| Could not be closed by QA | deploys (2), a release, certificates (2), production data (1), investigations |
| Report corrections | 6 |
| Production side effects | 5 trial rows, all prefixed and listed in the cleanup ledger |

The decision memo mattered as much as the bug list. Eleven findings were intentional-but-arguable; written
as bugs they would have been argued with, and written as a memo with options and a recommendation they were
all answered in a single message and then implemented.
