#!/usr/bin/env python3
"""Each skill's countable deliverable is recorded, not asserted.

    python -I tests/test_sufficiency_bars.py
    python -I tests/test_sufficiency_bars.py -v

Why this exists. An operator who had watched one engagement produce ~50 cases for a whole product
said they had started doubting the other skills. That doubt was warranted, and a keyword grep over
the skills was useless as an audit -- every file mentions `validate` somewhere, so everything looked
enforced. Probing each skill's SPECIFIC bar found two real holes:

  `launch`   The skill's central rule is "every claim in the copy links to a passing case, or is
             flagged unverified and does not ship." `CLAIMS_CHECKED` required a free-text
             `evidence` field. `evidence="checked them"` satisfied it. Marketing copy is the
             highest-exposure surface a product has and it had the weakest lock in the model.

  `design`   The skill's deliverable "is not a screen. It is **every state that screen can be
             in**" -- eight of them, and the ones skipped are the ones users hit. `REVIEWED`
             required NO field at all, so a design reached `ACCEPTED` with not one state recorded.

What was already sound, checked and stated so the audit is not just a list of faults: `design`
enforces `roles` and `different_actor_from` on both review and acceptance, so "never by its author"
holds; `backlog` refuses `READY` without criteria; `prd`/`analytics`/`discovery` require their
denominators, baselines and confidence; `release` computes rather than asserts.

Deliberately NOT enforced, and disclosed rather than quietly absent: an `adr`'s `falsifier`
(`skills/architecture` records the reason in its open questions).
"""

from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HUB = os.path.join(ROOT, "shared", "scripts", "hub.py")
VERBOSE = "-v" in sys.argv

FAILURES = []


def check(label, cond, detail=""):
    if cond:
        if VERBOSE:
            print("  ok   %s" % label)
    else:
        print("  FAIL %s%s" % (label, (" -- " + detail) if detail else ""))
        FAILURES.append(label)


