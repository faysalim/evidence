# launch - status: exercised

Run against a real product by its author, with defects found and fixed. **Weaker than `proven`**:
`shared/principles.md` principle 7 says the author does not grade their own work, and this status
was graded by its author. What it buys is that the prose has met a real product at least once;
what it does not buy is an independent verdict.

**What is load-bearing and enforced:** the `launch` lifecycles in `shared/hub/model.json`,
checked by `hub.py` and covered by `shared/scripts/test_hub.py`. Those transitions and
their required fields are not draft at any status.

**What this status does not cover:** the heuristics, the checkpoint lists and the
examples. Open questions are at the end of `SKILL.md` and are deliberate, not oversights.
