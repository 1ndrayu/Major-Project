/**
 * AIOps Autonomous Self-Healing Ecosystem - Revamped Frontend Engine
 * Modern, Clean, Intuitive Control Plane
 * High-Contrast Palette: Deep Onyx Black • Vivid Orange • Electric Blue
 */

let network = null;
let networkData = { nodes: null, edges: null };
let allNodesCache = [];
let allEdgesCache = [];
let nodeLookup = {};
let currentSelectedNodeId = "svc-066";
let currentStage = 1;
let isAutoHealingActive = false;
let isFocusMode = true; // Default to clean blast-radius focus
let simActiveFaults = {};
let simIncidents = [];
let isLocalSimMode = false;
let simInterval = null;

// Chart instances
let chartP99 = null;
let chartError = null;
let chartPool = null;
let chartRps = null;

// Telemetry history (max 20 points)
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
// 1. Tab Navigation
// -------------------------------------------------------------
function switchTab(tabId) {
    document.querySelectorAll(".tab-pane").forEach(el => el.classList.remove("active"));
    document.querySelectorAll(".tab-item").forEach(el => el.classList.remove("active"));

    const targetContent = document.getElementById(tabId);
    if (targetContent) targetContent.classList.add("active");

    const activeBtn = Array.from(document.querySelectorAll(".tab-item")).find(btn =>
        btn.getAttribute("onclick") && btn.getAttribute("onclick").includes(tabId)
    );
    if (activeBtn) activeBtn.classList.add("active");

    // Hide/show topology-specific actions in tab header
    const tabActions = document.getElementById("tab-top-actions");
    if (tabActions) {
        tabActions.style.display = tabId === "tab-topology" ? "flex" : "none";
    }

    // Refresh graph rendering if switching to topology tab
    if (tabId === "tab-topology" && network) {
        setTimeout(() => network.fit(), 150);
    }
}

// -------------------------------------------------------------
// 2. Minimalist Golden Signals (Chart.js)
// -------------------------------------------------------------
function initCharts() {
    const cleanChartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: false },
            tooltip: {
                backgroundColor: '#161a24',
                titleColor: '#ffffff',
                bodyColor: '#e2e8f0',
                titleFont: { family: 'JetBrains Mono', size: 9, weight: '700' },
                bodyFont: { family: 'JetBrains Mono', size: 10 },
                borderColor: '#2a3347',
                borderWidth: 1,
                padding: 6,
                cornerRadius: 4,
                displayColors: false
            }
        },
        scales: {
            x: { display: false },
            y: { display: false }
        },
        elements: {
            point: { radius: 0, hoverRadius: 3, hoverBorderColor: '#0ea5e9' },
            line: { tension: 0.3, borderWidth: 2.0 }
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
                backgroundColor: "rgba(14, 165, 233, 0.1)",
                fill: true
            }]
        },
        options: cleanChartOptions
    });

    const ctxError = document.getElementById("chart-error").getContext("2d");
    chartError = new Chart(ctxError, {
        type: "line",
        data: {
            labels: timeLabels,
            datasets: [{
                data: historyError,
                borderColor: "#ff6b00", // Vivid Orange
                backgroundColor: "rgba(255, 107, 0, 0.1)",
                fill: true
            }]
        },
        options: cleanChartOptions
    });

    const ctxPool = document.getElementById("chart-pool").getContext("2d");
    chartPool = new Chart(ctxPool, {
        type: "line",
        data: {
            labels: timeLabels,
            datasets: [{
                data: historyPool,
                borderColor: "#ff8533", // Amber Orange
                backgroundColor: "rgba(255, 133, 51, 0.1)",
                fill: true
            }]
        },
        options: cleanChartOptions
    });

    const ctxRps = document.getElementById("chart-rps").getContext("2d");
    chartRps = new Chart(ctxRps, {
        type: "line",
        data: {
            labels: timeLabels,
            datasets: [{
                data: historyRps,
                borderColor: "#38bdf8", // Cyan
                backgroundColor: "rgba(56, 189, 248, 0.1)",
                fill: true
            }]
        },
        options: cleanChartOptions
    });
}

