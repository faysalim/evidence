# Exercising the skills against a real product

2026-11-05. Seven skills run against a live codebase instead of read: a real distributed data
store with published releases, its real documentation, and its real public comparison page.

The point was not to produce artifacts. It was to find out which instructions do not survive
contact with a product, because **twelve of the fifteen skills had never been run**, and
`shared/principles.md` §3 does not accept the author's own reading of their own work as an oracle.

Twelve defects in the skills and tools, two in the product. The first appeared inside twenty
minutes, which is the whole argument for doing this.

---

## Defects in the suite

| id | Where | Defect | Severity |
|---|---|---|---|
| `E-1` | `hub.py` | `status` on an empty hub ended its hint with "otherwise `hub.py init`" — a command **rejected** for missing `--actor`/`--role`. The first thing a new engagement saw was advice that fails | major |
| `E-6` | all skills | `orient` Step 3 promises "have **every** downstream skill read" the profile and `conventions.md`. **Two of fifteen did.** `analytics`, `architecture`, `launch`, `prd` and `release` referenced neither — exactly the skills that otherwise guess the product class and impose vocabulary | major |
| `E-2` | `orient` Step 4 | "Enumerated from code" with no warning about scope. My own first count read compiled DLLs and reported 154 environment variables, with `Binary file ... matches` lines among the results. The real figure is 102 in non-test source | major |
| `E-3` | `orient` Step 6 | Requires stating what you could not establish, and warns "every downstream skill reads the profile and will otherwise assume you looked" — but the profile accepted `not_established` and **nothing read it**. The one safeguard against downstream silent assumption was prose with no consumer | major |
| `E-7` | `docs-conformance.md` | Step 4, the reverse-coverage method both `qa` and `docs-authoring` read, had the same scope gap as `E-2`, and did not name the reverse direction (a documented surface the product lacks) as a finding in its own right | major |
| `E-11` | `check_repo.py` | The secret pattern `(?:sk\|pk\|ghp\|gho\|AKIA)[-_A-Za-z0-9]{12,}` required no separator, so it flagged `skillListingBudgetFraction` — a settings key name — as a key. A false positive in a secret check teaches people to reword honest prose until the check goes quiet | major |
| `E-8` | `check_repo.py` | The `coverage` check I had just written read frontmatter as `split("\n---", 2)[1]`, which is the **body** for any file containing a `---` rule. It failed closed on a real skill and would have **passed** a skill whose body happened to contain a `roles:` line while its frontmatter declared nothing | major |
| `E-9` | two test tools | Both read the description as everything up to the closing `---`, so adding `roles:` and `status:` silently made them part of every measured description. `check_repo.py` read to the next key and was unaffected | medium |
| `E-12` | `dashboard.py` | Build identity was scoped to in-flight releases, which excluded `SHIPPED` — so a shipped release reported "no release names a build", the opposite of that condition's purpose | medium |
| `E-10` | budget test | Its failure message recommended `skillOverrides: name-only`, a remedy I had measured as doing nothing in four attempts. Telling a reader to apply a fix that does not work is the same defect as a false `Enforced:` line | medium |
| `E-4` | `dashboard.py` | An unnamed engagement rendered as the bare word "engagement" in the `<h1>` and the `<title>`. A first dashboard that says "engagement" reads as a placeholder the tool forgot to fill in | minor |
| `E-5` | `orient` | Never mentioned `init --engagement`, so every engagement following it got the above | minor |

All twelve are fixed. `E-1`, `E-3`, `E-6`, `E-8`, `E-9` and `E-11` have regression tests that were
each **proven to fail against the old code** before the fix was accepted.

### The one that mattered most

`E-6`, because it was invisible from inside any single skill. `orient` establishes the product
class, the deploy branch, the live build, and the team's own vocabulary — and then thirteen skills
never read any of it. `requirements` was the trigger: its contract hard-codes `REQ-14` and it never
mentioned adopting the team's numbering. Applied to the real cloud-readiness requirements document —
lettered themes `A`–`F` with `P0`/`P1` and **zero numbered ids** — following it would have renumbered
the team's requirements and broken every existing reference. That is the
imposition-over-adoption failure `orient`'s own "For the lead" section warns about, committed by the
suite itself.

