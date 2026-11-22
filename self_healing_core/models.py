"""
Data Models and Enums for the Autonomous Self-Healing Software Ecosystem
Implements the core domain models defined in UML Class Diagram (Figure 5.2).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Any
import time


class ServiceTier(str, Enum):
    FRONTEND = "FRONTEND"
    GATEWAY = "GATEWAY"
    MIDDLEWARE = "MIDDLEWARE"
    ORDER_PAYMENT = "ORDER_PAYMENT"
    DATABASE = "DATABASE"
    MESSAGING = "MESSAGING"
    ANALYTICS = "ANALYTICS"


class ServiceStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"
    SELF_HEALING = "SELF_HEALING"
    RECOVERED = "RECOVERED"


class FaultType(str, Enum):
    NONE = "NONE"
    DB_POOL_EXHAUSTION = "DB_POOL_EXHAUSTION"
    MEMORY_LEAK = "MEMORY_LEAK"
    CPU_HOGGING = "CPU_HOGGING"
    RETRY_STORM = "RETRY_STORM"
    NETWORK_LATENCY = "NETWORK_LATENCY"
    THREAD_STARVATION = "THREAD_STARVATION"


class RemediationPrimitive(str, Enum):
    RESIZE_DB_CONN_POOL = "RESIZE_DB_CONN_POOL"
    HORIZONTAL_POD_AUTOSCALE = "HORIZONTAL_POD_AUTOSCALE"
    CIRCUIT_BREAK = "CIRCUIT_BREAK"
    GRACEFUL_POD_RESTART = "GRACEFUL_POD_RESTART"
    RATE_LIMIT_ADAPTIVE = "RATE_LIMIT_ADAPTIVE"
    CONFIGMAP_HOT_RELOAD = "CONFIGMAP_HOT_RELOAD"


class VerificationVerdict(str, Enum):
    COMMITTED = "COMMITTED"
    ROLLED_BACK = "ROLLED_BACK"
    PENDING = "PENDING"


@dataclass
class ServiceNode:
    id: str
    name: str
    tier: ServiceTier
    host_node: str
    replicas: int = 3
    cpu_percent: float = 25.0
    memory_mb: float = 350.0
    memory_limit_mb: float = 1024.0
    db_pool_active: int = 15
    db_pool_max: int = 50
    db_idle_timeout_sec: int = 30
    p95_latency_ms: float = 22.0
    p99_latency_ms: float = 35.0
    request_rate_rps: float = 150.0
    error_rate: float = 0.001
    status: ServiceStatus = ServiceStatus.HEALTHY
    active_fault: FaultType = FaultType.NONE
    labels: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "tier": self.tier.value,
            "host_node": self.host_node,
            "replicas": self.replicas,
            "cpu_percent": round(self.cpu_percent, 2),
            "memory_mb": round(self.memory_mb, 2),
            "memory_limit_mb": self.memory_limit_mb,
            "db_pool_active": self.db_pool_active,
            "db_pool_max": self.db_pool_max,
            "db_pool_saturation": round(self.db_pool_active / max(1, self.db_pool_max), 3),
            "p95_latency_ms": round(self.p95_latency_ms, 2),
            "p99_latency_ms": round(self.p99_latency_ms, 2),
            "request_rate_rps": round(self.request_rate_rps, 2),
            "error_rate": round(self.error_rate, 4),
            "status": self.status.value,
            "active_fault": self.active_fault.value,
            "labels": self.labels,
        }


@dataclass
class CallEdge:
    source: str
    target: str
    edge_type: str = "RPC_CALL"
    request_rate_rps: float = 120.0
    p95_latency_ms: float = 20.0
    p99_latency_ms: float = 35.0
    error_rate: float = 0.001
    circuit_breaker_open: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "edge_type": self.edge_type,
            "request_rate_rps": round(self.request_rate_rps, 2),
            "p95_latency_ms": round(self.p95_latency_ms, 2),
            "p99_latency_ms": round(self.p99_latency_ms, 2),
            "error_rate": round(self.error_rate, 4),
            "circuit_breaker_open": self.circuit_breaker_open,
        }


@dataclass
class LogEntry:
    timestamp: float
    service_id: str
    level: str  # INFO, WARN, ERROR, CRITICAL
    message: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None


@dataclass
class TelemetryFrame:
    timestamp: float
    nodes: Dict[str, ServiceNode]
    edges: List[CallEdge]
    logs: List[LogEntry]
    system_p99_ms: float
    system_error_rate: float
    system_total_rps: float


@dataclass
class AnomalyScore:
    service_id: str
    z_score: float
    metric_deviations: Dict[str, float]
    log_anomaly_detected: bool
    log_patterns: List[str]
    is_anomalous: bool


@dataclass
class AnomalyEvent:
    event_id: str
    timestamp: float
    primary_anomalous_service: str
    affected_services: List[str]
    max_z_score: float
    metric_signals: Dict[str, float]
    log_evidence: List[str]
    anomaly_scores: Dict[str, AnomalyScore]


@dataclass
class RootCauseCandidate:
    service_id: str
    fault_type: FaultType
    confidence_score: float  # [0.0, 1.0]
    prior_score: float
    telemetry_evidence: float
    gnn_residual: float
    causal_effect_do_x: float
    explanation: str


@dataclass
class RootCauseReport:
    incident_id: str
    timestamp: float
    culprit_service: str
    fault_type: FaultType
    causal_confidence: float
    blast_radius: List[str]
    candidates_ranked: List[RootCauseCandidate]
    evidence_summary: str
    counterfactual_expected_gain: float


@dataclass
class RemediationAction:
    action_id: str
    primitive: RemediationPrimitive
    target_service: str
    parameters: Dict[str, Any]
    projected_latency_drop_pct: float
    projected_blast_cost: float
    rationale: str


@dataclass
class SnapshotManifest:
    snapshot_id: str
    service_id: str
    timestamp: float
    replicas: int
    db_pool_max: int
    db_idle_timeout_sec: int
    circuit_breaker_open: bool
    rate_limit_rps: float
    config_map: Dict[str, Any]


@dataclass
class VerificationResult:
    verification_id: str
    snapshot_id: str
    action_id: str
    service_id: str
    verdict: VerificationVerdict
    pre_intervention_p99_ms: float
    post_intervention_p99_ms: float
    pre_intervention_error_rate: float
    post_intervention_error_rate: float
    pre_db_pool_saturation: float
    post_db_pool_saturation: float
    slo_restored: bool
    rollback_executed: bool
    verification_window_sec: float
    summary: str


@dataclass
class IncidentRecord:
    incident_id: str
    start_time: float
    resolved_time: Optional[float]
    culprit_service: str
    fault_injected: FaultType
    root_cause_identified: str
    rca_accuracy: bool
    remediation_action: RemediationAction
    verification: VerificationResult
    mttd_seconds: float
    mttr_seconds: float
    etcd_snapshot: SnapshotManifest
    post_mortem_notes: str
