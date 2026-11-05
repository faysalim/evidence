---
name: orient
description: Establish the product profile and baseline before any other skill runs: new or existing product, its product class, the team's methodology, toolchain and existing conventions. For an existing product it builds a capability inventory from the running product and maps their artifacts onto hub item types. Use when starting work on an unfamiliar product or repo, or when another skill reports no profile. Not for testing - that is evidence:qa.
roles: HEAD_OF_PRODUCT
status: draft
---

# Orient

Every other skill calls this one when the hub has no profile, because every other skill otherwise guesses:
which domain file applies, what the team calls a story, whether `main` is the branch that deploys.

The rule that makes this skill worth running is `shared/principles.md` §10 — **reality beats paperwork.**
An existing product's backlog says one thing, its architecture diagram another, and its running code a
third. You are not here to tidy that up. You are here to write down all three and name the gaps, because
the gaps are the most valuable thing you will find and they are what everyone on the team is already
quietly confused about.

Read `${CLAUDE_PLUGIN_ROOT}/shared/principles.md` first. Items move only through
`python "${CLAUDE_PLUGIN_ROOT}/shared/scripts/hub.py"`.

## Step 1 — New or existing, and say which

```
hub.py status
```

| Mode | How you know | What changes |
|---|---|---|
| **NEW** | No product in production, no users, no prior artifacts | The profile is authored. Everything downstream is a first draft, and nothing is `reconstructed` |
| **EXISTING** | There is a running product, or users, or a prior backlog | The profile is **reconstructed from the product**, not from its documents. Downstream work is a *delta* against what is there |

Record it as the first profile field. Getting this wrong is expensive in one direction: treating an
existing product as new produces a PRD that describes a product nobody has, and a backlog of stories that
are already built.

## Step 2 — Product class, from the product

Pick from `${CLAUDE_PLUGIN_ROOT}/shared/domains/` — twenty-seven classes, indexed in its README. **Read the
closest one, and every one that applies**: a SaaS CRM is `crm.md` **and** `multi-tenant-saas.md`; an
API-fronted licensing platform is `licensing-server.md` **and** `api-platform.md`. Take the union.

Choose from what the product *is*, not what it is called. A "platform" that serves one tenant from one
database is not `multi-tenant-saas.md`; a "simple internal tool" that acknowledges writes and loses them
on restart is `distributed-database.md`'s problem whatever anyone calls it. If nothing is close, say so in
the profile and work from the scope families — then write the missing domain file afterwards, because the
next person in that field will need it.

```
hub.py profile --set mode=existing --set 'domains=["crm","multi-tenant-saas"]'
```

## Step 3 — Methodology, toolchain, conventions: adopt, never impose

This is the step that decides whether the team can use any of this. **Adopt their templates and their
terms.** If they say "ticket", the skills say ticket. If their definition of done includes a security
review, that is in the story lifecycle. If they use two-week sprints and a physical board, nothing here
asks them to stop.

Write `conventions.md` beside the profile, and have every downstream skill read it:

```
<report-dir>/conventions.md
```

| Record | Because |
|---|---|
| Their words for each item type | A `story` called an "MMF" that your report calls a story is two vocabularies in one team |
| Their definition of ready and of done | The hub's `story` lifecycle is a default, and theirs wins |
| Their severity scale, mapped to ours, **once** | A `blocker` that lands in their tracker as P2 gets scheduled rather than fixed |
| Their tracker, and whether the hub feeds it or shadows it | Decide this up front; two systems of record with no stated primary is how both rot |
| Branch, review and release conventions | Which branch deploys, who approves, what gates a merge |
| Test style and where tests live | So a handback's tests are ones they will keep |
| Their meeting and reporting rhythm | A status report nobody reads at a time nobody looks is not a deliverable |

**What not to adopt:** the ten principles. If the team's convention is that a verdict is written by whoever
is most confident, or that the author closes their own work, that is the thing this suite exists to change,
and it goes in the profile as a gap rather than a convention. Say it plainly and let the operator decide.

## Step 4 — For an existing product: inventory the product, not the documents

This is the heart of the skill, and it is `/evidence:qa`'s Step 1 applied before anyone tests
anything. **Establish each of these from the artifact, and record how you established it:**

