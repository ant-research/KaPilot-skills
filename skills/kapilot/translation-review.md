# KaPilot HopSpec 作者终审

输入技能：skills/kapilot/SKILL.md。目标正式文件：skills/kapilot/spec.md。此稿尚未写入正式技能目录。

流程摘要：四项原输入保留；先编译证明入口，再复用或提取安全要求；每轮最多两次规格预检，必要时一次混合预检；低分也验证；插入失败给下一轮反馈；最多两轮，第一次成功立即停止；核验后发布报告、success/fail 代码和最终源码。

需要作者确认的主要口径：逐项低分小于 6；空要求平均为 0；入口修正最多 20 次；验证阶段按更严格禁令只读，不在同轮修语法。完整研判点如下。部署需配置 python3 白名单和 hop_env_workspace_root。

原文逐字副本：[source.md](source.md)；包内原始脚本、模板及参考知识均在场。

## HopSpec 全文

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


## 翻译研判点全文

# 翻译研判点台账

已对齐的业务契约：目标函数名、源文件路径、原始行号、结果保存根四项输入；最终报告与 success/fail 验证代码两项文件交付。原文固定的两轮验证、每轮两次预检和通过平均分 6 保持不变。下面列出原文缺省、矛盾或需要改变实现形态的地方，供作者终审。

1. **低分要求阈值暂定为逐项小于 6。** 原文仅写 requirements_with_low_scores(precheck_result)，没有给逐项阈值。采用与平均通过分数相同的 6，且严格从最后一次预检提取低分要求，符合原文伪代码的输入来源。
2. **空要求列表的平均分暂定为 0。** 原文通篇未给空列表平均值；不处理会除以零。此稿不把空要求视作已通过预检，仍按两次预检和低分回退进入实际验证，只有真实验证成功才交付 success。
3. **入口语法修正最多 20 次。** 入口生成角色要求一直修到语法正确，原文没有上限。有限循环需要明确上限，因此暂定 20；耗尽时停止，不重复业务验证，也不把未完成的产物发布为已验收结果。
4. **验证阶段采用严格禁止改源码的条款。** kani-spec-run 正文允许在保持规格语义时修正生成片段的语法错误，但该文件的 Critical 第 1 条又禁止修改源文件。此稿采用后者：当前验证阶段只读诊断，语法问题和其它失败反馈交给下一轮生成；可能消耗第二验证轮，需作者确认。
5. **准备、插入与验证统一使用隔离项目副本，最后发布。** 原文在正式项目创建目录、写兼容配置并插入源码；HopSpec 的探索步骤只能写 work_zone。此稿将这些试错动作移到同一个项目副本，保持执行先后和实际插入后验证；最终 commit 才复制最终源码、整个结果目录和兼容配置到正式位置。原文禁止 Git，因此使用文件复制隔离，不调用 Git worktree。
6. **原始脚本保留，增加文件态配置桥接。** 原编译与验证脚本按自身固定目录层级找 .env，迁移后未必找到运行项目配置。新增 scripts/hop-support.py 从隔离 .claude/.env 读取 RESULT_FLDR，再显式传给原始命令进程；两份原始脚本、目录命名脚本及两个输出模板均逐字保持不变。
7. **部署工作区作为设施配置，不新增业务输入。** 引擎命令当前目录不等于 run(workspace_dir=...)，且没有自动提供该业务工作区变量。目标项目需配置 env.hop_env_workspace_root，与运行工作区相同。桥接脚本直接使用该配置，不猜服务进程目录。机器命令依赖为 Config.requires_commands: [python3]；Python 模块及 Kani 入口前提写在 DEPLOY.md。
8. **保存根不存在时仅在隔离副本中创建。** 原文要求目录脚本创建结果目录，没有明确要求保存根必须预先存在；realpath 对不存在路径的行为又取决于父目录情况。此稿先在副本创建保存根，再调用未改动的原脚本，正式位置直到发布才创建。
9. **即时展示由执行调用方落实。** 每个阶段和技能的原始 result_text 必须立即展示，之后同一文本按实际顺序进入报告。复用模式调用方应在收到步骤结果时展示全文；此稿不增加通知服务。独立模式若需要同样的实时界面，运行界面须转发这些阶段结果。
10. **不执行宿主配置和未引用的提交模板。** 模型别名、颜色、disable-model-invocation 和停止钩子属于原宿主配置；其中 .claude/hooks/dump.py 在当前仓库不存在。它们不转成业务步骤，业务结果、顺序和展示义务保留。templates/commit.md 未被主流程引用，且与禁止 Git 的要求不相容，保留原目录文件，但打包资产不带该模板。
11. **新增语义核验重试采用 2 次。** 原提取技能要求生成后验证 R1–R7，报告也必须符合模板，但未定义核验失败后的重试次数。此稿为提取和报告的可逆修订各设 retry=2；六个“失败即停止”的门保留 retry=0，不把评分接口错误变成额外第三次预检。
12. **命令外层等待上限明确写入。** 原编译/验证脚本的每入口默认超时为 1800 秒，外层上限采用 1800×入口数量+120 秒；复制准备与发布暂设 180 秒，模板渲染 60 秒。原文没有给后三项上限，作为部署运行保护的暂定值呈审。
13. **真实验证成功需有入口覆盖证据。** 原验证脚本可能对空的解析结果打印 Verify Success，且 Python 退出码本身不等于 Kani 结论。桥接保留原始输出，同时要求脚本成功返回、成功标志、所请求入口均在真实输出中出现且无失败检查，防止没有实际验证却标成功。

