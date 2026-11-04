# Contributing

`main` is protected: **all changes arrive as pull requests.** Fork, branch, open a PR — nobody pushes to
`main` directly.

## Run the checks; they are the house rules

The old version of this file listed four places a new domain file had to be registered. A rule that
depends on someone remembering four places fails silently, so it is now a check that fails loudly:

```bash
python -I shared/scripts/check_repo.py
```

Seven checks. They assert that every `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_SKILL_DIR}` path resolves **as
an installed plugin would see it**, that no shell block uses a `$CLAUDE_*` variable (those are substituted
into skill *text* at load and are not in the environment of a model-run command), that every domain file is
registered everywhere it must be, that counts stated in prose match the actual file listing, that every
domain file carries its seven headings, that no prose line exceeds 110 columns, and that no real hostname,
path, tenant id or key appears in an example. That last check has already caught a live violation.

Before opening a PR, run all of it:

```bash
python -I shared/scripts/test_hub.py
python -I shared/scripts/test_safe_edit.py
python -I shared/scripts/test_qa_dashboard.py
python -I shared/scripts/check_repo.py
python -I tests/test_description_budget.py
python -I tests/triggers/check_overlap.py
python -I tests/fixtures/build.py --all
claude plugin validate .
```

Python is **standard library only**. No new dependencies — a skill that needs a package installed is a
skill that silently does not run.

## The most useful contribution is a domain file

`shared/domains/README.md` lists the product classes that are missing and worth writing, and states the
bar a new one has to clear. A domain file earns its place when it has all three of:

1. a **distinct oracle** — something to grade against that no existing file provides,
2. a **fault catalogue** not already written down elsewhere, and
3. a **severity mapping that differs** from the generic one.

Anything that fails all three belongs in a scope family, not a new file. Accessibility, localization and
privacy are cross-cutting on purpose and already live in the families and in
`shared/references/experience.md` — please don't add them as domains. Performance is the one that fails the
test differently: it has its own oracle and its own fault population, so it is scope **8b** in
`skills/qa/references/scope-playbooks.md` rather than a domain file.

A new file copies the seven fixed headings (*Do the thing · Scope map · Failure catalogue · Defect classes
to look for by name · Evidence and severity · Experience · Domain gotchas*), declares its applicable scope
set with an agent count that fits the 11-agent ceiling, and runs 60–110 lines. One extra domain-specific
section is allowed after *Do the thing* where the domain needs one, as `payments.md` and `ai-tutor.md` each
do.

**Write it from an engagement, not from first principles.** That is the whole difference between a file
that works and a file that reads well. "Three nodes formed and one write was acknowledged and read back
from a different node after the leader was killed" is useful; "the product works" is not.

## Changing a skill

Each skill is `skills/<name>/SKILL.md`, **under 300 lines**, with detail in its own `references/`. It
loads on every trigger, so length there costs every user.

- **The description is the trigger**, and it is budgeted. 700 characters each, and the plugin's measured
  always-on cost must stay under 2,500 tokens (`tests/test_description_budget.py`). If that fails, trim —
  do not raise the ceiling. Over budget means Claude Code silently *drops* descriptions, starting with the
  least-invoked skills.
- **Every description needs a "Not for…" line** naming the neighbouring skill, because that is the only
  device in a description that pushes a prompt away. If you add a skill, add it to
  `tests/triggers/corpus.json` with five prompts that should route to it and five near-misses that should
  route elsewhere — `check_overlap.py` will tell you which boundaries you have left unguarded.
- **Items are created and moved only through `hub.py`.** A skill that writes a hub file directly breaks
  the one property the hub has.
- **Don't restate a shared rule.** Link to `shared/principles.md` or `shared/vocabulary.md`. A rule written
  in two places is two rules that drift.

Thirteen of the fifteen skills are marked `status: draft` in their own README because they were written
from first principles. **If you have run a real engagement in one of those roles, correcting it from
experience is the highest-value contribution in the repo** — and say in the PR what the evidence was.

## Changing the method

`skills/qa/`, `skills/dev/` and everything in `shared/` are the method, and changes there affect every
user. A PR that changes them should say **what evidence prompted it** — a defect class the method missed, a
run where it gave the wrong answer, a rule that turned out to forbid the testing it was meant to enable.
The biggest revisions so far all came from that: the state, upgrade and experience scopes exist because the
first version never asked whether data was still correct after a fault; the destructive-operations rule was
rewritten after it was found to forbid exactly the testing stateful products need most; and the computed
verdict exists because a review showed that a register nothing can refuse is decoration.

**A change to how QA enters or exits a phase is a decision, not a tidy-up.** Record it in
`docs/design/plugin.md` §8 rather than re-pointing it quietly.

Opinions about wording are welcome as issues. Opinions presented as defects are the thing this plugin
exists to prevent.

## House rules

- Prose wraps at about 110 columns. Tables, code blocks and link lists don't wrap.
- Cross-references use `${CLAUDE_PLUGIN_ROOT}/…` for shared files and `${CLAUDE_SKILL_DIR}/…` for a
  skill's own, and must resolve. **Never** a `../` path: a marketplace install copies the plugin, so
  anything above the root is simply absent, and it will work for you and break for everyone else.
- Always write the namespaced `/product-suite:<skill>` invocation. Never the bare form with the skill name
  alone — `check_repo.py lint` fails on it, because bare names resolve by an origin order this plugin does
  not control and one of them already collides with a skill that ships by default.
- No real hostnames, tenant ids, customer names, keys or tokens in examples — not even redacted ones.
  Refer to them by role, which is what the method requires of its own reports.
- Generated files (`qa-state.json`, `fix-state.json`, fixture dashboards) are regenerated, never
  hand-edited. If you need a different shape, change the generator.
