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

**57 of 102 production environment variables are undocumented**, and three documented names do not
exist in the code. Denominator: distinct `ZARIS_[A-Z0-9_]+` reads in `*.cs` under `src/`, excluding
directories matching `test|bench|harness` and excluding build output; 48 documented across the
site's docs, blog and pages. The undocumented set includes `ZARIS_CLIENT_PORT` and
`ZARIS_CLUSTER_PORT`. *Does not claim* all 102 are user-facing knobs — some may be internal or dead.

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

## What is still not exercised

Six skills remain `status: draft`: `analytics`, `architecture`, `backlog`, `design`, `discovery`,
`prd`. They are not untested — every documented command in all fifteen runs, every state they name
is checked against the model, and the profile contract is enforced for all of them — but none has
been pointed at a real product, and that is a different claim.

`discovery` in particular cannot be exercised here at all: its method needs real users to interview,
and inventing them would be the exact failure the suite exists to prevent. It is **NOT RUN**, for a
stated reason, rather than quietly passed.
