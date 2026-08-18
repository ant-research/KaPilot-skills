---
name: verify-spec
description: Run Kani verification on generated specs and analyze results. Use when verifying Kani proof harnesses after spec generation, checking for syntax errors in generated specifications, or analyzing verification failures and counterexamples.
---

## Overview

This skill runs Kani verification on generated specs and analyzes the results. It checks for syntax errors, parses verification results (failed checks, counterexamples), and reports success or detailed failure messages.

## Usage

Run the verification script with:

```bash
python scripts/verify-spec.py --harnesses <harness_name_list>
```

Where:
- `<harness_name_list>`: Comma-separated list of harness names to verify

An example:
```bash
python scripts/verify-spec.py --harnesses harness_from_raw_i32,harness_from_raw_u8
```

## Output Format
Directly print out the output of the script. 
