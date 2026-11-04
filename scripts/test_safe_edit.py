#!/usr/bin/env python3
"""Self-test for safe_edit.py. Standard library only, no network.

    python -I scripts/test_safe_edit.py

Each check marked [REGRESSION] fails against the version of safe_edit.py that validated
anchors sequentially against the partly-edited text. They are here because that version
shipped, and because this is the skill's own rule applied to itself: a test that passes
before the fix asserts nothing.
"""

from __future__ import annotations

import io
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import safe_edit  # noqa: E402

FAILURES = []
TMP = None


def check(label, condition, detail=""):
    if condition:
        print("  ok   %s" % label)
    else:
        print("  FAIL %s %s" % (label, detail))
        FAILURES.append(label)


def write(name, data):
    path = os.path.join(TMP, name)
    with io.open(path, "wb") as fh:
        fh.write(data)
    return path


def read(path):
    with io.open(path, "rb") as fh:
        return fh.read()


def expect_error(label, path, edits, needle=None):
    """The call must raise EditError and leave the file byte-identical."""
    before = read(path)
    try:
        safe_edit.apply(path, edits, verbose=False)
    except safe_edit.EditError as exc:
        same = read(path) == before
        matched = (needle is None) or (needle.lower() in str(exc).lower())
        check(label, same and matched,
              "file changed" if not same else "message was: %s" % exc)
        return
    except Exception as exc:  # noqa: BLE001 - any other exception is itself the bug
        check(label, False, "raised %s: %s" % (type(exc).__name__, exc))
        return
    check(label, False, "no error raised; file is now %r" % read(path))


def main():
    global TMP
    TMP = tempfile.mkdtemp(prefix="safe-edit-test-")
    try:
        print("validation happens against the original")
        # [REGRESSION] The second anchor does not exist in the original: it only appears
        # in the text the first edit creates. The old version wrote 'Z\n'.
        p = write("cascade.txt", b"foo\nbar\n")
        expect_error("[REGRESSION] an anchor matching only the post-edit text is rejected",
                     p, [("foo", "bar"), ("bar\nbar", "Z")], "matched 0 times in the original")

        # [REGRESSION] An anchor unique in the original but duplicated by an earlier edit
        # must still apply - it describes the file the caller read.
        p = write("dup.txt", b"alpha\nbeta\n")
        n = safe_edit.apply(p, [("alpha", "beta"), ("beta", "gamma")], verbose=False)
        check("[REGRESSION] each anchor applies to its own span in the original",
              read(p) == b"beta\ngamma\n" and n == 2, repr(read(p)))

        print("\nanchor validation")
        p = write("ok.txt", b"hello world\n")
        expect_error("a zero-match anchor aborts", p, [("nope", "x")], "matched 0 times")
        p = write("twice.txt", b"a\na\n")
        expect_error("a two-match anchor aborts", p, [("a", "b")], "matched 2 times")
        p = write("empty.txt", b"content\n")
        expect_error("an empty anchor is rejected, not an IndexError",
                     p, [("", "x")], "empty anchor")
        expect_error("a whitespace-only anchor is rejected, not an IndexError",
                     p, [("   ", "x")], "whitespace-only")
        expect_error("overlapping anchors are rejected",
                     write("ov.txt", b"abcdef\n"), [("abcd", "X"), ("cdef", "Y")], "overlap")
        expect_error("an empty edit list is rejected", p, [], "no edits")
        expect_error("a malformed edit pair is rejected", p, [("a",)], "not an (old, new) pair")
        expect_error("a non-string replacement is rejected", p, [("content", 7)],
                     "not a pair of strings")

        print("\nencoding and line endings")
        # [REGRESSION] mixed endings used to be silently treated as LF, so anchors written
        # with \n failed against the CRLF lines with a confusing "matched 0 times".
        p = write("mixed.txt", b"one\r\ntwo\nthree\r\n")
        expect_error("[REGRESSION] a file with mixed endings is rejected, not guessed at",
                     p, [("two", "TWO")], "mixed line endings")

        # [REGRESSION] non-UTF-8 used to crash with a raw UnicodeDecodeError.
        p = write("utf16.txt", u"hello\n".encode("utf-16"))
        expect_error("[REGRESSION] a non-UTF-8 file is rejected with an explanation",
                     p, [("hello", "x")], "not valid utf-8")

        p = write("bare-cr.txt", b"one\rtwo\r")
        expect_error("a bare-CR file is rejected", p, [("one", "x")], "bare cr")

        p = write("crlf.txt", b"alpha\r\nbeta\r\n")
        safe_edit.apply(p, [("alpha\nbeta", "beta\nalpha")], verbose=False)
        check("CRLF is preserved and \\n anchors still match",
              read(p) == b"beta\r\nalpha\r\n", repr(read(p)))

        p = write("bom.txt", u"﻿alpha\n".encode("utf-8"))
        safe_edit.apply(p, [("alpha", "beta")], verbose=False)
        check("a BOM is preserved", read(p) == u"﻿beta\n".encode("utf-8"), repr(read(p)))

        p = write("noeol.txt", b"last line no newline")
        safe_edit.apply(p, [("last", "final")], verbose=False)
        check("a missing trailing newline is not invented",
              read(p) == b"final line no newline", repr(read(p)))

        p = write("unicode.txt", u"em—dash and café\n".encode("utf-8"))
        safe_edit.apply(p, [(u"em—dash", u"en–dash")], verbose=False)
        check("non-ASCII anchors round-trip",
              read(p) == u"en–dash and café\n".encode("utf-8"), repr(read(p)))

        print("\ndry run and atomicity")
        p = write("dry.txt", b"keep me\n")
        n = safe_edit.apply(p, [("keep", "drop")], verbose=False, dry_run=True)
        check("a dry run validates and writes nothing",
              read(p) == b"keep me\n" and n == 0, repr(read(p)))

        p = write("atomic.txt", b"alpha\n")
        safe_edit.apply(p, [("alpha", "beta")], verbose=False)
        leftovers = [f for f in os.listdir(TMP) if f.startswith(".safe_edit-")]
        check("no temp file is left behind", not leftovers, repr(leftovers))

        expect_error("a missing file is an EditError, not an OSError",
                     write("exists.txt", b"x\n"),
                     [("x", "y")] and [("zzz", "y")], "matched 0 times")
        try:
            safe_edit.apply(os.path.join(TMP, "no-such-file.txt"), [("a", "b")], verbose=False)
            check("a nonexistent path is an EditError", False, "no error raised")
        except safe_edit.EditError as exc:
            check("a nonexistent path is an EditError", "cannot read" in str(exc), str(exc))
        except Exception as exc:  # noqa: BLE001
            check("a nonexistent path is an EditError", False,
                  "raised %s" % type(exc).__name__)

        print("\nthe --check CLI")
        p = write("cli.txt", b"anchor one\nanchor two\n")
        check("--check exits 0 when every anchor is unique",
              safe_edit.main(["--check", p, "anchor one", "anchor two"]) == 0)
        check("--check exits 1 when an anchor is missing",
              safe_edit.main(["--check", p, "absent"]) == 1)
        check("--check writes nothing", read(p) == b"anchor one\nanchor two\n")
    finally:
        shutil.rmtree(TMP, ignore_errors=True)

    print()
    if FAILURES:
        print("%d check(s) FAILED: %s" % (len(FAILURES), ", ".join(FAILURES)))
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
