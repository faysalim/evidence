# Council review — round 1

Five cold reviewers, each given only its brief and the repo, none seeing the others' work. This file
consolidates their findings **de-duplicated by root cause** and ranked, with a disposition for each.

**Status: 2 of 5 reported** (`MG` method guardian, `PP` practitioner panel). `PE` platform engineer,
`HA` hub adversary and `CR` cold runner still running; their findings append below as round 1b.

Every finding marked **VERIFIED** was reproduced here before being accepted. Three were verified and
rejected or reclassified; that is recorded too, because a council whose findings are all accepted was
not read critically.

---

## The one sentence worth taking away

> The restructure's own claims about what it did are now the weakest lines in the repo.
> — method guardian, summary

Three principles in `shared/principles.md` say *"Enforced: X"* where X does not enforce it. The design
doc records retargeting work that was not done. `check_repo.py` — the thing that exists so the repo
cannot lie about itself — is blind to all of it, because it validates `${CLAUDE_PLUGIN_ROOT}` paths and
nothing else.

That is exactly the failure this method is built to prevent, committed by the method's own author, in the
commit that claimed to make it enforceable. It is the most useful result the council could have produced.

---

## Root-cause clusters

### A — False or lost enforcement claims · **blocker**

**Root cause:** I wrote "Enforced: X" from intention rather than from a test, and nothing checks a claim
*about* enforcement. `MG-1`, `MG-2`, `MG-3`, `MG-9`, `MG-11`, and the second half of `PP-4`.

| id | Claim | Reality | Verified |
|---|---|---|---|
| `MG-1` | `principles.md:58` — "`case` items require an `oracle` field" | `add case S1-01 -f action=x` succeeds with no oracle. `model.json` has no create-time required fields and `cmd_add` checks only id, role and state | **VERIFIED** — reproduced, `show` has no oracle |
| `MG-2` | `principles.md:93` — "Verdicts are computed, never written. *Enforced:* `dashboard.py`" | `move REL-1 GREEN` succeeds by hand while `dashboard` computes `NO VERDICT` on the same hub. Nothing in `hub.py` consults the verdict | **VERIFIED** — reproduced both outputs side by side |
| `MG-3` | `ranked-index.md:46` and the old verdict both carry "Build identity established per component" | `grep -c` → `qa_dashboard.py:1`, `ranked-index.md:1`, **`dashboard.py:0`**. The condition was dropped in the port, and the generated `qa-state.json` no longer carries `builds_tested`, so there is nowhere for it to live | **VERIFIED** |
| `MG-9` | `qa-dev.md` invariant 1 — "NEW is not a resting state", with a `validate` check | The check keys on `fields.handed_over`, which **no skill, template or contract ever sets**. A finding filed and left `NEW` validates clean | **VERIFIED** by inspection: `grep -rn handed_over skills shared` → only the three lines inside `hub.py` |
| `MG-11` | `principles.md:41` — "the dashboard prints case counts with their derivation" | It prints counts by type and state. No derivation breakdown exists in `dashboard.py` | **VERIFIED** |

**Disposition: APPLY all five.** Two routes per item — make the claim true, or delete the claim. Taking
*make it true* for `MG-1` (create-time required fields), `MG-3` (restore the condition and the field it
needs) and `MG-9` (a real hand-over event). Taking *correct the claim* for `MG-11`. `MG-2` needs a
judgement call recorded below.

**`MG-2` — the decision.** Wiring `hub.py` to refuse `GREEN` unless `dashboard.verdict()` agrees is the
stronger fix and is what §6 promises. It also couples the write path to the renderer, which is a real
design cost. Taking it anyway: the alternative is softening the principle, and §6 is the one the whole
release skill rests on. **This changes how a release exits a phase, so it is recorded here as a
decision** rather than applied silently — but it restores a stated rule rather than changing one, so it
is applied, not held.

### B — Documents moved whole, still describing the old world · **blocker**

**Root cause:** files moved with `git mv` and never re-read in their new context; `check_repo.py` only
sees `${…}`-prefixed paths, so a bare legacy path is invisible to it. `MG-4`, `MG-5`, `MG-7`, `MG-6`,
`MG-10`, `MG-13`.

