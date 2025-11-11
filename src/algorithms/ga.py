import random
from typing import List, Optional, Tuple, Dict

from src.models.entities import Config, Order, Schedule
from src.evaluation.fitness import evaluate_schedule, compute_soft_fitness
from src.models.entities import SLOTS_PER_DAY, day_of_slot, slot_in_day


def random_schedule(horizon_days: int, config: Config) -> Schedule:
    slots = horizon_days * SLOTS_PER_DAY
    schedule: Schedule = []
    product_ids = [p.id for p in config.products]
    for _ in range(slots):
        line_choices: List[Optional[int]] = []
        for _l in range(config.lines):
            if config.allow_idle and random.random() < 0.2:
                line_choices.append(None)
            else:
                line_choices.append(random.choice(product_ids))
        schedule.append(line_choices)
    return schedule


def crossover(parent1: Schedule, parent2: Schedule) -> Tuple[Schedule, Schedule]:
    """Window crossover (M2): swap a small block (2–3 slots).

    Falls back to day boundary block if schedule too short.
    """
    assert len(parent1) == len(parent2)
    slots = len(parent1)
    if slots <= 3:
        # fallback to day-block
        days = max(1, slots // SLOTS_PER_DAY)
        point = random.randint(1, max(1, days - 1)) * SLOTS_PER_DAY if days > 1 else random.randint(1, slots - 1)
        child1 = parent1[:point] + parent2[point:]
        child2 = parent2[:point] + parent1[point:]
        return child1, child2

    win_len = random.choice([2, 3])
    start = random.randint(0, slots - win_len)
    child1 = parent1[:start] + parent2[start:start + win_len] + parent1[start + win_len:]
    child2 = parent2[:start] + parent1[start:start + win_len] + parent2[start + win_len:]
    return child1, child2


def mutate(schedule: Schedule, config: Config, pm: float = 0.05) -> None:
    """Hierarchical mutation (M2): product flip, idle insert, line swap, night-bias.

    - product flip: change to a random product id
    - idle insert: set to None (if allowed)
    - line swap: swap two lines within a slot
    - night-bias: reduce activity on expensive night slots probabilistically
    """
    product_ids = [p.id for p in config.products]
    L = config.lines
    for s in range(len(schedule)):
        for l in range(len(schedule[s])):
            if random.random() < pm:
                r = random.random()
                if config.allow_idle and r < 0.25:
                    schedule[s][l] = None
                elif r < 0.75:
                    schedule[s][l] = random.choice(product_ids)
                else:
                    # swap with another random line in the same slot
                    j = random.randint(0, L - 1)
                    schedule[s][l], schedule[s][j] = schedule[s][j], schedule[s][l]

        # night-bias per slot (slightly reduce activity on costly slots)
        slot_idx = slot_in_day(s)
        wmult = config.wage_multiplier_per_slot[slot_idx]
        if wmult >= 1.35 and config.allow_idle:
            # with small probability, set one random active line to idle
            if random.random() < pm * 0.5:
                active_lines = [i for i, lc in enumerate(schedule[s]) if lc is not None]
                if active_lines:
                    i = random.choice(active_lines)
                    schedule[s][i] = None


def _product_urgency(orders: List[Order]) -> Dict[int, int]:
    """Earliest due day per product (lower = more urgent)."""
    stats: Dict[int, int] = {}
    for o in orders:
        if o.product not in stats:
            stats[o.product] = o.due_day
        else:
            stats[o.product] = min(stats[o.product], o.due_day)
    return stats


def repair_schedule(schedule: Schedule, config: Config, orders: List[Order]) -> None:
    """Feasibility repairer (M2): avoid high-wage slots for non-urgent products.

    Heuristic:
    - For slots with wage multiplier >= 1.35 (night/late evening),
      if the chosen product is not due within 2 days, idle one line.
    - Keeps urgent products active.
    """
    urgency = _product_urgency(orders)
    for s, lines in enumerate(schedule):
        slot_idx = slot_in_day(s)
        wmult = config.wage_multiplier_per_slot[slot_idx]
        if wmult < 1.35:
            continue
        day = day_of_slot(s)
        for i, lc in enumerate(lines):
            if lc is None:
                continue
            due = urgency.get(lc, None)
            if due is None:
                # no orders for this product -> prefer idle
                schedule[s][i] = None
                continue
            # if not urgent within next 2 days, idle with small prob
            if day + 2 < due:
                if random.random() < 0.3:
                    schedule[s][i] = None


def tournament_select(pop: List[Schedule], fitnesses: List[float], k: int = 3) -> int:
    # return index of winner
    n = len(pop)
    best_i = None
    for _ in range(k):
        i = random.randint(0, n - 1)
        if best_i is None or fitnesses[i] > fitnesses[best_i]:
            best_i = i
    assert best_i is not None
    return best_i


def run_ga(config: Config, orders: List[Order], horizon_days: int, generations: int = 200,
           pop_size: int = 80, pc: float = 0.8, pm: float = 0.08,
           use_soft_fitness: bool = False, soft_alpha: float = 0.5, soft_beta: float = 0.2, soft_gamma: float = 0.0):
    # init population
    population: List[Schedule] = [random_schedule(horizon_days, config) for _ in range(pop_size)]
    eval_cache = {}

    def fitness(schedule: Schedule) -> float:
        key = id(schedule)
        if key in eval_cache:
            return eval_cache[key]
        if use_soft_fitness:
            score = compute_soft_fitness(schedule, config, orders, alpha_deadline=soft_alpha, beta_late_units=soft_beta, gamma_high_wage=soft_gamma)
            eval_cache[key] = score
            return score
        else:
            res = evaluate_schedule(schedule, config, orders)
            eval_cache[key] = res.profit
            return res.profit

    # evaluate initial
    fitnesses = [fitness(ind) for ind in population]
    best_idx = max(range(pop_size), key=lambda i: fitnesses[i])
    best = population[best_idx]
    best_fit = fitnesses[best_idx]
    best_eval = evaluate_schedule(best, config, orders)

    for g in range(generations):
        new_pop: List[Schedule] = []
        # elitism
        new_pop.append(best)
        while len(new_pop) < pop_size:
            # selection
            i1 = tournament_select(population, fitnesses)
            i2 = tournament_select(population, fitnesses)
            p1, p2 = population[i1], population[i2]
            # crossover
            if random.random() < pc:
                c1, c2 = crossover(p1, p2)
            else:
                c1, c2 = [list(map(list, p1)) for _ in range(1)], [list(map(list, p2)) for _ in range(1)]
                c1 = c1[0]
                c2 = c2[0]
            # mutation
            mutate(c1, config, pm)
            mutate(c2, config, pm)
            # feasibility repair
            repair_schedule(c1, config, orders)
            repair_schedule(c2, config, orders)
            new_pop.extend([c1, c2])
        population = new_pop[:pop_size]
        fitnesses = [fitness(ind) for ind in population]
        b_idx = max(range(pop_size), key=lambda i: fitnesses[i])
        if fitnesses[b_idx] > best_fit:
            best_fit = fitnesses[b_idx]
            best = population[b_idx]
            best_eval = evaluate_schedule(best, config, orders)

    return best, best_eval