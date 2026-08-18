"""AWA XML parser — parses .yxmd files into canonical Workflow IR."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from awa.model.workflow import Workflow, WorkflowMetadata
from awa.model.tool import Tool, ToolConfiguration, Position
from awa.model.connection import Connection
from awa.model.field import Field
from awa.parser.tool_parser import extract_tool_config


def parse_workflow(path: str | Path) -> Workflow:
    """Parse a .yxmd file into the canonical Workflow IR.

    Args:
        path: Path to the .yxmd file.

    Returns:
        Parsed Workflow dataclass.

    Raises:
        FileNotFoundError: If the file does not exist.
        ET.ParseError: If the XML is malformed.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Workflow file not found: {path}")

    tree = ET.parse(str(path))
    root = tree.getroot()

    metadata = _parse_metadata(root, path)
    tools = _parse_tools(root)
    connections = _parse_connections(root)

    return Workflow(
        metadata=metadata,
        tools=tools,
        connections=connections,
    )


def _parse_metadata(root: ET.Element, path: Path) -> WorkflowMetadata:
    """Extract workflow metadata from the document root."""
    version = root.get("yxmdVer", "")

    # Extract name from Properties/MetaInfo/Name
    name = path.stem
    meta_name = root.find("./Properties/MetaInfo/Name")
    if meta_name is not None and meta_name.text:
        name = meta_name.text

    # Extract author
    author = None
    author_el = root.find("./Properties/MetaInfo/Author")
    if author_el is not None and author_el.text:
        author = author_el.text

    # Extract description
    description = None
    desc_el = root.find("./Properties/MetaInfo/Description")
    if desc_el is not None and desc_el.text and desc_el.text.strip():
        description = desc_el.text.strip()

    # Extract raw properties
    properties = _parse_properties(root)

    return WorkflowMetadata(
        name=name,
        version=version,
        author=author,
        description=description,
        properties=properties,
    )


def _parse_properties(root: ET.Element) -> dict:
    """Parse workflow-level Properties into a dict."""
    props: dict = {}
    props_el = root.find("Properties")
    if props_el is None:
        return props

    for child in props_el:
        if child.tag == "MetaInfo":
            meta: dict = {}
            for meta_child in child:
                meta[meta_child.tag] = meta_child.text or meta_child.get("value", "")
            props["MetaInfo"] = meta
        else:
            if child.attrib:
                props[child.tag] = dict(child.attrib)
            elif child.text and child.text.strip():
                props[child.tag] = child.text.strip()
            else:
                props[child.tag] = ""
    return props


def _parse_tools(root: ET.Element) -> dict[int, Tool]:
    """Parse all Node elements into Tool dataclasses."""
    tools: dict[int, Tool] = {}

    for node in root.findall(".//Nodes/Node"):
        tool_id = int(node.get("ToolID", "0"))

        # Skip disabled nodes
        disabled_el = node.find(".//Properties/Disabled")
        if disabled_el is not None and disabled_el.get("value", "False") == "True":
            continue

        # Extract plugin from GuiSettings
        gui_settings = node.find("GuiSettings")
        plugin = gui_settings.get("Plugin", "") if gui_settings is not None else ""

        # Skip ToolContainer nodes (visual-only grouping, no data logic)
        if "ToolContainer" in plugin:
            continue

        # Derive tool_type from plugin string
        tool_type = _derive_tool_type(plugin)

        # Extract position
        position = _extract_position(gui_settings)

        # Extract annotation name
        name = _extract_annotation_name(node)

        # Extract full annotation text
        annotation = _extract_annotation_text(node)

        # Extract configuration
        config_el = node.find(".//Configuration")
        configuration = extract_tool_config(config_el, tool_type)

        # Extract output fields
        output_fields = _extract_fields(node)

        # Extract engine settings
        engine_settings = {}
        engine_el = node.find("EngineSettings")
        if engine_el is not None:
            engine_settings = dict(engine_el.attrib)

        tools[tool_id] = Tool(
            tool_id=tool_id,
            plugin=plugin,
            tool_type=tool_type,
            name=name,
            position=position,
            configuration=configuration,
            annotation=annotation,
            output_fields=output_fields,
            engine_settings=engine_settings,
        )

    return tools


def _derive_tool_type(plugin: str) -> str:
    """Derive the tool type name from the full plugin string.

    Examples:
        'AlteryxBasePluginsGui.Filter.Filter' → 'Filter'
        'AlteryxBasePluginsGui.DbFileInput.DbFileInput' → 'DbFileInput'
        'box_input_v1.0.3' → 'box_input_v1.0.3' (version-dotted, keep full)
    """
    if not plugin:
        return ""

    # Box-style plugins: last segment is a version digit, keep full string
    last = plugin.rsplit(".", 1)[-1]
    if last.isdigit():
        return plugin

    return last


def _extract_position(gui_settings: ET.Element | None) -> Position | None:
    """Extract the canvas position from GuiSettings."""
    if gui_settings is None:
        return None
    pos_el = gui_settings.find("Position")
    if pos_el is None:
        return None
    x = pos_el.get("x")
    y = pos_el.get("y")
    if x is not None and y is not None:
        try:
            return Position(x=int(x), y=int(y))
        except ValueError:
            return None
    return None


def _extract_annotation_name(node: ET.Element) -> str:
    """Extract the annotation name from a Node element."""
    ann_name = node.find(".//Annotation/Name")
    if ann_name is not None and ann_name.text:
        return ann_name.text
    return ""


def _extract_annotation_text(node: ET.Element) -> str:
    """Extract the full default annotation text."""
    ann_text = node.find(".//Annotation/DefaultAnnotationText")
    if ann_text is not None and ann_text.text:
        return ann_text.text
    return ""


def _extract_fields(node: ET.Element) -> list[Field]:
    """Extract output fields from MetaInfo/RecordInfo."""
    fields: list[Field] = []
    for meta_info in node.findall(".//MetaInfo"):
        for field_el in meta_info.findall(".//RecordInfo/Field"):
            name = field_el.get("name", "")
            ftype = field_el.get("type", "")
            size_str = field_el.get("size")
            scale_str = field_el.get("scale")
            fields.append(Field(
                name=name,
                type=ftype,
                size=int(size_str) if size_str else None,
                scale=int(scale_str) if scale_str else None,
            ))
    return fields


def _parse_connections(root: ET.Element) -> list[Connection]:
    """Parse all Connection elements into Connection dataclasses."""
    connections: list[Connection] = []

    for conn in root.findall(".//Connections/Connection"):
        origin = conn.find("Origin")
        dest = conn.find("Destination")
        if origin is not None and dest is not None:
            connections.append(Connection(
                origin_tool_id=int(origin.get("ToolID", "0")),
                origin_anchor=origin.get("Connection", ""),
                destination_tool_id=int(dest.get("ToolID", "0")),
                destination_anchor=dest.get("Connection", ""),
            ))

    return connections
