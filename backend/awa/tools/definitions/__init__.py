"""Aggregation of all 100 curated Alteryx tool definitions."""

from __future__ import annotations

from awa.tools.definition import ToolDefinition
from .in_out import IN_OUT_TOOLS
from .preparation import PREPARATION_TOOLS
from .join import JOIN_TOOLS
from .parse import PARSE_TOOLS
from .transform import TRANSFORM_TOOLS
from .developer import DEVELOPER_TOOLS
from .documentation import DOCUMENTATION_TOOLS
from .reporting import REPORTING_TOOLS
from .spatial import SPATIAL_TOOLS
from .in_database import IN_DATABASE_TOOLS
from .connectors import CONNECTOR_TOOLS

ALL_TOOLS: tuple[ToolDefinition, ...] = (
    *IN_OUT_TOOLS,
    *PREPARATION_TOOLS,
    *JOIN_TOOLS,
    *PARSE_TOOLS,
    *TRANSFORM_TOOLS,
    *DEVELOPER_TOOLS,
    *DOCUMENTATION_TOOLS,
    *REPORTING_TOOLS,
    *SPATIAL_TOOLS,
    *IN_DATABASE_TOOLS,
    *CONNECTOR_TOOLS,
)

__all__ = [
    "ALL_TOOLS",
    "IN_OUT_TOOLS",
    "PREPARATION_TOOLS",
    "JOIN_TOOLS",
    "PARSE_TOOLS",
    "TRANSFORM_TOOLS",
    "DEVELOPER_TOOLS",
    "DOCUMENTATION_TOOLS",
    "REPORTING_TOOLS",
    "SPATIAL_TOOLS",
    "IN_DATABASE_TOOLS",
    "CONNECTOR_TOOLS",
]
