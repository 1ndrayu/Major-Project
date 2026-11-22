"""
Comprehensive Test Suite for Self-Healing Software Ecosystem
Tests all 8 pillars and the 6-stage closed-loop autonomous remediation pipeline.
"""

import unittest
import time
from self_healing_core.models import FaultType, VerificationVerdict, RemediationPrimitive
from self_healing_core.orchestrator import SelfHealingOrchestrator
from self_healing_core.chaos.fault_injector import ChaosFaultInjector


class TestSelfHealingEcosystem(unittest.TestCase):
    def setUp(self):
        self.orchestrator = SelfHealingOrchestrator()
        self.injector = ChaosFaultInjector(self.orchestrator.collector)

    def test_01_observability_and_topology(self):
        """Pillar 1: Test 100-microservice topology and telemetry frame structure."""
        frame = self.orchestrator.tick_observability()
        self.assertEqual(len(frame.nodes), 100, "Should generate exactly 100 microservices")
        self.assertGreater(len(frame.edges), 40, "Should contain realistic inter-service call edges")
        self.assertIn("svc-066", frame.nodes, "Order-DB-Adapter must be present")
        self.assertEqual(frame.nodes["svc-066"].name, "Order-DB-Adapter")
        self.assertLess(frame.system_p99_ms, 100.0, "Baseline healthy p99 latency should be < 100ms")

    def test_02_anomaly_detection_baseline(self):
        """Pillar 2: Test normal baseline produces no spurious anomalies."""
        self.orchestrator.tick_observability()
        anomaly = self.orchestrator.run_stage_1_anomaly_detection()
        self.assertIsNone(anomaly, "Baseline system should have no active anomalies")

    def test_03_db_pool_exhaustion_detection(self):
        """Pillar 1 & 2: Test detection of DB connection pool exhaustion (z > 3.2 sigma)."""
        # Inject fault into Order-DB-Adapter (svc-066)
        self.injector.inject_db_pool_exhaustion("svc-066")
        frame = self.orchestrator.tick_observability()

        # Order-DB-Adapter should be saturated and high latency
        node = frame.nodes["svc-066"]
        self.assertEqual(node.db_pool_active, node.db_pool_max)
        self.assertGreater(node.p99_latency_ms, 1500.0)

        # Stage 1 Anomaly Detection
        anomaly = self.orchestrator.run_stage_1_anomaly_detection()
        self.assertIsNotNone(anomaly, "Anomaly detector must flag pool exhaustion")
        self.assertGreaterEqual(anomaly.max_z_score, 3.2, "Anomaly score must exceed 3.2 sigma")
        self.assertIn("svc-066", anomaly.affected_services)

    def test_04_blast_radius_extraction(self):
        """Pillar 3: Test dynamic graph blast-radius extraction."""
        self.injector.inject_db_pool_exhaustion("svc-066")
        self.orchestrator.tick_observability()
        self.orchestrator.run_stage_1_anomaly_detection()

        nodes, edges = self.orchestrator.run_stage_2_blast_radius()
        self.assertIn("svc-066", nodes)
        self.assertIn("svc-017", nodes, "Order-Orchestrator upstream caller must be in blast radius")
        self.assertGreaterEqual(len(nodes), 2)

    def test_05_gatv2_and_causal_rca(self):
        """Pillar 4 & 5: Test GATv2 edge attention and Causal SCM isolation of Order-DB-Adapter."""
        self.injector.inject_db_pool_exhaustion("svc-066")
        self.orchestrator.tick_observability()
        self.orchestrator.run_stage_1_anomaly_detection()
        self.orchestrator.run_stage_2_blast_radius()

        rca_report = self.orchestrator.run_stage_3_gnn_causal_diagnosis()
        self.assertEqual(rca_report.culprit_service, "svc-066", "Must isolate Order-DB-Adapter as true root cause")
        self.assertEqual(rca_report.fault_type, FaultType.DB_POOL_EXHAUSTION)
        self.assertGreater(rca_report.causal_confidence, 0.85, "Confidence should exceed 85%")

    def test_06_digital_twin_and_safe_rl(self):
        """Pillar 6: Test Digital Twin simulation and Safe-PPO constrained action selection."""
        self.injector.inject_db_pool_exhaustion("svc-066")
        self.orchestrator.tick_observability()
        self.orchestrator.run_stage_1_anomaly_detection()
        self.orchestrator.run_stage_2_blast_radius()
        self.orchestrator.run_stage_3_gnn_causal_diagnosis()

        # Stage 4: Digital Twin
        candidates = self.orchestrator.run_stage_4_digital_twin_simulation()
        self.assertEqual(len(candidates), 4, "Should evaluate 4 candidate remediation primitives")

        # Stage 5: Safe-PPO selection
        action, snapshot, patch = self.orchestrator.run_stage_5_safe_rl_execution()
        self.assertEqual(action.primitive, RemediationPrimitive.RESIZE_DB_CONN_POOL, "Safe-RL must select pool resizing")
        self.assertLessEqual(action.projected_blast_cost, 0.05, "Must respect safety blast radius budget <= 0.05")
        self.assertEqual(snapshot.service_id, "svc-066")
        self.assertEqual(patch["status"], "APPLIED")

    def test_07_canary_verification_and_commit(self):
        """Pillar 7 & 8: Test post-intervention canary health probing and state commit."""
        self.injector.inject_db_pool_exhaustion("svc-066")
        self.orchestrator.tick_observability()
        self.orchestrator.run_stage_1_anomaly_detection()
        self.orchestrator.run_stage_2_blast_radius()
        self.orchestrator.run_stage_3_gnn_causal_diagnosis()
        self.orchestrator.run_stage_4_digital_twin_simulation()
        self.orchestrator.run_stage_5_safe_rl_execution()

        # Stage 6: Canary Verification
        verification = self.orchestrator.run_stage_6_canary_verification()
        self.assertEqual(verification.verdict, VerificationVerdict.COMMITTED)
        self.assertTrue(verification.slo_restored)
        self.assertFalse(verification.rollback_executed)
        self.assertLess(verification.post_intervention_p99_ms, 65.0)
        self.assertEqual(len(self.orchestrator.incident_history), 1)

    def test_08_end_to_end_autonomous_cycle(self):
        """End-to-End: Test full synchronous 6-stage closed-loop execution."""
        self.injector.inject_db_pool_exhaustion("svc-066")
        result = self.orchestrator.execute_full_autonomous_cycle()

        self.assertEqual(result["status"], "REMEDIATED")
        self.assertEqual(result["culprit_service"], "svc-066")
        self.assertEqual(result["fault_type"], "DB_POOL_EXHAUSTION")
        self.assertEqual(result["selected_remediation"], "RESIZE_DB_CONN_POOL")
        self.assertEqual(result["verification_verdict"], "COMMITTED")
        self.assertLess(result["post_p99_ms"], 65.0)


if __name__ == "__main__":
    unittest.main()
