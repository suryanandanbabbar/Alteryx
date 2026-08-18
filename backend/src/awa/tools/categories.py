"""Tool categories and visual category mappings."""

from __future__ import annotations

from enum import Enum


class ToolCategory(str, Enum):
    """Authoritative tool categories from Alteryx Designer."""
    IN_OUT = "In/Out"
    PREPARATION = "Preparation"
    JOIN = "Join"
    PARSE = "Parse"
    TRANSFORM = "Transform"
    DEVELOPER = "Developer"
    DOCUMENTATION = "Documentation"
    REPORTING = "Reporting"
    SPATIAL = "Spatial"
    IN_DATABASE = "In-Database"
    CONNECTORS = "Connectors"


# Mapping from ToolCategory to default visual category
CATEGORY_TO_VISUAL: dict[ToolCategory, str] = {
    ToolCategory.IN_OUT: "input",
    ToolCategory.PREPARATION: "transform",
    ToolCategory.JOIN: "join",
    ToolCategory.PARSE: "regex",
    ToolCategory.TRANSFORM: "reshape",
    ToolCategory.DEVELOPER: "developer",
    ToolCategory.DOCUMENTATION: "documentation",
    ToolCategory.REPORTING: "reporting",
    ToolCategory.SPATIAL: "spatial",
    ToolCategory.IN_DATABASE: "in_database",
    ToolCategory.CONNECTORS: "connector",
}
