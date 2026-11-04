# Fixtures

Two worked engagements, built by `python -I tests/fixtures/build.py --all` and committed with their
rendered dashboards. Both are driven **entirely through `hub.py`** — nothing writes to a hub directory
directly — so they are a worked example and an integration test at the same time: if a lifecycle in
`shared/hub/model.json` forbids something a real engagement needs, the fixture fails to build.

The engagements are fictional. No real hostnames, tenant ids, customer names or keys, which is the same
house rule the skills are held to and is checked by `shared/scripts/check_repo.py examples`.

## `existing/` — an existing product, the full arc

24 items, 86 events. A team adds self-serve trials to a licensing product that already has customers:
orient (profile reconstructed from the product) → current-state PRD → PRD delta → requirements, with a
conflict routed to the operator as a decision → stories whose criteria are oracles → design with its
states → ADR with a falsifier → story built → QA gate rows then cases → finding filed → DEV fixes and
hands back → QA verifies and closes → release → docs verified against the product → launch copy with its
claims checked → metric read and interpreted → cleanup verified by re-listing.

**Verdict: NOT GREEN**, on three conditions, and each one is the point of the fixture:

- a `NOT RUN` case guards a critical class — the contractual durability requirement `R-1` could not be
  run, and that absence denies the verdict rather than being invisible
- an operator acceptance requirement has no `PASS`
- an open risk

The operator then **ships anyway**, in their own words, recorded and attributed. Shipping does not make
the verdict green, and the fixture demonstrates that those are two different facts.

It also exercises two refusals on purpose: the DEV who claimed `FIXED` is refused when they try to verify
it, and the PO cannot accept a story whose linked case has not passed.

## `new/` — a greenfield product, the short arc

10 items, 30 events. An internal intake tool. Most interesting states are honestly "not measured yet":
the metric is `NOT YET` instrumented, there is no baseline to compare to, and the first reading would *be*
the baseline. QA finds a critical cross-team leak in the CSV export that the UI correctly hides — the
channel nobody put on the settings page.

**Verdict: NOT GREEN** on an open critical, a story claimed `DONE` but unaccepted, no acceptance
requirements recorded, and an open risk.

## Regenerating

```
python -I tests/fixtures/build.py --all
```

Deterministic apart from timestamps, so a regenerated fixture diffs only on `ts` fields and the
dashboard's generated-at line. `tests/test_fixtures.py` rebuilds both in a temp directory and asserts the
shape rather than the bytes.
