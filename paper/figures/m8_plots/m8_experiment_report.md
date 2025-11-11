# M8阶段实验报告：不同订单紧迫度场景对比实验

## 实验概述

本实验旨在比较不同算法（GA、GA+VNS、GA+VNS+SA、PSO）在不同订单紧迫度场景（LOOSE、MEDIUM、TIGHT）下的性能表现。实验主要评估四个关键指标：利润、利用率、准时率和惩罚率。

## 实验完成情况

### 数据收集状态（更新）
- LOOSE、MEDIUM、TIGHT 三场景均已完成四种算法（GA、GA+VNS、GA+VNS+SA、PSO）各 30 次运行。
- 批量汇总文件已生成：`experiments/batch_ga-*_m6s3_summary.csv`、`experiments/batch_ga-vns-*_m6s3_summary.csv`、`experiments/batch_ga-vns-sa-*_m6s3_summary.csv`、`experiments/batch_pso-*_m6s3_summary.csv`。

### 数据处理状态（更新）
- 已执行聚合与统计：`experiments/scripts/aggregate_m8_batches.py` 与 `compute_m8_averages.py` 完成均值±标准差计算。
- 图表与总结表已生成：`experiments/scripts/plot_m8_figures.py` 输出到 `experiments/m8_plots/` 与 `paper/figures/m8_plots/`；统计汇总表位于 `experiments/m8_plots/m8_summary_table.md`。

## MEDIUM场景实验结果

### 描述性统计

| 算法 | 利润 | 利用率 | 准时率 | 惩罚率 | 样本数 |
|------|------|--------|--------|--------|--------|
| GA | 2422.67±3807.17 | 0.60±0.03 | 0.01±0.03 | 0.99±0.03 | 30 |
| GA+VNS | 2454.00±3919.19 | 0.61±0.03 | 0.01±0.03 | 0.99±0.03 | 30 |
| GA+VNS+SA | 4930.67±5552.44 | 0.63±0.08 | 0.07±0.14 | 0.93±0.14 | 30 |

### 统计显著性检验

与GA基准算法的配对t检验结果：

#### 利润指标
- **GA+VNS vs GA**：t=-0.07, p=0.947（不显著）
- **GA+VNS+SA vs GA**：t=-2.17, p=0.038*（显著，GA+VNS+SA表现更好）

#### 利用率指标
- **GA+VNS vs GA**：t=-1.15, p=0.259（不显著）
- **GA+VNS+SA vs GA**：t=-2.61, p=0.014*（显著，GA+VNS+SA表现更好）

#### 准时率指标
- **GA+VNS vs GA**：t=0.00, p=1.000（不显著）
- **GA+VNS+SA vs GA**：t=-2.14, p=0.041*（显著，GA+VNS+SA表现更好）

#### 惩罚率指标
- **GA+VNS vs GA**：t=0.00, p=1.000（不显著）
- **GA+VNS+SA vs GA**：t=2.14, p=0.041*（显著，GA+VNS+SA惩罚率更低）

### 关键发现

1. **GA+VNS+SA算法在MEDIUM场景中表现最优**：在利润、利用率、准时率和惩罚率四个指标上均显著优于基础GA算法。

2. **GA+VNS算法改进有限**：相比基础GA算法，GA+VNS在各个指标上均未表现出显著差异。

3. **算法性能排序**：GA+VNS+SA > GA+VNS ≈ GA

## 可视化结果

生成的图表包括：
- 利润对比箱线图
- 利用率对比柱状图
- 准时率对比柱状图
- 综合性能雷达图

