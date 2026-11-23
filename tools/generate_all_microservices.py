"""
Automated 100-Microservice Code Generator
Generates full production codebases for all 100 microservices defined in the dependency graph.
Each microservice includes FastAPI runtime, OTel tracing, Prometheus metrics,
domain API endpoints, downstream call chains, Dockerfile, and Kubernetes manifests.
"""

import os
import sys
import re

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from self_healing_core.observability.topology_generator import generate_100_service_topology


def sanitize_dir_name(sid: str, name: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9]+", "_", name.lower()).strip("_")
    clean_sid = sid.replace("-", "_")
    return f"{clean_sid}_{clean}"


def generate_service_code(sid: str, node, downstream_targets: list) -> str:
    is_db = node.tier.value == "DATABASE"
    is_order_db = sid == "svc-066"

    # Domain specific routes
    domain_route = "/api/v1/process"
    domain_method_name = "process_request"
    if "checkout" in node.name.lower():
        domain_route = "/api/v1/checkout"
        domain_method_name = "execute_checkout"
    elif "order" in node.name.lower() and "db" in node.name.lower():
        domain_route = "/api/v1/orders/record"
        domain_method_name = "persist_order_record"
    elif "cart" in node.name.lower():
        domain_route = "/api/v1/cart"
        domain_method_name = "manage_cart"
    elif "payment" in node.name.lower():
        domain_route = "/api/v1/payments/settle"
        domain_method_name = "settle_payment"
    elif "catalog" in node.name.lower():
        domain_route = "/api/v1/products"
        domain_method_name = "query_catalog"
    elif "auth" in node.name.lower():
        domain_route = "/api/v1/auth/verify"
        domain_method_name = "verify_token"

    return f'''"""
Microservice: {node.name} ({sid})
Tier: {node.tier.value} | Host Node: {node.host_node}
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
{"from microservices.common.pool import HikariConnectionPool, HikariPoolExhaustedException" if is_db else ""}

SERVICE_ID = "{sid}"
SERVICE_NAME = "{node.name}"
TIER = "{node.tier.value}"
HOST_NODE = "{node.host_node}"
DEFAULT_PORT = {8000 + int(sid.split("-")[1])}
DOWNSTREAM_SERVICES = {repr(downstream_targets)}

app = FastAPI(
    title=f"{{SERVICE_NAME}} Microservice",
    description=f"Cloud-Native Microservice for {{SERVICE_NAME}} ({{SERVICE_ID}})",
    version="1.0.0"
)

metrics = ServiceMetrics(SERVICE_ID, SERVICE_NAME)
metrics.cpu_percent = {node.cpu_percent}
metrics.memory_mb = {node.memory_mb}
circuit_breaker = CircuitBreaker(failure_rate_threshold_pct=50.0)

{"# HikariCP Connection Pool initialization (Pillar 1/7)" if is_db else ""}
{"db_pool = HikariConnectionPool(maximum_pool_size=" + str(node.db_pool_max) + ", idle_timeout_ms=30000)" if is_db else ""}

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
    if active_fault == "MEMORY_LEAK" and metrics.memory_mb > {node.memory_limit_mb}:
        raise HTTPException(status_code=503, detail="OOMKilled risk: Heap limit exceeded")
    return {{"status": "UP", "service": SERVICE_ID, "name": SERVICE_NAME}}


@app.get("/ready")
def readiness_probe():
    """Kubernetes readiness probe."""
    if not circuit_breaker.is_call_permitted():
        raise HTTPException(status_code=503, detail="Circuit Breaker OPEN: Service not ready")
    {"if db_pool.active_connections >= db_pool.maximum_pool_size:" if is_db else ""}
    {"    raise HTTPException(status_code=503, detail='HikariPool saturated') if active_fault == 'DB_POOL_EXHAUSTION' else None" if is_db else ""}
    return {{"status": "READY", "service": SERVICE_ID}}


@app.get("/metrics")
def prometheus_metrics():
    """Prometheus exposition format scraper endpoint."""
    pool_stats = {"db_pool.get_stats()" if is_db else "None"}
    raw_prom = metrics.to_prometheus_format(pool_stats)
    return Response(content=raw_prom, media_type="text/plain; version=0.0.4")


@app.post("{domain_route}")
async def {domain_method_name}(payload: Optional[Dict[str, Any]] = None, request: Request = None):
    """Core domain business endpoint for {node.name}."""
    trace_ctx = getattr(request.state, "trace_ctx", None)
    lease_id = f"lease-{{time.time()}}"

    {"# Database Connection Pool Lease Acquisition" if is_db else ""}
    {"try:" if is_db else ""}
    {"    await db_pool.acquire_connection(lease_id)" if is_db else ""}
    {"except HikariPoolExhaustedException as err:" if is_db else ""}
    {"    raise HTTPException(status_code=503, detail=str(err))" if is_db else ""}

    try:
        # Simulate business computation
        await asyncio.sleep(0.015)
        
        downstream_responses = {{}}
        # Propagate W3C trace downstream to dependencies
        # (In live integration, calls downstream HTTP endpoints)
        for ds in DOWNSTREAM_SERVICES:
            downstream_responses[ds] = "RPC_OK"

        return {{
            "status": "SUCCESS",
            "service": SERVICE_ID,
            "tier": TIER,
            "trace_id": trace_ctx.trace_id if trace_ctx else None,
            "downstream_calls": downstream_responses,
            {"'pool_status': db_pool.get_stats()," if is_db else ""}
            "timestamp": time.time()
        }}
    finally:
        {"await db_pool.release_connection(lease_id)" if is_db else "pass"}


@app.post("/chaos/fault/inject")
def inject_fault(req: ChaosFaultRequest):
    """Chaos engineering injection endpoint (ChaosMesh / stress-ng bridge)."""
    global active_fault
    active_fault = req.fault_type

    if req.fault_type == "DB_POOL_EXHAUSTION":
        {"db_pool.trigger_leak_simulation()" if is_db else "pass"}
    elif req.fault_type == "MEMORY_LEAK":
        metrics.memory_mb = {node.memory_limit_mb * 0.95}
        metrics.cpu_percent = 92.0
    elif req.fault_type == "CPU_HOGGING":
        metrics.cpu_percent = 99.0
    elif req.fault_type == "RETRY_STORM":
        metrics.cpu_percent = 95.0

    return {{"status": "FAULT_ACTIVE", "fault": active_fault, "service": SERVICE_ID}}


@app.post("/chaos/fault/clear")
def clear_fault():
    """Resets fault state to normal."""
    global active_fault
    active_fault = None
    {"db_pool.clear_leak_simulation()" if is_db else "pass"}
    metrics.cpu_percent = {node.cpu_percent}
    metrics.memory_mb = {node.memory_mb}
    return {{"status": "HEALTHY", "service": SERVICE_ID}}


@app.post("/config/reload")
def reload_config(req: ConfigReloadRequest):
    """Kubernetes ConfigMap hot-reload endpoint (Pillar 7)."""
    if req.maximum_pool_size:
        {"db_pool.resize_pool(req.maximum_pool_size, req.leak_detection_threshold_ms or 5000)" if is_db else "pass"}
    return {{"status": "CONFIG_RELOADED", "service": SERVICE_ID, {"'pool': db_pool.get_stats()" if is_db else "'details': 'Updated'"}}}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=DEFAULT_PORT)
'''