所有改动都限于执行形态、缺省值和原文矛盾的明确处置；没有新增安全要求、提高原文通过阈值或增加第三验证轮。


## 实测报告全文

# 翻译检查与实测报告

本报告验证生成的流程与桥接实现。八组流程用模拟 Rust/Kani 输出；自由生成、语义评估和语义检查使用固定样例结果，未执行真实 Rust 形式化证明。确定性 body、原始编译/验证 Python 脚本和模板渲染均由真实引擎执行。

## 合法关

hopjit validate：0 error，六条 P6 warning。warning 全集为步骤 1、2、3、5.3.2、5.4.1.3.1.4、7；逐条保留理由在 deep-validate-report.md，不静默忽略。负向探针把 1.1 输入改成未定义变量，实际命中 V1 和 B4 error；探针已删除，正式草稿未改。

## 忠实关

对读 49 段，逐段落点在 translation-traceability.md。补落 3 处：入口编译反馈的显式输入、完整知识章节引用、写作参考目录信号；纠偏 2 处：结构值 YAML/JSON 桥接、结果保存根不存在时的隔离创建。目录命名脚本、原始两份编译/验证脚本、原始两个输出模板和 source.md 均与原输入逐字一致。

对偶核两组：初始生成与预检反馈重新生成的候选接口；规格预检与混合预检的要求覆盖、0–10 评分接口及空列表处置。最终接口一致，两个生成位置均注入写作与相似参考规则，两种评分位置均以合法接口而非平均通过分数作门禁，没有未处置的不对称。

## 合理关

原文先后、两层循环、候选分数绑定、混合回退、插入失败继续和成功立即退出全部显式在场。前后置块、循环、辅助模块、入口的改动边界均保留。探索只写隔离副本，正式写盘在 commit 前有 final 检查。没有 call 步，因此无未交付的子流程入口。

机械前筛命令与结果：

```text
grep -rn 'run_in_background\|Agent 工具\|发射 agent\|发射 Agent\|subagent\|AskUserQuestion' package/spec.md package/references
结果：退出码 1，输出为空，执行面零命中。

test -e <每个实际 doc-ref 对应的包内 Markdown 文件>
结果：20 个引用全部通过，章节名也逐个实存。
```

审阅文件和 DEPLOY.md 中的实际文件指引也已核对；宣布正式写入的位置是待终审批准后的目标，不冒充已经落盘。旧角色示例命令属于规则说明，实际命令入口以本流程的确定性 body 与桥接脚本为准。

## 明确易懂关

