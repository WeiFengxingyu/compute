#!/usr/bin/env python3
"""
Plot M8 stage comparison figures across urgency scenarios.
"""
import csv
import statistics
from pathlib import Path

try:
    import matplotlib.pyplot as plt
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

BASE = Path(__file__).parent.parent
OUTPUT_DIR = BASE / "m8_plots"

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

def get_means_stds(scenario):
    """Get means and stds for all algorithms in a scenario."""
    algorithms = ["GA", "GA+VNS", "GA+VNS+SA", "PSO"]
    metrics = ['profit', 'utilization_rate', 'on_time_rate', 'penalty_rate']
    
    results = {}
    
    for algo in algorithms:
        key = (algo, scenario)
        path = SCENARIO_FILES.get(key)
        if path and path.exists():
            rows = read_csv(path)
            rows = dedupe_by_seed(rows)
            
            algo_results = {}
            for metric in metrics:
                values = [row[metric] for row in rows if metric in row]
                if values:
                    algo_results[metric] = {
                        'mean': statistics.mean(values),
                        'std': statistics.stdev(values) if len(values) > 1 else 0,
                        'count': len(values)
                    }
                else:
                    algo_results[metric] = {'mean': 0, 'std': 0, 'count': 0}
                    
            results[algo] = algo_results
            
    return results

