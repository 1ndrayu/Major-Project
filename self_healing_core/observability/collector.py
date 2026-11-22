"""
Full-Stack Telemetry Collector (Pillar 1)
Ingests and aligns real-time distributed traces (OTel), container metrics (Prometheus),
and structured logs (Loki) across the 100-microservice cluster.
Simulates realistic runtime telemetry dynamics and cascading backpressure propagation.
"""

import time
import random
import copy
from typing import Dict, List, Optional, Tuple, Set
from self_healing_core.models import (
    ServiceNode, CallEdge, LogEntry, TelemetryFrame, ServiceStatus, FaultType
)
from .topology_generator import generate_100_service_topology


class TelemetryCollector:
    """
    Simulates the OpenTelemetry Collector + Prometheus Scraper daemon.
    Continuously updates metrics, propagates realistic cascading backpressure across
    service call chains, and yields aligned multimodal telemetry frames.
    """
    def __init__(self, random_seed: int = 42):
        random.seed(random_seed)
        self.nodes, self.edges = generate_100_service_topology()
        self.base_nodes = copy.deepcopy(self.nodes)
        self.base_edges = copy.deepcopy(self.edges)
        self.active_faults: Dict[str, FaultType] = {}
        self.fault_start_times: Dict[str, float] = {}
        self.log_buffer: List[LogEntry] = []
        self.last_scrape_time = time.time()

        # Build reverse caller adjacency for fast upstream propagation
        self.upstream_callers: Dict[str, List[str]] = {nid: [] for nid in self.nodes}
        for edge in self.edges:
            self.upstream_callers[edge.target].append(edge.source)

    def inject_fault(self, service_id: str, fault: FaultType):
        """Injects a specific fault into a microservice node."""
        if service_id in self.nodes:
            self.active_faults[service_id] = fault
            self.fault_start_times[service_id] = time.time()
            node = self.nodes[service_id]
            node.active_fault = fault
            node.status = ServiceStatus.CRITICAL

    def clear_fault(self, service_id: str):
        """Clears active fault from a microservice and restores healthy baseline."""
        if service_id in self.active_faults:
            del self.active_faults[service_id]
            if service_id in self.fault_start_times:
                del self.fault_start_times[service_id]
        if service_id in self.nodes:
            base = self.base_nodes[service_id]
            self.nodes[service_id].cpu_percent = base.cpu_percent
            self.nodes[service_id].memory_mb = base.memory_mb
            self.nodes[service_id].db_pool_active = base.db_pool_active
            self.nodes[service_id].db_pool_max = base.db_pool_max
            self.nodes[service_id].p95_latency_ms = base.p95_latency_ms
            self.nodes[service_id].p99_latency_ms = base.p99_latency_ms
            self.nodes[service_id].error_rate = base.error_rate
            self.nodes[service_id].status = ServiceStatus.HEALTHY
            self.nodes[service_id].active_fault = FaultType.NONE

    def get_upstream_chain(self, root_id: str, max_depth: int = 4) -> Set[str]:
        """Calculates upstream blast radius services affected by downstream backpressure."""
        visited = set()
        queue = [(root_id, 0)]
        while queue:
            curr, depth = queue.pop(0)
            if depth >= max_depth:
                continue
            for caller in self.upstream_callers.get(curr, []):
                if caller not in visited:
                    visited.add(caller)
                    queue.append((caller, depth + 1))
        return visited

    def step_telemetry_simulation(self) -> TelemetryFrame:
        """
        Executes one discrete simulation tick (e.g. 5-second Prometheus scrape window).
        Applies organic background jitter and models cascading fault propagation.
        """
        now = time.time()
        new_logs: List[LogEntry] = []

        # 1. Apply baseline organic jitter to all services
        for sid, node in self.nodes.items():
            base = self.base_nodes[sid]
            jitter = (random.random() - 0.5) * 0.08  # +/- 4%
            node.cpu_percent = max(5.0, min(100.0, base.cpu_percent * (1.0 + jitter)))
            node.memory_mb = max(50.0, base.memory_mb * (1.0 + jitter * 0.5))
            node.db_pool_active = max(1, min(node.db_pool_max, int(base.db_pool_active * (1.0 + jitter))))
            node.p95_latency_ms = max(5.0, base.p95_latency_ms * (1.0 + jitter))
            node.p99_latency_ms = max(8.0, base.p99_latency_ms * (1.0 + jitter * 1.2))
            node.error_rate = max(0.0001, base.error_rate * (1.0 + jitter))
            node.status = ServiceStatus.HEALTHY

        # 2. Apply active faults and compute cascading upstream propagation
        affected_upstream_overall: Set[str] = set()

        for fault_sid, fault_type in list(self.active_faults.items()):
            if fault_sid not in self.nodes:
                continue
            fault_node = self.nodes[fault_sid]
            fault_node.active_fault = fault_type
            fault_node.status = ServiceStatus.CRITICAL

            if fault_type == FaultType.DB_POOL_EXHAUSTION:
                # Primary root cause: HikariPool connection pool saturation
                fault_node.db_pool_active = fault_node.db_pool_max
                fault_node.p95_latency_ms = 1250.0 + random.uniform(50, 200)
                fault_node.p99_latency_ms = 1850.0 + random.uniform(50, 300)
                fault_node.error_rate = 0.28 + random.uniform(0.02, 0.08)
                fault_node.cpu_percent = min(95.0, fault_node.cpu_percent + 20.0)

                new_logs.append(LogEntry(
                    timestamp=now,
                    service_id=fault_sid,
                    level="ERROR",
                    message=f"HikariPool-1 - Connection is not available, request timed out after 30005ms (active={fault_node.db_pool_active}/{fault_node.db_pool_max})",
                    trace_id=f"trace-{int(now * 1000)}"
                ))

            elif fault_type == FaultType.MEMORY_LEAK:
                fault_node.memory_mb = min(fault_node.memory_limit_mb * 0.98, fault_node.memory_mb * 1.8 + 400.0)
                fault_node.cpu_percent = min(98.0, fault_node.cpu_percent + 45.0)  # GC thrashing
                fault_node.p99_latency_ms = 1450.0 + random.uniform(100, 250)
                fault_node.error_rate = 0.15 + random.uniform(0.01, 0.05)

                new_logs.append(LogEntry(
                    timestamp=now,
                    service_id=fault_sid,
                    level="CRITICAL",
                    message=f"java.lang.OutOfMemoryError: Java heap space during buffer allocation ({fault_node.memory_mb:.1f}MB/{fault_node.memory_limit_mb:.1f}MB)"
                ))

            elif fault_type == FaultType.CPU_HOGGING:
                fault_node.cpu_percent = 98.5 + random.uniform(0.5, 1.4)
                fault_node.p99_latency_ms = 920.0 + random.uniform(50, 150)
                fault_node.error_rate = 0.08 + random.uniform(0.01, 0.03)

                new_logs.append(LogEntry(
                    timestamp=now,
                    service_id=fault_sid,
                    level="WARN",
                    message="CPU utilization exceeded 95% threshold for 3 consecutive scraping intervals"
                ))

            elif fault_type == FaultType.RETRY_STORM:
                fault_node.request_rate_rps = fault_node.request_rate_rps * 3.5
                fault_node.cpu_percent = min(96.0, fault_node.cpu_percent + 35.0)
                fault_node.p99_latency_ms = 1100.0 + random.uniform(50, 200)
                fault_node.error_rate = 0.22 + random.uniform(0.02, 0.06)

                new_logs.append(LogEntry(
                    timestamp=now,
                    service_id=fault_sid,
                    level="ERROR",
                    message="Client retry storm detected: inbound RPS tripled, circuit breaker approaching threshold"
                ))

            # Cascade upstream backpressure
            upstream_set = self.get_upstream_chain(fault_sid, max_depth=3)
            affected_upstream_overall.update(upstream_set)

            # Upstream callers degrade due to waiting on the slow dependency
            for up_id in upstream_set:
                up_node = self.nodes[up_id]
                up_node.status = ServiceStatus.DEGRADED
                up_node.p99_latency_ms = max(up_node.p99_latency_ms, fault_node.p99_latency_ms * 0.85)
                up_node.p95_latency_ms = max(up_node.p95_latency_ms, fault_node.p95_latency_ms * 0.80)
                up_node.error_rate = max(up_node.error_rate, 0.06 + random.uniform(0.01, 0.04))
                new_logs.append(LogEntry(
                    timestamp=now,
                    service_id=up_id,
                    level="WARN",
                    message=f"Upstream thread pool congestion: timeout waiting for downstream response from {fault_node.name}"
                ))

        # 3. Synchronize call edges with node latencies
        for edge in self.edges:
            target_node = self.nodes[edge.target]
            source_node = self.nodes[edge.source]
            edge.p99_latency_ms = target_node.p99_latency_ms * 0.95
            edge.p95_latency_ms = target_node.p95_latency_ms * 0.90
            edge.error_rate = max(source_node.error_rate, target_node.error_rate)

        # 4. Compute holistic cluster Golden Signals
        avg_p99 = sum(n.p99_latency_ms for n in self.nodes.values()) / len(self.nodes)
        max_p99 = max(n.p99_latency_ms for n in self.nodes.values())
        weighted_error = sum(n.error_rate * n.request_rate_rps for n in self.nodes.values()) / max(1.0, sum(n.request_rate_rps for n in self.nodes.values()))
        total_rps = sum(n.request_rate_rps for n in self.nodes.values())

        # Store latest logs (keep last 200)
        self.log_buffer.extend(new_logs)
        if len(self.log_buffer) > 200:
            self.log_buffer = self.log_buffer[-200:]

        return TelemetryFrame(
            timestamp=now,
            nodes=copy.deepcopy(self.nodes),
            edges=copy.deepcopy(self.edges),
            logs=new_logs,
            system_p99_ms=round(max_p99, 2),
            system_error_rate=round(weighted_error, 4),
            system_total_rps=round(total_rps, 2)
        )
