"""Tool-specific configuration extraction from XML.

Each Alteryx tool type has its own Configuration XML structure.
This module uses a dispatch table to extract structured configuration
from the raw XML elements.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from backend.src.awa.model.tool import ToolConfiguration


def extract_tool_config(
    config_el: ET.Element | None,
    tool_type: str,
) -> ToolConfiguration:
    """Extract tool configuration from an XML Configuration element.

    Always preserves raw XML. Dispatches to tool-specific extractors
    for structured parsing.

    Args:
        config_el: The <Configuration> XML element, or None.
        tool_type: The derived tool type name.

    Returns:
        ToolConfiguration with raw_xml and parsed dict.
    """
    if config_el is None:
        return ToolConfiguration(raw_xml="", parsed={})

    raw_xml = ET.tostring(config_el, encoding="unicode")
    extractor = _CONFIG_EXTRACTORS.get(tool_type)
    parsed = extractor(config_el) if extractor else {}

    return ToolConfiguration(raw_xml=raw_xml, parsed=parsed)


# ── Tool-specific extractors ────────────────────────────────────────


def _extract_file_input_config(config_el: ET.Element) -> dict:
    """Extract DbFileInput / InputData configuration."""
    config: dict = {}
    file_el = config_el.find("File")
    if file_el is not None:
        if file_el.text:
            config["file_path"] = file_el.text
        file_format = file_el.get("FileFormat")
        if file_format:
            config["file_format"] = file_format
        record_limit = file_el.get("RecordLimit")
        if record_limit:
            config["record_limit"] = record_limit

    # Format-specific options
    fmt_opts = config_el.find("FormatSpecificOptions")
    if fmt_opts is not None:
        for child in fmt_opts:
            if child.text:
                config[f"format_{child.tag.lower()}"] = child.text

    return config


def _extract_file_output_config(config_el: ET.Element) -> dict:
    """Extract DbFileOutput / OutputData configuration."""
    config: dict = {}
    file_el = config_el.find("File")
    if file_el is not None:
        if file_el.text:
            config["file_path"] = file_el.text
        file_format = file_el.get("FileFormat")
        if file_format:
            config["file_format"] = file_format
        max_records = file_el.get("MaxRecords")
        if max_records:
            config["max_records"] = max_records
    return config


def _extract_filter_config(config_el: ET.Element) -> dict:
    """Extract Filter configuration."""
    config: dict = {}
    expr_el = config_el.find("Expression")
    if expr_el is not None and expr_el.text:
        config["expression"] = expr_el.text
    mode_el = config_el.find("Mode")
    if mode_el is not None and mode_el.text:
        config["mode"] = mode_el.text
    return config


def _extract_formula_config(config_el: ET.Element) -> dict:
    """Extract Formula configuration (one or more formula fields)."""
    fields = []
    for formula_field in config_el.findall(".//FormulaField"):
        fields.append({
            "field": formula_field.get("field", ""),
            "expression": formula_field.get("expression", ""),
            "type": formula_field.get("type", ""),
            "size": formula_field.get("size", ""),
        })
    config: dict = {}
    if fields:
        config["formula_fields"] = fields
    return config


def _extract_select_config(config_el: ET.Element) -> dict:
    """Extract Select / AlteryxSelect configuration."""
    fields = []
    for sf in config_el.findall(".//SelectField"):
        fields.append({
            "field": sf.get("field", ""),
            "selected": sf.get("selected", "True"),
            "rename": sf.get("rename", ""),
            "type": sf.get("type", ""),
            "size": sf.get("size", ""),
        })
    config: dict = {}
    if fields:
        config["select_fields"] = fields
    return config


def _extract_join_config(config_el: ET.Element) -> dict:
    """Extract Join configuration."""
    config: dict = {}
    join_fields = []
    for join_el in config_el.findall(".//JoinInfo"):
        connection = join_el.get("connection", "")
        for field_el in join_el.findall("Field"):
            left = field_el.get("left", "")
            right = field_el.get("right", "")
            if left and right:
                join_fields.append({"left": left, "right": right})
        if connection:
            config["join_connection"] = connection
    if join_fields:
        config["join_fields"] = join_fields

    by_pos = config_el.find("JoinByRecordPos")
    if by_pos is not None:
        config["join_by_position"] = by_pos.get("value", "False") == "True"

    # Extract select configuration for join output
    select_config = config_el.find(".//SelectConfiguration/Configuration")
    if select_config is not None:
        output_conn = select_config.get("outputConnection", "")
        if output_conn:
            config["output_connection"] = output_conn

    return config


def _extract_union_config(config_el: ET.Element) -> dict:
    """Extract Union configuration."""
    config: dict = {}
    mode = config_el.get("Mode", "")
    if mode:
        config["mode"] = mode

    # Union field mappings
    by_name = config_el.find("ByName_or_ByPos")
    if by_name is not None and by_name.text:
        config["by_name_or_pos"] = by_name.text

    return config


def _extract_summarize_config(config_el: ET.Element) -> dict:
    """Extract Summarize configuration."""
    fields = []
    for sf in config_el.findall(".//SummarizeField"):
        fields.append({
            "field": sf.get("field", ""),
            "action": sf.get("action", ""),
            "rename": sf.get("rename", ""),
        })
    config: dict = {}
    if fields:
        config["summarize_fields"] = fields
    return config


def _extract_sort_config(config_el: ET.Element) -> dict:
    """Extract Sort configuration."""
    fields = []
    sort_info = config_el.find("SortInfo")
    if sort_info is not None:
        for sf in sort_info.findall("Field"):
            fields.append({
                "field": sf.get("field", ""),
                "order": sf.get("order", "Ascending"),
            })
    config: dict = {}
    if fields:
        config["sort_fields"] = fields
    return config


def _extract_unique_config(config_el: ET.Element) -> dict:
    """Extract Unique tool configuration."""
    fields = []
    for field_el in config_el.findall(".//UniqueFields/Field"):
        fname = field_el.get("field", "")
        if fname:
            fields.append(fname)
    config: dict = {}
    if fields:
        config["unique_fields"] = fields
    return config


def _extract_data_cleansing_config(config_el: ET.Element) -> dict:
    """Extract DataCleansing configuration."""
    config: dict = {}
    for opt in ("RemoveNull", "RemoveWhitespace", "TrimWhitespace"):
        el = config_el.find(opt)
        if el is not None:
            config[opt.lower()] = el.get("value", "True") == "True"

    modify_case_el = config_el.find("ModifyCase")
    if modify_case_el is not None:
        config["modify_case"] = modify_case_el.text or modify_case_el.get("value", "")

    fields: list[str] = []
    fields_el = config_el.find("Fields")
    if fields_el is not None:
        for field_el in fields_el.findall("Field"):
            fname = field_el.get("field", "")
            if fname:
                fields.append(fname)
    if fields:
        config["cleansing_fields"] = fields

    return config


def _extract_sample_config(config_el: ET.Element) -> dict:
    """Extract Sample tool configuration."""
    config: dict = {}
    mode_el = config_el.find("Mode")
    if mode_el is not None and mode_el.text:
        config["sample_mode"] = mode_el.text

    n_el = config_el.find("N")
    if n_el is not None and n_el.text:
        try:
            config["sample_n"] = int(n_el.text)
        except ValueError:
            pass

    pct_el = config_el.find("Pct")
    if pct_el is not None and pct_el.text:
        try:
            config["sample_pct"] = float(pct_el.text)
        except ValueError:
            pass

    return config


def _extract_record_id_config(config_el: ET.Element) -> dict:
    """Extract RecordID tool configuration."""
    config: dict = {}
    field_name = config_el.find("FieldName")
    if field_name is not None and field_name.text:
        config["field_name"] = field_name.text

    starting = config_el.find("StartValue")
    if starting is not None and starting.text:
        try:
            config["start_value"] = int(starting.text)
        except ValueError:
            config["start_value"] = 1

    return config


def _extract_transpose_config(config_el: ET.Element) -> dict:
    """Extract Transpose configuration."""
    config: dict = {}
    key_fields = []
    for field_el in config_el.findall(".//KeyFields/Field"):
        fname = field_el.get("field", "")
        if fname:
            key_fields.append(fname)
    if key_fields:
        config["key_fields"] = key_fields

    data_fields = []
    for field_el in config_el.findall(".//DataFields/Field"):
        fname = field_el.get("field", "")
        if fname:
            data_fields.append(fname)
    if data_fields:
        config["data_fields"] = data_fields

    return config


def _extract_cross_tab_config(config_el: ET.Element) -> dict:
    """Extract CrossTab configuration."""
    config: dict = {}
    group_fields = []
    for field_el in config_el.findall(".//GroupFields/Field"):
        fname = field_el.get("field", "")
        if fname:
            group_fields.append(fname)
    if group_fields:
        config["group_fields"] = group_fields

    header_el = config_el.find("HeaderField")
    if header_el is not None and header_el.text:
        config["header_field"] = header_el.text

    data_el = config_el.find("DataField")
    if data_el is not None and data_el.text:
        config["data_field"] = data_el.text

    method_el = config_el.find("Method")
    if method_el is not None and method_el.text:
        config["method"] = method_el.text

    return config


# ── Dispatch table ───────────────────────────────────────────────────

_CONFIG_EXTRACTORS: dict[str, callable] = {
    # I/O
    "DbFileInput": _extract_file_input_config,
    "InputData": _extract_file_input_config,
    "DbFileOutput": _extract_file_output_config,
    "OutputData": _extract_file_output_config,
    # Transform
    "Filter": _extract_filter_config,
    "Formula": _extract_formula_config,
    "Select": _extract_select_config,
    "AlteryxSelect": _extract_select_config,
    "Sort": _extract_sort_config,
    "DataCleansing": _extract_data_cleansing_config,
    "Sample": _extract_sample_config,
    "Unique": _extract_unique_config,
    "RecordID": _extract_record_id_config,
    # Join/Merge
    "Join": _extract_join_config,
    "Union": _extract_union_config,
    # Reshape
    "Summarize": _extract_summarize_config,
    "Transpose": _extract_transpose_config,
    "CrossTab": _extract_cross_tab_config,
}
