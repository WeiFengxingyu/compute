"""
Particle Swarm Optimization (PSO) for Production Scheduling

编码方式：连续空间编码，每个粒子的维度对应订单的优先级权重
decoder：使用基于优先级的EDD + 利润密度解码器
适应度：使用强化后的软适应度函数（包含期限压力和延迟惩罚）
"""

import random
import math
from typing import List, Optional, Tuple, Dict

from src.models.entities import Config, Order, Schedule
from src.evaluation.fitness import evaluate_schedule, compute_soft_fitness
from src.models.entities import SLOTS_PER_DAY, day_of_slot, slot_in_day


def random_particle_position(num_orders: int, min_val: float = 0.0, max_val: float = 1.0) -> List[float]:
    """Generate random particle position in continuous space."""
    return [random.uniform(min_val, max_val) for _ in range(num_orders)]


def random_particle_velocity(num_orders: int, max_vel: float = 0.2) -> List[float]:
    """Generate random particle velocity."""
    return [random.uniform(-max_vel, max_vel) for _ in range(num_orders)]


def decode_particle_to_schedule(
    particle: List[float], 
    config: Config, 
    orders: List[Order], 
    horizon_days: int
) -> Schedule:
    """
    Decode particle position to schedule using priority-based approach.
    
    Each dimension in particle represents priority weight for corresponding order.
    Higher priority = earlier processing.
    
    Decoding strategy:
    1. Sort orders by composite priority: particle_weight * (1/due_day) * profit_density
    2. Use greedy assignment based on EDD + profit density within priority groups
    """
    slots = horizon_days * SLOTS_PER_DAY
    schedule: Schedule = [[None for _ in range(config.lines)] for _ in range(slots)]
    
    # Create order priority scores
    order_priorities = []
    for i, order in enumerate(orders):
        # Composite priority: particle weight * urgency * profit density
        urgency = 1.0 / max(1, order.due_day)  # Earlier due = higher urgency
        profit_density = (order.unit_price - config.product_by_id(order.product).unit_cost) / order.qty
        priority_score = particle[i] * urgency * profit_density
        order_priorities.append((i, priority_score, order))
    
    # Sort by priority score (descending)
    order_priorities.sort(key=lambda x: x[1], reverse=True)
    
    # Track remaining demand and capacity
    remaining_demand = {order.id: order.qty for order in orders}
    slot_capacity_used = [[0 for _ in range(config.lines)] for _ in range(slots)]
    
    # Greedy assignment based on priority
    for order_idx, priority_score, order in order_priorities:
        remaining = remaining_demand[order.id]
        if remaining <= 0:
            continue
            
        # Find best slots for this order (considering due date and cost)
        best_slots = []
        for s in range(slots):
            day = day_of_slot(s)
            if day < order.available_from_day:
                continue
            if day >= order.due_day:
                continue  # Don't schedule after due date
                
            # Calculate slot attractiveness
            time_to_due = order.due_day - day
            wage_mult = config.wage_multiplier_per_slot[slot_in_day(s)]
            
            # Higher attractiveness = better (lower wage, more time to due)
            attractiveness = (1.0 / wage_mult) * (1.0 + time_to_due * 0.1)
            best_slots.append((s, attractiveness))
        
        # Sort slots by attractiveness
        best_slots.sort(key=lambda x: x[1], reverse=True)
        
        # Assign production to best available slots
        still_need = remaining
        for slot_idx, attractiveness in best_slots:
            if still_need <= 0:
                break
                
            # Try to assign to available lines in this slot
            for line_idx in range(config.lines):
                if still_need <= 0:
                    break
                    
                current_product = schedule[slot_idx][line_idx]
                line_capacity = config.product_by_id(order.product).slot_capacity
                
                # If line is empty or already producing this product
                if current_product is None or current_product == order.product:
                    available_capacity = line_capacity - slot_capacity_used[slot_idx][line_idx]
                    if available_capacity > 0:
                        assign_amount = min(still_need, available_capacity)
                        
                        # Set line to this product if not already set
                        if current_product is None:
                            schedule[slot_idx][line_idx] = order.product
                        
                        slot_capacity_used[slot_idx][line_idx] += assign_amount
                        still_need -= assign_amount
                        remaining_demand[order.id] -= assign_amount
    
    return schedule


