# KaPilot HopSpec 部署与打包

这份流程接收函数名、源文件相对路径、原始行号和结果保存根目录。正式运行工作区必须是实际 Rust 项目根，代码、结果根和 Kani 入口都在该项目内。保存根缺失时先在隔离副本创建，正式发布才创建正式结果目录。

在目标项目的 hopjit.yaml 合并以下配置，保留原有配置项；将路径换成该项目根的真实绝对路径：

```yaml
commands:
  - python3
env:
  hop_env_workspace_root: /path/to/rust-project
```

引擎实际调用的 python3 需要 PyYAML、click 和 python-dotenv。目标项目还需要可运行的 scripts/run-kani.sh、Kani/Rust 工具链及 bash、realpath、basename、date、mkdir。桥接脚本从本次隔离项目的 .claude/.env 读取 RESULT_FLDR，并显式传给原始脚本；原始编译与验证脚本无需修改。

以绝对路径指向本目录的 spec.md 起跑，并使 workspace_dir 与上述 hop_env_workspace_root 相同。复用模式运行时，调用方须在每个阶段和内部技能返回后立即展示原始结果；该显示义务已写入流程全局约束。

准备、源码改动、编译、预检、插入和验证都在 work_zone 中的项目副本执行。全部业务结束且最终核验通过后，发布步骤将最终源码、完整结果目录和 RESULT_FLDR 兼容文件写入正式项目。正式源码发生并发修改或同名结果目录已经存在时会拒绝覆盖；以前源码和兼容文件的备份保留在最终结果目录的 previous-workspace 中。流程不执行任何 Git 命令。

在本仓库根打包时使用以下命令；资产名按 spec.md 所在目录解析：

```bash
hopjit pack skills/kapilot/spec.md --name kapilot-hopspec --assets scripts,assets,references,templates/report.md,templates/spec.md,source.md,DEPLOY.md
```

该清单显式包含两个报告模板、全部知识和脚本；不带未被流程使用的 templates/commit.md。spec.md 与 source.md 并排保存，原始 SKILL.md 继续可读。
