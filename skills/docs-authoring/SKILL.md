---
name: docs-authoring
description: Write user and admin documentation from the product's observed behaviour rather than from tickets, then verify every claim by running it verbatim as a customer would, and enumerate the real surface to find what is undocumented. Use when the user wants user docs, admin guides, API reference or a quickstart written, reviewed or verified against the product. Not for marketing copy - that is product-suite:launch.
---

# Docs authoring

`status: draft` — see `${CLAUDE_SKILL_DIR}/README.md`.

Documentation is the contract, and a customer's first run **is** the documented path. So a documented path
that fails is a blocker regardless of how correct the product is underneath — the origin engagement's
sharpest blocker was exactly this: the site told customers to set one environment variable, the service
read another, and `/health` returned `200 {"status":"ok"}` throughout, so every uptime check was green on
an instance that could not issue a single licence.

This skill therefore writes docs the only way that cannot produce that: **from observed behaviour, then
verified by running every claim verbatim.** `${CLAUDE_PLUGIN_ROOT}/shared/references/docs-conformance.md`
is the method; it is the same file QA's scope 9 uses, run from the authoring side.

Items move only through `python "${CLAUDE_PLUGIN_ROOT}/shared/scripts/hub.py"`.

## What this skill produces

| Hub item | Note |
|---|---|
| `doc` | `DRAFT` → `VERIFIED_AGAINST_PRODUCT` (requires `evidence`) → `PUBLISHED` by a different actor |
| `finding` | Where the product, not the doc, is the thing that is wrong |

The middle state is the whole skill. A `doc` cannot be published straight from `DRAFT`, because a draft is
what you believe and the verified state is what you ran.

## Write from behaviour, not from tickets

A story says what was intended. The build says what happened, and they differ more often than anyone
expects — a feature shipped with a different flag name, a default that changed in review, an error message
that says something else.

So: **do the thing first, then write it down.** Install it as a customer would, run the flow, record the
exact commands, payloads and outputs, and write from that transcript. Where the product's behaviour
surprises you, that is either a doc you would have got wrong or a `finding` — and you cannot tell which
until you ask, so raise it rather than documenting around it.

Never paraphrase a command, an identifier or a payload. Paste it. Paraphrasing silently repairs the
product's bug in your head: you supply the parameter the example omits, and the customer does not.

## Verify forward: run every claim verbatim

Extract every executable claim and run it exactly as written. The recurring kinds, from
`docs-conformance.md`: command invocations · endpoint contracts and payloads · environment variables ·
config keys and their defaults · CLI flags · stated limits and quotas · version numbers · platform lists ·
prices · prerequisites, ports and paths · behavioural guarantees · performance claims · compatibility and
upgrade claims.

One row per claim, `PASS` / `FAIL` / `BLOCKED`, with the evidence:

```
| id  | claim                          | source        | how exercised      | result | evidence |
| D14 | POST /v1/trial {product,email} | trials.md:88  | curl, verbatim     | FAIL   | 400; `tenant` is effectively mandatory |
```

`BLOCKED` rows **stay in the denominator** — they are the honest cost of missing access, and dropping them
is how a coverage number becomes a lie. Where a claim fails, run the *working* variant too: knowing that
the documented call fails but the call with one extra parameter succeeds is what turns this into a
one-line doc fix.

## Verify reverse: find what is undocumented

Nothing else finds this, and an undocumented environment variable is a support ticket with a long fuse.
Enumerate from the code — route table, every environment-variable read, the option parser, the config
schema, the exported symbols, the container's declared env, labels, ports and volumes — then subtract what
is documented. The remainder is undocumented surface.

Report both numbers **with their denominators and how you enumerated them**. "100% coverage" with no stated
denominator carries no information; with it, a reader who disagrees with your enumeration can say so, which
is the point (`shared/principles.md` §2).

## Existing product: the gap is the deliverable

For an existing product the first pass is not writing, it is measuring. `/product-suite:orient`'s
capability inventory gives you the real surface; compare it to the published docs and report three
numbers with their denominators:

- **Claims that fail when run verbatim** — each one a blocker-class finding, because it is the path every
  new customer takes.
- **Surface that is undocumented** — per kind: endpoints, variables, flags, config keys.
- **Docs describing behaviour the product no longer has** — the most embarrassing kind, and the easiest to
  find once you are running the claims rather than reading them.

Then fix in that order. A doc set with 40 undocumented variables and 3 broken quickstart commands should
fix the 3 first, every time.

## After a release

Fixes change behaviour, and the docs that described the old behaviour are now wrong. So after each release:
re-run the forward claim set for every surface the release touched, and redo the reverse enumeration —
**fixes add environment variables, flags and endpoints, so new undocumented surface is created by the very
act of fixing.** That is not a hypothetical; it is the normal case.

**On a small team.** A `doc` is `PUBLISHED` by a different actor than the one who drafted it, and
a finding you file is verified and closed by QA — not by you, however obvious the fix.

## For the lead

Two questions. **Was every claim run, or read?** — the difference is the whole skill, and a verified doc
with no evidence column was read. And **what is the denominator on the coverage number?** If there is
none, the number is not reviewable.

Then check the direction nobody remembers: ask for the undocumented-surface count. A team that only ever
verifies forward has no idea how much of its product is undocumented, which is where the support load
comes from.

## Open questions

- Whether the claim ledger should be `case` items in the hub rather than a table in the doc. QA's scope 9
  adopts the ledger by reference today; making them cases would unify the denominators but risks
  double-counting, which is exactly what the reference-adoption rule avoids.
- No template ships for a quickstart or an API page. The claim ledger is the artifact this skill is built
  around; page structure is the team's convention from `orient`.
- The forward/reverse method has real provenance. The ordering advice (fix broken claims before filling
  gaps) is reasoned.

| File | Read it when |
|---|---|
| `${CLAUDE_PLUGIN_ROOT}/shared/principles.md` | First. §1, §2 and §10 govern this skill |
| `${CLAUDE_PLUGIN_ROOT}/shared/references/docs-conformance.md` | **The method.** Claim kinds, both directions, what a coverage claim requires |
| `${CLAUDE_PLUGIN_ROOT}/shared/references/evidence-standard.md` | What counts as proof per surface, when running a claim |
