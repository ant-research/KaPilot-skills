---
name: kani-compile
description: Run Kani on specific harnesses and analyze results. Use when checking the generated harnesses are syntactically correct, checking for syntax errors occurred in the harnesses.
allowed-tools:
  - Bash(python3:*)
---

## Usage

```bash
python3 scripts/kani-compile.py --harnesses <harness_name_list>
```

Where:
- `<harness_name_list>`: Comma-separated list of harness names to verify

E.g.:
```bash
python3 scripts/kani-compile.py --harnesses harness_from_raw_i32,harness_from_raw_u8
```

## Output Format
Directly print out the output of the script. 
