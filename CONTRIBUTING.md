# Contributing

`main` is protected: **all changes arrive as pull requests.** Fork, branch, open a PR — nobody pushes to
`main` directly.

## The most useful contribution is a domain file

`references/domains/README.md` lists the product classes that are missing and worth writing, and states the
bar a new one has to clear. A domain file earns its place when it has all three of:

1. a **distinct oracle** — something to grade against that no existing file provides,
2. a **fault catalogue** not already written down elsewhere in the skill, and
3. a **severity mapping that differs** from the generic one.

Anything that fails all three belongs in a scope family, not in a new file. Accessibility, localization,
privacy and performance are cross-cutting on purpose and already live in the families and in
`references/experience.md` — please don't add them as domains.

A new file copies the seven fixed headings (*Do the thing · Scope map · Failure catalogue · Defect classes
to look for by name · Evidence and severity · Experience · Domain gotchas*), declares its applicable scope
set with an agent count that fits the 11-agent cap, and runs 60–110 lines. One extra domain-specific
section is allowed after *Do the thing* where the domain needs one, as `payments.md` and `ai-tutor.md` each
do.

**Write it from an engagement, not from first principles.** That is the whole difference between a file
that works and a file that reads well. "Three nodes formed and one write was acknowledged and read back
from a different node after the leader was killed" is useful; "the product works" is not. If you have not
run a QA pass on this class of product, the file will show it.

## Changing the method itself

`SKILL.md` and the files in `references/` are the method, and changes there affect every run. A PR that
changes them should say what evidence prompted it — a defect class the method missed, a run where it gave
the wrong answer, a rule that turned out to forbid the testing it was meant to enable. The two biggest
revisions so far both came from that: the state, upgrade and experience families exist because the first
version never asked whether data was still correct after a fault, and the destructive-operations rule was
rewritten after it was found to forbid exactly the testing stateful products need most.

Opinions about wording are welcome as issues. Opinions presented as defects are the thing this skill exists
to prevent.

## House rules

- `SKILL.md` stays under 500 lines. It is loaded into context on every trigger, so length there costs
  every user. Detail goes in `references/`.
- Prose wraps at about 110 columns. Tables don't wrap.
- Cross-references use backticked filenames (`` `references/evidence-standard.md` ``) and must resolve.
- No real hostnames, tenant ids, customer names, keys or tokens in examples — not even redacted ones. Refer
  to them by role, which is what the skill requires of its own reports.
- A PR that adds a domain file should also add its row to `references/domains/README.md`, its line to the
  per-domain index in `references/experience.md`, and update the count in `SKILL.md` and `README.md`. All
  four, or the repo starts lying about itself.
