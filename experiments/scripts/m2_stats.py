import csv
import statistics
from pathlib import Path


def latest_rows_by_seed(csv_path: Path, seed_start: int, seed_end: int):
    seeds = set(range(seed_start, seed_end + 1))
    latest = {}
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                s = int(row["seed"])
            except Exception:
                continue
            if s not in seeds:
                continue
            if not row.get("profit"):
                continue
            ts = row.get("timestamp", "")
            prev = latest.get(s)
            if prev is None or ts > prev.get("timestamp", ""):
                latest[s] = row
    return latest


def compute_stats(latest: dict):
    metrics = [
        "profit",
        "total_revenue",
        "production_cost",
        "wage_cost",
        "penalty",
        "utilization_rate",
        "on_time_rate",
        "penalty_rate",
    ]
    print("Selected seeds:", sorted(latest.keys()))
    for m in metrics:
        vals = []
        for s in sorted(latest.keys()):
            v = latest[s].get(m)
            if v is None or v == "":
                continue
            try:
                vals.append(float(v))
            except Exception:
                pass
        if not vals:
            print(f"{m}: no data")
            continue
        mean = sum(vals) / len(vals)
        std = statistics.pstdev(vals)
        print(f"{m}: mean={mean:.2f} std={std:.2f} n={len(vals)}")


def main():
    csv_path = Path("experiments/batch_ga-enhanced_summary.csv")
    latest = latest_rows_by_seed(csv_path, 201, 205)
    compute_stats(latest)


if __name__ == "__main__":
    main()