Thirteen skills now carry the step, and `check_repo.py coverage` fails if any of them drops it.

## Defects in the product

Recorded in the exercise hub, with denominators and boundaries, as the method requires.

> **This finding was wrong in every number, and re-running it is what proved that.** It is left
> here, struck through, because the correction is the most useful thing in this document — see
> *The denominator that could not be recomputed* in the second exercise below. Corrected figure:
> **23 of 131** configuration variables undocumented (16 excluding benchmark knobs), and **2**
> documented names that do not exist. The three variables named below as headline examples were
> documented in the product's own shipped docs all along.

~~**57 of 102 production environment variables are undocumented**, and three documented names do not
exist in the code. Denominator: distinct `ZARIS_[A-Z0-9_]+` reads in `*.cs` under `src/`, excluding
directories matching `test|bench|harness` and excluding build output; 48 documented across the
site's docs, blog and pages. The undocumented set includes `ZARIS_CLIENT_PORT` and
`ZARIS_CLUSTER_PORT`.~~ *Does not claim* all 102 are user-facing knobs — some may be internal or dead.

**A headline comparison claim states no rig, workload or baseline.** The public Redis-comparison
page claims "18.5M ops/sec at 3 nodes vs Redis 7.57M" with no hardware, vCPU count, workload or
methodology, and no link to a measurement — while the row directly above it *is* qualified
("+70–87% vs Redis on 8-core nodes (measured)"). Two evidence standards in one table. *Does not
claim* the number is false; a larger rig could produce it. The defect is that it is unfalsifiable as
published, which `skills/launch` already names as a defect in itself — so this is the skill working,
not a gap in it.

## Mistakes I made during the exercise, and what they cost

Recorded because `shared/principles.md` §5 applies to the person running the method too, and because
three of them were caught by the repo's own checks rather than by me.

- **The first command harness was wrong.** It gave every documented command a fresh hub and reported
  nine failures, all its own fault: a document's examples are a *sequence*, so judging line two
  against a hub where line one never ran tests the harness, not the document. Rerun in document
  order: one real failure.
- **The first model-agreement check was wrong.** It tried to verify that a state belonged to a type
  the skill "owns" and produced nine failures, every one wrong — `dev` legitimately discusses a
  finding's `FIXED` because moving QA's findings *is* its job. Ownership is not inferable from text,
  so that check is now **not attempted** rather than attempted badly, and its docstring says so.
- **I claimed no skill mentioned `init --engagement`.** `skills/hub` documents it. The claim came
  from a grep I truncated with `head -4`, which cut the match. Corrected in the following commit.
- **I reported mojibake in a public page** (`+70�87%`) before checking the bytes. The file is clean
  UTF-8; the corruption was my own console read. Not reported as a finding.
- **I reached for a shell heredoc six times** on content containing `\n`, and it flattened the escape
  into a real newline every time, breaking three files. `shared/references/gotchas.md` names this
  exact trap. A file-writing tool was the right instrument from the first occurrence.

---

# Second exercise — `architecture` and `prd`, 2026-11-05

Same product, different question: the first exercise pointed seven skills at a codebase and its
public docs. This one pointed the two design skills at the product's **own certification
artifacts** — a 4-hour run that returns FAIL — and at its existing decision records.

Eight defects in the suite, six in the product, and one correction to the first exercise's own
published finding. The correction is the most instructive of the lot.

## Defects in the suite

