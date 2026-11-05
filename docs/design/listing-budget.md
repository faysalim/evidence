# The skill-listing budget — `PE-2`, measured

**Status:** the split I recommended is **not** the fix. A one-line setting is. Written 2026-11-05.

I recommended splitting this plugin in two, three times, on the assumption that its 15 descriptions
were what pushed the skill listing over budget and broke auto-triggering. I then measured the
listing instead of reasoning about it, and the recommendation does not survive the measurement.

---

## What the overflow actually is

Claude Code logs the overflow itself, which is a better oracle than any of my arithmetic:

```
[WARN] Skill listing over budget: 85 skills, 37942 chars > 30000 budget
       — descriptions will be truncated.
       Run /skills to disable some, or raise skillListingBudgetFraction in settings.
```

**Eighty-five skills, not fifteen.** Measured per plugin, from the installed copies on disk:

| Source | Skills | Listing chars | Share |
|---|---:|---:|---:|
| Built-ins + synced `anthropic-skills` | ~37 | ~16,800 | 44% |
| `vercel@claude-plugins-official` | 32 | 13,738 | 36% |
| **`evidence@evidence-market`** | **15** | **7,220** | **19%** |
| `andrej-karpathy-skills` | 1 | 219 | 1% |
| **Total** | **85** | **37,942** | |

So this plugin is a fifth of the overflow, and **removing it entirely does not fix anything**:
37,942 − 7,220 = 30,722 chars, still over the 30,000 budget. Cutting it to the four proven skills
would leave ~32,800. Deleting this plugin *and* all 32 vercel skills still leaves ~17,000 chars,
which is over a 200k-window model's 8,000 budget by more than twice.

**The overflow is a property of the machine, not of this plugin.** My recommendation would have
restructured the repo and changed nothing the user experiences.

## The fix, verified

The remedy named in the tool's own warning. Measured by running `claude -p` against temporary
settings files, reading the resulting budget from each run's debug log:

| `skillListingBudgetFraction` | Budget | Result |
|---|---:|---|
| `0.01` (default) | 30,000 | over by 7,942 — **7 of 15 descriptions dropped** |
| `0.011` | 33,000 | still over |
| `0.013` | 39,000 | **fits** |
| `0.02` | 60,000 | fits, 63% utilisation |
| `0.03` | 90,000 | fits |

The budget is linear in the fraction at 3,000,000 chars × fraction on this model, and scales with
the model's context window — which is why the same listing is over an 8,000 budget on a
200k-window model and a 30,000 one on the default.

**Recommended:** `0.02` in `~/.claude/settings.json`. It fits today's 85 skills with 22,000
characters of headroom, and costs a fraction of a percent more context.

```json
{ "skillListingBudgetFraction": 0.02 }
```

This restores descriptions for **all** 85 skills, not just this plugin's — so the eleven drafts
begin auto-triggering, and so does everything else that was being silently dropped.

## What I could not make work

`skillOverrides` should be the more surgical tool: the changelog records `off` (hidden from the
model and from `/`), `user-invocable-only` (hidden from the model) and `name-only` (collapses the
description). `name-only` on the eleven drafts is exactly the right shape — keep them invokable,
stop paying for their descriptions.

**It had no effect in four attempts.** Both `name-only` and `off`, with both plausible key shapes
(`analytics` and `evidence:analytics`), left the listing at 85 skills and 37,942 characters — byte
for byte unchanged. Either the key is something else, or the setting is not honoured through
`--settings`, which is plausible given the changelog describes it in a *managed*-settings context.

I did not modify the real `~/.claude/settings.json` to find out, because that is the user's
configuration and changing it to run an experiment is not mine to do. **So: mechanism documented,
my use of it unverified, not recommended on that basis.** If it does work from user settings it is
strictly better than raising the fraction, and worth one try by hand.

## Does the split still have a reason to exist?

A weaker one, and it is about strangers rather than about this machine.

**For:** 7,220 characters is 90% of a 200k-window model's entire 8,000-char budget, for one plugin.
A stranger on such a model who installs this gets their other skills' descriptions dropped, and the
`skillListingBudgetFraction` fix is something they have to be told about. A plugin that consumes
nine-tenths of a shared budget is antisocial regardless of whether a setting can paper over it.

**Against:** the split costs real structural damage. Marketplace installs **copy** the plugin
directory, so a plugin at `plugins/evidence-draft/` cannot read `../../shared/` — that was verified
earlier in the build. Every skill here reads `shared/principles.md`, `shared/vocabulary.md`,
`shared/hub/model.json` and `shared/scripts/hub.py`, so a second plugin needs its **own copy of
`shared/`**, kept byte-identical by a generator and a check. Two copies of the ten principles is
the exact failure `shared/principles.md` opens by naming: *"a rule written in fifteen places is
fifteen rules that drift."* It also splits one hub across two plugins that must agree on a model
file neither owns.

**Recommendation: do not split.** Instead:

1. Ship `skillListingBudgetFraction` guidance in the README, as the install step it is.
2. Keep every description under 700 characters — already enforced by `check_repo.py skills`.
3. Keep `tests/test_description_budget.py` failing against the 200k-model figure, as the standing
   conscience about distribution cost. It is the one number that makes this visible at all.
4. Revisit only if a per-skill override is confirmed to work, which would make the question moot.

## The lesson, which is the method's own

I gave the same recommendation three times without measuring the thing it rested on. The listing
cost was one grep of a debug log away the entire time, and the log was already on disk — written
during the council run that first reported `PE-2`.

"Seven of fifteen descriptions are dropped" was true. "Therefore this plugin is too big" was my
inference, and it was wrong: the correct reading was "this machine has 85 skills". The finding was
sound and the diagnosis was not, which is `shared/principles.md` §10 — report the disagreement,
do not reconcile it in your head — applied to my own conclusion.
