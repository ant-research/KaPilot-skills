# 原文逐段对读

以空行分段，共 49 段。下表逐段给出产物落点；标题行也纳入统计。

| 段 | 原文开头 | 产物落点 |
| --- | --- | --- |
| 1 | --- | 头部 Goal、Inputs；宿主元数据的排除见研判点 |
| 2 | target function name: $0 | Inputs 四项 |
| 3 | # Task | Goal |
| 4 | Generate Kani formal verification specifications for function $0 in $1 at line $2, us | 步骤 2、3、5 和五个独立角色知识文件 |
| 5 | First, run kani-harness-generator to generate the proof harnesses. | 步骤 2 先于步骤 5 |
| 6 | Produce a final report after the workflow completes. | 步骤 6–8 |
| 7 | # Preparation | 步骤 1 |
| 8 | bash | 步骤 1.1 和原始目录脚本 |
| 9 | - $1, $2, $3 are skill arguments (file path, line number, save_dir_root) | Inputs |
| 10 | 2. Write result_fldr to $(pwd)/.claude/.env for script compatibility: | 步骤 1.1、8 |
| 11 | bash | 步骤 1.1、8，兼容文件策略保持覆盖并留备份 |
| 12 | 3. Pass result_fldr explicitly to downstream subagents that need the result folder pa | 步骤 1.1 的 result_fldr 和下游输入 |
| 13 | - Pass the generated result_fldr to downstream subagents as the result_fldr input. | 各阶段显式输入及文件态配置桥接 |
| 14 | # Workflow | 步骤 5 |
| 15 | ## Workflow Logic | Constraints 和步骤 5 |
| 16 | 1. Assume Preparation is already complete. | 步骤 1–5 的顺序与分支 |
| 17 | ## Workflow Pseudocode | 步骤 5 的结构化流程 |
| 18 | text | 验证目标包接口及步骤 5.9–5.10 的插入前提 |
| 19 | harness_name_list = run kani-harness-generator(target_func_name, file_path, line_numb | 步骤 2 |
| 20 | if exists(<result_fldr>/safety-req.md): | 步骤 3 缓存分支 |
| 21 | verify_round = 0 | 步骤 4 |
| 22 | MAX_PRECHECK_ROUNDS = 2 | 步骤 4、5、5.3 |
| 23 | while verify_round < MAX_VERIFY_ROUNDS: | 步骤 5 外层循环 |
| 24 |    if verify_round == 0: | 步骤 5.1 的失败反馈输入 |
| 25 |    precheck_round = 0 | 步骤 5.3 内层循环 |
| 26 |       precheck_result = run kani-spec-precheck(current_spec, safety_requirements) | 步骤 5.3.1、5.3.3 |
| 27 |       if best_avg_score is unset or avg_score > best_avg_score: | 步骤 5.3.3 严格更高才更新最佳候选 |
| 28 |       if avg_score >= 6: | 步骤 5.3.3、5.3.4.1 达标结束预检 |
| 29 |       precheck_round = precheck_round + 1 | 步骤 5.3 固定两次迭代 |
| 30 |       if precheck_round < MAX_PRECHECK_ROUNDS: | 步骤 5.3.4.2 只在第一次后重新生成 |
| 31 |    if verification_target is None: | 步骤 5.4 的未达标条件 |
| 32 |       if some low_score_requirements should be expressed in harnesses rather than fun | 步骤 5.4.1.2 和 5.4.1.3.1.1 |
| 33 |          mixed_precheck_result = run kani-spec-precheck( | 步骤 5.4.1.3.1.3 使用最佳候选及显式入口编码 |
| 34 |          if mixed_avg_score > best_avg_score: | 步骤 5.4.1.3.1.5 只更新混合更高分 |
| 35 |          if mixed_avg_score >= 6: | 步骤 5.4.1.3.1.5 混合达到 6 时选择完整目标 |
| 36 |       if verification_target is None: | 步骤 5.5 必须回退最佳规格继续 |
| 37 |    insert_result = run kani-spec-insert( | 步骤 5.6–5.7 实际插入和七项清单 |
| 38 |    if insert_result is Insert Failed: | 步骤 5.8 插入失败反馈和 continue |
| 39 |    verify_result = run kani-spec-run( | 步骤 5.9–5.10 实际验证 |
| 40 |    if verify_result is Verify Success: | 步骤 5.11–5.12 成功立即结束外层循环 |
| 41 |    verify_round = verify_round + 1 | 步骤 5.2 的轮次递增 |
| 42 | output last_failure_result | 步骤 6.1–6.2 保存并呈现最后失败原文 |
| 43 | # Output | Outputs、步骤 6–8 |
| 44 | 1. Create a final report after the workflow completes. Save it as ${result_fldr}/exec | 步骤 6.2、原始 templates/report.md |
| 45 | 2. Using the template at templates/spec.md relative to this skill directory, write th | 步骤 6.2、原始 templates/spec.md、步骤 8 |
| 46 | # Constraints | Constraints |
| 47 | - **ABSOLUTELY NO GIT COMMANDS** in this workflow | Constraints 第一条，全部命令均无 Git |
| 48 | # Common Mistakes | Constraints 和步骤 5 各门禁 |
| 49 | \| Mistake \| Fix \| | 低分验证、混合再预检、即时展示、成功停止和禁 Git 的显式规则 |
