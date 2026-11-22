"""
FastAPI Live Control Plane Server (WebSockets + REST API)
Exposes the 6-stage self-healing pipeline, 100-microservice cluster topology,
real-time telemetry streams, and chaos engineering triggers.
"""

import asyncio
import json
import os
import time
from typing import Dict, Any, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from self_healing_core.orchestrator import SelfHealingOrchestrator
from self_healing_core.chaos.fault_injector import ChaosFaultInjector
from self_healing_core.models import FaultType

app = FastAPI(
    title="Self-Healing Software Ecosystem Control Plane",
    description="Autonomous AI System that Detects, Diagnoses, and Repairs Distributed Microservice Failures",
    version="1.0.0"
)

# Initialize Core Control Plane
orchestrator = SelfHealingOrchestrator()
fault_injector = ChaosFaultInjector(orchestrator.collector)

# WebSocket connection manager
active_websockets: List[WebSocket] = []


class ChaosRequest(BaseModel):
    scenario: str
    target_service: str = "svc-066"


class StepRequest(BaseModel):
    stage: int = 1


@app.on_event("startup")
async def startup_event():
    # Calibrate baseline normal features
    orchestrator.tick_observability()
    # Launch background telemetry generator loop
    asyncio.create_task(background_telemetry_loop())


async def background_telemetry_loop():
    """Continuously runs telemetry tick and broadcasts live frame over WebSockets."""
    while True:
        try:
            frame = orchestrator.tick_observability()
            msg = {
                "type": "TELEMETRY_UPDATE",
                "timestamp": frame.timestamp,
                "system_p99_ms": frame.system_p99_ms,
                "system_error_rate": frame.system_error_rate,
                "system_total_rps": frame.system_total_rps,
                "active_faults": {sid: f.value for sid, f in orchestrator.collector.active_faults.items()},
                "current_stage": orchestrator.current_stage,
                "status_message": orchestrator.stage_status_message,
                "logs": [
                    {"time": l.timestamp, "service": l.service_id, "level": l.level, "msg": l.message}
                    for l in frame.logs[-10:]
                ]
            }

            # Broadcast to connected clients
            dead_sockets = []
            for ws in active_websockets:
                try:
                    await ws.send_json(msg)
                except Exception:
                    dead_sockets.append(ws)
            for ws in dead_sockets:
                if ws in active_websockets:
                    active_websockets.remove(ws)

        except Exception as e:
            print(f"Error in telemetry broadcast loop: {e}")

        await asyncio.sleep(2.0)


@app.get("/api/cluster/topology")
def get_topology():
    """Returns the full 100-microservice topology and current node/edge status."""
    if not orchestrator.latest_frame:
        orchestrator.tick_observability()

    nodes_data = [node.to_dict() for node in orchestrator.collector.nodes.values()]
    edges_data = [edge.to_dict() for edge in orchestrator.collector.edges]

    return {
        "nodes": nodes_data,
        "edges": edges_data,
        "total_nodes": len(nodes_data),
        "total_edges": len(edges_data),
        "active_faults": {sid: f.value for sid, f in orchestrator.collector.active_faults.items()}
    }


@app.get("/api/cluster/metrics")
def get_metrics():
    """Returns real-time cluster Golden Signals."""
    if not orchestrator.latest_frame:
        orchestrator.tick_observability()

    frame = orchestrator.latest_frame
    return {
        "timestamp": frame.timestamp,
        "p99_latency_ms": frame.system_p99_ms,
        "error_rate": frame.system_error_rate,
        "total_rps": frame.system_total_rps,
        "active_faults_count": len(orchestrator.collector.active_faults),
        "current_stage": orchestrator.current_stage,
        "stage_status": orchestrator.stage_status_message
    }


@app.post("/api/chaos/inject")
def inject_chaos(req: ChaosRequest):
    """Triggers realistic Chaos Mesh fault injections."""
    sc = req.scenario.lower()
    tgt = req.target_service

    if "pool" in sc or "db" in sc:
        res = fault_injector.inject_db_pool_exhaustion(tgt)
    elif "mem" in sc or "leak" in sc:
        res = fault_injector.inject_memory_leak(tgt)
    elif "cpu" in sc or "hog" in sc:
        res = fault_injector.inject_cpu_hog(tgt)
    elif "retry" in sc or "storm" in sc:
        res = fault_injector.inject_retry_storm(tgt)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown chaos scenario: {req.scenario}")

    orchestrator.tick_observability()
    return {"status": "FAULT_INJECTED", "details": res}


@app.post("/api/chaos/clear")
def clear_chaos():
    """Resets the entire cluster to healthy baseline."""
    fault_injector.clear_all()
    orchestrator.tick_observability()
    orchestrator.current_stage = 1
    orchestrator.stage_status_message = "Cluster restored to healthy baseline."
    orchestrator.latest_anomaly = None
    return {"status": "CLEARED", "active_faults": len(orchestrator.collector.active_faults)}


