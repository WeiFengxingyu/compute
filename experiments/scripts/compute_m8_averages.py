#!/usr/bin/env python3
"""
Compute M8 stage averages across urgency scenarios.
"""
import csv
import statistics
from pathlib import Path

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

def mean_std(values):
    """Return mean ± std string."""
    if not values:
        return "N/A"
    m = statistics.mean(values)
    if len(values) == 1:
        return f"{m:.2f}"
    s = statistics.stdev(values)
    return f"{m:.2f}±{s:.2f}"

def main():
    print("# M8 阶段：不同订单紧迫度场景对比实验 - 平均值统计\n")
    
    scenarios = ["loose", "medium", "tight"]
    algorithms = ["GA", "GA+VNS", "GA+VNS+SA", "PSO"]
    
    for scenario in scenarios:
        print(f"## {scenario.upper()} 场景\n")
        
        # 收集该场景下所有算法的数据
        data = {}
        for algo in algorithms:
            key = (algo, scenario)
            path = SCENARIO_FILES.get(key)
            if path and path.exists():
                rows = read_csv(path)
                rows = dedupe_by_seed(rows)
                data[algo] = rows
                print(f"- {algo}: 读取 {len(rows)} 条有效记录\n")
            else:
                print(f"- {algo}: 文件不存在 {path}\n")
                
        if not data:
            print("无有效数据\n")
            continue
            
        # 计算平均值
        metrics = ['profit', 'utilization_rate', 'on_time_rate', 'penalty_rate']
        
        print("| 算法 | 利润 | 利用率 | 准时率 | 惩罚率 |")
        print("|------|------|--------|--------|--------|")
        
        for algo in algorithms:
            if algo not in data:
                print(f"| {algo} | N/A | N/A | N/A | N/A |")
                continue
                
            values = {}
            for metric in metrics:
                vals = [row[metric] for row in data[algo] if metric in row]
                values[metric] = mean_std(vals) if vals else "N/A"
                
            print(f"| {algo} | {values['profit']} | {values['utilization_rate']} | "
                  f"{values['on_time_rate']} | {values['penalty_rate']} |")
                  
        print()

if __name__ == "__main__":
    main()