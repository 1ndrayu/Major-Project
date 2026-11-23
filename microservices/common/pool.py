"""
HikariCP Database Connection Pool Emulator
Simulates production JDBC/HikariCP pool dynamics, thread acquisition contention,
connection leak detection, and dynamic runtime pool resizing.
"""

import time
import asyncio
from typing import Dict, Any, Optional


class HikariPoolExhaustedException(Exception):
    pass


class HikariConnectionPool:
    """
    Emulates the high-performance HikariCP JDBC connection pool.
    """
    def __init__(
        self,
        pool_name: str = "HikariPool-1",
        maximum_pool_size: int = 50,
        connection_timeout_ms: int = 3000,
        idle_timeout_ms: int = 30000,
        leak_detection_threshold_ms: int = 0
    ):
        self.pool_name = pool_name
        self.maximum_pool_size = maximum_pool_size
        self.connection_timeout_ms = connection_timeout_ms
        self.idle_timeout_ms = idle_timeout_ms
        self.leak_detection_threshold_ms = leak_detection_threshold_ms

        self.active_connections = 0
        self.leased_connections: Dict[str, float] = {}
        self.is_leaking = False
        self._lock = asyncio.Lock()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "pool_name": self.pool_name,
            "active_connections": self.active_connections,
            "maximum_pool_size": self.maximum_pool_size,
            "saturation_ratio": round(self.active_connections / max(1, self.maximum_pool_size), 3),
            "idle_connections": max(0, self.maximum_pool_size - self.active_connections),
            "threads_awaiting_connection": max(0, self.active_connections - self.maximum_pool_size + 5) if self.is_leaking else 0,
            "leak_detection_threshold_ms": self.leak_detection_threshold_ms,
            "is_exhausted": self.active_connections >= self.maximum_pool_size
        }

    async def acquire_connection(self, lease_id: str) -> bool:
        """Attempts to acquire a database connection from the pool."""
        if self.is_leaking:
            # Simulate high thread queue contention and timeout
            await asyncio.sleep(min(1.2, self.connection_timeout_ms / 1000.0))
            if self.active_connections >= self.maximum_pool_size:
                raise HikariPoolExhaustedException(
                    f"{self.pool_name} - Connection is not available, request timed out after {self.connection_timeout_ms}ms "
                    f"(total={self.maximum_pool_size}, active={self.active_connections}, waiting=82)"
                )

        async with self._lock:
            if self.active_connections >= self.maximum_pool_size:
                raise HikariPoolExhaustedException(
                    f"{self.pool_name} - Connection pool exhausted ({self.active_connections}/{self.maximum_pool_size})"
                )
            self.active_connections += 1
            self.leased_connections[lease_id] = time.time()
            return True

    async def release_connection(self, lease_id: str):
        """Releases the connection back to the pool."""
        async with self._lock:
            if lease_id in self.leased_connections:
                del self.leased_connections[lease_id]
                self.active_connections = max(0, self.active_connections - 1)

    def trigger_leak_simulation(self):
        """Simulates unclosed connection leak saturating all slots."""
        self.is_leaking = True
        self.active_connections = self.maximum_pool_size

    def clear_leak_simulation(self):
        """Clears connection leak and returns to healthy state."""
        self.is_leaking = False
        self.active_connections = max(3, int(self.maximum_pool_size * 0.3))
        self.leased_connections.clear()

    def resize_pool(self, new_max_connections: int, new_leak_threshold_ms: int = 5000):
        """Dynamic runtime pool resizing via Kubernetes ConfigMap reload."""
        self.maximum_pool_size = new_max_connections
        self.leak_detection_threshold_ms = new_leak_threshold_ms
        self.is_leaking = False
        self.active_connections = min(self.active_connections, int(new_max_connections * 0.35))
