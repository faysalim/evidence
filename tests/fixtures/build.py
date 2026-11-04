#!/usr/bin/env python3
"""Build the two worked fixtures by driving hub.py, and nothing else.

    python -I tests/fixtures/build.py --mode existing --out tests/fixtures/existing
    python -I tests/fixtures/build.py --mode new      --out tests/fixtures/new
    python -I tests/fixtures/build.py --all                      # both, then render dashboards

Every item is created and moved through the CLI, exactly as a skill would. Nothing writes to the
hub directly. That makes this a worked example AND an integration test of the whole model: if a
lifecycle in shared/hub/model.json forbids something a real engagement needs, this script fails
to build, which is the cheapest possible way to find that out.

The engagement is fictional on purpose. No real hostnames, tenant ids, customer names or keys --
the same house rule the skills are held to, checked by shared/scripts/check_repo.py examples.

`existing` is the full arc the brief asks for: orient -> PRD delta -> requirements -> stories with
criteria -> design -> ADR -> story built -> QA cases -> finding filed -> DEV fixes and hands back
-> QA verifies and closes -> release go/no-go -> docs -> launch copy -> metric reading.

`new` is the short arc for a greenfield product, where most of the interesting states are
"not measured yet" and the verdict is honestly NO VERDICT.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HUB_PY = os.path.join(ROOT, "shared", "scripts", "hub.py")

FAILED = []


def run(hub, actor, role, *args, **kw):
    """One hub.py invocation. A non-zero exit is a failure of the fixture, not of the test."""
    expect_fail = kw.pop("expect_fail", False)
    cmd = [sys.executable, "-I", HUB_PY, "--hub", hub, "--actor", actor, "--role", role]
    cmd += [str(a) for a in args]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    ok = (proc.returncode != 0) if expect_fail else (proc.returncode == 0)
    if not ok:
        FAILED.append("%s %s -> rc=%d %s" % (role, " ".join(str(a) for a in args[:3]),
                                             proc.returncode,
                                             (proc.stdout + proc.stderr).strip()[:180]))
    return proc


# ---------------------------------------------------------------------------
# the existing-product engagement
# ---------------------------------------------------------------------------

def build_existing(hub):
    """A team adding self-serve trials to a licensing product that already has customers."""

    # --- orient: the profile and the baseline, reconstructed from the product -------------
    run(hub, "lead", "QA", "init", "--engagement", "northwind-licensing")
    run(hub, "lead", "QA", "iteration", "1", "--note", "first pass on an existing product")
    run(hub, "lead", "QA", "profile",
        "--set", "mode=existing",
        "--set", 'domains=["licensing-server","api-platform"]',
        "--set", "deploy_branch=release/4.2",
        "--set", 'live_builds={"web":"a1b2c3d","issuer":"4.2.1@9f8e7d6"}',
        "--set", "methodology=two-week-iterations",
        "--set", 'mandate={"role":"QA","report_only":true,'
                 '"owned_environments":["the three-node test cluster I stood up"],'
                 '"out_of_bounds":["deploys","production config"]}',
        "--set", "conventions=conventions.md",
        "--set", "time_to_first_success_baseline=41min-9steps-2deadends")

    # The capability inventory found a surface the docs never mention. That is a finding
    # before any feature work starts.
    run(hub, "lead", "QA", "add", "finding", "F-1",
        "-f", "title=Issuer reads an env var the published docs never name",
        "-f", "severity=blocker", "-f", "scope=documentation",
        "-f", "status_action=CODE",
        "-f", "evidence=grep of the issuer binary names LICENCE_SELF_PATH; docs name LICENCE_PATH",
        "-f", "does_not_claim=whether any customer has hit it; no support data was supplied")

    # --- cleanup ledger, opened at minute one ---------------------------------------------
    run(hub, "lead", "QA", "add", "cleanup", "C-1",
        "-f", "title=three-node test cluster", "-f", "cost=billing per hour",
        "-f", "removable_by=me")

    # --- prd: current state first, then the delta -----------------------------------------
    run(hub, "pm", "PM", "add", "prd", "PRD-0",
        "-f", "title=Current state: how licences are issued today",
        "--provenance", "reconstructed",
        "-f", "note=reconstructed from the capability inventory, not from the wiki")
    run(hub, "pm", "PM", "add", "prd", "PRD-1",
        "-f", "title=Self-serve trials",
        "-f", "problem=A prospect cannot get a working licence without a sales call",
        "-f", "non_scope=No change to paid provisioning; no new plan tiers")
    run(hub, "pm", "PM", "link", "PRD-1", "derived_from", "PRD-0")

    run(hub, "pm", "PM", "add", "metric", "M-1",
        "-f", "name=trial-to-paid conversion",
        "-f", "definition=paid conversions within 30 days / trials started",
        "-f", "denominator=trials started, excluding internal and test mailboxes",
        "-f", "instrumented=NOT YET -- instrumenting is in scope")
    run(hub, "pm", "PM", "link", "PRD-1", "measures", "M-1")
    run(hub, "pm", "PM", "move", "PRD-1", "REVIEW")
    # The sponsor approves -- not the author. The hub enforces this.
    run(hub, "sponsor", "HEAD_OF_PRODUCT", "move", "PRD-1", "APPROVED")

    # --- requirements, with the conflict routed rather than blended ------------------------
    run(hub, "ba", "BA", "add", "requirement", "REQ-1",
        "-f", "statement=A trial licence expires 14 days after issue",
        "-f", "rationale=matches the sales-led trial length already in use",
        "-f", "source=sales lead, 2026-11-04, in the trials review",
        "-f", "exceptions=issued on the 29th of a short month; customer in a second region")
    run(hub, "ba", "BA", "link", "REQ-1", "refines", "PRD-1")
    run(hub, "po", "PO", "move", "REQ-1", "AGREED")

    run(hub, "ba", "BA", "add", "requirement", "REQ-2",
        "-f", "statement=One trial per email address",
        "-f", "source=support lead, 2026-11-04",
        "-f", "exceptions=subaddressing; case variants; a shared team mailbox")
    run(hub, "ba", "BA", "link", "REQ-2", "refines", "PRD-1")
    run(hub, "ba", "BA", "move", "REQ-2", "CONFLICTED",
        "-f", "reason=support wants one per email; sales wants one per company domain")
    run(hub, "ba", "BA", "add", "decision", "D-1",
        "-f", "title=Trial uniqueness: per email or per domain?",
        "-f", "options=[per email | per company domain | per email with a domain cap]",
        "-f", "recommendation=per email with a domain cap; it is what support already does by hand")
    run(hub, "ba", "BA", "link", "D-1", "blocks", "REQ-2")
    run(hub, "faisal", "OPERATOR", "move", "D-1", "ANSWERED",
        "-f", "answer=per email with a domain cap of 3, as recommended")
    run(hub, "faisal", "OPERATOR", "move", "REQ-2", "AGREED",
        "-f", "reason=settled by D-1")

    # --- backlog: criteria written as oracles ---------------------------------------------
    run(hub, "po", "PO", "add", "story", "S-1",
        "-f", "title=A prospect can request a trial licence and receive a working one")
    run(hub, "po", "PO", "link", "S-1", "realizes", "REQ-1")
    run(hub, "po", "PO", "move", "S-1", "READY",
        "-f", "acceptance_criteria=Submitting the form with a mailbox I control delivers an "
              "email within 5 minutes whose licence activates the real binary offline, and whose "
              "expiry read from the activated binary is 14 days from issue")

    run(hub, "po", "PO", "add", "story", "S-2",
        "-f", "title=A second trial request for the same mailbox is refused")
    run(hub, "po", "PO", "link", "S-2", "realizes", "REQ-2")
    run(hub, "po", "PO", "move", "S-2", "READY",
        "-f", "acceptance_criteria=A second request for the same mailbox, and for its "
              "subaddressed and case variants, returns a refusal naming the existing trial, and "
              "the issuer log shows exactly one licence minted for that mailbox")

    # --- design: the states, not just the happy path ---------------------------------------
    run(hub, "designer", "DESIGNER", "add", "design", "DES-1",
        "-f", "title=Trial request form and its states",
        "-f", "states=empty, submitting, success-pending-email, already-has-trial, "
              "provider-down, invalid-mailbox, rate-limited")
    run(hub, "designer", "DESIGNER", "link", "DES-1", "realizes", "S-1")
    run(hub, "design_lead", "DESIGN_LEAD", "move", "DES-1", "REVIEWED")
    run(hub, "po", "PO", "move", "DES-1", "ACCEPTED")

    # A design review finding of the strongest kind: the product's own two surfaces disagree.
    run(hub, "designer", "DESIGNER", "add", "finding", "F-2",
        "-f", "title=Trial form reports success before the licence is actually issued",
        "-f", "severity=major", "-f", "scope=experience",
        "-f", "status_action=CODE",
        "-f", "evidence=the paid checkout waits for the issuer; the trial form does not, and "
              "shows the same success panel",
        "-f", "does_not_claim=how often issuance actually fails in production")

    # --- architecture ----------------------------------------------------------------------
    run(hub, "tech_lead", "TECH_LEAD", "add", "adr", "ADR-1",
        "-f", "title=Trial issuance goes through the existing issuer, synchronously",
        "-f", "context=the issuer already enforces entitlement; a second path would duplicate it",
        "-f", "decision=call the issuer inline and fail the request if it fails",
        "-f", "consequences=request latency now depends on the issuer; a queue would hide "
              "failures from the user, which F-2 shows is the current defect",
        "-f", "rejected=async via queue (hides failure); a second minting path (duplicates "
              "entitlement logic)",
        "-f", "falsifier=if p95 form latency exceeds 3s at 10x current trial volume, this "
              "was the wrong call")
    run(hub, "tech_lead", "TECH_LEAD", "link", "ADR-1", "realizes", "S-1")
    run(hub, "tech_lead2", "TECH_LEAD", "move", "ADR-1", "ACCEPTED")

    # --- dev builds S-1 --------------------------------------------------------------------
    run(hub, "dev1", "DEV", "move", "S-1", "IN_PROGRESS")
    run(hub, "dev1", "DEV", "move", "S-1", "DONE", "-f", "commit=c0ffee1")

    # --- qa: gate rows first, then the cases -----------------------------------------------
    run(hub, "qa1", "QA", "add", "case", "S5-00a",
        "-f", "scope=licensing", "-f", "graded_by=licensing",
        "-f", "action=Issue one trial end to end through the real form and real mailbox",
        "-f", "oracle=a licence that activates the real binary")
    run(hub, "qa1", "QA", "move", "S5-00a", "PASS", "-f", "evidence=activated; 4.2.1@9f8e7d6")

    run(hub, "qa1", "QA", "add", "case", "S5-00b",
        "-f", "scope=licensing", "-f", "graded_by=licensing",
        "-f", "action=Revoke one issued licence by hand, then re-run the activation check",
        "-f", "oracle=the check reports exactly one failure, not zero and not two")
    run(hub, "qa1", "QA", "move", "S5-00b", "PASS", "-f", "evidence=1 failure reported")

    run(hub, "qa1", "QA", "add", "case", "S5-01",
        "-f", "scope=licensing", "-f", "graded_by=licensing",
        "-f", "action=POST the documented trial payload verbatim, then activate offline",
        "-f", "oracle=a usable licence in the real mailbox that activates the real binary",
        "-f", 'guards={"class":"documented path broken","ceiling":"blocker"}',
        "-f", 'touches=["issuer","web-form"]',
        "-f", 'ran_under={"build":"4.2.1@9f8e7d6","ran_by":"qa1"}')
    run(hub, "qa1", "QA", "link", "S5-01", "verifies", "S-1")

    run(hub, "qa1", "QA", "add", "case", "S5-02",
        "-f", "scope=licensing", "-f", "graded_by=licensing",
        "-f", "action=Request a second trial for the subaddressed variant of the same mailbox",
        "-f", "oracle=refusal, and exactly one licence in the issuer log for that mailbox",
        "-f", 'guards={"class":"uniqueness bypass","ceiling":"major"}',
        "-f", 'touches=["issuer"]')
    run(hub, "qa1", "QA", "link", "S5-02", "verifies", "S-2")

    # An acceptance requirement from the operator's contract -- source 0, outranking the docs.
    run(hub, "qa1", "QA", "add", "case", "R-1",
        "-f", "scope=requirements", "-f", "graded_by=licensing",
        "-f", "action=Issue 200 trials, kill the issuer mid-stream, reconcile against my ledger",
        "-f", "oracle=every acknowledged issue is present in the licence store after restart",
        "-f", 'guards={"class":"acknowledged issue lost","ceiling":"critical"}')

    # S5-01 fails -- the documented env var defect F-1 is what breaks it.
    run(hub, "qa1", "QA", "move", "S5-01", "FAIL",
        "-f", "evidence=403 from the issuer; it read LICENCE_SELF_PATH, which the docs do not name")
    run(hub, "qa1", "QA", "link", "S5-01", "verifies", "F-1")

    run(hub, "qa1", "QA", "move", "S5-02", "PASS",
        "-f", "evidence=refused; issuer log shows 1 licence for that mailbox")

    # R-1 cannot run here. That is a result, and it guards a critical class.
    run(hub, "qa1", "QA", "move", "R-1", "NOT_RUN",
        "-f", "reason=no second host available to kill the issuer independently")

    # --- dev fixes F-1 and hands back ------------------------------------------------------
    run(hub, "dev1", "DEV", "move", "F-1", "ACCEPTED")
    run(hub, "dev1", "DEV", "add", "fix", "FIX-1",
        "-f", "root_cause=issuer read LICENCE_SELF_PATH; the published name is LICENCE_PATH")
    run(hub, "dev1", "DEV", "link", "FIX-1", "fixes", "F-1")
    run(hub, "dev1", "DEV", "move", "FIX-1", "TEST_FAILS_FIRST",
        "-f", "test=Issuer_AcceptsDocumentedEnvVarName",
        "-f", "evidence=fails on 9f8e7d6, passes on d4d4d4d")
    run(hub, "dev1", "DEV", "move", "FIX-1", "DELIVERED",
        "-f", "commit=d4d4d4d", "-f", "build=4.2.2@d4d4d4d")
    run(hub, "dev1", "DEV", "move", "F-1", "FIXED",
        "-f", "commit=d4d4d4d", "-f", "build=4.2.2@d4d4d4d")

    # The DEV who claimed it may not verify it. Proven here, in the fixture.
    run(hub, "dev1", "QA", "move", "F-1", "VERIFIED",
        "-f", "evidence=x", "-f", "variant_used=y", expect_fail=True)

    # --- iteration 2: build identity, then verification -----------------------------------
    run(hub, "lead", "QA", "iteration", "2", "--note", "verifying the fix for F-1")
    run(hub, "qa2", "QA", "move", "FIX-1", "ACCEPTED")
    run(hub, "qa2", "QA", "move", "F-1", "VERIFIED",
        "-f", "evidence=three runs of 4.2.2@d4d4d4d differing only in the variable name",
        "-f", "variant_used=the undocumented name, which is now also accepted as a deprecated alias")
    run(hub, "qa2", "QA", "move", "F-1", "CLOSED")

    # re-arm and re-run the case that failed
    run(hub, "qa2", "QA", "move", "S5-01", "DESIGNED")
    run(hub, "qa2", "QA", "move", "S5-01", "PASS",
        "-f", "evidence=licence delivered and activated on 4.2.2@d4d4d4d")

    # now the PO can accept the story, because its linked case passes
    run(hub, "po", "PO", "move", "S-1", "ACCEPTED")

    # F-2 is accepted but deferred by the operator -- an honest outcome, recorded
    run(hub, "dev1", "DEV", "move", "F-2", "DEFERRED",
        "-f", "reason=the synchronous path from ADR-1 removes the cause; ship that first",
        "-f", "deferred_to=4.3")

    # --- release: the verdict is computed, and it is not green -----------------------------
    run(hub, "dm", "DELIVERY", "add", "release", "REL-1", "-f", "title=4.2.2")
    run(hub, "dev1", "DEV", "move", "REL-1", "CANDIDATE", "-f", "build=4.2.2@d4d4d4d")
    run(hub, "qa2", "QA", "move", "REL-1", "NO_VERDICT",
        "-f", "reason=R-1 guards a critical class and could not be run: no second host")

    run(hub, "dm", "DELIVERY", "add", "risk", "RISK-1",
        "-f", "title=No environment to exercise issuer durability",
        "-f", "impact=the contractual durability requirement is unverified at every release",
        "-f", "owner=TECH_LEAD")

    # The operator ships anyway. Their call, in their words, attributed.
    run(hub, "faisal", "OPERATOR", "move", "REL-1", "SHIPPED",
        "-f", "reason=the documented-path blocker is fixed and verified; the durability "
              "requirement stays unverified and I accept that for this release")

    # --- docs: verified against the product, not against the ticket ------------------------
    run(hub, "writer", "WRITER", "add", "doc", "DOC-1",
        "-f", "title=Requesting a trial licence")
    run(hub, "writer", "WRITER", "link", "DOC-1", "derived_from", "S-1")
    run(hub, "writer", "WRITER", "move", "DOC-1", "VERIFIED_AGAINST_PRODUCT",
        "-f", "evidence=11 of 11 claims run verbatim on 4.2.2@d4d4d4d; 1 FAIL corrected "
              "(the env var name), 2 BLOCKED (air-gapped activation, no host)")
    run(hub, "pm", "PM", "move", "DOC-1", "PUBLISHED")

    # --- launch: claims checked against cases ----------------------------------------------
    run(hub, "pmm", "PMM", "add", "launch", "LAU-1",
        "-f", "title=Self-serve trials announcement")
    run(hub, "pmm", "PMM", "link", "LAU-1", "derived_from", "PRD-1")
    run(hub, "pmm", "PMM", "move", "LAU-1", "CLAIMS_CHECKED",
        "-f", "evidence=4 claims: 2 SUPPORTED (S5-01, S5-02 PASS), 1 SOFTENED (offline "
              "activation is air-gapped-capable, not verified at scale), 1 REMOVED "
              "(no durability claim: R-1 is NOT RUN)")
    run(hub, "pm", "PM", "move", "LAU-1", "APPROVED")
    run(hub, "pmm", "PMM", "move", "LAU-1", "LIVE")

    # --- analytics: a reading the analyst makes and the PM interprets -----------------------
    run(hub, "analyst", "ANALYST", "move", "M-1", "BASELINED",
        "-f", "denominator=trials started, excluding internal and test mailboxes",
        "-f", "baseline=no prior self-serve trials existed; this reading IS the baseline")
    run(hub, "analyst", "ANALYST", "move", "M-1", "READ",
        "-f", "value=19 of 240 trials converted within 30 days (7.9%)",
        "-f", "denominator=240 trials started in the 30 days after launch",
        "-f", "evidence=issuer log joined to billing; 11 internal mailboxes excluded")
    run(hub, "pm", "PM", "move", "M-1", "INTERPRETED",
        "-f", "interpretation=first reading, so it is the baseline and not a result; a pricing "
              "page change landed in the same window and cannot be separated from it")
    run(hub, "analyst", "ANALYST", "add", "insight", "I-1",
        "-f", "claim=Trials that activate on the first day convert far more often",
        "-f", "evidence=14 of 19 converters activated within 24h; 3 of 221 non-converters did",
        "-f", "sample_size=240 trials, one 30-day window, one product",
        "-f", "does_not_show=causation, nor anything about trials that never activated at all")
    run(hub, "analyst", "ANALYST", "move", "I-1", "EVIDENCED")
    run(hub, "pm", "PM", "move", "I-1", "ACCEPTED")

    # --- cleanup verified by re-listing -----------------------------------------------------
    run(hub, "lead", "QA", "move", "C-1", "TORN_DOWN",
        "-f", "verified_by=re-listed instances: NONE")

    run(hub, "lead", "QA", "views")


# ---------------------------------------------------------------------------
# the new-product engagement
# ---------------------------------------------------------------------------

def build_new(hub):
    """A greenfield internal tool. Most things are honestly not measured yet."""
    run(hub, "lead", "PM", "init", "--engagement", "greenfield-intake")
    run(hub, "lead", "PM", "iteration", "1", "--note", "first slice of a new product")
    run(hub, "lead", "PM", "profile",
        "--set", "mode=new", "--set", 'domains=["multi-tenant-saas"]',
        "--set", "methodology=weekly",
        "--set", "note=no current state exists; there is no baseline to compare to")

    run(hub, "researcher", "RESEARCHER", "add", "insight", "I-1",
        "-f", "claim=Requests arrive by email and are lost when the handler is away",
        "-f", "evidence=6 of 9 coordinators described losing at least one request last month",
        "-f", "sample_size=9 coordinators across 3 teams; no requesters interviewed",
        "-f", "does_not_show=how many requests are lost, nor what they were worth")
    run(hub, "researcher", "RESEARCHER", "move", "I-1", "EVIDENCED")
    run(hub, "pm", "PM", "move", "I-1", "ACCEPTED")

    run(hub, "pm", "PM", "add", "prd", "PRD-1",
        "-f", "title=Request intake with an owner and a visible state",
        "-f", "problem=requests arrive by email and have no owner until someone notices",
        "-f", "non_scope=no approval workflow, no SLA reporting, no email replies in v1")
    run(hub, "pm", "PM", "link", "PRD-1", "derived_from", "I-1")
    run(hub, "pm", "PM", "add", "metric", "M-1",
        "-f", "name=requests with an owner within 1 business day",
        "-f", "definition=requests assigned within 1 business day / requests created",
        "-f", "denominator=requests created in the period",
        "-f", "instrumented=NOT YET")
    run(hub, "pm", "PM", "link", "PRD-1", "measures", "M-1")
    run(hub, "pm", "PM", "move", "PRD-1", "REVIEW")
    run(hub, "sponsor", "HEAD_OF_PRODUCT", "move", "PRD-1", "APPROVED")

    run(hub, "po", "PO", "add", "story", "S-1",
        "-f", "title=A coordinator can create a request and see its owner")
    run(hub, "po", "PO", "link", "S-1", "realizes", "PRD-1")
    run(hub, "po", "PO", "move", "S-1", "READY",
        "-f", "acceptance_criteria=Creating a request as a coordinator and reloading as a "
              "different coordinator shows the same owner and state; a coordinator from "
              "another team sees nothing")
    run(hub, "dev1", "DEV", "move", "S-1", "IN_PROGRESS")
    run(hub, "dev1", "DEV", "move", "S-1", "DONE", "-f", "commit=b0b0b01")

    run(hub, "qa1", "QA", "add", "case", "S3-00a",
        "-f", "scope=control-plane", "-f", "graded_by=control-plane",
        "-f", "action=Create one request and read it back as a second coordinator",
        "-f", "oracle=same owner and state, read by a different session")
    run(hub, "qa1", "QA", "move", "S3-00a", "PASS", "-f", "evidence=matched")
    run(hub, "qa1", "QA", "add", "case", "S3-00b",
        "-f", "scope=control-plane", "-f", "graded_by=control-plane",
        "-f", "action=Reassign one request directly in the store, then re-read",
        "-f", "oracle=the read-back reports exactly the one changed owner")
    run(hub, "qa1", "QA", "move", "S3-00b", "PASS", "-f", "evidence=1 change detected")

    run(hub, "qa1", "QA", "add", "case", "S3-01",
        "-f", "scope=control-plane", "-f", "graded_by=control-plane",
        "-f", "action=Read a request as a coordinator from another team, via UI and via export",
        "-f", "oracle=neither channel returns the row",
        "-f", 'guards={"class":"cross-team leak","ceiling":"critical"}',
        "-f", 'touches=["api","export"]')
    run(hub, "qa1", "QA", "link", "S3-01", "verifies", "S-1")
    run(hub, "qa1", "QA", "move", "S3-01", "FAIL",
        "-f", "evidence=the UI hides it; the CSV export returns it")
    run(hub, "qa1", "QA", "add", "finding", "F-1",
        "-f", "title=CSV export ignores team scoping and returns other teams rows",
        "-f", "severity=critical", "-f", "scope=security", "-f", "status_action=CODE",
        "-f", "evidence=export as team B contains 14 rows owned by team A",
        "-f", "does_not_claim=whether anyone has downloaded such an export; no audit log exists yet")
    run(hub, "qa1", "QA", "link", "S3-01", "verifies", "F-1")

    run(hub, "dm", "DELIVERY", "add", "risk", "RISK-1",
        "-f", "title=No audit log, so a leak cannot be investigated after the fact",
        "-f", "impact=cannot answer whether data was accessed", "-f", "owner=TECH_LEAD")
    run(hub, "dm", "DELIVERY", "add", "release", "REL-1", "-f", "title=0.1.0")
    run(hub, "dev1", "DEV", "move", "REL-1", "CANDIDATE", "-f", "build=0.1.0@b0b0b01")
    run(hub, "qa1", "QA", "move", "REL-1", "NOT_GREEN",
        "-f", "reason=F-1 is an open critical: the export crosses a team boundary")
    run(hub, "lead", "PM", "views")


# ---------------------------------------------------------------------------

def render(hub, out):
    sys.path.insert(0, os.path.join(ROOT, "shared", "scripts"))
    import hub as H
    import dashboard as D
    h = H.Hub(hub)
    pages = D.render(h, out)
    label, first_fail, _ = D.verdict(h)
    return h, pages, label, first_fail


def build(mode, out):
    out = os.path.abspath(out)
    if os.path.isdir(out):
        shutil.rmtree(out)
    hub = os.path.join(out, "hub")
    os.makedirs(os.path.join(hub, "events"), exist_ok=True)
    (build_existing if mode == "existing" else build_new)(hub)
    h, pages, label, first_fail = render(hub, os.path.join(out, "dashboard"))
    print("%s: %d items, %d events, %d pages" % (mode, len(h.items), len(h.applied), pages))
    print("  verdict: %s%s" % (label, "" if not first_fail else "  (first gap: %s)" % first_fail))
    problems = h.validate()
    for p in problems:
        print("  validate: %s" % p)
    return h, problems


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["existing", "new"])
    ap.add_argument("--out")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args(argv)

    base = os.path.join(ROOT, "tests", "fixtures")
    targets = [("existing", os.path.join(base, "existing")),
               ("new", os.path.join(base, "new"))] if args.all else \
        [(args.mode, args.out or os.path.join(base, args.mode))]

    bad = 0
    for mode, out in targets:
        _h, problems = build(mode, out)
        bad += len(problems)

    if FAILED:
        print("\n%d hub.py call(s) did not behave as the fixture expects:" % len(FAILED))
        for f in FAILED:
            print("  %s" % f)
        return 1
    if bad:
        print("\n%d validate problem(s) in the built fixtures" % bad)
        return 1
    print("\nboth fixtures built through hub.py only; validate is clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
