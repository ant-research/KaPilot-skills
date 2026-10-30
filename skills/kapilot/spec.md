# Spec: KaPilot Kani 规格生成与验证
Id: kapilot_commit
Goal: 为指定 Rust 函数生成 Kani 验证产物，按原流程尝试验证，并发布最终源码、执行报告和 success 或 fail 文件。

## Inputs
- target_func_name % line  # 目标 Rust 函数的名称。
- file_path % line  # 目标源文件相对运行工作区的路径，不得包含 ..。
- line_number % int  # 目标函数在原始文件中的起始行号，必须大于零。
- save_dir_root % line  # 结果保存根目录，相对运行工作区的路径，可以为点号；缺失时在隔离副本创建。

## Outputs
- report_path % line  # 已发布的 execution_report.md 的工作区相对路径。
- artifact_path % line  # 已发布的 success 或 fail 文件的工作区相对路径。

## Constraints
- 整个工作流绝对禁止执行任何 Git 命令，包括只读命令。
- 必须先生成并编译证明入口，再提取或复用安全要求，再按生成、预检、插入、验证的顺序执行。
- 安全要求只提取一次并缓存为 safety-req.md，所有验证轮必须复用同一份要求。
- 最多执行两轮验证；每轮最多执行两次规格预检。分数不足 6 时仍必须选择最高分候选进行插入和验证，不得因为低分跳过验证。
- 如果有意把安全要求编码进证明入口，必须先对最高分候选和这些入口编码执行一次混合模式预检，不能直接验证。
- 一旦实际验证返回 Verify Success，必须立即退出整个验证循环；只能继续生成和发布最终报告。
- 每个已执行阶段或内部技能完成后，必须立即展示其 result_text 原文，并按实际执行顺序记录，循环内的记录必须含验证轮和预检轮信息。
- 所有生成、插入、修正和运行命令必须使用同一个 work_zone 内的隔离项目副本。不得在探索步骤写正式源文件、正式结果目录或正式兼容配置。
- 最终发布前必须核对所有源码改动只作用于允许的验证区域，原始实现行为不得改变。
- 五个执行角色的业务规则由对应步骤注入。文档中的技能名和示例脚本调用表示业务方法，实际命令只由本流程带 body 的步骤执行，不依赖任何宿主角色启动机制。
- 验证阶段禁止修改源文件；遇到语法或语义问题必须将真实错误反馈给下一验证轮的生成阶段。这是对原文冲突采用更严格禁止条款的暂定处置。

## Tools

## Config
engine_min_version: 0.20.0
requires_commands: [python3]

## Steps
1. [subtask retry=0] 校验输入并建立隔离项目和结果目录。
  + → preparation % yaml  # 隔离项目、结果目录和准备命令的回执。
  + → job_path % line  # work_zone 内的运行配置 JSON 路径。
  + → staged_file_path % line  # 隔离项目内的目标源文件绝对路径。
  + → result_fldr % line  # 隔离项目内供各阶段使用的结果目录绝对路径。
  + → original_source % text  # 正式源文件在开始执行时的完整原文。
  + → execution_log % [yaml]  # 按实际执行顺序记录的原始阶段结果。
  1.1. [act] 复制项目并执行原始结果目录脚本和兼容配置写入。
    - ← target_func_name, file_path, line_number, save_dir_root
    + → preparation % yaml  # 准备脚本返回的结构化回执，失败时含 error 字段。
    + → preparation_command % yaml  # 准备命令的退出码和原始标准输出、错误输出。
    + → job_path % line  # 后续脚本共同读取的运行配置路径。
    + → staged_file_path % line  # 各代码阶段共同加工的隔离源文件路径。
    + → result_fldr % line  # 已创建的隔离结果目录路径。
    + → writing_reference_dir % line  # 包内四类 Kani 写作参考文件的绝对目录。
    + → original_source % text  # 目标源文件的开始状态，供最终改动核对使用。
    + → execution_log % [yaml]  # 初始为空的执行记录。
    > Python 桥接脚本只向 work_zone 复制和写入。结果目录的原始命名规则由 scripts/mk-result-dir.sh 保留，兼容文件为隔离项目的 .claude/.env，RESULT_FLDR 显式传给后续命令。
    > ```hop_python
    > job_path = work_zone_path("job.json")
    > request_data = {"workspace_dir": hop_env_workspace_root, "target_func_name": target_func_name, "file_path": file_path, "line_number": line_number, "save_dir_root": save_dir_root, "scratch_root": work_zone_path("project"), "job_path": job_path}
    > preparation_command = subprocess.run(["python3", spec_dir("scripts/hop-support.py"), "prepare"], input: str(request_data), timeout: 180)
    > preparation = parse_json(preparation_command.stdout) if preparation_command.stdout else {"error": preparation_command.stderr}
    > staged_file_path = get(preparation, "staged_file_path", "")
    > result_fldr = get(preparation, "result_fldr", "")
    > original_source = read(path: file_path) if preparation_command.returncode == 0 else ""
    > writing_reference_dir = spec_dir("references/kani-spec-write/references")
    > execution_log = []
    > ```
  1.2. [check final] 准备成功且所有加工路径都位于本次隔离项目。
    - ← preparation, preparation_command, staged_file_path, result_fldr, original_source
    + → preparation_ok % bool  # 准备步骤是否可以继续。
    + → preparation_note % text  # 准备失败的真实原因。
    > ```hop_python
    > preparation_ok = preparation_command.returncode == 0 and len(staged_file_path) > 0 and len(result_fldr) > 0 and len(original_source) > 0
    > preparation_note = "准备成功" if preparation_ok else preparation_command.stdout + preparation_command.stderr
    > ```