| What | How |
|---|---|
| Which branch actually deploys | The hosting config, not the repo default. One repo's `master` was a month stale while the live line was `release/2.5.0` |
| Which build is live, per component | A version endpoint, an image digest, or a string you can grep in the served asset. Record the commit delta from the branch tip |
| What the product actually exposes | The route table, every environment-variable read, the option parser, the config schema. This is the **capability inventory**, and it is enumerated from code, never from the docs |
| What the docs claim it exposes | The published surface. The difference, both ways, is your first set of findings |
| What data it keeps, and what it promises about it | Consistency, durability, delivery guarantees — stated or **absent**. An absent contract is itself the first finding |
| Who the users actually are | There is rarely one. An admin, an end user, an implementation partner, a support agent |

**Do the thing, once, as a user would.** Install it, sign up, run the quickstart — and time it. That
first-run trace is perishable: you get exactly one genuine first encounter with a product, and it is also
the baseline every later iteration is measured against.
`${CLAUDE_PLUGIN_ROOT}/shared/references/experience.md`
has the method. Take it **before** you read the architecture docs, or label it warm and say so.

## Step 5 — Map their artifacts onto hub types

Existing products arrive with artifacts. Map rather than rewrite:

| They have | Becomes | Note |
|---|---|---|
| A backlog or tracker export | `story` items | `provenance: reconstructed`. Stories with no testable criterion are flagged, not fixed — that is `/evidence:backlog` |
| A PRD, spec or wiki page | `prd`, `requirement` | A reconstructed current-state PRD comes first; the change is a delta against it |
| An architecture diagram or ADR folder | `adr` | Record the architecture that *is*, then the decision to change it |
| A bug tracker | `finding` | Ids preserved. States **not** inherited: nobody verified them here |
| A test suite | `case` items for what it actually asserts | A test whose assertion is weaker than its name is a finding |
| Runbooks, SLOs, a contract | **acceptance requirements**, source 0 | The highest-authority oracle there is, and the one most often missing from QA |
| Cloud resources, tenants, keys you touch | `cleanup` | From minute one |

`hub.py import <dir>` does the mechanical part for a prior `qa-state.json`. Everything else is `add
--provenance reconstructed`, and the mapping itself goes in the profile so the next person uses the same
one.

## Step 6 — Write the profile and the baseline

```
hub.py profile --set mode=existing --set 'domains=[...]' --set methodology=scrum \
   --set deploy_branch=release/2.5.0 --set 'live_builds={"web":"a1b2c3d"}' \
   --set conventions=conventions.md --set acceptance_requirements=<path>
```

The **baseline** is the part people skip, and it is what makes the next iteration measurable: time to
first success, the live build per component, the capability count with its denominator, and the gaps
between code, docs and backlog. Record it as an `initiative` item if the work has a name, or as profile
fields if it does not.

Finish by stating, in one short paragraph, **what you could not establish and why** — the credentials you
were not given, the environment you could not reach, the component whose build you could not identify.
Every downstream skill reads the profile and will otherwise assume you looked.

## For the lead

Two questions to ask of any profile before work starts on it. **Was the product class chosen from the
product or from its marketing?** — that is the single decision that determines which faults anyone looks
for. And **is the conventions file adoption or imposition?** A `conventions.md` that reads like this
plugin's own defaults means nobody asked the team, and the first handoff will be rejected on vocabulary
rather than substance.

## Open questions

- Whether the capability inventory should become `case` items directly (one per route, env var and flag) or
  stay a profile artifact that `/evidence:qa` derives from. Today it is the latter; the former would
  make coverage computable from the hub alone.
- Whether `conventions.md` belongs in the hub as an item with a lifecycle, so changing a convention is an
  event with an owner rather than a file edit.
- No template ships for `conventions.md` yet; it is a heading list in this file. If two engagements write
  it differently, that is the signal to add one.

| File | Read it when |
|---|---|
| `${CLAUDE_PLUGIN_ROOT}/shared/principles.md` | First. §10 governs this skill |
| `${CLAUDE_PLUGIN_ROOT}/shared/domains/README.md` | Choosing the product class, and which pair up |
| `${CLAUDE_PLUGIN_ROOT}/shared/references/experience.md` | The first-run trace, before you read the architecture |
| `${CLAUDE_PLUGIN_ROOT}/shared/references/docs-conformance.md` | Enumerating the real surface, both directions |
| `${CLAUDE_PLUGIN_ROOT}/shared/references/gotchas.md` | Before heavy local work on an unfamiliar repo |
