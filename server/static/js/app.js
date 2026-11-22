/**
 * Self-Healing Software Ecosystem - Frontend Application
 * Handles Real-Time WebSockets, Vis.js 100-Service Dynamic Graph,
 * Chart.js Golden Signals, Chaos Injection, and Stepped Pipeline Execution.
 */

let network = null;
let networkData = { nodes: null, edges: null };
let nodeLookup = {};
let currentSelectedNodeId = "svc-066";
let currentStage = 1;

// Chart instances
let chartP99 = null;
let chartError = null;
let chartPool = null;
let chartRps = null;

// Telemetry history for charts (max 20 data points)
const historyP99 = [];
const historyError = [];
const historyPool = [];
const historyRps = [];
const timeLabels = [];

document.addEventListener("DOMContentLoaded", () => {
    initCharts();
    initWebSocket();
    loadTopology();
    refreshLedger();
});

// -------------------------------------------------------------
// 1. Chart.js Golden Signal Telemetry Initialization
// -------------------------------------------------------------
function initCharts() {
    const commonOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { enabled: true } },
        scales: {
            x: { display: false },
            y: {
                display: true,
                grid: { color: 'rgba(255, 255, 255, 0.05)' },
                ticks: { color: '#64748b', font: { size: 9 } }
            }
        },
        elements: {
            point: { radius: 0 },
            line: { tension: 0.35, borderWidth: 2 }
        }
    };

    const ctxP99 = document.getElementById("chart-p99").getContext("2d");
    chartP99 = new Chart(ctxP99, {
        type: "line",
        data: { labels: timeLabels, datasets: [{ data: historyP99, borderColor: "#06b6d4", backgroundColor: "rgba(6, 182, 212, 0.1)", fill: true }] },
        options: commonOptions
    });

    const ctxError = document.getElementById("chart-error").getContext("2d");
    chartError = new Chart(ctxError, {
        type: "line",
        data: { labels: timeLabels, datasets: [{ data: historyError, borderColor: "#ef4444", backgroundColor: "rgba(239, 68, 68, 0.1)", fill: true }] },
        options: commonOptions
    });

    const ctxPool = document.getElementById("chart-pool").getContext("2d");
    chartPool = new Chart(ctxPool, {
        type: "line",
        data: { labels: timeLabels, datasets: [{ data: historyPool, borderColor: "#f59e0b", backgroundColor: "rgba(245, 158, 11, 0.1)", fill: true }] },
        options: commonOptions
    });

    const ctxRps = document.getElementById("chart-rps").getContext("2d");
    chartRps = new Chart(ctxRps, {
        type: "line",
        data: { labels: timeLabels, datasets: [{ data: historyRps, borderColor: "#8b5cf6", backgroundColor: "rgba(139, 92, 246, 0.1)", fill: true }] },
        options: commonOptions
    });
}

function updateChartData(p99, errorRate, poolSat, rps) {
    const nowLabel = new Date().toLocaleTimeString();
    timeLabels.push(nowLabel);
    historyP99.push(p99);
    historyError.push(errorRate * 100);
    historyPool.push(poolSat * 100);
    historyRps.push(rps);

    if (timeLabels.length > 25) {
        timeLabels.shift();
        historyP99.shift();
        historyError.shift();
        historyPool.shift();
        historyRps.shift();
    }

    chartP99.update();
    chartError.update();
    chartPool.update();
    chartRps.update();

    // Update numbers
    document.getElementById("metric-p99").innerHTML = `${p99.toFixed(1)} <span class="unit">ms</span>`;
    document.getElementById("metric-error").innerHTML = `${(errorRate * 100).toFixed(2)} <span class="unit">%</span>`;
    document.getElementById("metric-pool").innerHTML = `${(poolSat * 100).toFixed(1)} <span class="unit">%</span>`;
    document.getElementById("metric-rps").innerHTML = `${rps.toLocaleString()} <span class="unit">RPS</span>`;
}

