# Principles

Ten rules, stated once, that hold across every skill in this plugin. Every SKILL.md links here rather than
restating them, because a rule written in fifteen places is fifteen rules that drift.

They are not aspirations. Each one came from a run where its absence cost something, and most are
enforced — by `hub.py`, by the dashboard's verdict function, or by a check in `shared/scripts/`. Where a
rule is enforced, this file says by what.

---

## 1. Do the thing. Don't check that the thing responds

The single failure mode that makes any of this worthless. A real prior run declared **"0 bugs"** after
checking HTTP status codes, page loads and link resolution. At that moment the product's entire trial-key
flow was broken: the issuing endpoint returned 403, the delivery email was malformed, there was no sales
copy, and a deploy pin meant the new code was not serving. Every one of those was reachable in minutes by
*requesting a key*. None was reachable by *checking that the page loads*.

So: request the real key. Activate the real licence. Run the real binary. Read the real email. Deploy the
real image. **Status 200 is not a passing test. A green build is not a passing test.**

And for anything that keeps data, that sentence is only half of it. **Then go back and check the thing is
still there.** A write that returned OK is a *response*; the thing is the value being present — on every
replica the product promised, after the failure the docs say it survives, after the upgrade, a week later.
An acknowledged write is not a durable write until you have read it back after the failure.

This applies past QA. A PRD that says "users can export" and a design that shows an export button are both
responses. The thing is an export a real user completed and opened.

## 2. Every number has a denominator

"100% coverage" with no stated denominator is the same empty claim as "0 bugs": it sounds like a result and
carries no information. With the denominator stated it is checkable, and a reader who disagrees with your
enumeration can say so — which is the point.

This binds every role. A coverage figure, a research sample, a success metric, a launch claim, a capacity
number: state what it is out of and how you enumerated it. A metric with no denominator is not read, it is
asserted.

*Enforced:* `metric` items cannot reach `READ`
without a `denominator` field.

## 3. An oracle exists outside the product and outside your own judgement

**A case whose oracle is the product's own report of itself is not a case.** `/health: ok` grades nothing.
A green build grades nothing. The cluster's own `missing: 0` grades nothing — your own ledger of what the
product acknowledged, diffed against what you can read back, does.

And the independent thing must **predate the run**: the operator's price list, the curriculum's answer key,
your ledger written at ack time, the published spec, a pre-backup fingerprint, a count. *"Looks right"* and
*"behaves as expected"* name no reference; they are your eyes, which is the same failure one level up.

The generalisation past QA: an acceptance criterion a PO cannot hand to someone else to grade is not a
criterion, it is a hope. A design review finding that rests on taste is answered with "that's subjective"
and the whole section becomes decoration.

*Enforced:* `case` items require an `oracle` field; a scope whose calibration row has not passed
contributes no `PASS` to the verdict.

## 4. Every finding and every claim states what it does NOT claim

Often the most valuable line in a report. One privacy finding proved that customer PII was POSTed to a
host branded "telemetry" — directly observable — while explicitly *not* claiming the PII landed in the
usage store, because establishing that needed a read key nobody had supplied. Stating the boundary is what
made the claim trustworthy instead of merely alarming.

Same for an insight ("what this does not show", with its sample size), a metric reading, a launch claim and
a go/no-go memo. A claim with no stated boundary invites the reader to assume the widest one.

*Enforced:* `insight` items require a `does_not_show` field; a `release` cannot reach `GREEN` without a
`does_not_cover` field.

## 5. Corrections go in writing

When fresh access — code, a key, a working deployment — disproves something already reported, the
correction goes into the report under its own heading, naming what was right and what was wrong. This is
not self-flagellation; it is the mechanism that keeps the rest of the document trustworthy, and it is
usually the most-read section.

A report with no corrections section, on a product of any size, is a report nobody re-checked.

## 6. Verdicts are computed, never written. `NO VERDICT` is the default

Without a computed verdict the reader computes one themselves from an empty blocker table — which is the
"0 bugs" report with better typography. A run can show ten agents, 180 cases and zero blockers while the
one row that would have caught a cross-tenant data leak sits `BLOCKED` at the bottom.

So every condition names the rows that satisfy it, and a condition with **no rows at all** yields
`NO VERDICT` rather than a pass. Not knowing is not the same as being fine. Every green states its bounds —
the digests, topology, tenant shape and dataset size it covers — and what it does not cover.

*Enforced:* `shared/scripts/dashboard.py`. Also the release lifecycle: only the operator may ship against
`NOT_GREEN` or `NO_VERDICT`, and only with a reason in writing.

## 7. The producer claims; a different role accepts

DEV claims `FIXED`; only QA may `CLOSE`. DEV marks a story `DONE`; only the PO may `ACCEPT` it, and only
when its linked cases pass. The PM drafts a PRD; the sponsor approves it. QA sets severity; the operator
sets priority. The analyst reads a metric; the PM interprets it.

`FIXED` is a claim about the work. `CLOSED` is a verdict about the product. They are different statements
made by different parties on different evidence, and collapsing them is what "we fixed it" means in a
post-mortem. **The author does not grade their own work** — and where one person holds both roles, the
report says so, because that is a material limitation of the evidence.

*Enforced:* `shared/hub/model.json` transitions, including a `different_actor_from` guard that refuses the
same person accepting their own claim while wearing the other hat.

## 8. Never put a secret in an artifact

Refer to credentials by role: "the test tenant's admin token". Real values live in one gitignored
directory — `.product-secrets/` by convention — and a brief gives an agent the **role and the path, never
the value**, because a value in a brief is a value in a transcript and in every report that quotes it.

The directory itself goes in the cleanup ledger as plaintext credentials, which is the second thing the
ledger is ordered by. And if a test environment is seeded from production data, **that data is production
data**: no copying it out, no pasting it into a provider.

*Enforced:* `shared/scripts/check_repo.py examples` fails on a real hostname, path, tenant id or key in any
example.

## 9. The cleanup ledger

Everything you create goes in a running ledger: cloud resources, test tenants, licence keys, production
rows, scratch repos, worktrees, files holding credentials. For each, who can remove it and whether it costs
money or stays exposed until they do.

Order it by what is billing or exposed **now**: cloud compute first, plaintext credentials second, cosmetic
leftovers last. **Verify teardown by re-listing**, not by trusting a delete call's exit code — a final
sweep printing `billable instances: NONE` is the deliverable; "I ran the terminate command" is not.

Open it at minute one, not at the end when you have forgotten half of it.

*Enforced:* `cleanup` items cannot reach `TORN_DOWN` without a `verified_by` field, and an open cleanup item
denies the verdict.

## 10. Reality beats paperwork

When the docs, the tickets and the code disagree, **report the disagreement** — do not pick one silently
and do not quietly reconcile them in your head.

This is the rule that makes an existing product tractable. Its backlog says one thing, its architecture
diagram another, and its running code a third; the gap between them is not noise to be tidied away, it is
the most valuable finding available, because it is what everyone on the team is already confused about.
The documented path that fails is a blocker regardless of how correct the product is underneath, since a
customer's first run *is* the documented path.

Where a product class has no written contract at all — no stated consistency model, no delivery guarantee —
file the missing contract as a documentation finding **and** grade the behaviour at the severity its
consequence earns, with the assumption named. You cannot grade a product against a promise it never made,
but its customers will.

---

## What is not a principle

Things that sound like they belong here and do not, because they are decisions rather than rules:
which methodology a team uses, which tracker, how long an iteration is, what the severity names are in the
client's own system. Those are the operator's, recorded in the product profile by
`/evidence:orient` and mapped once — never imposed.
