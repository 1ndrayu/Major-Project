"""
Log Semantic Sequence Analyzer & LogBERT Pattern Recognizer (Pillar 2)
Encodes and classifies structured log messages to identify signature exception patterns.
"""

import re
from typing import List, Dict, Tuple
from self_healing_core.models import LogEntry, FaultType


class LogPatternDetector:
    """
    LogBERT / Regex-based template semantic analyzer.
    Detects critical log signatures corresponding to infrastructure and application failures.
    """
    SIGNATURE_PATTERNS = [
        (FaultType.DB_POOL_EXHAUSTION, re.compile(r"HikariPool.*Connection is not available|connection timeout|pool exhausted|max_connections reached", re.I)),
        (FaultType.MEMORY_LEAK, re.compile(r"OutOfMemoryError|Java heap space|GC overhead limit|OOMKilled|memory limit exceeded", re.I)),
        (FaultType.CPU_HOGGING, re.compile(r"CPU utilization exceeded|thread starvation|high cpu load", re.I)),
        (FaultType.RETRY_STORM, re.compile(r"retry storm|circuit breaker approaching|DEADLINE_EXCEEDED|HTTP 504", re.I)),
        (FaultType.NETWORK_LATENCY, re.compile(r"socket timeout|connection reset|packet loss", re.I))
    ]

    def analyze_logs(self, logs: List[LogEntry]) -> Dict[str, Tuple[bool, List[str], FaultType]]:
        """
        Analyzes batch of logs grouped by service_id.
        Returns: {service_id: (has_anomaly, matching_patterns, suspected_fault)}
        """
        results: Dict[str, Tuple[bool, List[str], FaultType]] = {}

        for log in logs:
            sid = log.service_id
            if sid not in results:
                results[sid] = (False, [], FaultType.NONE)

            has_anom, patterns, suspected = results[sid]

            if log.level in ["ERROR", "CRITICAL"]:
                for fault_type, pattern in self.SIGNATURE_PATTERNS:
                    if pattern.search(log.message):
                        patterns.append(log.message[:120])
                        has_anom = True
                        if suspected == FaultType.NONE:
                            suspected = fault_type

            results[sid] = (has_anom, patterns, suspected)

        return results
