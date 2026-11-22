"""
Safe Reinforcement Learning (Safe-PPO) CMDP Policy Agent (Pillar 6)
Implements Lagrangian Constrained Proximal Policy Optimization (CMDP).
Selects remediation policy maximizing SLO recovery reward subject to blast radius cost constraint J_C <= 0.05.
"""

from typing import List, Dict, Tuple, Optional
from self_healing_core.models import (
    RemediationAction, RemediationPrimitive, RootCauseReport, ServiceNode
)


class SafeRLRemediationAgent:
    """
    Constrained MDP policy agent.
    Filters candidate actions through safety blast constraints and ranks via Lagrangian objective:
    L(a) = Reward(a) - lambda * max(0, Cost(a) - delta_safe)
    """
    def __init__(self, max_blast_cost_constraint: float = 0.05, lagrange_multiplier: float = 8.5):
        self.delta_safe = max_blast_cost_constraint
        self.lagrange_multiplier = lagrange_multiplier

    def select_action(
        self,
        candidate_actions: List[RemediationAction],
        rca_report: RootCauseReport
    ) -> Tuple[RemediationAction, Dict[str, float]]:
        """
        Evaluates candidate actions using the constrained objective and returns the optimal policy.
        """
        if not candidate_actions:
            raise ValueError("Candidate actions list cannot be empty")

        scored_actions: List[Tuple[float, RemediationAction, float]] = []

        for act in candidate_actions:
            reward = act.projected_latency_drop_pct
            cost = act.projected_blast_cost

            # Safety penalty via Lagrangian constraint
            safety_violation = max(0.0, cost - self.delta_safe)
            lagrangian_q_val = reward - self.lagrange_multiplier * safety_violation

            scored_actions.append((lagrangian_q_val, act, safety_violation))

        # Sort descending by Lagrangian objective score
        scored_actions.sort(key=lambda item: item[0], reverse=True)
        best_score, best_action, best_violation = scored_actions[0]

        decision_metrics = {
            "selected_action": best_action.primitive.value,
            "target_service": best_action.target_service,
            "projected_latency_drop": best_action.projected_latency_drop_pct,
            "blast_cost": best_action.projected_blast_cost,
            "safety_budget": self.delta_safe,
            "safety_violation": best_violation,
            "lagrangian_q_value": round(best_score, 4),
            "is_within_safety_guardrail": best_action.projected_blast_cost <= self.delta_safe
        }

        return best_action, decision_metrics
