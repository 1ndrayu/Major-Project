"""
Chaos Engineering & Fault Injection Engine
Simulates realistic failure scenarios (ChaosMesh / stress-ng style) across the 100-microservice cluster.
"""

from typing import Dict, Any, List
from self_healing_core.models import FaultType
from self_healing_core.observability.collector import TelemetryCollector


class ChaosFaultInjector:
    """
    Executes targeted chaos experiments to validate the self-healing ecosystem.
    """
    def __init__(self, collector: TelemetryCollector):
        self.collector = collector

    def inject_db_pool_exhaustion(self, target_service: str = "svc-066") -> Dict[str, Any]:
        """
        Scenario 1 (Primary Case Study): Relational database connection pool exhaustion
        on Order-DB-Adapter (svc-066). Squeezes pool to 100%, causing cascading timeouts.
        """
        self.collector.inject_fault(target_service, FaultType.DB_POOL_EXHAUSTION)
        return {
            "scenario": "DATABASE_CONNECTION_POOL_EXHAUSTION",
            "target_service": target_service,
            "target_name": self.collector.nodes[target_service].name,
            "description": "Simulated HikariCP pool exhaustion with connection leak and query pileup",
            "expected_symptoms": ["p99 latency spike to 1850ms", "HikariPool timeout exceptions", "cascading checkout failures"]
        }

    def inject_memory_leak(self, target_service: str = "svc-020") -> Dict[str, Any]:
        """
        Scenario 2: Memory leak and stop-the-world GC thrashing on Payment-Settlement-Core (svc-020).
        """
        self.collector.inject_fault(target_service, FaultType.MEMORY_LEAK)
        return {
            "scenario": "MEMORY_LEAK_AND_GC_THRASHING",
            "target_service": target_service,
            "target_name": self.collector.nodes[target_service].name,
            "description": "Simulated uncollected heap buffers triggering GC pauses and OOM risk",
            "expected_symptoms": ["Heap utilization > 95%", "Stop-the-world GC latency", "HTTP 500 error surge"]
        }

    def inject_cpu_hog(self, target_service: str = "svc-018") -> Dict[str, Any]:
        """
        Scenario 3: CPU hogging / thread pool starvation on Cart-State-Service (svc-018).
        """
        self.collector.inject_fault(target_service, FaultType.CPU_HOGGING)
        return {
            "scenario": "CPU_HOGGING_THREAD_STARVATION",
            "target_service": target_service,
            "target_name": self.collector.nodes[target_service].name,
            "description": "Runaway computational loop pegging CPU to 99%",
            "expected_symptoms": ["CPU saturation > 98%", "Queue buildup", "Gradual latency degradation"]
        }

    def inject_retry_storm(self, target_service: str = "svc-016") -> Dict[str, Any]:
        """
        Scenario 4: Cascading retry storm on Checkout-API-Service (svc-016).
        """
        self.collector.inject_fault(target_service, FaultType.RETRY_STORM)
        return {
            "scenario": "CASCADING_RETRY_STORM",
            "target_service": target_service,
            "target_name": self.collector.nodes[target_service].name,
            "description": "Aggressive client retry loops multiplying inbound traffic by 3.5x",
            "expected_symptoms": ["Inbound RPS surge", "DEADLINE_EXCEEDED errors", "Thread saturation"]
        }

    def clear_all(self):
        """Restores healthy baseline across all services."""
        for sid in list(self.collector.active_faults.keys()):
            self.collector.clear_fault(sid)
