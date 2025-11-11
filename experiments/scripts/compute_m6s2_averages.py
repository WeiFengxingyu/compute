import csv
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

def read_rows(path: Path):
    rows = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            # Cast numeric fields
            for k in [
                "seed",
                "profit",
                "total_revenue",
                "production_cost",
                "wage_cost",
                "penalty",
                "utilization_rate",
                "on_time_rate",
                "penalty_rate",
            ]:
                r[k] = float(r[k]) if k != "seed" else int(float(r[k]))
            rows.append(r)
    return rows

def dedup_last_by_seed(rows):
    # Keep the last occurrence per seed by natural order of file (append semantics)
    latest = {}
    for r in rows:
        latest[r["seed"]] = r
    return list(latest.values())

def mean(values):
    return sum(values) / len(values) if values else 0.0

def stdev(values):
    n = len(values)
    if n < 2:
        return 0.0
    mu = mean(values)
    var = sum((x - mu) ** 2 for x in values) / (n - 1)
    return var ** 0.5

def summarize(rows):
    profits = [r["profit"] for r in rows]
    utils = [r["utilization_rate"] for r in rows]
    on_times = [r["on_time_rate"] for r in rows]
    pen_rates = [r["penalty_rate"] for r in rows]
    revenues = [r["total_revenue"] for r in rows]
    prod_costs = [r["production_cost"] for r in rows]
    wage_costs = [r["wage_cost"] for r in rows]
    penalties = [r["penalty"] for r in rows]

    return {
        "n": len(rows),
        "profit": (mean(profits), stdev(profits)),
        "utilization": (mean(utils), stdev(utils)),
        "on_time": (mean(on_times), stdev(on_times)),
        "penalty_rate": (mean(pen_rates), stdev(pen_rates)),
        "revenue": (mean(revenues), stdev(revenues)),
        "prod_cost": (mean(prod_costs), stdev(prod_costs)),
        "wage_cost": (mean(wage_costs), stdev(wage_costs)),
        "penalty": (mean(penalties), stdev(penalties)),
    }

def main():
    print("Scenario averages (dedup by last row per seed):")
    for scen in ["low", "medium", "high"]:
        print(f"\n[{scen}]")
        for algo in ["GA", "GA+VNS", "GA+VNS+SA"]:
            path = FILES[(algo, scen)]
            rows = read_rows(path)
            rows = dedup_last_by_seed(rows)
            m = summarize(rows)
            pm, ps = m['profit']
            um, us = m['utilization']
            om, os = m['on_time']
            rm, rs = m['penalty_rate']
            print(
                f"{algo}: n={m['n']}, profit={pm:.2f} (±{ps:.2f}), util={um:.4f} (±{us:.4f}), "
                f"on_time={om:.3f} (±{os:.3f}), penalty_rate={rm:.3f} (±{rs:.3f})"
            )

if __name__ == "__main__":
    main()