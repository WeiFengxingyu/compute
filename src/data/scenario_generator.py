import json
import random
from typing import List, Dict, Any
from .generator import default_config, generate_orders


def generate_scenario_orders(scenario: str, horizon_days: int = 7, num_orders: int = 12, seed: int = None) -> List[Dict[str, Any]]:
    """
    生成不同场景的订单数据
    
    Args:
        scenario: 场景类型 ("loose", "medium", "tight")
        horizon_days: 时间范围天数
        num_orders: 订单数量
        seed: 随机种子，用于复现
    
    Returns:
        订单列表
    """
    if seed is not None:
        random.seed(seed)
    
    # 映射场景到紧迫度参数
    urgency_map = {
        "loose": "loose",
        "medium": "medium", 
        "tight": "tight"
    }
    
    urgency = urgency_map.get(scenario, "medium")
    return generate_orders(num_orders, horizon_days, urgency)


def generate_scenario_config(scenario: str) -> Dict[str, Any]:
    """
    生成不同场景的配置数据
    
    Args:
        scenario: 场景类型 ("loose", "medium", "tight")
    
    Returns:
        配置字典
    """
    config = default_config()
    
    # 根据场景调整工资系数
    if scenario == "loose":
        # 宽松场景：工资系数较低
        config["wage_multiplier_per_slot"] = [1.0, 1.05, 1.1, 1.15, 1.25, 1.2]
    elif scenario == "tight":
        # 紧张场景：工资系数较高，增加调度难度
        config["wage_multiplier_per_slot"] = [1.0, 1.15, 1.3, 1.5, 1.7, 1.4]
    # medium场景使用默认配置
    
    return config


def save_scenario_data(scenario: str, horizon_days: int = 7, num_orders: int = 12, 
                      output_dir: str = "data/scenarios", seed: int = None) -> None:
    """
    保存场景数据到文件
    
    Args:
        scenario: 场景类型
        horizon_days: 时间范围天数
        num_orders: 订单数量
        output_dir: 输出目录
        seed: 随机种子
    """
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    # 生成订单和配置
    orders = generate_scenario_orders(scenario, horizon_days, num_orders, seed)
    config = generate_scenario_config(scenario)
    
    # 保存文件
    orders_file = os.path.join(output_dir, f"orders_{scenario}.json")
    config_file = os.path.join(output_dir, f"config_{scenario}.json")
    
    with open(orders_file, "w", encoding="utf-8") as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)
    
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print(f"场景 '{scenario}' 数据已保存:")
    print(f"  订单文件: {orders_file}")
    print(f"  配置文件: {config_file}")
    print(f"  订单数量: {len(orders)}")
    print(f"  时间范围: {horizon_days} 天")
    
    # 显示统计信息
    if orders:
        due_days = [o["due_day"] for o in orders]
        arrival_days = [o["arrival_day"] for o in orders]
        print(f"  到达日范围: {min(arrival_days)}-{max(arrival_days)}")
        print(f"  截止日范围: {min(due_days)}-{max(due_days)}")
        print(f"  平均提前期: {sum(d - a for d, a in zip(due_days, arrival_days))/len(orders):.1f} 天")


if __name__ == "__main__":
    # 生成三个场景的数据
    for scenario in ["loose", "medium", "tight"]:
        save_scenario_data(scenario, horizon_days=7, num_orders=12, seed=42)
        print()