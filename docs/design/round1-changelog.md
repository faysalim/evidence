# Round 1 changelog

**Why this file exists:** the commit `0d4c25f` that carries these changes has a mangled message.
Backticks in the `-m` argument were interpreted as shell command substitution and the message
captured an environment dump. Amending was refused by this session's permission rules -- correctly,
because rewriting history was forbidden for this run -- so the intended message lives here instead.
The commit's *contents* are correct; only its message is polluted.

---

Council round 1: close 8 critical verdict bypasses and 5 blockers

Applies HA-1..8, CR-1/2/5/6, MG-1/2/3, PP-2/3/5/8, SF-1/2/3. Every fix was
reproduced here before being accepted; the repros are in docs/design/council-review.md.

The headline: the adversary found SEVEN independent ways to get GREEN out of a hub
that should not be green, two of them available to DEV alone. All seven are closed.

Write-path authority (HA-1, HA-2, MG-1)
- fields_owned_by was enforced only in "set", so a move or add carrying
  severity=polish walked past it. A DEV could un-block a release while the dashboard
  reported no open critical and validate ran clean. One helper now guards add, move
  and set, on the CLI and on replay.
- "add --state CLOSED" reached ANY state with no transition rule applied: one flag
  defeated every authority rule in the model. Creation is the initial state only.
- A case now requires action and oracle at creation. principles.md claimed this was
  enforced before it was true.

requires_fields semantics (CR-2)
- It OR-ed with fields already on the item, so a release reaching SHIPPED already
  carried QA's reason from NO_VERDICT and the operator's own reason was never
  demanded. The audit trail showed a reason-less ship that read as reasoned. Now
  checked against the fields on THIS event, by presence rather than truthiness, so a
  metric reading of 0 is a reading.

Verdict robustness (CR-1, HA-3..8, MG-3, CR-3)
- A prose guards value crashed the only verdict path with an AttributeError, and
  prose is the form every skill documents. guards and severity are validated on write
  and read defensively; unreadable means unknown, and unknown denies.
- A FAIL case with a blocking ceiling did not deny the verdict: the page printed
  "cases fail: 2" and GREEN together.
- DUPLICATE pointing at nothing, an unknown or space-padded severity, and a cleanup
  item parked in OPERATORS all hid real state from the verdict.
- Restored "Build identity established per component", which qa_dashboard.py computed
  and the port lost. It is the condition the whole iteration gate rests on. Added a
  check that smoke and calibration ran on the build the verdict names.

Log integrity (HA-7, HA-10, HA-12, HA-13, HA-17)
- An unreadable line was a note, so validate exited 0 and the verdict went GREEN over
  a log the hub had failed to read. UNREADABLE and MISATTRIBUTED are now problems,
  and a malformed payload is reported rather than raised.
- event_id was actor-and-seq per role/actor FILE, so one person wearing two hats
  produced two colliding ids and the fold silently dropped the second.
- The fold trusted role and actor in the payload over the path holding the line.
- The view check was a row count; a hand-edit with the header intact passed clean.
  Now a sha256 over the applied event ids.

GREEN is computed on the write path too (MG-2, HA-14). The first version of that fix
had a circular dependency the tests caught: it re-ran during replay, where the
mid-fold hub looks stale to its own view, which made a recorded GREEN permanently
unreplayable. It is a write-time precondition, not a replay-time invariant.

Lifecycle dead ends (PP-2, PP-8, CR-5) and the give-up point (CR-6)
- launch and doc CHANGES_REQUESTED, metric NOT_MEASURABLE and finding DEFERRED were
  all terminal, so send-back-and-resubmit and "deferred to the next build" were
  one-way doors out of the id. Return edges added.
- Added unlink. A wrong verifies link permanently blocked story acceptance with no
  documented way out, and that is where the cold runner gave up.

waiting_on ignored escape hatches (PP-5, CR-9): a SHIPPED release was reported as
awaiting the operator because it can still be rolled back, which made the delivery
report's first and most-read section wrong by construction.

Windows (PE-3): every read command died with UnicodeEncodeError once an item carried
a character outside cp1252, and python -I, which every skill prescribes, ignores
PYTHONUTF8. stdout and stderr are now reconfigured explicitly.

Also: the colon dropped from SAFE_ID, because on Windows it became an NTFS alternate
data stream and the index linked to a page that did not exist. Severity ownership
widened to every role that may file a finding, which the designer's own review
finding exposed as too narrow. evals/results removed from the index. NOTICE renamed.
And .gitignore's qa-state.json rule scoped to the repo root: unscoped, it silently
excluded both fixtures' generated view, so a clone got half a fixture and
test_fixtures.py could not catch it because it rebuilds from scratch.

tests/test_description_budget.py now FAILS, deliberately. It measured this plugin's
own always-on cost, but the binding constraint is the skill listing budget shared
with every other skill the user has. See PE-2 in the final report: it needs a product
decision, not a code fix.