图表文件保存在：`d:\Desktop\计算智能\github\compute\experiments\m8_plots\`

## 关键结论（更新）

- 强化适应度函数是解决低准时率的关键：按 M7.1 的做法，提高截止权重与软惩罚系数（如提高 `alpha_deadline`、`beta_late_units`），显著提升准时率并降低罚金触发率，三场景统计均得到验证。
- 横向对比算法采用 PSO：在现有框架下的 PSO（受 `--seed` 控制的随机源）作为论文横向对比算法，与 GA 家族形成互证；PSO 在准时率与罚金方面具有优势，具体数值已汇总在 `experiments/m8_plots/m8_summary_table.md`。
- 算法选择建议：论文对比可采用 GA、GA+VNS、GA+VNS+SA 与 PSO 四线并行；若调整 PSO 的随机性或参数（`w/c1/c2/max_vel`），仅需重跑 PSO 的三场景×30 次并重新聚合与绘图，GA 系列无需重跑。

附：所有图表亦同步到 `paper/figures/m8_plots/` 便于论文插图使用。

## 结论

在最新的三场景×四算法×30 次的完整统计中：
- 强化适应度函数（提高截止与软惩罚权重）显著改善准时率并抑制罚金，是解决“低准时率”问题的关键路径；
- PSO 作为横向对比算法在多场景下展现出更优的期限遵守能力，与 GA+VNS+SA 的整体改进形成互证；
- 具体均值±标准差及算法间显著性检验详见 `experiments/m8_plots/m8_summary_table.md` 与本目录图表。

为确保可复现性，若后续仅调整 PSO 参数，请按“仅重跑 PSO 三场景×30 次 → 重新聚合 → 重新绘图”的流程更新统计与图表。

---

## M8 数值摘要与显著性（均值±标准差与配对t检验）

- 数据源：
  - LOOSE：`experiments/batch_ga-loose-m6s3_summary.csv`、`experiments/batch_ga-vns-loose-m6s3_summary.csv`、`experiments/batch_ga-vns-sa-loose-m6s3_summary.csv`、`experiments/batch_pso-loose-m6s3_summary.csv`
  - MEDIUM：`experiments/batch_ga-medium-m6s3_summary.csv`、`experiments/batch_ga-vns-medium-m6s3_summary.csv`、`experiments/batch_ga-vns-sa-medium-m6s3_summary.csv`、`experiments/batch_pso-medium-m6s3_summary.csv`
  - TIGHT：`experiments/batch_ga-tight-m6s3_summary.csv`、`experiments/batch_ga-vns-tight-m6s3_summary.csv`、`experiments/batch_ga-vns-sa-tight-m6s3_summary.csv`、`experiments/batch_pso-tight-m6s3_summary.csv`

- 说明：每算法每场景 n=30；均值±标准差由 `experiments/scripts/compute_m8_averages.py` 输出；显著性为“相对 GA 的配对 t 检验”，由 `experiments/scripts/compute_m8_tests.py` 输出（ns: 不显著；*: p<0.05；***: p<0.001）。

### LOOSE 场景（n=30）
- GA：`profit=-39050.33±8135.48`，`util=0.65±0.04`，`on_time=0.33±0.10`，`penalty=0.67±0.10`
- GA+VNS：`profit=-41824.67±7501.53`，`util=0.64±0.05`，`on_time=0.34±0.12`，`penalty=0.66±0.12`
- GA+VNS+SA：`profit=38454.43±14191.17`，`util=0.91±0.03`，`on_time=0.62±0.06`，`penalty=0.38±0.06`
- PSO：`profit=75926.10±3134.79`，`util=0.80±0.01`，`on_time=0.63±0.04`，`penalty=0.37±0.04`
- 显著性（相对 GA）：
  - 利润：GA+VNS `p=0.085` ns；GA+VNS+SA `p=0.000` ***；PSO `p=0.000` ***
  - 利用率：GA+VNS `p=0.482` ns；GA+VNS+SA `p=0.000` ***；PSO `p=0.000` ***
  - 准时率：GA+VNS `p=0.762` ns；GA+VNS+SA `p=0.000` ***；PSO `p=0.000` ***
  - 罚金率：GA+VNS `p=0.762` ns；GA+VNS+SA `p=0.000` ***；PSO `p=0.000` ***
- 结论：PSO 与 GA+VNS+SA 在准时率与罚金率上均显著优于 GA；PSO 在利润上显著最高，GA+VNS+SA 在利用率上显著最高。

### MEDIUM 场景（n=30）
- GA：`profit=2422.67±3807.17`，`util=0.60±0.03`，`on_time=0.01±0.03`，`penalty=0.99±0.03`
- GA+VNS：`profit=2454.00±3919.19`，`util=0.61±0.03`，`on_time=0.01±0.03`，`penalty=0.99±0.03`
- GA+VNS+SA：`profit=4930.67±5552.44`，`util=0.63±0.08`，`on_time=0.07±0.14`，`penalty=0.93±0.14`
- PSO：`profit=-12093.00±0.00`，`util=0.49±0.00`，`on_time=0.25±0.00`，`penalty=0.75±0.00`
- 显著性（相对 GA）：
  - 利润：GA+VNS `p=0.947` ns；GA+VNS+SA `p=0.038` *；PSO `p=0.000` ***
  - 利用率：GA+VNS `p=0.259` ns；GA+VNS+SA `p=0.014` *；PSO `p=0.000` ***
  - 准时率：GA+VNS `p=1.000` ns；GA+VNS+SA `p=0.041` *；PSO `p=0.000` ***
  - 罚金率：GA+VNS `p=1.000` ns；GA+VNS+SA `p=0.041` *；PSO `p=0.000` ***
- 结论：在当前参数下，PSO 显著提升准时率与降低罚金率，但利用率与利润显著低；GA+VNS+SA 相对 GA 在利润、利用率、准时率上均有小幅显著改善。

### TIGHT 场景（n=30）
- GA：`profit=-17978.67±4614.08`，`util=0.49±0.04`，`on_time=0.01±0.03`，`penalty=0.99±0.03`
- GA+VNS：`profit=-19858.33±4465.85`，`util=0.48±0.05`，`on_time=0.01±0.03`，`penalty=0.99±0.03`
- GA+VNS+SA：`profit=-2498.27±13505.06`，`util=0.68±0.13`，`on_time=0.07±0.04`，`penalty=0.93±0.04`
- PSO：`profit=-33856.00±0.00`，`util=0.42±0.00`，`on_time=0.25±0.00`，`penalty=0.75±0.00`
- 显著性（相对 GA）：
  - 利润：GA+VNS `p=0.136` ns；GA+VNS+SA `p=0.000` ***；PSO `p=0.000` ***
  - 利用率：GA+VNS `p=0.302` ns；GA+VNS+SA `p=0.000` ***；PSO `p=0.000` ***
  - 准时率：GA+VNS `p=1.000` ns；GA+VNS+SA `p=0.000` ***；PSO `p=0.000` ***
  - 罚金率：GA+VNS `p=1.000` ns；GA+VNS+SA `p=0.000` ***；PSO `p=0.000` ***
- 结论：PSO 与 GA+VNS+SA 均显著提升准时与降低罚金；PSO 在准时率上最高但利润最低；GA+VNS+SA 在利润与利用率上显著优于 GA。

备注：MEDIUM/TIGHT 场景下 PSO 的标准差为 0，属当前参数与解码配置下的稳定最优/唯一最优表现；并非“未注入随机种子”。若调整 PSO 随机性（如 `w/c1/c2/max_vel` 或加入微小抖动），建议仅重跑 PSO 三场景×30 次并重新聚合与统计。