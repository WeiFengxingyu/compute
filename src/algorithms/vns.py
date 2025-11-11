import random
from copy import deepcopy
from typing import List, Optional, Tuple

from src.models.entities import Config, Order, Schedule
from src.evaluation.fitness import evaluate_schedule
from src.models.entities import slot_in_day, day_of_slot


def _product_urgency(orders: List[Order]) -> dict:
    """Earliest due day per product (lower more urgent)."""
    stats = {}
    for o in orders:
        stats[o.product] = min(stats.get(o.product, o.due_day), o.due_day)
    return stats


def _neighbor_swap_adjacent(schedule: Schedule, config: Config) -> Schedule:
    """Small neighborhood: swap adjacent slots on the same line.

    Choose a random line l and slot s, swap with s±1 if exists.
    """
    if not schedule:
        return schedule
    new_sched = deepcopy(schedule)
    slots = len(new_sched)
    l = random.randint(0, config.lines - 1)
    s = random.randint(0, slots - 1)
    if slots == 1:
        return new_sched
    # pick neighbor slot
    if s == 0:
        t = 1
    elif s == slots - 1:
        t = slots - 2
    else:
        t = s + (1 if random.random() < 0.5 else -1)
    new_sched[s][l], new_sched[t][l] = new_sched[t][l], new_sched[s][l]
    return new_sched


def _neighbor_cross_line_reassign(schedule: Schedule, config: Config, orders: List[Order]) -> Schedule:
    """Medium neighborhood: reassign products across lines within a slot.

    Heuristic: In a random slot, bias one line to the most urgent product
    present in that slot, or to globally most urgent if slot has None.
    """
    if not schedule:
        return schedule
    new_sched = deepcopy(schedule)
    urgency = _product_urgency(orders)
    s = random.randint(0, len(new_sched) - 1)
    # products present in this slot
    present = [p for p in new_sched[s] if p is not None]
    target_product: Optional[int]
    if present:
        # pick the most urgent among present products
        target_product = min(present, key=lambda pid: urgency.get(pid, 10**9))
    else:
        # globally most urgent product
        all_p = [p.id for p in config.products]
        target_product = min(all_p, key=lambda pid: urgency.get(pid, 10**9))
    # choose a line to set as target product
    l = random.randint(0, config.lines - 1)
    new_sched[s][l] = target_product
    return new_sched


def _neighbor_block_shift(schedule: Schedule, config: Config) -> Schedule:
    """Large neighborhood: shift a line's assignment from a high-wage slot
    to an earlier/lower-wage slot (swap assignments to keep capacity consistent)."""
    if not schedule:
        return schedule
    new_sched = deepcopy(schedule)
    slots = len(new_sched)
    l = random.randint(0, config.lines - 1)
    s = random.randint(0, slots - 1)
    src_wmult = config.wage_multiplier_per_slot[slot_in_day(s)]
    # find a target slot t earlier with lower wage multiplier if possible
    candidates: List[int] = []
    for t in range(0, s):
        if config.wage_multiplier_per_slot[slot_in_day(t)] < src_wmult:
            candidates.append(t)
    if candidates:
        t = random.choice(candidates)
        new_sched[s][l], new_sched[t][l] = new_sched[t][l], new_sched[s][l]
    else:
        # fallback: swap within same day toward earlier slot
        day_start = day_of_slot(s) * len(config.wage_multiplier_per_slot)
        if s > day_start:
            t = s - 1
            new_sched[s][l], new_sched[t][l] = new_sched[t][l], new_sched[s][l]
    return new_sched


def vns_improve(
    schedule: Schedule,
    config: Config,
    orders: List[Order],
    rounds: int = 3,
    attempts_per_neigh: int = 100,
) -> Tuple[Schedule, float]:
    """Basic VNS: iterate through small/medium/large neighborhoods.

    Accept-improving strategy: keep the best found; restart neighborhoods
    when improvement occurs. Returns improved schedule and its profit.
    """
    best_sched = deepcopy(schedule)
    best_eval = evaluate_schedule(best_sched, config, orders)
    best_profit = best_eval.profit

    neighborhoods = [
        lambda sch: _neighbor_swap_adjacent(sch, config),
        lambda sch: _neighbor_cross_line_reassign(sch, config, orders),
        lambda sch: _neighbor_block_shift(sch, config),
    ]

    for _r in range(rounds):
        improved = False
        for neigh in neighborhoods:
            for _ in range(attempts_per_neigh):
                cand = neigh(best_sched)
                cand_eval = evaluate_schedule(cand, config, orders)
                if cand_eval.profit > best_profit:
                    best_sched = cand
                    best_profit = cand_eval.profit
                    improved = True
                    break  # move to next neighborhood after improvement
            if improved:
                break  # restart from first neighborhood
        if not improved:
            # no improvement in this round; stop early
            break

    return best_sched, best_profit