| id | Where | Defect | Severity |
|---|---|---|---|
| `X-1` | `hub.py status` | Eleven skills open with `status  # mode, the product class, and what orient could not establish`. **`status` printed no product class.** It lived only in `hub.py profile`, so a skill that believed its own first line either guessed the class or made an undocumented second call. Worse than an ordinary wrong comment: that block *is* the fix for `E-6`, whose whole subject was a false promise about what downstream reads | major |
| `X-2` | `hub.py profile` | `domains` was unvalidated. `domains=[..., "self-hosted-deployment"]` was stored in silence and there is no such file, so the fault catalogue for a class the product really is would never have been read and nothing would ever have said so. `X-1`'s fix made this worse by broadcasting the unrecognised name to eleven skills with the profile's authority | major |
| `X-3` | `metric`, model | `prd` says each metric is "`DEFINED` with its denominator before anything is built" and `analytics` opens by reading metrics "against the denominator and baseline the PRD stated". `add metric M-1 -f name=activation` was accepted into `DEFINED` with no denominator — handing `analytics` exactly the nothing it is written to avoid inventing | major |
| `X-4` | `docs-conformance.md` Step 4/5, `orient` Step 4 | **The reverse-coverage denominator was prose, and prose is not reproducible.** See below | major |
| `X-5` | same | **A one-language enumeration is not the surface, and it manufactures findings.** See below | major |
| `X-6` | `architecture` | The ADR section presented `id ADR-4` and a six-field block as *the* template. The team keeps five records as `docs/decisions/NNNN-kebab-title.md`, titled `# Decision NNNN — …`, with their own section names and a sketchnote companion — and calls them **Decisions**. Following the skill would have renumbered and renamed them: the same imposition-over-adoption failure `requirements` committed with a hard-coded `REQ-14`, which was `E-6`'s trigger, still live in a second skill | major |
| `X-9` | 7 × `SKILL.md` | Frontmatter said `status: exercised` while the first line of the body still said `` `status: draft` ``. **Five of the seven predate this exercise** — left behind when the statuses were flipped, and invisible to `check_repo coverage`, which read frontmatter only. A file that contradicts itself about its own maturity is worse than one with no marker: the reader cannot tell which line is stale, and the banner is what they see first | medium |
| `X-7` | `adr` lifecycle | `PROPOSED → ACCEPTED → SUPERSEDED` cannot express a decision that is accepted and half-built. Decision 0003's real status is `Partial (instrumentation + safety net implemented; core transport fix pending)`. `ACCEPTED` overstates it, `PROPOSED` is false, and `orient` Step 5 tells you to map their folder onto `adr` items with no guidance for the case | medium |
| `X-8` | `prd` | Reconstruct-then-delta is this skill's distinguishing idea, and it gave no guidance on how the nine sections re-read in a reconstruction. Read the change-PRD way, §4 and §6 produce a filled-in template with **no findings in it** — which is the whole value gone. Both of this engagement's largest product findings came out of asking those two sections the current-state question instead | medium |
| `X-10` | `test_documented_commands.py` | The harness's seed failed **silently**. Tightening `metric` (`X-3`) stopped `SEED-M1` from being created, and the harness would then have reported a document's fault for its own broken setup. A harness whose setup fails quietly blames the thing it is testing — the same class as the first exercise's fresh-hub-per-command mistake | medium |
| `X-11` | `architecture` | "An ADR attached to nothing is a preference" is stated flatly and enforced nowhere, while the neighbouring undecided rule (`falsifier`) *is* disclosed as an open question. Now disclosed too, with the reason it stays unenforced | minor |

`X-1`, `X-2`, `X-3`, `X-9` and `X-10` have regression tests, each **proven to fail against the old
code** before the fix was accepted: `tests/test_status_contract.py`,
`tests/test_domain_vocabulary.py`, `tests/test_metric_denominator.py`, and a ninth check in
`check_repo.py coverage`.

### The denominator that could not be recomputed (`X-4`)

The first exercise published "**57 of 102** production environment variables are undocumented,
counting distinct reads in non-test source, excluding build output" — and
`shared/references/docs-conformance.md` used that very sentence as its worked example of a
*checkable* claim.

