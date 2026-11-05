#!/usr/bin/env python3
"""Every closed vocabulary is declared once, enforced on both write paths, and documented truly.

    python -I tests/test_field_vocabularies.py
    python -I tests/test_field_vocabularies.py -v

Why this exists. Three separate exercises each found a field whose values were a closed set in the
prose and an open set in the code: `domains`, `link_types`, then `confidence`. Three is a habit, not
a coincidence, so this is the sweep rather than a fourth one-off.

What it found, and what it now prevents:

  `mode`          `profile --set mode=exsiting` was stored in silence. Thirteen skills branch on
                  this field, and `skills/orient` says getting it wrong is "expensive in one
                  direction: treating an existing product as new produces a PRD that describes a
                  product nobody has, and a backlog of stories that are already built". A typo put
                  every downstream skill on the NEW branch of a live product.

  `provenance`    Guarded by argparse `choices` on the CLI and by NOTHING on replay, so a
                  hand-written log line carrying `reconstrcuted` folded in with 0 problems. The
                  suite already has a rule for this -- a hand-written line must not do what the CLI
                  refuses -- and this field was outside it.

  `instrumented`  `skills/prd` documents `yes / no / NOT YET`; `instrumented=maybe-ish` was stored.
                  Worse, `skills/analytics` documented the SAME field on the same item type as
                  prose ("which events, since when"), so the producer and the consumer of a metric
                  disagreed about what the field holds.

  `confidence`    Fixed in the previous exercise -- and its own contract block still listed three of
                  the four values while the bullets below it listed four. The test written for it
                  checked only the bullets, so it passed. That is the second time one of my checks
                  had this blind spot, which is why the doc-agreement clause below reads EVERY
                  documented occurrence, not a chosen one.

`priority` is deliberately NOT here. `severity` is this suite's vocabulary; priority is the
operator's, and `skills/orient` Step 3 says to adopt the team's scale. It stays open on purpose, and
`shared/vocabulary.md` now says so -- because "open by design" and "nobody got round to it" must not
look the same to a reader.
"""

from __future__ import annotations

import glob
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HUB = os.path.join(ROOT, "shared", "scripts", "hub.py")
VERBOSE = "-v" in sys.argv

FAILURES = []


