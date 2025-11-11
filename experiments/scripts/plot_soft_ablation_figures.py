import os
import sys
import math
from typing import Dict, Tuple

import csv


def read_csv_rows(path: str) -> Tuple[list, list]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"CSV not found: {path}")
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)
    header = rows[0]
    data = rows[1:]
    return header, data


def mean_std_from_list(vals: list) -> Tuple[float, float]:
    vals = [float(x) for x in vals if x is not None and x != "" ]
    if len(vals) == 0:
        return float("nan"), float("nan")
    mean = sum(vals) / len(vals)
    if len(vals) > 1:
        var = sum((x - mean) ** 2 for x in vals) / (len(vals) - 1)
        std = math.sqrt(var)
    else:
        std = 0.0
    return mean, std


def summarize(header: list, data: list) -> Dict[str, Tuple[float, float]]:
    metrics = ["profit", "utilization_rate", "on_time_rate", "penalty_rate"]
    out: Dict[str, Tuple[float, float]] = {}
    # Build index map
    idx = {col: i for i, col in enumerate(header)}
    for m in metrics:
        if m in idx:
            col_i = idx[m]
            values = []
            for row in data:
                try:
                    values.append(float(row[col_i]))
                except Exception:
                    continue
            out[m] = mean_std_from_list(values)
    return out


def plot_bars(means_stds: Dict[str, Tuple[float, float]], title: str, ylabel: str, save_path: str):
    try:
        import matplotlib.pyplot as plt
    except Exception as e:
        # Fallback: write markdown summary if matplotlib not available
        md = [f"# {title}", "", "| Metric | Mean | Std |", "|---|---:|---:|"]
        for k, (mu, sd) in means_stds.items():
            md.append(f"| {k} | {mu:.4f} | {sd:.4f} |")
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path.replace('.png', '.md'), 'w', encoding='utf-8') as f:
            f.write("\n".join(md))
        print(f"matplotlib not available; wrote markdown summary: {save_path.replace('.png', '.md')}")
        return

    labels = list(means_stds.keys())
    means = [means_stds[k][0] for k in labels]
    stds = [means_stds[k][1] for k in labels]

    plt.figure(figsize=(7.5, 4.5))
    bars = plt.bar(labels, means, yerr=stds, capsize=6, color=["#3b82f6", "#ef4444"], alpha=0.85)
    plt.title(title)
    plt.ylabel(ylabel)
    plt.grid(axis='y', linestyle='--', alpha=0.3)
    for bar, mu, sd in zip(bars, means, stds):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height(), f"{mu:.2f} ± {sd:.2f}",
                 ha='center', va='bottom', fontsize=9)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.tight_layout()
    plt.savefig(save_path, dpi=160)
    plt.close()
    print(f"Saved figure: {save_path}")


def main():
    root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    # CSVs
    h14_csv = os.path.join(root, "experiments", "batch_ga-vns-soft-h14_summary.csv")
    h30_csv = os.path.join(root, "experiments", "batch_ga-vns-soft-h30_summary.csv")

    h14_header, h14_data = read_csv_rows(h14_csv)
    h30_header, h30_data = read_csv_rows(h30_csv)

    sum_h14 = summarize(h14_header, h14_data)
    sum_h30 = summarize(h30_header, h30_data)

    # Prepare dicts for each metric
    def dict_for(metric: str) -> Dict[str, Tuple[float, float]]:
        return {
            "soft-h14": sum_h14.get(metric, (float("nan"), float("nan"))),
            "soft-h30": sum_h30.get(metric, (float("nan"), float("nan"))),
        }

    figs_dir = os.path.join(root, "paper", "figures")
    os.makedirs(figs_dir, exist_ok=True)

    # Profit bars
    plot_bars(dict_for("profit"), title="软截止消融：利润（均值±标准差）", ylabel="Profit", save_path=os.path.join(figs_dir, "m6s2_soft_profit_bars.png"))
    # Utilization bars
    plot_bars(dict_for("utilization_rate"), title="软截止消融：产线利用率（均值±标准差）", ylabel="Utilization Rate", save_path=os.path.join(figs_dir, "m6s2_soft_utilization_rate_bars.png"))
    # On-time bars
    plot_bars(dict_for("on_time_rate"), title="软截止消融：准时率（均值±标准差）", ylabel="On-time Rate", save_path=os.path.join(figs_dir, "m6s2_soft_on_time_rate_bars.png"))
    # Penalty bars
    plot_bars(dict_for("penalty_rate"), title="软截止消融：罚金触发率（均值±标准差）", ylabel="Penalty Trigger Rate", save_path=os.path.join(figs_dir, "m6s2_soft_penalty_rate_bars.png"))

    # Console summary
    def fmt(mu_sd: Tuple[float, float]) -> str:
        mu, sd = mu_sd
        return f"{mu:.4f} ± {sd:.4f}"

    print("Summary (mean ± std):")
    for m in ["profit", "utilization_rate", "on_time_rate", "penalty_rate"]:
        print(f"  {m}: h14={fmt(sum_h14.get(m, (float('nan'), float('nan'))))}, h30={fmt(sum_h30.get(m, (float('nan'), float('nan'))))}")


if __name__ == "__main__":
    sys.exit(main())