Re-running it on the same commit of the same repository, I could not reproduce any part of it.

| Reading of "excluding directories matching `test|bench|harness`" | Distinct names |
|---|---|
| exclude a path whose segment matches | 93 |
| exclude a project directory whose name matches | 96 |
| exclude a `.Tests`-style project name only | 103 |
| no exclusion | 131 |

Four honest readings of one sentence, four answers. **A denominator nobody can recompute is not a
denominator** — and the reference was teaching the error while holding it up as the good example.

The fix is small and total: **record the enumeration as a re-runnable command, verbatim, beside the
number**, and put it in the profile as `capability_inventory_method`. The next pass then recomputes
instead of re-deciding.

### The corpus nobody stated (`X-4`, continued)

Worse, and more interesting. The *code* side of a coverage ratio gets all the attention; the
*documentation* side needs a stated corpus just as badly.

| Documentation corpus | Undocumented |
|---|---|
| the public site only | **85 of 131 (65%)** |
| site + the product's own shipped `docs/` + the chart's inline comments | **23 of 131 (18%)** |
| … less 7 `*BENCH*` knobs that are not operator surface | **16 (12%)** |

Same product, same commit, same enumeration: **47 points of difference**, entirely from an unstated
choice between two items on the method's *own* list of documentation surfaces. And the three
variables the first exercise named as its headline examples — `ZARIS_CLIENT_PORT`,
`ZARIS_CLUSTER_PORT`, `ZARIS_HEALTH_PORT` — are documented in the shipped docs and the chart. The
finding named, as its evidence, three things that were documented all along.

### One language is not the surface (`X-5`)

The method says to grep "the environment-read API". Following it on `*.cs` gave **96** names.
Repeating it across the Helm chart, Dockerfiles, the web console's TypeScript and the entrypoint
scripts gave **131** — 53 names invisible to a single-language grep.

It does not only undercount. **Three of five reverse-direction findings were manufactured by it**:
variables documented and real, reported as nonexistent purely because the grep could not see the
chart or the console that read them. After the multi-language sweep, 2 of the 5 survive.

## Defects in the product

All six established from the product's own artifacts, with the artifact named.

**P-1 — the consolidated report says no keys were affected; the evidence beside it says 49.**
`FINAL_CERTIFICATION_REPORT.md`'s "Top Failure Attribution" reads `Keys affected: 0` for
`CheckpointValidation`, the only failing category of a FAIL run. `failed-keys.json`, in the same
directory, reads `DistinctKeyCount: 49`. The report is what its own artifact index calls the
"Human-readable consolidated certification result and investigation guide" — the first thing an
operator reads. Reading it, 13 failures look like a harness artifact that touched nothing.
**The most likely of the six to cause a real mistake**, because it points the reader away from a
real defect.

**P-2 — there is no availability contract, and the hole it leaves is minutes wide.** The 168-line
`consistency-and-durability-model.md` uses the word "available" once, in passing. Nothing states how
long a key may be unservable after an ownership change. The only convergence budget in the product,
`ConvergenceSLO`, lives in the test suite and measures *replica data* convergence; production code
names it only in comments about past aborts. Meanwhile the 4-hour rung records 49 distinct keys
across 49 distinct segments, all `Status: ActiveReadFailed`, message `Read with Leader returned
Moved: Segment N not owned locally` — each acknowledged **218 to 274 seconds** before the failing
read, with the longest `Degraded` window in `ownership-history.json` at **248.9 s**. Durability over
the same run is clean: 0 missing, 0 corrupt, 0 version regressions over 3,122,373 keys. *Does not
claim* those segments were continuously unavailable for the whole window — the artifact fixes one
instant, that long after acknowledgement. Nothing promises a bound, so nothing was violated, which
is why a window this size sits open with every gate green.

