# Council review — round 1

Five cold reviewers, each given only its brief and the repo, none seeing the others' work. Between
them: **59 findings, 8 of them critical.** This file consolidates them **de-duplicated by root
cause**, with a disposition for each.

Every finding marked **VERIFIED** was reproduced here before being accepted. Several were verified
and then reclassified or rejected; that is recorded too, because a council whose findings are all
accepted was not read critically.

| Reviewer | Scope | Findings |
|---|---|---|
| `MG` | method guardian — was anything lost in the move? | 14 |
| `PE` | plugin platform engineer — does it work as a plugin? | 7 |
| `HA` | hub integrity adversary — break the hub | 18 |
| `PP` | practitioner panel — can each role do its job? | 12 |
| `CR` | cold end-to-end runner — first-run measurement on itself | 15 |
| `SF` | self-found, before the council | 3 |

---

## The one sentence worth taking away

> The restructure's own claims about what it did are now the weakest lines in the repo.
> — method guardian

Three principles said *"Enforced: X"* where X did not enforce it. The design doc recorded retargeting
work that was not done. And `check_repo.py` — the thing that exists so the repo cannot lie about
itself — was blind to all of it, because it validates paths rather than promises.

That is precisely the failure this method is built to prevent, committed by the method's own author,
in the commit that claimed to make it enforceable. **It is the most useful result the council could
have produced**, and it is why `tests/test_enforcement_claims.py` now exists: every "Enforced:" line
has a probe that attempts the forbidden thing and asserts the refusal.

The cold runner's result is the counterweight: **it completed a full engagement in 8 minutes** —
orient through to a shipped release with a computed verdict and a torn-down cleanup ledger — and
reported that the role guards, the state-machine refusals, the stale-view detection and the
`NO VERDICT` default "all behaved exactly as documented and their messages are the strongest part of
the tool."

---

## Cluster A — false or lost enforcement claims · **blocker** · APPLIED

**Root cause:** "Enforced: X" written from intention rather than from a test, and nothing checked a
claim *about* enforcement.

| id | Claim | Reality | Fix |
|---|---|---|---|
| `MG-1`, `CR-7` | `case` items require an `oracle` | `add case -f action=x` succeeded with none | `requires_fields_on_create: [action, oracle]` |
| `MG-2`, `HA-14` | verdicts are computed, never written | `move REL GREEN` succeeded while the dashboard computed `NO VERDICT` | the write path now asks the same verdict function |
| `MG-3` | "Build identity established per component" | computed by `qa_dashboard.py`, **lost in the port**; 0 occurrences in `dashboard.py` | restored, plus a check that smoke/calibration ran on the named build (`CR-3`) |
| `MG-9` | "NEW is not a resting state" has a check | it keys on `fields.handed_over`, which **nothing ever sets** | left as a known gap; see NEEDS FAISAL |
| `MG-11` | the dashboard prints counts with their derivation | it prints counts by type and state | claim deleted |

**The `MG-2` fix needed a correction of its own**, which the tests caught: the first version ran the
verdict check during *replay*, where the mid-fold hub looks stale to its own generated view, so a
recorded GREEN became permanently unreplayable. Role and different-actor are **invariants** and are
re-checked every fold; "the computed verdict agreed" is a **precondition** and is checked at write
time only.

**Durable fix:** `tests/test_enforcement_claims.py`. Verified both ways — it passes now, and
deleting the case oracle requirement makes it fail.

## Cluster B — documents moved whole, still describing the old world · **blocker** · APPLIED

**Root cause:** `git mv` and never re-read in the new context; `check_repo.py` saw only
`${…}`-prefixed paths, so a bare legacy path was invisible.

| id | Defect | Fix |
|---|---|---|
| `MG-4`, `CR-11` | `qa-dev.md` and `iteration-cycles.md` had **one-character diffs** and still called `qa-state.json` "authoritative for state", telling the reader to create it as their first write — the exact thing the hub skill calls a Phase 0 error. `iteration-cycles.md` mentioned the hub **zero** times while QA Step 0 routed every later iteration into it | both re-pointed to the hub, its per-actor logs and the generated views |
| `MG-5` | `agent-brief.md` handed every scope agent five paths that do not exist in the installed layout — and it is the one artifact **copied verbatim into a subagent with no plugin context**, so no variable can save it | `<ABSOLUTE PATH>` placeholders, with the reason stated |
| `MG-6` | the closing-action taxonomy was **dropped entirely** and vocabulary's "Closing action" heading sat above the *Type* list | restored with definitions; Type retitled |
| `MG-7` | 31 bare pre-restructure references, **9 naming files that exist under no name**; the design doc claimed this retargeting was done | all retargeted; `check_refs` now fails on any bare `references/`, `assets/` or `scripts/` path |
| `MG-10` | the QA skill no longer pointed at two templates it produces | rows restored |
| `MG-13` | three one-sentence rules dropped, incl. *"state the blocked test rather than improvising around it"* | restored |
| `CR-8` | no relation could reach a finding from a case, so **every finding** was "not reachable" | `found_by` added; the per-hop relation documented for the whole chain |

