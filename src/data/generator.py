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


def generate_orders(num_orders: int = 12, horizon_days: int = 7) -> List[Dict[str, Any]]:
    orders: List[Dict[str, Any]] = []
    # product mix probabilities
    product_probs = [0.4, 0.35, 0.25]
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

        # due day arrival_day+1..horizon_days-1 (must be after arrival)
        due_day = random.randint(arrival_day + 1, horizon_days - 1)

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