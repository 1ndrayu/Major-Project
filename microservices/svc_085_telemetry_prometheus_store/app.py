"""
Microservice: Telemetry-Prometheus-Store (svc-085)
Tier: DATABASE | Host Node: k8s-worker-05
Generated for Self-Healing Software Ecosystem (Academic Year 2026-27)
"""

import os
import time
import asyncio
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, Header, HTTPException, Request, Response
from pydantic import BaseModel

# Shared telemetry and infrastructure
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from microservices.common.tracing import extract_w3c_trace, inject_w3c_trace, TraceContext
from microservices.common.metrics import ServiceMetrics
from microservices.common.circuit_breaker import CircuitBreaker
from microservices.common.pool import HikariConnectionPool, HikariPoolExhaustedException

SERVICE_ID = "svc-085"
SERVICE_NAME = "Telemetry-Prometheus-Store"
TIER = "DATABASE"
HOST_NODE = "k8s-worker-05"
DEFAULT_PORT = 8085
DOWNSTREAM_SERVICES = []

app = FastAPI(
    title=f"{SERVICE_NAME} Microservice",
    description=f"Cloud-Native Microservice for {SERVICE_NAME} ({SERVICE_ID})",
    version="1.0.0"
)

metrics = ServiceMetrics(SERVICE_ID, SERVICE_NAME)
metrics.cpu_percent = 37.0
metrics.memory_mb = 710.0
circuit_breaker = CircuitBreaker(failure_rate_threshold_pct=50.0)

# HikariCP Connection Pool initialization (Pillar 1/7)
db_pool = HikariConnectionPool(maximum_pool_size=35, idle_timeout_ms=30000)

# Active chaos state
active_fault: Optional[str] = None


class ChaosFaultRequest(BaseModel):
    fault_type: str  # DB_POOL_EXHAUSTION, MEMORY_LEAK, CPU_HOGGING, RETRY_STORM
    duration_sec: int = 60


class ConfigReloadRequest(BaseModel):
    maximum_pool_size: Optional[int] = None
    leak_detection_threshold_ms: Optional[int] = None
    replicas: Optional[int] = None


@app.middleware("http")
async def telemetry_middleware(request: Request, call_next):
    start_time = time.time()
    trace_ctx = extract_w3c_trace(dict(request.headers))
    request.state.trace_ctx = trace_ctx

    try:
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000.0
        metrics.record_request(duration_ms, success=(response.status_code < 500))
        response.headers["traceparent"] = trace_ctx.to_header()
        return response
    except Exception as exc:
        duration_ms = (time.time() - start_time) * 1000.0
        metrics.record_request(duration_ms, success=False)
        raise exc


@app.get("/healthz")
def liveness_probe():
    """Kubernetes liveness probe."""
    if active_fault == "MEMORY_LEAK" and metrics.memory_mb > 1775.0:
        raise HTTPException(status_code=503, detail="OOMKilled risk: Heap limit exceeded")
    return {"status": "UP", "service": SERVICE_ID, "name": SERVICE_NAME}


@app.get("/ready")
def readiness_probe():
    """Kubernetes readiness probe."""
    if not circuit_breaker.is_call_permitted():
        raise HTTPException(status_code=503, detail="Circuit Breaker OPEN: Service not ready")
    if db_pool.active_connections >= db_pool.maximum_pool_size:
        raise HTTPException(status_code=503, detail='HikariPool saturated') if active_fault == 'DB_POOL_EXHAUSTION' else None
    return {"status": "READY", "service": SERVICE_ID}


@app.get("/metrics")
def prometheus_metrics():
    """Prometheus exposition format scraper endpoint."""
    pool_stats = db_pool.get_stats()
    raw_prom = metrics.to_prometheus_format(pool_stats)
    return Response(content=raw_prom, media_type="text/plain; version=0.0.4")


@app.post("/api/v1/process")
async def process_request(payload: Optional[Dict[str, Any]] = None, request: Request = None):
    """Core domain business endpoint for Telemetry-Prometheus-Store."""
    trace_ctx = getattr(request.state, "trace_ctx", None)
    lease_id = f"lease-{time.time()}"

    # Database Connection Pool Lease Acquisition
    try:
        await db_pool.acquire_connection(lease_id)
    except HikariPoolExhaustedException as err:
        raise HTTPException(status_code=503, detail=str(err))

    try:
        # Simulate business computation
        await asyncio.sleep(0.015)
        
        downstream_responses = {}
        # Propagate W3C trace downstream to dependencies
        # (In live integration, calls downstream HTTP endpoints)
        for ds in DOWNSTREAM_SERVICES:
            downstream_responses[ds] = "RPC_OK"

        return {
            "status": "SUCCESS",
            "service": SERVICE_ID,
            "tier": TIER,
            "trace_id": trace_ctx.trace_id if trace_ctx else None,
            "downstream_calls": downstream_responses,
            'pool_status': db_pool.get_stats(),
            "timestamp": time.time()
        }
    finally:
        await db_pool.release_connection(lease_id)


@app.post("/chaos/fault/inject")
def inject_fault(req: ChaosFaultRequest):
    """Chaos engineering injection endpoint (ChaosMesh / stress-ng bridge)."""
    global active_fault
    active_fault = req.fault_type

    if req.fault_type == "DB_POOL_EXHAUSTION":
        db_pool.trigger_leak_simulation()
    elif req.fault_type == "MEMORY_LEAK":
        metrics.memory_mb = 1686.25
        metrics.cpu_percent = 92.0
    elif req.fault_type == "CPU_HOGGING":
        metrics.cpu_percent = 99.0
    elif req.fault_type == "RETRY_STORM":
        metrics.cpu_percent = 95.0

    return {"status": "FAULT_ACTIVE", "fault": active_fault, "service": SERVICE_ID}


@app.post("/chaos/fault/clear")
def clear_fault():
    """Resets fault state to normal."""
    global active_fault
    active_fault = None
    db_pool.clear_leak_simulation()
    metrics.cpu_percent = 37.0
    metrics.memory_mb = 710.0
    return {"status": "HEALTHY", "service": SERVICE_ID}


@app.post("/config/reload")
def reload_config(req: ConfigReloadRequest):
    """Kubernetes ConfigMap hot-reload endpoint (Pillar 7)."""
    if req.maximum_pool_size:
        db_pool.resize_pool(req.maximum_pool_size, req.leak_detection_threshold_ms or 5000)
    return {"status": "CONFIG_RELOADED", "service": SERVICE_ID, 'pool': db_pool.get_stats()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=DEFAULT_PORT)