**P-3 — partition durability rests on an anti-affinity the chart does not set.** The contract is
that replicas live on distinct *pods* and a rescheduled pod rebuilds from another pod's copy, with
state on an `emptyDir`. Pods are not failure domains. `node.affinity` is `{}` by default and the
`StatefulSet` applies affinity only `with .Values.node.affinity`, so both pods of a partition may
land on one Kubernetes node; draining it takes both copies. `pdb.maxUnavailable: 1` covers voluntary
eviction only and does not apply to node failure. No zone, rack or failure-domain concept exists
anywhere in the server — placement is disjoint across *instances* and blind to anything physical.
The related multiple-of-RF precondition **is** warned about, and only warned about: in
`NOTES.txt`, printed after `helm install` exits 0.

**P-4 — the ownership sampler is blind exactly where the failure is.** `ownership-history.json`
holds **no sample between `07:41:33` and `07:46:00`**, a 4m27s gap straddling the `07:45:06`
failure, and its last sample before the gap reports P0 `Healthy`. So no root cause is establishable
from the run's own artifacts. Two further defects in the same file: the two samples at `07:41:33`
are byte-identical duplicates, and the 554 samples split 279/275 across two partitions, so sampling
is neither regular nor deduplicated. *Does not claim* ownership was unhealthy during the gap — the
defect is that the artifact cannot say either way.

**P-5 — 16 of 131 configuration variables are undocumented anywhere**, four of them telemetry:
`ZARIS_NO_TELEMETRY`, `ZARIS_TELEMETRY_KEY`, `ZARIS_TELEMETRY_URL`, `ZARIS_LICENSE_TELEMETRY_URL`.
An undocumented telemetry opt-out in a self-hosted store is the most consequential of the sixteen.
Enumerated by the command recorded in the profile; corpus = public site + shipped `docs/` + chart
comments.

**P-6 — two documented variables do not exist in the product**:
`ZARIS_ADVERTISED_ADDRESS_EXTERNAL` and `ZARIS_RESP_FAILOVER_MODEL`, both on the public site, both
absent from every tracked file in the repository in every language.

## What the exercise settled about the skills themselves

`architecture`'s `falsifier` field was the suite's own invention, marked untested in its own open
questions. **The team's records settled it, not an argument.** None of their five Decisions states a
falsifier — and two carry a dated `## Addendum` recording that the decision was later found wrong or
incomplete: *"the fence had a hole: a Handoff→Recovering bounce"*, and a regression-and-revert of
half a fix. Those addenda are falsifiers, written after a failed run paid for them. Proposing the
field is adoption of a practice the team already has, moved earlier — which is the argument to make
to them, and it is not one I could have made without reading their history.

## Mistakes I made in this exercise

- **I published a product finding I could not reproduce.** "57 of 102", with three headline examples
  that were documented all along. The cause was not arithmetic: the method let me state exclusions
  in prose and never asked which docs counted. Both are now fixed in the method, which is the only
  reason the mistake was worth making.
- **I wrote a skill example that fails when pasted.** `hub.py link ADR-3 blocked_by RISK-2`, in
  `architecture`, referencing two items nothing creates. My own `test_documented_commands.py` caught
  it on the next run.
- **My first refusal message gave a confidently wrong suggestion.** `self-hosted-deployment -- did
  you mean payments?`, from difflib at a 0.4 cutoff. A wrong hint is worse than none: a reader who
  accepts it reads the fault catalogue for the wrong class. Tightened to require a shared token or a
  0.8 ratio, and tested in both directions.
- **I nearly reported five reverse-direction findings where two were real.** Three were my
  single-language grep's blind spot. Checking each against the whole repository before reporting is
  what caught it — the check took one command.
- **I set a product class the suite has no file for** and the tool let me. That is `X-2`; I was its
  first victim.

---

# Third exercise — `analytics` and `backlog`, 2026-11-05

`analytics` against the product's **three certification rungs** rather than one; `backlog` against
its real 157-line cloud-readiness requirements document — 9 themes, **29 ids** `CR-A1`…`CR-I2`, each
theme carrying one `**Acceptance:**` line.

Six defects in the suite, five in the product, and the most serious finding of all three exercises.

