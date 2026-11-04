# Eval suite

Trigger evals, run with the built-in harness:

```
claude plugin eval product-suite --eval-dir evals
```

**This directory ships a representative subset, not the whole corpus.** The full corpus —
15 skills x 5 hits x 5 near-misses — lives as data in `tests/triggers/corpus.json`, and
`python -I tests/triggers/check_overlap.py --emit-evals` writes all 150 cases here. It is not
committed in full because each case is a full Claude child running on the operator's own
credential and rate limit, and 150 of those is a large spend to incur on someone's behalf.

The six committed cases are chosen to cover the boundaries the corpus says are most confusable:
`qa` vs `dev` (fixing), `qa` vs `release` (the ship decision), `qa` vs `backlog` (acceptance
criteria), `hub` vs `delivery` (a direct status query), plus one case that must trigger
**nothing** — ordinary debugging, which the `qa` description explicitly excludes. That last one
matters most: a suite of 15 always-on skills that claims unrelated work is worse than one that
under-triggers.

The cheap half of trigger testing runs in a second and needs no agent at all:
`python -I tests/triggers/check_overlap.py` measures description overlap and asserts that every
pair the corpus names as confusable is guarded by a "Not for" line. It found eight unguarded
pairs on first run.
