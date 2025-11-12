# 论文大纲（中文）

## 拟定标题
- 强化适应度驱动的生产线调度优化：多场景下的算法比较与复现
- Reinforced Fitness for Production Line Scheduling: Multi‑Scenario Comparative Study

## 核心贡献
- 提出并验证“强化适应度函数”（提高截止权重与软惩罚系数）显著提升准时率并抑制罚金。
- 在 LOOSE/MEDIUM/TIGHT 三场景下，系统比较 GA、GA+VNS、GA+VNS+SA、PSO 四算法的利润、利用率、准时率、惩罚率表现与统计显著性。
- 明确 PSO 的复现性（受 `--seed` 控制），并给出参数变动的最小重跑策略与结果同步流程。
- 提供可复现的脚本与图表、统计表，支撑论文数据透明化复现。

## 结构大纲
1. 摘要
   - 研究问题、方法概述、关键结论（强化适应度有效；PSO 在时限遵守上优越；GA+VNS+SA 在利用率/利润上更均衡）。
2. 引言
   - 生产线调度的挑战；交付期限与成本的平衡；本文问题设定与目标；贡献列表。
3. 相关工作
   - 进化算法（GA）、邻域搜索（VNS/SA）、群智能（PSO）在调度中的应用；软惩罚与截止建模；本工作与现有方法的差异。
4. 方法
   - 问题建模与指标定义：利润、利用率、准时率、惩罚率。
   - 强化适应度函数：提高截止权重与软惩罚系数（示例超参数 `alpha_deadline`、`beta_late_units`）；作用机理。
   - 算法配置：GA、GA+VNS、GA+VNS+SA、PSO 的关键参数与解码策略（如 EDD 解码）。
5. 实验设置
   - 数据与场景：LOOSE/MEDIUM/TIGHT 的订单紧迫度设定；每算法每场景 n=30。
   - 复现设置：随机源 `--seed`；脚本与路径；聚合与统计流程。
   - 统计方法：均值±标准差；相对 GA 的配对 t 检验（显著性符号 ns/*/***）。
6. 结果
   - 三场景的数值摘要与显著性结果（表格与文字结论）。
   - 关键图表：利润箱线图、利用率柱状图、准时率柱状图、雷达图。
   - 结果解读：时限遵守与成本/效率的权衡；不同算法的优势版图。
7. 讨论
   - 强化适应度的普适性与边界；PSO 参数稳定性与复现性；GA+VNS+SA 的收益/效率取舍。
   - 对业务的建议：优先目标不同的算法选择与参数策略。
8. 结论与未来工作
   - 主要发现与实践价值；未来在多目标/多资源约束、动态订单的扩展方向。
9. 复现与开源资料
   - 数据、脚本、图表与统计表的位置；重跑流程（仅 PSO 参数调整时的最小重跑）。
10. 致谢与参考文献

## 关键数据与图表插入点
- 数值表：`paper/figures/m8_plots/m8_summary_table.md`
- 图表：
  - `paper/figures/m8_plots/m8_profit_comparison.png`
  - `paper/figures/m8_plots/m8_utilization_comparison.png`
  - `paper/figures/m8_plots/m8_on_time_rate_comparison.png`
  - `paper/figures/m8_plots/m8_radar_comparison.png`
- 报告文本参考：`paper/figures/m8_plots/m8_experiment_report.md`