## Defects in the suite

| id | Where | Defect | Severity |
|---|---|---|---|
| `Y-1` | `metric`, model | **A reading had to be sourced and the baseline did not.** `BASELINED` required `denominator` and `baseline`; `READ` required `value`, `denominator` and `evidence`. So the number every future reading is compared against needed no provenance, while the readings did — exactly backwards, since an unsourced baseline silently poisons all of them. `analytics` says "compare to the stated baseline, not to a recollection", and the hub could not tell one from the other | major |
| `Y-2` | `analytics` | **The unit of analysis was the run, not the series.** Steps 3–5 say to compare to a baseline, segment a population, and verify instrumentation — nothing said that reading one acceptance run out of several is itself a selection effect, with the same shape as reporting only the metrics that improved. It produced a confidently wrong verdict: see `P-7` | major |
| `Y-3` | `backlog` | **The criterion test passed a criterion that cites an authority which does not exist.** Question 2 asks "what independently says pass or fail?", and *"within the documented RTO"* is an excellent answer to it — until you look and find no RTO with a value anywhere in the repository. A citation to a document that does not say is the most convincing kind of untestable criterion, because it reads as rigour. Now question 5: open the thing it cites | major |
| `Y-4` | `backlog` | **Criteria stated at a coarser grain than the ids they govern.** 9 acceptance lines for 29 requirement ids, so one criterion covered up to four requirements and some were covered by **no clause at all** — while their theme displayed a perfectly good criterion. See `P-10`. A coarse criterion does not merely under-specify; it makes the gap invisible | major |
| `Y-5` | `hub.py link` | `link_types` is declared in `model.json` — thirteen of them — and was **enforced nowhere on write**. `link A blocked_by B` printed `A --blocked_by--> B` and exited 0; `validate` then mentioned it as a *note*, which does not fail. Worse, the second exercise had just put that exact command into `architecture` as the prescribed way to record a decision's unfinished half, so a reader would have run something that succeeds and records what the hub cannot read | major |
| `Y-6` | `test_link_vocabulary.py` | My own new check scanned skills for undeclared link types and **passed** — because the bad example it was written for used `<angle bracket>` placeholders, and its `\S+` for the subject skipped the line. The check missed the one defect that prompted it. Placeholders are now collapsed before matching | medium |

`Y-1`, `Y-5` and `Y-6` have regression tests proven to fail first: `tests/test_baseline_evidence.py`
and `tests/test_link_vocabulary.py`. The latter also asserts that **every link type documented in any
skill or reference is declared in the model**, which is what would have caught `blocked_by` in review
instead of in a hub three steps later.

## Defects in the product

**P-7 — the 3-hour rung lost two acknowledged keys.** This is the most serious finding across all
three exercises, and it is a **correction to my own earlier claim.** The second exercise reported
"durability is clean: Missing 0, Corrupt 0, Version Regressions 0" — true of the 4-hour rung, which
was the one I opened. Reading the series:

| rung | duration | CRUD ops | MissingKeys | OwnershipConvergenceFailures | failed keys |
|---|---|---|---|---|---|
| 2h | 02:03:22 | 1,546,650 | 0 | 0 | 0 |
| 3h | 03:01:38 | 2,127,375 | **2** | 0 | 29 |
| 4h | 04:03:54 | 3,162,600 | 0 | 13 | 49 |

The two keys are `…:0000:000000000003` and `…:0000:000000000007`, `FailureType: NotFound`,
`ExpectedVersion: 1` — created once, never updated, absent at final validation. They appear in
**none** of the acknowledgement snapshot's `Deleted` (5 entries), `Ambiguous` (96) or `Failed`
(11,568) sets. The run is FAIL at 66% confidence. That is acknowledged-write loss by the product's
own validator, against the no-loss invariant in `consistency-and-durability-model.md` §5.
*Does not claim* a root cause: both keys are among the earliest writes of the run, so a
validator-ledger race at start-up is not excluded by this artifact, and the acknowledgement snapshot
is `Truncated: True` to the most recent 300,000 entries — which would have dropped sequences 3 and 7
from the *Acknowledged* list, though not from the three failure sets checked above.

