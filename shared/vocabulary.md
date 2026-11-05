# Vocabulary

One definition of every shared term, used by every skill in this plugin and by the dashboard. A skill that
restates a tier or a status here instead of linking to it creates a second source of truth, and the two
copies drift — which is how a `blocker` in one skill's report becomes a `major` in another's.

Three vocabularies live here: **severity** (how bad), **closing action** (who closes it, and with what),
and **states** (where an item is). Item states themselves are machine-readable in
`${CLAUDE_PLUGIN_ROOT}/shared/hub/model.json`, which is what `hub.py` enforces; this file is the prose.

## Severity

| Severity | Test |
|---|---|
| **critical** | Data the product acknowledged is lost or corrupted, a tenant / user / role boundary is crossed, or money moves wrongly. Nothing the customer does recovers it, and no deploy undoes damage already done. Examples: acknowledged writes missing after a fault the docs say is survived; two nodes accepting writes during a partition; a role's export containing records it cannot see; a retried checkout charging twice |
| **blocker** | A customer following a documented path cannot succeed, loses money, or is misinformed in a way that reaches the public (wrong published price, broken acquisition flow, a silent no-op install instruction) — *or the business's control over its own revenue or obligations is defeated* (entitlement bypass, fail-open licence validation, incomplete erasure, a store-policy violation that removes the listing) |
| **major** | A real customer journey is damaged, or the business loses revenue or leads, but a workaround exists |
| **minor** | Wrong, visible, and worth fixing, but nobody is blocked or misled materially |
| **polish** | Correct but rough |

Severity is by consequence. A stale structured-data price undercutting the real one is a blocker even
though the fix is one line, because search engines publish it as the offer.

**Silence is a multiplier** — the tiebreaker between adjacent tiers, not part of the definition. The same
defect with a loud, visible error sits lower, because the customer can act on it; one that happens behind
a green dashboard sits higher. Loss of acknowledged data is `critical` whether or not the product
announces it, because the consequence does not depend on the loudness.

**Where the docs state no contract** — what consistency, what isolation level, what delivery guarantee —
file the missing contract as the first finding in scope 9 **and** file the data finding at the severity its
consequence earns, with status `DECIDE` and a first line that names the assumption: *"graded as if
acknowledged writes survive one node loss; if the intended contract is weaker, downgrade it and document
it."* A `DECIDE` carrying `critical` or `blocker` severity **is still open at that severity** for the
verdict and for the stopping rule. You cannot grade a product against a promise it never made — but its
customers will, so the grade is stated and the operator overrules it in writing or not at all.

This is also what "severity by consequence, not by effort" requires: the consequence of losing
acknowledged data does not depend on whether a doc page promised to keep it.

**Severity is the worst consequence the defect causes, whatever section it is filed in.** An experience
defect inherits the severity of the action it leads the user into: a confirmation dialog that invites a
reflexive click on a cluster wipe is `critical`, because the consequence is the wipe; the same dialog on a
rename is `minor`. File such findings in both sections under one id — the experience section explains
*why* the user does it, the product-bug section records *what it costs*. Without this rule neither rubric
owns the class, because the product "worked as designed".

**Experience findings** use the severity table in
`${CLAUDE_PLUGIN_ROOT}/shared/references/experience.md`, scaled by abandonment and
support cost rather than incorrect output — and, for operator-facing products, by time to diagnose and
recover. Severity there is consequence × **reach**, so state reach on the finding: every user / first run
only / one role / one platform / operators under incident. Anything that **tells the user something
false** is always both a product bug and an experience blocker, under one shared id.

## Priority: deliberately NOT a vocabulary here

`severity` above is closed, declared and enforced: it is this suite's word for how bad a defect is,
and the verdict reads it. **`priority` is the operator's field and stays open on purpose.** It holds
whatever scale the team already uses — `P0`/`P1`, MoSCoW, a sprint number — because
`/evidence:orient` Step 3 says to adopt their scale and map it once, not to impose one.

This is written down because "open by design" and "nobody got round to it" look identical to a
reader otherwise. A sweep for closed vocabularies that were enforced nowhere found four real ones
(`confidence`, `mode`, `instrumented`, `provenance` on the replay path); `priority` came up in the
same sweep and is the one that should **not** be closed. The model still restricts *who* may set it
to `OPERATOR`, which is the part that matters.