| id | Defect | Verified |
|---|---|---|
| `MG-4` | `qa-dev.md` and `iteration-cycles.md` have **one-character diffs** and still instruct hand-writing `qa-state.json` as "authoritative for state" — the exact thing `skills/hub` calls a stale artifact and a Phase 0 error. `iteration-cycles.md` mentions the hub **zero** times, yet QA Step 0 routes every later iteration into it | **VERIFIED** |
| `MG-5` | `agent-brief.md` hands every scope agent five paths (`references/domains/…`, `references/scope-playbooks.md`, …) that do not exist in the installed layout — and the brief is the one artifact **copied verbatim into a subagent with no plugin context**, so variable substitution cannot save it | **VERIFIED** |
| `MG-6` | The closing-action taxonomy (`CODE / DEPLOY / RELEASE / DATA / PROCURE / DECIDE / INVESTIGATE`) was **dropped**, and `vocabulary.md`'s heading "Closing action" sits above the old *Type* list. "Operators answer memos; they argue with bug reports" is gone from the repo | **VERIFIED** — the seven appear only as a bare key in `ranked-index.md:28` |
| `MG-7` | 36 bare legacy relative references across 15 moved files; **9 unresolvable** under any name (`references/dev-handoff.md` ×6, `assets/finding.md` ×2, and `experience.md:213` pointing at a table that moved to `vocabulary.md`). `plugin.md:164` claims this retargeting was done | **VERIFIED** |
| `MG-10` | `test-case-register.md` and `handoff-packet.md` are no longer reachable from the QA skill that produces them | **VERIFIED** |
| `MG-13` | Four `qa-state.json` view fields dropped that `iteration-cycles.md` says "a resumed run cannot work without": `scopes` (applied/N-A families), `not_verified[].unblocked_by`, `stopped`, `builds_tested`. Plus three one-sentence rules gone, including *"state the blocked test rather than improvising around it"* | **VERIFIED** |

**Disposition: APPLY all six**, plus the durable fix: extend `check_repo.refs` to fail on any bare
`references/|assets/|scripts/` path, which is what would have caught every one of them. The design doc's
false claim at `plugin.md:164-166` gets corrected rather than quietly deleted.

### C — Examples nothing ever executed · **blocker**

| id | Defect | Verified |
|---|---|---|
| `PP-1` | **Every `hub.py` write example in six skills is rejected verbatim.** `--actor/--role` are top-level argparse options and all nine examples trail them after the subcommand. The documented first command of every non-QA role fails | **VERIFIED** — `usage: hub.py …` error reproduced; `grep` confirms 9 lines across 6 skills |

**Root cause:** the fixture builder is Python that passes options in the right order, so it never
exercised the prose. `check_repo.py lint` passes 7/7 because nothing runs the examples.

**Disposition: APPLY, as the class fix.** Register `--hub/--actor/--role` on every subparser so both
orders work — better than editing nine lines, because the natural order then works forever — **and** add
`check_repo.py examples` which executes every `hub.py` block in the skills against a scratch hub. The
second half is the real fix; the first is so that correct-looking commands are correct.

### D — Lifecycle dead ends the fixture never reached · **blocker**

| id | Defect | Verified |
|---|---|---|
| `PP-2` | `launch` and `doc` in `CHANGES_REQUESTED` are **terminal**. A PMM or writer whose copy is sent back can never resubmit; the only exit is a new id, which severs `derived_from` and the history time-in-state is built on. `prd` and `design` have the return edge; these two do not | **VERIFIED** for both types |
| `PP-8` | `metric` `NOT_MEASURABLE` is **terminal** — and `skills/analytics` explicitly steers the analyst into it for a not-yet-instrumented metric, which for a new product is the normal path. The PRD's `measures` link then points at a dead item | **VERIFIED** |

**Root cause:** both fixtures walk happy paths through review, so `build.py` never requested changes or
declared a metric unmeasurable. A fixture that only succeeds cannot find a dead end.

**Disposition: APPLY.** Add the return edges, add a `test_hub.py` case for each, **and extend both
fixtures to walk a rejection path**, which is the fix that stops this class recurring.

### E — Skills promising outputs their role may not create · **major**

| id | Defect | Verified |
|---|---|---|
| `PP-3` | `discovery` tells the RESEARCHER a conflict "is a `decision`" and lists `metric` as an output; `launch` lists `finding` and `decision` for the PMM. The hub refuses all four | **VERIFIED** — all four refusals reproduced |

**Disposition: APPLY** by widening the `create` lists in `model.json`. A researcher who finds two user
groups in conflict is the right person to file that decision, and a PMM who finds copy right and the
product wrong is filing a real finding. The alternative — telling them to ask someone else to file it
under their name — breaks "a claim is attributable", which is principle 7's point.

### F — `waiting_on` reports resting states as blocked · **major**

| id | Defect | Verified |
|---|---|---|
| `PP-5` | `list --waiting-on OPERATOR` on the committed fixture reports `REL-1 release SHIPPED` as awaiting the operator, and the committed dashboard's "Awaiting the operator" section says the same. Cause: `waiting_on` unions the roles on *any* outgoing transition, including escape hatches (`SHIPPED→ROLLED_BACK`, `AGREED→SUPERSEDED`, `PASS→DESIGNED`), and `TERMINAL_OK` has no entry for 8 of the 17 types | **VERIFIED** — reproduced on the unmodified committed fixture |

**Disposition: APPLY.** This is the delivery skill's first and most-read report section — "blocked on a
human" — being wrong by construction, and the hub skill's own rule is "quote states, do not paraphrase".
Mark escape-hatch transitions in `model.json` and exclude them from `waiting_on`.

### G — The "no translation step" claim does not hold · **major**