**P-8 — the second exercise's own denominator was wrong by a factor of four.** It recorded the
metric baseline as "49 of 512 replicated segments". The product states its own bound in
`replica-validation.json`: *"Bounded to latest 128 keys per validation pass."* The real reading is
**49 of 128 — 38%, not 9.6%** — and because the pass samples the *latest* 128 keys, the failures are
concentrated in recently-written keys, which is a stronger signal than a uniform sample would be.
The 512 was inferred and nothing required me to source it. That is `Y-1`.

**P-9 — a P1 requirement's acceptance criterion cannot be graded by anyone.** `CR-F` (durability &
disaster recovery): *"a full-cluster restart restores data from the latest snapshot within the
documented RTO."* `RTO` appears in three tracked files — one of them a PNG, one the requirements
document itself — and **nowhere with a value**. The criterion delegates its oracle to a document that
does not exist. It connects directly to `RISK-2`: there is no availability contract to cite.

**P-10 — one requirement is covered by no acceptance clause, in a theme that looks fully specified.**
Theme D (P0, the known blocker) holds `CR-D1` lossless scale-in drain, `CR-D2` HPA/KEDA autoscaling
*with a documented step-size and cooldown policy*, and `CR-D3` spot reclamation — under two clauses:
"repeated automated scale-in/out under load loses **0** keys" and "spot reclamation keeps the store
serving with RF≥2". Clause one covers D1, clause two covers D3, and **nothing covers D2's documented
policy** — clause one passes with D1 shipped and D2 never written, because a manual scale-in can lose
zero keys with no autoscaling policy in existence.

**P-11 — two more criteria are not gradeable by a stranger.** `CR-G`: "a cloud operator sees Zaris
health in their existing monitoring stack **within minutes, no bespoke wiring**" — no number, and
"bespoke" is undefined. `CR-I`: "the Operator converges it **safely**, including drain-safe
scale-in" — "safely" names no invariant. Graded against the five criterion questions by one reader,
so this is a reading and not a verdict (§7). On that grading: of 9 acceptance lines, 5 are oracles,
1 is partial (`CR-C`'s "rotation propagates to nodes" has no time bound), and 3 are not gradeable.

## Mistakes I made in this exercise

- **I was the victim of `Y-1` before I found it.** I wrote "49 of 512" as a baseline in the previous
  exercise, inferred rather than read, and the hub asked me for nothing. The fix is the gate that
  would have stopped me.
- **I claimed "durability is clean" from one run of three.** The 3-hour rung was sitting in the same
  artifacts directory the whole time. `Y-2` is that mistake turned into an instruction.
- **I wrote `6 ids are named by no clause` into the skill without counting.** Caught it on reread,
  within minutes of having corrected exactly that sin in `analytics`. Replaced with the two figures
  I did verify (9 criteria, 29 ids, every criterion theme-level) and an instruction to grade the
  rest case by case and name the grader.
- **My own new check passed while the defect it was written for sat two files away** (`Y-6`).
- **I read `�` in a console dump and checked the codepoints before reacting.** It was U+2014 and a
  cp1252 console. The first exercise reported mojibake that was its own console read; this time the
  check cost one command.

## What is still not exercised

Two skills remain `status: draft`: `design` and `discovery`. They are not untested — every
documented command in all fifteen runs, every state they name is checked against the model, and the
profile contract is enforced for both — but neither has been pointed at a real product, and that is
a different claim.

`discovery` cannot be exercised here at all: its method needs real users to interview, and inventing
them would be the exact failure the suite exists to prevent. It is **NOT RUN**, for a stated reason,
rather than quietly passed. `design` is weak ground on this product: its surface is a management
console and a CLI, with little of the flow-and-state work the skill is about.