修正 3 类：把角色职责写成可独立执行的完整指令；为下游消费的所有固定字段说明类型和内容；把原文强禁令保留为必须或不得，避免仅在一处局部生效。结构是准备→入口→缓存→两轮验证→报告→最终核验→发布，命名与数据链清楚。

## 控制流实测

命令：python3 /tmp/kapilot-hopbuild-Z9YG0h/test-control-flow.py

| 场景 | 验证轮 | 预检次数（含混合） | 实际验证命令数 | 最终状态 | 结论 |
| --- | --- | --- | --- | --- | --- |
| 首次达标并成功立即结束 | 1 | 1 | 1 | success | 通过 |
| 最后候选更差，仍选最佳候选 | 1 | 2 | 1 | success | 通过 |
| 混合达标但验证失败，下轮反馈后成功 | 2 | 4 | 2 | success | 通过 |
| 两轮都失败后输出 fail | 2 | 4 | 2 | fail | 通过 |
| 插入失败跳过验证，下轮成功 | 2 | 2 | 1 | success | 通过 |
| 空要求平均值为 0，仍执行验证 | 1 | 2 | 1 | success | 通过 |
| 混合仍低分，回退最佳规格继续验证 | 1 | 3 | 1 | success | 通过 |
| 插入前提失败，不运行命令但保留反馈 | 2 | 2 | 0 | fail | 通过 |

模拟工作区的正式源文件在全部业务试错步骤中均保持原文。角色原始结果按执行记录顺序进入报告，模板没有未填槽。

## 桥接和发布检查

- 发布脚本已在临时样例工作区验证：并发源文件修改拒绝、源码/报告/产物发布、旧源码与兼容配置备份、正式 RESULT_FLDR 更新、重复发布拒绝。
- 自定义状态目录被排除，隔离复制不递归包含自己的 work_zone。
- 保存根缺失只在隔离副本创建，正式位置保持不变。
- 模板只替换原模板槽；Rust 代码中的字面双花括号和类似槽名文本保持原文，真正缺槽仍报错。

## 真实知识注入与打包检查

实际引擎起跑后，入口步骤的 doc_ref_context 包含完整角色门禁和非确定值指南的后续章节。普通双链已改为明确 #完整规则 章节，避免合法但不注入的链接。最终打包有 12 个独立知识文件、20 个章节引用，全部闭合；显式 assets 包括脚本、知识、两个模板、source.md 与 DEPLOY.md，不包含未使用的 Git 提交模板。只打包到临时目录，没有安装到用户技能目录。

## 跑前深检

deep-validate 已由引擎驱动完成，最终风险报告经独立判定者通过。报告有五面及六条实际 warning 的完整表态；保留两项部署风险：目标项目的 python3 命令白名单与 hop_env_workspace_root 尚需配置。它们是部署前提，不把静态语法通过当成已经具备真实 Kani 环境。

## 本次验证范围

已验证编排、确定性数据链、脚本桥接、隔离、模板、资产和发布保护。没有用户提供的目标 Rust 函数，也没有真实目标项目的 Kani 入口，因此没有宣称生成的任何实际 Rust 规格已被证明。



## 跑前深检风险报告全文

# KaPilot 跑前深检报告

结论：风险 2 条，高 2 条、中 0 条、低 0 条；均为运行环境需要准备的项目，不是静态语法错误。审查模式为 standalone；复用模式同样执行确定性 body，因此这两项前提也适用。

## 一、执行模式能力面矛盾

已检查，未发现需要不存在的宿主角色启动工具、shell 工具或外部服务的步骤。生成、阅读和隔离代码编辑由 act free 负责；命令全部由 subprocess.run body 执行；判断所需代码与评分均经输入变量传入；无 body 的检查步骤只核对其明确声明的输入，不教判定者另行读盘。源码修改与实际命令的操作规则由步骤正文限定，知识文件中的旧角色命名只用于报告标识。

## 二、确定性步骤形态