## Closing action: what actually closes a finding

"Bug" collapses the distinction the operator needs to plan. A report that says "22 bugs" when
nine are deploy lag and two need a certificate has told them nothing about what to do on Monday.

- `CODE` -- the code is wrong. Closing it is a diff.
- `DEPLOY` -- the code is right, production is behind. Closing it is a deploy.
- `RELEASE` -- needs a build or publish action (a stale bundle, an unbuilt tag).
- `DATA` -- a production data operation (duplicate rows, orphaned records).
- `PROCURE` -- needs a certificate, licence or account nobody has yet.
- `DECIDE` -- intentional-but-arguable. Write it as a decision memo with options and a
  recommendation, not as a bug. **Operators answer memos; they argue with bug reports.**
- `INVESTIGATE` -- real symptom, root cause not established. Say so; never guess in a status
  column.

## Type: which kind of defect it is

Orthogonal to the closing action. A `content/i18n` defect can still be closed by a `DEPLOY`.

`product bug` · `usability` · `correctness` · `security` · `privacy` · `perf` · `content/i18n` ·
`docs` (the documentation is wrong, stale, or missing — see
`${CLAUDE_PLUGIN_ROOT}/shared/references/docs-conformance.md`)

## Roles

| Role | Who |
|---|---|
| `PM` | Product manager |
| `HEAD_OF_PRODUCT` | Head of product / sponsor |
| `RESEARCHER` | UX researcher |
| `BA` | Business analyst |
| `PO` | Product owner |
| `DELIVERY` | Project / delivery manager |
| `DESIGNER` | Designer |
| `DESIGN_LEAD` | Design lead |
| `TECH_LEAD` | Tech lead / engineering manager |
| `DEV` | Engineer |
| `QA` | QA engineer / QA lead |
| `WRITER` | Technical writer |
| `PMM` | Product marketing |
| `ANALYST` | Data / product analyst |
| `OPERATOR` | The human who owns the decision, the budget and the release |

Roles are not people. One person holds several; a role is which hat they are wearing for a given write,
and it is what the hub checks. That is why `hub.py` takes `--role` separately from `--actor`: the
`different_actor_from` guard still refuses a person who tries to accept their own work while wearing the
other hat.

## Item types

`initiative` · `insight` · `prd` · `requirement` · `decision` · `story` · `design` · `adr` · `case` ·
`finding` · `fix` · `release` · `doc` · `launch` · `metric` · `risk` · `cleanup`

Traceability chain:

```
initiative → prd → requirement → story → design/adr → case → finding → fix → release → metric
```

`provenance` on every item: `authored` (written here), `derived` (generated from another item), or
`reconstructed` (imported from an existing product's artifacts, where the original intent is unknown).
`reconstructed` is not a lesser status — for an existing product it is the honest one, and the report says
the register was reconstructed rather than implying it was authored.

## Case results

| Result | Meaning |
|---|---|
| `PASS` | The oracle says the product did the thing, with evidence attached |
| `PASS_SHORT` | Ran below the domain's short form. Honest, cheap, and not a pass: it satisfies nothing in the verdict until its long form reads back |
| `FAIL` | The oracle says it did not. Names its finding |
| `BLOCKED` | Could not run: access, credential or platform missing. Stays in the denominator |
| `NOT_RUN` | Designed and not executed. The most useful rows in the register |
| `LONG` | Started, reads back later. A lien on the report: it can be delivered, but carries no verdict while one is open |

**A `PASS` with no evidence is a `NOT_RUN`.** Record it as one.

## Verdict

| Verdict | Meaning |
|---|---|
| `GREEN within stated bounds` | Every condition in the table holds, each naming the rows that satisfy it, and the bounds and the "what this does not cover" block are written down |
| `NOT GREEN` | A condition fails on evidence: an open blocker, an unsatisfied acceptance requirement, a critical class guarded only by a `NOT_RUN` row |
| `NO VERDICT` | **The default.** A condition had no rows at all. Not knowing is not the same as being fine |

The verdict is **computed** from the hub by `hub.py dashboard`, never written by hand. An unbounded green
is the claim this whole method exists to prevent.
