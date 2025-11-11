import math
import random
from copy import deepcopy
from typing import List, Tuple, Optional

from src.models.entities import Config, Order, Schedule
from src.evaluation.fitness import evaluate_schedule
from src.algorithms.vns import (
    _neighbor_swap_adjacent,
    _neighbor_cross_line_reassign,
    _neighbor_block_shift,
)


def _auto_initial_temp(current: Schedule, config: Config, orders: List[Order], samples: int = 30) -> float:
    """Estimate initial temperature from sampled neighbor deltas.

    Use average magnitude of negative profit deltas as baseline; ensure >= 1.0.
    """
    base_eval = evaluate_schedule(current, config, orders)
    base_profit = base_eval.profit
    deltas: List[float] = []
    neighs = [
        lambda sch: _neighbor_swap_adjacent(sch, config),
        lambda sch: _neighbor_cross_line_reassign(sch, config, orders),
        lambda sch: _neighbor_block_shift(sch, config),
    ]
    for _ in range(samples):
        cand = random.choice(neighs)(current)
        cand_profit = evaluate_schedule(cand, config, orders).profit
        deltas.append(cand_profit - base_profit)
    neg = [abs(d) for d in deltas if d < 0]
    if not neg:
        return 1.0
    avg_neg = sum(neg) / len(neg)
    return max(1.0, avg_neg)


def run_sa(
    schedule: Schedule,
    config: Config,
    orders: List[Order],
    initial_temp: Optional[float] = None,
    cooling: float = 0.95,
    moves_per_temp: int = 150,
    temps: int = 20,
) -> Tuple[Schedule, float, float]:
    """Simulated Annealing on schedule using VNS neighbors.

    Returns (best_schedule, best_profit, accept_rate).
    """
    current = deepcopy(schedule)
    curr_eval = evaluate_schedule(current, config, orders)
    curr_profit = curr_eval.profit
    best = deepcopy(current)
    best_profit = curr_profit

    T = initial_temp if (initial_temp is not None and initial_temp > 0) else _auto_initial_temp(current, config, orders)
    accepted = 0
    total = 0

    neighs = [
        lambda sch: _neighbor_swap_adjacent(sch, config),
        lambda sch: _neighbor_cross_line_reassign(sch, config, orders),
        lambda sch: _neighbor_block_shift(sch, config),
    ]

    for _ in range(temps):
        for _m in range(moves_per_temp):
            total += 1
            cand = random.choice(neighs)(current)
            cand_eval = evaluate_schedule(cand, config, orders)
            cand_profit = cand_eval.profit
            delta = cand_profit - curr_profit
            if delta >= 0:
                accepted += 1
                current = cand
                curr_profit = cand_profit
                if cand_profit > best_profit:
                    best = cand
                    best_profit = cand_profit
            else:
                # accept worse move with probability exp(delta / T)
                p = math.exp(delta / max(1e-9, T))
                if random.random() < p:
                    accepted += 1
                    current = cand
                    curr_profit = cand_profit
        T *= cooling

    accept_rate = (accepted / total) if total > 0 else 0.0
    return best, best_profit, accept_rate