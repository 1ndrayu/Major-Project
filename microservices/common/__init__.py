"""
Shared Microservice Infrastructure Package
OpenTelemetry Tracing, HikariCP Connection Pool, Circuit Breaker, and Prometheus Metrics.
"""

from .tracing import TraceContext, inject_w3c_trace, extract_w3c_trace
from .pool import HikariConnectionPool
from .circuit_breaker import CircuitBreaker
from .metrics import ServiceMetrics

__all__ = [
    "TraceContext",
    "inject_w3c_trace",
    "extract_w3c_trace",
    "HikariConnectionPool",
    "CircuitBreaker",
    "ServiceMetrics",
]
