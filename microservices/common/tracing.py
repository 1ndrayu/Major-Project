"""
OpenTelemetry W3C TraceContext Propagation (Pillar 1)
Generates and parses W3C TraceContext headers (traceparent: 00-{trace_id}-{span_id}-{flags})
to maintain end-to-end distributed span waterfalls across microservice RPC hops.
"""

import os
import time
import uuid
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class TraceContext:
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    sampled: bool = True

    def to_header(self) -> str:
        flags = "01" if self.sampled else "00"
        return f"00-{self.trace_id}-{self.span_id}-{flags}"


def generate_trace_id() -> str:
    return uuid.uuid4().hex


def generate_span_id() -> str:
    return uuid.uuid4().hex[:16]


def extract_w3c_trace(headers: Dict[str, str]) -> TraceContext:
    """Extracts W3C traceparent header or creates a new root trace."""
    raw = headers.get("traceparent") or headers.get("Traceparent") or ""
    parts = raw.split("-")
    if len(parts) == 4 and parts[0] == "00":
        parent_trace_id = parts[1]
        parent_span_id = parts[2]
        sampled = parts[3] == "01"
        return TraceContext(
            trace_id=parent_trace_id,
            span_id=generate_span_id(),
            parent_span_id=parent_span_id,
            sampled=sampled
        )
    # Generate new root trace
    return TraceContext(
        trace_id=generate_trace_id(),
        span_id=generate_span_id(),
        parent_span_id=None,
        sampled=True
    )


def inject_w3c_trace(ctx: TraceContext, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Injects W3C traceparent header into outbound RPC request headers."""
    if headers is None:
        headers = {}
    headers["traceparent"] = ctx.to_header()
    return headers
