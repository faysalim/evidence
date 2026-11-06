# Domain: compiler / obfuscator / SDK tooling (DRAFT, authored from the Nebula.NET engagement)

A tool that **transforms a program and must preserve its meaning** — obfuscator, minifier, AOT/IL rewriter,
bytecode instrumenter, codegen. Distributed as a CLI + build-system integration (MSBuild/Gradle/webpack) +
sometimes a GUI; licensed by edition. Its defining property: the output is not content, it is *the user's
own program altered*, and the only thing that makes the alteration acceptable is that behaviour is
unchanged. Not in the plugin's 27 files; this draft is for the next engagement in the field.

## Do the thing

> Obfuscate a REAL assembly, **RUN it, and diff its output against the un-obfuscated run captured first.**
> Then prove the transform actually applied (decompile / grep the bytes). **"It wrote an output file,
> exit 0, verifyOutput:true passed" is this domain's HTTP 200** — and it lies: in this engagement
> `encryptMethods` reported success on every one of those signals while shipping a binary that threw at
> first call (F-101). A transform tool that self-certifies is grading its own homework (principle 3).

## The semantic-preservation oracle (domain-specific)

The oracle is **the un-obfuscated program's own observable behaviour, captured BEFORE the transform** —
stdout, return codes, files written, a test suite's pass set. It predates the run and lives outside the
tool, so it is a real oracle. Build a matrix of small REAL programs that each exercise one language/runtime
construct the transform is likely to break, run each before and after, and diff. One variable per run:
toggling a single pass (e.g. `encryptMethods` on/off on the identical fixture) is what localises a defect
to a pass, as it did for F-101.

## Scope map (families → this domain → agent)

| Family | Here | Agent | Notes |
|---|---|---|---|
| 1 Acquisition | download, NuGet/registry package, edition claims | own | version self-report vs package is a real trap |
| 2 Primary product | the transform engine | own ×2 | split: CLI/engine vs build-integration (MSBuild) — different users |
| 4 Deployment | installer + the `dotnet tool`/package install; the two coexisting on PATH | own | F-005: two install methods, undefined PATH precedence, silent version divergence |
| 5 Entitlement | Free vs paid caps, license activation, offline license | own | caps gate *which transforms run* — test the cap, not just the banner |
| 8 Security | the tool's own signing + what it injects into the user's binary (a decrypt runtime is attack surface) | own | |
| 9 Documentation | CLI reference, config schema, every env var, exit codes | own | enumerate from code; the kill-switch env var was undocumented (F-203) |
| 10 State under fault | malformed input, unreadable assembly, partial output | →2 | |
| 11 Upgrade | config-schema compatibility across versions; re-transform of already-transformed input | own | |
| 12 Experience | first protected build; does the summary tell the truth | own | |

Determinism and output-reproducibility cut across 2/11 and have no family — call it out explicitly (F-102).

## Fault / failure catalogue (feed these to the transform, each its own run)

Generics and constructed generic types (`List<int>`, `Dictionary<,>`) · async/await state machines ·
iterators (`yield`) · lambdas/closures, delegates, events · reflection (`Type.GetType`, `nameof`,
serialization round-trip) · `preservePublicApi`/keep-rules on a library consumed by an un-transformed
caller · multi-assembly input with cross-references · embedded/satellite resources and localization ·
the maximum transform level (aggressive/all passes at once) · re-transforming an already-transformed
artifact · the same input twice (determinism) · an input the tool cannot parse · the Free-edition caps vs
the paid behaviour on the identical config.

## Defect classes to look for by name

**Semantic break under transformation** — the output compiles/loads/"verifies" but throws or computes a
different result at runtime (F-101 is the archetype: injected-runtime IL token fixup drops the declaring
type for members on a generic instantiation). · **Silent success on a broken output** — exit 0 + the
tool's own `verifyOutput` passing on a binary that crashes; the verify step checks structure, not a smoke
run. · **Non-deterministic output with no stated contract** — same input+config → different bytes, breaking
reproducible builds, hash-keyed caches and rebuild-compare supply-chain checks (F-102). · **Version
self-report drift** — the running binary, the package, and the output's embedded tool-version disagree
(watch for a stale install shadowing the new one on PATH — F-005). · **Cap mismatch** — the edition banner
claims a limit the engine doesn't actually enforce (or vice-versa). · **Keep-rule leak** — `preservePublicApi`
renames something public, or keeps something it shouldn't. · **Undocumented surface** — config keys, env
vars (especially an air-gapped/offline kill-switch) and commands the docs never mention (F-203, F-202, F-204).

## Evidence and severity

Capture per run: OS/arch, runtime version, tool version (self-reported AND package), edition/license state,
the exact config, and the before/after stdout. `evidence-standard.md` → *decompiler/binary* (prove the
transform applied by inspecting bytes: the literal is gone, the name changed) and *CLI* (exit codes,
stderr). Prove a negative through its positive: "strings encrypted" = grep the plaintext in the output and
show **zero** hits while runtime output is unchanged.

| Observation | Severity |
|---|---|
| Transform ships a binary that crashes / changes behaviour at runtime | **critical** — the tool's one job is semantic preservation |
| Silent success (exit 0 / verify passes) on a broken output | raises any correctness defect to **critical** — CI can't see it |
| Transform silently omitted but reported as applied | **blocker** |
| Non-deterministic output, no documented contract | **major** (minor if a determinism contract exists and is met) |
| Undocumented security-relevant surface (offline kill-switch) | **major** |
| Edition cap mis-stated vs enforced | **major** |

## Experience

**Who the user is:** a developer wiring the tool into a build/CI once (cares that the summary is honest and
exit codes branch correctly), and whoever later debugs a crash that only happens in the protected build.
**Where it lives:** first protected build from the quickstart; the run summary (does it tell the truth about
what it renamed/encrypted/skipped); and the moment a protected binary throws and the user must map the
mangled stack trace back (the symbol map + a `deobfuscate` round-trip is first success for *that* user, and
it passed here). **First success is:** a real assembly protected, run, behaving identically, and verified
obfuscated by decompiling. **Defect classes:** a success summary that hides a skipped/failed method; a
crash in the protected build with no pointer to the symbol map; CLI flags that contradict the GUI/docs.

## Domain gotchas

- The engine runs the same regardless of edition once a license is present — so a licensed test box
  **cannot observe the Free-edition path or caps** (F-207). Keep an unlicensed profile.
- Never build the tool's own signed/obfuscated distributable under a **trial** license — it can bake a
  self-destruct into what you ship. Test the pre-built release artifact.
- Two install methods (installer + language-package) put the same command on PATH; which one runs is
  PATH-order, and they drift in version silently. Resolve `which -a` before trusting `--version` (this trap
  cost the lead two false findings this engagement).
- `verifyOutput`/self-check is the tool certifying itself — never let it stand in for an external run.
- Determinism is a *contract*, present or absent; if absent, file the missing contract AND grade the
  behaviour at the consequence its absence earns (principle 10).
