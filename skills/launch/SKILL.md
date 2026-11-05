---
name: launch
description: Positioning, launch plan and customer-facing copy where every product claim links to a passing test case or is flagged unverified, and every price, limit and plan name is checked against the source of truth rather than the previous copy. Use when the user wants launch messaging, positioning, announcement or website copy, or a go-to-market plan written or reviewed. Not for the ship decision - that is evidence:release.
---

# Launch

`status: draft` — see `${CLAUDE_SKILL_DIR}/README.md`.

Marketing copy is the one artifact in this suite that a stranger reads and relies on without any way to
check it. So it gets the strictest version of the evidence rule: **every product claim in customer-facing
copy links to a passing case, or is flagged unverified and does not ship.**

This is not caution for its own sake. In the origin engagement, stale structured data undercut real prices
by up to 45% and was a **blocker**, because search engines publish structured data as the offer — the
marketing surface was making a commitment the product would not honour. And the same run found no sales
copy at all on a page whose entire purpose was conversion, which nobody noticed because nothing was
broken, exactly.

Items move only through `python "${CLAUDE_PLUGIN_ROOT}/shared/scripts/hub.py"`.

## What this skill produces

| Hub item | Note |
|---|---|
| `launch` | `DRAFT` → `CLAIMS_CHECKED` (requires `evidence`) → `APPROVED` by PM, Head of Product or operator → `LIVE` |
| `finding` | Where the copy is right and the product is wrong — that is a product finding, not a copy edit |
| `decision` | Where a claim cannot be substantiated and someone must decide whether to soften it or delay |

`CLAIMS_CHECKED` before approval is the gate. A claim table with no evidence column has not been checked,
it has been written.

## The claims table

Every product claim, one row, before any of it ships:

```
| claim (as it will appear)        | kind         | evidence                   | verdict    |
| "restores in under 15 minutes"   | performance  | case S10-12, PASS, 50 GB   | SUPPORTED  |
| "works offline"                  | capability   | case S2-07, PASS_SHORT     | SOFTEN     |
| "SOC 2 compliant"                | compliance   | no artifact                 | REMOVE     |
| "$149/mo"                        | price        | pricing source of truth     | SUPPORTED  |
| "unlimited projects"             | limit        | config: cap is 500          | REMOVE     |
```

Four verdicts, and only one of them ships as written:

- **SUPPORTED** — a `PASS` case or an authoritative source backs it, at the scale the claim implies.
- **SOFTEN** — true in a narrower form. "Works offline" over a `PASS_SHORT` becomes "queues changes while
  offline and syncs when you reconnect", which is both true and more useful.
- **REMOVE** — no evidence, or the evidence contradicts it. An "unlimited" that is capped at 500 is not a
  rounding error; it is the claim a customer will quote back during an escalation.
- **UNVERIFIED** — plausible, nobody has measured it. Allowed in internal drafts, **never** in published
  copy. If it matters, it becomes a `case` for QA and the copy waits.

**A performance claim with no stated conditions is itself a defect.** "3× faster" needs the rig, the
workload and the baseline, or it is unfalsifiable — which is `shared/principles.md` §2, and also what a
competitor's legal team looks for first.

## Prices, limits and plan names

Check these against the **source of truth**, never against the previous version of the copy. Copy is
copied, so an error propagates silently across a site, a deck, an email template and a store listing, and
then one of them gets fixed.

For each: where the value actually lives (config, billing provider, contract), what the site renders, what
the **structured data** says, what the checkout charges, and what the plan is called in the product's own
UI. Those five disagree more often than any of them is wrong alone — and the structured data is the one
nobody looks at, which is why it was the blocker.

`/evidence:qa`'s acquisition-surface scope exercises the same ground from the testing side; where both
run, reconcile once rather than filing twice.

## The launch plan

Short, and ordered by what is irreversible:

1. **What goes live, and where** — site, docs, store listing, in-product, email, partners. Each surface is
   a place a claim can be stale independently.
2. **The sequence, and what gates each step.** Nothing customer-facing goes before the release is
   `SHIPPED` in the hub, and the hub's release item is the gate rather than someone's recollection.
3. **What is irreversible.** A sent email, a published store listing, a tweet, a press embargo. These get
   a named approver, and they are the only items in this plan that need one.
4. **The rollback for the message**, not just the product. If the release is pulled, who un-says this?
5. **What support needs before, not after.** The three questions this launch will generate, with answers.
   Support finding out at launch is the most common self-inflicted launch failure.
6. **The metric** that tells you whether the positioning worked, inheriting its definition from the PRD
   (`/evidence:analytics` reads it).

## New product and existing product

For a **new** product, positioning rests on `insight` items from discovery, and the honest claims list is
short. Resist filling it with capability claims the product has not been measured on; a short, true launch
outperforms a broad one that generates escalations.

For an **existing** product the risk is different and larger: **the old copy is already live and already
wrong.** Inventory it before writing anything new — every page, template, store listing and deck that
states a price, a limit, a platform list or a version. The audit routinely finds more problems than the
new copy introduces, and they are already costing something.

## For the lead

Ask for the claims table and read the `verdict` column only. If every row says SUPPORTED, it has not been
checked — a real product has claims that need softening. Then ask which surfaces the price appears on and
whether structured data was one of them.

The last question before approving anything irreversible: **is the release `SHIPPED` in the hub?** Copy
that goes live ahead of the thing it describes is the one launch mistake that cannot be quietly fixed.

## Open questions

- Whether `launch` should require links to the specific `case` ids backing each claim, so the dashboard can
  show an unsupported claim directly. That is the strongest enforcement candidate here.
- No template ships for positioning itself, deliberately — positioning is not a form. The claims table is
  the artifact this skill is built around.
- The structured-data and price-propagation warnings have real provenance from the origin engagement. The
  launch-plan ordering is reasoned.

| File | Read it when |
|---|---|
| `${CLAUDE_PLUGIN_ROOT}/shared/principles.md` | First. §2 and §4 govern this skill |
| `${CLAUDE_PLUGIN_ROOT}/shared/references/evidence-standard.md` | What backs a claim, per surface — including structured data |
| `${CLAUDE_PLUGIN_ROOT}/shared/vocabulary.md` | Case results, so you can read what a `PASS_SHORT` permits |
