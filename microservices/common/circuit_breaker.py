"""
Resilience4j / Envoy Circuit Breaker Pattern
Monitors failure rates across downstream dependencies and trips circuit to prevent cascading failures.
"""

import time
from enum import Enum
from typing import Dict, Any


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """
    Implements sliding-window circuit breaker with failure-rate trip threshold.
    """
    def __init__(
        self,
        failure_rate_threshold_pct: float = 50.0,
        wait_duration_in_open_state_sec: float = 10.0,
        sliding_window_size: int = 20
    ):
        self.threshold = failure_rate_threshold_pct
        self.open_duration = wait_duration_in_open_state_sec
        self.window_size = sliding_window_size

        self.state = CircuitState.CLOSED
        self.history = []  # boolean: True=success, False=failure
        self.last_state_change = time.time()

    def record_result(self, success: bool):
        self.history.append(success)
        if len(self.history) > self.window_size:
            self.history.pop(0)

        if self.state == CircuitState.OPEN:
            if time.time() - self.last_state_change > self.open_duration:
                self.state = CircuitState.HALF_OPEN
                self.last_state_change = time.time()

        elif self.state in [CircuitState.CLOSED, CircuitState.HALF_OPEN]:
            if len(self.history) >= 10:
                failure_count = sum(1 for res in self.history if not res)
                failure_pct = (failure_count / len(self.history)) * 100.0
                if failure_pct >= self.threshold:
                    self.state = CircuitState.OPEN
                    self.last_state_change = time.time()
                elif self.state == CircuitState.HALF_OPEN and failure_pct < self.threshold:
                    self.state = CircuitState.CLOSED
                    self.last_state_change = time.time()

    def is_call_permitted(self) -> bool:
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_state_change > self.open_duration:
                self.state = CircuitState.HALF_OPEN
                self.last_state_change = time.time()
                return True
            return False
        return True

    def get_status(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "window_size": len(self.history),
            "is_permitted": self.is_call_permitted()
        }
