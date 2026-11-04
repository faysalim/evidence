# Gotchas

Traps that each cost a cycle in a real engagement. Skim before heavy local work — builds, scripted edits,
file rewrites. Most are not QA-specific; they are the reasons a measurement silently lies to you, which is
the same thing as a bad finding, a bad fix or a bad benchmark.

Testing-specific traps — browser automation, cloud teardown, stateful and clustered testing — live in
`skills/qa/references/gotchas-testing.md`.

## Contents

- [Editing source files at scale](#editing-source-files-at-scale)
- [Builds that pass while shipping a broken artifact](#builds-that-pass-while-shipping-a-broken-artifact)
- [Build and toolchain traps](#build-and-toolchain-traps)
- [Locale and formatting](#locale-and-formatting)
- [Repositories and branches](#repositories-and-branches)
- [Reasoning traps](#reasoning-traps)

## Editing source files at scale

**Reading a file in Python text mode normalises CRLF to `\n`.** Every "is this file CRLF?" test built on a
text-mode read is therefore silently false. This rewrote an entire 3,863-line file as LF in one engagement,
and adding `utf-8-sig` on the write put a BOM on it as well — a diff that buried the actual two-line change
completely.

Use `scripts/safe_edit.py`, which reads **bytes**, detects the newline and BOM from the bytes, requires
every anchor to match **exactly once**, and writes nothing at all if any anchor fails. The abort-on-mismatch
behaviour is the valuable half: an anchor that matches zero times usually means a character you assumed is
a hyphen is actually an em dash (`—`), and failing loudly beats a partial edit.

**Escape sequences flatten when a script writes a script.** A `'\n'` inside a JS string, written through
another language's string literal, can arrive in the file as a real newline — producing an unterminated
string literal. Prefer a construct that needs no escape (a template literal, a raw string) over getting
the escaping depth right.

**Writing generated files into a project directory can make the build compile them.** SDK-style projects
glob `**/*.cs`; a probe that wrote decompiled output beside the source produced duplicate-definition
errors that looked like a product bug. Write probe output outside the project tree.

## Builds that pass while shipping a broken artifact

**A green build proves the toolchain was happy, nothing more.** A real example, worth internalising: an
escape flattened into a real newline inside an inline `<script>`, leaving an unterminated string literal.
The build was green, the page rendered normally, and the entire script failed to parse — so the form on it
did nothing whatsoever. Only opening the page and reading the console caught it.

Therefore: build, then **run the artifact and read the console**. For a site, that means serving `dist/`
and driving it. For a binary, launching it. This is the single highest-yield habit in the whole skill.

**Tests passing is not evidence either, unless you watched them fail first.** A test written after the fix
that passes immediately may assert nothing at all. Run every new test against the unfixed code and record
that it failed.

## Build and toolchain traps

- **`npx <tool>` in a directory without `node_modules`** fetches a *different* version globally, which
  then fails on config it cannot resolve (`Tsconfig not found ...`). Run the install first.
- **MSBuild on an I/O-starved host** appears to hang. `-m:1 -p:UseSharedCompilation=false -nodeReuse:false`
  makes it finish. If `tasklist` or a process listing is also timing out, the host is the problem, not the
  build.
- **`dotnet run -c Release <msbuild flags> -- <args>`** passes the MSBuild flags through to the program,
  which then fails with a baffling `FileNotFoundException: '-m:1'`. Build, then run the produced
  executable directly.
- **A stale artifact explains more "impossible" results than anything else.** If a newly added symbol is
  missing, check the artifact's timestamp before forming any theory.
- **Shell heredocs break on large content** with unbalanced-quote errors that have nothing to do with the
  content's meaning. Use a file-writing tool for anything substantial rather than fighting the quoting.
- **MSYS/Git-Bash `/tmp` is invisible to native Windows interpreters.** A path that works in the shell
  gives `FileNotFoundError` to native Python. Use a real Windows path.

## Locale and formatting

**Verify before "fixing" what looks wrong.** `$1490/año` with no thousands separator looks like a bug and
is correct `es-ES`: CLDR sets `minimumGroupingDigits=2` for Spanish, so four-digit numbers are not grouped
(`1490`, but `15.000`). Check the locale's actual rules — fixing this would have introduced a defect while
closing a non-finding.

Related: a locale redirect built on a path-only map silently drops the query string and hash, taking
`?product=` and every `utm_*` parameter with it. Always test redirects with parameters attached.

## Repositories and branches

- **The repo's default branch may not be the development line.** One `master` was a month stale while
  `release/2.5.0` was live. Establish the deploying branch from the hosting config.
- **Published tags lie.** A `2.5.0` image predated its own `release/2.5.0` tip. Grep the artifact for a
  string you know changed.
- **A checked-in generated manifest** (parity matrix, lockfile, snapshot) may already be out of date on the
  base branch, so a gate fails for reasons unrelated to your change. Check whether it was already red
  before blaming yourself — and prove it by comparing the manifest's last-modified commit against the
  commit that should have updated it.
- **Grep counts mislead on substrings.** A count of 1 for `auth/me` was matching `auth/methods`. Anchor
  the pattern.

## Reasoning traps

- **"It must be upstream."** Three decompiler defects were written off as upstream and unfixable; one was a
  single wrong line in the product's own code, and the product had been rendering all modern language
  constructs in lowered form as a result. Prove upstream attribution by running upstream's own defaults,
  and ideally two upstream versions, before claiming it.
- **A downgrade-only API looks like an upgrade.** Code constructed settings at the oldest version and then
  called a `SetVersion(Latest)` method that only ever turns features *off*. It read as an upgrade and was a
  no-op, leaving 70 of 111 feature flags false. Read what the method actually does, not what its name
  implies.
- **Check the assertion targets what you think it does.** A test asserting a construct is reconstructed is
  worthless if the chosen fixture type never contained that construct. Scan for a real candidate first.
- **Test the branch you are on.** Measuring a behaviour on the wrong branch produces a confident, wrong
  result. Confirm the working directory and the checked-out ref before measuring.
- **Two near-identical identifiers usually exist on purpose.** Before reporting one as a typo, read the
  commit that introduced it — two similarly named environment variables turned out to be a deliberate
  split between two consumers, which changed the finding from "typo in code" to "docs name the wrong
  consumer's variable", a different fix with a different owner.
