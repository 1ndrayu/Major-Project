/**
 * AIOps Autonomous Self-Healing Ecosystem - Frontend Logic
 * Design System: CRED Luxury & H&M High-Fashion Editorial (Light Mode)
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

// Telemetry history for charts (max 25 data points)
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
// 1. Technical Dark Chart.js Initialization (Black, Orange, Blue)
// -------------------------------------------------------------
function initCharts() {
    const techDarkOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: false },
            tooltip: {
                backgroundColor: '#151820',
                titleColor: '#ffffff',
                bodyColor: '#e2e8f0',
                titleFont: { family: 'JetBrains Mono', size: 10, weight: '700' },
                bodyFont: { family: 'JetBrains Mono', size: 11 },
                borderColor: '#282e3d',
                borderWidth: 1,
                padding: 8,
                cornerRadius: 0,
                displayColors: false
            }
        },
        scales: {
            x: { display: false },
            y: {
                display: true,
                grid: { color: 'rgba(255, 255, 255, 0.05)', drawTicks: false },
                ticks: {
                    color: '#94a3b8',
                    font: { family: 'JetBrains Mono', size: 8, weight: '600' },
                    maxTicksLimit: 3
                },
                border: { display: false }
            }
        },
        elements: {
            point: { radius: 0, hoverRadius: 4, hoverBorderColor: '#0ea5e9' },
            line: { tension: 0.25, borderWidth: 2.0 }
        }
    };

    const ctxP99 = document.getElementById("chart-p99").getContext("2d");
    chartP99 = new Chart(ctxP99, {
        type: "line",
        data: {
            labels: timeLabels,
            datasets: [{
                data: historyP99,
                borderColor: "#0ea5e9", // Electric Blue
                backgroundColor: "rgba(14, 165, 233, 0.08)",
                fill: true
            }]
        },
        options: techDarkOptions
    });

    const ctxError = document.getElementById("chart-error").getContext("2d");
    chartError = new Chart(ctxError, {
        type: "line",
        data: {
            labels: timeLabels,
            datasets: [{
                data: historyError,
                borderColor: "#ff6b00", // Vivid Orange
                backgroundColor: "rgba(255, 107, 0, 0.08)",
                fill: true
            }]
        },
        options: techDarkOptions
    });

    const ctxPool = document.getElementById("chart-pool").getContext("2d");
    chartPool = new Chart(ctxPool, {
        type: "line",
        data: {
            labels: timeLabels,
            datasets: [{
                data: historyPool,
                borderColor: "#ff8533", // Amber Orange
                backgroundColor: "rgba(255, 133, 51, 0.08)",
                fill: true
            }]
        },
        options: techDarkOptions
    });

    const ctxRps = document.getElementById("chart-rps").getContext("2d");
    chartRps = new Chart(ctxRps, {
        type: "line",
        data: {
            labels: timeLabels,
            datasets: [{
                data: historyRps,
                borderColor: "#38bdf8", // Cyan Blue
                backgroundColor: "rgba(56, 189, 248, 0.08)",
                fill: true
            }]
        },
        options: techDarkOptions
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

    // Update numbers with crisp black typography
    document.getElementById("metric-p99").innerHTML = `${p99.toFixed(1)} <span class="unit">ms</span>`;
    document.getElementById("metric-error").innerHTML = `${(errorRate * 100).toFixed(2)} <span class="unit">%</span>`;
    document.getElementById("metric-pool").innerHTML = `${(poolSat * 100).toFixed(1)} <span class="unit">%</span>`;
    document.getElementById("metric-rps").innerHTML = `${rps.toLocaleString()} <span class="unit">RPS</span>`;
}

// -------------------------------------------------------------
// 2. Vis.js Dynamic 100-Microservice Topology Graph (Black, Orange, Blue)
// -------------------------------------------------------------
async function loadTopology() {
    try {
        const resp = await fetch("/api/cluster/topology");
        const data = await resp.json();

        const visNodes = [];
        const visEdges = [];

        data.nodes.forEach((n) => {
            nodeLookup[n.id] = n;
            let bgColor = "#101217";
            let borderColor = "#0ea5e9";
            let fontColor = "#e2e8f0";

            if (n.status === "CRITICAL") {
                bgColor = "#ff6b00";
                borderColor = "#ffffff";
                fontColor = "#000000";
            } else if (n.status === "DEGRADED") {
                bgColor = "#ff8533";
                borderColor = "#ff6b00";
                fontColor = "#000000";
            } else if (n.status === "SELF_HEALING") {
                bgColor = "#0ea5e9";
                borderColor = "#38bdf8";
                fontColor = "#000000";
            }

            visNodes.push({
                id: n.id,
                label: n.name.length > 18 ? n.name.substring(0, 16) + '..' : n.name,
                title: `${n.name} [${n.id}]\nTier: ${n.tier}\nHost: ${n.host_node}\np99: ${n.p99_latency_ms}ms`,
                color: {
                    background: bgColor,
                    border: borderColor,
                    highlight: { background: "#ff6b00", border: "#ffffff" }
                },
                font: { color: fontColor, size: 9, face: "Space Grotesk", strokeWidth: 0 },
                shape: n.tier === "DATABASE" ? "database" : (n.tier === "GATEWAY" ? "diamond" : "dot"),
                size: n.id === "svc-066" ? 22 : 13
            });
        });

        data.edges.forEach((e, idx) => {
            const isHighLatency = e.p99_latency_ms > 500;
            visEdges.push({
                id: `e-${idx}`,
                from: e.source,
                to: e.target,
                arrows: "to",
                color: { color: isHighLatency ? "#ff6b00" : "rgba(14, 165, 233, 0.45)", opacity: isHighLatency ? 0.95 : 0.6 },
                width: isHighLatency ? 2.0 : 0.8
            });
        });

        const container = document.getElementById("network-topology-container");
        container.innerHTML = "";

        networkData.nodes = new vis.DataSet(visNodes);
        networkData.edges = new vis.DataSet(visEdges);

        const options = {
            nodes: {
                borderWidth: 1.5,
                shadow: false
            },
            edges: {
                smooth: { type: "continuous" }
            },
            physics: {
                stabilization: { iterations: 120 },
                barnesHut: { gravitationalConstant: -3600, centralGravity: 0.28, springLength: 75 }
            },
            interaction: { hover: true, tooltipDelay: 200 }
        };

        network = new vis.Network(container, networkData, options);

        network.once('stabilizationIterationsDone', function() {
            network.fit({ animation: { duration: 600, easingFunction: "easeInOutQuad" } });
        });

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

    document.getElementById("inspector-service-name").textContent = `${n.name} [${n.id}]`;
    const statusEl = document.getElementById("inspector-service-status");
    statusEl.textContent = n.status;

    if (n.status === "CRITICAL") {
        statusEl.className = "status-chip chip-breached";
    } else if (n.status === "DEGRADED") {
        statusEl.className = "status-chip chip-gold";
    } else if (n.status === "SELF_HEALING") {
        statusEl.className = "status-chip chip-selected";
    } else {
        statusEl.className = "status-chip chip-safe";
    }

    document.getElementById("ins-p99").textContent = `${n.p99_latency_ms.toFixed(1)} ms`;
    document.getElementById("ins-err").textContent = `${(n.error_rate * 100).toFixed(2)}%`;
    const poolSat = (n.db_pool_active / Math.max(1, n.db_pool_max) * 100).toFixed(0);
    document.getElementById("ins-pool").textContent = `${n.db_pool_active} / ${n.db_pool_max} (${poolSat}%)`;
    document.getElementById("ins-reps").textContent = `${n.replicas} Pods [${n.host_node}]`;

    const preview = document.getElementById("ins-log-preview");
    if (n.active_fault === "DB_POOL_EXHAUSTION") {
        preview.textContent = `[ERROR] HikariPool-1 - Connection is not available, request timed out after 30005ms (active=${n.db_pool_active}/${n.db_pool_max})
[ERROR] org.springframework.dao.CannotAcquireLockException: Connection pool exhausted
[WARN] Cascading thread pool exhaustion: 82 worker threads waiting on DB connection lease`;
    } else if (n.active_fault === "MEMORY_LEAK") {
        preview.textContent = `[CRITICAL] java.lang.OutOfMemoryError: Java heap space
[WARN] Full GC pause took 2840ms. Stop-the-world event triggered.`;
    } else {
        preview.textContent = `[INFO] ${n.name} healthy. Inbound throughput: ${n.request_rate_rps.toFixed(0)} req/s.
[INFO] W3C trace context propagated over gRPC. p99 response time: ${n.p99_latency_ms.toFixed(1)}ms`;
    }
}

function resetGraphView() {
    if (network) network.fit({ animation: { duration: 500, easingFunction: "easeInOutQuad" } });
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
                // Only sync pipeline stage from background telemetry if no autonomous cycle or manual stepping is active
                if (!isAutoHealingActive && currentStage === 1 && data.current_stage === 1) {
                    // Update ticker only if still in steady state
                    const ticker = document.getElementById("pipeline-status-text");
                    if (ticker && (!ticker.textContent || ticker.textContent.includes("steady state") || ticker.textContent.includes("ready") || ticker.textContent.includes("idle"))) {
                        ticker.textContent = data.status_message;
                    }
                }

                // Update charts
                const orderDbPoolSat = nodeLookup["svc-066"] ? (nodeLookup["svc-066"].db_pool_active / Math.max(1, nodeLookup["svc-066"].db_pool_max)) : 0.3;
                updateChartData(data.system_p99_ms, data.system_error_rate, orderDbPoolSat, data.system_total_rps);

                // Update status badge
                const faultCount = Object.keys(data.active_faults).length;
                document.getElementById("active-fault-pill").textContent = `${faultCount} Active`;

                const badgeText = document.getElementById("system-status-text");
                const dot = document.getElementById("system-status-badge").querySelector(".pip");

                if (faultCount === 0) {
                    badgeText.textContent = "SYSTEM OPERATIONAL";
                    dot.className = "pip pip-live";
                } else {
                    badgeText.textContent = `ANOMALY DETECTED // ${faultCount} FAULT${faultCount === 1 ? '' : 'S'}`;
                    dot.className = "pip pip-critical";
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
                let bgColor = "#101217";
                let borderColor = "#0ea5e9";
                let fontColor = "#e2e8f0";

                if (n.status === "CRITICAL") {
                    bgColor = "#ff6b00";
                    borderColor = "#ffffff";
                    fontColor = "#000000";
                } else if (n.status === "DEGRADED") {
                    bgColor = "#ff8533";
                    borderColor = "#ff6b00";
                    fontColor = "#000000";
                } else if (n.status === "SELF_HEALING") {
                    bgColor = "#0ea5e9";
                    borderColor = "#38bdf8";
                    fontColor = "#000000";
                }

                networkData.nodes.update({
                    id: n.id,
                    color: { background: bgColor, border: borderColor },
                    font: { color: fontColor }
                });
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
let isAutoHealingActive = false;

function setPipelineStage(stageNum, message) {
    currentStage = stageNum;
    for (let i = 1; i <= 6; i++) {
        const card = document.getElementById(`step-card-${i}`);
        const statusEl = document.getElementById(`step-status-${i}`);
        if (!card || !statusEl) continue;

        if (i < stageNum) {
            card.className = "stage-tile completed";
            statusEl.textContent = "VERIFIED";
        } else if (i === stageNum) {
            card.className = "stage-tile active";
            statusEl.textContent = "EXECUTING";
        } else {
            card.className = "stage-tile";
            statusEl.textContent = "STANDBY";
        }
    }
    if (message) {
        document.getElementById("pipeline-status-text").textContent = message;
    }
}

function resetPipelineUI() {
    currentStage = 1;
    for (let i = 1; i <= 6; i++) {
        const card = document.getElementById(`step-card-${i}`);
        const statusEl = document.getElementById(`step-status-${i}`);
        if (card) card.className = "stage-tile";
        if (statusEl) statusEl.textContent = "STANDBY";
    }
    document.getElementById("pipeline-status-text").textContent = "Pipeline ready. Click 'STEP PIPELINE' or 'AUTONOMOUS EXECUTION' to initiate.";
}

async function stepStage() {
    if (isAutoHealingActive) return;

    const stepBtn = document.getElementById("btn-step-stage");
    stepBtn.disabled = true;

    // Use currentStage (1 to 6)
    const stageToRun = currentStage > 6 ? 1 : currentStage;

    try {
        // Set visual cue that this stage is executing
        setPipelineStage(stageToRun, `Executing Stage 0${stageToRun}...`);

        const resp = await fetch("/api/self-heal/step", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ stage: stageToRun })
        });
        const res = await resp.json();

        // Highlight affected/culprit nodes in topology based on stage
        if (res.primary_service) {
            selectService(res.primary_service);
        } else if (res.culprit_service) {
            selectService(res.culprit_service);
        } else if (res.target_service) {
            selectService(res.target_service);
        }

        // Advance to next stage or finish
        if (stageToRun === 6) {
            // Mark all stages completed
            for (let i = 1; i <= 6; i++) {
                const card = document.getElementById(`step-card-${i}`);
                const statusEl = document.getElementById(`step-status-${i}`);
                if (card) card.className = "stage-tile completed";
                if (statusEl) statusEl.textContent = "VERIFIED";
            }
            document.getElementById("pipeline-status-text").textContent = res.message;
            currentStage = 1;
            refreshLedger();
            setTimeout(() => {
                refreshTopologyStatus({});
            }, 500);
        } else {
            const next = res.next_stage || (stageToRun + 1);
            setPipelineStage(next, res.message);
        }

        refreshTopologyStatus({});
    } catch (e) {
        console.error("Pipeline step error:", e);
        document.getElementById("pipeline-status-text").textContent = `Error in stage ${stageToRun}: ${e.message || e}`;
    } finally {
        stepBtn.disabled = false;
    }
}

async function triggerAutoHeal() {
    if (isAutoHealingActive) return;
    isAutoHealingActive = true;

    const autoBtn = document.getElementById("btn-auto-heal");
    const stepBtn = document.getElementById("btn-step-stage");
    const originalText = autoBtn.innerHTML;

    autoBtn.disabled = true;
    stepBtn.disabled = true;
    autoBtn.innerHTML = `<span>RUNNING OODA...</span>`;

    const sleep = (ms) => new Promise(r => setTimeout(r, ms));

    try {
        // Sequentially execute all 6 stages with crisp visual progression
        for (let s = 1; s <= 6; s++) {
            setPipelineStage(s, `Executing Stage 0${s} in autonomous closed-loop...`);

            const resp = await fetch("/api/self-heal/step", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ stage: s })
            });
            const res = await resp.json();

            // Highlight target in inspector
            if (res.primary_service) selectService(res.primary_service);
            if (res.culprit_service) selectService(res.culprit_service);
            if (res.target_service) selectService(res.target_service);

            document.getElementById("pipeline-status-text").textContent = res.message;
            refreshTopologyStatus({});

            // Realistic pause per stage so observers can see the decision cycle
            if (s < 6) {
                await sleep(950);
            }
        }

        // Mark all 6 stages verified
        for (let i = 1; i <= 6; i++) {
            const card = document.getElementById(`step-card-${i}`);
            const statusEl = document.getElementById(`step-status-${i}`);
            if (card) card.className = "stage-tile completed";
            if (statusEl) statusEl.textContent = "VERIFIED";
        }

        refreshLedger();
        refreshTopologyStatus({});
        currentStage = 1;

    } catch (e) {
        console.error("Autonomous execution error:", e);
        document.getElementById("pipeline-status-text").textContent = `Autonomous loop error: ${e.message || e}`;
    } finally {
        isAutoHealingActive = false;
        autoBtn.disabled = false;
        stepBtn.disabled = false;
        autoBtn.innerHTML = originalText;
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
        setPipelineStage(1, `FAULT INJECTED // ${res.details.description} on ${res.details.target_name}`);
        selectService(target);
        refreshTopologyStatus({});
    } catch (e) {
        alert("Failed to inject chaos experiment: " + e);
    }
}

async function clearChaos() {
    try {
        const resp = await fetch("/api/chaos/clear", { method: "POST" });
        const res = await resp.json();
        setPipelineStage(1, "Cluster steady-state baseline restored. Injected faults cleared.");
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
            tbody.innerHTML = `<tr><td colspan="7" class="empty-state">No incidents logged. Execute a synthetic fault above to initiate the autonomous cycle.</td></tr>`;
            return;
        }

        tbody.innerHTML = data.incidents.map(inc => `
            <tr>
                <td><span class="mono-code">${inc.incident_id}</span></td>
                <td><strong style="color:var(--cred-crimson)">${inc.culprit_service}</strong></td>
                <td><span class="status-chip chip-gold">94.0%</span></td>
                <td><span class="mono-code">${inc.remediation_action}</span></td>
                <td><span class="mono-code">${inc.mttd_sec}s</span></td>
                <td><span class="val-positive">${inc.mttr_sec}s</span></td>
                <td><span class="status-chip chip-safe">${inc.verdict}</span></td>
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
