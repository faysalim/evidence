# Documentation conformance

The docs are the contract. A customer's first run is the *documented* path, so a documented path that
fails is a blocker no matter how correct the product is underneath. This scope exists because that failure
is invisible to every other scope: an agent testing the product the way the product wants to be used will
never discover that the docs say something different.

Run this as its own scope with its own agent, so the run produces one coverage matrix and one defensible
coverage number. Every other scope still checks the docs for its own surface as it goes — but without a
dedicated owner, nobody ends up holding the number.

## Contents

- [The three failure directions](#the-three-failure-directions)
- [Coverage must be two-way](#coverage-must-be-two-way)
- [Step 1 — Inventory the documentation surfaces](#step-1--inventory-the-documentation-surfaces)
- [Step 2 — Extract executable claims](#step-2--extract-executable-claims)
- [Step 3 — Run every claim verbatim](#step-3--run-every-claim-verbatim)
- [Step 4 — Reverse coverage: enumerate what the product actually exposes](#step-4--reverse-coverage-enumerate-what-the-product-actually-exposes)
- [Step 5 — Coverage arithmetic, stated honestly](#step-5--coverage-arithmetic-stated-honestly)
- [Deciding which side is the defect](#deciding-which-side-is-the-defect)
- [Doc defects worth checking directly](#doc-defects-worth-checking-directly)
- [What a 100% claim requires](#what-a-100-claim-requires)

## The three failure directions

Most doc QA finds only the first. The third is where the support tickets come from.

1. **Wrong** — the doc says X, the product does Y. A website told self-hosting customers to set
   `KEYRIGHT_LICENSE`; the service read `KEYRIGHT_SELF_LICENSE`. Following the instruction was
   byte-for-byte identical to supplying no licence at all, while `/health` stayed green — so the
   customer's monitoring reported a healthy instance that could not issue a single licence.
2. **Stale** — it was true once. Versions, prices, platform lists, and features listed as "next
   milestones" that shipped two releases ago.
3. **Missing** — the product has a flag, variable, endpoint or behaviour with no documentation anywhere.
   Invisible to anyone reading the docs, which is why it needs the reverse pass in Step 4.

## Coverage must be two-way

- **Forward (docs → product):** every executable claim in the docs is extracted and run verbatim.
  This catches *wrong* and *stale*.
- **Reverse (product → docs):** every surface the product actually exposes is enumerated from the code and
  checked for a documentation entry. This catches *missing*, and nothing else does.

A coverage number from one direction alone is not a coverage number. Forward-only coverage can read 100%
on a product whose docs describe a third of it.

## Step 1 — Inventory the documentation surfaces

Docs are scattered, and the scattered copies are the ones that go stale. Enumerate before extracting:

- The public docs site, page by page
- `README.md` per repository, and per published package
- In-product help: `--help` output, `man` pages, usage strings
- The API reference, and any OpenAPI/schema file
- Quickstarts, getting-started guides, and sample repositories
- Code samples *inside* docs, including ones in other languages
- `CHANGELOG` / release notes, and the release description on the published artifact
- Marketing and pricing pages — they make checkable claims about limits, platforms and features
- `llms.txt`, structured data, and anything else machine-readable that states facts
- Container documentation: image labels, `compose` examples, Helm values, env-var tables
- Docstrings / XML doc comments that surface in IDE tooltips
- Empty states, tooltips, and error messages that name a variable, path or command

Record where each lives, because the same claim repeated in five places drifts in four of them.

## Step 2 — Extract executable claims

A **claim** is any doc statement you can turn into a command, a request, or a check. Give each one an id
and a source location. The recurring kinds:

| Claim kind | Example | How it is checked |
|---|---|---|
| Command invocation | `nebula register --key <k>` | Run it verbatim |
| Endpoint contract | `POST /v1/trial {product, tenant, email}` | Call it; diff the response shape against the documented shape |
| Environment variable | `KEYRIGHT_LICENSE` accepts a path or inline JSON | Set each accepted form; observe behaviour |
| Config key and default | `timeout` defaults to 30s | Read it unset; confirm the default |
| CLI flag | `--verbose` | Run with and without |
| Stated limit or quota | "3 resends per day" | Reach the limit |
| Version number | "current release is 1.1.7" | Compare to the published artifact's metadata |
| Platform list | "Windows, macOS, Linux" | Compare to the download matrix |
| Price | "$149/mo" | Compare to visible copy, client-rendered value and structured data |
| Prerequisite / port / path | "requires Postgres 14 on 5432" | Deploy with exactly that |
| Behavioural guarantee | "writes acknowledged at RF2 survive loss of one node" / "SERIALIZABLE" / "exactly-once delivery" | A scope-10 fault run designed to falsify the exact wording; the wording is the pass criterion. If the docs state no contract at all, that absence is the first finding |
| Performance claim | "1M ops/s on 3 nodes" / "p99 < 10 ms" | Reproduce on a stated rig; report rig, workload and number. A claim with no stated conditions is itself a doc defect |
| Compatibility / upgrade claim | "in-place upgrade from 2.x" / "Android 8+" / "1.x clients work against 2.x servers" | Scope 11: upgrade from the *oldest* claimed version; connect the *oldest* claimed client |
| Policy declaration | store data-safety form, privacy-policy data categories, compliance statements | Compare against observed egress and behaviour (scope 7); a mismatch is a store-policy or legal exposure, not a nit |

**Copy the claim, do not paraphrase it.** Paraphrasing silently repairs the doc's defect in your head —
you supply the parameter the example omits, or the variable name you know is right. Paste it exactly as a
customer would.

## Step 3 — Run every claim verbatim

One row per claim, filled in as you go:

```
| id | claim | source | how exercised | result | evidence |
|----|-------|--------|---------------|--------|----------|
| D14 | POST /v1/trial {product,email} returns key+tier | docs/trials.md:88 | curl, verbatim payload | FAIL | 400; `tenant` effectively mandatory in prod |
```

`result` is `PASS`, `FAIL`, or `BLOCKED` with a reason. `BLOCKED` rows stay in the denominator — they are
the honest cost of missing access, and quietly dropping them is how a coverage number becomes a lie.

**This ledger is a test-case register of one kind**
(`${CLAUDE_PLUGIN_ROOT}/skills/qa/references/test-cases.md`): a claim is an action, the
documented wording is the oracle, and the row carries its result and evidence. The run-wide register adopts
these rows **by reference** — `D1`–`D<n>` with their totals — and does not re-list them, so the two
denominators never double-count the same work.

Where a claim fails, run the *working* variant too. Knowing that the documented call fails but the call
with one extra parameter succeeds is what turns the finding into a one-line doc fix.

## Step 4 — Reverse coverage: enumerate what the product actually exposes

Enumerate from the code, then subtract what is documented. The remainder is the undocumented surface.

| Surface | How to enumerate it |
|---|---|
| HTTP routes | Router registrations / route table (`MapGet`, `MapPost`, decorators, route files) |
| Environment variables | Grep the environment-read API: `Environment.GetEnvironmentVariable`, `process.env`, `os.environ`, `getenv`; dedupe |
| CLI commands and flags | The option-parser definitions, not `--help` (help text is itself a doc that can be wrong) |
| Config keys | The config schema or binding class, plus defaults |
| Public API | Exported/public symbols of each shipped package |
| Container surface | The image's declared env, labels, ports, volumes, entrypoint |
| Feature flags | The flag registry or their read sites |
| Error codes | The enum or constant table |

Then diff. An undocumented environment variable is a support ticket with a long fuse; an undocumented
endpoint is either dead code or an unannounced API someone will build on. Report both.

A useful standing rule: **every environment variable has an entry in a dedicated reference page, and that
page is re-synced on every docs pass.** It is cheap to maintain and it makes this diff trivial next time.

## Step 5 — Coverage arithmetic, stated honestly

Report both numbers with their denominators and how the denominator was enumerated:

```
Forward coverage  — documented claims exercised:    142 / 142  (100%)
                    of which PASS 118 · FAIL 19 · BLOCKED 5
Reverse coverage  — product surface documented:     96 / 113   (85%)
                    undocumented: 14 env vars, 2 routes, 1 CLI flag
Denominators: claims extracted from the 9 doc surfaces in §1 (list);
              surface enumerated from route table, env-read grep, parser defs.
```

**"100% coverage" means nothing without the denominator and the enumeration method.** An unqualified 100%
is the same failure as the "0 bugs" report this whole skill is built against: it sounds like a result and
contains no information. With the denominator stated, 100% forward coverage is a strong, checkable claim —
and a reader who disagrees with your enumeration can say so, which is exactly what you want.

Keep `BLOCKED` rows visible in the final report as the not-verified list, each with the reason and what
would unblock it.

## Deciding which side is the defect

When docs and product disagree, which one is wrong is a real judgement, not a formality — it decides
whether the fix is a sentence or a release.

Ask: which behaviour is correct *by design*? Read the commit that introduced the divergence. In the env-var
case the commit history settled it — the author had deliberately introduced two similarly named variables
for two different consumers (the client SDK reads one, the issuing service the other), so the product was
right and the docs had named the wrong consumer's variable in a self-hosting context. The fix was one
sentence; the severity was still blocker, because the documented path was a silent no-op.

Watch specifically for **docs for one deployment mode bleeding into another**. Multi-mode products (SaaS
vs self-hosted, CLI vs GUI, cloud vs air-gapped) accumulate near-identical identifiers whose differences
only matter in one mode, and the docs for the less-used mode are the ones nobody runs.

## Doc defects worth checking directly

These recur often enough to check on purpose rather than hope to stumble into:

- A documented response shape the API never returns. One guide promised `key`, `tier` and `seats`; the
  endpoint returned none of them, so the guide's own sample code would have shown users
  `Your trial key: undefined`.
- A canonical example that fails because a parameter became effectively mandatory — the documented call
  returned 400 in production.
- A README that documents no CLI although one ships, and lists already-shipped features as "next
  milestones".
- Install or activation instructions naming the wrong identifier (see above).
- Docs for the current release while the only downloadable bundle is three minor versions behind.
- Version numbers, platform lists, prices and limits that disagree with the product.
- Copy-paste blocks that do not paste: smart quotes, line continuations, placeholders that look literal.
- A stated default that changed in a release and was never re-documented.
- Documentation of a *removed* feature — rarer, worse, because customers build on it.

## What a 100% claim requires

Before writing the number, confirm every line:

- [ ] All documentation surfaces from Step 1 enumerated and listed in the report
- [ ] Every executable claim extracted, with a source location
- [ ] Every claim exercised verbatim, or marked `BLOCKED` with a reason
- [ ] Each exercised claim carries evidence a reader can re-run
- [ ] Product surface enumerated from code for each applicable surface type
- [ ] Undocumented surface items listed individually, not summarised as a count
- [ ] Both coverage numbers stated with their denominators and enumeration method
- [ ] For each disagreement, a stated judgement on which side is the defect, with the reasoning