def run(hub, *args):
    p = subprocess.run([sys.executable, "-I", "-B", HUB, "--hub", hub] + [str(a) for a in args],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def check(label, cond, detail=""):
    if cond:
        if VERBOSE:
            print("  ok   %s" % label)
    else:
        print("  FAIL %s%s" % (label, (" -- " + detail) if detail else ""))
        FAILURES.append(label)


def model():
    return json.loads(io.open(os.path.join(ROOT, "shared", "hub", "model.json"),
                              encoding="utf-8").read())


# How to exercise each vocabulary through the CLI: (argv builder, needs_item)
def write_probe(field, value):
    """Return argv that sets `field` to `value` through a normal write."""
    if field == "mode":
        return ["profile", "--set", "mode=%s" % value, "--actor", "h1",
                "--role", "HEAD_OF_PRODUCT"]
    if field == "provenance":
        return ["add", "story", "S-P", "-f", "title=probe", "--provenance", str(value),
                "--actor", "o1", "--role", "PO"]
    if field == "confidence":
        return ["add", "insight", "I-P", "-f", "claim=probe",
                "-f", "confidence=%s" % value, "--actor", "r1", "--role", "RESEARCHER"]
    if field == "instrumented":
        return ["add", "metric", "M-P", "-f", "name=probe", "-f", "denominator=probe",
                "-f", "instrumented=%s" % value, "--actor", "p1", "--role", "PM"]
    if field == "owner_role":
        # Created by a release-side role on purpose: creating is allowed for them, meeting is not,
        # so this probe exercises the vocabulary without tripping the ownership rule.
        return ["add", "readiness", "RD-P", "-f", "title=probe",
                "-f", "owner_role=%s" % value, "--actor", "d1", "--role", "DELIVERY"]
    return None


def main():
    m = model()
    vocabs = m.get("field_vocabularies") or {}
    print("model declares %d field vocabular%s: %s"
          % (len(vocabs), "y" if len(vocabs) == 1 else "ies", ", ".join(sorted(vocabs))))
    check("the model declares field vocabularies in one place", bool(vocabs),
          "model.json has no `field_vocabularies`")
    for required in ("confidence", "mode", "provenance", "instrumented"):
        check("%r is declared" % required, required in vocabs,
              "declared: %s" % ", ".join(sorted(vocabs)))
    if not vocabs:
        print("\n%d failure(s)" % len(FAILURES))
        return 1

    tmp = tempfile.mkdtemp(prefix="fieldvocab_")
    try:
        for field, allowed in sorted(vocabs.items()):
            probe = write_probe(field, "")
            if probe is None:
                check("%r has a probe in this test" % field, False,
                      "add one, or the vocabulary is declared and unverified")
                continue

            # Every declared value is accepted.
            for value in allowed:
                hub = os.path.join(tmp, "ok-%s-%s" % (field, re.sub(r"\W+", "_", value)))
                run(hub, "init", "--actor", "h1", "--role", "HEAD_OF_PRODUCT")
                rc, out = run(hub, *write_probe(field, value))
                check("%s=%r is accepted" % (field, value), rc == 0, out.strip()[:150])

            # An undeclared value is refused on the CLI path.
            hub = os.path.join(tmp, "bad-%s" % field)
            run(hub, "init", "--actor", "h1", "--role", "HEAD_OF_PRODUCT")
            rc, out = run(hub, *write_probe(field, "nonsense-value"))
            check("%s rejects an undeclared value on write" % field, rc != 0,
                  "exit %d: %s" % (rc, out.strip()[:150]))
            check("%s's refusal lists the real values" % field,
                  rc != 0 and any(str(v) in out for v in allowed), out.strip()[:170])

        # A hand-written log line must not do what the CLI refuses. argparse `choices` guards only
        # the CLI, which is how `provenance` stayed unchecked on replay.
        hub = os.path.join(tmp, "replay")
        run(hub, "init", "--actor", "h1", "--role", "HEAD_OF_PRODUCT")
        run(hub, "add", "story", "S-1", "-f", "title=real", "--actor", "o1", "--role", "PO")
        logs = glob.glob(os.path.join(hub, "events", "PO", "*.jsonl"))
        check("the probe hub has a PO log to plant into", bool(logs))
        if logs:
            planted = {
                "provenance": {"v": 1, "event_id": "PO/o1#901", "seq": 901,
                               "ts": "2026-11-05T23:00:00.000000Z", "actor": "o1", "role": "PO",
                               "op": "add", "type": "story", "item": "S-90", "owner": "PO",
                               "state": "DRAFT", "provenance": "reconstrcuted",
                               "fields": {"title": "planted"}},
                "field": {"v": 1, "event_id": "PO/o1#902", "seq": 902,
                          "ts": "2026-11-05T23:00:01.000000Z", "actor": "o1", "role": "PO",
                          "op": "add", "type": "story", "item": "S-91", "owner": "PO",
                          "state": "DRAFT", "provenance": None,
                          "fields": {"title": "planted", "instrumented": "maybe-ish"}},
            }
            with io.open(logs[0], "a", encoding="utf-8", newline="") as fh:
                for ev in planted.values():
                    fh.write(json.dumps(ev) + "\n")
            rc, out = run(hub, "validate")
            check("a planted top-level provenance is a problem on replay",
                  "reconstrcuted" in out, out.strip()[:250])
            check("a planted field value is a problem on replay",
                  "maybe-ish" in out, out.strip()[:250])
            check("and validate exits non-zero on them", rc != 0, "exit %d" % rc)

        # Documentation must match the model EVERYWHERE it enumerates the values -- not in one
        # chosen place. `confidence` was documented as three values in its contract block and four
        # in the bullets below it, and the test written for it looked only at the bullets.
        docs = sorted(glob.glob(os.path.join(ROOT, "skills", "*", "SKILL.md"))
                      + glob.glob(os.path.join(ROOT, "shared", "*.md"))
                      + glob.glob(os.path.join(ROOT, "shared", "references", "*.md")))
        for field, allowed in sorted(vocabs.items()):
            lower = [str(v).lower() for v in allowed]
            for path in docs:
                text = io.open(path, encoding="utf-8").read()
                rel = os.path.relpath(path, ROOT).replace("\\", "/")
                # A line that enumerates this field's values with | or / separators.
                for line in text.splitlines():
                    if not re.match(r"^%s\s{2,}\S" % re.escape(field), line):
                        continue
                    # A contract line often carries a trailing clause after an em dash --
                    # "yes / no / not yet -- if no, that is work in scope". Cut it before
                    # splitting, or the last value is swallowed by the prose and the check reports
                    # a vocabulary gap that is really a parse failure.
                    # STRIP FIRST. Splitting on a 3+ space run before stripping consumed the
                    # line's own leading indent and returned an empty body, which silently blinded
                    # this check on the very line it was written for.
                    body = line[len(field):].strip()
                    body = re.split(r"\s+[—-]{1,2}\s+", body, 1)[0]
                    listed = [w.strip().lower() for w in re.split(r"[|/]", body)
                              if w.strip() and len(w.strip().split()) <= 3]
                    hits = [w for w in listed if w in lower]
                    if len(hits) < 2:
                        continue   # prose, not an enumeration
                    missing = [v for v in lower if v not in listed]
                    check("%s: %r enumerates the full vocabulary" % (rel, field), not missing,
                          "line omits %s -- %r" % (", ".join(missing), line.strip()[:90]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILURES:
        print("%d failure(s)" % len(FAILURES))
        return 1
    print("  ok   every closed vocabulary is declared once, enforced twice, documented truly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