function updateChartData(p99, errorRate, poolSat, rps) {
    const nowLabel = new Date().toLocaleTimeString();
    timeLabels.push(nowLabel);
    historyP99.push(p99);
    historyError.push(errorRate * 100);
    historyPool.push(poolSat * 100);
    historyRps.push(rps);

    if (timeLabels.length > 20) {
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
// 3. Dynamic Topology Graph (Focused & De-cluttered)
// -------------------------------------------------------------
async function loadTopology() {
    try {
        let data = null;
        try {
            const resp = await fetch("/api/cluster/topology");
            if (resp.ok) data = await resp.json();
        } catch (e) {}

        if (!data) {
            // Static hosting fallback (GitHub Pages)
            isLocalSimMode = true;
            try {
                const resp = await fetch("./static/data/topology.json");
                if (resp.ok) data = await resp.json();
            } catch (e) {}
        }

        if (!data) {
            data = generateFallbackCluster();
        }

        allNodesCache = data.nodes;
        allEdgesCache = data.edges;

        data.nodes.forEach(n => {
            nodeLookup[n.id] = n;
        });

        renderGraph();
        selectService("svc-066");

        if (isLocalSimMode) {
            startLocalSimulationLoop();
        }

    } catch (e) {
        console.error("Failed to load topology:", e);
    }
}

function startLocalSimulationLoop() {
    if (simInterval) return;
    simInterval = setInterval(() => {
        const faultCount = Object.keys(simActiveFaults).length;
        let baseP99, baseErr, basePool, baseRps;

        if (faultCount > 0) {
            const isDb = !!simActiveFaults["svc-066"];
            baseP99 = isDb ? (780 + Math.random() * 90) : (410 + Math.random() * 60);
            baseErr = 0.084 + Math.random() * 0.025;
            basePool = isDb ? 0.98 : 0.45;
            baseRps = 1420 + Math.floor(Math.random() * 60);
        } else {
            baseP99 = 42.5 + Math.sin(Date.now() / 4000) * 8.5;
            baseErr = 0.0008 + Math.random() * 0.0005;
            basePool = 0.28 + Math.sin(Date.now() / 6000) * 0.04;
            baseRps = 1450 + Math.floor(Math.random() * 50);
        }

        updateChartData(baseP99, baseErr, basePool, baseRps);

        const badgeText = document.getElementById("system-status-text");
        const pip = document.getElementById("system-status-pip");
        if (badgeText && pip) {
            if (faultCount === 0) {
                badgeText.textContent = "All 100 Services Operational";
                pip.className = "status-dot healthy";
            } else {
                badgeText.textContent = `Incident Active • ${faultCount} Active Fault${faultCount === 1 ? '' : 's'}`;
                pip.className = "status-dot critical";
            }
        }
    }, 1000);
}

function generateFallbackCluster() {
    const nodes = [];
    const edges = [];
    const tiers = ["GATEWAY", "INGRESS", "AUTH", "CART", "PAYMENT", "ORDER", "INVENTORY", "NOTIFICATION", "DATABASE"];
    
    for (let i = 1; i <= 100; i++) {
        const id = `svc-${String(i).padStart(3, '0')}`;
        const tier = i <= 2 ? "GATEWAY" : (i <= 5 ? "INGRESS" : (i >= 90 ? "DATABASE" : tiers[i % tiers.length]));
        const name = i === 66 ? "Order-DB-Adapter" : (i === 1 ? "API-Gateway" : (i === 16 ? "Checkout-API" : (i === 20 ? "Payment-Settlement" : `Service-${i}`)));
        
        nodes.push({
            id: id,
            name: name,
            tier: tier,
            host_node: `k8s-worker-${(i % 8) + 1}`,
            status: "HEALTHY",
            p99_latency_ms: 35.0 + (i % 20),
            error_rate: 0.001,
            request_rate_rps: 120.0 + (i % 50),
            cpu_usage_pct: 25.0 + (i % 30),
            memory_usage_pct: 40.0 + (i % 25),
            db_pool_active: tier === "DATABASE" ? 12 : 0,
            db_pool_max: tier === "DATABASE" ? 50 : 0,
            replicas: tier === "GATEWAY" ? 6 : 3,
            active_fault: null
        });
        
        if (i > 1 && i <= 88) {
            const parentId = `svc-${String(Math.max(1, Math.floor(i / 2))).padStart(3, '0')}`;
            edges.push({
                source: parentId,
                target: id,
                p99_latency_ms: 12.0 + (i % 15),
                error_rate: 0.0005,
                throughput_rps: 65.0
            });
        }
    }
    return { nodes, edges, total_nodes: 100, total_edges: edges.length, active_faults: {} };
}

function renderGraph() {
    const visNodes = [];
    const visEdges = [];

    // Filter nodes if in Focus Mode (only show primary tiers & blast-radius nodes)
    let filteredNodes = allNodesCache;
    if (isFocusMode) {
        // Show active culprit, degraded nodes, and critical tier dependencies (around 20-30 clean nodes)
        const relevantIds = new Set(["svc-066", "svc-001", "svc-002", "svc-016", "svc-018", "svc-020", "svc-006", "svc-007", "svc-008", "svc-010", "svc-012", "svc-025", "svc-030", "svc-040", "svc-050", "svc-060", "svc-070", "svc-080", "svc-090", "svc-100"]);

        // Include any node currently degraded or critical
        allNodesCache.forEach(n => {
            if (n.status === "CRITICAL" || n.status === "DEGRADED" || n.status === "SELF_HEALING") {
                relevantIds.add(n.id);
            }
        });

        filteredNodes = allNodesCache.filter(n => relevantIds.has(n.id));
    }

    filteredNodes.forEach((n) => {
        let bgColor = "#14171d";
        let borderColor = "#3b82f6";
        let fontColor = "#ffffff";

        if (n.status === "CRITICAL") {
            bgColor = "#ea580c";
            borderColor = "#ffffff";
            fontColor = "#ffffff";
        } else if (n.status === "DEGRADED") {
            bgColor = "#fb923c";
            borderColor = "#ea580c";
            fontColor = "#000000";
        } else if (n.status === "SELF_HEALING") {
            bgColor = "#2563eb";
            borderColor = "#60a5fa";
            fontColor = "#ffffff";
        }

        visNodes.push({
            id: n.id,
            label: n.name.length > 16 ? n.name.substring(0, 14) + '..' : n.name,
            title: `${n.name} [${n.id}]\nTier: ${n.tier}\nLatency: ${n.p99_latency_ms.toFixed(1)}ms`,
            color: {
                background: bgColor,
                border: borderColor,
                highlight: { background: "#ea580c", border: "#ffffff" }
            },
            font: { color: fontColor, size: 10, face: "Inter" },
            shape: n.tier === "DATABASE" ? "database" : (n.tier === "GATEWAY" ? "diamond" : "dot"),
            size: n.id === "svc-066" ? 22 : 13
        });
    });

    const activeNodeSet = new Set(filteredNodes.map(n => n.id));
    allEdgesCache.forEach((e, idx) => {
        if (activeNodeSet.has(e.source) && activeNodeSet.has(e.target)) {
            const isHighLatency = e.p99_latency_ms > 500;
            visEdges.push({
                id: `e-${idx}`,
                from: e.source,
                to: e.target,
                arrows: "to",
                color: { color: isHighLatency ? "#ea580c" : "rgba(59, 130, 246, 0.35)", opacity: isHighLatency ? 0.95 : 0.6 },
                width: isHighLatency ? 2.2 : 1.0
            });
        }
    });

    const container = document.getElementById("network-topology-container");
    container.innerHTML = "";

    networkData.nodes = new vis.DataSet(visNodes);
    networkData.edges = new vis.DataSet(visEdges);

    const options = {
        nodes: { borderWidth: 1.5, shadow: false },
        edges: { smooth: { type: "continuous" } },
        physics: {
            stabilization: { iterations: 100 },
            barnesHut: { gravitationalConstant: -3200, centralGravity: 0.25, springLength: 85 }
        },
        interaction: { hover: true, tooltipDelay: 150 }
    };

    network = new vis.Network(container, networkData, options);

    network.once('stabilizationIterationsDone', function() {
        network.fit({ animation: { duration: 500, easingFunction: "easeInOutQuad" } });
    });

    network.on("click", (params) => {
        if (params.nodes.length > 0) {
            selectService(params.nodes[0]);
        }
    });
}

function toggleGraphFocus() {
    isFocusMode = !isFocusMode;
    const btn = document.getElementById("btn-toggle-view");
    if (btn) {
        btn.textContent = isFocusMode ? "Blast Radius Focus" : "Full 100-Mesh View";
        btn.className = isFocusMode ? "micro-btn active" : "micro-btn";
    }
    renderGraph();
}

function resetGraphView() {
    if (network) network.fit({ animation: { duration: 400, easingFunction: "easeInOutQuad" } });
}

function selectService(serviceId) {
    currentSelectedNodeId = serviceId;
    const n = nodeLookup[serviceId];
    if (!n) return;

    document.getElementById("inspector-service-name").textContent = `${n.name} [${n.id}]`;
    const statusEl = document.getElementById("inspector-service-status");
    statusEl.textContent = n.status;

    if (n.status === "CRITICAL") {
        statusEl.className = "badge badge-orange";
    } else if (n.status === "DEGRADED") {
        statusEl.className = "badge badge-orange";
    } else if (n.status === "SELF_HEALING") {
        statusEl.className = "badge badge-blue";
    } else {
        statusEl.className = "badge badge-healthy";
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
        preview.textContent = `[INFO] ${n.name} operational. Inbound throughput: ${n.request_rate_rps.toFixed(0)} req/s.
[INFO] W3C trace context propagated over gRPC. p99 response time: ${n.p99_latency_ms.toFixed(1)}ms`;
    }
}

// -------------------------------------------------------------
// 4. WebSocket Real-Time Telemetry Stream
// -------------------------------------------------------------
function initWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    if (!host || host.includes("github.io") || window.location.protocol === "file:") {
        // Pure static environment: run local simulation engine
        isLocalSimMode = true;
        startLocalSimulationLoop();
        return;
    }

    try {
        const wsUrl = `${protocol}//${host}/ws/live-stream`;
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            isLocalSimMode = false;
            if (simInterval) {
                clearInterval(simInterval);
                simInterval = null;
            }
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === "TELEMETRY_UPDATE") {
                    if (!isAutoHealingActive && currentStage === 1 && data.current_stage === 1) {
                        const ticker = document.getElementById("pipeline-status-text");
                        if (ticker && (!ticker.textContent || ticker.textContent.includes("operational") || ticker.textContent.includes("steady"))) {
                            ticker.textContent = data.status_message;
                        }
                    }

                    const orderDbPoolSat = nodeLookup["svc-066"] ? (nodeLookup["svc-066"].db_pool_active / Math.max(1, nodeLookup["svc-066"].db_pool_max)) : 0.3;
                    updateChartData(data.system_p99_ms, data.system_error_rate, orderDbPoolSat, data.system_total_rps);

                    const faultCount = Object.keys(data.active_faults).length;
                    const badgeText = document.getElementById("system-status-text");
                    const pip = document.getElementById("system-status-pip");

                    if (faultCount === 0) {
                        badgeText.textContent = "All 100 Services Operational";
                        pip.className = "status-dot healthy";
                    } else {
                        badgeText.textContent = `Incident Active • ${faultCount} Active Fault${faultCount === 1 ? '' : 's'}`;
                        pip.className = "status-dot critical";
                    }

                    if (data.active_faults) {
                        refreshTopologyStatus(data.active_faults);
                    }
                }
            } catch (e) {
                console.error("Error parsing WS message:", e);
            }
        };

        ws.onerror = () => {
            if (!isLocalSimMode) {
                isLocalSimMode = true;
                startLocalSimulationLoop();
            }
        };

        ws.onclose = () => {
            if (!isLocalSimMode) {
                setTimeout(initWebSocket, 4000);
            }
        };
    } catch (e) {
        isLocalSimMode = true;
        startLocalSimulationLoop();
    }
}

