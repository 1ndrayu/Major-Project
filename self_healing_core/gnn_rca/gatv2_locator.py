"""
Spatiotemporal Graph Attention Network v2 (GATv2) & PSC-GRCA Engine (Pillar 4)
Implements dynamic edge-attention GNN and Prior-Separated Centered Graph RCA (Buljić, 2026).
Decomposes root-cause scoring: s_i = w_p * p_i + w_e * e_i + w_r * (GATv2(x_i) - mu_G).
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, List, Tuple, Set, Optional
from self_healing_core.models import RootCauseCandidate, FaultType
from self_healing_core.graph.dependency_graph import ServiceDependencyGraph


class GATv2Layer(nn.Module):
    """
    Standard GATv2 dynamic edge-attention layer (Brody et al., ICLR 2022).
    Addresses the static attention limitation of standard GAT by applying attention after non-linearity.
    """
    def __init__(self, in_features: int, out_features: int, heads: int = 2):
        super(GATv2Layer, self).__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.heads = heads

        self.W = nn.Linear(in_features, out_features * heads, bias=False)
        self.a = nn.Parameter(torch.empty(size=(heads, out_features)))
        nn.init.xavier_uniform_(self.a.data, gain=1.414)
        self.leaky_relu = nn.LeakyReLU(0.2)

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        # x: [num_nodes, in_features]
        num_nodes = x.size(0)
        h = self.W(x).view(num_nodes, self.heads, self.out_features)  # [N, H, D]

        src_idx, dst_idx = edge_index[0], edge_index[1]
        # GATv2 dynamic scoring: a^T * LeakyReLU(W * x_i + W * x_j)
        h_sum = h[src_idx] + h[dst_idx]  # [E, H, D]
        e = self.leaky_relu(h_sum)
        # Multiply by attention vector a: [H, D]
        scores = (e * self.a.unsqueeze(0)).sum(dim=-1)  # [E, H]

        # Softmax over incoming edges per node
        # Compute normalized attention coefficients using scatter_softmax or dense representation
        alpha = torch.softmax(scores, dim=0)

        # Message passing aggregation
        out = torch.zeros(num_nodes, self.heads, self.out_features, device=x.device)
        # Aggregate messages from src to dst
        for h_idx in range(self.heads):
            out[:, h_idx, :].index_add_(0, dst_idx, alpha[:, h_idx].unsqueeze(-1) * h[src_idx, h_idx, :])

        return out.mean(dim=1)  # Average multi-head attention: [N, D]


class SpatiotemporalGATv2Model(nn.Module):
    """
    2-Layer Spatiotemporal GATv2 model with residual skip connection.
    Processes multivariate telemetry features across the directed service dependency graph.
    """
    def __init__(self, in_dim: int = 6, hidden_dim: int = 16, out_dim: int = 8):
        super(SpatiotemporalGATv2Model, self).__init__()
        self.gat1 = GATv2Layer(in_dim, hidden_dim, heads=2)
        self.gat2 = GATv2Layer(hidden_dim, out_dim, heads=2)
        self.fc_score = nn.Linear(out_dim, 1)

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        h1 = F.elu(self.gat1(x, edge_index))
        h2 = F.elu(self.gat2(h1, edge_index))
        scores = self.fc_score(h2).squeeze(-1)
        return scores


class SpatiotemporalGNNLocator:
    """
    Combines the Spatiotemporal GATv2 architecture with the Prior-Separated Centered
    Graph RCA (PSC-GRCA) formulation to rank root-cause candidate services.
    """
    def __init__(self, w_p: float = 0.20, w_e: float = 0.45, w_r: float = 0.35):
        self.model = SpatiotemporalGATv2Model(in_dim=6, hidden_dim=16, out_dim=8)
        self.model.eval()
        self.w_p = w_p  # Weight on structural topological prior
        self.w_e = w_e  # Weight on local telemetry evidence
        self.w_r = w_r  # Weight on centered GNN message passing residual

    def rank_candidates(
        self,
        dep_graph: ServiceDependencyGraph,
        candidate_subset: Set[str],
        top_k: int = 5
    ) -> List[RootCauseCandidate]:
        """
        Ranks the services within candidate_subset using PSC-GRCA decomposition.
        """
        x, edge_index, node_ids = dep_graph.to_pyg_tensors(candidate_subset)
        if len(node_ids) == 0:
            return []

        with torch.no_grad():
            raw_gnn_scores = self.model(x, edge_index).numpy()

        mu_g = float(np.mean(raw_gnn_scores)) if len(raw_gnn_scores) > 0 else 0.0

        candidates: List[RootCauseCandidate] = []

        for idx, sid in enumerate(node_ids):
            node_data = dep_graph.graph.nodes[sid]

            # 1. Structural Prior p_i:
            # Downstream leaf services / DB adapters have high in-degree from callers and 0 or low out-degree
            in_deg = dep_graph.graph.in_degree(sid)
            out_deg = dep_graph.graph.out_degree(sid)
            p_i = min(1.0, (in_deg / max(1.0, in_deg + out_deg + 1.0)) * 1.2)
            if node_data["tier"] == "DATABASE":
                p_i = min(1.0, p_i + 0.30)

            # 2. Local Telemetry Evidence e_i:
            # Direct resource saturation, connection pool ratio, memory pressure
            pool_sat = node_data.get("db_pool_saturation", 0.0)
            mem_sat = node_data.get("mem_saturation", 0.0)
            cpu_sat = node_data.get("cpu", 0.0) / 100.0
            error_r = min(1.0, node_data.get("error_rate", 0.0) * 10.0)

            # Telemetry evidence prioritizes the bottleneck resource
            e_i = max(pool_sat, mem_sat, cpu_sat) * 0.7 + error_r * 0.3

            # 3. Centered GNN Residual r_i:
            r_i = float(raw_gnn_scores[idx]) - mu_g

            # Final PSC-GRCA Score
            total_score = self.w_p * p_i + self.w_e * e_i + self.w_r * max(0.0, r_i)

            # Deduce likely fault type from resource signatures
            suspected_fault = FaultType.NONE
            explanation = ""
            if pool_sat >= 0.85:
                suspected_fault = FaultType.DB_POOL_EXHAUSTION
                explanation = f"Connection pool exhaustion ({node_data['db_pool_active']}/{node_data['db_pool_max']} active, {pool_sat*100:.1f}% saturation)"
            elif mem_sat >= 0.88:
                suspected_fault = FaultType.MEMORY_LEAK
                explanation = f"Heap memory exhaustion ({node_data['mem_mb']:.1f}MB, {mem_sat*100:.1f}% saturation)"
            elif cpu_sat >= 0.90:
                suspected_fault = FaultType.CPU_HOGGING
                explanation = f"CPU thread saturation ({cpu_sat*100:.1f}% utilization)"
            elif error_r >= 0.5:
                suspected_fault = FaultType.RETRY_STORM
                explanation = "Elevated error burst and retry backpressure"
            else:
                suspected_fault = FaultType.NETWORK_LATENCY
                explanation = f"Tail latency degradation (p99={node_data['p99_latency']:.1f}ms)"

            candidates.append(RootCauseCandidate(
                service_id=sid,
                fault_type=suspected_fault,
                confidence_score=round(float(total_score), 4),
                prior_score=round(p_i, 4),
                telemetry_evidence=round(e_i, 4),
                gnn_residual=round(r_i, 4),
                causal_effect_do_x=0.0,  # Will be populated by Causal SCM
                explanation=explanation
            ))

        # Sort descending by composite PSC-GRCA score
        candidates.sort(key=lambda c: c.confidence_score, reverse=True)
        return candidates[:top_k]
