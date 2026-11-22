"""
Dynamic Service Dependency Graph (Pillar 3)
Builds and maintains real-time directed attributed graph G_t = (V_t, E_t, X_t, W_t).
Supports blast-radius subgraph extraction and tensor conversion for PyTorch GATv2.
"""

from typing import Dict, List, Optional, Set, Tuple
import networkx as nx
import numpy as np
import torch
from self_healing_core.models import ServiceNode, CallEdge, TelemetryFrame


class ServiceDependencyGraph:
    """
    Maintains the live directed graph combining RPC call edges and host co-location edges.
    Extracts anomalous subgraphs and exports graph matrices to PyTorch Geometric formats.
    """
    def __init__(self):
        self.graph = nx.DiGraph()
        self.node_id_to_idx: Dict[str, int] = {}
        self.idx_to_node_id: Dict[int, str] = {}

    def update_topology(self, frame: TelemetryFrame):
        """Reconstructs the NetworkX dynamic graph from the latest telemetry frame."""
        self.graph.clear()
        self.node_id_to_idx.clear()
        self.idx_to_node_id.clear()

        # Add Nodes with full telemetry features
        for idx, (sid, node) in enumerate(frame.nodes.items()):
            self.node_id_to_idx[sid] = idx
            self.idx_to_node_id[idx] = sid

            pool_sat = node.db_pool_active / max(1, node.db_pool_max)
            mem_sat = node.memory_mb / max(1.0, node.memory_limit_mb)

            self.graph.add_node(
                sid,
                name=node.name,
                tier=node.tier.value,
                host=node.host_node,
                cpu=node.cpu_percent,
                mem_mb=node.memory_mb,
                mem_saturation=mem_sat,
                db_pool_active=node.db_pool_active,
                db_pool_max=node.db_pool_max,
                db_pool_saturation=pool_sat,
                p95_latency=node.p95_latency_ms,
                p99_latency=node.p99_latency_ms,
                rps=node.request_rate_rps,
                error_rate=node.error_rate,
                status=node.status.value,
                feature_vec=[
                    node.cpu_percent / 100.0,
                    mem_sat,
                    pool_sat,
                    min(1.0, node.p99_latency_ms / 2000.0),
                    min(1.0, node.error_rate * 5.0),
                    min(1.0, node.request_rate_rps / 1000.0)
                ]
            )

        # Add Directed RPC Call Edges
        for edge in frame.edges:
            if edge.source in self.graph and edge.target in self.graph:
                self.graph.add_edge(
                    edge.source,
                    edge.target,
                    edge_type="RPC_CALL",
                    rps=edge.request_rate_rps,
                    p99_latency=edge.p99_latency_ms,
                    error_rate=edge.error_rate,
                    weight=edge.p99_latency_ms / 1000.0
                )

        # Add Node Co-location Edges (Microservices residing on the same Kubernetes worker node)
        hosts: Dict[str, List[str]] = {}
        for sid, node in frame.nodes.items():
            hosts.setdefault(node.host_node, []).append(sid)

        for host_name, service_list in hosts.items():
            for i in range(len(service_list)):
                for j in range(i + 1, min(i + 4, len(service_list))):
                    u, v = service_list[i], service_list[j]
                    if not self.graph.has_edge(u, v):
                        self.graph.add_edge(u, v, edge_type="HOST_COLOCATION", weight=0.1)

    def extract_anomalous_subgraph(self, anomalous_node_ids: List[str], hops: int = 2) -> Tuple[Set[str], List[Tuple[str, str]]]:
        """
        Extracts the k-hop neighborhood surrounding all detected anomalous services
        to bound the diagnostic blast radius.
        """
        subgraph_nodes: Set[str] = set()
        for nid in anomalous_node_ids:
            if nid in self.graph:
                subgraph_nodes.add(nid)
                # Upstream (predecessors) and downstream (successors)
                predecessors = nx.single_source_shortest_path_length(self.graph.reverse(copy=False), nid, cutoff=hops)
                successors = nx.single_source_shortest_path_length(self.graph, nid, cutoff=hops)
                subgraph_nodes.update(predecessors.keys())
                subgraph_nodes.update(successors.keys())

        subgraph_edges = []
        for u in subgraph_nodes:
            for v in self.graph.successors(u):
                if v in subgraph_nodes:
                    subgraph_edges.append((u, v))

        return subgraph_nodes, subgraph_edges

    def to_pyg_tensors(self, candidate_subset: Optional[Set[str]] = None) -> Tuple[torch.Tensor, torch.Tensor, List[str]]:
        """
        Converts the graph (or a candidate subgraph) into PyTorch Tensors for GATv2.
        Returns:
            x: Node feature tensor [num_nodes, d_v]
            edge_index: Graph connectivity tensor [2, num_edges]
            node_ids: List of node IDs corresponding to row indices
        """
        if candidate_subset is None:
            nodes_to_include = list(self.graph.nodes())
        else:
            nodes_to_include = [n for n in candidate_subset if n in self.graph]

        sub_id_to_idx = {nid: idx for idx, nid in enumerate(nodes_to_include)}

        features = []
        for nid in nodes_to_include:
            features.append(self.graph.nodes[nid]["feature_vec"])

        x = torch.tensor(features, dtype=torch.float32)

        edge_list_src = []
        edge_list_dst = []
        for u in nodes_to_include:
            for v in self.graph.successors(u):
                if v in sub_id_to_idx:
                    edge_list_src.append(sub_id_to_idx[u])
                    edge_list_dst.append(sub_id_to_idx[v])

        if len(edge_list_src) == 0:
            # Self-loops if no internal edges
            edge_list_src = list(range(len(nodes_to_include)))
            edge_list_dst = list(range(len(nodes_to_include)))

        edge_index = torch.tensor([edge_list_src, edge_list_dst], dtype=torch.long)
        return x, edge_index, nodes_to_include
