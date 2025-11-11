import json
import random
from typing import List, Dict, Any


def default_config() -> Dict[str, Any]:
    return {
        "lines": 3,
        "products": [
            {"id": 1, "rate_per_hour": 12, "unit_cost": 40},
            {"id": 2, "rate_per_hour": 10, "unit_cost": 35},
            {"id": 3, "rate_per_hour": 8, "unit_cost": 30},
        ],
        "wage_per_slot_per_line": 2000.0,
        "wage_multiplier_per_slot": [1.0, 1.1, 1.2, 1.35, 1.5, 1.3],
        "allow_idle": True,
    }


def generate_orders(num_orders: int = 12, horizon_days: int = 7, urgency: str = "medium") -> List[Dict[str, Any]]:
    """
    生成订单数据，支持不同的紧迫度场景
    
    Args:
        num_orders: 订单数量
        horizon_days: 时间范围天数
        urgency: 紧迫度级别 ("loose", "medium", "tight")
            - loose: 宽松，截止日期较远
            - medium: 中等，默认行为
            - tight: 紧张，截止日期较近
    """
    orders: List[Dict[str, Any]] = []
    # product mix probabilities
    product_probs = [0.4, 0.35, 0.25]
    
    # 根据紧迫度设置截止日期分布
    if urgency == "loose":
        # 宽松：截止日期相对较远，给算法更多调度空间
        due_day_min_offset = 2
        due_day_max_offset = 4
    elif urgency == "tight":
        # 紧张：截止日期很近，考验算法的紧急调度能力
        due_day_min_offset = 1
        due_day_max_offset = 2
    else:  # medium
        # 中等：默认行为
        due_day_min_offset = 1
        due_day_max_offset = 3
    
    for i in range(num_orders):
        # choose product
        r = random.random()
        if r < product_probs[0]:
            product = 1
        elif r < product_probs[0] + product_probs[1]:
            product = 2
        else:
            product = 3

        # quantity scaled by horizon
        base_qty = random.randint(180, 800)
        qty = base_qty

        # unit price varies by product
        unit_price = {1: 120.0, 2: 110.0, 3: 100.0}[product]

        # arrival day 0..horizon_days-2, arrival slot 0..5
        arrival_day = random.randint(0, max(0, horizon_days - 2))
        arrival_slot_index = random.randint(0, 5)

        # due day based on urgency setting
        min_due = arrival_day + due_day_min_offset
        max_due = min(arrival_day + due_day_max_offset, horizon_days - 1)
        
        if min_due > max_due:
            due_day = min_due
        else:
            due_day = random.randint(min_due, max_due)

        orders.append(
            {
                "id": f"O{i+1:02d}",
                "product": product,
                "qty": qty,
                "unit_price": unit_price,
                "arrival_day": arrival_day,
                "arrival_slot_index": arrival_slot_index,
                "due_day": due_day,
            }
        )
    return orders


def save_json(path: str, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)