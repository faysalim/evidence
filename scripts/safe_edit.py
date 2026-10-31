"""Validated, newline-and-BOM-preserving substitution.

Reads in BINARY and detects the newline from the bytes. Reading in text mode with universal newlines
normalises CRLF to \n, which makes any "is this file CRLF?" test silently false and rewrites the whole
file - that happened in a real engagement and produced a 3863-line diff that buried the actual two-line
change. Never read in text mode here.

apply(path, edits): every `old` must occur exactly once. Nothing is written unless all of them do, so a
mismatched anchor costs nothing. An anchor matching zero times is usually a character you assumed was a
hyphen and is really an em dash (U+2014), or a tab you wrote as spaces.

Write anchors with plain \n even in a CRLF file: this normalises internally and restores the file's own
newline on write.

Usage from an edit script:

    import sys; sys.path.insert(0, "<path to this scripts/ directory>")
    import safe_edit
    safe_edit.apply("src/Program.cs", [
        ("old text, unique in the file", "replacement"),
        ("another anchor", "another replacement"),
    ])
"""
import io


def apply(path, edits, verbose=True):
    raw = io.open(path, "rb").read()
    bom = raw[:3] == b"\xef\xbb\xbf"
    body = raw[3:] if bom else raw
    crlf = body.count(b"\r\n") > 0 and body.count(b"\n") == body.count(b"\r\n")
    nl = "\r\n" if crlf else "\n"
    s = body.decode("utf-8")

    # Work in LF internally so anchors can be written with plain \n, then restore on write.
    s_lf = s.replace("\r\n", "\n") if crlf else s

    for old, new in edits:
        c = s_lf.count(old)
        if verbose:
            print("  %-56s -> %d" % (old.strip().splitlines()[0][:54], c))
        if c != 1:
            raise SystemExit("ABORT %s: anchor matched %d times; nothing written" % (path, c))
        s_lf = s_lf.replace(old, new)

    out = s_lf.replace("\n", nl) if crlf else s_lf
    data = out.encode("utf-8")
    io.open(path, "wb").write((b"\xef\xbb\xbf" + data) if bom else data)
    if verbose:
        print("  WRITTEN %s (newline=%s, bom=%s)" % (path, "CRLF" if crlf else "LF", bom))
