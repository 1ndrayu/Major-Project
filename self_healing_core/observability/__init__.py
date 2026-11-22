"""
Observability Package
Handles OpenTelemetry trace collection, Prometheus metric scraping, and Loki log ingestion.
"""

from .collector import TelemetryCollector
from .topology_generator import generate_100_service_topology

__all__ = ["TelemetryCollector", "generate_100_service_topology"]
