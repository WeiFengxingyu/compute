import os
import subprocess
import json
from typing import List, Dict, Any
import sys


def run_algorithm_comparison(
    scenarios: List[str] = ["loose", "medium", "tight"],
    algorithms: List[str] = ["ga", "ga-vns", "ga-vns-sa", "pso"],
    repeats: int = 30,
    base_seed: int = 1000,
    horizon_days: int = 7
) -> None:
    """
    在新场景下运行所有算法进行对比实验
    
    Args:
        scenarios: 场景列表
        algorithms: 算法列表
        repeats: 每个算法的重复次数
        base_seed: 基础随机种子
        horizon_days: 时间范围天数
    """
    
    # 算法参数配置
    algo_params = {
        "ga": {
            "generations": 200,
            "pop": 80,
            "pc": 0.8,
            "pm": 0.08
        },
        "ga-vns": {
            "generations": 200,
            "pop": 80,
            "pc": 0.8,
            "pm": 0.08,
            "local_search": "vns",
            "ls_rounds": 3,
            "ls_attempts": 120
        },
        "ga-vns-sa": {
            "generations": 150,
            "pop": 60,
            "pc": 0.8,
            "pm": 0.08,
            "local_search": "vns",
            "ls_rounds": 2,
            "ls_attempts": 80,
            "sa_enabled": None,  # 标志参数
            "sa_temps": 15,
            "sa_moves_per_temp": 100
        },
        "pso": {
            "pso_enabled": None,  # 标志参数
            "pso_particles": 20,
            "pso_iterations": 50,
            "pso_c1": 2.0,
            "pso_c2": 2.0,
            "pso_w": 0.7
        }
    }
    
    # 软适应度参数（所有算法统一使用）
    soft_fitness_params = {
        "soft_deadline": None,  # 标志参数
        "soft_alpha": 1.5,
        "soft_beta": 0.8,
        "soft_gamma": 0.1
    }
    
    total_experiments = len(scenarios) * len(algorithms) * repeats
    current_experiment = 0
    
    print(f"开始大规模对比实验:")
    print(f"场景: {scenarios}")
    print(f"算法: {algorithms}")
    print(f"重复次数: {repeats}")
    print(f"总实验数: {total_experiments}")
    print("-" * 60)
    
    for scenario in scenarios:
        print(f"\n=== 场景: {scenario} ===")
        
        # 场景数据文件路径
        config_file = f"data/scenarios/config_{scenario}.json"
        orders_file = f"data/scenarios/orders_{scenario}.json"
        
        for algorithm in algorithms:
            print(f"\n--- 算法: {algorithm} ---")
            
            for repeat in range(repeats):
                current_experiment += 1
                seed = base_seed + repeat
                
                # 构建命令
                cmd = [
                    "python", "-m", "src.main",
                    "--horizon", str(horizon_days),
                    "--config", config_file,
                    "--orders", orders_file,
                    "--out", "results",
                    "--runs_dir", "experiments",
                    "--exp_tag", f"{algorithm}-{scenario}-m6s3",
                    "--seed", str(seed)
                ]
                
                # 添加算法特定参数
                params = algo_params[algorithm].copy()
                for key, value in params.items():
                    if value is None:  # 标志参数
                        cmd.extend([f"--{key}"])
                    else:
                        cmd.extend([f"--{key}", str(value)])
                
                # 添加软适应度参数
                for key, value in soft_fitness_params.items():
                    if value is None:  # 标志参数
                        cmd.extend([f"--{key}"])
                    else:
                        cmd.extend([f"--{key}", str(value)])
                
                print(f"[{current_experiment}/{total_experiments}] {algorithm}-{scenario} (seed={seed})")
                
                try:
                    # 运行实验
                    result = subprocess.run(cmd, capture_output=True, text=True, cwd=".")
                    
                    if result.returncode == 0:
                        print(f"  ✓ 成功")
                    else:
                        print(f"  ✗ 失败 (返回码: {result.returncode})")
                        if result.stderr:
                            print(f"  错误: {result.stderr[:200]}...")
                    
                except Exception as e:
                    print(f"  ✗ 异常: {str(e)}")
                
                # 每10个实验后显示进度
                if current_experiment % 10 == 0:
                    progress = (current_experiment / total_experiments) * 100
                    print(f"\n进度: {progress:.1f}% ({current_experiment}/{total_experiments})")
    
    print(f"\n=== 实验完成 ===")
    print(f"总计完成: {current_experiment} 个实验")
    print(f"实验结果保存在: experiments/")
    print(f"批量汇总文件在: experiments/batch_*-m6s3_summary.csv")


def generate_summary_report(scenarios: List[str], algorithms: List[str]) -> None:
    """
    生成实验总结报告
    """
    print("\n=== 实验总结 ===")
    
    for scenario in scenarios:
        print(f"\n场景: {scenario}")
        for algorithm in algorithms:
            # 查找对应的批量汇总文件
            pattern = f"experiments/batch_{algorithm}-{scenario}-m6s3_summary.csv"
            if os.path.exists(pattern):
                print(f"  {algorithm}: 有汇总数据")
            else:
                print(f"  {algorithm}: 无汇总数据")


if __name__ == "__main__":
    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "--summary":
        # 只生成总结报告
        generate_summary_report(["loose", "medium", "tight"], ["ga", "ga-vns", "ga-vns-sa", "pso"])
    else:
        # 运行完整实验
        run_algorithm_comparison(
            scenarios=["loose", "medium", "tight"],
            algorithms=["ga", "ga-vns", "ga-vns-sa", "pso"],
            repeats=30,
            base_seed=2000,
            horizon_days=7
        )