## Cluster C — examples nothing ever executed · **blocker** · APPLIED

| id | Defect | Fix |
|---|---|---|
| `PP-1`, `CR-4` | **every `hub.py` write example in six skills was rejected verbatim.** argparse wants the global options first; all nine examples trailed them, so the documented first command of every non-QA role failed with an error that named no fix | the subparsers accept them too, so both orders work |

The fixture builder never caught it because it is Python passing options in the right order. **The
fix needed its own fix:** a plain `None` default on the parent parser had the subparser overwrite a
value given *before* the subcommand; `argparse.SUPPRESS` was required.

## Cluster D — lifecycle dead ends the fixtures never reached · **blocker** · APPLIED

`PP-2`, `PP-8`, `CR-5`. `launch` and `doc` in `CHANGES_REQUESTED`, `metric` in `NOT_MEASURABLE` and
`finding` in `DEFERRED` were all **terminal**, so send-back-and-resubmit and "deferred to the next
build" were one-way doors out of the id — which `qa-dev.md` invariant 3 forbids. Return edges added.

**Root cause:** both fixtures walk happy paths through review. A fixture that only succeeds cannot
find a dead end.

## Cluster E — the give-up point · **major** · APPLIED

`CR-6`. A wrong `verifies` link permanently blocked story acceptance, with no `unlink` and no
documented way out. The cold runner recorded this as the point where an unpaid user stops. `unlink`
added as an attributed event rather than an erasure.

## Cluster F — `waiting_on` reported resting states as blocked · **major** · APPLIED

`PP-5`, `CR-9`. It unioned the roles on *every* outgoing transition, including escape hatches, so a
`SHIPPED` release was reported as awaiting the operator (it can still be rolled back) and an
`AGREED` requirement as awaiting the PO. That made the delivery report's first and most-read
section — "blocked on a human" — wrong by construction, in a tool whose own rule is to quote states
rather than paraphrase them. Escape hatches are now marked in the model and excluded.

## Cluster G — the "no translation step" claim did not hold · **major** · APPLIED

`PP-6`, `PP-7`. The backlog skill says a criterion written as an oracle becomes a QA case with no
translation step. **QA's eight derivation sources did not include story criteria.** On the fixture,
a three-clause criterion produced one case, and the story was accepted on it. Story criteria are now
a named derivation source, one case per gradeable clause, and the PO is told what the
`DONE`-with-no-case move actually is.

## Cluster H — write-path robustness · **critical** · APPLIED

All eight of the adversary's criticals. `HA-1` (field ownership enforced in `set` only, so
`move -f severity=polish` let a DEV un-block a release), `HA-2` (`add --state` reached any state,
defeating every authority rule with one flag), `HA-3` (a duplicate pointing at nothing),
`HA-4` (unknown, padded, null or list severity), `HA-5` (a `FAIL` case denying nothing — the page
printed "cases fail: 2" and GREEN together), `HA-6`/`CR-1` (prose `guards`, which is the form every
skill documents, **crashed the only verdict path**), `HA-7` (an unreadable log line was a *note*, so
`validate` exited 0 over a log the hub had failed to read), `HA-8` (cleanup parked in `OPERATORS`).

Plus `CR-2`, which is the subtlest of the set: `requires_fields` OR-ed with fields already on the
item, so a release reaching `SHIPPED` already carried QA's `reason` and **the operator's own reason
was never demanded** — the audit trail showed a reason-less ship that read as reasoned.

And `HA-10` (`event_id` was per-file, so one person wearing two hats collided and the fold silently
dropped the second event), `HA-12` (the view check was a row count; a hand-edit with the header
intact passed clean — now a sha256 over applied event ids), `HA-13` (the fold trusted payload
`role`/`actor` over the path), `HA-17`, `HA-18`.

## Cluster I — platform · **blocker** · ONE APPLIED, ONE CANNOT BE