2. [subtask retry=0] 生成证明入口并编译，只修正生成模块直到语法正确。
  + → harness_name_list % [line]  # 后续插入和验证必须使用的证明入口名称。
  + → harness_code % text  # 当前完整的 verify_<line_number> 模块代码。
  2.1. [act] 初始化入口编译反馈。
    + → compile_feedback % text  # 上一次入口编译的原始反馈，第一次为空。
    > ```hop_python
    > compile_feedback = ""
    > ```
  2.2. [loop max=20] 生成或修正证明入口并重新编译。
    2.2.1. [act free] 按真实函数类型生成或修正证明入口。
      - ← target_func_name, line_number, staged_file_path, result_fldr, original_source, preparation, compile_feedback
      + → harness_name_list % [line]  # 已生成的证明入口名称，至少一个。
      + → harness_code % text  # 完整证明模块代码。
      + → harness_result_text % text  # 函数分析、具体泛型实例及其选择理由、名称列表和完整入口代码。
      > 读取 staged_file_path 以及隔离项目内必要的定义。泛型先搜索真实使用实例，没有时选通常 1–3 个有代表性的类型；每种实例至少一个 #[kani::proof_for_contract(...)]。只追加一个 mod verify_<line_number>，已存在时仅替换该模块。不得修改目标函数或其它实现代码；不得加入 kani::assert()。必须使用 compile_feedback 修正上一轮语法问题；首次反馈为空。后续只允许修正该模块及模块内导入。此步不得运行编译命令，命令由下一步执行。
      > [[references/roles/kani-harness-generator#完整规则]]
      > [[references/kani-nondet-values-nostd/SKILL#完整规则]]
    2.2.2. [act] 记录入口结果并运行原始编译技能脚本。
      - ← job_path, harness_name_list, harness_result_text, execution_log
      + → compile_feedback % text  # 本次真实编译输出，必须传给下一次入口修正。
      + → compile_result % yaml  # 真实编译结果，含 successful、result_text 和命令原始输出。
      + → execution_log % [yaml]  # 已追加入口与编译技能结果的执行记录。
      > 命令只对隔离项目执行；脚本依赖的 RESULT_FLDR 从隔离兼容文件桥接，不依赖安装位置。
      > ```hop_python
      > execution_log = execution_log + [{"executor_name": "kani-harness-generator", "kind": "stage", "round": "准备阶段", "result_text": harness_result_text}]
      > compile_command = subprocess.run(["python3", spec_dir("scripts/hop-support.py"), "compile"], input: str({"job_path": job_path, "harness_name_list": harness_name_list}), timeout: 1800 * len(harness_name_list) + 120)
      > compile_result = parse_json(compile_command.stdout) if compile_command.stdout else {"successful": False, "result_text": compile_command.stderr}
      > compile_feedback = get(compile_result, "result_text", compile_command.stdout + compile_command.stderr)
      > execution_log = execution_log + [{"executor_name": "kani-compile", "kind": "skill", "round": "准备阶段", "result_text": get(compile_result, "result_text", compile_command.stdout + compile_command.stderr)}]
      > ```
    2.2.3. [branch] 语法正确时结束入口修正循环。
      2.2.3.1. [case(get(compile_result, "successful", False))] 所有生成入口已经编译。
        2.2.3.1.1. [break] 进入安全要求阶段。
  2.3. [check final] 入口非空且真实编译已经通过。
    - ← harness_name_list, harness_code, compile_result
    + → harness_ok % bool  # 入口阶段是否通过。
    + → harness_note % text  # 未通过的真实编译反馈。
    > ```hop_python
    > harness_ok = len(harness_name_list) > 0 and len(harness_code) > 0 and get(compile_result, "successful", False)
    > harness_note = "入口语法正确" if harness_ok else get(compile_result, "result_text", "编译命令未成功；不得继续生成规格")
    > ```

3. [subtask retry=0] 读取一次安全要求缓存，缺失时提取并核验后保存。
  + → safety_requirements % markdown  # 在所有验证轮复用的安全要求原文。
  + → requirement_items % [yaml]  # 安全要求列表，每项含 id、sentence 和 citation。
  3.1. [act] 探测缓存并读入已有安全要求。
    - ← result_fldr
    + → cache_present % bool  # 隔离结果目录中是否已经有 safety-req.md。
    + → cached_requirements % text  # 存在时逐字读入的缓存原文，否则为空。
    > ```hop_python
    > cache_present = parse_json(exists(path: result_fldr + "/safety-req.md")).exists
    > cached_requirements = read(path: result_fldr + "/safety-req.md") if cache_present else ""
    > ```
  3.2. [branch] 复用缓存或执行安全要求提取。
    + → safety_requirements % markdown  # 本次流程固定复用的安全要求。
    + → requirement_items % [yaml]  # 与安全要求原文一一对应的要求记录。
    3.2.1. [case(cache_present)] 不重新提取已有缓存。
      + → safety_requirements % markdown  # 未改写的缓存原文。
      + → requirement_items % [yaml]  # 从缓存读取的要求项。
      3.2.1.1. [act free] 保留缓存原文并识别其中的要求项。
        - ← cached_requirements
        + → safety_requirements % markdown  # 与 cached_requirements 逐字一致的内容。
        + → requirement_items % [yaml]  # 每项明确给出 id、sentence、citation，不引入新要求。
        > safety_requirements 必须保持 cached_requirements 原文不变。只解析其中明确列出的 RQ-<N> 条目，输出 id、sentence、citation 三个字段；不得按实现代码推导或扩充要求。
    3.2.2. [case(else)] 从允许的文档来源提取要求。
      + → safety_requirements % markdown  # 按提取技能格式输出的要求文档。
      + → requirement_items % [yaml]  # 已核验的原子要求列表。
      3.2.2.1. [subtask retry=2] 提取并逐条验证来源、原子性和完整性。
        3.2.2.1.1. [act free] 读取函数前置文档和明确引用，生成可追溯要求。
          - ← target_func_name, line_number, staged_file_path, preparation
          + → safety_requirements % markdown  # 按 Safety Requirements 和 RQ-<N> 格式编写的要求全文。
          + → requirement_items % [yaml]  # 每项含 id、sentence 和 citation。
          + → safety_evidence % [yaml]  # 实际读取的允许来源，每项含 path 和 content，含目标前置文档与其明确引用。
          > 只读取函数之前的 /// 或 /**...*/ 文档及它明确提到的引用；引用须在整个隔离项目内定位并实际读过。不得读取函数体内 // SAFETY: 作为提取来源，也不得跟随未被前置文档明确调用的引用。只提取 Safety、Panics 和内存安全或运行时 panic 相关行为。输出 requirement_items 的 id、sentence、citation 字段，以及实际读过的 safety_evidence 路径和文本。
          > [[references/safety-requirement-extractor/SKILL#完整规则]]
          > [[references/safety-requirement-extractor/rules#完整规则]]
          > [[references/safety-requirement-extractor/examples#完整规则]]
        3.2.2.1.2. [check final] 每条要求符合 R1–R7 且覆盖所有允许来源中的安全约束。
          - ← safety_requirements, requirement_items, safety_evidence
          + → safety_ok % bool  # 所有要求和来源是否符合提取规则。
          + → safety_note % text  # 一次列全不合格的要求、引用和遗漏。
          > 只对已提供的 safety_evidence 和要求判定，不读取文件。逐条核对单句单属性、目标接口变量、内存安全与 panic 范围、可定位的明确引用、范围和强度、无重复或蕴含或矛盾，以及允许来源完整覆盖。requirement_items 必须与文档中的 RQ 条目一一对应。空要求只在允许来源确实没有安全约束时通过，不得编造要求。
          > [[references/safety-requirement-extractor/rules#完整规则]]
      3.2.2.2. [act] 保存已核验的隔离缓存并记录提取结果。
        - ← result_fldr, safety_requirements, execution_log
        + → execution_log % [yaml]  # 已追加提取技能原文的执行记录。
        > ```hop_python
        > cache_written = write(path: result_fldr + "/safety-req.md", content: safety_requirements)
        > execution_log = execution_log + [{"executor_name": "safety-requirement-extractor", "kind": "skill", "round": "准备阶段", "result_text": safety_requirements}]
        > ```
  3.3. [check final] 两条来源路径都给出相同接口且缓存保持固定。
    - ← safety_requirements, requirement_items
    + → requirements_ready % bool  # 安全要求是否可以供后续评分逐条使用。
    + → requirements_note % text  # 要求列表接口缺口。
    > ```hop_python
    > requirements_ready = all([len(get(r, "id", "")) > 0 and len(get(r, "sentence", "")) > 0 and len(get(r, "citation", "")) > 0 for r in requirement_items])
    > requirements_note = "要求接口齐全；空列表仍需执行实际验证" if requirements_ready else "要求项必须逐个包含 id、sentence 和 citation"
    > ```

4. [act] 初始化原文规定的循环、计数和失败反馈。
  + → verification_iterations % [int]  # 固定为两次验证迭代。
  + → precheck_iterations % [int]  # 每轮固定为两次规格预检迭代。
  + → last_failure_result % yaml  # 上一验证轮的真实插入或验证失败反馈，初始为空。
  + → total_verify_rounds % int  # 实际执行的验证轮数。
  + → total_precheck_rounds % int  # 实际执行的规格预检和混合模式预检总次数。
  + → final_status % enum(success, fail)  # 最终状态，只有真实验证成功才赋 success。
  > ```hop_python
  > verification_iterations = [1, 2]
  > precheck_iterations = [1, 2]
  > last_failure_result = {}
  > total_verify_rounds = 0
  > total_precheck_rounds = 0
  > final_status = "fail"
  > ```

5. [loop for-each verification_iteration in verification_iterations] 最多执行两轮规格生成、选择、插入和验证。
  5.1. [act free] 从固定安全要求与上一轮真实失败反馈生成候选。
    - ← target_func_name, file_path, line_number, staged_file_path, preparation, result_fldr, safety_requirements, requirement_items, last_failure_result, verification_iteration, writing_reference_dir
    + → current_spec % yaml  # 候选，含 safety_requirements、preconditions、postconditions、loop_invariants、auxiliary_code 和 similar_references。
    + → generation_result_text % text  # 安全要求在前的完整原始生成结果及对反馈的修正说明。
    > 读取隔离项目相关定义并按生成角色规则产出原始验证片段，不修改实现逻辑。current_spec 必须包含 safety_requirements 文本、preconditions 与 postconditions 文本列表、loop_invariants 列表（每项含 loop_locator、code）、auxiliary_code 文本及 similar_references 文本；没有的类别用空列表或空文本。每个 requires/ensures 必须带显式 RQ 映射。第一轮没有失败反馈，第二轮必须使用 last_failure_result；保留仍正确的映射。相似规格查找可选，只作参考；相关写作文件以 writing_reference_dir 为绝对目录，按需要读取 pre-post-conditions.md、type-invariant.md、loop-invariant.md 或 mem-predicate.md。使用相似参考时把参考保存到隔离 result_fldr/similar-func-specs.md，并保持辅助依赖完整。不得运行命令。
    > [[references/roles/kani-spec-generation#完整规则]]
    > [[references/kani-spec-write/SKILL#完整规则]]
    > [[references/find-similar/SKILL#完整规则]]
    > [[references/find-similar/template#完整规则]]
  5.2. [act] 记录初始候选并重置本轮最佳候选和验证目标。
    - ← current_spec, generation_result_text, execution_log, verification_iteration, total_verify_rounds
    + → best_avg_score % float  # 本轮见过的最高平均分，初始为 -1。
    + → best_spec_candidate % yaml  # 与最高分绑定的完整候选，不能用最后一次候选替代。
    + → verification_target % yaml  # 选中的目标包，空对象表示尚未选择。
    + → harness_side_encodings % text  # 本轮为混合模式明确提供的证明入口编码摘要，初始为空。
    + → execution_log % [yaml]  # 已记录生成角色原文的执行记录。
    + → total_verify_rounds % int  # 已进入的验证轮总数。
    > ```hop_python
    > best_avg_score = -1.0
    > best_spec_candidate = current_spec
    > verification_target = {}
    > harness_side_encodings = ""
    > total_verify_rounds = total_verify_rounds + 1
    > execution_log = execution_log + [{"executor_name": "kani-spec-generation", "kind": "stage", "round": "verify=" + str(verification_iteration) + ", precheck=初始生成", "result_text": generation_result_text}]
    > ```
  5.3. [loop for-each precheck_iteration in precheck_iterations] 每轮最多预检两次，达到平均 6 分时立即结束。
    5.3.1. [act free] 仅评估显式映射的规格，每条安全要求输出一次评分。
      - ← current_spec, safety_requirements, requirement_items, verification_iteration, precheck_iteration
      + → precheck_result % [yaml]  # 完整评分列表，每项含 req、pre-conditions、harness-encodings、post-conditions、score、reason。
      + → precheck_result_text % text  # 原始 JSON 评分列表全文。
      > 采用规格模式，不提供证明入口编码。必须对 requirement_items 中每项恰好评分一次，score 是 0–10 的数值；只采信 requires/ensures 明确注释的 RQ 映射。不得把循环不变量、辅助代码或未标注的入口逻辑当作评分证据，不得修改或生成替代规格。空要求列表输出空列表。
      > [[references/roles/kani-spec-precheck#完整规则]]
    5.3.2. [subtask retry=0] 核对评分接口而不以通过分数阻断后续验证。
      5.3.2.1. [check final] 每条要求恰有一条合法评分。
        - ← precheck_result, requirement_items
        + → precheck_schema_ok % bool  # 评分接口是否完整合法，与分数是否达到 6 无关。
        + → precheck_schema_note % text  # 评分接口缺口。
        > ```hop_python
        > precheck_schema_ok = len(precheck_result) == len(requirement_items) and all([any([startswith(get(p, "req", ""), r.id + ":") for p in precheck_result]) for r in requirement_items]) and all([p.score >= 0 and p.score <= 10 and len(get(p, "reason", "")) > 0 for p in precheck_result])
        > precheck_schema_note = "每项均有合法评分；低分继续走回退路径" if precheck_schema_ok else "要求和评分必须一一对应，且分数在 0–10 范围内"
        > ```
    5.3.3. [act] 按算术平均更新最高分候选，并在达标时选当前候选。
      - ← precheck_result, current_spec, best_avg_score, best_spec_candidate, verification_target, execution_log, verification_iteration, precheck_iteration, precheck_result_text, total_precheck_rounds
      + → avg_score % float  # 本次评分的算术平均；没有要求时暂定为 0。
      + → best_avg_score % float  # 严格大于旧最高分时才更新。
      + → best_spec_candidate % yaml  # 保留首个同分候选的最佳候选。
      + → verification_target % yaml  # 达标时选当前规格，未达标时仍为空。
      + → execution_log % [yaml]  # 已记录当前预检原文的执行记录。
      + → total_precheck_rounds % int  # 真实预检调用总数。
      > ```hop_python
      > avg_score = sum([p.score for p in precheck_result]) / len(precheck_result) if precheck_result else 0.0
      > best_spec_candidate = current_spec if avg_score > best_avg_score else best_spec_candidate
      > best_avg_score = avg_score if avg_score > best_avg_score else best_avg_score
      > verification_target = {"spec": current_spec, "safety_requirements": current_spec.safety_requirements, "harness_side_encodings": ""} if avg_score >= 6 else verification_target
      > total_precheck_rounds = total_precheck_rounds + 1
      > execution_log = execution_log + [{"executor_name": "kani-spec-precheck", "kind": "stage", "round": "verify=" + str(verification_iteration) + ", precheck=" + str(precheck_iteration), "result_text": precheck_result_text}]
      > ```
    5.3.4. [branch] 已达标立即结束，否则仅在第一次预检后再生成候选。
      5.3.4.1. [case(verification_target)] 当前候选已达到平均 6 分。
        5.3.4.1.1. [break] 不执行多余的预检或重新生成。
      5.3.4.2. [case(precheck_iteration == 1)] 使用当前预检反馈进行第二次候选生成。
        5.3.4.2.1. [act free] 根据评分反馈只修正需要改变的规格。
          - ← target_func_name, staged_file_path, preparation, result_fldr, safety_requirements, requirement_items, current_spec, precheck_result, writing_reference_dir
          + → current_spec % yaml  # 与初始生成相同字段接口的修正候选。
          + → generation_result_text % text  # 完整修正结果及对低分要求的处理说明。
          > 按初始生成的六字段接口返回候选，保留仍有效的要求映射；必须把 precheck_result 当作反馈使用。读取隔离定义和包内参考知识；按需要读取 writing_reference_dir 内的四类写作文件，不改变实现代码。原始安全要求仍必须在输出最前面。
          > [[references/roles/kani-spec-generation#完整规则]]
          > [[references/kani-spec-write/SKILL#完整规则]]
          > [[references/find-similar/SKILL#完整规则]]
          > [[references/find-similar/template#完整规则]]
        5.3.4.2.2. [act] 记录本轮预检后的重新生成结果。
          - ← execution_log, verification_iteration, generation_result_text
          + → execution_log % [yaml]  # 已记录修正候选原文的执行记录。
          > ```hop_python
          > execution_log = execution_log + [{"executor_name": "kani-spec-generation", "kind": "stage", "round": "verify=" + str(verification_iteration) + ", precheck=1 后修正", "result_text": generation_result_text}]
          > ```
  5.4. [branch] 两次规格预检均未达标时才考虑证明入口编码。
    5.4.1. [case(not verification_target)] 没有平均分达到 6 的候选。
      5.4.1.1. [act] 从最后一次预检提取低分要求并读入当前入口源码。
        - ← precheck_result, staged_file_path
        + → low_score_requirements % [yaml]  # 最后一次预检中逐项分数小于 6 的要求及理由。
        + → current_source % text  # 当前隔离源文件完整内容，供入口修订判断。
        > ```hop_python
        > low_score_requirements = [p for p in precheck_result if p.score < 6]
        > current_source = read(path: staged_file_path)
        > ```
      5.4.1.2. [reason] 判断是否有低分要求应在证明入口中表达。
        - ← low_score_requirements, safety_requirements, best_spec_candidate, current_source, harness_code, harness_name_list
        + → revise_harnesses % bool  # 是否需要通过入口设置或见证编码某些安全要求。
        + → harness_revision_plan % text  # 明确列出需要修改的入口、RQ 映射与理由，或说明不修订的理由。
        > 只对提供的低分要求、代码和规格做语义判断。只有要求更适合用证明入口的设置或见证构造表达时才返回 true；不得为了提高分数引入文档之外的约束。修订必须保持原有 proof_for_contract、签名、非确定参数构造和函数调用，不增加 kani::assert()。
      5.4.1.3. [branch] 修订入口时必须执行且只执行一次混合预检。
        5.4.1.3.1. [case(revise_harnesses)] 需要有意编码安全要求。
          5.4.1.3.1.1. [act free] 只在选定证明入口内部实施安全要求编码。
            - ← staged_file_path, line_number, harness_name_list, harness_revision_plan, safety_requirements, best_spec_candidate
            + → harness_side_encodings % text  # 每个入口编码的代码和显式 RQ-<N> 注释。
            + → harness_code % text  # 修订后的完整证明模块代码。
            + → harness_revision_result_text % text  # 入口改动原文与要求映射摘要。
            > 修改隔离源文件 mod verify_<line_number> 中 harness_name_list 指定的入口。不得改变其它代码，不新建入口，不删除已有调用或属性。所有用于混合预检的片段必须在 harness_side_encodings 中明确列出并带 RQ 注释；不能只改文件却不给评估阶段提供证据。
            > [[references/roles/kani-spec-insert#完整规则]]
          5.4.1.3.1.2. [act] 记录入口编码的修订结果。
            - ← execution_log, verification_iteration, harness_revision_result_text
            + → execution_log % [yaml]  # 已记录入口修订原文的执行记录。
            > ```hop_python
            > execution_log = execution_log + [{"executor_name": "harness-side-revision", "kind": "stage", "round": "verify=" + str(verification_iteration) + ", mixed=准备", "result_text": harness_revision_result_text}]
            > ```
          5.4.1.3.1.3. [act free] 使用最佳候选与明确提供的入口编码进行混合预检。
            - ← best_spec_candidate, safety_requirements, requirement_items, harness_side_encodings
            + → mixed_precheck_result % [yaml]  # 与规格预检相同字段接口的混合评分列表。
            + → mixed_precheck_result_text % text  # 混合预检的原始 JSON 结果全文。
            > 必须使用 best_spec_candidate，不能改用最后生成的其它候选。只评估显式 RQ 映射的 requires/ensures 与 harness_side_encodings，一条要求恰评分一次，score 为 0–10 数值；不改写规格，不推断未提供的映射。
            > [[references/roles/kani-spec-precheck#完整规则]]
          5.4.1.3.1.4. [subtask retry=0] 核对混合评分的要求覆盖和数值接口。
            5.4.1.3.1.4.1. [check final] 混合结果完整合法，低分不阻断验证。
              - ← mixed_precheck_result, requirement_items
              + → mixed_schema_ok % bool  # 混合评分接口是否有效。
              + → mixed_schema_note % text  # 接口缺口。
              > ```hop_python
              > mixed_schema_ok = len(mixed_precheck_result) == len(requirement_items) and all([any([startswith(get(p, "req", ""), r.id + ":") for p in mixed_precheck_result]) for r in requirement_items]) and all([p.score >= 0 and p.score <= 10 and len(get(p, "reason", "")) > 0 for p in mixed_precheck_result])
              > mixed_schema_note = "混合接口有效；低分继续用最佳规格验证" if mixed_schema_ok else "混合评分必须完整覆盖要求且分数在 0–10 范围内"
              > ```
          5.4.1.3.1.5. [act] 更新最高分并仅在混合达标时选择带入口编码的目标包。
            - ← mixed_precheck_result, mixed_precheck_result_text, best_avg_score, best_spec_candidate, harness_side_encodings, verification_target, execution_log, verification_iteration, total_precheck_rounds
            + → mixed_avg_score % float  # 混合预检的算术平均分。
            + → best_avg_score % float  # 混合更高时才更新的最高分，最佳规格内容不改变。
            + → verification_target % yaml  # 混合达到 6 时含最佳规格与入口编码，否则仍为空。
            + → execution_log % [yaml]  # 已记录混合预检原文的执行记录。
            + → total_precheck_rounds % int  # 加上本次真实混合预检后的总次数。
            > ```hop_python
            > mixed_avg_score = sum([p.score for p in mixed_precheck_result]) / len(mixed_precheck_result) if mixed_precheck_result else 0.0
            > best_avg_score = mixed_avg_score if mixed_avg_score > best_avg_score else best_avg_score
            > verification_target = {"spec": best_spec_candidate, "safety_requirements": best_spec_candidate.safety_requirements, "harness_side_encodings": harness_side_encodings} if mixed_avg_score >= 6 else verification_target
            > total_precheck_rounds = total_precheck_rounds + 1
            > execution_log = execution_log + [{"executor_name": "kani-spec-precheck", "kind": "stage", "round": "verify=" + str(verification_iteration) + ", precheck=mixed", "result_text": mixed_precheck_result_text}]
            > ```
  5.5. [act] 尚无达标目标时仍选最佳规格进入插入。
    - ← verification_target, best_spec_candidate, safety_requirements
    + → verification_target % yaml  # 最终选择的完整验证目标包。
    > 目标包始终包含安全要求及所选规格的前置条件、后置条件、循环不变量和辅助代码。仅混合达标时额外提供入口编码；混合未达标时按原文退回 bundle(best_spec_candidate)，不以低分取消验证。
    > ```hop_python
    > verification_target = verification_target if verification_target else {"spec": best_spec_candidate, "safety_requirements": safety_requirements, "harness_side_encodings": ""}
    > ```
  5.6. [act free] 按检查清单把本轮目标真正插入隔离源码和选定入口。
    - ← target_func_name, line_number, staged_file_path, verification_target, harness_name_list
    + → insert_result % yaml  # 插入回执，含 success、feedback 和七项 checklist。
    + → insert_result_text % text  # 原始 Insertion Success 或 Insertion Failed 结果及反馈。
    > 必须真实插入验证目标。前后置块紧邻目标函数签名，已有标记只替换内部内容；要求注释保持跨轮不变。每条循环不变量必须匹配现有 while，匹配不了立即返回失败反馈。辅助代码只放 verify_aux_<line_number>；入口编码只改指定入口，保留属性、签名、非确定参数和调用。不创建新入口，不改实现逻辑。返回 success 布尔、feedback 文本和 checklist 对象，固定键为 contracts、requirements、loops、auxiliary、harness_encodings、all_harnesses、additive_only，所有七项核对成功才报告成功。
    > [[references/roles/kani-spec-insert#完整规则]]
  5.7. [act] 按七项清单计算插入是否成功并记录真实结果。
    - ← insert_result, insert_result_text, execution_log, verification_iteration
    + → insertion_succeeded % bool  # 只有角色报告成功且七项均通过时为真。
    + → execution_log % [yaml]  # 已追加本轮插入原文的执行记录。
    > ```hop_python
    > insertion_succeeded = get(insert_result, "success", False) and all([get(get(insert_result, "checklist", {}), k, False) for k in ["contracts", "requirements", "loops", "auxiliary", "harness_encodings", "all_harnesses", "additive_only"]])
    > execution_log = execution_log + [{"executor_name": "kani-spec-insert", "kind": "stage", "round": "verify=" + str(verification_iteration), "result_text": insert_result_text}]
    > ```
  5.8. [branch] 插入失败直接反馈下一轮，不运行验证。
    5.8.1. [case(not insertion_succeeded)] 插入失败。
      5.8.1.1. [act] 将插入失败作为下一轮生成反馈。
        - ← insert_result, insert_result_text
        + → last_failure_result % yaml  # 真实插入结果和具体修正反馈。
        > ```hop_python
        > last_failure_result = {"kind": "insert", "result": insert_result, "result_text": insert_result_text}
        > ```
      5.8.1.2. [continue] 下一验证轮重新生成。
  5.9. [act free] 检查当前轮的插入前提，不修改源码。
    - ← target_func_name, line_number, staged_file_path, verification_target, harness_name_list
    + → insertion_ready % bool  # 当前目标的必要验证区域是否都已实际存在且一致。
    + → insertion_precondition_note % text  # 前提缺口，必须给出具体区域和反馈。
    > 只读隔离源文件，确认本轮所选条件、循环不变量、辅助代码、入口编码及指定入口已实际存在，未选的类别无需创造。不完整或不一致时返回 false，不运行验证命令；不得以此机会修正源码。
    > [[references/roles/kani-spec-run#完整规则]]
  5.10. [branch] 前提满足时运行真实验证，否则形成验证阶段失败回执。
    + → verify_result % yaml  # 本轮验证阶段结果，所有路径都有 status 和 result_text。
    5.10.1. [case(insertion_ready)] 对插入后的隔离项目执行验证。
      + → verify_result % yaml  # 真实命令结果与语义分析反馈。
      5.10.1.1. [act] 执行原始 verify-spec 脚本并保留全部原始输出。
        - ← job_path, harness_name_list
        + → verify_command_result % yaml  # 原始命令退出码、输出、错误输出和日志。
        > Python 桥接保留原始脚本，但不把空验证结果误判为成功。只有脚本成功返回、输出 Verify Success 且实际覆盖请求的所有入口时才标记 successful。
        > ```hop_python
        > verify_command = subprocess.run(["python3", spec_dir("scripts/hop-support.py"), "verify"], input: str({"job_path": job_path, "harness_name_list": harness_name_list}), timeout: 1800 * len(harness_name_list) + 120)
        > verify_command_result = parse_json(verify_command.stdout) if verify_command.stdout else {"successful": False, "status": "Verify Failed", "result_text": verify_command.stderr}
        > ```
      5.10.1.2. [act free] 返回真实验证结果，失败时追踪原因并给下一轮反馈。
        - ← verify_command_result, verification_target, staged_file_path, preparation, harness_name_list
        + → verify_result % yaml  # 含 status、result_text、feedback 和 command_evidence 的验证结果。
        > 必须复制真实 status；只有 verify_command_result.successful 为真才返回 Verify Success。result_text 必须完整保留命令原始结果并补上本轮实际使用的验证产物、入口和函数代码。失败时只读追踪代码路径、数据流、类型定义和相关代码；语法错误不在此阶段改源码。只有失败消息匹配 “Check that <some_var> is assignable” 时才附精确 modifies 位置的可选修复建议，不把建议冒充根因。feedback 必须包括真实失败原因，command_evidence 必须保留 verify_command_result 完整结构。
        > [[references/roles/kani-spec-run#完整规则]]
    5.10.2. [case(else)] 插入前提不满足。
      + → verify_result % yaml  # 没有执行命令的失败反馈。
      5.10.2.1. [act] 返回前提缺口，明确说明未运行验证命令。
        - ← insertion_precondition_note
        + → verify_result % yaml  # status 为 Verify Failed 的前提失败结果。
        > ```hop_python
        > verify_result = {"status": "Verify Failed", "result_text": "未运行验证：" + insertion_precondition_note, "feedback": insertion_precondition_note, "command_evidence": {}}
        > ```
  5.11. [act] 记录验证阶段结果并更新最终状态或失败反馈。
    - ← verify_result, execution_log, verification_iteration, last_failure_result
    + → final_status % enum(success, fail)  # 真实命令证据与成功状态同时满足时才为 success。
    + → last_failure_result % yaml  # 失败时保留本輪真实结果供下轮生成使用。
    + → execution_log % [yaml]  # 已记录 verify-spec 与验证角色原始结果的执行记录。
    > ```hop_python
    > command_evidence = get(verify_result, "command_evidence", {})
    > final_status = "success" if verify_result.status == "Verify Success" and get(command_evidence, "successful", False) else "fail"
    > last_failure_result = last_failure_result if final_status == "success" else {"kind": "verify", "result": verify_result, "result_text": verify_result.result_text}
    > execution_log = execution_log + ([{"executor_name": "verify-spec", "kind": "skill", "round": "verify=" + str(verification_iteration), "result_text": get(command_evidence, "result_text", "")} ] if command_evidence else [])
    > execution_log = execution_log + [{"executor_name": "kani-spec-run", "kind": "stage", "round": "verify=" + str(verification_iteration), "result_text": verify_result.result_text}]
    > ```
  5.12. [branch] 验证成功立即结束整个验证循环。
    5.12.1. [case(final_status == "success")] 不再生成、预检、插入或验证。
      5.12.1.1. [break] 直接进入最终报告阶段。

6. [subtask retry=2] 按模板生成最终报告和 success 或 fail 文件并核对。
  + → rendered % yaml  # 报告和产物文本及其最终工作区相对路径。
  + → final_source % text  # 隔离项目当前的完整目标源文件内容。
  6.1. [act free] 读取实际最终源码和入口，整理最终产物内容。
    - ← target_func_name, line_number, staged_file_path, verification_target, safety_requirements, harness_name_list, final_status, last_failure_result, execution_log
    + → final_artifacts % text  # 实际留在最终源码中的前后置条件、循环不变量、辅助代码和入口编码。
    + → final_target_code % text  # 当前目标函数完整代码，包含已插入的验证注释和属性。
    + → final_harness_code % text  # 最终选定入口的实际代码。
    + → final_details % text  # 成功证据或最后失败结果原文，不掩盖没有运行命令的路径。
    > 只读取隔离源文件并整理真实最终状态，不再次生成规格或执行验证。success 时使用最后一次真实验证用过的代码；fail 时也报告目前实际代码和 last_failure_result，不能写成已验证成功。必须把四个输出完整给出，不只返回路径。原文模板位于包内 templates/report.md 和 templates/spec.md，下一步会机械填充。
  6.2. [act] 机械填充模板并读取最终源文件供验收。
    - ← job_path, execution_log, final_status, total_verify_rounds, total_precheck_rounds, verification_target, safety_requirements, final_artifacts, final_target_code, final_harness_code, final_details, staged_file_path
    + → rendered % yaml  # 按模板生成的 report_text、artifact_text、report_path 和 artifact_path。
    + → final_source % text  # 交付前当前源文件的完整内容。
    + → render_command % yaml  # 模板生成命令的真实退出码与原始输出。
    > 只写隔离结果目录，所有运行事件由脚本按 execution_log 顺序填入模板，不由模型重写原始结果。
    > ```hop_python
    > render_request = {"job_path": job_path, "execution_log": execution_log, "final_status": final_status, "total_verify_rounds": total_verify_rounds, "total_precheck_rounds": total_precheck_rounds, "verification_target": verification_target, "safety_requirements": safety_requirements, "final_artifacts": final_artifacts, "final_target_code": final_target_code, "final_harness_code": final_harness_code, "final_details": final_details}
    > render_command = subprocess.run(["python3", spec_dir("scripts/hop-support.py"), "render"], input: str(render_request), timeout: 60)
    > rendered = parse_json(render_command.stdout) if render_command.stdout else {"error": render_command.stderr}
    > final_source = read(path: staged_file_path)
    > ```
  6.3. [check final] 报告和结果文件完整反映实际运行顺序与最终代码。
    - ← rendered, render_command, execution_log, final_status, total_verify_rounds, total_precheck_rounds, verification_target, safety_requirements, final_artifacts, final_target_code, final_harness_code, final_details, final_source
    + → report_ok % bool  # 报告和结果文件是否达到原文输出要求。
    + → report_note % text  # 报告、轮次、代码或状态的具体缺口。
    > 不读取文件，只对 supplied 输入判定。render_command 必须成功；report_text 包含模板全部章节，每条实际阶段和技能结果全文按 execution_log 顺序出现，轮次和两类总计与记录相符。artifact_text 必须包含实际最终验证产物和完整目标函数代码，路径后缀严格为 final_status。success 必须有真实 Verify Success 命令证据；fail 必须清楚给出最后失败原因。不得把只生成未验证的代码写成成功。

7. [subtask retry=0] 在正式发布之前核对允许的源码改动和循环门禁。
  7.1. [check final] 原始实现未改变，最终产物与实际验证状态一致。
    - ← original_source, final_source, final_target_code, final_harness_code, verification_target, execution_log, final_status, total_verify_rounds, total_precheck_rounds, rendered, line_number, harness_name_list
    + → publication_ok % bool  # 是否允许将隔离项目产物发布到正式位置。
    + → publication_note % text  # 不允许发布的具体源码改动或流程缺口。
    > 只对已提供的原始与最终源码及运行记录判定。源码差异只允许目标前后置块、目标 while 的生成不变量、verify_aux_<原始行号> 和 verify_<原始行号> 指定入口；其它原始实现必须逐字保留。确认所有实际入口编码修改之后都做过混合预检；每轮规格预检最多两次，混合最多一次，验证轮最多两轮；低分仍进入插入和验证，插入或插入前提失败可以带真实反馈跳过命令；首次 Verify Success 后不得再出现业务循环动作。两条完成路径都必须有报告和 success/fail 产物。

8. [commit] 发布已核验源码、完整结果目录和 RESULT_FLDR 兼容配置。
  - ← job_path, final_status, rendered, publication_ok
  + → report_path % line  # 正式结果目录下已发布的报告相对路径。
  + → artifact_path % line  # 正式结果目录下已发布的 success 或 fail 相对路径。
  > Python 发布脚本先比对正式源文件的开始状态，遇到并发修改或已有同名结果目录就拒绝覆盖。保留此前目标源码和兼容配置的备份后复制已核验源码，完整复制隔离结果目录，并把正式 .claude/.env 写为最终 RESULT_FLDR。此步不执行任何 Git 命令。
  > ```hop_python
  > publication_command = subprocess.run(["python3", spec_dir("scripts/hop-support.py"), "publish"], input: str({"job_path": job_path, "final_status": final_status}), timeout: 180)
  > publication_receipt = parse_json(publication_command.stdout)
  > report_path = publication_receipt.report_path
  > artifact_path = publication_receipt.artifact_path
  > ```

9. [exit] 交付最终报告和按实际验证结果命名的产物路径。

## 部署前提清单

- 运行工作区必须是实际目标 Rust 项目根，包含目标源文件和 scripts/run-kani.sh。源文件与保存根都在工作区内；外部项目必须先作为运行工作区或挂入工作区，不能传沙箱外路径。
- 在项目 hopjit.yaml 中为 commands 声明 python3。所有 body 命令名同时在 Config.requires_commands 声明；不自动修改用户白名单。
- 项目 hopjit.yaml 的 env.hop_env_workspace_root 必须设为该运行工作区的绝对路径，且与 run(workspace_dir=...) 相同。这是部署设施参数，不能当作业务输入；桥接脚本不猜测服务进程或命令的当前目录。
- 被引擎实际启动的 python3 必须能导入 yaml、click 和 dotenv（安装包名分别为 PyYAML、click、python-dotenv），不能只依赖交互式 shell 的别名。HopSpec 的 str(结构值) 输出 YAML，桥接脚本读取 YAML 并返回 JSON。
- Python 桥接脚本会调用 bash、realpath、basename、date、mkdir，以及目标 scripts/run-kani.sh 间接使用的 Kani/Rust 工具链。它们必须已可用。原始脚本资产保持不变，所需 RESULT_FLDR 从隔离 .claude/.env 读取并传给命令子进程。
- 桥接脚本复制整个项目到 work_zone，排除 .git、.hopstate、.hoplog、target、node_modules 和 .venv，也排除容纳本次 work_zone 的自定义状态目录以避免递归复制；需要足够磁盘空间。项目应支持在副本中通过相同入口编译，不能依赖指向正式源码的硬编码路径。
- 本流程未新增外部服务，Tools 清单为空；代码阅读和编辑使用引擎内置工具。
- 入口语法修正的原文没有次数上限，此稿暂设 20 次，耗尽后终止，不继续发布；最终验收材料会呈明这一暂定值。
- 打包必须包含 scripts、assets、references、templates；不纳入未被流程引用的 templates/commit.md。

## 使用说明

结果目录仍采用 spec-<源文件名去扩展>/<原始行号>/<时间戳> 布局。各阶段消费隔离副本中的 result_fldr；完成后整个结果目录复制到正式 save_dir_root，同步更新兼容配置。报告里的 Result Folder 使用最终目录路径。

原文逐字副本为 source.md，角色业务规则及其它技能知识已随包保留。评分下限、空要求平均值、入口修正上限和验证角色的源文件修改冲突详见翻译研判点台账，均需终审确认。
