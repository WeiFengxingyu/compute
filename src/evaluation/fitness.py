from typing import List, Optional, Dict

from src.models.entities import Config, Order, EvaluationResult, day_of_slot, slot_in_day


def evaluate_schedule(schedule: List[List[Optional[int]]], config: Config, orders: List[Order]) -> EvaluationResult:
    # Delivered units across all time (decoder decides allocation); also need delivered before due
    from src.decoders.edd_decoder import decode_assignments

    # First compute delivered totals across all slots
    delivered_total = decode_assignments(schedule, config, orders)

    # Compute delivered before due-day cutoff
    delivered_before_due: Dict[str, int] = {o.id: 0 for o in orders}
    # To get per-slot assignment timing, we need a second pass assigning with cutoff
    # We'll simulate slot-by-slot and update delivered before due.
    remaining_for_due = {o.id: o.qty for o in orders}

    for s, lines in enumerate(schedule):
        day = day_of_slot(s)
        produced_by_product: Dict[int, int] = {}
        for l_choice in lines:
            if l_choice is None:
                continue
            cap = config.product_by_id(l_choice).slot_capacity
            produced_by_product[l_choice] = produced_by_product.get(l_choice, 0) + cap

        # EDD ordering for each product
        for p, produced in produced_by_product.items():
            # orders sorted by due then profit density
            subset = [o for o in orders if o.product == p]
            subset.sort(key=lambda o: (o.due_day, -(o.unit_price - config.product_by_id(p).unit_cost)))
            for o in subset:
                if day < o.available_from_day:
                    continue
                need = remaining_for_due[o.id]
                if need <= 0:
                    continue
                take = min(need, produced)
                if take > 0:
                    # only counts toward delivered-before-due if still before due_day
                    if day < o.due_day:
                        delivered_before_due[o.id] += take
                    remaining_for_due[o.id] -= take
                    produced -= take
                if produced <= 0:
                    break

    # Revenue: all delivered units (even after due) count revenue
    revenue = 0.0
    delivered_per_order = {}
    for o in orders:
        delivered_units = min(delivered_total[o.id], o.qty)
        delivered_per_order[o.id] = delivered_units
        revenue += delivered_units * o.unit_price

    # Production cost: count produced units (only when line active)
    prod_cost = 0.0
    active_lines_count = 0
    total_lines_slots = 0
    for s, lines in enumerate(schedule):
        total_lines_slots += len(lines)
        for l_choice in lines:
            if l_choice is None:
                continue
            active_lines_count += 1
            p = config.product_by_id(l_choice)
            prod_cost += p.slot_capacity * p.unit_cost

    # Wage cost: per active line per slot with multiplier
    wage_cost = 0.0
    for s, lines in enumerate(schedule):
        wmult = config.wage_multiplier_per_slot[slot_in_day(s)]
        # count active lines
        active = sum(1 for lc in lines if lc is not None)
        wage_cost += config.wage_per_slot_per_line * wmult * active

    # Penalty: if not fully delivered before due_day
    penalty = 0.0
    on_time_orders = 0
    for o in orders:
        if delivered_before_due[o.id] >= o.qty:
            on_time_orders += 1
        else:
            penalty += 0.1 * o.qty * o.unit_price

    total_orders = len(orders)
    on_time_rate = on_time_orders / total_orders if total_orders else 0.0
    penalty_rate = (total_orders - on_time_orders) / total_orders if total_orders else 0.0

    # Utilization rate: fraction of line-slots actively producing
    utilization_rate = active_lines_count / total_lines_slots if total_lines_slots else 0.0

    profit = revenue - prod_cost - wage_cost - penalty
    return EvaluationResult(
        total_revenue=revenue,
        production_cost=prod_cost,
        wage_cost=wage_cost,
        penalty=penalty,
        profit=profit,
        utilization_rate=utilization_rate,
        on_time_rate=on_time_rate,
        penalty_rate=penalty_rate,
        delivered_per_order=delivered_per_order,
    )


