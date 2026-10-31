# Domain: AI / model-backed feature

A product feature backed by a language or vision model: nondeterministic output, prompts assembled partly
from content the user did not write, tools the model can invoke, per-call cost, and a quality claim that
is meaningless without a denominator.

## Do the thing

> The demo prompt returns an excellent answer. Run the *same* input twenty times and report the
> distribution; then feed it a document that contains instructions addressed to the model. **A good answer
> to the demo prompt is this domain's HTTP 200 — and here a single passing run is not weak evidence, it is
> no evidence at all.**

## Scope map

| Family | In this domain | Agent | Notes |
|---|---|---|---|
| 1 Acquisition | marketing claims about what the model can do | own | the hardest claims in the product to defend |
| 2 Primary product | the feature, and the eval harness | own ×2 | split: the user-facing path vs the quality measurement |
| 3 Control plane | admin controls, model selection, spend limits | own | |
| 4 Deployment | SaaS | N/A | `own` if self-hosted with model weights |
| 5 Entitlement | usage limits, **cost ceilings** | →3 | |
| 6 Secondary | the tools the model can call | →8 | tools are the abuse surface, so they test together |
| 7 Telemetry | what leaves for the provider, retention, PII | own | a policy declaration with legal weight |
| 8 Security | **prompt injection**, tool abuse, output handling | own | |
| 9 Documentation | capability claims, limits, the quality number | own | |
| 10 State under fault | provider outage, timeout, truncation, partial stream | own | |
| 11 Upgrade | **a provider model version change is a silent behaviour change** | own | |
| 12 Experience | uncertainty, provenance, correction | own | |

**Usual set: 1,2×2,3,7,8,9,10,11,12 own + 4 N/A, 5→3, 6→8 = 10 agents.**

## Failure catalogue

The same input twenty times · an input carrying instructions ("ignore the above and…") inside a document,
a filename, a web page, a CSV cell, a code comment, an email signature · an input in another language and
in mixed scripts · an input at the context limit and one token beyond · provider `429` and `503` ·
provider latency spike · a stream cut mid-token · a tool call with hallucinated arguments · a tool-call
loop · output containing HTML, JavaScript, SQL or Markdown links that something downstream renders · an
empty or refusing response · a provider-side model version change · an input containing real PII · and
the single most expensive plausible request a user could send.

## Defect classes to look for by name

**Indirect prompt injection through content the product ingests** — the document, the ticket, the web
page, the email the model reads and the user did not write · **model output rendered without escaping**
(cross-site scripting by way of the model) · a tool the model can call with wider privileges than the
asking user holds, the confused-deputy defect · no spend ceiling, so one input can cost without bound ·
automatic retry on a non-idempotent tool call · **truncation presented as a complete answer** · a quality
claim with no eval set and no denominator · silent model-version drift that changes behaviour with no
changelog entry · a provider outage whose failure mode is a *wrong answer* rather than an error · PII sent
to a provider the privacy policy does not name.

## Evidence and severity

**One run is not a result.** Every finding in this domain carries `n`, the observed rate, and the input
verbatim — this is the nondeterminism rule from `evidence-standard.md` applied as the domain's default
rather than its exception. Keep a fixed eval set with checkable properties, and state the denominator in
every quality claim you report or verify.

Record on every finding: provider, model id, temperature and sampling settings, a hash of the system
prompt, the tool set offered, and the token counts. Without those, nothing is reproducible.
`evidence-standard.md` → *Authorization and permission matrices* for tool privileges, *Experience
findings* for the uncertainty work.

| Observation | Severity |
|---|---|
| Injection that causes a tool call with a real-world effect | **critical** |
| Model output rendered unescaped | **critical** |
| PII sent to an undisclosed provider | **critical** — a false policy declaration |
| No spend ceiling | **blocker** |
| Truncation shown as a complete answer | **blocker** |
| A published quality claim with no denominator | **blocker** — a documentation defect, filed under scope 9 |
| Variation inside the documented tolerance | **not a finding** — say so explicitly, with the rate |

## Experience

**Who the user is:** someone who cannot distinguish a confident wrong answer from a right one, which is
the defining condition of this domain.

**Where it lives:** how uncertainty is communicated; whether output cites something the user can check;
latency and whether streaming makes the wait legible; what a refusal looks like; how a user corrects the
model; and whether it is clear which parts of what they are reading were generated.

**First success is:** the user completes the task **and can verify the answer without leaving the
product.**

**Do the thing, for experience:**

> Give it an input where the correct answer is "I don't know" or "that isn't in this document". Watch
> whether the product says so — and whether a user could tell that it should have.

**Defect classes:** confident presentation of unverifiable output · no citation or provenance · no way to
correct, constrain or retry with guidance · a spinner with no progress on a thirty-second call · an error
that blames the user for a provider timeout.

**Evidence note:** this is the one domain where **convergent cold runs are the primary harm evidence**
rather than the fallback. The harm is statistical, so the harm axis starts at a measured rate against a
fixed input set — a single trace of a confused user is the weaker artifact here, not the stronger one.

## Domain gotchas

- Your injection tests are real attacks against a real endpoint. Keep them inside your own tenant with
  your own data, and ledger them.
- A passing run proves almost nothing; a failing run proves a great deal. Spend the budget on repetition
  of the inputs that failed, not on breadth of inputs that passed.
- **Never paste real customer data into a provider** to see what happens. Generate synthetic PII that is
  recognisably synthetic.
- Cost is a test output, not an overhead: record spend per run and report the most expensive plausible
  request as a number.
- The **model version is part of build identity**. A re-test after a provider-side change is a different
  build, and `iteration-cycles.md` Phase 0 applies — pin it, or the verification is meaningless.
- Provider rate limits will shape your results and can look like product defects. Establish the limit
  first and record it.