def sh(hub, actor, role, *args):
    p = subprocess.run([sys.executable, "-I", "-B", HUB, "--hub", hub] + [str(a) for a in args]
                       + ["--actor", actor, "--role", role],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main():
    tmp = tempfile.mkdtemp(prefix="bars_")
    try:
        # ---- launch: a claim must name the case that carries it ------------------------
        hub = os.path.join(tmp, "launch")
        sh(hub, "h1", "HEAD_OF_PRODUCT", "init")
        sh(hub, "m1", "PMM", "add", "launch", "L-1", "-f", "title=2.5 announcement")
        rc, out = sh(hub, "m1", "PMM", "move", "L-1", "CLAIMS_CHECKED",
                     "-f", "evidence=checked them")
        check("a launch cannot reach CLAIMS_CHECKED on free-text evidence alone", rc != 0,
              "exit %d: %s" % (rc, out.strip()[:170]))
        check("  and the refusal names what is needed",
              "claims_verified_by" in out or "unverified_claims" in out, out.strip()[:200])

        rc, out = sh(hub, "m1", "PMM", "move", "L-1", "CLAIMS_CHECKED",
                     "-f", "evidence=each claim traced",
                     "-f", "claims_verified_by=S5-01 (3x figure), S5-02 (uptime)",
                     "-f", "unverified_claims=none")
        check("naming the cases and the unverified set is accepted", rc == 0,
              out.strip()[:170])

        # "none unverified" must be sayable, and so must an honest list -- the rule is that an
        # unverified claim is FLAGGED, not that it cannot exist.
        hub2 = os.path.join(tmp, "launch2")
        sh(hub2, "h1", "HEAD_OF_PRODUCT", "init")
        sh(hub2, "m1", "PMM", "add", "launch", "L-2", "-f", "title=blog post")
        rc, out = sh(hub2, "m1", "PMM", "move", "L-2", "CLAIMS_CHECKED",
                     "-f", "evidence=traced",
                     "-f", "claims_verified_by=S1-01",
                     "-f", "unverified_claims=the 99.99% figure: no case; flagged and cut")
        check("an unverified claim may be declared rather than hidden", rc == 0,
              out.strip()[:170])

        # ---- design: the eight states are the deliverable -----------------------------
        hub3 = os.path.join(tmp, "design")
        sh(hub3, "h1", "HEAD_OF_PRODUCT", "init")
        sh(hub3, "d1", "DESIGNER", "add", "design", "DSN-1", "-f", "title=export flow")
        rc, out = sh(hub3, "dl1", "DESIGN_LEAD", "move", "DSN-1", "REVIEWED")
        check("a design cannot be REVIEWED with no state coverage recorded", rc != 0,
              "exit %d: %s" % (rc, out.strip()[:170]))
        check("  and the refusal names the field", "states_covered" in out, out.strip()[:200])

        rc, out = sh(hub3, "dl1", "DESIGN_LEAD", "move", "DSN-1", "REVIEWED",
                     "-f", "states_covered=empty, loading, partial, error-per-cause, "
                           "permission-denied, too-much-data, offline n/a, success")
        check("with the states recorded it is accepted", rc == 0, out.strip()[:170])

        # what was already sound: the author cannot review or accept their own design
        hub4 = os.path.join(tmp, "design2")
        sh(hub4, "h1", "HEAD_OF_PRODUCT", "init")
        sh(hub4, "d1", "DESIGNER", "add", "design", "DSN-2", "-f", "title=x")
        rc, out = sh(hub4, "d1", "DESIGN_LEAD", "move", "DSN-2", "REVIEWED",
                     "-f", "states_covered=all eight")
        check("the author may not review their own design, even wearing the lead's hat", rc != 0,
              "exit %d: %s" % (rc, out.strip()[:140]))

        # ---- the bars that were already enforced, asserted so a regression shows ------
        hub5 = os.path.join(tmp, "sound")
        sh(hub5, "h1", "HEAD_OF_PRODUCT", "init")
        rc, _o = sh(hub5, "p1", "PO", "add", "story", "S-1", "-f", "title=a story")
        check("a story is created", rc == 0)
        rc, out = sh(hub5, "p1", "PO", "move", "S-1", "READY")
        check("backlog: READY still refuses a story with no criteria", rc != 0,
              out.strip()[:140])
        rc, out = sh(hub5, "pm1", "PM", "add", "metric", "M-1", "-f", "name=x")
        check("prd: a metric still refuses to exist without a denominator", rc != 0,
              out.strip()[:140])
        rc, out = sh(hub5, "r1", "RESEARCHER", "add", "insight", "I-1", "-f", "claim=x")
        check("discovery: an insight is created, and EVIDENCED is where the bar is", rc == 0)
        rc, out = sh(hub5, "r1", "RESEARCHER", "move", "I-1", "EVIDENCED",
                     "-f", "evidence=a", "-f", "sample_size=b", "-f", "does_not_show=c")
        check("discovery: EVIDENCED still refuses without confidence", rc != 0,
              out.strip()[:140])

        # ---- and the one deliberately left open is still disclosed --------------------
        arch = io.open(os.path.join(ROOT, "skills", "architecture", "SKILL.md"),
                       encoding="utf-8").read()
        check("architecture still discloses that falsifier is unenforced",
              "falsifier" in arch.split("## Open questions")[-1], "disclosure missing")

        model = json.loads(io.open(os.path.join(ROOT, "shared", "hub", "model.json"),
                                   encoding="utf-8").read())
        adr_met = [t for t in model["types"]["adr"]["transitions"] if t["to"] == "ACCEPTED"]
        check("  and it really is unenforced, so the disclosure is accurate",
              adr_met and "falsifier" not in (adr_met[0].get("requires_fields") or []),
              "falsifier became required; update the disclosure")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILURES:
        print("%d failure(s)" % len(FAILURES))
        return 1
    print("  ok   each skill's countable deliverable is recorded, and the open one is disclosed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