# --- M3.1: Soft deadline weights to guide GA/VNS (fitness only) ---

def _earliest_due_per_product(orders: List[Order]) -> Dict[int, int]:
    stats: Dict[int, int] = {}
    for o in orders:
        if o.product not in stats:
            stats[o.product] = o.due_day
        else:
            stats[o.product] = min(stats[o.product], o.due_day)
    return stats


def _delivered_before_due(schedule: List[List[Optional[int]]], config: Config, orders: List[Order]) -> Dict[str, int]:
    delivered_before_due: Dict[str, int] = {o.id: 0 for o in orders}
    remaining_for_due = {o.id: o.qty for o in orders}
    for s, lines in enumerate(schedule):
        day = day_of_slot(s)
        produced_by_product: Dict[int, int] = {}
        for l_choice in lines:
            if l_choice is None:
                continue
            cap = config.product_by_id(l_choice).slot_capacity
            produced_by_product[l_choice] = produced_by_product.get(l_choice, 0) + cap

        for p, produced in produced_by_product.items():
            subset = [o for o in orders if o.product == p]
            subset.sort(key=lambda o: (o.due_day, -(o.unit_price - config.product_by_id(p).unit_cost)))
            for o in subset:
                if day < o.available_from_day:
                    continue
                need = remaining_for_due[o.id]
                if need <= 0:
                    continue
                take = min(need, produced)
                if take > 0:
                    if day < o.due_day:
                        delivered_before_due[o.id] += take
                    remaining_for_due[o.id] -= take
                    produced -= take
                if produced <= 0:
                    break
    return delivered_before_due


def compute_soft_fitness(
    schedule: List[List[Optional[int]]],
    config: Config,
    orders: List[Order],
    alpha_deadline: float = 0.5,
    beta_late_units: float = 0.2,
    gamma_high_wage: float = 0.0,
) -> float:
    """Return fitness score with soft deadline guidance.

    - alpha_deadline: penalize production scheduled close to/past earliest due of its product.
    - beta_late_units: penalize units not delivered before due (soft, separate from hard penalty).
    - gamma_high_wage: discourage activity in high-wage slots (soft guidance).
    """
    res = evaluate_schedule(schedule, config, orders)

    # compute earliest due per product
    earliest_due = _earliest_due_per_product(orders)

    # soft term 1: deadline pressure per produced capacity near/past due
    soft_deadline_pressure = 0.0
    for s, lines in enumerate(schedule):
        day = day_of_slot(s)
        for l_choice in lines:
            if l_choice is None:
                continue
            p = config.product_by_id(l_choice)
            ed = earliest_due.get(l_choice, None)
            if ed is None:
                # no orders for this product -> mild penalty to avoid waste
                soft_deadline_pressure += 0.5 * p.slot_capacity
                continue
            days_to_due = ed - day
            # pressure grows as we get closer to or past due; min buffer considered = 2 days
            pressure = max(0.0, 2.0 - days_to_due)
            soft_deadline_pressure += pressure * p.slot_capacity

    # soft term 2: units not delivered before due (soft), independent of revenue penalty
    delivered_bd = _delivered_before_due(schedule, config, orders)
    late_units_soft = 0.0
    for o in orders:
        late_units = max(0, o.qty - delivered_bd[o.id])
        late_units_soft += late_units

    # soft term 3: high wage activity guidance
    high_wage_soft = 0.0
    if gamma_high_wage > 0.0:
        for s, lines in enumerate(schedule):
            wmult = config.wage_multiplier_per_slot[slot_in_day(s)]
            active = sum(1 for lc in lines if lc is not None)
            high_wage_soft += config.wage_per_slot_per_line * max(0.0, wmult - 1.0) * active

    soft_total = alpha_deadline * soft_deadline_pressure + beta_late_units * late_units_soft + gamma_high_wage * high_wage_soft
    fitness_score = res.profit - soft_total
    return fitness_score