def create_summary_table():
    """Create a markdown summary table if matplotlib is not available."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    summary_file = OUTPUT_DIR / "m8_summary_table.md"
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("# M8 阶段：不同订单紧迫度场景对比实验 - 总结表格\n\n")
        
        scenarios = ["loose", "medium", "tight"]
        algorithms = ["GA", "GA+VNS", "GA+VNS+SA", "PSO"]
        metrics = ['profit', 'utilization_rate', 'on_time_rate', 'penalty_rate']
        
        for scenario in scenarios:
            f.write(f"## {scenario.upper()} 场景\n\n")
            
            results = get_means_stds(scenario)
            
            if not results:
                f.write("无有效数据\n\n")
                continue
                
            f.write("| 算法 | 利润 | 利用率 | 准时率 | 惩罚率 | 样本数 |\n")
            f.write("|------|------|--------|--------|--------|--------|\n")
            
            for algo in algorithms:
                if algo not in results:
                    f.write(f"| {algo} | N/A | N/A | N/A | N/A | 0 |\n")
                    continue
                    
                row_data = []
                for metric in metrics:
                    metric_data = results[algo][metric]
                    if metric_data['count'] > 0:
                        if metric_data['std'] > 0:
                            value_str = f"{metric_data['mean']:.2f}±{metric_data['std']:.2f}"
                        else:
                            value_str = f"{metric_data['mean']:.2f}"
                    else:
                        value_str = "N/A"
                    row_data.append(value_str)
                    
                count = results[algo]['profit']['count']
                f.write(f"| {algo} | {row_data[0]} | {row_data[1]} | {row_data[2]} | {row_data[3]} | {count} |\n")
                
            f.write("\n")
            
    print(f"✅ 总结表格已保存到: {summary_file}")

def plot_comparison_figures():
    """Create comparison figures."""
    if not MATPLOTLIB_AVAILABLE:
        print("⚠️ matplotlib 不可用，生成总结表格替代")
        create_summary_table()
        return
        
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    scenarios = ["loose", "medium", "tight"]
    algorithms = ["GA", "GA+VNS", "GA+VNS+SA", "PSO"]
    
    # 1. 利润对比图
    plt.figure(figsize=(12, 8))
    
    for i, scenario in enumerate(scenarios):
        plt.subplot(2, 2, i+1)
        
        results = get_means_stds(scenario)
        if not results:
            continue
            
        means = []
        stds = []
        labels = []
        
        for algo in algorithms:
            if algo in results:
                profit_data = results[algo]['profit']
                means.append(profit_data['mean'])
                stds.append(profit_data['std'])
                labels.append(algo)
                
        x_pos = np.arange(len(labels))
        
        bars = plt.bar(x_pos, means, yerr=stds, capsize=5, alpha=0.7)
        plt.xlabel('算法')
        plt.ylabel('利润')
        plt.title(f'{scenario.upper()} 场景 - 利润对比')
        plt.xticks(x_pos, labels, rotation=45)
        plt.grid(True, alpha=0.3)
        
        # 添加数值标签
        for j, (mean, std) in enumerate(zip(means, stds)):
            plt.text(j, mean + std + 0.01*max(means), f'{mean:.0f}', 
                    ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "m8_profit_comparison.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    # 2. 准时率对比图
    plt.figure(figsize=(12, 8))
    
    for i, scenario in enumerate(scenarios):
        plt.subplot(2, 2, i+1)
        
        results = get_means_stds(scenario)
        if not results:
            continue
            
        means = []
        stds = []
        labels = []
        
        for algo in algorithms:
            if algo in results:
                on_time_data = results[algo]['on_time_rate']
                means.append(on_time_data['mean'] * 100)  # 转换为百分比
                stds.append(on_time_data['std'] * 100)
                labels.append(algo)
                
        x_pos = np.arange(len(labels))
        
        bars = plt.bar(x_pos, means, yerr=stds, capsize=5, alpha=0.7, color='green')
        plt.xlabel('算法')
        plt.ylabel('准时率 (%)')
        plt.title(f'{scenario.upper()} 场景 - 准时率对比')
        plt.xticks(x_pos, labels, rotation=45)
        plt.ylim(0, 105)
        plt.grid(True, alpha=0.3)
        
        # 添加数值标签
        for j, (mean, std) in enumerate(zip(means, stds)):
            plt.text(j, mean + std + 1, f'{mean:.1f}%', 
                    ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "m8_on_time_rate_comparison.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    # 3. 利用率对比图
    plt.figure(figsize=(12, 8))
    
    for i, scenario in enumerate(scenarios):
        plt.subplot(2, 2, i+1)
        
        results = get_means_stds(scenario)
        if not results:
            continue
            
        means = []
        stds = []
        labels = []
        
        for algo in algorithms:
            if algo in results:
                util_data = results[algo]['utilization_rate']
                means.append(util_data['mean'] * 100)  # 转换为百分比
                stds.append(util_data['std'] * 100)
                labels.append(algo)
                
        x_pos = np.arange(len(labels))
        
        bars = plt.bar(x_pos, means, yerr=stds, capsize=5, alpha=0.7, color='blue')
        plt.xlabel('算法')
        plt.ylabel('利用率 (%)')
        plt.title(f'{scenario.upper()} 场景 - 利用率对比')
        plt.xticks(x_pos, labels, rotation=45)
        plt.ylim(0, 105)
        plt.grid(True, alpha=0.3)
        
        # 添加数值标签
        for j, (mean, std) in enumerate(zip(means, stds)):
            plt.text(j, mean + std + 1, f'{mean:.1f}%', 
                    ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "m8_utilization_comparison.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    # 4. 综合对比雷达图
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), subplot_kw=dict(projection='polar'))
    
    metrics = ['利润', '利用率', '准时率', '低惩罚率']
    metric_keys = ['profit', 'utilization_rate', 'on_time_rate', 'penalty_rate']
    
    for i, scenario in enumerate(scenarios):
        ax = axes[i]
        
        results = get_means_stds(scenario)
        if not results:
            continue
            
        # 计算角度
        angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
        angles += angles[:1]  # 闭合图形
        
        # 为每个算法绘制雷达图
        colors = ['red', 'blue', 'green', 'orange']
        
        for j, algo in enumerate(algorithms):
            if algo not in results:
                continue
                
            values = []
            for k, metric_key in enumerate(metric_keys):
                metric_data = results[algo][metric_key]
                value = metric_data['mean']
                
                # 惩罚率需要反向（越低越好）
                if metric_key == 'penalty_rate':
                    value = 1 - value
                    
                # 标准化到0-1范围（简单标准化）
                if metric_key == 'profit':
                    # 利润标准化到0-1
                    max_profit = max(results[alg][metric_key]['mean'] for alg in results.keys())
                    if max_profit > 0:
                        value = value / max_profit
                elif metric_key in ['utilization_rate', 'on_time_rate']:
                    # 利用率、准时率已经是0-1，保持不变
                    pass
                    
                values.append(value)
                
            values += values[:1]  # 闭合图形
            
            ax.plot(angles, values, 'o-', linewidth=2, label=algo, color=colors[j])
            ax.fill(angles, values, alpha=0.25, color=colors[j])
            
        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(metrics)
        ax.set_ylim(0, 1)
        ax.set_title(f'{scenario.upper()} 场景', size=14, fontweight='bold')
        ax.grid(True)
        
        if i == 0:  # 只在第一个子图添加图例
            ax.legend(loc='upper right', bbox_to_anchor=(1.2, 1.0))
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "m8_radar_comparison.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✅ 图表已保存到: {OUTPUT_DIR}")
    
    # 同时生成总结表格
    create_summary_table()

if __name__ == "__main__":
    plot_comparison_figures()