| id | Defect | Verified |
|---|---|---|
| `PP-6` | `skills/backlog` says a criterion written as an oracle "becomes a QA case with no translation step" and that QA "derives cases from the story's criteria as a derivation source". QA's eight derivation sources **do not include story criteria**. On the fixture, `S-1`'s criterion has three clauses (email within 5 minutes, activates offline, expiry is 14 days) and the linked case `S5-01` carries one; the story was `ACCEPTED` on that case alone | **VERIFIED** by inspection |
| `PP-7` | A PO whose story is `DONE` before QA has written a case has no documented move: accept is refused, a PO may not create a case, and `backlog` never says who can | **VERIFIED** |

**Disposition: APPLY.** This is the suite's stated reason for hanging together, so the claim gets made
true rather than withdrawn: add story acceptance criteria as a **named derivation source** in
`test-cases.md` and the QA skill, one case per gradeable clause, and tell the PO in `backlog` what the
`DONE`-with-no-case move actually is.

### H — Natural prompts mostly do not route · **major, and the least certain**

| id | Finding |
|---|---|
| `PP-12` | 1 of 8 realistic prompts fired a skill (`what's waiting on me?` → `hub`). Prompts matching description text nearly verbatim — the refund-window conflict, the launch blog, "did onboarding move activation", "can we ship on Friday" — fired nothing; the model answered in prose or asked for context instead |

**Disposition: PARTIALLY APPLY, and record the uncertainty.** One run per prompt in an empty working
directory with `--max-turns 3` is not a rate, and the reviewer says so. It is also consistent with the
deterministic eval result, where the *must-not-trigger* case is solid and the hit cases are
inconclusive. What is actionable now: prompt 2 ("what goes in the next release") is genuinely ambiguous
across three skills and none of their descriptions claims it. The rest needs a measurement before a fix —
**recorded as `NEEDS FAISAL`**, because trading description length against trigger rate would push the
measured always-on cost up against its ceiling, and that is a cost/benefit call rather than a defect fix.

### Minor, applying without discussion

| id | Defect |
|---|---|
| `MG-12` | `principles.md` renamed the secrets directory to `.product-secrets/`; `.gitignore` still ignores only `.qa-secrets/`. **A rule that says "gitignored" over a directory that is not.** |
| `PP-10` | `delivery`'s worked risk example uses id `R-3`, which is the namespace QA's acceptance requirements own. Ids are global, so it collides |
| `PP-11` | No skill says where its document artifact lives; the hub holds a one-line summary. The launch claims table "the artifact this skill is built around" exists nowhere in either fixture |
| `PP-4` | `release` is addressed to "EM, QA lead, PM" but only QA may record the verdict, and the skill's condition table has two rows the dashboard never computes while the rows it does compute key on QA id conventions (`-00a`, `-00b`, `R-`) the release skill never mentions |
| `PP-9` | Four skills rely on a second actor that a one-person-per-role team does not have, and none names the fallback hat |
| `SF-1` | **Mine, found before the council:** `.gitignore`'s `qa-state.json` rule silently excluded both fixtures' generated view. `fix-state.json` is committed, `qa-state.json` is not — a clone gets half a fixture, and `test_fixtures.py` cannot catch it because it rebuilds from scratch |
| `SF-2` | `evals/results/` committed as source |
| `SF-3` | `NOTICE` still names `product-qa` |

### Rejected, with reasons

| id | Why not |
|---|---|
| `MG-14` (both) | Correctly identified as **pre-existing, not regressions** — the "scope-playbooks says what extra agents buy" mismatch and `test-cases.md`'s "Eight sources" over a 0–8 list are both identical at the snapshot. Recording them, fixing the count (a one-word edit), and leaving the agent-budget wording for a separate pass rather than smuggling a method change into a restructure |
| `PP-12`, in part | See above — the trigger *rate* is not established by one run per prompt, so the fix is not yet knowable |

---

## What survived, which is most of it

The method guardian checked the prime directive and both halves, every Step 0 mandate bullet, the Step 1
ground-truth table, the twelve families with the provisional-then-reconfirmed N/A rule, the agent budget,
the case gate including smoke and calibration, two-way docs coverage with denominators, the first-run
trace rules, dedupe by root cause, the iteration gate phase by phase, and the whole QA↔DEV contract —
**and found them intact**, with `fix-phase.md`, `handoff-packet.md`, `evidence-standard.md`,
`docs-conformance.md`, `experience.md`, `test-cases.md`, `scope-playbooks.md`, `case-file.md`, all 27
domain files and `safe_edit.py` at **0-line diffs**. The `gotchas.md` split lost nothing: all three moved
sections are byte-identical.

Two things are now **stronger** than before the restructure: stable ids are mechanically enforced
(`hub.py` refuses reuse, with the original sentence as its message), and an uncalibrated scope denies
the verdict rather than merely being discouraged.

So the restructure moved the method without weakening it. What it got wrong was its own bookkeeping —
which is the part the method says to check first.
