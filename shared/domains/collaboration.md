# Domain: real-time collaboration

Two or more people editing the same thing at the same time. The product's hard claim is
**convergence**: everyone ends up seeing the same document, and nobody's keystroke is lost. Every
interesting defect in this domain is invisible to a single user.

## Do the thing

> Open the same document in two sessions as two different users. Type in both **at the same time**,
> in the same paragraph. Then take one session offline, keep typing in both, and bring it back.
> Compare the two final documents character by character, and compare both against what each user
> typed. **A single-session test passes on a product that loses every concurrent edit**, which is
> why this is the only domain where the "do the thing" step requires two clients.

## Scope map

| Family | In this domain | Agent | Notes |
|---|---|---|---|
| 1 Acquisition | docs, sign-up, invite flow | own | the invite is the product's real front door here |
| 2 Primary product | concurrent edit and convergence | own ×3 | split: two-writer same-region, offline/reconnect, permission change mid-session |
| 3 Control plane | sharing, roles, link permissions, workspace admin | own | |
| 4 Deployment | if self-hosted: websocket path, sticky routing, relay | own | load balancers that break websockets are the classic |
| 5 Entitlement | seats, guest limits | →3 | |
| 6 Secondary | comments, mentions, presence, version history, export | own ×2 | version history is a durability claim; export is a data-portability one |
| 7 Telemetry | presence and activity signals | →12 | |
| 8 Security | **access revocation while a session is live**, link sharing, tenant isolation | own | |
| 9 Documentation | the conflict-resolution and offline claims | own | "automatically merges" needs a stated semantics |
| 10 State under fault | network partition, reconnect, server restart mid-edit, clock skew | own ×2 | split: partition/reconnect vs server-side restart |
| 11 Upgrade | schema change to the document format, mixed client versions | own | old clients editing new documents is the trap |
| 12 Experience | does the user ever see someone else's edit overwrite theirs | lead | |

**Usual set: 1,2×3,3,4,6×2,8,9,10×2,11 own + 5→3, 7→12, 12→lead = 13 agents.**

## Failure catalogue

- **Lost update under true concurrency.** Two users type in the same paragraph; one user's text is
  gone and nothing reports an error. The product looks fine to both until someone notices.
- **Divergence.** Both sessions stop erroring and show *different* final documents. Worse than a
  lost update because neither user can tell which is real.
- **Offline reconnect drops the offline work**, or applies it twice.
- **Revocation does not reach a live session.** Access removed in the control plane; the open tab
  keeps editing and its writes keep landing. This is the security defect of this domain, and it is
  routinely `critical`.
- **Presence lies.** Shows a user who left, or omits one who is editing — which makes users
  overwrite each other deliberately.
- **Version history is not a restore path.** It lists versions and cannot reproduce one, or restores
  a version that never existed.
- **Comment or mention anchored to deleted text** — orphaned, misplaced, or silently dropped.
- **Export loses structure** the editor shows: a data-portability claim failing quietly.
- **Mixed client versions corrupt the document** when the format changed between them.
- **Cursor or selection jumps** on remote edit — not a correctness bug but the loudest usability one.

## Defect classes to look for by name

| Class | What makes it this class |
|---|---|
| **Lost update** | A keystroke that was accepted and is not in the final document |
| **Divergence** | Two clients, two different final states, no error |
| **Stale authorisation** | A revoked user's writes still land |
| **Offline reconciliation defect** | Offline edits dropped, duplicated or reordered on reconnect |
| **History/restore defect** | A listed version cannot be restored, or restores wrongly |
| **Anchor drift** | Comments, mentions or links attached to the wrong content after an edit |

## Evidence and severity

**Evidence here is always a pair of client transcripts plus the final state.** One client's view is
not evidence of convergence; it is evidence of what one client thinks. Record what each user typed,
in order, with timestamps, and the final document from each session independently.

`shared/principles.md` §3 applies sharply: **the product's own "synced" indicator is not an oracle.**
A green sync badge over a divergent document is the single most common false pass in this domain.
Compare documents, not badges.

Severity: a **lost update is `critical`** — it is acknowledged-work loss, and this suite treats that
as data loss regardless of how small the text was. **Divergence is `critical`.** Stale
authorisation inherits the sensitivity of the document. Cursor jumps are `minor` unless they cause
mis-edits, in which case say so and grade by that.

## Experience

The question this domain is judged on: **can a user ever lose work without being told?** Everything
else is secondary. If a conflict is resolved by picking a winner, the loser must be told and must be
able to recover their text.

Then: **what does the product look like at second two of a network blip?** A banner that says
"reconnecting" while silently discarding keystrokes is worse than freezing the editor, because the
user keeps typing into nothing.

Time to first success is **two people editing one thing**, not one person opening a document — and
that includes the invite, which is why family 1 is owned here rather than skipped.

## Domain gotchas

- **You cannot test this with one client.** Two sessions, two identities, genuinely concurrent.
- **"Last write wins" is a semantics, not a bug** — but it must be documented, and users must be
  able to see what was overwritten. An undocumented LWW is a documentation defect at the severity of
  the data lost.
- **Websockets through a proxy** are the most common self-hosted failure, and they fail as
  "collaboration doesn't work" rather than as a network error.
- **Clock skew between clients** affects ordering in any timestamp-based resolution.
- **Clean up every document, workspace and invited guest** in the cleanup ledger: invited test users
  retain access until removed, which is an exposure, not untidiness.
