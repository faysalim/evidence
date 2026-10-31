# Domain: infrastructure operator / IaC provider

Software that manages other software: a Kubernetes operator, a Terraform provider, a deployment
controller. Its job is convergence, and its characteristic failure is confident divergence.

## Do the thing

> You applied the manifest and `status` says `Ready`. Now change the managed resource behind the
> operator's back, delete one of its children, and apply the same manifest twice. **`status: Ready` is
> this domain's HTTP 200 — the question is whether it reconciled, or merely stopped looking.**

## Scope map

| Family | In this domain | Agent | Notes |
|---|---|---|---|
| 1 Acquisition | docs, chart registry | N/A | |
| 2 Primary product | the reconcile loop | own ×2 | split: happy-path convergence vs drift, adoption, deletion |
| 3 Control plane | the CRD / resource schema and admission validation | own | the schema is the API, and the docs' main claim |
| 4 Deployment | install path, **the RBAC it requests**, namespacing | own | the RBAC is in the chart, not the code, which is why it is missed |
| 5 Entitlement | if licensed | →4 | |
| 6 Secondary | the managed system itself, per version | own | |
| 7 Telemetry | operator metrics and events | →8 | |
| 8 Security | privilege breadth, secret handling, escalation paths | own | |
| 9 Documentation | field reference, upgrade notes, what it will and will not do | own | |
| 10 State under fault | operator restart mid-operation, API unavailable, partial apply | own | |
| 11 Upgrade | **CRD version migration and operator upgrade with live resources** | own | |
| 12 Experience | diagnosability from the object alone | own | the product is consumed through `describe` |

**Usual set: 2×2,3,4,6,8,9,10,11,12 own + 1 N/A, 5→4, 7→8 = 10 agents.**

## Failure catalogue

Apply the same manifest twice · delete a child resource the operator created · mutate a managed resource
by hand · kill the operator mid-reconcile · make the control-plane API unavailable for sixty seconds · a
resource with an invalid field · a field changed in place that requires a replacement · two operator
replicas running at once · a namespace deleted with managed resources still in it · a CRD upgraded with
existing objects stored at the old version · a finalizer that cannot complete · a resource quota denying a
create halfway through a reconcile · a node drained during a managed rollout · uninstall with live
resources.

## Defect classes to look for by name

**A non-idempotent reconcile** — the second apply changes something, or the loop never settles · **status
reporting `Ready` while the managed resource is not**, which every downstream automation then trusts ·
drift left uncorrected — or corrected destructively, where the operator deletes user data to converge · a
finalizer that deadlocks deletion, leaving a namespace `Terminating` forever · a reconcile hot loop that
hammers the control plane and takes the cluster's API with it · leader election absent, so two replicas
fight over the same resource · RBAC far broader than the documentation implies, or cluster-admin requested
silently · secrets logged, or written into a non-secret object · a CRD schema change that invalidates
stored objects · an upgrade that **recreates** rather than updates a stateful managed resource.

## Evidence and severity

The oracle is the desired state you declared, compared against the actual state read **from the managed
system**, never from the operator's own status — that is the self-report rule, and in this domain the
status field is the most tempting false positive available.

Idempotency is proved by applying twice and diffing the managed system. Convergence is proved by mutating
out of band and timing the correction. Record per run: operator version, CRD version, the manifest
verbatim, the reconcile interval, and the RBAC the operator holds.

`evidence-standard.md` → *Stateful systems under fault*, *Migrations, upgrades and restores* (the CRD
migration is a schema migration with live objects), *Background and scheduled work* (the reconcile loop is
background work and must be proved by side effect).

| Observation | Severity |
|---|---|
| The operator deletes or recreates a stateful resource in order to converge | **critical** — data loss by design |
| `Ready` reported while the resource is not | **critical** — every downstream gate trusts it |
| Finalizer deadlock | **blocker** |
| Reconcile hot loop | **blocker** — cost, rate limits, and it degrades the whole cluster |
| RBAC broader than documented | **blocker** |
| Drift silently uncorrected | **major** |

## Experience

**Who the user is:** the platform engineer who will debug this at 3am with nothing but the CLI, and who
cannot read your source in the moment.

**Where it lives:** whether status conditions and events say **why** rather than only **what**; whether an
error names the offending field; whether a destructive change can be previewed; and whether uninstall is
honest about what it leaves behind.

**First success is:** one resource applied, the managed thing demonstrably working — verified from outside
the operator — and surviving an operator restart.

**Do the thing, for experience:**

> Break one field in the resource. Using only `describe` and the operator's own events and logs, name the
> field and the fix.

**Defect classes:** `status: Ready` with no condition detail · an error that exists only in the operator's
log and never on the object the user is looking at · no plan or dry-run before a destructive change · an
uninstall that orphans resources without listing them.

**Evidence note:** diagnosability *is* the product here, so time-to-diagnose — measured from the resource
and its events alone, with the source closed — is this domain's headline experience number, not a
secondary one.

## Domain gotchas

- Run against a cluster **you created** (kind, k3d, a disposable cloud cluster). This is the clearest case
  of the rule that destructive is defined by whose state it destroys: against a shared cluster the core
  scope cannot run at all, and saying so is the finding.
- A stuck finalizer can leave a namespace `Terminating` indefinitely. Know the escape route before you
  cause one.
- The operator's requested RBAC lives in the install chart, not the controller code. Read the chart.
- Reconcile intervals mean findings have latency. Record the interval, and never conclude "it did not
  converge" before one full interval has passed.
- Testing an upgrade requires the **previously released** operator version managing live resources. A
  fresh install of the new version proves nothing about the upgrade path.
- Two operator replicas is a legitimate test and can corrupt the managed system. Only in a cluster you own.
