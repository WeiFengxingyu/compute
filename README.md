# Compute —— 生产调度优化与实验记录

本仓库包含以遗传算法（GA）为基线的生产调度优化原型，以及可重复的实验记录机制与项目文档。目标是在半月至一月内由两人完成从基线到多算法对比的实现与验证，并沉淀完整的设计与实施材料。

## 项目简介
- 基线算法：`GA`（窗口交叉、变异、可行性修复等将逐步增强）
- 扩展方向：`VNS/ILS` 邻域局部搜索、`SA/TS` 退火/禁忌搜索、`PSO/ACO` 对比
- 可重复实验：自动将每次运行的配置、数据、结果、指标与摘要保存到 `experiments/run-YYYYMMDD_HHMMSS_<tag>_seed<SEED>/`
- 文档入口：
  - 设计方案：`设计与实现方案.md`
  - 实施计划：`实施步骤计划.md`

## 目录结构（简要）
```
.
├── data/                    # 示例配置与订单
├── experiments/             # 自动生成的实验运行记录
│   └── run-YYYYMMDD_HHMMSS_<tag>_seed<SEED>/
│       ├── config.json
│       ├── orders.json
│       ├── schedule.json
│       ├── metrics.json
│       └── summary.md
├── results/                 # 最近一次调度产物等
├── src/                     # 源码
│   ├── algorithms/ga.py     # 基线GA
│   ├── decoders/edd_decoder.py
│   ├── evaluation/fitness.py
│   ├── models/entities.py
│   ├── utils/run_logger.py  # 实验记录工具
│   └── main.py              # 入口，含CLI与记录集成
├── 设计与实现方案.md
└── 实施步骤计划.md
```

## 环境要求
- Python 3.9+（建议 3.10），Windows/Linux/macOS 皆可
- 常用依赖以标准库为主；若后续引入额外库，将在文档与代码中标注

## 快速开始
1) 使用内置示例数据运行一次基线 GA 并记录实验：
```
python -m src.main \
  --horizon 30 \
  --generations 100 \
  --pop 60 \
  --pc 0.9 \
  --pm 0.1 \
  --config data/config.json \
  --orders data/orders.json \
  --out results \
  --runs_dir experiments \
  --exp_tag baseline-ga \
  --seed 123
```
- 运行完成后，将自动生成目录：`experiments/run-YYYYMMDD_HHMMSS_baseline-ga_seed123/`
- 其中包含：`config.json`、`orders.json`、`schedule.json`、`metrics.json` 与 `summary.md`

2) 进行更强的基线验证（建议）：
```
python -m src.main \
  --horizon 30 \
  --generations 300 \
  --pop 80 \
  --pc 0.9 \
  --pm 0.1 \
  --config data/config.json \
  --orders data/orders.json \
  --out results \
  --runs_dir experiments \
  --exp_tag baseline-ga-longrun \
  --seed 123
```

## 实验记录规范
- 每次运行均创建独立目录：`experiments/run-YYYYMMDD_HHMMSS_<tag>_seed<SEED>/`
- 保存内容：
  - `config.json` / `orders.json`：本次实验的配置与订单数据
  - `schedule.json`：生成的最佳或最新调度方案
  - `metrics.json`：评估指标（利润、收入、成本、罚金等）
  - `summary.md`：摘要与关键数值、订单完成情况概要
- 命名建议：通过 `--exp_tag` 表达方法或版本，如 `ga-v0.2-repair`、`vns-slot-swap`、`pso-baseline`
- 随机性控制：通过 `--seed` 固定随机种子，提高可复现性

## 文档与路线图
- 设计方案详见：`设计与实现方案.md`（含算法版本规划 v0.1→v1.0、工程结构、实验日志标准与风险控制）
- 实施计划详见：`实施步骤计划.md`（里程碑 M0-M7、每阶段验收标准、命令模板与打钩规则）
- 当前状态：
  - M0（基础设施与记录框架）已完成
  - M1（基线 GA）已具备运行能力，建议先完成 300 代验证

## 常用命令
- 查看最近提交：`git log -n 1 --oneline`
- 推送到远端：`git push`
- 修改远端为 SSH：`git remote set-url origin git@gitee.com:wei-feng-xingyu/compute.git`

## 仓库链接
- Gitee：<https://gitee.com/wei-feng-xingyu/compute>
- 分支：`main`

## 后续工作建议
- 优先完成 M1 的长跑基线验证；随后在 M2 引入“可行性修复器”与“窗口交叉”增强，观察利润、罚金与准时率的改善
- 持续用 `--exp_tag` 标注方法版本，迭代后将关键结果与算法说明同步到 `设计与实现方案.md` 与 `paper/`（若创建）

## 批量实验（Runner）
- 批量运行并聚合指标到 CSV：
```
python -m src.experiments.runner \
  --exp_tag ga-v0.1 \
  --seed-start 1 --seed-end 30 \
  --horizon 30 \
  --generations 300 \
  --population 80 \
  --crossover 0.9 \
  --mutation 0.1 \
  --config data/config.json \
  --orders data/orders.json \
  --outdir results \
  --runs_dir experiments
```
- 也可显式指定种子集合：`--seeds 1 2 3 4 5`
- 运行后自动生成：`experiments/batch_ga-v0.1_summary.csv`
- 每行包含：`timestamp, exp_tag, seed, profit, total_revenue, production_cost, wage_cost, penalty, utilization_rate, on_time_rate, penalty_rate, run_dir`
 - 每行包含：`timestamp, exp_tag, seed, profit, total_revenue, production_cost, wage_cost, penalty, utilization_rate, on_time_rate, penalty_rate, run_dir`
 - 注：批量运行器的 `--population/--crossover/--mutation/--outdir` 会在内部映射到 `src.main` 的 `--pop/--pc/--pm/--out`，使用者无需关心差异。

## English Overview
- This repository provides a baseline Genetic Algorithm (GA) for production scheduling and a reproducible experiment logging pipeline.
- Each run is recorded under `experiments/run-YYYYMMDD_HHMMSS_<tag>_seed<SEED>/` with `config.json`, `orders.json`, `schedule.json`, `metrics.json`, and a `summary.md`.
- A batch runner (`src.experiments.runner`) is available to iterate seeds and aggregate metrics into a CSV for quick analysis.
- Documents: design (`设计与实现方案.md`) and implementation plan (`实施步骤计划.md`) describe milestones, variants, and logging standards.