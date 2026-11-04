# Handoff packets

Two templates for a two-session engagement: what QA hands DEV, and what DEV hands back.
`${CLAUDE_PLUGIN_ROOT}/shared/contracts/qa-dev.md` is the mechanism — the lifecycle, who may set which
state, and how disputes
resolve. These are the shapes.

Both are files on disk. Nothing passes between the sessions in a message alone; a live message may announce
a packet, never replace it.

---

# Packet 1 — QA → DEV: the ticket

One per finding, or one document with one section per finding. It is complete when a stranger could start
work from it alone.

## `<ID>` — `<one-sentence statement of the defect>` — `<SEVERITY>` / `<CODE | DATA | RELEASE | …>`

**Area:** `<product / component / endpoint / page>`
**Build it reproduced on:** `<commit / digest / version, per component — per node for a cluster>`
**Environment:** `<live production | local build | container digest | platform + OS | topology (nodes, RF,
partitions) | device × OS>`
**Reproducibility:** `deterministic | <k>/<N> runs under <load / fault schedule>`

### Repro — verbatim, copy-pasteable

```
<the command, the URL, the payload, the inputs — exactly as run>
```

### Expected vs actual

**Expected:** `<what a reasonable customer is entitled to, and why>`
**Actual:** `<what happened>`

```
<raw evidence: response body, console output, grep count, exit code, header dump, binary
 metadata. Secrets referred to by role only — this file gets forwarded>
```

### Why it matters

`<the consequence in business terms. Severity follows from this, not from how hard the fix looks.>`

### What this finding does NOT claim

`<the boundary of what was actually proved, and what further access would settle the rest. This is what
makes the claim trustworthy rather than merely alarming — and it stops DEV chasing a cause QA never
established.>`

### Acceptance criterion — how this fix will be graded, and by whom

**Case:** `<case id>` · **Oracle:** `<the independent thing that answers PASS or FAIL, stated plainly>`

> `<case id>` will be re-run **verbatim**, plus **one unspecified neighbour** of the reported input —
> `<name the class: a different domain, a different case, a tag-only local part, surrounding whitespace /
> a different platform / the same call at the quota boundary>`. A fix that special-cases the exact reported
> string comes back as `PARTIAL`, which does not pass the gate.

*The class is named; the specific neighbour is not. Naming it would invite a fix that handles that one too
and nothing else.*

**Verified by:** QA, not by the author of the fix.

---

# Packet 2 — DEV → QA: the handback

One document per build. **QA returns this unread if any of the five required parts is missing** — that is
far cheaper than a verification round that reports `NOT IN BUILD` for half the register.

## Build under test

| Component | Commit / digest / version | How to obtain it |
|---|---|---|
| `<component>` | `<commit or digest — never a branch name, never "latest">` | `<registry path / artifact URL / tag>` |

*A branch tip moves between the handback and the test. A digest does not.*

## Per-finding disposition — none left `NEW`

| id | Triage | Claimed | Branch | Commit | Root cause, one sentence | Cases claimed |
|---|---|---|---|---|---|---|
| `K1` | `ACCEPTED` | `FIXED` | `fix/qa-k1-env-var` | `9f8e7d6` | Service read the undocumented variable name | `S5-01`, `S5-02` |
| `T4` | `REJECTED` | — | — | — | Works as designed — **citation:** `<doc page>` *(or: none found)* | — |
| `W9` | `DEFERRED` | — | — | — | Real; needs the schema migration in `<build>` | — |
| `L7` | `DUPLICATE` | — | — | — | Same root cause as `K1` | — |

A `REJECTED` row with no citation does not close the finding — it converts it to a documentation finding
against the same id. See *Disputes* in `${CLAUDE_PLUGIN_ROOT}/shared/contracts/qa-dev.md`.

## Tests added, with the fail-first proof

| Test | Automates case | Failed against unfixed code | Asserts |
|---|---|---|---|
| `<TestName>` | `<case id>` | `yes` | `<the oracle, copied verbatim from the case>` |

Report guards honestly: *"5 of 5 new tests fail against unfixed code; 2 of 7 pass either way by design —
they are guards."* A test that passes before the fix asserts nothing.

## Deliberately not changed, with reasons

| What | Why not |
|---|---|
| `<legal text / registered identity / registry path / unverified security policy / operator-owned config>` | `<reason>` |

*An unexplained omission reads as an oversight, and QA will file it again.*

## Merge order and expected conflicts

| Branch | Must merge after | Files/regions that will conflict |
|---|---|---|

## Notes to QA

Addressed to the other session, because neither side may write the other's ledger. Corrections QA should
make to its own register go here, as requests — including anything code access disproved about a finding.

## Found while fixing, not fixed

| What | Why it was not silently resolved |
|---|---|

*Adjacent problems with external consequences — two packaging scripts disagreeing about a publisher name,
one of them conflicting with a store registration — are reported, never quietly chosen between.*
