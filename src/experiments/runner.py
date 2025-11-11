import argparse
import csv
import json
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


# 场景工资系数映射（M6 阶段2）
SCENARIO_WAGE_MULTIPLIERS: Dict[str, List[float]] = {
    "wage-low":   [1.0, 1.05, 1.1, 1.2, 1.3, 1.15],
    "wage-medium": [1.0, 1.1, 1.2, 1.35, 1.5, 1.3],
    "wage-high":  [1.0, 1.15, 1.3, 1.5, 1.7, 1.4],
}


def find_run_dir(runs_dir: str, tag: str, seed: int) -> Optional[Path]:
    """Find the latest run directory matching tag and seed.

    Pattern: run-YYYYMMDD_HHMMSS_<tag>_seed<SEED>
    """
    base = Path(runs_dir)
    pattern = f"run-*_{tag}_seed{seed}"
    candidates = [p for p in base.glob(pattern) if p.is_dir()]
    if not candidates:
        return None
    # Sort by modification time desc, pick latest
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def read_metrics(run_dir: Path) -> Optional[Dict]:
    """Read metrics.json if exists."""
    metrics_path = run_dir / "metrics.json"
    if metrics_path.exists():
        with open(metrics_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def write_summary_row(summary_csv: Path, row: Dict[str, Optional[float]], header: List[str]):
    """Append one summary row into CSV, creating header if file not exists."""
    file_exists = summary_csv.exists()
    summary_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_csv, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def prepare_scenario_config(base_config_path: str, scenario: str, runs_dir: str) -> str:
    """Load base config.json, override wage_multiplier_per_slot by scenario, write a new file.

    Returns the path to the scenario-specific config JSON.
    """
    if scenario not in SCENARIO_WAGE_MULTIPLIERS:
        raise ValueError(f"Unknown scenario '{scenario}'. Available: {list(SCENARIO_WAGE_MULTIPLIERS.keys())}")
    with open(base_config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["wage_multiplier_per_slot"] = SCENARIO_WAGE_MULTIPLIERS[scenario]
    scripts_dir = Path(runs_dir) / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    out_path = scripts_dir / f"config_{scenario}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    return str(out_path)


def build_cmd(py_exe: str, args: argparse.Namespace, seed: int) -> List[str]:
    """Compose the command to run one experiment via src.main.

    Map runner options to src.main CLI flags: --pop, --pc, --pm, --out.
    """
    cmd = [
        py_exe, "-m", "src.main",
        "--horizon", str(args.horizon),
        "--generations", str(args.generations),
        "--pop", str(args.population),
        "--pc", str(args.crossover),
        "--pm", str(args.mutation),
        "--config", args.config,
        "--orders", args.orders,
        "--out", args.outdir,
        "--runs_dir", args.runs_dir,
        "--exp_tag", args.exp_tag,
        "--seed", str(seed),
    ]
    # forward local search flags if provided
    if getattr(args, "local_search", None):
        cmd += ["--local_search", args.local_search]
    if getattr(args, "ls_rounds", None) is not None:
        cmd += ["--ls_rounds", str(args.ls_rounds)]
    if getattr(args, "ls_attempts", None) is not None:
        cmd += ["--ls_attempts", str(args.ls_attempts)]
    # forward soft fitness flags
    if getattr(args, "soft_deadline", None):
        cmd += ["--soft_deadline"]
    if getattr(args, "soft_alpha", None) is not None:
        cmd += ["--soft_alpha", str(args.soft_alpha)]
    if getattr(args, "soft_beta", None) is not None:
        cmd += ["--soft_beta", str(args.soft_beta)]
    if getattr(args, "soft_gamma", None) is not None:
        cmd += ["--soft_gamma", str(args.soft_gamma)]
    # forward SA flags
    if getattr(args, "sa_enabled", None):
        cmd += ["--sa_enabled"]
    if getattr(args, "sa_initial_temp", None) is not None:
        cmd += ["--sa_initial_temp", str(args.sa_initial_temp)]
    if getattr(args, "sa_cooling", None) is not None:
        cmd += ["--sa_cooling", str(args.sa_cooling)]
    if getattr(args, "sa_moves_per_temp", None) is not None:
        cmd += ["--sa_moves_per_temp", str(args.sa_moves_per_temp)]
    if getattr(args, "sa_temps", None) is not None:
        cmd += ["--sa_temps", str(args.sa_temps)]
    # forward PSO flags
    if getattr(args, "pso_enabled", None):
        cmd += ["--pso_enabled"]
    if getattr(args, "pso_particles", None) is not None:
        cmd += ["--pso_particles", str(args.pso_particles)]
    if getattr(args, "pso_iterations", None) is not None:
        cmd += ["--pso_iterations", str(args.pso_iterations)]
    if getattr(args, "pso_c1", None) is not None:
        cmd += ["--pso_c1", str(args.pso_c1)]
    if getattr(args, "pso_c2", None) is not None:
        cmd += ["--pso_c2", str(args.pso_c2)]
    if getattr(args, "pso_w", None) is not None:
        cmd += ["--pso_w", str(args.pso_w)]
    return cmd


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Batch runner for compute project: run multiple seeds and aggregate metrics",
    )
    ap.add_argument("--exp_tag", required=True, help="Tag to annotate the experiment method/version (e.g., ga-v0.1)")
    ap.add_argument("--horizon", type=int, default=30)
    ap.add_argument("--generations", type=int, default=100)
    ap.add_argument("--population", type=int, default=60)
    ap.add_argument("--crossover", type=float, default=0.9)
    ap.add_argument("--mutation", type=float, default=0.1)
    ap.add_argument("--config", default="data/config.json")
    ap.add_argument("--orders", default="data/orders.json")
    ap.add_argument("--outdir", default="results")
    ap.add_argument("--runs_dir", default="experiments")
    ap.add_argument("--local_search", choices=["none", "vns"], default="none", help="局部搜索方法")
    ap.add_argument("--ls_rounds", type=int, default=3, help="VNS轮数")
    ap.add_argument("--ls_attempts", type=int, default=100, help="每邻域尝试次数")
    # M3.1: soft deadline guidance flags
    ap.add_argument("--soft_deadline", action="store_true", help="启用截止软约束权重引导适应度")
    ap.add_argument("--soft_alpha", type=float, default=0.5, help="截止接近度软权重系数 alpha")
    ap.add_argument("--soft_beta", type=float, default=0.2, help="未按期单位软惩罚系数 beta")
    ap.add_argument("--soft_gamma", type=float, default=0.0, help="高工资时段软引导系数 gamma")
    # M4: SA flags
    ap.add_argument("--sa_enabled", action="store_true", help="启用模拟退火（SA）二次优化")
    ap.add_argument("--sa_initial_temp", default="auto", help="初始温度，数值或 'auto'")
    ap.add_argument("--sa_cooling", type=float, default=0.95, help="降温系数（0-1）")
    ap.add_argument("--sa_moves_per_temp", type=int, default=150, help="每温度尝试的移动次数")
    ap.add_argument("--sa_temps", type=int, default=20, help="温度层数")
    # M5: PSO flags
    ap.add_argument("--pso_enabled", action="store_true", help="启用粒子群优化（PSO）算法")
    ap.add_argument("--pso_particles", type=int, default=30, help="粒子数量")
    ap.add_argument("--pso_iterations", type=int, default=200, help="PSO迭代次数")
    ap.add_argument("--pso_c1", type=float, default=2.0, help="认知系数c1")
    ap.add_argument("--pso_c2", type=float, default=2.0, help="社会系数c2")
    ap.add_argument("--pso_w", type=float, default=0.9, help="惯性权重w")
    # M6 阶段2：场景支持（工资系数不同场景）
    ap.add_argument("--scenario", choices=list(SCENARIO_WAGE_MULTIPLIERS.keys()), help="单场景：工资系数方案")
    ap.add_argument("--scenarios", nargs="*", choices=list(SCENARIO_WAGE_MULTIPLIERS.keys()), help="多场景列表：一次批量跑多个场景")
    ap.add_argument("--append_scenario_to_tag", action="store_true", help="将场景名追加到 exp_tag（如 ga-vns -> ga-vns-wage-low）")
    ap.add_argument("--seeds", type=int, nargs="*", default=[], help="Explicit seed list, e.g., --seeds 1 2 3")
    ap.add_argument("--seed-start", type=int, help="Start of seed range (inclusive)")
    ap.add_argument("--seed-end", type=int, help="End of seed range (inclusive)")
    ap.add_argument("--dry-run", action="store_true", help="Print commands without executing")
    return ap.parse_args()


def main():
    args = parse_args()
    # Build seed list
    if args.seeds:
        seeds = args.seeds
    elif args.seed_start is not None and args.seed_end is not None:
        seeds = list(range(args.seed_start, args.seed_end + 1))
    else:
        seeds = [42, 123, 2025]

    py_exe = sys.executable
    header = [
        "timestamp", "exp_tag", "seed",
        "profit", "total_revenue", "production_cost", "wage_cost", "penalty",
        "utilization_rate", "on_time_rate", "penalty_rate",
        "run_dir",
    ]

    # Determine scenarios to run
    scenario_list: List[str] = []
    if args.scenarios:
        scenario_list = args.scenarios
    elif args.scenario:
        scenario_list = [args.scenario]
    else:
        scenario_list = [None]

    # Iterate scenarios (or None for default config)
    for scenario in scenario_list:
        current_tag = args.exp_tag
        effective_config = args.config
        if scenario:
            # Prepare scenario config file and tag suffix
            effective_config = prepare_scenario_config(args.config, scenario, args.runs_dir)
            if args.append_scenario_to_tag:
                current_tag = f"{args.exp_tag}-{scenario}"
        summary_csv = Path(args.runs_dir) / f"batch_{current_tag}_summary.csv"
        print(f"[Batch] exp_tag={current_tag} scenario={scenario or 'default'} seeds={seeds} gens={args.generations} pop={args.population}")

        # Build a per-scenario args namespace to avoid mutating the original
        scenario_args = argparse.Namespace(**vars(args))
        scenario_args.config = effective_config
        scenario_args.exp_tag = current_tag

        for seed in seeds:
            cmd = build_cmd(py_exe, scenario_args, seed)
            print("[Run] ", " ".join(cmd))
            if args.dry_run:
                row = {
                    "timestamp": _now_iso(),
                    "exp_tag": current_tag,
                    "seed": seed,
                    "profit": None,
                    "total_revenue": None,
                    "production_cost": None,
                    "wage_cost": None,
                    "penalty": None,
                    "utilization_rate": None,
                    "on_time_rate": None,
                    "penalty_rate": None,
                    "run_dir": "",
                }
                write_summary_row(summary_csv, row, header)
                continue

            try:
                subprocess.run(cmd, check=True)
            except subprocess.CalledProcessError as e:
                print(f"[Error] run failed for seed={seed}: {e}")
                row = {
                    "timestamp": _now_iso(),
                    "exp_tag": current_tag,
                    "seed": seed,
                    "profit": None,
                    "total_revenue": None,
                    "production_cost": None,
                    "wage_cost": None,
                    "penalty": None,
                    "utilization_rate": None,
                    "on_time_rate": None,
                    "penalty_rate": None,
                    "run_dir": "",
                }
                write_summary_row(summary_csv, row, header)
                continue

            run_dir = find_run_dir(args.runs_dir, current_tag, seed)
            metrics = read_metrics(run_dir) if run_dir else None
            row = {
                "timestamp": _now_iso(),
                "exp_tag": current_tag,
                "seed": seed,
                "profit": metrics.get("profit") if metrics else None,
                "total_revenue": metrics.get("total_revenue") if metrics else None,
                "production_cost": metrics.get("production_cost") if metrics else None,
                "wage_cost": metrics.get("wage_cost") if metrics else None,
                "penalty": metrics.get("penalty") if metrics else None,
                "utilization_rate": metrics.get("utilization_rate") if metrics else None,
                "on_time_rate": metrics.get("on_time_rate") if metrics else None,
                "penalty_rate": metrics.get("penalty_rate") if metrics else None,
                "run_dir": str(run_dir) if run_dir else "",
            }
            write_summary_row(summary_csv, row, header)
            print(f"[Saved] {summary_csv}")


if __name__ == "__main__":
    main()