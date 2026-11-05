#!/usr/bin/env python3
"""The secret-shaped-token patterns, tested in BOTH directions.

    python -I tests/test_secret_patterns.py

Why this exists. `check_repo.py check_examples` enforces house rule 8 -- no real key in any
example -- and its key pattern was `\\b(?:sk|pk|ghp|gho|AKIA)[-_A-Za-z0-9]{12,}`, with no
separator required after the prefix. So it matched any word beginning "sk" or "pk" followed by
twelve characters, and it failed the build over `skillListingBudgetFraction`: a settings key NAME,
documented in the README, not a secret.

A false positive in a secret check is not harmless. It trains whoever hits it to reword honest
prose until the check goes quiet, and the next thing they silence that way might be a real key.

Both directions are tested because only testing the positive direction is how the original got
shipped: a pattern that flags everything passes every "does it catch a key?" test there is.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "shared", "scripts"))

import check_repo  # noqa: E402

# Real tokens, lightly mangled so this file does not itself trip the check it tests.
MUST_FLAG = [
    "sk-abc123def456ghi789",
    "sk_test_abcdefghijklmnop",
    "pk_live_abcdefghijklmno",      # the separator-in-tail case
    "ghp_aaaaaaaaaaaaaaaaaaaa",
    "gho_bbbbbbbbbbbbbbbbbbbb",
    "AKIAIOSFODNN7EXAMPLE",
]

# Honest prose and real identifiers that must NEVER be called a secret.
MUST_NOT_FLAG = [
    "skillListingBudgetFraction",   # the one that actually broke the build
    "skillOverrides",
    "skipTheseLongIdentifiers",
    "pkcs11providerlibrary",
    "skeletonConfiguration",
    "pkgManagerSelection",
]


def key_patterns():
    """The key/token patterns from check_examples, found by their message rather than by index.

    Reaching in by position would silently test the wrong pattern the moment someone reorders
    the list -- the same class of mistake as the regex this file exists for.
    """
    import re
    src = open(check_repo.__file__, encoding="utf-8").read()
    out = []
    for raw, msg in re.findall(r"re\.compile\(r'([^']+)'\),\s*\"([^\"]+)\"", src):
        if "key" in msg:
            out.append((re.compile(raw), msg))
    return out


def main():
    pats = key_patterns()
    failures = []

    if len(pats) < 2:
        failures.append("expected at least 2 key patterns in check_examples, found %d -- "
                        "the extraction here is stale, so nothing below was really tested"
                        % len(pats))

    def flagged(text):
        return any(p.search(text) for p, _ in pats)

    print("must be flagged")
    for text in MUST_FLAG:
        ok = flagged(text)
        print("  %s %s" % ("ok  " if ok else "FAIL", text))
        if not ok:
            failures.append("a real-looking token is NOT flagged: %s" % text)

    print("\nmust NOT be flagged")
    for text in MUST_NOT_FLAG:
        ok = not flagged(text)
        print("  %s %s" % ("ok  " if ok else "FAIL", text))
        if not ok:
            failures.append("honest text IS flagged as a secret: %s -- a false positive in a "
                            "secret check teaches people to reword around it" % text)

    print()
    for f in failures:
        print("  FAIL %s" % f)
    if failures:
        print("\n%d failure(s)" % len(failures))
        return 1
    print("  ok   %d flagged, %d cleared, across %d pattern(s)"
          % (len(MUST_FLAG), len(MUST_NOT_FLAG), len(pats)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