async function refreshTopologyStatus(activeFaults) {
    try {
        let nodesToUpdate = allNodesCache;
        try {
            const resp = await fetch("/api/cluster/topology");
            if (resp.ok) {
                const data = await resp.json();
                allNodesCache = data.nodes;
                nodesToUpdate = data.nodes;
            }
        } catch (e) {}

        nodesToUpdate.forEach(n => {
            nodeLookup[n.id] = n;
            if (networkData.nodes && networkData.nodes.get(n.id)) {
                let bgColor = "#14171d";
                let borderColor = "#3b82f6";
                let fontColor = "#ffffff";

                if (n.status === "CRITICAL") {
                    bgColor = "#ea580c";
                    borderColor = "#ffffff";
                    fontColor = "#ffffff";
                } else if (n.status === "DEGRADED") {
                    bgColor = "#fb923c";
                    borderColor = "#ea580c";
                    fontColor = "#000000";
                } else if (n.status === "SELF_HEALING") {
                    bgColor = "#2563eb";
                    borderColor = "#60a5fa";
                    fontColor = "#ffffff";
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
// 5. Runway Stepper & Autonomous Loop
// -------------------------------------------------------------
const SIMULATED_STAGES = {
    1: { message: "Anomaly detected via multimodal telemetry (z = 3.42σ). Initiating blast radius isolation.", primary_service: "svc-066" },
    2: { message: "Dynamic G_t subgraph extracted. Blast radius isolated to 4 downstream services.", culprit_service: "svc-066" },
    3: { message: "GATv2 Causal RCA completed. Root culprit identified: Order-DB-Adapter (svc-066) with 94.0% confidence.", culprit_service: "svc-066" },
    4: { message: "Digital Twin simulated 3 candidate policies. Policy #1 (DB pool expansion) verified safe.", target_service: "svc-066" },
    5: { message: "Safe-RL policy PATCH_HIKARICP_POOL applied: max=80, timeout=10s. Atomic rollback checkpoint primed.", target_service: "svc-066" },
    6: { message: "Canary verification PASSED: p99 latency returned to 38.4ms, error rate 0.00%. Incident closed.", target_service: "svc-066" }
};

function setPipelineStage(stageNum, message) {
    currentStage = stageNum;
    for (let i = 1; i <= 6; i++) {
        const card = document.getElementById(`step-card-${i}`);
        const statusEl = document.getElementById(`step-status-${i}`);
        if (!card || !statusEl) continue;

        if (i < stageNum) {
            card.className = "stage-item completed";
            statusEl.textContent = "Verified";
        } else if (i === stageNum) {
            card.className = "stage-item active";
            statusEl.textContent = "Running";
        } else {
            card.className = "stage-item";
            statusEl.textContent = "Standby";
        }
    }
    if (message) {
        document.getElementById("pipeline-status-text").textContent = message;
    }
}

async function stepStage() {
    if (isAutoHealingActive) return;

    const stepBtn = document.getElementById("btn-step-stage");
    stepBtn.disabled = true;

    const stageToRun = currentStage > 6 ? 1 : currentStage;

    try {
        setPipelineStage(stageToRun, `Executing Stage 0${stageToRun}...`);

        let res = null;
        try {
            const resp = await fetch("/api/self-heal/step", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ stage: stageToRun })
            });
            if (resp.ok) res = await resp.json();
        } catch (e) {}

        if (!res) {
            res = SIMULATED_STAGES[stageToRun] || { message: `Stage 0${stageToRun} completed.` };
            if (stageToRun === 5 && nodeLookup["svc-066"]) {
                nodeLookup["svc-066"].status = "SELF_HEALING";
            } else if (stageToRun === 6) {
                simActiveFaults = {};
                allNodesCache.forEach(n => {
                    n.status = "HEALTHY";
                    n.active_fault = null;
                    n.p99_latency_ms = 38.4;
                    n.error_rate = 0.0002;
                    if (n.db_pool_max) n.db_pool_active = 14;
                });
                simIncidents.unshift({
                    incident_id: "INC-" + Math.floor(1000 + Math.random() * 9000),
                    culprit_service: "svc-066",
                    remediation_action: "PATCH_HIKARICP_POOL(max=80)",
                    mttd_sec: 1.4,
                    mttr_sec: 4.8,
                    verdict: "PASSED"
                });
            }
        }

        if (res.primary_service) selectService(res.primary_service);
        if (res.culprit_service) selectService(res.culprit_service);
        if (res.target_service) selectService(res.target_service);

        if (stageToRun === 6) {
            for (let i = 1; i <= 6; i++) {
                const card = document.getElementById(`step-card-${i}`);
                const statusEl = document.getElementById(`step-status-${i}`);
                if (card) card.className = "stage-item completed";
                if (statusEl) statusEl.textContent = "Verified";
            }
            document.getElementById("pipeline-status-text").textContent = res.message;
            currentStage = 1;
            refreshLedger();
            setTimeout(() => refreshTopologyStatus({}), 500);
        } else {
            const next = res.next_stage || (stageToRun + 1);
            setPipelineStage(next, res.message);
        }

        refreshTopologyStatus({});
    } catch (e) {
        console.error("Step error:", e);
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
    autoBtn.innerHTML = `<span>Remediating Incident...</span>`;

    const sleep = (ms) => new Promise(r => setTimeout(r, ms));

    try {
        for (let s = 1; s <= 6; s++) {
            setPipelineStage(s, `Executing Stage 0${s} in automated remediation pipeline...`);

            let res = null;
            try {
                const resp = await fetch("/api/self-heal/step", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ stage: s })
                });
                if (resp.ok) res = await resp.json();
            } catch (e) {}

            if (!res) {
                res = SIMULATED_STAGES[s] || { message: `Stage 0${s} completed.` };
                if (s === 5 && nodeLookup["svc-066"]) {
                    nodeLookup["svc-066"].status = "SELF_HEALING";
                } else if (s === 6) {
                    simActiveFaults = {};
                    allNodesCache.forEach(n => {
                        n.status = "HEALTHY";
                        n.active_fault = null;
                        n.p99_latency_ms = 38.4;
                        n.error_rate = 0.0002;
                        if (n.db_pool_max) n.db_pool_active = 14;
                    });
                    simIncidents.unshift({
                        incident_id: "INC-" + Math.floor(1000 + Math.random() * 9000),
                        culprit_service: "svc-066",
                        remediation_action: "PATCH_HIKARICP_POOL(max=80)",
                        mttd_sec: 1.4,
                        mttr_sec: 4.8,
                        verdict: "PASSED"
                    });
                }
            }

            if (res.primary_service) selectService(res.primary_service);
            if (res.culprit_service) selectService(res.culprit_service);
            if (res.target_service) selectService(res.target_service);

            document.getElementById("pipeline-status-text").textContent = res.message;
            refreshTopologyStatus({});

            if (s < 6) await sleep(800);
        }

        for (let i = 1; i <= 6; i++) {
            const card = document.getElementById(`step-card-${i}`);
            const statusEl = document.getElementById(`step-status-${i}`);
            if (card) card.className = "stage-item completed";
            if (statusEl) statusEl.textContent = "Verified";
        }

        refreshLedger();
        refreshTopologyStatus({});
        currentStage = 1;

    } catch (e) {
        console.error("Autonomous error:", e);
    } finally {
        isAutoHealingActive = false;
        autoBtn.disabled = false;
        stepBtn.disabled = false;
        autoBtn.innerHTML = originalText;
    }
}

// -------------------------------------------------------------
// 6. Chaos Fault Injection
// -------------------------------------------------------------
async function triggerChaos(scenario, target) {
    try {
        let handledByBackend = false;
        try {
            const resp = await fetch("/api/chaos/inject", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ scenario, target_service: target })
            });
            if (resp.ok) {
                const res = await resp.json();
                setPipelineStage(1, `FAULT INJECTED // ${res.details.description} on ${res.details.target_name}`);
                handledByBackend = true;
            }
        } catch (e) {}

        if (!handledByBackend) {
            simActiveFaults[target] = scenario;
            if (nodeLookup[target]) {
                nodeLookup[target].status = "CRITICAL";
                nodeLookup[target].active_fault = scenario.toUpperCase();
                if (scenario === "db_pool_exhaustion") {
                    nodeLookup[target].db_pool_active = nodeLookup[target].db_pool_max;
                    nodeLookup[target].p99_latency_ms = 840.5;
                    nodeLookup[target].error_rate = 0.125;
                } else if (scenario === "cpu_starvation") {
                    nodeLookup[target].cpu_usage_pct = 99.4;
                    nodeLookup[target].p99_latency_ms = 620.0;
                }
            }

            allEdgesCache.forEach(e => {
                if (e.target === target && nodeLookup[e.source]) {
                    nodeLookup[e.source].status = "DEGRADED";
                    nodeLookup[e.source].p99_latency_ms = 380.0;
                }
            });

            setPipelineStage(1, `FAULT INJECTED // ${scenario.toUpperCase().replace(/_/g, ' ')} on ${target}`);
            startLocalSimulationLoop();
        }

        selectService(target);
        refreshTopologyStatus({});
        switchTab('tab-topology');
    } catch (e) {
        console.error("Failed to inject fault:", e);
    }
}

