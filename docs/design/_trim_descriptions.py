"""One-shot: trim every skill description to fit the measured listing budget.

Kept in docs/design so the change is auditable rather than a mystery diff. The measured
always-on cost with the original descriptions was 2,773 tokens against a 2,500 threshold;
over budget means Claude Code silently DROPS descriptions, starting with the least-invoked
skills -- which would be the new drafts. Every trigger phrase and every "Not for" line is
preserved; what came out is role preambles and redundancy.
"""
import io
import os
import re

D = {
    "analytics": (
        "Read product metrics against the denominator and baseline the PRD stated, compare to that "
        "baseline rather than a feeling, write the post-launch review including the metrics that did "
        "not move, and feed findings back as insights. Use when the user wants metrics read or "
        "defined, a launch or experiment assessed, a funnel or retention analysed, or a post-launch "
        "review. Not for defining success criteria - that is evidence:prd. Not for instrumenting "
        "code - that is evidence:dev."),
    "architecture": (
        "Document the architecture a product actually has before changing it, then write the technical "
        "design as a change against that, recording each consequential choice as an ADR with the "
        "options rejected and what would prove it wrong. Covers the durability, consistency and "
        "failure-mode contracts the product class implies. Use when the user wants a technical design, "
        "ADR, system diagram, or an existing system's architecture documented. Not for product scope - "
        "that is evidence:prd."),
    "backlog": (
        "Turn a PRD and requirements into stories whose acceptance criteria are oracles - each "
        "gradeable the same way by a different person, so QA can turn it straight into a test case. "
        "For an existing product it imports the backlog, adds missing criteria and flags untestable "
        "stories. Use when the user wants stories or tickets written, a backlog groomed or prioritised, "
        "or acceptance criteria written or reviewed. Not for deciding what to build - that is "
        "evidence:prd."),
    "delivery": (
        "Generate delivery status from the work-item hub instead of collecting it, maintain the RAID "
        "risk log, surface what is blocked and on whom, and plan milestones against dependencies the "
        "hub already knows. Use when the user wants a status report, delivery plan or milestones, a "
        "RAID or risk log, cross-team dependencies tracked, or an answer to why something is late. Not "
        "for prioritising the backlog - that is evidence:backlog."),
    "design": (
        "Turn stories into flows and designs covering the failure, empty, partial and "
        "permission-denied states as well as the happy path, and run design reviews whose findings are "
        "provable rather than matters of taste. Use when the user wants a flow, screen, interaction or "
        "design system work designed or reviewed, a usability problem diagnosed, or error and empty "
        "states specified. Not for testing a build - that is evidence:qa."),
    "dev": (
        "Build a story or fix a reported finding: learn an existing repo's real conventions and deploy "
        "branch first, work in an isolated worktree, write the test before the fix and prove it fails, "
        "copy the case's oracle into that test, and hand back a packet naming the build digest. Use "
        "when the user wants a story implemented, a bug or QA finding fixed, a fix handed back for "
        "verification, or a repo's conventions learned before a change. Not for finding or verifying "
        "bugs - that is evidence:qa, and you never grade your own fix."),
    "discovery": (
        "Plan and synthesise product research: interview guides, and insight items that each carry "
        "their evidence, sample size and what they do not show, separating observed from reported from "
        "inferred. Use when the user wants user research planned or synthesised, interviews or "
        "usability sessions prepared, findings turned into insights, or a problem validated before a "
        "PRD. Not for writing the PRD - that is evidence:prd."),
    "docs-authoring": (
        "Write user and admin documentation from the product's observed behaviour rather than from "
        "tickets, then verify every claim by running it verbatim as a customer would, and enumerate the "
        "real surface to find what is undocumented. Use when the user wants user docs, admin guides, "
        "API reference or a quickstart written, reviewed or verified against the product. Not for "
        "marketing copy - that is evidence:launch."),
    "hub": (
        "Answer status questions from the shared work-item hub and render its dashboard: what is the "
        "status, what is waiting on me or on a role, what is blocked, show the traceability, validate "
        "the hub, and create items for roles with no skill of their own. Use when the user asks where "
        "something stands, what is waiting on whom, or wants the dashboard. Not for doing a role's "
        "work - use that role's skill, and a question the hub cannot answer gets a plain "
        "does-not-know."),
    "launch": (
        "Positioning, launch plan and customer-facing copy where every product claim links to a "
        "passing test case or is flagged unverified, and every price, limit and plan name is checked "
        "against the source of truth rather than the previous copy. Use when the user wants launch "
        "messaging, positioning, announcement or website copy, or a go-to-market plan written or "
        "reviewed. Not for the ship decision - that is evidence:release."),
    "orient": (
        "Establish the product profile and baseline before any other skill runs: new or existing "
        "product, its product class, the team's methodology, toolchain and existing conventions. For an "
        "existing product it builds a capability inventory from the running product and maps their "
        "artifacts onto hub item types. Use when starting work on an unfamiliar product or repo, or "
        "when another skill reports no profile. Not for testing - that is evidence:qa."),
    "prd": (
        "Write a product requirements document: the problem, who has it, success metrics measurable "
        "with a stated denominator and baseline, and an explicit non-scope. For an existing product it "
        "reconstructs a current-state PRD from what the product does, then states the change as a "
        "delta. Use when the user wants a PRD, product brief, spec or one-pager written or reviewed, "
        "scope defined, or success criteria agreed before build. Not for stories - that is "
        "evidence:backlog."),
    "qa": (
        "Evidence-first end-to-end QA: prove every finding by doing the thing rather than checking that "
        "it responds, publish the test cases and the coverage denominator, and compute a bounded "
        "release verdict instead of asserting one. Use when the user wants a product, release, website, "
        "app, API, SaaS or deployment tested or QA'd; bugs found, verified or ranked before shipping; "
        "test cases or a test matrix written; or the docs checked against the product. Not for fixing "
        "what QA found - that is evidence:dev."),
    "release": (
        "Call a release: compute the go/no-go from the hub rather than asserting it, state the bounds "
        "the verdict covers and what it does not, write release notes from what actually shipped, and "
        "record the operator's decision when they ship without a green. Use when the user asks whether "
        "something is ready to ship, or wants a go/no-go, release-readiness assessment or release "
        "notes. Not for testing the build - that is evidence:qa."),
    "requirements": (
        "Turn a PRD and stakeholder input into numbered requirements traceable to the PRD, map the real "
        "business process including its exceptions, capture the business rules, and route every conflict "
        "to the operator as a decision memo instead of picking one reading. Use when the user wants "
        "requirements elicited or documented, a business process mapped, business rules captured, a "
        "legacy system specified, or conflicting stakeholder input resolved. Not for stories with "
        "acceptance criteria - that is evidence:backlog."),
}

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    old = new = 0
    for name, desc in sorted(D.items()):
        path = os.path.join(ROOT, "skills", name, "SKILL.md")
        text = io.open(path, encoding="utf-8").read()
        m = re.search(r'(?<=\ndescription: ).*?(?=\n---\n)', text, re.S)
        if not m:
            raise SystemExit("no description in %s" % path)
        old += len(m.group(0).strip())
        new += len(desc)
        io.open(path, "w", encoding="utf-8", newline="\n").write(
            text[:m.start()] + desc + text[m.end():])
    print("descriptions: %d -> %d chars (%.1f%% smaller)" % (old, new, 100.0 * (old - new) / old))


if __name__ == "__main__":
    main()