// -------------------------------------------------------------
// 2. Vis.js Dynamic 100-Microservice Topology Graph
// -------------------------------------------------------------
async function loadTopology() {
    try {
        const resp = await fetch("/api/cluster/topology");
        const data = await resp.json();

        const visNodes = [];
        const visEdges = [];

        data.nodes.forEach((n) => {
            nodeLookup[n.id] = n;
            let color = "#06b6d4";
            if (n.status === "CRITICAL") color = "#ef4444";
            else if (n.status === "DEGRADED") color = "#f59e0b";
            else if (n.status === "SELF_HEALING") color = "#a855f7";

            visNodes.push({
                id: n.id,
                label: n.name.length > 18 ? n.name.substring(0, 16) + '..' : n.name,
                title: `${n.name} (${n.id})\nTier: ${n.tier}\nHost: ${n.host_node}\np99: ${n.p99_latency_ms}ms`,
                color: {
                    background: color,
                    border: "#1e293b",
                    highlight: { background: "#ffffff", border: color }
                },
                font: { color: "#ffffff", size: 10, face: "Plus Jakarta Sans" },
                shape: n.tier === "DATABASE" ? "database" : (n.tier === "GATEWAY" ? "diamond" : "dot"),
                size: n.id === "svc-066" ? 22 : 14
            });
        });

        data.edges.forEach((e, idx) => {
            visEdges.push({
                id: `e-${idx}`,
                from: e.source,
                to: e.target,
                arrows: "to",
                color: { color: e.p99_latency_ms > 500 ? "#ef4444" : "#334155", opacity: 0.6 },
                width: e.p99_latency_ms > 500 ? 2 : 1
            });
        });

        const container = document.getElementById("network-topology-container");
        container.innerHTML = "";

        networkData.nodes = new vis.DataSet(visNodes);
        networkData.edges = new vis.DataSet(visEdges);

        const options = {
            nodes: {
                borderWidth: 1.5,
                shadow: { enabled: true, color: "rgba(0,0,0,0.5)", size: 5 }
            },
            edges: {
                smooth: { type: "continuous" }
            },
            physics: {
                stabilization: { iterations: 120 },
                barnesHut: { gravitationalConstant: -3500, centralGravity: 0.3, springLength: 75 }
            },
            interaction: { hover: true, tooltipDelay: 200 }
        };

        network = new vis.Network(container, networkData, options);

        network.on("click", (params) => {
            if (params.nodes.length > 0) {
                const clickedId = params.nodes[0];
                selectService(clickedId);
            }
        });

        // Select Order-DB-Adapter by default
        selectService("svc-066");

    } catch (e) {
        console.error("Failed to load topology:", e);
    }
}

function selectService(serviceId) {
    currentSelectedNodeId = serviceId;
    const n = nodeLookup[serviceId];
    if (!n) return;

    document.getElementById("inspector-service-name").textContent = `Service Inspector: ${n.name} (${n.id})`;
    document.getElementById("inspector-service-status").textContent = n.status;
    document.getElementById("inspector-service-status").className = `badge ${n.status.toLowerCase()}`;

    document.getElementById("ins-p99").textContent = `${n.p99_latency_ms.toFixed(1)} ms`;
    document.getElementById("ins-err").textContent = `${(n.error_rate * 100).toFixed(2)}%`;
    const poolSat = (n.db_pool_active / Math.max(1, n.db_pool_max) * 100).toFixed(0);
    document.getElementById("ins-pool").textContent = `${n.db_pool_active} / ${n.db_pool_max} (${poolSat}%)`;
    document.getElementById("ins-reps").textContent = `${n.replicas} Pods (${n.host_node})`;

    const preview = document.getElementById("ins-log-preview");
    if (n.active_fault === "DB_POOL_EXHAUSTION") {
        preview.textContent = `[ERROR] HikariPool-1 - Connection is not available, request timed out after 30005ms (active=${n.db_pool_active}/${n.db_pool_max})
[ERROR] org.springframework.dao.CannotAcquireLockException: Connection pool exhausted
[WARN] Cascading thread pool exhaustion: 82 worker threads waiting on DB connection lease`;
    } else if (n.active_fault === "MEMORY_LEAK") {
        preview.textContent = `[CRITICAL] java.lang.OutOfMemoryError: Java heap space
[WARN] Full GC pause took 2840ms. Stop-the-world event triggered.`;
    } else {
        preview.textContent = `[INFO] ${n.name} healthy. Receiving ${n.request_rate_rps.toFixed(0)} req/s.
[INFO] W3C trace context propagated over gRPC. p99 response time: ${n.p99_latency_ms.toFixed(1)}ms`;
    }
}

