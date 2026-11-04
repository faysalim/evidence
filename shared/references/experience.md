# Experience and usability

A correct product with a bad experience fails anyway, and it fails quietly — nobody files a bug saying "I
gave up". So the experience has to be tested deliberately, not noticed in passing.

The obstacle is not finding UX problems; it is **getting them accepted**. A correctness finding is settled
by evidence. A usability finding gets answered with "that's subjective" and dropped, and the whole
usability section of a report becomes decoration. So an experience finding has to be as provable as a
correctness finding — with one deliberate exception, below, because a report that cannot say "the mental
model is wrong" has not raised its standard, only narrowed its vision.

## Contents

- [What this scope delivers](#what-this-scope-delivers)
- [Who the user is](#who-the-user-is)
- [The first-run measurement](#the-first-run-measurement)
- [Diagnosability — the first-run measurement for operators](#diagnosability--the-first-run-measurement-for-operators)
- [The second week](#the-second-week)
- [Making an experience finding provable](#making-an-experience-finding-provable)
- [Judgement, labelled as judgement](#judgement-labelled-as-judgement)
- [Severity](#severity)
- [Error messages are a product surface](#error-messages-are-a-product-surface)
- [Dangerous affordances](#dangerous-affordances)
- [Losing the user's work](#losing-the-users-work)
- [Waiting](#waiting)
- [Interrupts](#interrupts)
- [Defaults are the experience most users have](#defaults-are-the-experience-most-users-have)
- [Localization beyond string parity](#localization-beyond-string-parity)
- [Accessibility](#accessibility)
- [Per-domain index](#per-domain-index)

## What this scope delivers

What keeps `docs-conformance.md` from being skipped is that it produces **a number the operator wants,
with a stated denominator**. This scope produces two:

- **The first-run baseline table** — one row per surface per iteration: time and steps per milestone,
  exits from the product, the call-someone point. Re-measured every iteration, so it is a regression
  detector rather than an anecdote.
- **The error-message audit score** — one point per question in the five below, per message provoked:
  "41 messages provoked; 12 name the specific thing to change (29%)". A percentage with a denominator is
  arguable in the way a good finding should be.

Plus the findings, the labelled judgement, and the accessibility subsection. If a run of this scope ends
without those two numbers, it has produced opinion.

## Who the user is

Name every one before starting; they rarely share a surface. An operator, an integrating developer, a
buyer, an end user, an administrator, an auditor, and — for mobile — a platform reviewer whose guidelines
are enforced. A product can be excellent for one and unusable for another, and a report that says "the UX
is good" has silently picked one. The domain files in `${CLAUDE_PLUGIN_ROOT}/shared/domains/` carry this
per product class.

## The first-run measurement

The highest-yield experience test, and the most time-sensitive: it has to be taken by whoever is **cold**.
In a multi-agent run that is every scope agent on first contact — a freshly briefed agent is a first-time
user by construction. In a solo run it is you, before Step 1's code reading on the primary surface; if you
have already read the code, say the trace is warm.

**Define first success before starting the clock, and decompose it.** First success is the product doing
its job once — not being installed — and for most products it is a sequence of milestones, each with its
own clock: install → configure → the product running → the first core operation → that operation
confirmed independently (the write read back from another node, the key validating inside the product, the
batch reconciled, the task reopened after process death). A multi-day deployment yields a trace of five or
six timed milestones, not one useless total. The domain files define the milestones per product class.

**"Cold" means as the customer arrives.** For an app or a website, the product with no docs. For
infrastructure — a database, a pipeline, a licensing server — the quickstart and nothing else, because the
quickstart is the only door. Either way, stop reading where a customer would and start doing.

Record as you go:

- **Time and steps per milestone**, and how many steps required *leaving the product* — docs, a dashboard,
  an email, a human. Each exit is a place people drop out.
- **Concepts introduced before first success.** Count the nouns the quickstart makes you learn. "Eleven
  before the first write, of which a user needs three" is a number an operator can argue with.
- **Every guess, backtrack and dead end**, with what you expected versus what happened.
- **Every doc round-trip**, with what you were looking for. Those are the sentences the product should
  have said itself. For developer and operator products the documentation *is* the interface, so it has
  its own experience: can the answer be found by search in two minutes; does the quickstart's claimed
  duration match the measured one (a mismatch is also a scope-9 claim); does an error link to the specific
  page or to the docs home; does the first page tell a newcomer which of three install modes they are in.
- **The empty states.** What the product shows with nothing in it — a blank table, an empty cluster, a
  dashboard with no data. That is where every new user actually stands, and it either tells them what to
  do next or it does not.
- **The point where you would have called someone, or worked around the product.** Not "given up" — users
  of mandated, internal and operator products do not give up, they open a ticket or build a shadow
  spreadsheet, and both are the abandonment analogue. Name the point, **stop the cold clock there**, then
  read or ask and continue warm. The skill's fail-fast rule applies here as everywhere: a cold tester can
  otherwise lose three hours to a typo.

The trace is a **regression baseline**. Re-measure it in later iterations — a milestone that got slower, a
step count that grew after a fix, a new noun — and you have a finding no correctness test can see.

Where a second cold party is available (another agent, another person), take a second trace and diff them.
Convergent failure is the strongest evidence in this file; divergence tells you which failures were
personal. If a person does it, watch in silence.

**Where the real first user is a consultant or implementation partner**, your trace is a proxy and must
say so. Ask the operator for the partner's escalation log and the first-month ticket set — that is the
real first run, and it is field evidence of the strongest kind.

## Diagnosability — the first-run measurement for operators

For a product whose user is an operator, "time to first success" has a sibling that matters more: **time
to diagnose**. Every fault run in scope 10 is also this measurement, for free.

When a fault is injected, start a second clock and answer, from the product's own output only — status,
console, CLI, logs, metrics, in that order, listing which you consulted — when an operator who did *not*
inject it could have named the condition and the action. Record the answer per fault as a time, or as
*never*. "Never — invisible until reconciliation" is a usability blocker that is also an outage, and it is
provable: the fault schedule says exactly what happened and the product's output demonstrably does not.

The same run answers the vocabulary question for the integrating developer: collect every exception the
client SDK surfaced during the fault and ask the error-message questions of each — above all, *did it say
whether retrying is safe?*

## The second week

First-run measures the newcomer. Operators and power users are measured by what the product costs them
every day, which is a different set of questions:

- **Scriptability.** Non-interactive mode without prompts when there is no TTY; machine-readable output;
  exit codes that mean something; idempotent commands safe to re-run; no information that exists only in a
  GUI. For an operator product, "can this be automated?" *is* the experience question, and `--help`
  usually answers it.
- **Repetition cost.** The action done fifty times a day — approving, assigning, acknowledging,
  redeploying — in clicks or keystrokes, and whether a bulk or keyboard path exists.
- **Findability.** Time to locate a known record, setting or log line from a cold start inside the
  product, using its own search and navigation rather than your memory.
- **Terminology drift.** The same thing named differently across CLI, console, docs and logs ("store" /
  "workspace" / "namespace"). A daily tax on every operator, and internal inconsistency in its purest form.

## Making an experience finding provable

Two questions, with different evidence. **Is a user harmed, how often, and how badly?** — that is the
finding. **Is the fix uncontroversial?** — that is what gets it accepted. Reach for the highest available
on the first axis; attach the second wherever it exists.

**Evidence of harm, strongest first**

1. **Field evidence.** Real users have already failed here: support tickets, docs-site search queries,
   forum threads, store reviews, analytics drop-off, an implementation partner's escalation log. Ask the
   operator for it at Step 0. It is usually the cheapest evidence in the run and the only kind that
   carries *frequency*.
2. **Convergent cold runs.** Two or more independent first-time users — people, or separately briefed
   agents who have not seen each other's output — stop at the same point. Where they agree the finding is
   reproducible; where they diverge you have learned which failures were personal.
3. **A blocked or abandoned goal, n = 1.** State the goal, then show where the path stops, loops, or
   needs information the user does not have. "A self-hosted prospect cannot discover the activation
   variable without reading the source" is a fact about the product.
4. **A measurement against a baseline.** Time, steps, exits from the product, doc round-trips, recovery
   attempts, concepts before first success, time to diagnose. A measurement is evidence only *relative to
   something*: the product's own other path, a previous iteration, a competitor, a stated budget, or the
   docs' own promise — a "5-minute quickstart" that took 47 minutes is also a docs-conformance claim and
   should be filed there too. A number with no comparator is taste with decimals.
5. **A convention violation with a named cost.** Cite the specific convention — platform guidelines,
   WCAG, POSIX exit-code and `--help` conventions, what the category's other products do — and say what it
   costs this user. Where the convention is *enforced* (store policy, performance-vitals thresholds, app
   review) the platform has named the cost for you, and the finding ranks higher than an unenforced
   convention would.

**Evidence that the fix is uncontroversial**

**Internal inconsistency — the product already does it right somewhere else.** This removes taste from the
argument: it is the product's own two surfaces disagreeing, and one of them is the author's own answer.
It is the strongest *acceptance* lever here and should be attached to any finding where it exists. On its
own, though, it establishes only that the product disagrees with itself — so before filing it, check
whether the two surfaces serve two audiences on purpose (the skill's own reasoning trap: two
near-identical things usually exist for a reason), and name the user cost of the disagreement. An
inconsistency that blocks nobody is polish.

**Not evidence: aesthetic preference with no stated cost.** If you cannot name the user goal it damages,
it is polish or it is nothing. A usability section padded with taste is what teaches people to ignore
usability sections.

## Judgement, labelled as judgement

Some experience truths are not reachable by any evidence kind above: the product has too many concepts;
the mental model it teaches first is the wrong one; an error is technically precise and still frightening;
the primary workflow is organised around the implementation rather than the task. Refusing to write these
down does not make a report more rigorous — it makes it blind to the findings that most need a human to
say them.

Write them in their own subsection — **Assessment** — as expert judgement with its reasoning and, where
one exists, the heuristic it rests on. Three to five observations, not thirty. They are **not ranked, not
counted in the finding totals, and get no finding ids**; they are routed exactly as `DECIDE` items are, as
a decision memo with options and a recommendation, because that is the form an operator can answer. A
judgement dressed as a finding gets argued with; the same judgement written as "here are two directions
and the one I would take" gets a reply.

The test for inclusion is not provability but **falsifiability by the operator**: they must be able to say
"no, because…" and have that end it. "The onboarding introduces eleven nouns before the first write; a
user needs three" passes — the count is checkable, the recommendation concrete. "The UI feels dated" does
not.

## Severity

Consequence-based, like the bug rubric in `${CLAUDE_PLUGIN_ROOT}/shared/templates/finding.md`, but the
consequence is **abandonment or
support cost** rather than incorrect output:

| Severity | Test |
|---|---|
| **blocker** | A user who wants to complete the core task cannot work out how, or is actively misled about what happened |
| **major** | The task is completable, but a meaningful fraction of users will give up — or it generates a support contact every single time |
| **minor** | Friction a motivated user absorbs without help |
| **polish** | Aesthetic, with no cost you can name |

Severity is **consequence × reach**, and the table above carries only consequence. So state reach on the
finding itself: every user / first run only / one role / one platform / operators under incident. "Every
install, ten thousand of them" moves a major in a way the tier cannot express.

**Severity inherits the worst consequence the defect causes** — see the rule under `finding.md`'s table,
which both rubrics share. An experience defect takes the severity of the action it leads the user into: a
reflexive confirmation on a cluster wipe is `critical`, because the consequence is the wipe.

For **operator-facing products** the consequence unit is time to diagnose and recover, not abandonment —
an operator does not give up, they page someone. A condition the product cannot show is a usability
blocker *and* an availability finding, because every minute the operator spends finding what the product
already knew is outage.

**Telling the user something false** is always also a product bug. A success panel for a swallowed
submission is a usability blocker and a lost customer at once; file it in both sections under one shared id.

## Error messages are a product surface

Audit them on purpose. Errors are where users are most stressed, least patient and most likely to leave,
and they are almost never reviewed because nobody reaches them on the happy path.

Reach them deliberately: every failure branch your scope's playbook names, plus the operator set — disk
full, port in use, peer unreachable, version mismatch between components, permission denied on the data
directory, clock skew, a dependency down at startup — and the mobile set — permission denied, offline, low
storage, process killed.

For each, five questions, one point each. The total is this scope's second number:

- Does it say **what happened**, in the user's vocabulary rather than the implementation's?
- Does it say **what to do next**?
- Does it **name the specific thing to change** — the variable, field, file or value — rather than
  gesturing at a category?
- Is it **reachable at all**, or swallowed, logged where the user cannot see, or replaced by a silent
  redirect?
- Does it avoid blaming the user for the product's own ambiguity?

For operator-facing products, **log lines and metric names are the error messages** — audit them the same
way. And group findings by root cause: one bad message style across three surfaces is one finding.

**Silent failure is the worst possible error message.** A swallowed exception is an experience finding as
much as a correctness one, and together they turn a transient blip into a permanently lost customer.

## Dangerous affordances

Most of this file is about users who did not know. This section is about users who knew exactly what they
wanted, and whom the product let do the wrong thing anyway. These have the worst consequences of any
experience finding, and nobody reaches them by happy-path testing, because the happy path is what they
look like.

For every destructive or irreversible action your scope can reach — delete, wipe, revoke, force,
overwrite, merge, purge, reset — ask:

- **Is it adjacent to a routine action**, in the menu, in argument order, on the screen? "Delete" one row
  below "Edit" is a slip waiting for a tired hand.
- **Is the confirmation reflexive or deliberate?** "Are you sure? OK / Cancel" is reflexive and will be
  clicked through. Typing the resource's name, or a two-step showing the consequence ("this removes 3
  nodes and 2.1 M keys"), is deliberate. A confirmation nobody reads is not a control.
- **Is there a dry-run, a preview, or an undo?** Reversibility is the strongest safety property a product
  can offer. Where it is absent the confirmation carries the whole load, and usually cannot.
- **Does it default to the dangerous setting?** `--force` on, cascade on, "apply to all" pre-ticked, or a
  destructive command reachable without authentication — which is a security finding *and* this one.
- **Is the state it destroys shown before it is destroyed?** An operator wiping "the cluster" should see
  *which* cluster, with its size, in the dialog.

Severity inherits the consequence of the action, so a slip into data loss is `critical`, and the finding
belongs to scope 10 and scope 12 under one id.

## Losing the user's work

Session expiry mid-form; navigation away from an unsaved edit; a draft lost to process death, rotation or
a dropped connection; a failed submit that empties the form; a wizard that cannot be resumed. Each is a
small data loss the product caused and could have prevented, and users experience it as a product's single
most infuriating behaviour.

Reach it deliberately — expire the session, kill the process, drop the network — at the moment of maximum
invested effort, and record what survived. Multi-device continuity is the same question across machines:
start on one, continue on another, and see what the second one knows.

## Waiting

Raw throughput is a documentation claim and belongs to scope 9. *Waiting* is an experience: what the
product does while something takes time. The thresholds are old and still right — around 100 ms feels
instant, around a second keeps the user's train of thought, past ten seconds they need to be told how long
and left free to do something else.

Measure the core task's waits against those three lines, and for each ask whether the product **shows that
it is working, how far it has got, and roughly when it will finish**. For operator products the long
operations — rebalance, migration, backfill, restore, rolling upgrade — are where this bites hardest: an
operation that will take forty minutes and shows nothing is indistinguishable from one that has hung, and
an operator who cannot tell will restart it. Jank and dropped frames on a low-end device are the mobile
form of the same finding, and there they are also a store-visibility gate.

## Interrupts

Notifications, alerts, emails, modal prompts, confirmation dialogs. Count them per core task and per day
of normal operation, and ask of each whether a user who ignored it would have been worse off.

For operators this is the alert set: a surface that pages on everything pages on nothing, and the real
incident arrives as the fortieth notification of the shift. For mobile it is notification-permission burn
— ask too early and too often and the user revokes it permanently. For a CRM it is the automation that
emails the customer three times for one event. The claim is "every notification carried information the
user needed and would have acted on"; test it by counting.

## Defaults are the experience most users have

Install with nothing configured and list every default a newcomer inherits: replication factor, auth,
bind address, fsync, retention, telemetry, log level. Flag each that is unsafe, slow, insecure or
surprising, and note which the quickstart silently relies on.

Nobody chose these, and most users will never change them. Where the docs recommend a different value
from the default, that is internal inconsistency — the product disagreeing with itself — and it is the
cheapest finding in this section.

## Localization beyond string parity

The evidence standard covers string parity and number formatting. This covers what gets translated last:
**error messages**, empty states, email templates, form validation messages, and the docs the product
links to. Then the mechanics — text expansion truncating buttons, right-to-left layout, locale-specific
input (phone, postcode, address order), date and number *entry* rather than display, and what happens when
the locale falls back.

A product translated on the happy path and English in every error has told its users which of them it was
built for.

## Accessibility

Not polish, and for a business tool in several jurisdictions not optional. The minimum pass, on the core
task rather than a representative page:

- Complete the core task **keyboard-only**.
- Complete it with a **screen reader**.
- Contrast against **WCAG AA**.
- Focus visibility and a sane focus order.
- An accessible name on every control, alt text on every meaningful image.
- Touch-target size, **text scaling to 200%**, and orientation changes on mobile.
- Reduced-motion respected.

For products without a screen the list is short and still real: no colour-only signalling in terminal
output, `NO_COLOR` and `TERM=dumb` respected, tabular output readable by a screen reader (not structured
by box-drawing alone), and progress indication that does not flood a reader with redraws. A device with
only an LED is covered by state legibility, not by WCAG.

Report accessibility as its own subsection in either case — or as one line, "N/A — no UI; terminal output
checked" — because the owner and the fix usually differ from everything else, and burying it in a general
list is how it gets deferred indefinitely.

## Per-domain index

The experience surface is not always a screen; for each product class the question is *who* the user is
and *what they are trying to find out*. One line each, with the detail in each domain file's §Experience:

| Product class | Where the experience lives |
|---|---|
| **Distributed / clustered** | Operator diagnosability. Time to diagnose an injected condition is this domain's time to first success. → `domains/distributed-database.md` |
| **Relational database** | Error-message precision on constraint and migration failures, and what a failed migration tells you about the state you are now in. → `domains/relational-database.md` |
| **Licensing / entitlement** | The acquisition funnel is the product; and whether every failure path reaches a human. → `domains/licensing-server.md` |
| **CRM** | Permission opacity — can a user tell what they are *not* allowed to see? → `domains/crm.md` |
| **ETL / pipelines** | Operator experience under partial failure: which records, and how to resume. → `domains/data-pipeline.md` |
| **Mobile** | Permissions, offline ambiguity, jank on a low-end device, and enforced platform policy. → `domains/mobile-app.md` |
| **Payments** | The ambiguous state after a timeout, which is what causes the second submit. → `domains/payments.md` |
| **Embedded / devices** | State legibility without a screen: the states the device can be in, against the signals it can emit. → `domains/embedded.md` |
| **API / developer platform** | Time to first successful call, and whether an error body names the field — the reader is in a different codebase. → `domains/api-platform.md` |
| **Identity / SSO** | The recovery path, and the real tension between a helpful message and a non-enumerable one. → `domains/identity-provider.md` |
| **Multi-tenant SaaS** | Role names versus what they grant, and what the quota boundary tells the admin. → `domains/multi-tenant-saas.md` |
| **Broker / streaming** | Whether a consumer's position is legible, and whether an offset reset can be previewed. → `domains/message-queue.md` |
| **Desktop** | First launch on a locked-down machine, OS trust prompts, and crash recovery. → `domains/desktop-app.md` |
| **AI / model-backed** | Whether the user can tell a confident wrong answer from a right one, and verify without leaving. → `domains/ai-product.md` |
| **AI tutor** | The transfer test: can the learner do the *next* problem unaided? The only experience measure that separates teaching from telling. → `domains/ai-tutor.md` |
| **Education platform** | Receipt-ability — can a learner prove what they submitted and when, to someone who will not take their word for it? → `domains/education-platform.md` |
| **File sync / storage** | What "synced" and "deleted" appear to mean, and whether a conflict is choosable. → `domains/file-sync-storage.md` |
| **Observability** | Zero versus no data — a rendering defect whose consequence is a wrong 3am decision. → `domains/observability-platform.md` |
| **Infra operator / IaC** | Diagnosis from the object and its events alone, with the source closed. → `domains/infra-operator.md` |
| **Billing / metering** | Predictability: the gap between the bill the product predicted and the bill that arrived. → `domains/billing-and-metering.md` |
| **Messaging delivery** | Time to answer "why did this one not arrive" — and the message as a real client renders it. → `domains/messaging-delivery.md` |
| **Scheduling / booking** | A time shown without its zone: the commonest and most expensive wording defect there is. → `domains/scheduling-and-booking.md` |
| **Backup / recovery** | The restorer is cold *by definition*, because the warm person is the one who is unavailable. → `domains/backup-and-recovery.md` |
| **Secrets / PKI** | Time-to-expiry visibility: every credential the system holds, against those whose lifetime a human can see. → `domains/secrets-and-pki.md` |
| **Workflow engine** | Side effects re-executed by the recovery action the console itself offers. → `domains/workflow-engine.md` |
| **Search / ranking** | The zero-result screen — the one new users see most — and whether anyone logs it. → `domains/search-and-ranking.md` |
| **E-commerce / marketplace** | The seller who cannot trace a payout to its orders, and then keeps their own spreadsheet. → `domains/ecommerce-marketplace.md` |

One cost to flag before testing a funnel: proving that **every failure path reaches a human** means
submitting real enquiries to a real sales or support team. Mark every test submission as a test in its
free-text field, tell the operator in advance, and put it in the cleanup ledger — a sales team chasing
your fake leads is a cost you created.

> Writing the report itself is also a design problem. That guidance now lives where the writer will see
> it: the preamble of `${CLAUDE_PLUGIN_ROOT}/skills/qa/assets/ranked-index.md`.
