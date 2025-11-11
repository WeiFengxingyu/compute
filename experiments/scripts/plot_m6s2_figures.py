import csv
import os
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

FILES = {
    ("GA", "low"): BASE / "batch_ga-only-m6s2-wage-low_summary.csv",
    ("GA", "medium"): BASE / "batch_ga-only-m6s2-wage-medium_summary.csv",
    ("GA", "high"): BASE / "batch_ga-only-m6s2-wage-high_summary.csv",
    ("GA+VNS", "low"): BASE / "batch_ga-vns-m6s2-wage-low_summary.csv",
    ("GA+VNS", "medium"): BASE / "batch_ga-vns-m6s2-wage-medium_summary.csv",
    ("GA+VNS", "high"): BASE / "batch_ga-vns-m6s2-wage-high_summary.csv",
    ("GA+VNS+SA", "low"): BASE / "batch_ga-vns-sa-m6s2-wage-low_summary.csv",
    ("GA+VNS+SA", "medium"): BASE / "batch_ga-vns-sa-m6s2-wage-medium_summary.csv",
    ("GA+VNS+SA", "high"): BASE / "batch_ga-vns-sa-m6s2-wage-high_summary.csv",
}

ALGOS = ["GA", "GA+VNS", "GA+VNS+SA"]
SCENARIOS = ["low", "medium", "high"]

def read_rows(path: Path):
    rows = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                r["seed"] = int(float(r["seed"]))
                for k in [
                    "profit",
                    "total_revenue",
                    "production_cost",
                    "wage_cost",
                    "penalty",
                    "utilization_rate",
                    "on_time_rate",
                    "penalty_rate",
                ]:
                    r[k] = float(r[k])
            except Exception:
                continue
            rows.append(r)
    return rows

def dedup_last_by_seed(rows):
    latest = {}
    for r in rows:
        latest[r["seed"]] = r
    return list(latest.values())

def mean(xs):
    return sum(xs) / len(xs) if xs else 0.0

def stdev(xs):
    n = len(xs)
    if n < 2:
        return 0.0
    mu = mean(xs)
    var = sum((x - mu) ** 2 for x in xs) / (n - 1)
    return var ** 0.5

def ensure_dir(p):
    os.makedirs(p, exist_ok=True)

def try_import_matplotlib():
    try:
        import matplotlib.pyplot as plt
        return plt
    except Exception as e:
        print("[Warn] matplotlib not available:", e)
        return None

def profit_boxplots(plt, out_dir):
    fig, axes = plt.subplots(1, 3, figsize=(14, 4), sharey=True)
    for i, scen in enumerate(SCENARIOS):
        data = []
        for algo in ALGOS:
            rows = dedup_last_by_seed(read_rows(FILES[(algo, scen)]))
            profits = [r["profit"] for r in rows]
            data.append(profits)
        axes[i].boxplot(data, labels=ALGOS)
        axes[i].set_title(f"Profit box ({scen})")
        axes[i].axhline(0, color="gray", linewidth=0.8, linestyle="--")
        axes[i].set_ylabel("Profit") if i == 0 else None
    fig.tight_layout()
    fig.savefig(out_dir / "m6s2_profit_box_by_scenario.png", dpi=150)
    plt.close(fig)

def metric_bars(plt, out_dir, metric_key: str, title: str, yfmt=None):
    fig, axes = plt.subplots(1, 3, figsize=(14, 4), sharey=True)
    for i, scen in enumerate(SCENARIOS):
        means = []
        stds = []
        for algo in ALGOS:
            rows = dedup_last_by_seed(read_rows(FILES[(algo, scen)]))
            vals = [r[metric_key] for r in rows]
            means.append(mean(vals))
            stds.append(stdev(vals))
        x = range(len(ALGOS))
        axes[i].bar(x, means, yerr=stds, capsize=4, color=["#4e79a7", "#59a14f", "#f28e2b"])
        axes[i].set_xticks(x)
        axes[i].set_xticklabels(ALGOS)
        axes[i].set_title(f"{title} ({scen})")
        if yfmt:
            axes[i].yaxis.set_major_formatter(yfmt)
    fig.tight_layout()
    fname = f"m6s2_{metric_key}_bars_by_scenario.png"
    fig.savefig(out_dir / fname, dpi=150)
    plt.close(fig)

def write_summary_table(out_dir: Path):
    # Fallback summary when matplotlib is missing
    path = out_dir / "m6s2_averages_table.md"
    lines = ["# M6S2 Averages (mean ± std)\n"]
    for scen in SCENARIOS:
        lines.append(f"\n## {scen}\n")
        for algo in ALGOS:
            rows = dedup_last_by_seed(read_rows(FILES[(algo, scen)]))
            def ms(key):
                vals = [r[key] for r in rows]
                return mean(vals), stdev(vals)
            pm, ps = ms("profit")
            um, us = ms("utilization_rate")
            om, os = ms("on_time_rate")
            rm, rs = ms("penalty_rate")
            lines.append(
                f"- {algo}: profit={pm:.2f} ± {ps:.2f}, util={um:.4f} ± {us:.4f}, "
                f"on_time={om:.3f} ± {os:.3f}, penalty_rate={rm:.3f} ± {rs:.3f}\n"
            )
    with path.open("w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"[Saved] {path}")

def main():
    out_dir = Path("paper/figures")
    ensure_dir(out_dir)
    plt = try_import_matplotlib()
    if plt is None:
        write_summary_table(out_dir)
        return
    profit_boxplots(plt, out_dir)
    # Bars for utilization / on_time / penalty_rate
    metric_bars(plt, out_dir, "utilization_rate", "Utilization")
    metric_bars(plt, out_dir, "on_time_rate", "On-time rate")
    metric_bars(plt, out_dir, "penalty_rate", "Penalty trigger rate")
    print("[Saved] figures to", out_dir)

if __name__ == "__main__":
    main()