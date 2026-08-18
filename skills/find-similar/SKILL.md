---
name: find-similar
description: Find similar Rust spec references in the codebase based on the target function's signature and preceding documentation comments. Use when generating or reviewing specs and looking for related spec patterns.
argument-hint: [function_name] [file_path] [line_number] [n]
allowed-tools: [Read, Grep, Glob]
model: inherit
---

## Input Parameters

- `function_name`: Target function name
- `file_path`: Absolute or relative path to the file
- `line_number`: Line number of the function
- `n`: Number of similar results to find (default: 3)

## Execution Steps

### Step 1: Extract Target Function Information

1. Read the file at `file_path`
2. Find the function starting at or near `line_number`
3. Extract:
   - **Comments**: All comments immediately before the function (doc comments `///`, `//!`, block comments `/* */`)
   - **Function signature**: The function declaration line (fn name + parameters + return type), without the body

### Step 2: Build Search Query

Combine the extracted text into a single search query:
```
{comments}
{function_signature}
```

### Step 3: Search for Similar Spec References

Search the codebase for functions that already have specifications and can serve as spec references for the target function based on:
- Function signatures
- Documented comments

### Step 4: Rank and Select Top N

Use similarity matching to rank results and select the top N most useful spec references.

### Step 5: Extract Helper Functions/Macros

For each selected spec reference:
1. Output its location (file path and line number)
2. Extract its comments, Kani specs, and function signature
3. For Kani specs, identify all non-Kani helper functions and helper macros used by the specs, then recursively extract any helper functions or macros they call or expand to until the dependency set is complete, making the result self-contained for reference.

## Output

See `./template.md` for the output format. No explanations.