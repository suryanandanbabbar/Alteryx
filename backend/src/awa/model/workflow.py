"""Workflow and metadata models."""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field

from .tool import Tool
from .connection import Connection
from .diagnostic import Diagnostic, Dependency


@dataclass
class WorkflowMetadata:
    """Metadata about the workflow.
    
    Attributes:
        name: Workflow name.
        version: Alteryx version string (yxmdVer attribute).
        author: Author, if available.
        description: Description, if available.
        properties: Raw properties dict from XML.
    """
    name: str
    version: str
    author: str | None = None
    description: str | None = None
    properties: dict = dc_field(default_factory=dict)

    def to_dict(self) -> dict:
        d: dict = {
            "name": self.name,
            "version": self.version,
        }
        if self.author:
            d["author"] = self.author
        if self.description:
            d["description"] = self.description
        if self.properties:
            d["properties"] = self.properties
        return d


@dataclass
class Workflow:
    """The canonical Workflow Intermediate Representation.
    
    This is the single source of truth parsed from a .yxmd file.
    All generators (JSON, Python, Markdown) consume this model.
    
    Attributes:
        metadata: Workflow-level metadata.
        tools: Tools keyed by tool_id.
        connections: Directed connections between tools.
        dependencies: External dependencies detected.
        diagnostics: Diagnostic messages from analysis.
    """
    metadata: WorkflowMetadata
    tools: dict[int, Tool] = dc_field(default_factory=dict)
    connections: list[Connection] = dc_field(default_factory=list)
    dependencies: list[Dependency] = dc_field(default_factory=list)
    diagnostics: list[Diagnostic] = dc_field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "metadata": self.metadata.to_dict(),
            "tools": {
                str(tid): tool.to_dict()
                for tid, tool in sorted(self.tools.items())
            },
            "connections": [c.to_dict() for c in self.connections],
            "dependencies": [d.to_dict() for d in self.dependencies],
            "diagnostics": [d.to_dict() for d in self.diagnostics],
        }
