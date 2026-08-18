---
name: kani-spec-verify
description: Deprecated compatibility wrapper. Prefer kani-spec-insert followed by kani-spec-run.
model: haiku
tools: [Read, Grep, Glob]
color: red
---

This agent has been split into two focused subagents:
- `kani-spec-insert`
- `kani-spec-run`

Use `kani-spec-insert` to perform source-file and harness insertion.
Use `kani-spec-run` to run `verify-spec` and analyze the result.

Do not use `kani-spec-verify` in new workflows.

If maintaining an older workflow that still references this agent, update it to:
1. run `kani-spec-insert`
2. if insertion succeeds, run `kani-spec-run`