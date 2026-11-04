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

### Acceptance criterion — how a fix will be graded, and by whom

**Case:** `<case id>` · **Oracle:** `<the independent thing that answers PASS or FAIL>`
`<case id>` will be re-run verbatim plus **one unspecified neighbour** of the reported input —
`<name the class, not the value: a different domain, a different platform, the quota boundary>`. A fix that
special-cases the exact reported string returns as `PARTIAL`.

*The **class** is published here, in the ticket: it is a specification, and it tells whoever fixes this to
fix the class rather than the value. The **value** QA actually used is published with the verdict, after
the fact — withholding it leaves a `PARTIAL` nobody else can reproduce, which turns the status that
matters most into an argument. The register row carries the concrete action either way.*

*Required when a separate dev session will fix this (`references/dev-handoff.md`); good practice always.
Verified by QA, never by the author of the fix.*

### What this finding does NOT claim

`<the boundary of what you actually proved. Often the most valuable line in the report: it is what makes
the claim trustworthy rather than merely alarming, and it tells the operator precisely what further
access would settle the rest.>`

### Not verified

`<adjacent checks you could not execute, with the reason and what would unblock them>`

---

## Severity and type

Both vocabularies are defined once, in `${CLAUDE_PLUGIN_ROOT}/shared/vocabulary.md`, and used by every
skill and by the dashboard. Read them there; restating the tiers here guarantees the two copies drift.

The two rules that belong on every finding, because they are how severity gets assigned wrongly:

- **Severity is the worst consequence the defect causes, not the effort to fix it.** A one-line fix can be
  a blocker.
- **Severity inherits.** An experience defect takes the severity of the action it leads the user into: a
  confirmation dialog that invites a reflexive click on a cluster wipe is `critical`, because the
  consequence is the wipe. File such findings in both sections under one id.
