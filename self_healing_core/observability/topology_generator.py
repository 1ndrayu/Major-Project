"""
Enterprise 100-Microservice Topology Generator
Constructs a realistic cloud-native topology following DeathStarBench & TrainTicket benchmarks.
Generates 100 services partitioned across functional tiers with realistic call graphs and Kubernetes node co-locations.
"""

from typing import Dict, List, Tuple
from self_healing_core.models import ServiceNode, CallEdge, ServiceTier, ServiceStatus, FaultType


def generate_100_service_topology() -> Tuple[Dict[str, ServiceNode], List[CallEdge]]:
    """
    Generates 100 interconnected microservice nodes and realistic RPC call edges.
    Tiers:
    - FRONTEND & EDGE (Services 1-5): Web-UI, Mobile-BFF, Partner-API, Admin-Portal, Edge-CDN-Proxy
    - API GATEWAYS (Services 6-10): API-Gateway-Alpha, API-Gateway-Beta, Ingress-Router, GraphQL-Gateway, WAF-Gateway
    - AUTH & IDENTITY (Services 11-15): Auth-Service, Token-Issuer, OAuth-Broker, User-Directory, Session-Store-Proxy
    - CORE COMMERCE & CHECKOUT (Services 16-30):
        Checkout-API, Order-Orchestrator, Cart-Service, Payment-Gateway, Payment-Processor,
        Payment-Audit, Fraud-Detector, Pricing-Engine, Tax-Calculator, Currency-Converter,
        Coupon-Service, Loyalty-Points, Gift-Card-Service, Invoice-Generator, Receipt-Mailer
    - CATALOG & SEARCH (Services 31-45):
        Product-Catalog, Category-Tree, Search-Engine, Elasticsearch-Proxy, Auto-Complete,
        Filter-Service, Product-Review, Rating-Aggregator, Media-CDN-Proxy, Inventory-Lookup,
        Warehouse-Tracker, Stock-Reservation, Seller-Directory, Recommendation-Feed, Personalization-Engine
    - FULFILLMENT & SHIPPING (Services 46-55):
        Shipping-Coordinator, Carrier-Integration, Tracking-Service, Dispatch-Planner, Package-Scanner,
        Return-Processing, Fleet-Manager, Customs-Declarator, Address-Validator, Geo-Routing
    - NOTIFICATION & MESSAGING (Services 56-65):
        Notification-Dispatcher, Push-Notifier, SMS-Gateway, Email-Relay, In-App-Messenger,
        Kafka-Ingress-Proxy, Kafka-Egress-Adapter, Event-Audit-Logger, Webhook-Caller, Alert-Broadcaster
    - DATABASE ADAPTERS & TIERS (Services 66-85):
        Order-DB-Adapter, User-DB-Adapter, Payment-Ledger-DB, Catalog-DB-Adapter, Inventory-DB-Adapter,
        Cart-Redis-Cluster, Session-Redis-Cluster, Auth-DB-Adapter, Shipping-DB-Adapter, Analytics-ClickHouse,
        Reporting-Replica, Search-Index-Store, Audit-Cassandra-Cluster, Metadata-Postgres, Token-Cache-Cluster,
        Config-ZooKeeper, Secret-Vault-Proxy, Read-Replica-Pool-1, Read-Replica-Pool-2, TimeSeries-DB-Adapter
    - ANALYTICS & PLATFORM (Services 86-100):
        Realtime-Metrics-Aggregator, Clickstream-Ingestor, ETL-Pipeline-Coordinator, Spark-Job-Trigger,
        ML-Inference-Serving, AB-Testing-Engine, Feature-Store-Proxy, User-Behavior-Modeler,
        Fraud-Inference-Worker, Cost-Allocation-Tracker, Health-Monitor, Chaos-Agent,
        Trace-Collector-Daemon, Log-Shipper-Daemon, Operator-Controller
    """
    nodes: Dict[str, ServiceNode] = {}
    edges: List[CallEdge] = []

    k8s_nodes = [f"k8s-worker-{i:02d}" for i in range(1, 9)]

    service_definitions = [
        # (id, name, tier, default_cpu, default_mem, default_pool_max, default_rps, default_p99)
        # FRONTEND & EDGE (1-5)
        ("svc-001", "Web-UI-Frontend", ServiceTier.FRONTEND, 18.0, 256.0, 20, 650.0, 28.0),
        ("svc-002", "Mobile-BFF-Gateway", ServiceTier.FRONTEND, 22.0, 310.0, 25, 520.0, 32.0),
        ("svc-003", "Partner-Public-API", ServiceTier.FRONTEND, 15.0, 280.0, 20, 210.0, 35.0),
        ("svc-004", "Admin-Portal-UI", ServiceTier.FRONTEND, 12.0, 220.0, 15, 60.0, 25.0),
        ("svc-005", "Edge-CDN-Proxy", ServiceTier.FRONTEND, 25.0, 380.0, 30, 800.0, 15.0),

        # API GATEWAYS (6-10)
        ("svc-006", "API-Gateway-Alpha", ServiceTier.GATEWAY, 30.0, 512.0, 40, 720.0, 38.0),
        ("svc-007", "API-Gateway-Beta", ServiceTier.GATEWAY, 28.0, 480.0, 40, 680.0, 39.0),
        ("svc-008", "Ingress-Router", ServiceTier.GATEWAY, 35.0, 550.0, 40, 950.0, 20.0),
        ("svc-009", "GraphQL-Aggregator", ServiceTier.GATEWAY, 32.0, 620.0, 35, 450.0, 45.0),
        ("svc-010", "WAF-Security-Filter", ServiceTier.GATEWAY, 24.0, 390.0, 25, 880.0, 18.0),

        # AUTH & IDENTITY (11-15)
        ("svc-011", "Auth-Token-Validator", ServiceTier.MIDDLEWARE, 20.0, 320.0, 30, 850.0, 22.0),
        ("svc-012", "OAuth2-Token-Issuer", ServiceTier.MIDDLEWARE, 22.0, 350.0, 35, 320.0, 30.0),
        ("svc-013", "User-Identity-Directory", ServiceTier.MIDDLEWARE, 26.0, 420.0, 40, 420.0, 34.0),
        ("svc-014", "Session-State-Manager", ServiceTier.MIDDLEWARE, 18.0, 290.0, 30, 780.0, 19.0),
        ("svc-015", "Role-RBAC-Authorizer", ServiceTier.MIDDLEWARE, 16.0, 260.0, 25, 600.0, 21.0),

        # CORE COMMERCE & ORDER FLOW (16-30)
        ("svc-016", "Checkout-API-Service", ServiceTier.ORDER_PAYMENT, 35.0, 680.0, 45, 380.0, 48.0),
        ("svc-017", "Order-Orchestrator-Saga", ServiceTier.ORDER_PAYMENT, 40.0, 750.0, 50, 320.0, 55.0),
        ("svc-018", "Cart-State-Service", ServiceTier.ORDER_PAYMENT, 28.0, 450.0, 40, 540.0, 26.0),
        ("svc-019", "Payment-Gateway-Router", ServiceTier.ORDER_PAYMENT, 32.0, 580.0, 45, 290.0, 60.0),
        ("svc-020", "Payment-Settlement-Core", ServiceTier.ORDER_PAYMENT, 30.0, 620.0, 45, 240.0, 65.0),
        ("svc-021", "Payment-Audit-Trail", ServiceTier.ORDER_PAYMENT, 18.0, 340.0, 25, 180.0, 35.0),
        ("svc-022", "Fraud-Detection-Rules", ServiceTier.ORDER_PAYMENT, 42.0, 820.0, 35, 310.0, 58.0),
        ("svc-023", "Dynamic-Pricing-Engine", ServiceTier.ORDER_PAYMENT, 25.0, 430.0, 30, 410.0, 40.0),
        ("svc-024", "Tax-Jurisdiction-Calculator", ServiceTier.ORDER_PAYMENT, 20.0, 360.0, 25, 320.0, 32.0),
        ("svc-025", "Currency-Exchange-Service", ServiceTier.ORDER_PAYMENT, 14.0, 250.0, 20, 220.0, 24.0),
        ("svc-026", "Promo-Coupon-Validator", ServiceTier.ORDER_PAYMENT, 19.0, 310.0, 30, 280.0, 28.0),
        ("svc-027", "Customer-Loyalty-Points", ServiceTier.ORDER_PAYMENT, 17.0, 290.0, 25, 190.0, 30.0),
        ("svc-028", "Gift-Card-Manager", ServiceTier.ORDER_PAYMENT, 15.0, 270.0, 20, 110.0, 29.0),
        ("svc-029", "Digital-Invoice-Generator", ServiceTier.ORDER_PAYMENT, 24.0, 410.0, 25, 140.0, 42.0),
        ("svc-030", "Customer-Receipt-Relay", ServiceTier.ORDER_PAYMENT, 16.0, 280.0, 20, 130.0, 33.0),

        # CATALOG, INVENTORY & SEARCH (31-45)
        ("svc-031", "Product-Catalog-Reader", ServiceTier.MIDDLEWARE, 34.0, 580.0, 45, 620.0, 36.0),
        ("svc-032", "Product-Category-Tree", ServiceTier.MIDDLEWARE, 22.0, 370.0, 30, 450.0, 27.0),
        ("svc-033", "Search-Query-Executor", ServiceTier.MIDDLEWARE, 45.0, 890.0, 50, 490.0, 62.0),
        ("svc-034", "Elasticsearch-Cluster-Proxy", ServiceTier.MIDDLEWARE, 40.0, 810.0, 50, 510.0, 52.0),
        ("svc-035", "Search-Autocomplete-Trie", ServiceTier.MIDDLEWARE, 24.0, 440.0, 30, 720.0, 18.0),
        ("svc-036", "Catalog-Facet-Filter", ServiceTier.MIDDLEWARE, 28.0, 490.0, 35, 410.0, 31.0),
        ("svc-037", "Product-Review-Collector", ServiceTier.MIDDLEWARE, 20.0, 350.0, 25, 230.0, 38.0),
        ("svc-038", "Review-Rating-Aggregator", ServiceTier.MIDDLEWARE, 18.0, 320.0, 20, 190.0, 34.0),
        ("svc-039", "Product-Media-CDN-Proxy", ServiceTier.MIDDLEWARE, 26.0, 460.0, 30, 580.0, 22.0),
        ("svc-040", "Realtime-Inventory-Lookup", ServiceTier.MIDDLEWARE, 32.0, 540.0, 40, 510.0, 39.0),
        ("svc-041", "Warehouse-Stock-Manager", ServiceTier.MIDDLEWARE, 27.0, 460.0, 35, 280.0, 41.0),
        ("svc-042", "Inventory-Stock-Reservation", ServiceTier.MIDDLEWARE, 36.0, 610.0, 45, 340.0, 49.0),
        ("svc-043", "Merchant-Seller-Directory", ServiceTier.MIDDLEWARE, 19.0, 330.0, 25, 170.0, 29.0),
        ("svc-044", "Product-Recommendation-Feed", ServiceTier.MIDDLEWARE, 38.0, 720.0, 35, 380.0, 56.0),
        ("svc-045", "User-Personalization-Engine", ServiceTier.MIDDLEWARE, 35.0, 690.0, 35, 360.0, 54.0),

        # FULFILLMENT & SHIPPING (46-55)
        ("svc-046", "Shipping-Coordinator", ServiceTier.MIDDLEWARE, 22.0, 380.0, 30, 180.0, 44.0),
        ("svc-047", "Carrier-Partner-Gateway", ServiceTier.MIDDLEWARE, 24.0, 410.0, 30, 160.0, 72.0),
        ("svc-048", "Package-Tracking-Engine", ServiceTier.MIDDLEWARE, 20.0, 350.0, 25, 240.0, 33.0),
        ("svc-049", "Dispatch-Route-Planner", ServiceTier.MIDDLEWARE, 29.0, 520.0, 25, 120.0, 48.0),
        ("svc-050", "Barcode-Scanner-Intake", ServiceTier.MIDDLEWARE, 15.0, 260.0, 20, 95.0, 25.0),
        ("svc-051", "Return-RMA-Processor", ServiceTier.MIDDLEWARE, 18.0, 310.0, 20, 80.0, 37.0),
        ("svc-052", "Delivery-Fleet-Telemetry", ServiceTier.MIDDLEWARE, 23.0, 400.0, 25, 210.0, 28.0),
        ("svc-053", "Cross-Border-Customs", ServiceTier.MIDDLEWARE, 16.0, 290.0, 20, 65.0, 45.0),
        ("svc-054", "Postal-Address-Validator", ServiceTier.MIDDLEWARE, 17.0, 300.0, 25, 290.0, 31.0),
        ("svc-055", "Geo-Coordinates-Lookup", ServiceTier.MIDDLEWARE, 19.0, 320.0, 25, 330.0, 26.0),

        # NOTIFICATION & EVENT STREAMING (56-65)
        ("svc-056", "Notification-Dispatcher", ServiceTier.MESSAGING, 25.0, 420.0, 35, 350.0, 38.0),
        ("svc-057", "FCM-Push-Notifier", ServiceTier.MESSAGING, 22.0, 380.0, 30, 290.0, 42.0),
        ("svc-058", "SMS-Telephony-Gateway", ServiceTier.MESSAGING, 18.0, 310.0, 25, 170.0, 55.0),
        ("svc-059", "SMTP-Email-Relay-Worker", ServiceTier.MESSAGING, 20.0, 360.0, 25, 210.0, 48.0),
        ("svc-060", "In-App-Message-WebSocket", ServiceTier.MESSAGING, 31.0, 540.0, 35, 620.0, 24.0),
        ("svc-061", "Kafka-Ingress-Producer", ServiceTier.MESSAGING, 34.0, 600.0, 45, 850.0, 20.0),
        ("svc-062", "Kafka-Consumer-Dispatcher", ServiceTier.MESSAGING, 32.0, 580.0, 40, 810.0, 22.0),
        ("svc-063", "Enterprise-Audit-Logger", ServiceTier.MESSAGING, 21.0, 380.0, 30, 450.0, 25.0),
        ("svc-064", "Partner-Webhook-Invoker", ServiceTier.MESSAGING, 23.0, 390.0, 25, 140.0, 68.0),
        ("svc-065", "Incident-Alert-Broadcaster", ServiceTier.MESSAGING, 15.0, 270.0, 20, 80.0, 30.0),

        # DATABASE & DATA STORE ADAPTERS (66-85)
        # Note: svc-066 Order-DB-Adapter is the featured primary root-cause service from the synopsis
        ("svc-066", "Order-DB-Adapter", ServiceTier.DATABASE, 38.0, 720.0, 50, 410.0, 45.0),
        ("svc-067", "User-Account-DB-Proxy", ServiceTier.DATABASE, 30.0, 580.0, 45, 480.0, 38.0),
        ("svc-068", "Payment-Ledger-DB-Proxy", ServiceTier.DATABASE, 36.0, 690.0, 45, 290.0, 52.0),
        ("svc-069", "Catalog-Relational-DB", ServiceTier.DATABASE, 35.0, 660.0, 50, 580.0, 36.0),
        ("svc-070", "Inventory-Postgres-Proxy", ServiceTier.DATABASE, 34.0, 640.0, 45, 460.0, 41.0),
        ("svc-071", "Cart-Redis-Cluster-Proxy", ServiceTier.DATABASE, 20.0, 420.0, 60, 750.0, 12.0),
        ("svc-072", "Session-Redis-Cache-Proxy", ServiceTier.DATABASE, 18.0, 390.0, 60, 820.0, 10.0),
        ("svc-073", "Auth-Credentials-DB-Proxy", ServiceTier.DATABASE, 26.0, 490.0, 40, 450.0, 28.0),
        ("svc-074", "Shipping-Logistics-DB", ServiceTier.DATABASE, 24.0, 460.0, 35, 210.0, 39.0),
        ("svc-075", "Analytics-ClickHouse-Proxy", ServiceTier.DATABASE, 42.0, 880.0, 35, 160.0, 65.0),
        ("svc-076", "Reporting-Replica-Pool", ServiceTier.DATABASE, 29.0, 540.0, 35, 140.0, 58.0),
        ("svc-077", "Search-Elasticsearch-Nodes", ServiceTier.DATABASE, 44.0, 920.0, 45, 520.0, 48.0),
        ("svc-078", "Audit-Cassandra-Cluster", ServiceTier.DATABASE, 33.0, 680.0, 40, 380.0, 35.0),
        ("svc-079", "Product-Metadata-Store", ServiceTier.DATABASE, 28.0, 510.0, 35, 340.0, 32.0),
        ("svc-080", "Token-Cache-Memcached", ServiceTier.DATABASE, 16.0, 320.0, 60, 890.0, 8.0),
        ("svc-081", "Cluster-ZooKeeper-Proxy", ServiceTier.DATABASE, 19.0, 350.0, 30, 260.0, 15.0),
        ("svc-082", "Secret-Vault-HSM-Proxy", ServiceTier.DATABASE, 22.0, 380.0, 30, 310.0, 22.0),
        ("svc-083", "Read-Replica-Pool-Alpha", ServiceTier.DATABASE, 31.0, 590.0, 45, 420.0, 34.0),
        ("svc-084", "Read-Replica-Pool-Beta", ServiceTier.DATABASE, 30.0, 570.0, 45, 390.0, 36.0),
        ("svc-085", "Telemetry-Prometheus-Store", ServiceTier.DATABASE, 37.0, 710.0, 35, 270.0, 28.0),

        # ANALYTICS & PLATFORM CONTROLLERS (86-100)
        ("svc-086", "Metrics-Stream-Aggregator", ServiceTier.ANALYTICS, 28.0, 530.0, 30, 340.0, 30.0),
        ("svc-087", "Clickstream-Ingestor", ServiceTier.ANALYTICS, 32.0, 610.0, 35, 460.0, 26.0),
        ("svc-088", "ETL-Workflow-Coordinator", ServiceTier.ANALYTICS, 25.0, 480.0, 25, 95.0, 55.0),
        ("svc-089", "Spark-Job-Scheduler", ServiceTier.ANALYTICS, 22.0, 430.0, 20, 60.0, 65.0),
        ("svc-090", "ML-Recommendation-Inference", ServiceTier.ANALYTICS, 48.0, 960.0, 35, 280.0, 70.0),
        ("svc-091", "AB-Experimentation-Router", ServiceTier.ANALYTICS, 21.0, 370.0, 25, 480.0, 21.0),
        ("svc-092", "Feature-Store-Reader", ServiceTier.ANALYTICS, 30.0, 560.0, 35, 310.0, 33.0),
        ("svc-093", "User-Churn-Prediction-Worker", ServiceTier.ANALYTICS, 26.0, 490.0, 20, 85.0, 62.0),
        ("svc-094", "Fraud-ML-Scoring-Worker", ServiceTier.ANALYTICS, 44.0, 890.0, 30, 230.0, 68.0),
        ("svc-095", "FinOps-Cost-Profiler", ServiceTier.ANALYTICS, 18.0, 330.0, 20, 50.0, 40.0),
        ("svc-096", "Cluster-Synthetic-Prober", ServiceTier.ANALYTICS, 15.0, 280.0, 20, 110.0, 25.0),
        ("svc-097", "Chaos-Mesh-Injector-Bridge", ServiceTier.ANALYTICS, 14.0, 260.0, 15, 40.0, 30.0),
        ("svc-098", "OTel-Trace-Collector-Daemon", ServiceTier.ANALYTICS, 36.0, 680.0, 40, 920.0, 20.0),
        ("svc-099", "FluentBit-Log-Aggregator", ServiceTier.ANALYTICS, 32.0, 620.0, 35, 870.0, 22.0),
        ("svc-100", "Autonomous-Self-Healing-Operator", ServiceTier.ANALYTICS, 28.0, 520.0, 30, 180.0, 32.0),
    ]

    for idx, (sid, sname, stier, cpu, mem, pool_max, rps, p99) in enumerate(service_definitions):
        assigned_host = k8s_nodes[idx % len(k8s_nodes)]
        nodes[sid] = ServiceNode(
            id=sid,
            name=sname,
            tier=stier,
            host_node=assigned_host,
            replicas=3 if stier not in [ServiceTier.FRONTEND, ServiceTier.GATEWAY] else 5,
            cpu_percent=cpu,
            memory_mb=mem,
            memory_limit_mb=mem * 2.5,
            db_pool_active=max(3, int(pool_max * 0.3)),
            db_pool_max=pool_max,
            db_idle_timeout_sec=30,
            p95_latency_ms=p99 * 0.65,
            p99_latency_ms=p99,
            request_rate_rps=rps,
            error_rate=0.0008,
            status=ServiceStatus.HEALTHY,
            active_fault=FaultType.NONE,
            labels={"app.kubernetes.io/name": sname, "env": "production", "zone": "us-east-1a"}
        )

    # Directed Call Edges (Topology connections representing live RPC & service dependencies)
    call_pairs = [
        # Ingress / Frontends to Gateways
        ("svc-001", "svc-006"), ("svc-001", "svc-008"), ("svc-002", "svc-007"), ("svc-003", "svc-008"),
        ("svc-004", "svc-006"), ("svc-005", "svc-008"), ("svc-008", "svc-010"), ("svc-010", "svc-006"),
        ("svc-010", "svc-007"), ("svc-006", "svc-009"),

        # Gateways to Auth & Middleware
        ("svc-006", "svc-011"), ("svc-007", "svc-011"), ("svc-011", "svc-014"), ("svc-011", "svc-015"),
        ("svc-012", "svc-013"), ("svc-013", "svc-073"), ("svc-014", "svc-072"), ("svc-015", "svc-080"),

        # Gateway to Core Commerce (Crucial checkout flow)
        ("svc-006", "svc-016"),  # Gateway -> Checkout-API
        ("svc-006", "svc-018"),  # Gateway -> Cart-State-Service
        ("svc-007", "svc-016"),
        ("svc-007", "svc-018"),
        ("svc-016", "svc-017"),  # Checkout-API -> Order-Orchestrator-Saga
        ("svc-016", "svc-018"),  # Checkout-API -> Cart
        ("svc-016", "svc-023"),  # Checkout-API -> Pricing
        ("svc-016", "svc-024"),  # Checkout-API -> Tax
        ("svc-016", "svc-026"),  # Checkout-API -> Promo-Coupon

        # Order Orchestrator Saga to Payments, Inventory & Order-DB
        ("svc-017", "svc-019"),  # Order-Orchestrator -> Payment-Gateway
        ("svc-017", "svc-042"),  # Order-Orchestrator -> Stock-Reservation
        ("svc-017", "svc-066"),  # Order-Orchestrator -> Order-DB-Adapter (PRIMARY ROOT CAUSE TARGET)
        ("svc-017", "svc-027"),  # Order-Orchestrator -> Loyalty-Points
        ("svc-017", "svc-029"),  # Order-Orchestrator -> Invoice-Generator
        ("svc-017", "svc-056"),  # Order-Orchestrator -> Notification-Dispatcher

        # Payment Flow
        ("svc-019", "svc-020"),  # Payment-Gateway -> Settlement-Core
        ("svc-019", "svc-022"),  # Payment-Gateway -> Fraud-Detection
        ("svc-020", "svc-068"),  # Settlement -> Payment-Ledger-DB
        ("svc-020", "svc-021"),  # Settlement -> Payment-Audit
        ("svc-021", "svc-078"),  # Audit -> Cassandra
        ("svc-022", "svc-094"),  # Fraud -> Fraud-ML-Worker

        # Cart to Storage
        ("svc-018", "svc-071"),  # Cart -> Redis-Cluster

        # Order-DB-Adapter to Storage & Read Replicas
        ("svc-066", "svc-083"),  # Order-DB-Adapter -> Read-Replica-Alpha
        ("svc-066", "svc-084"),  # Order-DB-Adapter -> Read-Replica-Beta

        # Catalog & Search
        ("svc-006", "svc-031"), ("svc-007", "svc-031"),
        ("svc-031", "svc-032"), ("svc-031", "svc-069"), ("svc-031", "svc-040"),
        ("svc-006", "svc-033"), ("svc-033", "svc-034"), ("svc-034", "svc-077"),
        ("svc-033", "svc-035"), ("svc-033", "svc-036"),
        ("svc-031", "svc-037"), ("svc-037", "svc-038"), ("svc-037", "svc-079"),
        ("svc-031", "svc-044"), ("svc-044", "svc-045"), ("svc-045", "svc-090"),

        # Inventory & Warehouse
        ("svc-040", "svc-070"), ("svc-041", "svc-070"), ("svc-042", "svc-070"),
        ("svc-042", "svc-041"),

        # Fulfillment & Shipping
        ("svc-017", "svc-046"), ("svc-046", "svc-047"), ("svc-046", "svc-074"),
        ("svc-046", "svc-048"), ("svc-046", "svc-049"), ("svc-048", "svc-052"),
        ("svc-046", "svc-054"), ("svc-054", "svc-055"),

        # Notifications & Messaging
        ("svc-056", "svc-057"), ("svc-056", "svc-058"), ("svc-056", "svc-059"),
        ("svc-056", "svc-060"), ("svc-056", "svc-061"), ("svc-061", "svc-062"),
        ("svc-062", "svc-063"), ("svc-062", "svc-064"),

        # Analytics, ML & Telemetry
        ("svc-006", "svc-087"), ("svc-087", "svc-061"), ("svc-088", "svc-089"),
        ("svc-088", "svc-075"), ("svc-090", "svc-092"), ("svc-091", "svc-044"),
        ("svc-096", "svc-008"), ("svc-098", "svc-085"), ("svc-099", "svc-078"),
        ("svc-100", "svc-098")
    ]

    for src, dst in call_pairs:
        if src in nodes and dst in nodes:
            src_node = nodes[src]
            dst_node = nodes[dst]
            edges.append(CallEdge(
                source=src,
                target=dst,
                edge_type="RPC_CALL",
                request_rate_rps=min(src_node.request_rate_rps, dst_node.request_rate_rps * 0.8),
                p95_latency_ms=dst_node.p95_latency_ms * 0.8,
                p99_latency_ms=dst_node.p99_latency_ms * 0.9,
                error_rate=0.0005,
                circuit_breaker_open=False
            ))

    return nodes, edges
