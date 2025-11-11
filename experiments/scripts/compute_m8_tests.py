#!/usr/bin/env python3
"""
Statistical significance tests for M8 stage experiments.
"""
import csv
import statistics
from pathlib import Path

try:
    from scipy import stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

BASE = Path(__file__).parent.parent

SCENARIO_FILES = {
    ("GA", "loose"): BASE / "batch_ga-loose-m6s3_summary.csv",
    ("GA+VNS", "loose"): BASE / "batch_ga-vns-loose-m6s3_summary.csv", 
    ("GA+VNS+SA", "loose"): BASE / "batch_ga-vns-sa-loose-m6s3_summary.csv",
    ("PSO", "loose"): BASE / "batch_pso-loose-m6s3_summary.csv",
    
    ("GA", "medium"): BASE / "batch_ga-only-m6s2-wage-medium_summary.csv",
    ("GA+VNS", "medium"): BASE / "batch_ga-vns-m6s2-wage-medium_summary.csv",
    ("GA+VNS+SA", "medium"): BASE / "batch_ga-vns-sa-m6s2-wage-medium_summary.csv",
    ("PSO", "medium"): BASE / "batch_pso-medium-m6s3_summary.csv",
    
    ("GA", "tight"): BASE / "batch_ga-tight-m6s3_summary.csv",
    ("GA+VNS", "tight"): BASE / "batch_ga-vns-tight-m6s3_summary.csv",
    ("GA+VNS+SA", "tight"): BASE / "batch_ga-vns-sa-tight-m6s3_summary.csv", 
    ("PSO", "tight"): BASE / "batch_pso-tight-m6s3_summary.csv",
}

def read_csv(path):
    """Read CSV and cast numeric fields."""
    rows = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            for key in ['profit', 'utilization_rate', 'on_time_rate', 'penalty_rate']:
                if key in row:
                    row[key] = float(row[key])
            rows.append(row)
    return rows

def dedupe_by_seed(rows):
    """Keep only the first occurrence of each seed."""
    seen = set()
    out = []
    for row in rows:
        seed = row.get('seed', row.get('seed_value', None))
        if seed is None:
            out.append(row)
            continue
        if seed not in seen:
            seen.add(seed)
            out.append(row)
    return out

def paired_t_test(values1, values2, name1, name2, metric):
    """Perform paired t-test."""
    if not SCIPY_AVAILABLE:
        return "scipy 不可用"
    
    if len(values1) != len(values2):
        return f"样本数量不匹配: {len(values1)} vs {len(values2)}"
        
    if len(values1) < 2:
        return "样本数量不足 (n<2)"
        
    try:
        t_stat, p_value = stats.ttest_rel(values1, values2)
        significance = "***" if p_value < 0.001 else "**" if p_value < 0.01 else "*" if p_value < 0.05 else "ns"
        return f"t={t_stat:.2f}, p={p_value:.3f}{significance}"
    except Exception as e:
        return f"计算错误: {str(e)}"

def main():
    print("# M8 阶段：不同订单紧迫度场景对比实验 - 统计检验\n")
    
    if not SCIPY_AVAILABLE:
        print("⚠️ 警告：scipy 库未安装，无法进行统计检验。请安装 scipy 后重新运行。\n")
    
    scenarios = ["loose", "medium", "tight"]
    algorithms = ["GA", "GA+VNS", "GA+VNS+SA", "PSO"]
    metrics = ['profit', 'utilization_rate', 'on_time_rate', 'penalty_rate']
    
    for scenario in scenarios:
        print(f"## {scenario.upper()} 场景\n")
        
        # 读取数据
        data = {}
        for algo in algorithms:
            key = (algo, scenario)
            path = SCENARIO_FILES.get(key)
            if path and path.exists():
                rows = read_csv(path)
                rows = dedupe_by_seed(rows)
                data[algo] = rows
                print(f"- {algo}: {len(rows)} 条有效记录\n")
            else:
                print(f"- {algo}: 文件不存在 {path}\n")
                
        if len(data) < 2:
            print("数据不足，无法进行统计检验\n")
            continue
            
        # 进行配对t检验（GA作为基准）
        print("### 与GA基准算法的配对t检验\n")
        
        if "GA" not in data:
            print("GA基准数据缺失\n")
            continue
            
        for metric in metrics:
            print(f"#### {metric.upper()}\n")
            
            # 获取GA基准值
            ga_values = [row[metric] for row in data["GA"] if metric in row]
            
            print("| 对比算法 | 平均值±标准差 | t检验结果 |")
            print("|----------|---------------|-----------|")
            
            for algo in algorithms:
                if algo == "GA" or algo not in data:
                    continue
                    
                algo_values = [row[metric] for row in data[algo] if metric in row]
                
                if len(ga_values) != len(algo_values):
                    test_result = f"样本数量不匹配: {len(ga_values)} vs {len(algo_values)}"
                else:
                    test_result = paired_t_test(ga_values, algo_values, "GA", algo, metric)
                    
                # 计算平均值和标准差
                if algo_values:
                    mean_val = statistics.mean(algo_values)
                    if len(algo_values) > 1:
                        std_val = statistics.stdev(algo_values)
                        stats_str = f"{mean_val:.2f}±{std_val:.2f}"
                    else:
                        stats_str = f"{mean_val:.2f}"
                else:
                    stats_str = "N/A"
                    
                print(f"| {algo} | {stats_str} | {test_result} |")
                
            print()

if __name__ == "__main__":
    main()