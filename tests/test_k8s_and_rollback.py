"""Unit tests for Kubernetes Actuator, Etcd Snapshotting, and Atomic Rollback Guard"""
import unittest
from self_healing_core.observability.collector import TelemetryCollector
from self_healing_core.actuator.k8s_actuator import KubernetesActuator
from self_healing_core.verification.canary_verifier import CanaryVerifier
from self_healing_core.models import (
    RemediationAction, RemediationPrimitive, VerificationVerdict
)

class TestKubernetesRollback(unittest.TestCase):
    def setUp(self):
        self.collector = TelemetryCollector()
        self.actuator = KubernetesActuator(self.collector)
        self.verifier = CanaryVerifier(self.collector, self.actuator, max_acceptable_p99_ms=60.0)

    def test_etcd_snapshot_and_rollback(self):
        # 1. Snapshot original state
        snap = self.actuator.snapshot_state("svc-066")
        self.assertEqual(snap.db_pool_max, 50)
        self.assertEqual(snap.service_id, "svc-066")

        # 2. Apply a mutation
        action = RemediationAction(
            action_id="test-action-1",
            primitive=RemediationPrimitive.RESIZE_DB_CONN_POOL,
            target_service="svc-066",
            parameters={"max_connections": 120},
            projected_latency_drop_pct=0.88,
            projected_blast_cost=0.01,
            rationale="Test pool resize"
        )
        self.actuator.apply_remediation(action)
        self.assertEqual(self.collector.nodes["svc-066"].db_pool_max, 120)

        # 3. Simulate failure causing canary probe rejection
        self.collector.nodes["svc-066"].p99_latency_ms = 950.0  # severely violates 60ms threshold
        pre_metrics = {"p99": 1800.0, "error_rate": 0.25, "pool_sat": 1.0}

        verif_result = self.verifier.verify_post_intervention(action, snap, pre_metrics)

        # 4. Verify rollback triggered and executed
        self.assertEqual(verif_result.verdict, VerificationVerdict.ROLLED_BACK)
        self.assertTrue(verif_result.rollback_executed)
        self.assertFalse(verif_result.slo_restored)
        self.assertEqual(self.collector.nodes["svc-066"].db_pool_max, 50, "Must restore original max pool size")

if __name__ == "__main__":
    unittest.main()
