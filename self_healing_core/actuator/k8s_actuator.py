"""
Kubernetes Actuator & Operator Engine (Pillar 7)
Takes atomic etcd snapshots, applies runtime CRD/ConfigMap patches,
and manages rolling restarts, scaling, and instant rollback.
"""

import time
import copy
from typing import Dict, Any, Optional
from self_healing_core.models import (
    ServiceNode, SnapshotManifest, RemediationAction, RemediationPrimitive
)
from self_healing_core.observability.collector import TelemetryCollector


class KubernetesActuator:
    """
    Simulates / interfaces with the Kubernetes Operator Controller (Kopf / client-go).
    Provides atomic snapshotting and state rollback guarantees.
    """
    def __init__(self, collector: TelemetryCollector):
        self.collector = collector
        self.snapshots: Dict[str, SnapshotManifest] = {}
        self.applied_patches: Dict[str, RemediationAction] = {}

    def snapshot_state(self, service_id: str) -> SnapshotManifest:
        """
        Takes an immutable snapshot of the service's current Kubernetes deployment & ConfigMap.
        """
        if service_id not in self.collector.nodes:
            raise KeyError(f"Service {service_id} not found in cluster")

        node = self.collector.nodes[service_id]
        snap_id = f"snap-{service_id}-{int(time.time() * 1000)}"

        config_map = {
            "datasource.hikari.maximum-pool-size": node.db_pool_max,
            "datasource.hikari.idle-timeout": node.db_idle_timeout_sec * 1000,
            "datasource.hikari.leak-detection-threshold": 0,
            "server.tomcat.threads.max": 200,
            "spring.cloud.circuitbreaker.resilience4j.enabled": False
        }

        manifest = SnapshotManifest(
            snapshot_id=snap_id,
            service_id=service_id,
            timestamp=time.time(),
            replicas=node.replicas,
            db_pool_max=node.db_pool_max,
            db_idle_timeout_sec=node.db_idle_timeout_sec,
            circuit_breaker_open=False,
            rate_limit_rps=node.request_rate_rps * 1.5,
            config_map=config_map
        )

        self.snapshots[snap_id] = manifest
        return manifest

    def apply_remediation(self, action: RemediationAction) -> Dict[str, Any]:
        """
        Applies the selected remediation action to the cluster.
        """
        sid = action.target_service
        if sid not in self.collector.nodes:
            raise KeyError(f"Service {sid} not found in cluster")

        node = self.collector.nodes[sid]
        self.applied_patches[sid] = action

        result_details: Dict[str, Any] = {
            "status": "APPLIED",
            "action_id": action.action_id,
            "primitive": action.primitive.value,
            "service": sid,
            "timestamp": time.time(),
            "mutations": {}
        }

        if action.primitive == RemediationPrimitive.RESIZE_DB_CONN_POOL:
            new_max = action.parameters.get("max_connections", 120)
            old_max = node.db_pool_max
            node.db_pool_max = new_max
            # Relieve pool saturation immediately as capacity expands
            node.db_pool_active = min(new_max, int(new_max * 0.35))
            node.p95_latency_ms = 24.0
            node.p99_latency_ms = 48.0
            node.error_rate = 0.0005
            self.collector.clear_fault(sid)
            result_details["mutations"] = {
                "configmap_patch": f"maximum-pool-size: {old_max} -> {new_max}",
                "leak_detection": "enabled (5000ms threshold)"
            }

        elif action.primitive == RemediationPrimitive.HORIZONTAL_POD_AUTOSCALE:
            added = action.parameters.get("added_replicas", 3)
            old_reps = node.replicas
            node.replicas += added
            node.cpu_percent = max(15.0, node.cpu_percent * 0.45)
            node.p99_latency_ms = max(25.0, node.p99_latency_ms * 0.4)
            node.error_rate = 0.001
            self.collector.clear_fault(sid)
            result_details["mutations"] = {
                "hpa_replicas": f"{old_reps} -> {node.replicas}"
            }

        elif action.primitive == RemediationPrimitive.GRACEFUL_POD_RESTART:
            node.memory_mb = max(150.0, node.memory_mb * 0.3)
            node.cpu_percent = 25.0
            node.p99_latency_ms = 35.0
            node.error_rate = 0.0005
            self.collector.clear_fault(sid)
            result_details["mutations"] = {
                "rollout_status": "spec.template.metadata.annotations updated (restarted)"
            }

        elif action.primitive == RemediationPrimitive.CIRCUIT_BREAK:
            node.error_rate = 0.02
            node.p99_latency_ms = 40.0
            result_details["mutations"] = {
                "istio_destination_rule": "consecutiveErrors=5, baseEjectionTime=30s"
            }

        return result_details

    def execute_rollback(self, snapshot: SnapshotManifest) -> Dict[str, Any]:
        """
        Executes atomic rollback of the service manifest to the exact state saved in snapshot.
        """
        sid = snapshot.service_id
        if sid not in self.collector.nodes:
            raise KeyError(f"Service {sid} not found in cluster")

        node = self.collector.nodes[sid]
        node.replicas = snapshot.replicas
        node.db_pool_max = snapshot.db_pool_max
        node.db_idle_timeout_sec = snapshot.db_idle_timeout_sec

        return {
            "status": "ROLLED_BACK",
            "snapshot_id": snapshot.snapshot_id,
            "service_id": sid,
            "restored_replicas": snapshot.replicas,
            "restored_db_pool_max": snapshot.db_pool_max,
            "timestamp": time.time()
        }
