# Domain: workflow / durable execution engine

Long-running processes made of steps, timers, signals, retries and compensation — a product whose promise is
that a business process survives the operating-system process.

## Do the thing

> The workflow finished and the history looks right. Now kill the worker mid-step, deploy changed code while
> a workflow is in flight, and make one step time out and retry. Then count how many times the
> non-idempotent side effect actually happened. **`status: COMPLETED` is this domain's HTTP 200 — the
> product is what survives a crash and a deploy.**

## Scope map

| Family | In this domain | Agent | Notes |
|---|---|---|---|
| 1 Acquisition | docs | N/A | |
| 2 Primary product | the engine | own ×2 | split: execution and determinism vs timers, signals and queries |
| 3 Control plane | console, history inspection, terminate / retry / reset controls | own | |
| 4 Deployment | engine cluster, persistence backend, worker fleet | own | |
| 5 Entitlement | licensing | →4 | |
| 6 Secondary | SDK per language, activity workers | own | determinism rules are SDK-specific |
| 7 Telemetry | engine metrics | →8 | |
| 8 Security | who can terminate or signal a workflow; payloads at rest; task-queue isolation | own | a signal is a remote write to a running process |
| 9 Documentation | **the delivery and determinism semantics**, versioning guidance | own | |
| 10 State under fault | the core | own ×2 | split: worker and engine faults vs timers and long duration |
| 11 Upgrade | **deploying new code with workflows in flight** | own | this domain's hardest scope |
| 12 Experience | diagnosing a stuck workflow | lead | |

**Usual set: 2×2,3,4,6,8,9,10×2,11 own + 1 N/A, 5→4, 7→8, 12→lead = 10 agents.**

## Failure catalogue

Kill the worker mid-activity · kill it **between the activity completing and its result being recorded** ·
kill the engine · partition workers from the engine · deploy changed workflow code with workflows in flight ·
a step that times out and retries · a step that succeeds but whose result is lost · a non-idempotent side
effect retried · timers of 1 second, 1 hour and 30 days · a signal arriving before the workflow starts and
after it completes · a query during replay · a workflow exceeding the history limit · a compensation step
that itself fails · two workers claiming the same task · clock skew · a payload over the size limit.

## Defect classes to look for by name

**Non-deterministic workflow code accepted and then failing on replay** — the defining defect of the domain,
and the engine's job is to make it loud rather than tolerate it · **a duplicated side effect**, where
at-least-once activity execution met a non-idempotent activity: the docs warned the user and nothing
enforced it · **a lost activity result**, so a completed step runs a second time · a timer that fires early,
late, twice or never — especially across a restart and across a long duration · a signal silently dropped
when it arrives too early or too late · **compensation that does not compensate**, leaving a saga's partial
state behind · a workflow stuck with no visible reason and no way out · history growing until the workflow
cannot continue · a terminate that leaves resources allocated · versioning that strands in-flight workflows
with no migration path.

## Evidence and severity

The oracle is the **acknowledged-effect ledger**: every side effect you asked for, recorded *outside* the
engine, reconciled against the number of times it actually happened. The engine's own history is the
self-report — it tells you what the engine believes, which is precisely what is in question when a result is
lost. Run the harness self-test from `evidence-standard.md` first: inject one known duplicate and prove your
ledger catches it.

Determinism findings are proved by replaying against changed code, never by reasoning about the code. Record
engine version, SDK version and language, worker count, the full history as an artifact, and the fault with
its timestamp.

`evidence-standard.md` → *Stateful systems under fault* (the kill schedule), *Background and scheduled work*
(timers and retries are proved by side effect), *Migrations, upgrades and restores* (the in-flight deploy is
a migration with running state in it).

| Observation | Severity |
|---|---|
| A duplicated side effect with a real-world consequence — a payment, an email, a shipment | **critical** |
| A lost activity result | **critical** |
| Compensation leaving partial state | **critical** |
| Non-determinism accepted silently instead of failing loudly | **blocker** |
| A timer that never fires | **blocker** |
| In-flight workflows stranded by a deploy, with no migration path | **blocker** |
| A stuck workflow with no diagnosis and no escape | **blocker** |

## Experience

**Who the user is:** the engineer who owns a business process at 3am, holding a workflow id and one
question — what is it waiting for?

**Where it lives:** whether the history is readable by a human; whether a stuck workflow says *why*; whether
retry, terminate and reset are available, explained and reversible; and whether a payload can be inspected
without being exposed.

**First success is:** one workflow run end to end, surviving a worker restart, with its side effect
confirmed outside the engine.

**Do the thing, for experience:**

> Make a workflow stick. From the console and the history alone, name the step, the reason, and the command
> that resumes it **without re-running the side effect**.

**Defect classes:** a history that is a machine format and nothing else · `RUNNING` for days with no
indication of what it is waiting on · a retry control that re-runs a side effect with no warning, which is
the dangerous-affordance class · no dry-run for a reset · payloads either wholly invisible or wholly
exposed, with no setting in between.

**Evidence note:** time-to-diagnose from a workflow id with the source closed is the headline number, and
beside it a second count that is specific to this domain — **side effects re-executed by the recovery action
the console itself offers.** That is where a recovery becomes the incident.

## Domain gotchas

- Run against an engine and worker fleet you own. Killing workers is the core test and it is destructive to
  anyone else's workflows on the same cluster.
- **A 30-day timer cannot be tested in a sprint.** Use a controllable clock where the engine supports one,
  say plainly when you have tested only the short form, and run the long one as a background job.
- Determinism rules are SDK- and version-specific. Read which constructs are banned before calling a replay
  failure a product bug.
- The history-size limit turns a slow leak into a hard stop weeks later. Measure history growth per
  iteration and extrapolate — the defect appears long after your test ends.
- Payloads persist in histories, so test data in a shared cluster lives on in a place nobody thinks to purge.
  Ledger it.
