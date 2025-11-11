import os
import json
from datetime import datetime
from typing import Any, Dict, List


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def create_run_dir(base_dir: str, tag: str, seed: int | None = None) -> str:
    os.makedirs(base_dir, exist_ok=True)
    suffix = f"_{tag}" if tag else ""
    seed_part = f"_seed{seed}" if seed is not None else ""
    run_dir = os.path.join(base_dir, f"run-{_ts()}{suffix}{seed_part}")
    os.makedirs(run_dir, exist_ok=True)
    os.makedirs(os.path.join(run_dir, "plots"), exist_ok=True)
    return run_dir


def save_json(path: str, data: Any):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def order_to_dict(order) -> Dict[str, Any]:
    return {
        "id": order.id,
        "product": order.product,
        "qty": order.qty,
        "unit_price": order.unit_price,
        "arrival_day": order.arrival_day,
        "arrival_slot_index": order.arrival_slot_index,
        "due_day": order.due_day,
    }


def write_summary_md(path: str, algo_tag: str, config: Dict[str, Any], metrics: Dict[str, Any]):
    lines: List[str] = []
    lines.append(f"# 实验总结 - {algo_tag}\n")
    lines.append("## 关键指标\n")
    for k, v in metrics.items():
        lines.append(f"- {k}: {v}")
    lines.append("\n## 主要配置片段\n")
    lines.append(f"- lines: {config.get('lines')}")
    lines.append(f"- wage_per_slot_per_line: {config.get('wage_per_slot_per_line')}")
    lines.append(f"- wage_multiplier_per_slot: {config.get('wage_multiplier_per_slot')}\n")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))