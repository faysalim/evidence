# Finding template

One per finding. The id is a name, not a position — assign it once and never renumber it, because later
iterations and the operator's own tickets refer to it.

---

## `<ID>` — `<one-sentence statement of the defect>` — `<SEVERITY>` / `<TYPE>`

**Area:** `<product / component / endpoint / page>`
**Environment:** `<live production | local build | container digest | platform + OS version | topology
(nodes, RF, partitions) | device × OS>`
**Build under test:** `<commit / image digest / version, and how you established it — per node for a
cluster, because a mixed-version cluster is a normal state during a rolling upgrade>`
**Reproducibility:** `deterministic | <k>/<N> runs under <load / fault schedule>`
**Topology and fault** *(stateful findings)*: `<nodes, RF, partitions; what was killed / partitioned /
paused, on which node, at what second, for how long; the convergence signal observed and how long it took>`
**Status:** `CODE | DEPLOY | RELEASE | DATA | PROCURE | DECIDE | INVESTIGATE`

### Repro

```
<exact steps: the command, the URL, the payload, the inputs — copy-pasteable>
```

This block is also the verification test for the next iteration, so write it as something a stranger can
run. A vague repro means the finding can never be verified closed, and it stays open forever.

### Expected vs actual

**Expected:** `<what a reasonable customer is entitled to, and why>`
**Actual:** `<what happened>`

```
<evidence inline: response body, console output, grep count, exit code, screenshot path,
 header dump, binary metadata — with secrets replaced by their role>
```

### Why it matters

`<the consequence, in business terms. Severity follows from this, not from how hard the fix looks.>`

### What this finding does NOT claim

`<the boundary of what you actually proved. Often the most valuable line in the report: it is what makes
the claim trustworthy rather than merely alarming, and it tells the operator precisely what further
access would settle the rest.>`

### Not verified

`<adjacent checks you could not execute, with the reason and what would unblock them>`

---

## Severity

| Severity | Test |
|---|---|
| **critical** | Data the product acknowledged is lost or corrupted, a tenant / user / role boundary is crossed, or money moves wrongly — **and the product does not tell anyone**. Nothing the customer does recovers it, and no deploy undoes damage already done. Examples: acknowledged writes missing after a fault the docs say is survived; two nodes accepting writes during a partition; a role's export containing records it cannot see; a retried checkout charging twice |
| **blocker** | A customer following a documented path cannot succeed, loses money, or is misinformed in a way that reaches the public (wrong published price, broken acquisition flow, a silent no-op install instruction) — *or the business's control over its own revenue or obligations is defeated* (entitlement bypass, fail-open licence validation, incomplete erasure, a store-policy violation that removes the listing) |
| **major** | A real customer journey is damaged, or the business loses revenue or leads, but a workaround exists |
| **minor** | Wrong, visible, and worth fixing, but nobody is blocked or misled materially |
| **polish** | Correct but rough |

Severity is by consequence. A stale structured-data price undercutting the real one is a blocker even
though the fix is one line, because search engines publish it as the offer.

**Silence is a multiplier.** The same defect with a loud, visible error is one tier lower, because the
customer can act on it. A failover that loses writes and *says so* is a blocker; one that loses them
behind a green dashboard is critical. Where severity depends on a contract the docs never state — what
consistency, what isolation level, what delivery guarantee — file the undocumented contract as the first
finding in scope 9, and hold the data finding at `DECIDE` until it is answered. You cannot grade a product
against a promise it never made.

**Severity is the worst consequence the defect causes, whatever section it is filed in.** An experience
defect inherits the severity of the action it leads the user into: a confirmation dialog that invites a
reflexive click on a cluster wipe is `critical`, because the consequence is the wipe; the same dialog on a
rename is `minor`. File such findings in both sections under one id — the experience section explains
*why* the user does it, the product-bug section records *what it costs*. Without this rule neither rubric
owns the class, because the product "worked as designed".

**Experience findings** use the severity table in `references/experience.md`, scaled by abandonment and
support cost rather than incorrect output — and, for operator-facing products, by time to diagnose and
recover. Severity there is consequence × **reach**, so state reach on the finding: every user / first run
only / one role / one platform / operators under incident. Anything that **tells the user something
false** is always both a product bug and an experience blocker, under one shared id.

## Type

`product bug` · `usability` · `correctness` · `security` · `privacy` · `perf` · `content/i18n` ·
`docs` (the documentation is wrong, stale, or missing — see `references/docs-conformance.md`)
