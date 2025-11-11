import argparse
import json
import os
from typing import Any, Dict, List

from src.data.generator import default_config, generate_orders, save_json
from src.models.entities import Config, Order, SLOTS_PER_DAY, slot_in_day
from src.algorithms.ga import run_ga
from src.algorithms.vns import vns_improve
from src.algorithms.pso import run_pso
from src.utils.run_logger import create_run_dir, save_json as save_json_rl, order_to_dict, write_summary_md


def load_config(path: str) -> Config:
    if not os.path.exists(path):
        cfg = default_config()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        save_json(path, cfg)
    with open(path, "r", encoding="utf-8") as f:
        return Config.from_dict(json.load(f))


def load_orders(path: str, horizon_days: int) -> List[Order]:
    if not os.path.exists(path):
        orders_data = generate_orders(num_orders=12, horizon_days=horizon_days)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        save_json(path, orders_data)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    orders = [Order(**o) for o in data]
    return orders


def save_results(schedule, eval_result, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    result = {
        "schedule": schedule,
        "metrics": {
            "total_revenue": eval_result.total_revenue,
            "production_cost": eval_result.production_cost,
            "wage_cost": eval_result.wage_cost,
            "penalty": eval_result.penalty,
            "profit": eval_result.profit,
            "utilization_rate": eval_result.utilization_rate,
            "on_time_rate": eval_result.on_time_rate,
            "penalty_rate": eval_result.penalty_rate,
        },
        "delivered_per_order": eval_result.delivered_per_order,
    }
    with open(os.path.join(out_dir, "latest_schedule.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


def print_summary(eval_result):
    print("=== 调度评估结果 ===")
    print(f"利润: {eval_result.profit:.2f}")
    print(f"收入: {eval_result.total_revenue:.2f}")
    print(f"生产成本: {eval_result.production_cost:.2f}")
    print(f"工资成本: {eval_result.wage_cost:.2f}")
    print(f"罚款: {eval_result.penalty:.2f}")
    print(f"产线利用率: {eval_result.utilization_rate:.3f}")
    print(f"按时完成率: {eval_result.on_time_rate:.3f}")
    print(f"触发罚款比例: {eval_result.penalty_rate:.3f}")


def main():
    parser = argparse.ArgumentParser(description="智能制造生产调度 - 计算智能大作业")
    parser.add_argument("--config", default="data/config.json", help="配置文件路径")
    parser.add_argument("--orders", default="data/orders.json", help="订单文件路径")
    parser.add_argument("--horizon", type=int, default=7, help="计划视野（天）")
    parser.add_argument("--generations", type=int, default=200, help="GA迭代代数")
    parser.add_argument("--pop", type=int, default=80, help="种群规模")
    parser.add_argument("--pc", type=float, default=0.8, help="交叉率")
    parser.add_argument("--pm", type=float, default=0.08, help="变异率")
    parser.add_argument("--out", default="results", help="输出目录")
    parser.add_argument("--runs_dir", default="experiments", help="实验运行记录目录")
    parser.add_argument("--exp_tag", default="baseline-ga", help="实验标签")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    parser.add_argument("--local_search", choices=["none", "vns"], default="none", help="局部搜索方法")
    parser.add_argument("--ls_rounds", type=int, default=3, help="VNS轮数")
    parser.add_argument("--ls_attempts", type=int, default=100, help="每邻域尝试次数")
    # M3.1: soft deadline guidance in fitness
    parser.add_argument("--soft_deadline", action="store_true", help="启用截止软约束权重引导适应度")
    parser.add_argument("--soft_alpha", type=float, default=0.5, help="截止接近度软权重系数 alpha")
    parser.add_argument("--soft_beta", type=float, default=0.2, help="未按期单位软惩罚系数 beta")
    parser.add_argument("--soft_gamma", type=float, default=0.0, help="高工资时段软引导系数 gamma")
    # M4: SA simulated annealing
    parser.add_argument("--sa_enabled", action="store_true", help="启用模拟退火（SA）二次优化")
    parser.add_argument("--sa_initial_temp", default="auto", help="初始温度，数值或 'auto'")
    parser.add_argument("--sa_cooling", type=float, default=0.95, help="降温系数（0-1）")
    parser.add_argument("--sa_moves_per_temp", type=int, default=150, help="每温度尝试的移动次数")
    parser.add_argument("--sa_temps", type=int, default=20, help="温度层数")
    # M5: PSO particle swarm optimization
    parser.add_argument("--pso_enabled", action="store_true", help="启用粒子群优化（PSO）算法")
    parser.add_argument("--pso_particles", type=int, default=30, help="粒子数量")
    parser.add_argument("--pso_iterations", type=int, default=200, help="PSO迭代次数")
    parser.add_argument("--pso_c1", type=float, default=2.0, help="认知系数c1")
    parser.add_argument("--pso_c2", type=float, default=2.0, help="社会系数c2")
    parser.add_argument("--pso_w", type=float, default=0.9, help="惯性权重w")
    args = parser.parse_args()

    # set seed for reproducibility
    import random
    random.seed(args.seed)

    config = load_config(args.config)
    orders = load_orders(args.orders, args.horizon)

    # Choose algorithm: GA or PSO
    if args.pso_enabled:
        best_schedule, eval_result = run_pso(
            config=config,
            orders=orders,
            horizon_days=args.horizon,
            n_particles=args.pso_particles,
            iterations=args.pso_iterations,
            c1=args.pso_c1,
            c2=args.pso_c2,
            w=args.pso_w,
            use_soft_fitness=args.soft_deadline,
            soft_alpha=args.soft_alpha,
            soft_beta=args.soft_beta,
            soft_gamma=args.soft_gamma,
        )
    else:
        best_schedule, eval_result = run_ga(
            config=config,
            orders=orders,
            horizon_days=args.horizon,
            generations=args.generations,
            pop_size=args.pop,
            pc=args.pc,
            pm=args.pm,
            use_soft_fitness=args.soft_deadline,
            soft_alpha=args.soft_alpha,
            soft_beta=args.soft_beta,
            soft_gamma=args.soft_gamma,
        )

    # Optional local search (M3): VNS
    if args.local_search == "vns":
        before_profit = eval_result.profit
        improved_schedule, improved_profit = vns_improve(
            best_schedule, config, orders, rounds=args.ls_rounds, attempts_per_neigh=args.ls_attempts
        )
        if improved_profit > before_profit:
            best_schedule = improved_schedule
            # re-evaluate for full metrics
            from src.evaluation.fitness import evaluate_schedule
            eval_result = evaluate_schedule(best_schedule, config, orders)
            print(f"[VNS] 局部搜索提升利润: {before_profit:.2f} -> {eval_result.profit:.2f}")
        else:
            print(f"[VNS] 未找到更优邻域解，保持GA最优: {before_profit:.2f}")

    # Optional secondary optimization (M4): SA
    if args.sa_enabled:
        from src.algorithms.sa import run_sa
        before_profit = eval_result.profit
        try:
            init_temp = None if str(args.sa_initial_temp).lower() == "auto" else float(args.sa_initial_temp)
        except ValueError:
            init_temp = None
        sa_sched, sa_profit, sa_accept_rate = run_sa(
            best_schedule,
            config,
            orders,
            initial_temp=init_temp,
            cooling=args.sa_cooling,
            moves_per_temp=args.sa_moves_per_temp,
            temps=args.sa_temps,
        )
        if sa_profit > before_profit:
            best_schedule = sa_sched
            from src.evaluation.fitness import evaluate_schedule
            eval_result = evaluate_schedule(best_schedule, config, orders)
            print(f"[SA] 二次优化提升利润: {before_profit:.2f} -> {eval_result.profit:.2f} (接受率 {sa_accept_rate:.3f})")
        else:
            print(f"[SA] 未提升利润（接受率 {sa_accept_rate:.3f}），保持当前解: {before_profit:.2f}")

    save_results(best_schedule, eval_result, args.out)
    print_summary(eval_result)

    # experiment run logging
    run_dir = create_run_dir(args.runs_dir, args.exp_tag, args.seed)
    # save config and orders
    with open(args.config, "r", encoding="utf-8") as f:
        cfg_raw = json.load(f)
    save_json_rl(os.path.join(run_dir, "config.json"), cfg_raw)
    save_json_rl(os.path.join(run_dir, "orders.json"), [order_to_dict(o) for o in orders])
    # save schedule and metrics
    save_json_rl(os.path.join(run_dir, "schedule.json"), best_schedule)
    save_json_rl(os.path.join(run_dir, "metrics.json"), {
        "profit": eval_result.profit,
        "total_revenue": eval_result.total_revenue,
        "production_cost": eval_result.production_cost,
        "wage_cost": eval_result.wage_cost,
        "penalty": eval_result.penalty,
        "utilization_rate": eval_result.utilization_rate,
        "on_time_rate": eval_result.on_time_rate,
        "penalty_rate": eval_result.penalty_rate,
        "delivered_per_order": eval_result.delivered_per_order,
    })
    # write summary
    write_summary_md(os.path.join(run_dir, "summary.md"), args.exp_tag, cfg_raw, {
        "profit": eval_result.profit,
        "on_time_rate": eval_result.on_time_rate,
        "utilization_rate": eval_result.utilization_rate,
        "penalty": eval_result.penalty,
    })


if __name__ == "__main__":
    main()