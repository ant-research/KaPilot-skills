# Kani Spec Generation Report

## Target Function
- Function: {{target_func_name}}
- File: {{file_path}}
- Line: {{line_num}}
- Result Folder: {{result_fldr}}

## Execution Summary
- Final verification status: {{final_verification_status}}
- Total verify rounds: {{total_verify_rounds}}
- Total precheck rounds: {{total_precheck_rounds}}
- Final verification target: {{final_verification_target}}

## Execution Details
Record each subagent and skill result below in the exact order they were executed at runtime.

### Step {{step_index}}: {{executor_name}}
- Kind: {{subagent_or_skill}}
- Round: {{verify_round_and_precheck_round_or_na}}
- Status: {{executed_or_skipped}}
- Result:

```text
{{verbatim_result}}
```

## Final Artifacts
### Safety Requirements
{{final_safety_requirements}}

### Final Verification Artifacts
{{final_verification_artifacts}}

### Final Target Function Code
{{final_target_function_code}}

### Final Harnesses
{{final_harnesses_code}}

## Verification Status
{{final_verification_details}}