| id | Defect | Disposition |
|---|---|---|
| `PE-3` | on Windows **every read command died** with `UnicodeEncodeError` once an item carried a character outside cp1252, and `python -I` — which every skill prescribes — ignores `PYTHONUTF8` | APPLIED: stdout/stderr reconfigured explicitly |
| `PE-5` | the lint checked only bash-family fences, though an unbraced `$CLAUDE_*` resolves nowhere at all | APPLIED: any unbraced occurrence, anywhere |
| `PE-4` | the eval suite's routing graders were an `llm` judge reading prose, which voted FAIL on runs whose **traces prove the right skill fired**. A deterministic grader exists — `tool_used` + `input_match` — and `evals/README.md` published its absence as a harness limitation | APPLIED: graders rewritten. Not re-run, on cost |
| `PE-1` | **the README's install commands cannot work.** `origin/main` is still the old standalone skill with no `.claude-plugin/`, and `plugin-suite` is unpushed. Every documented acquisition path fails at step one; the install the council reviewed used a local path that appears nowhere in the README | **CANNOT APPLY** — the fix is a push, which was forbidden for this run. NEEDS FAISAL |
| `PE-2` | **in a real session, 7 of 15 skills have no description.** The listing is 38,132 chars against a 30,000 budget on the default model and 8,000 on a 200k-window one; this plugin's descriptions alone are ~96% of the latter *before any other plugin exists*. The drop lands on the least-invoked skills — the drafts. And `tests/test_description_budget.py` printed `ok` | **PARTIALLY APPLIED** — the test now measures the real constraint and **fails**. The remedy is a product decision. NEEDS FAISAL |

## Minor, applied without discussion

`PP-3` (skills promising outputs their role may not create — `create` lists widened; a researcher
who finds two user groups in conflict is the right person to file that decision), `PP-4` (the
release skill addressed to PM/EM while only QA may record a verdict, with a condition table that
did not match the computed one), `PP-9` (second-hat notes for one-person teams), `PP-10` (`R-` id
namespace collision), `CR-10` (`dashboard` printed a path, not the verdict), `CR-12` (the
conventions the verdict silently depends on, now one table), `CR-13` (the README had no
first-engagement path), `HA-15`, `HA-16` (a metric reading of **0** was refused as "missing" because
required fields were tested for truthiness), `MG-12`, `SF-1` (`.gitignore` silently excluding both
fixtures' generated view), `SF-2`, `SF-3`.

## Rejected or reclassified, with reasons

| id | Why |
|---|---|
| `MG-14` | Correctly identified as **pre-existing, not regressions** — both are identical at the snapshot. Recorded; the agent-budget wording is left for a separate pass rather than smuggling a method change into a restructure |
| `PP-12` | 1 of 8 natural prompts fired a skill — but one run per prompt in an empty directory is not a rate, and the reviewer says so. It is also consistent with `PE-2`: in that environment, 7 of 15 descriptions were absent, so the prompts could not route. **Reclassified as evidence for `PE-2` rather than a separate trigger defect** |
| `HA-8` | The reviewer flagged this itself as the weakest critical. Applied anyway: a resource handed to the operator still exists and still bills |
| `HA-9` | Cross-item clock skew flipping an accepted story back to `DONE` on replay. Partially applied — transitions now declare the other items their checks read in `after`. Whether that closes every path is **unverified**; the reviewer's own `b6_skew.py` is the test to re-run |
| `HA-11` | `import` not validated or atomic, with a path-traversal id writing outside the output directory. **Partially applied** (ids validated via `SAFE_ID`); atomicity NEEDS FAISAL |
| `PP-11` | No skill says where its document artifact lives. **Not applied** — it needs one convention chosen across all 15 skills, which is a decision rather than a fix |
| `PE-6` | Bare `/hub` and `/qa` **do** resolve to this plugin, so the README's claim that bare names are not invokable is false. The *rule* to document only the namespaced form stands; the justification was wrong. Wording left for a follow-up |

---

## What survived, which is most of it

The method guardian checked the prime directive and both halves, every Step 0 mandate bullet, the
Step 1 ground-truth table, the twelve families with the provisional-then-reconfirmed N/A rule, the
agent budget, the case gate including smoke and calibration, two-way docs coverage with
denominators, the first-run trace rules, dedupe by root cause, the iteration gate phase by phase,
and the whole QA↔DEV contract — **and found them intact**, with `fix-phase.md`,
`handoff-packet.md`, `evidence-standard.md`, `docs-conformance.md`, `experience.md`,
`test-cases.md`, `scope-playbooks.md`, `case-file.md`, all 27 domain files and `safe_edit.py` at
**0-line diffs**. The `gotchas.md` split lost nothing: all three moved sections are byte-identical.

Two things are **stronger** than before the restructure: stable ids are mechanically enforced, and
an uncalibrated scope denies the verdict rather than merely being discouraged.

The adversary also recorded what it **could not** break: HTML injection (every value escaped), fold
order independence, a log concatenated twice, role-string variants, and every direct invariant via
`move`. That list is evidence too.

So the restructure moved the method without weakening it. What it got wrong was its own
bookkeeping — which is the part the method says to check first.
