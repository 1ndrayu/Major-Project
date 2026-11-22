"""
Multimodal Anomaly Detection Module (Pillar 2)
Fuses LSTM-VAE multivariate metric drift with LogBERT log sequence patterns.
"""

import time
import numpy as np
from typing import Dict, List, Optional
from self_healing_core.models import (
    TelemetryFrame, AnomalyScore, AnomalyEvent, FaultType
)
from .lstm_vae import MultivariateAnomalyDetector
from .log_detector import LogPatternDetector


class MultimodalAnomalyDetector:
    """
    Unified multimodal anomaly detection engine.
    Scans the live telemetry frame, scores each service using LSTM-VAE and log analysis,
    and constructs an AnomalyEvent if anomaly score z > 3.2 sigma.
    """
    def __init__(self, threshold_sigma: float = 3.2):
        self.metric_detector = MultivariateAnomalyDetector(input_dim=6, threshold_sigma=threshold_sigma)
        self.log_detector = LogPatternDetector()
        self.threshold_sigma = threshold_sigma

    def evaluate_frame(self, frame: TelemetryFrame) -> Optional[AnomalyEvent]:
        """
        Evaluates a TelemetryFrame. Returns an AnomalyEvent if any service
        violates the threshold, otherwise returns None.
        """
        log_analysis = self.log_detector.analyze_logs(frame.logs)
        anomaly_scores: Dict[str, AnomalyScore] = {}
        anomalous_services: List[str] = []
        max_z = 0.0
        primary_service = ""

        for sid, node in frame.nodes.items():
            pool_sat = node.db_pool_active / max(1, node.db_pool_max)
            mem_sat = node.memory_mb / max(1.0, node.memory_limit_mb)
            features = np.array([
                node.cpu_percent / 100.0,
                mem_sat,
                pool_sat,
                min(1.0, node.p99_latency_ms / 2000.0),
                min(1.0, node.error_rate * 5.0),
                min(1.0, node.request_rate_rps / 1000.0)
            ], dtype=np.float32)

            z_score, deviations = self.metric_detector.compute_anomaly_score(features)
            has_log_anom, patterns, _ = log_analysis.get(sid, (False, [], FaultType.NONE))

            if has_log_anom:
                z_score += 2.0  # Boost confidence on log exception match

            is_anom = (z_score >= self.threshold_sigma) or has_log_anom

            anomaly_scores[sid] = AnomalyScore(
                service_id=sid,
                z_score=round(z_score, 2),
                metric_deviations=deviations,
                log_anomaly_detected=has_log_anom,
                log_patterns=patterns,
                is_anomalous=is_anom
            )

            if is_anom:
                anomalous_services.append(sid)
                if z_score > max_z:
                    max_z = z_score
                    primary_service = sid

        if not anomalous_services:
            return None

        # Build list of evidence and signals
        evidence = []
        metric_signals = {}
        for sid in anomalous_services:
            score_obj = anomaly_scores[sid]
            metric_signals[f"{sid}_z_score"] = score_obj.z_score
            for p in score_obj.log_patterns:
                evidence.append(f"[{sid}] {p}")

        return AnomalyEvent(
            event_id=f"anom-{int(time.time() * 1000)}",
            timestamp=time.time(),
            primary_anomalous_service=primary_service,
            affected_services=anomalous_services,
            max_z_score=round(max_z, 2),
            metric_signals=metric_signals,
            log_evidence=evidence[:10],
            anomaly_scores=anomaly_scores
        )


__all__ = ["MultimodalAnomalyDetector", "MultivariateAnomalyDetector", "LogPatternDetector"]
