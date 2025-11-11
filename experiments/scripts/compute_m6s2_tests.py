import csv
import random
import math
from pathlib import Path
from math import sqrt

# Optional SciPy for exact p-values
try:
    from scipy import stats as ss  # type: ignore
except Exception:
    ss = None

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

def read_latest_by_seed(path: Path):
    latest = {}
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                seed = int(float(r["seed"]))
            except Exception:
                continue
            latest[seed] = r
    return latest

def paired_t(diff):
    n = len(diff)
    if n < 2:
        return 0.0, 0.0
    mean_d = sum(diff) / n
    var_d = sum((x - mean_d) ** 2 for x in diff) / (n - 1)
    sd = sqrt(var_d)
    t = mean_d / (sd / sqrt(n)) if sd > 0 else 0.0
    return mean_d, t

def p_value(diff, t_stat):
    """Return two-sided p-value for paired differences.
    Uses SciPy if available; otherwise approximates via random sign-flip permutation.
    """
    n = len(diff)
    if n < 2:
        return 1.0
    if ss is not None:
        try:
            res = ss.ttest_1samp(diff, popmean=0.0)
            p = float(res.pvalue)
            if math.isnan(p):
                raise ValueError("pvalue is NaN, fallback to permutation")
            return p
        except Exception:
            pass
    # Fallback: approximate via sign-flip permutation test
    rng = random.Random(42)
    iterations = 20000 if n >= 10 else 10000
    count_extreme = 0
    # Precompute mean and sd function to reuse
    def t_of(vec):
        m = sum(vec) / n
        var = sum((x - m) ** 2 for x in vec) / (n - 1)
        sd = sqrt(var)
        return (m / (sd / sqrt(n))) if sd > 0 else 0.0
    for _ in range(iterations):
        flipped = [(x if rng.random() < 0.5 else -x) for x in diff]
        t_perm = t_of(flipped)
        if abs(t_perm) >= abs(t_stat):
            count_extreme += 1
    return count_extreme / iterations

def scenario_tests(scen: str):
    print(f"\n[{scen}] Paired t-tests (Δ, t, p)")
    # Load latest rows per seed for each algorithm
    rows = {algo: read_latest_by_seed(FILES[(algo, scen)]) for algo in ["GA", "GA+VNS", "GA+VNS+SA"]}
    # Common seeds intersection
    seeds = set(rows["GA"].keys()) & set(rows["GA+VNS"].keys()) & set(rows["GA+VNS+SA"].keys())
    seeds = sorted(seeds)
    def metric_vec(algo, field):
        return [float(rows[algo][s][field]) for s in seeds]
    results = []
    for field in ["profit", "utilization_rate", "on_time_rate", "penalty_rate"]:
        ga = metric_vec("GA", field)
        vns = metric_vec("GA+VNS", field)
        sa = metric_vec("GA+VNS+SA", field)
        d_ga_sa = [sa[i] - ga[i] for i in range(len(seeds))]
        d_vns_sa = [sa[i] - vns[i] for i in range(len(seeds))]
        d_ga_vns = [vns[i] - ga[i] for i in range(len(seeds))]
        m1, t1 = paired_t(d_ga_sa); p1 = p_value(d_ga_sa, t1)
        m2, t2 = paired_t(d_vns_sa); p2 = p_value(d_vns_sa, t2)
        m3, t3 = paired_t(d_ga_vns); p3 = p_value(d_ga_vns, t3)
        print(f"{field}: SA-GA Δ={m1:.2f}, t={t1:.2f}, p={p1:.4f}; SA-VNS Δ={m2:.2f}, t={t2:.2f}, p={p2:.4f}; VNS-GA Δ={m3:.2f}, t={t3:.2f}, p={p3:.4f}")
        results.extend([
            {"scenario": scen, "metric": field, "pair": "SA-GA", "n": len(seeds), "delta": m1, "t": t1, "p": p1},
            {"scenario": scen, "metric": field, "pair": "SA-VNS", "n": len(seeds), "delta": m2, "t": t2, "p": p2},
            {"scenario": scen, "metric": field, "pair": "VNS-GA", "n": len(seeds), "delta": m3, "t": t3, "p": p3},
        ])
    return results

def main():
    print("Paired t-tests across algorithms per scenario")
    all_results = []
    for scen in ["low", "medium", "high"]:
        res = scenario_tests(scen)
        all_results.extend(res)
    # Write markdown summary
    out_dir = Path("paper/figures")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "m6s2_ttests_summary.md"
    lines = []
    lines.append("# M6 阶段2 配对 t 检验摘要\n")
    lines.append("说明：Δ为配对差值（后者-前者）均值，t为t统计量，p为双侧p值。\n")
    # Group by scenario
    for scen in ["low", "medium", "high"]:
        lines.append(f"\n## 场景：{scen}\n")
        lines.append("| 指标 | 对比 | 样本数 n | Δ | t | p |\n")
        lines.append("|---|---|---:|---:|---:|---:|\n")
        for r in [x for x in all_results if x["scenario"] == scen]:
            lines.append(f"| {r['metric']} | {r['pair']} | {r['n']} | {r['delta']:.4f} | {r['t']:.4f} | {r['p']:.6f} |\n")
    with out_path.open("w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"\nSaved summary: {out_path}")

if __name__ == "__main__":
    main()