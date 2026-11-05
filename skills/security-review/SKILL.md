---
name: security-review
description: Establish the security, privacy and compliance sign-offs a release needs, each a readiness checkpoint the release verdict reads - what data the change touches, which named authority signs, whether dependencies and secrets were checked against this build, and what the review did not cover. Use when the user wants a security or privacy review, a compliance or legal sign-off, a threat model, or dependency or secret scanning. Not for exploiting or testing the product - that is evidence:qa. Not for deploy, rollback or alerting - that is evidence:ops-readiness. Not for known issues - that is evidence:support-readiness. Not for calling the release - that is evidence:release.
roles: SECURITY
status: draft
---

# Security review

`status: draft` — see `${CLAUDE_SKILL_DIR}/README.md`.

Two failures define this skill, and they are opposites.

**The sign-off nobody can produce.** A release blocked for weeks because "security has to look at
it", with no statement of who signs, what they need, or what question they are answering.

**The sign-off that signed nothing.** A green tick against a review that read the diff, never
established what data the change touches, and did not say so — which is a `PASS` with no evidence
(`shared/principles.md` §3) wearing a more intimidating hat.

So this skill produces **checkpoints with named authorities and stated boundaries**, and it is
governed by §4 — **every claim states what it does not claim.** A security review whose scope is
unstated will be read as covering everything, by everyone, forever.

Items move only through `python "${CLAUDE_PLUGIN_ROOT}/shared/scripts/hub.py"`.

## Before you start: read the profile

```
hub.py status          # mode, the product class, and what orient could not establish
hub.py profile         # the full profile, including their domains and acceptance requirements
```

If there is no profile, stop and run `/evidence:orient` — without it this skill guesses the product
class, the deploy branch and what the team calls things, and a guess here is wrong in a way nobody
notices until the first handoff is rejected on vocabulary.

Read `<report-dir>/conventions.md` too, and **use their words, their ids and their templates.** If
they number requirements `CR-4` or call a story an MMF, so does this skill; existing ids are
preserved, never renumbered. The ten principles in `${CLAUDE_PLUGIN_ROOT}/shared/principles.md` are
the only thing here that is not theirs to set — and `status` prints what orient could not establish,
which you must read before assuming anyone looked.

**This skill does not set the bar.** Regulated products have an external authority — a framework, an
auditor, a contract — and that authority outranks everything here. `/evidence:orient` Step 5 maps it
in as acceptance requirements, source 0, the highest-authority oracle there is. Import it.

## What this skill produces

| Hub item | Note |
|---|---|
| `readiness` | One per sign-off. `OPEN` → `MET` with the **signer, the date and the scope**. Only the operator may `WAIVE` |
| `finding` | A vulnerability is a `finding` with a severity, not a readiness checkpoint. It goes through the same lifecycle as any defect and `/evidence:qa` grades the fix |
| `decision` | Where a risk is accepted rather than fixed — that is the operator's call, in writing |
| `risk` | A known exposure nobody is mitigating yet |

```
hub.py add readiness RD-2 -f title="privacy sign-off: new field is personal data" \
       -f owner_role=SECURITY --role SECURITY
hub.py move RD-2 MET -f evidence="DPIA addendum signed by the DPO 2026-03-05; covers the new \
       field only, not the existing export path" --role SECURITY
```

**A vulnerability is never a `readiness` item.** If you find one, file a `finding` at the severity
its consequence earns. Readiness checkpoints are about whether the *process* that should have caught
it ran; findings are about what it found. Collapsing them hides defects inside a checklist.

## Establish before you review

The order matters, and getting it wrong is how a review signs nothing.

1. **What data does this change touch?** Personal, financial, health, credentials, another tenant's.
   This single answer decides which authorities apply, and it is established from the code and the
   schema, not from the ticket.
2. **Which authority must sign?** A named person or body per concern — privacy, legal, the framework
   owner. "Security" is not an authority; a person is. If nobody can name one, that is the finding.
3. **What build?** A review is about a digest. A review of `main` three weeks ago has expired, and
   saying so is cheaper than discovering it at the gate.
4. **What is out of scope, in writing?** Before you start, not after.

## The checkpoints that earn their place

| Checkpoint | What `MET` requires |
|---|---|
| **Data classification for the change** | What classes of data it touches, established from schema and code |
| **Privacy sign-off** | The named signer, the date, and the scope they signed — a DPIA or equivalent where the change touches personal data |
| **Legal / contractual sign-off** | Where a term, licence or customer contract is implicated |
| **Dependency check against this build** | Run on the candidate digest, with the result. A scan of last month's tree is not about this release |
| **Secrets check** | No credential in the artifact, the image, the logs or the client bundle. `${CLAUDE_PLUGIN_ROOT}/shared/scripts/check_repo.py examples` is this suite's own version of the check |
| **Authentication and authorisation on new surface** | Every new route, flag or field: who may reach it, proven by exercising it as a role that must not |
| **Audit trail for the new action** | If the change adds a privileged action, it is attributable afterwards |
| **Threat model updated, or explicitly not** | "Unchanged" is a valid answer and has to be stated, not left to inference |

**Severity is QA's vocabulary and it applies here unchanged.** A `critical` is a `critical`
(`shared/vocabulary.md`); do not invent a parallel security scale, because the release verdict reads
one scale and a second one is invisible to it.

## For the lead

Read the `evidence` on each `MET` checkpoint and look for three things: **a name, a date, and a
boundary.** A sign-off with no named signer cannot be relied on, one with no date has an unknown
expiry, and one with no boundary will be quoted as covering whatever the reader hopes.

Then ask: **did this review establish what data the change touches, or assume it?** That is the
answer everything else depends on, and it is the one most often skipped because it feels obvious.

## Open questions

- Whether `readiness` needs a signer field of its own rather than prose in `evidence`, so an expired
  sign-off can be found mechanically. Probably yes; it is not done because the field set should be
  driven by one real engagement rather than guessed.
- Whether a vulnerability found here should auto-create a `case` for `/evidence:qa` to grade the
  fix. Today it is a `finding` and QA derives the case, which is one handoff more than necessary.
- This skill deliberately has no scanner integration and no CVE policy: both are product- and
  org-specific, and inventing a default would be imposing one.
- The eight checkpoints are reasoned from common review failures, not measured against a real
  engagement with a real auditor.

| File | Read it when |
|---|---|
| `${CLAUDE_PLUGIN_ROOT}/shared/principles.md` | First. §3 and §4 govern this skill |
| `${CLAUDE_PLUGIN_ROOT}/shared/vocabulary.md` | Severity — one scale, shared with QA |
| `${CLAUDE_PLUGIN_ROOT}/shared/domains/secrets-and-pki.md` | Where the product class is credential-bearing |
| `${CLAUDE_PLUGIN_ROOT}/shared/contracts/release-readiness.md` | The handoff into `/evidence:release` |
