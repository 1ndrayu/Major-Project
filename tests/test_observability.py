"""Unit tests for Observability, 100-Service Topology and Metrics Scraping"""
import unittest
from self_healing_core.observability.collector import TelemetryCollector
from self_healing_core.models import FaultType, ServiceStatus

class TestObservability(unittest.TestCase):
    def setUp(self):
        self.collector = TelemetryCollector()

    def test_cluster_initialization(self):
        self.assertEqual(len(self.collector.nodes), 100)
        self.assertGreater(len(self.collector.edges), 40)
        for nid, node in self.collector.nodes.items():
            self.assertEqual(node.status, ServiceStatus.HEALTHY)
            self.assertEqual(node.active_fault, FaultType.NONE)

    def test_fault_injection_and_clear(self):
        self.collector.inject_fault("svc-066", FaultType.DB_POOL_EXHAUSTION)
        frame = self.collector.step_telemetry_simulation()
        node = frame.nodes["svc-066"]
        self.assertEqual(node.status, ServiceStatus.CRITICAL)
        self.assertEqual(node.db_pool_active, node.db_pool_max)

        self.collector.clear_fault("svc-066")
        frame_after = self.collector.step_telemetry_simulation()
        node_after = frame_after.nodes["svc-066"]
        self.assertEqual(node_after.status, ServiceStatus.HEALTHY)

if __name__ == "__main__":
    unittest.main()