def update_particle_velocity(
    particle: List[float],
    velocity: List[float],
    personal_best: List[float],
    global_best: List[float],
    w: float = 0.7,      # inertia weight
    c1: float = 1.5,      # cognitive coefficient
    c2: float = 1.5,      # social coefficient
    max_vel: float = 0.2  # velocity clamping
) -> List[float]:
    """Update particle velocity using standard PSO formula."""
    new_velocity = []
    for i in range(len(particle)):
        r1, r2 = random.random(), random.random()
        
        # Standard PSO velocity update
        new_v = (w * velocity[i] + 
                c1 * r1 * (personal_best[i] - particle[i]) +
                c2 * r2 * (global_best[i] - particle[i]))
        
        # Velocity clamping
        new_v = max(-max_vel, min(max_vel, new_v))
        new_velocity.append(new_v)
    
    return new_velocity


def update_particle_position(particle: List[float], velocity: List[float]) -> List[float]:
    """Update particle position."""
    new_position = []
    for i in range(len(particle)):
        new_pos = particle[i] + velocity[i]
        # Ensure position stays in valid range [0, 1]
        new_pos = max(0.0, min(1.0, new_pos))
        new_position.append(new_pos)
    
    return new_position


def run_pso(
    config: Config,
    orders: List[Order],
    horizon_days: int,
    n_particles: int = 30,
    iterations: int = 100,
    w: float = 0.7,       # inertia weight
    c1: float = 1.5,      # cognitive coefficient
    c2: float = 1.5,       # social coefficient
    max_vel: float = 0.2,  # max velocity
    use_soft_fitness: bool = True,  # use enhanced soft fitness
    soft_alpha: float = 1.5,      # enhanced deadline pressure
    soft_beta: float = 0.8,       # enhanced late units penalty
    soft_gamma: float = 0.0,
) -> Tuple[Schedule, object]:  # Return schedule and evaluation result
    """
    Particle Swarm Optimization for production scheduling.
    
    Returns:
        best_schedule: Best found schedule
        best_eval: Evaluation result of best schedule
    """
    num_orders = len(orders)
    
    # Initialize swarm
    swarm_positions = []
    swarm_velocities = []
    personal_best_positions = []
    personal_best_fitnesses = []
    
    for _ in range(n_particles):
        pos = random_particle_position(num_orders)
        vel = random_particle_velocity(num_orders, max_vel)
        
        swarm_positions.append(pos)
        swarm_velocities.append(vel)
        
        # Initial personal best
        schedule = decode_particle_to_schedule(pos, config, orders, horizon_days)
        if use_soft_fitness:
            fitness = compute_soft_fitness(schedule, config, orders, soft_alpha, soft_beta, soft_gamma)
        else:
            eval_result = evaluate_schedule(schedule, config, orders)
            fitness = eval_result.profit
        
        personal_best_positions.append(pos.copy())
        personal_best_fitnesses.append(fitness)
    
    # Find global best
    global_best_idx = max(range(n_particles), key=lambda i: personal_best_fitnesses[i])
    global_best_position = personal_best_positions[global_best_idx].copy()
    global_best_fitness = personal_best_fitnesses[global_best_idx]
    
    # Main PSO loop
    for iteration in range(iterations):
        # Update each particle
        for i in range(n_particles):
            # Update velocity
            swarm_velocities[i] = update_particle_velocity(
                swarm_positions[i], swarm_velocities[i],
                personal_best_positions[i], global_best_position,
                w, c1, c2, max_vel
            )
            
            # Update position
            swarm_positions[i] = update_particle_position(swarm_positions[i], swarm_velocities[i])
            
            # Evaluate new position
            schedule = decode_particle_to_schedule(swarm_positions[i], config, orders, horizon_days)
            if use_soft_fitness:
                fitness = compute_soft_fitness(schedule, config, orders, soft_alpha, soft_beta, soft_gamma)
            else:
                eval_result = evaluate_schedule(schedule, config, orders)
                fitness = eval_result.profit
            
            # Update personal best
            if fitness > personal_best_fitnesses[i]:
                personal_best_fitnesses[i] = fitness
                personal_best_positions[i] = swarm_positions[i].copy()
                
                # Update global best
                if fitness > global_best_fitness:
                    global_best_fitness = fitness
                    global_best_position = swarm_positions[i].copy()
        
        # Adaptive inertia weight (linear decrease)
        w = 0.9 - 0.4 * (iteration / iterations)
    
    # Final evaluation
    best_schedule = decode_particle_to_schedule(global_best_position, config, orders, horizon_days)
    best_eval = evaluate_schedule(best_schedule, config, orders)
    
    return best_schedule, best_eval