已检查，无风险。评分算术平均、严格更高时更新最佳候选、循环退出、失败反馈、日志拼接和报告模板填充都有确定性 body。自由步骤只承担文档理解、规格生成、语义评分、插入定位和错误根因分析。桥接入口显式接受 HopSpec str(结构值) 产生的 YAML，返回 JSON；没有把 YAML 误当成 JSON 解析。所有脚本入参的固定字段都在生成步骤的说明或确定性组装中明确列出。

## 三、体量模式

已检查，未发现把机器生成的全部事件清单交给模型逐项转写的步骤。执行记录以列表在确定性 body 中追加，报告的事件列表由 Python 模板渲染器机械填充，原始结果不经模型重写。语义判断仍需要读取目标代码、允许来源及当前候选，这是业务本身的工作；审查不把不存在的输入规模当成确定故障。

## 四、环境依赖

### R1：项目未配置 python3 命令白名单

- 坑位：步骤 1.1、2.2.2、5.10.1.1、6.2、8，命令形态为 `subprocess.run(["python3", spec_dir("scripts/hop-support.py"), ...])`；Config 已声明 `requires_commands: [python3]`。
- 病理：机械备料得到 env_config 为空，当前审查工作区没有 hopjit.yaml。环境事实教材规定命令白名单缺席时 subprocess.run 被拒；requires_commands 会在进入业务步骤之前指出缺少命令授权。这是明确的部署配置缺口，不能把“文档写了依赖”当成已经授权。
- 修法：实际目标 Rust 项目的 hopjit.yaml 增加 `commands: [python3]`，或在该项目已有 commands 列表中增补 python3。解释器实际调用的 Python 需能导入 PyYAML、click 和 python-dotenv；目标项目需有 scripts/run-kani.sh 及它使用的 Kani/Rust 工具链。这些前提在交付计划的部署清单中已逐项列明，本次翻译不自动修改用户配置。
- 严重度：高。配置缺失时无法进入业务步骤；配置补齐即可解除。

### R2：部署设施参数 hop_env_workspace_root 尚未配置

- 坑位：步骤 1.1，`request_data = {"workspace_dir": hop_env_workspace_root, ...}`。
- 病理：机械备料得到 env_config 为空，因此本项目没有提供这个 env 值。hop_env_* 是部署配置提供的变量，并不是引擎自动生成的业务输入；没有值时准备脚本不能确定实际工作区。服务进程和 subprocess.run 的当前目录也不能替代 run 的显式 workspace_dir。
- 修法：实际目标项目的 hopjit.yaml 设置 `env.hop_env_workspace_root` 为该项目根的绝对路径，并使它与 run(workspace_dir=...) 一致。桥接脚本只按这项显式配置定位原项目，四项业务 Inputs 保持不变。
- 严重度：高。缺值时准备阶段失败，且不能开始复制和验证。

## 五、写域与路径

已检查，无风险。所有业务路径输入为工作区相对路径；准备脚本将加工项目和结果目录创建在 work_zone_path("project") 内。各生成、插入、修正和命令步骤只消费该副本中的路径。最终源码和目录写回由步骤 8 的 commit 负责，并有步骤 7 的 final 检查；发布脚本拒绝并发源文件变化和已有同名输出目录，并保留以前内容。包内文档引用、模板和脚本路径已真实在场。

## validate 警告逐条表态

- P6，步骤 1：保留 retry=0。输入或准备失败即停止，不重跑复制和创建结果目录。
- P6，步骤 2：保留 retry=0。内部入口修正循环已提供重编译路径；耗尽后停止，不另开整组重试。
- P6，步骤 3：保留 retry=0。缓存选择只做一次；提取子任务已有独立语义核验重试。
- P6，步骤 5.3.2：保留 retry=0。只验证评分接口，不因平均低分失败；接口非法须停止，不偷偷增加第三次预检。
- P6，步骤 5.4.1.3.1.4：保留 retry=0。只验证一次混合评分接口；接口非法须停止，不偷偷增加第二次混合预检。
- P6，步骤 7：保留 retry=0。禁止把最终源码核验失败降级为继续发布；有改动问题必须停下。

上述六条构成机械体检实际给出的 warning 全集，无其它 warning 可供表态。静态错误数为 0。


## 逐段对读表

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