function resetGraphView() {
    if (network) network.fit({ animation: { duration: 600, easingFunction: "easeInOutQuad" } });
}

// -------------------------------------------------------------
// 3. WebSocket Real-Time Telemetry Stream
// -------------------------------------------------------------
function initWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/live-stream`;
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.type === "TELEMETRY_UPDATE") {
                // Update stage indicator
                setPipelineStage(data.current_stage, data.status_message);

                // Update charts
                const orderDbPoolSat = nodeLookup["svc-066"] ? (nodeLookup["svc-066"].db_pool_active / Math.max(1, nodeLookup["svc-066"].db_pool_max)) : 0.3;
                updateChartData(data.system_p99_ms, data.system_error_rate, orderDbPoolSat, data.system_total_rps);

                // Update status badge
                const faultCount = Object.keys(data.active_faults).length;
                document.getElementById("active-fault-pill").textContent = `${faultCount} Active Fault${faultCount === 1 ? '' : 's'}`;

                const badge = document.getElementById("system-status-badge");
                const badgeText = document.getElementById("system-status-text");
                const dot = badge.querySelector(".status-dot");

                if (faultCount === 0) {
                    badgeText.textContent = "CLUSTER OPERATIONAL";
                    dot.className = "status-dot healthy";
                } else {
                    badgeText.textContent = `INCIDENT DETECTED (${faultCount})`;
                    dot.className = "status-dot critical";
                }

                // Periodically sync nodeLookup
                if (data.active_faults) {
                    refreshTopologyStatus(data.active_faults);
                }
            }
        } catch (e) {
            console.error("Error parsing WS message:", e);
        }
    };

    ws.onclose = () => {
        setTimeout(initWebSocket, 3000);
    };
}

async function refreshTopologyStatus(activeFaults) {
    try {
        const resp = await fetch("/api/cluster/topology");
        const data = await resp.json();
        data.nodes.forEach(n => {
            nodeLookup[n.id] = n;
            if (networkData.nodes) {
                let color = "#06b6d4";
                if (n.status === "CRITICAL") color = "#ef4444";
                else if (n.status === "DEGRADED") color = "#f59e0b";
                else if (n.status === "SELF_HEALING") color = "#a855f7";
                networkData.nodes.update({ id: n.id, color: { background: color, border: "#1e293b" } });
            }
        });
        if (currentSelectedNodeId && nodeLookup[currentSelectedNodeId]) {
            selectService(currentSelectedNodeId);
        }
    } catch (e) {}
}

// -------------------------------------------------------------
// 4. Stepped & Autonomous Pipeline Execution
// -------------------------------------------------------------
function setPipelineStage(stageNum, message) {
    currentStage = stageNum;
    for (let i = 1; i <= 6; i++) {
        const card = document.getElementById(`step-card-${i}`);
        const pill = document.getElementById(`step-status-${i}`);
        if (i < stageNum) {
            card.className = "step-card";
            pill.textContent = "Passed";
            pill.style.color = "#10b981";
        } else if (i === stageNum) {
            card.className = "step-card active";
            pill.textContent = "Executing";
            pill.style.color = "#c4b5fd";
        } else {
            card.className = "step-card";
            pill.textContent = "Idle";
            pill.style.color = "#64748b";
        }
    }
    if (message) {
        document.getElementById("pipeline-status-text").textContent = message;
    }
}

async function stepStage() {
    const nextStage = currentStage >= 6 ? 1 : currentStage;
    try {
        const resp = await fetch("/api/self-heal/step", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ stage: nextStage })
        });
        const res = await resp.json();
        setPipelineStage(nextStage === 6 ? 1 : nextStage + 1, res.message);
        if (nextStage === 6) {
            refreshLedger();
        }
        refreshTopologyStatus({});
    } catch (e) {
        alert("Error executing stage step: " + e);
    }
}

async function triggerAutoHeal() {
    const banner = document.getElementById("pipeline-status-text");
    banner.textContent = "Autonomous Closed-Loop OODA Pipeline Executing...";

    try {
        const resp = await fetch("/api/self-heal/auto", { method: "POST" });
        const res = await resp.json();

        if (res.status === "REMEDIATED") {
            setPipelineStage(1, `Incident ${res.incident_id} Resolved! Root Cause: ${res.culprit_service} (${res.fault_type}). Remediation: ${res.selected_remediation}. p99 restored to ${res.post_p99_ms}ms.`);
            refreshLedger();
        } else {
            setPipelineStage(1, res.message);
        }
        refreshTopologyStatus({});
    } catch (e) {
        alert("Error in auto-heal: " + e);
    }
}

// -------------------------------------------------------------
// 5. Chaos Engineering Trigger Calls
// -------------------------------------------------------------
async function triggerChaos(scenario, target) {
    try {
        const resp = await fetch("/api/chaos/inject", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ scenario, target_service: target })
        });
        const res = await resp.json();
        setPipelineStage(1, `Chaos Injected: ${res.details.description} on ${res.details.target_name}`);
        selectService(target);
        refreshTopologyStatus({});
    } catch (e) {
        alert("Failed to inject chaos: " + e);
    }
}

async function clearChaos() {
    try {
        const resp = await fetch("/api/chaos/clear", { method: "POST" });
        const res = await resp.json();
        setPipelineStage(1, "Cluster reset to healthy operating baseline.");
        refreshTopologyStatus({});
    } catch (e) {
        alert("Failed to clear chaos: " + e);
    }
}

// -------------------------------------------------------------
// 6. Incident Audit Ledger & Post-Mortem Export
// -------------------------------------------------------------
async function refreshLedger() {
    try {
        const resp = await fetch("/api/audit/incidents");
        const data = await resp.json();
        const tbody = document.getElementById("incident-ledger-body");

        if (data.incidents.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted">No incidents recorded yet. Inject a chaos fault above to trigger autonomous remediation.</td></tr>`;
            return;
        }

        tbody.innerHTML = data.incidents.map(inc => `
            <tr>
                <td><code>${inc.incident_id}</code></td>
                <td><strong style="color:#ef4444">${inc.culprit_service}</strong></td>
                <td><span class="badge-mini safe">94.0%</span></td>
                <td><code>${inc.remediation_action}</code></td>
                <td>${inc.mttd_sec}s</td>
                <td><strong style="color:#10b981">${inc.mttr_sec}s</strong></td>
                <td><span class="badge-mini safe">${inc.verdict}</span></td>
            </tr>
        `).join("");
    } catch (e) {
        console.error("Failed to load incidents:", e);
    }
}

function exportAuditLedger() {
    fetch("/api/audit/incidents")
        .then(r => r.json())
        .then(data => {
            const jsonStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(data, null, 2));
            const dlAnchor = document.createElement("a");
            dlAnchor.setAttribute("href", jsonStr);
            dlAnchor.setAttribute("download", `post_mortem_audit_${Date.now()}.json`);
            dlAnchor.click();
        });
}
