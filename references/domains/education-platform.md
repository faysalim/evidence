# Domain: education platform / LMS

Courses and cohorts, assignments and submissions, assessment and the gradebook, accommodations, roster
integration with a student information system, and an export whose last hop is somebody's permanent
record.

## Do the thing

> The gradebook shows 87%. Recompute it by hand from the submissions — with the late penalty, the
> drop-lowest rule, the excused item, the weighted categories and the extra credit — and see whether you
> get 87%. Then submit one second before the deadline from a different timezone. **A gradebook that
> renders is this domain's HTTP 200, and the grade is the product.**

## Scope map

| Family | In this domain | Agent | Notes |
|---|---|---|---|
| 1 Acquisition | catalog, enrolment, institutional trial | →2 | for institutional products the funnel is procurement, not self-serve |
| 2 Primary product | the learner: find, do, submit | own | |
| 3 Control plane | instructor tools, **gradebook**, roster, sections | own ×2 | split: gradebook arithmetic vs roster, sections and permissions |
| 4 Deployment | self-hosted install | own | `N/A` if SaaS only |
| 5 Entitlement | seats, institutional licence, course access windows | →3 | |
| 6 Secondary | **LTI / SIS integration**, mobile, proctoring vendor | own | |
| 7 Telemetry and privacy | student records, learning analytics, third-party processors | own | regulated data, and a contractual claim to the institution |
| 8 Security | role matrix, cross-section leakage, exam integrity | own | |
| 9 Documentation | **the accessibility conformance statement**, grading policy, integration guide | own | a VPAT is a procurement gate, so it is a claim with a price |
| 10 State under fault | timed exam under connection loss, deadline boundary, concurrent grading | own | |
| 11 Upgrade | **term rollover**, course copy, archive, grade export to the SIS | own | |
| 12 Experience | accessibility, the learner at 11pm, the instructor with 200 submissions | own | |

**Usual set: 2,3×2,6,7,8,9,10,11,12 own + 1→2, 4 N/A, 5→3 = 10 agents.**

## Failure catalogue

A submission one second before and one second after the deadline · the same submission from another
timezone, and across a DST change · a learner enrolled in two sections · a dropped learner's existing
grades · an assignment's rubric or point total edited **after** submissions exist · a randomized question
pool · a timed exam with the connection cut at minute 40 of 60 · an accommodation (1.5× time, alternate
format) applied mid-attempt · an LTI launch carrying a stale roster · an SIS sync where a student id
changed · term rollover and course copy · a bulk grade import with a malformed row · two teaching
assistants grading the same submission at once · a proctoring flag raised on a false positive · a guardian
account opened against the wrong child.

## Defect classes to look for by name

**Gradebook arithmetic wrong under a combination of rules** — late penalty × drop-lowest × weighted
categories × excused is where it breaks, never a single rule alone · **a deadline evaluated in server
time**, so a learner in another zone is marked late for work submitted early · **a timed exam that loses
the attempt** on disconnect, or restarts the clock, or fails to stop it · **an accommodation not
honoured**, which fails precisely the learner who most needs it · roster drift between the SIS and the
platform, so a grade lands on the wrong student id · cross-section or cross-course leakage — another
learner's submission visible, or a whole cohort's grades in one export · **an academic-integrity flag
presented as certainty** rather than as a signal · a grade export that maps wrongly on the final,
irreversible hop · anonymous grading that is not anonymous (the name in the filename, the metadata, the
submission order) · randomized pools of unequal difficulty, so scores are not comparable · core content
that is inaccessible — notation as an image, video without captions, an untagged PDF.

## Evidence and severity

**Independent recomputation is the oracle.** Build the expected gradebook in a spreadsheet from the
submissions and the published rules, then diff. A gradebook graded against itself is the self-report
failure, and here the self-report is the deliverable.

Record per run: the full rule set in force, the timezone of every actor, the term, and the section. Run the
role × action × object matrix **per section and per term**, not once. For accessibility, test with the
actual assistive technology — a linter pass belongs in `evidence-standard.md`'s list of evidence that
looks strong and is not.

`evidence-standard.md` → *Authorization and permission matrices*, *Stateful systems under fault* (the
exam-under-disconnect schedule), *Migrations, upgrades and restores* (term rollover and course copy are
migrations with grades in them).

| Observation | Severity |
|---|---|
| A wrong grade recorded or exported | **critical** — it is a permanent record |
| A timed exam losing a learner's work | **critical** |
| An accommodation not honoured | **critical**, with named legal exposure |
| An integrity flag shown as certainty | **critical** — it invites an irreversible accusation, and inherits that consequence |
| Another learner's submission or grades visible | **critical** |
| Deadline evaluated in the wrong timezone | **blocker** |
| Core content inaccessible to assistive technology | **blocker**, with named legal exposure |
| Anonymous grading leaking identity | **blocker** |

## Experience

**Who the user is:** the learner at 11pm on a slow connection before a deadline; the instructor grading
two hundred submissions; the learner using a screen reader, for whom accessibility is not a preference but
access; and the guardian.

**Where it lives:** finding the thing that is due; what a submission confirmation is worth; where feedback
went; bulk grading ergonomics; and whether the deadline is displayed in the learner's own timezone.

**First success is:** a learner finds the assignment, submits it, and holds a confirmation they can prove
with later.

**Do the thing, for experience:**

> Submit one minute before the deadline on a throttled connection, then prove from the product alone
> exactly what was submitted and when.

**Defect classes:** a confirmation that is not evidence — no receipt, no keepable timestamp, nothing to
show a registrar · a deadline shown in the wrong zone · an upload that fails silently at 99% · feedback
the learner cannot find · a progress bar that counts clicks rather than learning.

**Evidence note:** this domain has an experience measurement the others do not — **receipt-ability**. Can
the user prove what they did, to someone who will not take their word for it? It is a yes or no per flow,
not a taste, and in a dispute it is the only thing that matters.

## Domain gotchas

- **Never test against a live course.** One accidental grade write is a real academic consequence for a
  real person, and it is not reversible by apologising.
- Student records are regulated data. Refer to learners by role in every finding — never by name, email or
  id — the same rule the skill already applies to secrets.
- Terms and rollover produce a whole class of defects that exist only at a boundary occurring twice a
  year. **Create a fake past term** and roll it over deliberately.
- LTI and SIS integration need a second system, and **its own misconfiguration will masquerade as a
  product bug** — prove the baseline launch and sync before filing anything, exactly as with federation in
  `identity-provider.md`.
- A proctoring vendor is a third-party processor with its own privacy posture and its own false-positive
  rate. That is family 7, and it is a claim the institution has signed.
- Timezones are not a detail in this domain, they are a defect class. Fix an actor in a non-server zone
  for the whole run rather than testing the zone as a special case.