def generate_dockerfile(node) -> str:
    return f"""# Production Dockerfile for {node.name} ({node.id})
FROM python:3.11-slim-bullseye

WORKDIR /app

# Install security updates
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as unprivileged container user
USER 10001
EXPOSE {8000 + int(node.id.split("-")[1])}

HEALTHCHECK --interval=10s --timeout=3s --retries=3 \\
    CMD curl -f http://localhost:{8000 + int(node.id.split("-")[1])}/healthz || exit 1

ENTRYPOINT ["python", "app.py"]
"""


def generate_k8s_manifest(node, downstream) -> str:
    port = 8000 + int(node.id.split("-")[1])
    is_db = node.tier.value == "DATABASE"
    clean_name = node.name.lower().replace("_", "-")

    return f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {clean_name}
  namespace: self-healing-ecosystem
  labels:
    app.kubernetes.io/name: {clean_name}
    app.kubernetes.io/part-of: self-healing-software-ecosystem
    tier: {node.tier.value.lower()}
    service-id: {node.id}
spec:
  replicas: {node.replicas}
  selector:
    matchLabels:
      app: {clean_name}
  template:
    metadata:
      labels:
        app: {clean_name}
        tier: {node.tier.value.lower()}
        service-id: {node.id}
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "{port}"
        prometheus.io/path: "/metrics"
    spec:
      nodeSelector:
        kubernetes.io/hostname: {node.host_node}
      containers:
      - name: {clean_name}
        image: selfhealing/{clean_name}:v1.0.0
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: {port}
          name: http
        resources:
          requests:
            cpu: "{int(node.cpu_percent * 10)}m"
            memory: "{int(node.memory_mb)}Mi"
          limits:
            cpu: "1000m"
            memory: "{int(node.memory_limit_mb)}Mi"
        env:
        - name: SERVICE_ID
          value: "{node.id}"
        - name: SERVICE_NAME
          value: "{node.name}"
        - name: PORT
          value: "{port}"
        {"- name: HIKARI_MAX_POOL_SIZE\\n          value: '" + str(node.db_pool_max) + "'" if is_db else ""}
        {"- name: HIKARI_IDLE_TIMEOUT_SEC\\n          value: '" + str(node.db_idle_timeout_sec) + "'" if is_db else ""}
        livenessProbe:
          httpGet:
            path: /healthz
            port: {port}
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: {port}
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: {clean_name}
  namespace: self-healing-ecosystem
  labels:
    app: {clean_name}
