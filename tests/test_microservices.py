"""
Unit and Integration Tests for Generated Microservices
Tests OpenTelemetry tracing, HikariCP pool dynamics, Prometheus metrics, and health probes.
"""

import unittest
import importlib.util
import os
import sys

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

from microservices.common.tracing import TraceContext, inject_w3c_trace, extract_w3c_trace
from microservices.common.pool import HikariConnectionPool, HikariPoolExhaustedException
from microservices.common.circuit_breaker import CircuitBreaker, CircuitState
from microservices.common.metrics import ServiceMetrics


class TestMicroserviceCommon(unittest.TestCase):
    def test_w3c_trace_context(self):
        ctx = TraceContext(trace_id="4bf92f3577b34da6a3ce929d0e0e4736", span_id="00f067aa0ba902b7")
        header_val = ctx.to_header()
        self.assertEqual(header_val, "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01")

        extracted = extract_w3c_trace({"traceparent": header_val})
        self.assertEqual(extracted.trace_id, "4bf92f3577b34da6a3ce929d0e0e4736")
        self.assertEqual(extracted.parent_span_id, "00f067aa0ba902b7")

    def test_hikaricp_pool_lease_and_exhaustion(self):
        pool = HikariConnectionPool(maximum_pool_size=2)
        import asyncio

        async def run_pool_test():
            # Acquire 2
            await pool.acquire_connection("lease-1")
            await pool.acquire_connection("lease-2")
            self.assertEqual(pool.active_connections, 2)

            # 3rd should fail
            with self.assertRaises(HikariPoolExhaustedException):
                await pool.acquire_connection("lease-3")

            # Release 1
            await pool.release_connection("lease-1")
            self.assertEqual(pool.active_connections, 1)

            # Dynamic ConfigMap resize 2 -> 10
            pool.resize_pool(10)
            self.assertEqual(pool.maximum_pool_size, 10)

        asyncio.run(run_pool_test())

    def test_circuit_breaker_tripping(self):
        cb = CircuitBreaker(failure_rate_threshold_pct=50.0, sliding_window_size=10)
        # Record 10 failures
        for _ in range(10):
            cb.record_result(success=False)
        self.assertEqual(cb.state, CircuitState.OPEN)
        self.assertFalse(cb.is_call_permitted())

    def test_prometheus_metrics_export(self):
        metrics = ServiceMetrics("svc-066", "Order-DB-Adapter")
        metrics.record_request(duration_ms=45.2, success=True)
        raw_prom = metrics.to_prometheus_format({"pool_name": "HikariPool-1", "active_connections": 15, "maximum_pool_size": 50})
        self.assertIn("http_requests_total", raw_prom)
        self.assertIn("hikaricp_active_connections", raw_prom)
        self.assertIn("svc-066", raw_prom)


class TestGeneratedMicroservices(unittest.TestCase):
    def test_order_db_adapter_app(self):
        svc_path = os.path.join(BASE_DIR, "microservices", "svc_066_order_db_adapter", "app.py")
        self.assertTrue(os.path.exists(svc_path))

        spec = importlib.util.spec_from_file_location("app_066", svc_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        self.assertEqual(mod.SERVICE_ID, "svc-066")
        self.assertEqual(mod.SERVICE_NAME, "Order-DB-Adapter")
        self.assertEqual(mod.db_pool.maximum_pool_size, 50)

    def test_checkout_api_app(self):
        svc_path = os.path.join(BASE_DIR, "microservices", "svc_016_checkout_api_service", "app.py")
        self.assertTrue(os.path.exists(svc_path))

        spec = importlib.util.spec_from_file_location("app_016", svc_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        self.assertEqual(mod.SERVICE_ID, "svc-016")
        self.assertEqual(mod.SERVICE_NAME, "Checkout-API-Service")


if __name__ == "__main__":
    unittest.main()
