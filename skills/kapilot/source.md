---
name: kapilot
description: Generate Kani specs for a Rust function with ordered subagent execution, retry loops, and strict reporting
argument-hint: "[target_func_name] [file_path] [line_number] [save_dir_root]"
disable-model-invocation: true
---

target function name: $0
file path: $1
line number: $2
save_dir_root: $3

# Task

Generate Kani formal verification specifications for function `$0` in `$1` at line `$2`, using the following subagents:
- `kani-harness-generator`
- `kani-spec-generation`
- `kani-spec-precheck`
- `kani-spec-insert`
- `kani-spec-run`
and skill:
- `safety-requirement-extractor`

First, run `kani-harness-generator` to generate the proof harnesses.
Then run the pipeline consisting of `kani-spec-generation`, `kani-spec-precheck`, `kani-spec-insert`, and `kani-spec-run` to produce Kani specifications.

Produce a final report after the workflow completes.

# Preparation
1. Create `result_fldr` by executing the following command to store intermediate and final results:

```bash
result_fldr=$(scripts/mk-result-dir.sh "$(realpath "$1")" "$2" "$3")
```

- `$1`, `$2`, `$3` are skill arguments (`file path`, `line number`, `save_dir_root`)

2. Write `result_fldr` to `$(pwd)/.claude/.env` for script compatibility:

```bash
echo "RESULT_FLDR=$result_fldr" > $(pwd)/.claude/.env
```

3. Pass `result_fldr` explicitly to downstream subagents that need the result folder path.

- Pass the generated `result_fldr` to downstream subagents as the `result_fldr` input.
- Keep `$(pwd)/.claude/.env` only as compatibility support for scripts that load `RESULT_FLDR` directly.


# Workflow

## Workflow Logic
The pseudocode below is authoritative for control flow. Use the following prose only as a rule summary:

1. Assume Preparation is already complete.
2. Cache safety requirements in `<result_fldr>/safety-req.md` and reuse them across all rounds.
3. In each `verify_round`, generate an initial spec candidate and run up to 2 precheck rounds, tracking the highest-scoring spec as `best_spec_candidate`.
4. If no candidate reaches average score `>= 6`, inspect the low-score requirements and optionally revise the harnesses, then run one mixed-mode precheck on `best_spec_candidate`.
5. Build a `verification_target` bundle for verification. It always includes the selected spec candidate, and may additionally include harness-side safety requirement encodings.
6. Insert the selected target into the source file and harnesses before running verification.
7. Run verification on the inserted target, stop immediately on `Verify Success`, and otherwise continue until 2 `verify_round`s are exhausted.

## Workflow Pseudocode

```text
# Preconditions:
# - result_fldr already exists
#
# Conventions:
# - verification_target passed to kani-spec-insert is a bundle containing:
#   - safety requirements
#   - selected preconditions and postconditions
#   - selected loop invariants, if any
#   - selected auxiliary verification code, if any
#   - selected harness-side safety requirement encodings, if any
# - kani-spec-run verifies the current workspace state after kani-spec-insert completes

harness_name_list = run kani-harness-generator(target_func_name, file_path, line_number)

if exists(<result_fldr>/safety-req.md):
   safety_requirements = read <result_fldr>/safety-req.md
else:
   safety_requirements = call skill: /safety-requirement-extractor target_func_name file_path line_number
   save safety_requirements to <result_fldr>/safety-req.md

verify_round = 0
last_failure_result = None

MAX_PRECHECK_ROUNDS = 2
MAX_VERIFY_ROUNDS = 2

while verify_round < MAX_VERIFY_ROUNDS:

   if verify_round == 0:
      current_spec = run kani-spec-generation(target_func_name, file_path, result_fldr, safety_requirements)
   else:
      current_spec = run kani-spec-generation(target_func_name, file_path, result_fldr, safety_requirements, feedback = last_failure_result)
   best_avg_score = unset
   best_spec_candidate = current_spec
   verification_target = None

   precheck_round = 0
   while precheck_round < MAX_PRECHECK_ROUNDS:

      precheck_result = run kani-spec-precheck(current_spec, safety_requirements)
      avg_score = arithmetic_mean(precheck_result[*].score)

      if best_avg_score is unset or avg_score > best_avg_score:
         best_avg_score = avg_score
         best_spec_candidate = current_spec

      if avg_score >= 6:
         verification_target = bundle(current_spec)
         break

      precheck_round = precheck_round + 1

      if precheck_round < MAX_PRECHECK_ROUNDS:
         current_spec = run kani-spec-generation(
            target_func_name,
            file_path,
            result_fldr,
            safety_requirements,
            feedback = precheck_result,
         )

   if verification_target is None:
      low_score_requirements = requirements_with_low_scores(precheck_result)

      if some low_score_requirements should be expressed in harnesses rather than function specs:
         revise harnesses accordingly
         harness_side_encodings = summarize harness-side encodings

         mixed_precheck_result = run kani-spec-precheck(
            best_spec_candidate,
            safety_requirements,
            harness_side_encodings,
         )
         mixed_avg_score = arithmetic_mean(mixed_precheck_result[*].score)

         if mixed_avg_score > best_avg_score:
            best_avg_score = mixed_avg_score

         if mixed_avg_score >= 6:
            verification_target = bundle(best_spec_candidate, harness_side_encodings)

      if verification_target is None:
         verification_target = bundle(best_spec_candidate)

   insert_result = run kani-spec-insert(
      target_func_name,
      file_path,
      line_number,
      verification_target,
      harness_name_list,
   )

   if insert_result is Insert Failed:
      last_failure_result = insert_result
      verify_round = verify_round + 1
      continue

   verify_result = run kani-spec-run(
      target_func_name,
      file_path,
      line_number,
      harness_name_list,
   )

   if verify_result is Verify Success:
      stop workflow and produce final success report
   else:
      last_failure_result = verify_result

   verify_round = verify_round + 1

output last_failure_result
```


# Output

1. Create a final report after the workflow completes. Save it as `${result_fldr}/execution_report.md`, using the template at `templates/report.md` relative to this skill directory.
   - In `Execution Details`, record every executed subagent and skill result in the exact runtime order.
   - Include loop round information for entries produced inside the workflow loops.

2. Using the template at `templates/spec.md` relative to this skill directory, write the final verification artifacts and final target function code to the file `${result_fldr}/success` or `${result_fldr}/fail`, depending on the final verification result.

# Constraints

- **ABSOLUTELY NO GIT COMMANDS** in this workflow

# Common Mistakes

| Mistake | Fix |
|---------|-----|
| Skipping verify when precheck stays `< 6` | Still run verification after precheck loop ends |
| Revising harnesses without re-running mixed-mode precheck | If safety requirements are intentionally encoded in harnesses, re-run `kani-spec-precheck` with those harness encodings included |
| Not displaying subagent results immediately | Show each result right after execution |
| Continuing after `Verify Success` | Stop entire workflow immediately |
| Using git commands | Never use git in this workflow |