async function clearChaos() {
    try {
        try {
            await fetch("/api/chaos/clear", { method: "POST" });
        } catch (e) {}

        simActiveFaults = {};
        allNodesCache.forEach(n => {
            n.status = "HEALTHY";
            n.active_fault = null;
            n.p99_latency_ms = 35.0 + Math.random() * 10;
            n.error_rate = 0.0008;
            if (n.db_pool_max) n.db_pool_active = Math.floor(n.db_pool_max * 0.28);
        });

        setPipelineStage(1, "Cluster baseline restored. Active faults cleared.");
        refreshTopologyStatus({});
    } catch (e) {
        console.error("Failed to clear chaos:", e);
    }
}

// -------------------------------------------------------------
// 7. Incident Audit Ledger
// -------------------------------------------------------------
async function refreshLedger() {
    try {
        let incidents = [];
        try {
            const resp = await fetch("/api/audit/incidents");
            if (resp.ok) {
                const data = await resp.json();
                incidents = data.incidents || [];
            }
        } catch (e) {}

        if (incidents.length === 0 && simIncidents.length > 0) {
            incidents = simIncidents;
        }

        const tbody = document.getElementById("incident-ledger-body");
        if (!tbody) return;

        if (incidents.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="empty-state">No incidents logged. Execute a failure simulation above to observe the automated remediation workflow.</td></tr>`;
            return;
        }

        tbody.innerHTML = incidents.map(inc => `
            <tr>
                <td><span class="mono-tag">${inc.incident_id}</span></td>
                <td><strong style="color:var(--accent-orange)">${inc.culprit_service}</strong></td>
                <td><span class="mono-tag">94.0%</span></td>
                <td><span class="mono-tag">${inc.remediation_action}</span></td>
                <td><span class="txt-muted">${inc.mttd_sec}s</span></td>
                <td><span class="txt-muted">${inc.mttr_sec}s</span></td>
                <td><span class="badge badge-blue">${inc.verdict}</span></td>
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
