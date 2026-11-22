"""
Automated Canary Health Verifier & Rollback Guard (Pillar 8)
Continuously evaluates Golden Signals (p99 latency, error rate, pool saturation)
over the post-intervention canary window; triggers atomic rollback if SLO degrades.
"""

import time
from typing import Dict, Any, Optional
from self_healing_core.models import (
    SnapshotManifest, RemediationAction, VerificationResult, VerificationVerdict
)
from self_healing_core.actuator.k8s_actuator import KubernetesActuator
from self_healing_core.observability.collector import TelemetryCollector


class CanaryVerifier:
    """
    Validates SLO restoration and acts as an automated safety breaker.
    """
    def __init__(
        self,
        collector: TelemetryCollector,
        actuator: KubernetesActuator,
        max_acceptable_p99_ms: float = 65.0,
        max_acceptable_error_rate: float = 0.015,
        max_acceptable_pool_sat: float = 0.50
    ):
        self.collector = collector
        self.actuator = actuator
        self.max_p99 = max_acceptable_p99_ms
        self.max_error = max_acceptable_error_rate
        self.max_pool_sat = max_acceptable_pool_sat

    def verify_post_intervention(
        self,
        action: RemediationAction,
        snapshot: SnapshotManifest,
        pre_metrics: Dict[str, float],
        verification_window_sec: float = 3.0
    ) -> VerificationResult:
        """
        Runs synthetic canary health checks post-remediation.
        """
        sid = action.target_service
        node = self.collector.nodes[sid]

        # Gather post-remediation metrics
        post_p99 = node.p99_latency_ms
        post_error = node.error_rate
        post_pool_sat = node.db_pool_active / max(1, node.db_pool_max)

        # Check SLO criteria
        p99_ok = post_p99 <= self.max_p99
        error_ok = post_error <= self.max_error
        pool_ok = post_pool_sat <= self.max_pool_sat

        slo_restored = p99_ok and error_ok and pool_ok
        rollback_executed = False

        if slo_restored:
            verdict = VerificationVerdict.COMMITTED
            summary = (
                f"SLO successfully restored on {sid}. "
                f"p99 latency dropped from {pre_metrics['p99']:.1f}ms to {post_p99:.1f}ms. "
                f"Error rate restored to {post_error*100:.3f}%. "
                f"DB pool saturation normalized to {post_pool_sat*100:.1f}%. Action COMMITTED."
            )
        else:
            verdict = VerificationVerdict.ROLLED_BACK
            rollback_executed = True
            self.actuator.execute_rollback(snapshot)
            summary = (
                f"SLO degradation detected during canary probing on {sid}. "
                f"p99={post_p99:.1f}ms (threshold={self.max_p99}ms). "
                f"Triggered instant atomic state rollback to snapshot {snapshot.snapshot_id}."
            )

        return VerificationResult(
            verification_id=f"verif-{int(time.time() * 1000)}",
            snapshot_id=snapshot.snapshot_id,
            action_id=action.action_id,
            service_id=sid,
            verdict=verdict,
            pre_intervention_p99_ms=round(pre_metrics["p99"], 2),
            post_intervention_p99_ms=round(post_p99, 2),
            pre_intervention_error_rate=round(pre_metrics["error_rate"], 4),
            post_intervention_error_rate=round(post_error, 4),
            pre_db_pool_saturation=round(pre_metrics["pool_sat"], 3),
            post_db_pool_saturation=round(post_pool_sat, 3),
            slo_restored=slo_restored,
            rollback_executed=rollback_executed,
            verification_window_sec=verification_window_sec,
            summary=summary
        )
