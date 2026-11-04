---
type: llm
weight: 1
---

The work must be routed to `product-suite:qa`, and not to a neighbouring skill. Judge from what the response actually does and names.

KNOWN WEAKNESS: this grader reads the response prose, so it is weak evidence for which tool fired. The deterministic half is the sibling grader; see evals/README.md.
