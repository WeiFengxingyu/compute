from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


SLOTS_PER_DAY = 6  # [8-12], [12-16], [16-20], [20-24], [0-4], [4-8]


def day_of_slot(slot_index: int) -> int:
    return slot_index // SLOTS_PER_DAY


def slot_in_day(slot_index: int) -> int:
    return slot_index % SLOTS_PER_DAY


@dataclass
class Product:
    id: int
    rate_per_hour: float  # pieces/hour
    unit_cost: float

    @property
    def slot_capacity(self) -> int:
        return int(4 * self.rate_per_hour)


@dataclass
class Config:
    lines: int
    products: List[Product]
    wage_per_slot_per_line: float
    wage_multiplier_per_slot: List[float]  # length must be 6
    allow_idle: bool = True

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Config":
        products = [Product(**p) for p in d["products"]]
        return Config(
            lines=d["lines"],
            products=products,
            wage_per_slot_per_line=d["wage_per_slot_per_line"],
            wage_multiplier_per_slot=d["wage_multiplier_per_slot"],
            allow_idle=d.get("allow_idle", True),
        )

    def product_by_id(self, pid: int) -> Product:
        for p in self.products:
            if p.id == pid:
                return p
        raise KeyError(f"Unknown product id: {pid}")


@dataclass
class Order:
    id: str
    product: int
    qty: int
    unit_price: float
    arrival_day: int
    arrival_slot_index: int  # 0..5, if >0 then schedule next day
    due_day: int  # deadline at 8:00 of this day

    # runtime state
    delivered: int = 0

    @property
    def available_from_day(self) -> int:
        return self.arrival_day + (1 if self.arrival_slot_index > 0 else 0)


# Schedule: for each slot (0..S-1), list of length L with product id or None (idle)
Schedule = List[List[Optional[int]]]


@dataclass
class EvaluationResult:
    total_revenue: float
    production_cost: float
    wage_cost: float
    penalty: float
    profit: float
    utilization_rate: float
    on_time_rate: float
    penalty_rate: float
    delivered_per_order: Dict[str, int]