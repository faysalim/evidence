"""Validated, newline-and-BOM-preserving substitution.

Reads in BINARY and detects the newline from the bytes. Reading in text mode with universal newlines
normalises CRLF to \n, which makes any "is this file CRLF?" test silently false and rewrites the whole
file - that happened in a real engagement and produced a 3863-line diff that buried the actual two-line
change. Never read in text mode here.

apply(path, edits): **every `old` is validated against the ORIGINAL file, before any edit is applied.**
Each must occur exactly once there, and no two anchors may overlap. Nothing is written unless all of them
pass, so a mismatched anchor costs nothing. An anchor matching zero times is usually a character you
assumed was a hyphen and is really an em dash (U+2014), or a tab you wrote as spaces.

Validating against the original matters because edits otherwise cascade: given a file `foo\nbar` and the
edits [("foo","bar"), ("bar\nbar","Z")], a sequential implementation finds the second anchor in text the
first edit just created and writes `Z` - an anchor that never appeared in the file you were looking at
silently rewrote it. Anchors describe the file you read, not an intermediate state you cannot see.

Write anchors with plain \n even in a CRLF file: this normalises internally and restores the file's own
newline on write. A file with MIXED endings is rejected rather than guessed at, because either choice
silently rewrites the lines of the other kind.

The write is atomic: a temp file in the same directory, flushed and replaced, so an interrupted run cannot
leave a half-written source file.

Usage from an edit script:

    import sys; sys.path.insert(0, "<path to this scripts/ directory>")
    import safe_edit
    safe_edit.apply("src/Program.cs", [
        ("old text, unique in the file", "replacement"),
        ("another anchor", "another replacement"),
    ])

    safe_edit.apply("src/Program.cs", edits, dry_run=True)   # validate and report, write nothing

Or from the command line, to check anchors before committing to them:

    python scripts/safe_edit.py --check src/Program.cs "anchor one" "anchor two"
"""
import io
import os
import sys
import tempfile


class EditError(Exception):
    """Validation failed. Nothing has been written."""


def _label(old):
    """A one-line label for an anchor, safe for an empty or whitespace-only string."""
    lines = old.strip().splitlines()
    head = lines[0] if lines else repr(old)
    return head[:54]


def _read(path):
    """Return (text_lf, newline, bom, had_crlf). Rejects mixed endings and non-UTF-8."""
    try:
        raw = io.open(path, "rb").read()
    except OSError as exc:
        raise EditError("cannot read %s: %s" % (path, exc))

    bom = raw[:3] == b"\xef\xbb\xbf"
    body = raw[3:] if bom else raw

    crlf_count = body.count(b"\r\n")
    lf_total = body.count(b"\n")
    lone_cr = body.replace(b"\r\n", b"").count(b"\r")

    if crlf_count and crlf_count != lf_total:
        raise EditError(
            "%s has MIXED line endings (%d CRLF of %d LF): refusing to guess, because either "
            "choice silently rewrites every line of the other kind. Normalise the file first "
            "(and commit that separately) or edit it by hand."
            % (path, crlf_count, lf_total))
    if lone_cr:
        raise EditError(
            "%s contains %d bare CR (old-Mac) line ending(s): normalise the file first."
            % (path, lone_cr))

    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise EditError(
            "%s is not valid UTF-8 (%s at byte %d). This tool preserves bytes it can round-trip; "
            "a UTF-16 or Latin-1 source needs its own handling, and guessing the encoding is how "
            "a diff ends up rewriting the whole file." % (path, exc.reason, exc.start))

    had_crlf = bool(crlf_count)
    return (text.replace("\r\n", "\n") if had_crlf else text,
            "\r\n" if had_crlf else "\n", bom, had_crlf)


