---
name: safety-requirement-extractor
description: Extracts rigorous safety requirements from a Rust function's preceding documentation comments. Use when producing atomic, traceable requirements for downstream Kani spec generation.
---

## Overview

This skill extracts safety requirements from the target function's preceding Rust doc comments. It enforces strict rules to produce atomic, traceable, and verifiable requirements suitable for downstream Kani spec generation. After extraction, it validates each requirement against the same rules.

## Workflow

### Step 1: Read Target Function Documentation
- Locate and read the function's **preceding** doc comment (`///` or `/**...*/`).
- Do NOT extract requirements from comments inside the function body, including implementation comments such as `// SAFETY:`.

### Step 2: Identify Safety-Relevant Sources
Consider only these sources:
- The target function's preceding doc comment
- Any explicit cross-references mentioned in that doc comment

From each allowed source, identify ONLY:
- `# Safety` and `# Panics` sections
- Behavioral statements about memory safety or runtime panics

For each cross-reference:
- Search the entire codebase to locate the referenced content, then read the referenced text before using it
- Do NOT infer content without reading the referenced text
- Do NOT follow references not explicitly invoked by the target function's preceding doc comment

### Step 3: Extract Requirements
- Generate safety requirements from the sources identified in Steps 1-2, following rules R1-R7 in `rules.md`.

### Step 4: Validate Against R1-R7
- Validate each requirement against R1-R7.

## Output Format

```
## Safety Requirements for `<function_name>`

### RQ-<N>: 
<requirement sentence>. [TF-Safety: <cited statement>]
```

## Examples

See `examples.md`.

## Critical

The extraction MUST satisfy all rules in `rules.md`.