@app.post("/api/self-heal/step")
def step_self_healing(req: StepRequest):
    """Steps through the 6-stage autonomous pipeline one stage at a time."""
    stage = req.stage
    if stage == 1:
        anom = orchestrator.run_stage_1_anomaly_detection()
        return {
            "stage": 1,
            "title": "Multimodal Anomaly Detection",
            "anomaly_detected": anom is not None,
            "primary_service": anom.primary_anomalous_service if anom else None,
            "max_z_score": anom.max_z_score if anom else 0.0,
            "affected_count": len(anom.affected_services) if anom else 0,
            "message": orchestrator.stage_status_message
        }
    elif stage == 2:
        nodes, edges = orchestrator.run_stage_2_blast_radius()
        return {
            "stage": 2,
            "title": "Blast Radius Subgraph Extraction",
            "subgraph_nodes": nodes,
            "subgraph_edge_count": len(edges),
            "message": orchestrator.stage_status_message
        }
    elif stage == 3:
        rca = orchestrator.run_stage_3_gnn_causal_diagnosis()
        return {
            "stage": 3,
            "title": "GATv2 & Causal SCM Root Cause Isolation",
            "culprit_service": rca.culprit_service,
            "fault_type": rca.fault_type.value,
            "causal_confidence": rca.causal_confidence,
            "ranked_candidates": [
                {
                    "service": c.service_id,
                    "confidence": c.confidence_score,
                    "prior": c.prior_score,
                    "evidence": c.telemetry_evidence,
                    "gnn_residual": c.gnn_residual,
                    "do_effect": c.causal_effect_do_x,
                    "explanation": c.explanation
                }
                for c in rca.candidates_ranked
            ],
            "message": orchestrator.stage_status_message
        }
    elif stage == 4:
        candidates = orchestrator.run_stage_4_digital_twin_simulation()
        return {
            "stage": 4,
            "title": "Digital Twin Queuing Simulation",
            "simulated_actions": [
                {
                    "primitive": a.primitive.value,
                    "projected_latency_drop": a.projected_latency_drop_pct,
                    "blast_cost": a.projected_blast_cost,
                    "rationale": a.rationale
                }
                for a in candidates
            ],
            "message": orchestrator.stage_status_message
        }
    elif stage == 5:
        action, snapshot, patch = orchestrator.run_stage_5_safe_rl_execution()
        return {
            "stage": 5,
            "title": "Safe-PPO Selection & Kubernetes Mutation",
            "selected_action": action.primitive.value,
            "blast_cost": action.projected_blast_cost,
            "target_service": action.target_service,
            "snapshot_id": snapshot.snapshot_id,
            "patch_details": patch,
            "message": orchestrator.stage_status_message
        }
    elif stage == 6:
        verification = orchestrator.run_stage_6_canary_verification()
        return {
            "stage": 6,
            "title": "Canary Verification & State Rollback Guard",
            "verdict": verification.verdict.value,
            "slo_restored": verification.slo_restored,
            "pre_p99_ms": verification.pre_intervention_p99_ms,
            "post_p99_ms": verification.post_intervention_p99_ms,
            "rollback_executed": verification.rollback_executed,
            "summary": verification.summary,
            "message": orchestrator.stage_status_message
        }
    else:
        raise HTTPException(status_code=400, detail="Stage must be between 1 and 6")


@app.post("/api/self-heal/auto")
def auto_self_healing():
    """Runs the full 6-stage autonomous self-healing loop synchronously."""
    res = orchestrator.execute_full_autonomous_cycle()
    return res


@app.get("/api/audit/incidents")
def get_incidents():
    """Returns complete historical incident post-mortem ledger."""
    records = []
    for inc in orchestrator.incident_history:
        records.append({
            "incident_id": inc.incident_id,
            "start_time": inc.start_time,
            "resolved_time": inc.resolved_time,
            "culprit_service": inc.culprit_service,
            "fault_injected": inc.fault_injected.value,
            "root_cause_identified": inc.root_cause_identified,
            "rca_accuracy": inc.rca_accuracy,
            "remediation_action": inc.remediation_action.primitive.value,
            "verdict": inc.verification.verdict.value,
            "pre_p99_ms": inc.verification.pre_intervention_p99_ms,
            "post_p99_ms": inc.verification.post_intervention_p99_ms,
            "mttd_sec": inc.mttd_seconds,
            "mttr_sec": inc.mttr_seconds,
            "snapshot_id": inc.etcd_snapshot.snapshot_id,
            "summary": inc.post_mortem_notes
        })
    return {"incidents": records, "count": len(records)}


@app.websocket("/ws/live-stream")
async def websocket_endpoint(websocket: WebSocket):
    """Real-time live streaming connection for frontend dashboard."""
    await websocket.accept()
    active_websockets.append(websocket)
    try:
        while True:
            # Keep-alive receive
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in active_websockets:
            active_websockets.remove(websocket)


# Mount static frontend assets
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def serve_index():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Self-Healing Software Ecosystem API is running. Visit /docs for OpenAPI documentation."}
