#!/usr/bin/env python3
"""Repository self-checks. The repo should be unable to lie about itself.

    python -I shared/scripts/check_repo.py            # all checks
    python -I shared/scripts/check_repo.py refs lint  # named checks only
    python -I shared/scripts/check_repo.py --list

This replaces the old "a PR must update these four places" rule in CONTRIBUTING. A rule that
depends on someone remembering four places is a rule that fails silently; a check fails loudly.

Checks:
  refs      every `${CLAUDE_PLUGIN_ROOT}/...` and `${CLAUDE_SKILL_DIR}/...` path resolves, AS THE
            INSTALLED PLUGIN SEES IT, and no path escapes a skill or the plugin root
  lint      the variables rule: no $CLAUDE_PLUGIN_ROOT inside a shell block (it is not in the
            environment of model-run Bash), and no bare /skill-name invocation in our own docs
  registry  every domain file is registered in the domains README and the experience index, and
            every count stated in prose matches the actual file listing
  headings  every domain file carries the seven-heading contract
  width     no prose line over 110 columns (tables, code blocks and link lists exempt)
  examples  no real hostname, absolute path, tenant id or key in an example
  skills    every skill has frontmatter with a description, under the character ceiling, with a
            "Not for" line, and a SKILL.md no longer than the line budget

Exit 0 when every selected check passes, 1 otherwise.
"""

from __future__ import annotations

import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SKILL_LINE_BUDGET = 300
DESC_CEILING = 700          # characters; see docs/design/plugin.md decision D-8
DOMAIN_HEADINGS = 7         # plus one sanctioned extra section in two files
PROSE_WIDTH = 110

FAILURES = []
PASSES = []


def fail(check, msg):
    FAILURES.append("%s: %s" % (check, msg))


def ok(check, msg):
    PASSES.append("%s: %s" % (check, msg))


def md_files(*subdirs):
    out = []
    for sub in subdirs or [""]:
        base = os.path.join(ROOT, sub) if sub else ROOT
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames
                           if d not in (".git", "__pycache__", "node_modules")]
            for name in filenames:
                if name.endswith(".md"):
                    out.append(os.path.join(dirpath, name))
    return sorted(set(out))


def read(path):
    with io.open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def rel(path):
    return os.path.relpath(path, ROOT).replace("\\", "/")