spec:
  type: ClusterIP
  ports:
  - port: {port}
    targetPort: {port}
    protocol: TCP
    name: http
  selector:
    app: {clean_name}
"""


def main():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "microservices"))
    os.makedirs(base_dir, exist_ok=True)

    nodes, edges = generate_100_service_topology()

    # Build downstream map
    downstream_map = {sid: [] for sid in nodes}
    for e in edges:
        downstream_map[e.source].append(e.target)

    requirements_content = """fastapi>=0.110.0
uvicorn>=0.28.0
pydantic>=2.6.0
requests>=2.31.0
httpx>=0.27.0
"""

    print(f"[*] Generating all {len(nodes)} microservice codebases in {base_dir}...")

    generated_count = 0
    for sid, node in nodes.items():
        dir_name = sanitize_dir_name(sid, node.name)
        svc_dir = os.path.join(base_dir, dir_name)
        os.makedirs(svc_dir, exist_ok=True)

        # 1. app.py
        app_code = generate_service_code(sid, node, downstream_map.get(sid, []))
        with open(os.path.join(svc_dir, "app.py"), "w", encoding="utf-8") as f:
            f.write(app_code)

        # 2. requirements.txt
        with open(os.path.join(svc_dir, "requirements.txt"), "w", encoding="utf-8") as f:
            f.write(requirements_content)

        # 3. Dockerfile
        docker_code = generate_dockerfile(node)
        with open(os.path.join(svc_dir, "Dockerfile"), "w", encoding="utf-8") as f:
            f.write(docker_code)

        # 4. k8s-deployment.yaml
        k8s_code = generate_k8s_manifest(node, downstream_map.get(sid, []))
        with open(os.path.join(svc_dir, "k8s-deployment.yaml"), "w", encoding="utf-8") as f:
            f.write(k8s_code)

        generated_count += 1

    print(f"[+] Successfully generated all {generated_count} microservice codebases!")


if __name__ == "__main__":
    main()
