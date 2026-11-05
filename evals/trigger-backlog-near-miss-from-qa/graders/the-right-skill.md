---
type: tool_used
tool: Skill
input_match: '"skill"\s*:\s*"(?:[\w-]+:)?backlog"'
min: 1
weight: 2
---

The work must route to `evidence:backlog`. Deterministic: this matches the actual Skill
tool call in the trace, including the namespaced form. The earlier version asked an llm
judge to infer the tool call from the response prose, which voted FAIL on runs whose
traces prove the right skill fired -- the product reporting on itself, which this
method's own principle 3 rejects as an oracle.
