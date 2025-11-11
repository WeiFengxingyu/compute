from typing import List, Dict, Optional
from dataclasses import replace

from src.models.entities import Order, Config, day_of_slot, slot_in_day


def decode_assignments(schedule: List[List[Optional[int]]], config: Config, orders: List[Order]) -> Dict[str, int]:
    """Assign produced units to orders using EDD + profit density.

    - For each slot s, aggregate production by product across lines.
    - Assign to orders of that product with earliest due day first.
    - Respect availability from day (arrival after 8 -> next day).
    - Production units per line per slot = product.slot_capacity.
    - If allow_idle and None, that line produces 0.
    Returns delivered units per order across all time (may be after due).
    """
    # Copy orders to avoid mutating inputs
    ords = [replace(o) for o in orders]
    # Remaining demand by order id
    remaining = {o.id: o.qty for o in ords}

    # Pre-index orders per product, sorted by (due_day, unit_profit desc)
    prod_orders: Dict[int, List[Order]] = {}
    for p in {p.id for p in config.products}:
        subset = [o for o in ords if o.product == p]
        subset.sort(key=lambda o: (o.due_day, -(o.unit_price - config.product_by_id(p).unit_cost)))
        prod_orders[p] = subset

    # Iterate slots
    for s, lines in enumerate(schedule):
        day = day_of_slot(s)
        # aggregate produced per product
        produced_by_product: Dict[int, int] = {}
        for l_choice in lines:
            if l_choice is None:
                continue
            cap = config.product_by_id(l_choice).slot_capacity
            produced_by_product[l_choice] = produced_by_product.get(l_choice, 0) + cap

        for p, produced in produced_by_product.items():
            if produced <= 0:
                continue
            # assign to orders of product p, EDD first
            for o in prod_orders[p]:
                # must be available
                if day < o.available_from_day:
                    continue
                need = remaining[o.id]
                if need <= 0:
                    continue
                take = min(need, produced)
                if take > 0:
                    remaining[o.id] -= take
                    produced -= take
                if produced <= 0:
                    break

    delivered = {o.id: (o.qty - remaining[o.id]) for o in ords}
    return delivered