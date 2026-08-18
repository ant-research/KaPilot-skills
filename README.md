## Overview

KaPilot is an LLM-assisted tool for generating Kani specifications for **unsafe Rust** verification. The technical details are described in our ISSTA 2026 paper, ["KaPilot: LLM-Assisted Generation of Kani Specifications for Unsafe Rust Verification"](https://arxiv.org/abs/2607.21957).


This repository provides `KaPilot-skills`: a Claude Code CLI implementation of KaPilot's multi-agent workflow. It turns the agents, prompts, and supporting utilities from KaPilot into reusable Claude Code sub-agents and skills.

The main sub-agents live under `claude/agents`: `kani-harness-generator`, `kani-spec-generation`, `kani-spec-precheck`, `kani-spec-insert`, and `kani-spec-run`. They cover the full path from harness generation to final verification. In between, they generate candidate specifications, precheck their quality, insert the selected artifacts into the source code, and run Kani.

Supporting skills are kept under `claude/skills`. These skills handle focused pieces of the workflow, such as extracting safety requirements, writing Kani specifications, constructing nondeterministic values, and compiling or verifying generated artifacts.


## Preparation
1. Install Kani
```sh
cargo install --locked kani-verifier --version 0.65.0
cargo kani setup
```

2. Install Claude Code
```sh
curl -fsSL https://claude.ai/install.sh | bash
```

## Execution Steps

1. Go to the target codebase and link the KaPilot Claude configuration directory:

```sh
ln -s <path-to-kapilot-skills>/claude .claude
```

2. Find the target Rust function and add a temporary fake precondition before it:

```rust
#[kani::requires(true)] // fake
```

3. Record the target function name, file path, and line number.

4. Start `claude` from the target codebase, then run:

```
/kapilot <target_func_name> <file_path> <line_number> <result_folder>
```

Example:

```
/kapilot from_raw library/alloc/src/rc.rs 1337 temp_results
```

## Results

Intermediate artifacts are written to:

```text
<result_folder>/<spec-rust-file>/<line_number>/<timestamp>/
```

After the workflow completes, the generated specification is inserted into `<file_path>`.



## Citation
If you use KaPilot in your research, please cite our paper:
```
@misc{wang2026kapilotllmassistedgenerationkani,
      title={KaPilot: LLM-Assisted Generation of Kani Specifications for Unsafe Rust Verification}, 
      author={Minghua Wang and Yuxi Ling and Mingzhi Gao and Yuwei Liu and Lin Huang},
      year={2026},
      eprint={2607.21957},
      archivePrefix={arXiv},
      primaryClass={cs.SE},
      url={https://arxiv.org/abs/2607.21957}, 
}
```