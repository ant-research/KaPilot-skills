## Overview

KaPilot is an LLM-assisted tool for generating Kani specifications for **unsafe Rust** verification. The technical details are described in our ISSTA 2026 paper, ["KaPilot: LLM-Assisted Generation of Kani Specifications for Unsafe Rust Verification"](https://dl.acm.org/doi/10.1145/3832239).


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
@article{10.1145/3832239,
author = {Wang, Minghua and Ling, Yuxi and Gao, Mingzhi and Liu, Yuwei and Huang, Lin},
title = {KaPilot: LLM-Assisted Generation of Kani Specifications for Unsafe Rust Verification},
year = {2026},
issue_date = {October 2026},
publisher = {Association for Computing Machinery},
address = {New York, NY, USA},
volume = {3},
number = {ISSTA},
url = {https://doi.org/10.1145/3832239},
doi = {10.1145/3832239},
abstract = {Rust’s ownership and type system provide strong memory safety guarantees, but unsafe code still presents memory safety risks. Formal verification is crucial for ensuring memory safety, but writing precise specifications for unsafe Rust is challenging and largely manual. Large language models (LLMs) have shown promise in generating formal specifications but are often code-centric, prone to inheriting implementation flaws, and lack systematic quality assessment.    In this paper, we present KaPilot, a multi-agent framework for automatically generating specifications to verify unsafe Rust memory safety using Kani. The process begins with lightweight program analysis and proof harness generation. The SafetyReq agent extracts a concise, refined list of safety requirements from the target Rust function’s documentation, which guides the SpecGen agent in producing initial specifications that specify memory safety concerns. Then, the specifications are iteratively refined through a generate–precheck–verify loop involving SpecGenerate, SpecPrecheck, and SpecVerify agents, which assess quality and feed errors back. By executing this loop multiple times, KaPilot generates a set of candidate specifications. Finally, the shuffle-and-implication strategy is applied to systematically determine the best specification from these candidates. We evaluated KaPilot on 54 unsafe Rust functions with ground truth and 44 without. KaPilot achieved 88.9\% and 69.2\% specification generation success, respectively, with 57.4\% of generated specifications equivalent to or stronger than the ground truth. Compared with AutoSpec, KaPilot produces 14.8\% more verifiable specifications and 25.9\% more equivalent-or-better specifications.},
journal = {Proc. ACM Softw. Eng.},
month = oct,
articleno = {ISSTA148},
numpages = {22},
keywords = {LLM, Memory Safety, Specification Generation, Unsafe Rust Verification}
}
```