def strip_code_blocks(text):
    """Return (prose_lines, shell_blocks) with 1-based line numbers."""
    prose, blocks = [], []
    fence = None
    current = []
    for n, line in enumerate(text.split("\n"), 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            if fence is None:
                fence = stripped[3:].strip().lower()
                current = []
            else:
                blocks.append((fence, current))
                fence, current = None, []
            continue
        if fence is None:
            prose.append((n, line))
        else:
            current.append((n, line))
    if fence is not None:
        blocks.append((fence, current))
    return prose, blocks


# ---------------------------------------------------------------------------

def check_refs():
    """Resolve every plugin-root and skill-dir path the way an installed plugin would."""
    pattern = re.compile(r'\$\{(CLAUDE_PLUGIN_ROOT|CLAUDE_SKILL_DIR)\}/([A-Za-z0-9_./-]+)')
    bad = 0
    seen = 0
    for path in md_files():
        if rel(path).startswith("docs/"):
            continue
        text = read(path)
        skill_dir = None
        m = re.match(r"skills/([^/]+)/", rel(path))
        if m:
            skill_dir = os.path.join(ROOT, "skills", m.group(1))
        for var, target in pattern.findall(text):
            seen += 1
            target = target.rstrip(".,;:)`")
            if var == "CLAUDE_PLUGIN_ROOT":
                resolved = os.path.join(ROOT, target)
            else:
                if skill_dir is None:
                    fail("refs", "%s uses ${CLAUDE_SKILL_DIR} but is not inside a skill" % rel(path))
                    bad += 1
                    continue
                resolved = os.path.join(skill_dir, target)
            if not (os.path.isfile(resolved) or os.path.isdir(resolved)):
                fail("refs", "%s -> ${%s}/%s does not exist" % (rel(path), var, target))
                bad += 1
        if rel(path).startswith("docs/"):
            continue
        # a path that escapes the plugin root can never work on a copied install
        for esc in re.findall(r'`((?:\.\./)+[A-Za-z0-9_./-]+)`', text):
            fail("refs", "%s references %r, which escapes its directory. On a marketplace "
                         "install the plugin is copied and anything above the root is absent."
                 % (rel(path), esc))
            bad += 1
        # backticked repo-relative paths that are not variable-prefixed are ambiguous once installed
        for cand in re.findall(r'`((?:shared|skills|tests)/[A-Za-z0-9_./-]+\.(?:md|py|json))`', text):
            if not os.path.exists(os.path.join(ROOT, cand)):
                fail("refs", "%s references `%s`, which does not exist" % (rel(path), cand))
                bad += 1
        # A bare pre-restructure path. These were invisible to this check before, so 31 of them
        # survived the move -- 9 naming files that no longer exist under any name -- while the
        # check reported 7/7 green. The directories are gone, so none of them resolves.
        for cand in re.findall(r'`((?:references|assets|scripts)/[A-Za-z0-9_./-]+)`', text):
            fail("refs", "%s references `%s`, a pre-restructure path. Those directories no "
                         "longer exist; use ${CLAUDE_PLUGIN_ROOT}/... or ${CLAUDE_SKILL_DIR}/..."
                 % (rel(path), cand))
            bad += 1
    if not bad:
        ok("refs", "%d variable path(s) resolve; no escapes" % seen)


def check_lint():
    """The variables rule, and namespaced invocation only."""
    bad = 0
    # The unbraced form resolves NOWHERE: substitution happens only on the ${...} form in
    # skill text, and none of these names is in the environment of a model-run command
    # (verified by probe: printenv CLAUDE_PLUGIN_ROOT after invoking a skill exits 1 with no
    # output). So it is a defect in prose, in a shell block, and in a powershell or python
    # block alike. The earlier version looked only inside bash-family fences, so it could not
    # see the other three.
    unbraced = re.compile(
        r"[$](CLAUDE_PLUGIN_ROOT|CLAUDE_SKILL_DIR|CLAUDE_PLUGIN_DATA|CLAUDE_PROJECT_DIR)")
    for path in md_files():
        # docs/ discusses the rules, so it quotes the forbidden forms on purpose.
        if rel(path).startswith("docs/"):
            continue
        for n, line in enumerate(read(path).splitlines(), 1):
            for m in unbraced.finditer(line):
                fail("lint", "%s:%d writes the unbraced $%s. Only the ${...} form is"
                             " substituted into skill text, and the name is not in the"
                             " environment of a model-run command, so this resolves nowhere."
                     % (rel(path), n, m.group(1)))
                bad += 1
    # bare slash-command form in our own docs
    skill_names = sorted(os.listdir(os.path.join(ROOT, "skills"))) \
        if os.path.isdir(os.path.join(ROOT, "skills")) else []
    for path in md_files():
        if rel(path).startswith("docs/"):
            continue
        text = read(path)
        for name in skill_names:
            for m in re.finditer(r'(?<![:\w/>])/%s(?![\w-])' % re.escape(name), text):
                line = text[:m.start()].count("\n") + 1
                fail("lint", "%s:%d writes the bare `/%s` form. Bare names resolve by an origin "
                             "order we do not control; document /evidence:%s."
                     % (rel(path), line, name, name))
                bad += 1
    if not bad:
        ok("lint", "no bare $CLAUDE_* in shell blocks; no bare slash-command forms")


def check_registry():
    """Every domain file registered everywhere, and every stated count true."""
    dom_dir = os.path.join(ROOT, "shared", "domains")
    if not os.path.isdir(dom_dir):
        fail("registry", "shared/domains is missing")
        return
    files = sorted(f for f in os.listdir(dom_dir) if f.endswith(".md") and f != "README.md")
    n = len(files)
    bad = 0

    readme = read(os.path.join(dom_dir, "README.md"))
    for f in files:
        if "`%s`" % f not in readme:
            fail("registry", "%s is not listed in shared/domains/README.md" % f)
            bad += 1

    exp_path = os.path.join(ROOT, "shared", "references", "experience.md")
    if os.path.isfile(exp_path):
        exp = read(exp_path)
        for f in files:
            stem = f[:-3]
            if stem not in exp:
                fail("registry", "%s is not in the per-domain index of experience.md" % f)
                bad += 1

    # Only count claims that are ABOUT domain files. A bare number-word elsewhere is prose:
    # "seventeen fault-catalogue entries" is not a claim about how many domain files exist, and
    # a check that cannot tell the difference gets ignored, which is worse than no check.
    words = {"seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
             "twenty-five": 25, "twenty-six": 26, "twenty-seven": 27, "twenty-eight": 28,
             "twenty-nine": 29, "thirty": 30}
    subject = r'(?:domain file|product class|domain)'
    for path in md_files():
        if rel(path).startswith("docs/"):
            continue
        text = read(path).lower()
        for m in re.finditer(r'\b([a-z-]+|\d+)\s+%s' % subject, text):
            token = m.group(1)
            claimed = words.get(token, int(token) if token.isdigit() else None)
            if claimed is None or claimed == n:
                continue
            line = text[:m.start()].count("\n") + 1
            fail("registry", "%s:%d claims %s domain files but there are %d"
                 % (rel(path), line, token, n))
            bad += 1
    if not bad:
        ok("registry", "%d domain files, all registered, all counts agree" % n)


def check_headings():
    dom_dir = os.path.join(ROOT, "shared", "domains")
    bad = 0
    for f in sorted(os.listdir(dom_dir)):
        if not f.endswith(".md") or f == "README.md":
            continue
        count = len(re.findall(r'^## ', read(os.path.join(dom_dir, f)), re.M))
        if count not in (DOMAIN_HEADINGS, DOMAIN_HEADINGS + 1):
            fail("headings", "%s has %d `## ` headings; the contract is %d (or %d with one "
                             "sanctioned extra section)"
                 % (f, count, DOMAIN_HEADINGS, DOMAIN_HEADINGS + 1))
            bad += 1
    if not bad:
        ok("headings", "every domain file satisfies the seven-heading contract")


def check_width():
    bad = 0
    for path in md_files():
        # evals/ holds prompts and grader criteria, not prose. A criterion is one sentence read
        # by a judge model; hard-wrapping it is a change to the text being graded, so the column
        # rule does not apply there.
        if rel(path).startswith("evals/"):
            continue
        text = read(path)
        # YAML frontmatter cannot wrap: a folded description changes meaning.
        fm_end = 0
        if text.startswith("---\n"):
            m = re.match(r"---\n.*?\n---\n", text, re.S)
            if m:
                fm_end = text[:m.end()].count("\n")
        prose, _ = strip_code_blocks(text)
        for n, line in prose:
            if n <= fm_end:
                continue
            s = line.strip()
            if s.startswith("|") or s.startswith("- [") or s.startswith("["):
                continue
            if len(line) > PROSE_WIDTH:
                fail("width", "%s:%d is %d columns (limit %d)"
                     % (rel(path), n, len(line), PROSE_WIDTH))
                bad += 1
    if not bad:
        ok("width", "no prose line over %d columns" % PROSE_WIDTH)


def check_examples():
    """No real hostname, absolute path, tenant id or key in an example."""
    patterns = [
        (re.compile(r'\b[A-Za-z]:[\\/](?:Users|Personal|home)\b'), "a real absolute path"),
        (re.compile(r'\b(?:[a-z0-9-]+\.)+(?:com|io|net|dev|org|ai)\b'), "a real-looking hostname"),
        # The separator is load-bearing. Without it, `(?:sk|pk)` matched any word beginning
        # "sk" or "pk" followed by 12 characters, and flagged `skillListingBudgetFraction` --
        # a settings key NAME, not a secret -- as a key. Real tokens of these families all
        # carry a separator: sk-..., sk_..., pk_live_..., ghp_... . The tail admits further
        # separators, because pk_live_xxx would otherwise slip past the 12-character run.
        (re.compile(r'\b(?:sk|pk|ghp|gho)[-_][-_A-Za-z0-9]{12,}'), "something shaped like a key"),
        # AWS ids are the exception: no separator, but fixed-case and fixed-length.
        (re.compile(r'\bAKIA[A-Z0-9]{12,}'), "something shaped like an AWS key id"),
    ]
    allow_host = re.compile(
        r'^(example\.(com|org|net)|example\.test|localhost|code\.claude\.com|claude\.com|'
        r'apache\.org|github\.com|json-schema\.org|schema\.org|anthropic\.com|'
        r'opensource\.org|semver\.org)$')
    bad = 0
    for path in md_files():
        if rel(path).startswith("docs/"):
            continue
        for n, line in enumerate(read(path).split("\n"), 1):
            for pat, what in patterns:
                for m in pat.finditer(line):
                    if what == "a real-looking hostname" and allow_host.match(m.group(0)):
                        continue
                    fail("examples", "%s:%d contains %s (%r). House rule: no real hostnames, "
                                     "paths, tenant ids or keys in examples."
                         % (rel(path), n, what, m.group(0)[:40]))
                    bad += 1
    if not bad:
        ok("examples", "no real hostnames, paths or keys in examples")


def check_skills():
    sk_dir = os.path.join(ROOT, "skills")
    if not os.path.isdir(sk_dir):
        fail("skills", "skills/ is missing")
        return
    bad = 0
    found = 0
    for name in sorted(os.listdir(sk_dir)):
        path = os.path.join(sk_dir, name, "SKILL.md")
        if not os.path.isfile(path):
            fail("skills", "skills/%s has no SKILL.md" % name)
            bad += 1
            continue
        found += 1
        text = read(path)
        lines = text.count("\n") + 1
        if lines > SKILL_LINE_BUDGET:
            fail("skills", "skills/%s/SKILL.md is %d lines (budget %d). It loads on every "
                           "trigger, so length there costs every user."
                 % (name, lines, SKILL_LINE_BUDGET))
            bad += 1
        m = re.match(r"---\n(.*?)\n---\n", text, re.S)
        if not m:
            fail("skills", "skills/%s/SKILL.md has no YAML frontmatter" % name)
            bad += 1
            continue
        fm = m.group(1)
        dm = re.search(r'(?<=^description: ).*?(?=\n[a-z_-]+:|\Z)', fm, re.S | re.M)
        if not dm:
            fail("skills", "skills/%s has no description, which is the whole trigger" % name)
            bad += 1
            continue
        desc = dm.group(0).strip()
        if len(desc) > DESC_CEILING:
            fail("skills", "skills/%s description is %d chars (ceiling %d)"
                 % (name, len(desc), DESC_CEILING))
            bad += 1
        if "not for" not in desc.lower():
            fail("skills", "skills/%s description has no \"Not for...\" line. That line is what "
                           "separates it from its neighbours." % name)
            bad += 1
    if not bad:
        ok("skills", "%d skill(s) within the line and description budgets" % found)


# The three honest levels. A skill may not claim more than it has earned.
#   proven    -- carries a real engagement's provenance, where its absence cost something
#   exercised -- run end to end against a real product by its author, defects found and fixed.
#                NOT an independent engagement: principle 7 means the author does not grade
#                their own work, so this is explicitly weaker than proven.
#   draft     -- written from first principles, never run. CONTRIBUTING.md warns against this.
STATUSES = ("proven", "exercised", "draft")


def check_coverage():
    """Every model role has a skill, every skill declares a real role and an honest status.

    This exists because "one skill per deliverable, every role covered" was the plugin's
    headline claim and NOTHING could verify it: no skill declared its role, so the claim was
    prose. That is the same defect as the three false "Enforced:" lines the review found in
    principles.md -- a claim with no mechanism behind it -- in the README instead.
    """
    model_path = os.path.join(ROOT, "shared", "hub", "model.json")
    skills_dir = os.path.join(ROOT, "skills")
    if not os.path.isfile(model_path) or not os.path.isdir(skills_dir):
        fail("coverage", "shared/hub/model.json or skills/ is missing")
        return
    model = json.loads(read(model_path))
    roles = set(model.get("roles", []))
    bad = 0
    declared, statuses = {}, {}

    for name in sorted(os.listdir(skills_dir)):
        path = os.path.join(skills_dir, name, "SKILL.md")
        if not os.path.isfile(path):
            continue
        # Frontmatter is the block between the FIRST two `---` lines, and nothing else. The
        # earlier `split("\n---", 2)` then `head[1] if len>2 else head[0]` read the BODY as
        # frontmatter for any skill containing a `---` rule -- which fails closed on a real
        # skill, and worse, would PASS a skill whose body happened to contain a `roles:` line
        # while its actual frontmatter declared nothing.
        text = read(path)
        fm = ""
        if text.startswith("---\n"):
            end = text.find("\n---", 3)
            fm = text[4:end] if end != -1 else ""
        mr = re.search(r"^roles:\s*(.+)$", fm, re.M)
        mr = re.search(r"^roles:\s*(.+)$", fm, re.M)
        ms = re.search(r"^status:\s*(\S+)\s*$", fm, re.M)
        if not mr:
            fail("coverage", "%s declares no `roles:` -- then nothing can check that the "
                             "suite covers every role" % name)
            bad += 1
        else:
            rr = [x.strip() for x in mr.group(1).split(",") if x.strip()]
            declared[name] = rr
            for r in rr:
                if r not in roles:
                    fail("coverage", "%s declares role %r, which is not in model.json" % (name, r))
                    bad += 1
        if not ms:
            fail("coverage", "%s declares no `status:` -- a reader then infers 'proven' from "
                             "the absence of a warning" % name)
            bad += 1
        elif ms.group(1) not in STATUSES:
            fail("coverage", "%s has status %r; allowed: %s"
                 % (name, ms.group(1), ", ".join(STATUSES)))
            bad += 1
        else:
            statuses[name] = ms.group(1)

    served = {r for rr in declared.values() for r in rr}
    for r in sorted(roles - served):
        fail("coverage", "role %s is in model.json and no skill serves it -- the README's "
                         "'every role covered' claim would be false" % r)
        bad += 1

    # A count stated in the README must match the declarations, so it cannot drift. The
    # README said "thirteen are marked status: draft" when eleven were.
    readme = os.path.join(ROOT, "README.md")
    if os.path.isfile(readme):
        text = read(readme)
        words = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven",
                 8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve",
                 13: "thirteen", 14: "fourteen", 15: "fifteen"}
        for st in STATUSES:
            n = sum(1 for v in statuses.values() if v == st)
            claim = re.search(r"\*\*(?:Only )?(\w+) (?:are|is) marked `status: %s`" % st, text)
            if claim:
                said = claim.group(1).lower()
                if said not in (words.get(n, ""), str(n)):
                    fail("coverage", "README says %s skill(s) are status: %s; %d are"
                         % (said, st, n))
                    bad += 1

    if not bad:
        ok("coverage", "%d skills cover all %d roles; statuses: %s"
           % (len(declared), len(roles),
              ", ".join("%d %s" % (sum(1 for v in statuses.values() if v == s), s)
                        for s in STATUSES)))


CHECKS = {
    "refs": check_refs, "lint": check_lint, "registry": check_registry,
    "headings": check_headings, "width": check_width, "examples": check_examples,
    "skills": check_skills, "coverage": check_coverage,
}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--list" in argv:
        for name in CHECKS:
            print(name)
        return 0
    selected = [a for a in argv if not a.startswith("-")] or list(CHECKS)
    unknown = [s for s in selected if s not in CHECKS]
    if unknown:
        print("unknown check(s): %s" % ", ".join(unknown), file=sys.stderr)
        return 2
    for name in selected:
        CHECKS[name]()
    for line in PASSES:
        print("  ok   %s" % line)
    for line in FAILURES:
        print("  FAIL %s" % line)
    print()
    if FAILURES:
        print("%d failure(s) across %d check(s)" % (len(FAILURES), len(selected)))
        return 1
    print("all %d check(s) passed" % len(selected))
    return 0


if __name__ == "__main__":
    sys.exit(main())