def _validate(text, edits, path, verbose):
    """Check every anchor against `text` (the original). Returns the resolved spans."""
    if not edits:
        raise EditError("no edits given for %s" % path)

    spans = []
    problems = []
    for index, item in enumerate(edits):
        try:
            old, new = item
        except (TypeError, ValueError):
            raise EditError("edit %d of %s is not an (old, new) pair: %r" % (index, path, item))
        if not isinstance(old, str) or not isinstance(new, str):
            raise EditError("edit %d of %s is not a pair of strings: %r" % (index, path, item))
        if not old:
            raise EditError(
                "edit %d of %s has an EMPTY anchor, which matches at every position. "
                "An empty anchor is always a bug in the calling script." % (index, path))
        if not old.strip():
            raise EditError(
                "edit %d of %s has a whitespace-only anchor (%r): it is almost never unique and "
                "is unreadable in a diff. Include a non-blank line." % (index, path, old))

        count = text.count(old)
        if verbose:
            print("  %-56s -> %d" % (_label(old), count))
        if count != 1:
            problems.append("anchor %d (%s) matched %d times in the original"
                            % (index, _label(old), count))
            continue
        start = text.index(old)
        spans.append((start, start + len(old), index, old, new))

    if problems:
        raise EditError("ABORT %s: %s; nothing written" % (path, "; ".join(problems)))

    # Overlapping anchors mean the result depends on application order, which the caller
    # cannot see. Reject rather than pick an order for them.
    ordered = sorted(spans)
    for (a_start, a_end, a_i, a_old, _), (b_start, b_end, b_i, b_old, _) in zip(ordered, ordered[1:]):
        if b_start < a_end:
            raise EditError(
                "ABORT %s: anchors %d (%s) and %d (%s) OVERLAP in the original; the result would "
                "depend on application order. Nothing written."
                % (path, a_i, _label(a_old), b_i, _label(b_old)))
    return ordered


def apply(path, edits, verbose=True, dry_run=False):
    """Apply `edits` to `path`. Validates everything against the original first.

    Raises EditError without writing if any anchor does not match exactly once, if two
    anchors overlap, or if the file cannot be round-tripped. Returns the number of edits
    applied (0 for a dry run).
    """
    text, newline, bom, had_crlf = _read(path)
    spans = _validate(text, edits, path, verbose)

    if dry_run:
        if verbose:
            print("  DRY RUN %s: %d anchor(s) validated, nothing written" % (path, len(spans)))
        return 0

    # Build the result from the original by slicing, so no edit can ever see, match, or
    # disturb the output of another.
    out, cursor = [], 0
    for start, end, _index, _old, new in spans:
        out.append(text[cursor:start])
        out.append(new)
        cursor = end
    out.append(text[cursor:])
    result = "".join(out)

    data = (result.replace("\n", newline) if had_crlf else result).encode("utf-8")
    if bom:
        data = b"\xef\xbb\xbf" + data

    directory = os.path.dirname(os.path.abspath(path)) or "."
    fd, temp = tempfile.mkstemp(dir=directory, prefix=".safe_edit-", suffix=".tmp")
    try:
        with io.open(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp, path)
    except BaseException:
        try:
            os.unlink(temp)
        except OSError:
            pass
        raise

    if verbose:
        print("  WRITTEN %s (%d edits, newline=%s, bom=%s)"
              % (path, len(spans), "CRLF" if had_crlf else "LF", bom))
    return len(spans)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] not in ("--check", "--help", "-h"):
        print(__doc__.strip().splitlines()[0])
        print("usage: python safe_edit.py --check <path> <anchor> [<anchor> ...]")
        return 0 if argv and argv[0] in ("--help", "-h") else 2
    if argv[0] in ("--help", "-h"):
        print(__doc__)
        return 0
    if len(argv) < 3:
        print("usage: python safe_edit.py --check <path> <anchor> [<anchor> ...]",
              file=sys.stderr)
        return 2
    path, anchors = argv[1], argv[2:]
    try:
        apply(path, [(a, a) for a in anchors], verbose=True, dry_run=True)
    except EditError as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
