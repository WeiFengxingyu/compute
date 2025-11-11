#!/usr/bin/env python3
"""
Aggregate M8 run summaries into batch CSVs per scenario and algorithm.

Scans run directories like:
  run-YYYYMMDD_HHMMSS_<algo>-<scenario>-m6s3_seed<SEED>

Reads metrics.json and writes batch CSVs expected by downstream scripts:
  batch_ga-loose-m6s3_summary.csv
  batch_ga-vns-loose-m6s3_summary.csv
  batch_ga-vns-sa-loose-m6s3_summary.csv
  batch_pso-loose-m6s3_summary.csv
  batch_pso-medium-m6s3_summary.csv
  batch_ga-tight-m6s3_summary.csv, etc.
"""
import csv
import json
import re
from pathlib import Path

BASE = Path(__file__).parent.parent  # experiments/

# Map friendly names to directory tokens and output filenames
ALGO_MAP = {
    "GA": "ga",
    "GA+VNS": "ga-vns",
    "GA+VNS+SA": "ga-vns-sa",
    "PSO": "pso",
}

SCENARIOS = ["loose", "medium", "tight"]

# Output file mapping
OUTPUT_FILES = {
    ("GA", "loose"): BASE / "batch_ga-loose-m6s3_summary.csv",
    ("GA+VNS", "loose"): BASE / "batch_ga-vns-loose-m6s3_summary.csv",
    ("GA+VNS+SA", "loose"): BASE / "batch_ga-vns-sa-loose-m6s3_summary.csv",
    ("PSO", "loose"): BASE / "batch_pso-loose-m6s3_summary.csv",

    ("GA", "medium"): BASE / "batch_ga-medium-m6s3_summary.csv",  # not used by plots, kept for completeness
    ("GA+VNS", "medium"): BASE / "batch_ga-vns-medium-m6s3_summary.csv",
    ("GA+VNS+SA", "medium"): BASE / "batch_ga-vns-sa-medium-m6s3_summary.csv",
    ("PSO", "medium"): BASE / "batch_pso-medium-m6s3_summary.csv",

    ("GA", "tight"): BASE / "batch_ga-tight-m6s3_summary.csv",
    ("GA+VNS", "tight"): BASE / "batch_ga-vns-tight-m6s3_summary.csv",
    ("GA+VNS+SA", "tight"): BASE / "batch_ga-vns-sa-tight-m6s3_summary.csv",
    ("PSO", "tight"): BASE / "batch_pso-tight-m6s3_summary.csv",
}

SEED_RE = re.compile(r"seed(\d+)")

def extract_seed(name: str) -> int | None:
    m = SEED_RE.search(name)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None

def find_runs(algo_token: str, scenario: str):
    # Directory names follow: run-YYYYMMDD_HHMMSS_<algo>-<scenario>-m6s3_seed<SEED>
    pattern = f"run-*_{algo_token}-{scenario}-m6s3_seed*"
    return sorted(BASE.glob(pattern))

def read_metrics(run_dir: Path) -> dict | None:
    path = run_dir / "metrics.json"
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            m = json.load(f)
        return m
    except Exception:
        return None

def aggregate_for(algo_name: str, scenario: str) -> int:
    """Aggregate one (algo, scenario), return rows count written."""
    algo_token = ALGO_MAP[algo_name]
    out_path = OUTPUT_FILES[(algo_name, scenario)]

    runs = find_runs(algo_token, scenario)
    rows = []
    for run_dir in runs:
        seed = extract_seed(run_dir.name)
        metrics = read_metrics(run_dir)
        if metrics is None:
            continue
        row = {
            "seed": seed,
            "profit": metrics.get("profit"),
            "utilization_rate": metrics.get("utilization_rate"),
            "on_time_rate": metrics.get("on_time_rate"),
            "penalty_rate": metrics.get("penalty_rate"),
        }
        # Only include rows with all required metrics
        if None in row.values():
            # tolerate missing seed
            if row["seed"] is None:
                row.pop("seed")
            # still require metrics
            if any(row[k] is None for k in ["profit","utilization_rate","on_time_rate","penalty_rate"]):
                continue
        rows.append(row)

    if not rows:
        return 0

    # Write CSV
    fields = ["seed", "profit", "utilization_rate", "on_time_rate", "penalty_rate"]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    return len(rows)

def main():
    print("# 聚合M8运行结果为批量CSV\n")
    total = 0
    for scenario in SCENARIOS:
        print(f"## 场景: {scenario}")
        for algo in ALGO_MAP.keys():
            cnt = aggregate_for(algo, scenario)
            out_path = OUTPUT_FILES[(algo, scenario)]
            if cnt == 0:
                print(f"- {algo}: 未找到有效运行或缺少metrics.json -> 跳过 ({out_path.name})")
            else:
                print(f"- {algo}: 写入 {cnt} 条记录 -> {out_path.name}")
                total += cnt
        print()
    print(f"合计写入记录: {total}")

if __name__ == "__main__":
    main()