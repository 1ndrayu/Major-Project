"""
Prometheus Metrics Exporter for Cloud Microservices
Exposes standard Prometheus exposition format metrics (Golden Signals: Latency, Traffic, Errors, Saturation).
"""

import time
from typing import Dict, Any


class ServiceMetrics:
    """
    Tracks and formats Prometheus metrics for scraping.
    """
    def __init__(self, service_id: str, service_name: str):
        self.service_id = service_id
        self.service_name = service_name

        self.requests_total = 0
        self.requests_failed = 0
        self.total_duration_sec = 0.0
        self.p99_latency_ms = 35.0
        self.cpu_percent = 25.0
        self.memory_mb = 350.0

    def record_request(self, duration_ms: float, success: bool = True):
        self.requests_total += 1
        if not success:
            self.requests_failed += 1
        self.total_duration_sec += duration_ms / 1000.0
        # Running p99 estimation
        self.p99_latency_ms = round(0.9 * self.p99_latency_ms + 0.1 * duration_ms, 2)

    def to_prometheus_format(self, pool_stats: Dict[str, Any] = None) -> str:
        lines = [
            f"# HELP http_requests_total Total number of HTTP requests",
            f"# TYPE http_requests_total counter",
            f'http_requests_total{{service="{self.service_id}",app="{self.service_name}",status="200"}} {self.requests_total - self.requests_failed}',
            f'http_requests_total{{service="{self.service_id}",app="{self.service_name}",status="500"}} {self.requests_failed}',
            f"# HELP request_duration_p99_ms 99th percentile request latency in milliseconds",
            f"# TYPE request_duration_p99_ms gauge",
            f'request_duration_p99_ms{{service="{self.service_id}",app="{self.service_name}"}} {self.p99_latency_ms}',
            f"# HELP container_cpu_usage_percent CPU utilization percentage",
            f"# TYPE container_cpu_usage_percent gauge",
            f'container_cpu_usage_percent{{service="{self.service_id}",app="{self.service_name}"}} {self.cpu_percent}',
            f"# HELP container_memory_usage_mb Memory utilization in MB",
            f"# TYPE container_memory_usage_mb gauge",
            f'container_memory_usage_mb{{service="{self.service_id}",app="{self.service_name}"}} {self.memory_mb}',
        ]

        if pool_stats:
            lines.extend([
                f"# HELP hikaricp_active_connections Current active DB connections in pool",
                f"# TYPE hikaricp_active_connections gauge",
                f'hikaricp_active_connections{{service="{self.service_id}",pool="{pool_stats.get("pool_name", "HikariPool-1")}"}} {pool_stats.get("active_connections", 0)}',
                f"# HELP hikaricp_max_connections Maximum allowed DB connections in pool",
                f"# TYPE hikaricp_max_connections gauge",
                f'hikaricp_max_connections{{service="{self.service_id}",pool="{pool_stats.get("pool_name", "HikariPool-1")}"}} {pool_stats.get("maximum_pool_size", 50)}',
            ])

        return "\n".join(lines) + "\n"
