"""Tool-specific configuration extraction and security redaction from XML."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any, Callable

from awa.model.tool import ToolConfiguration

# Sensitive key patterns for security redaction
REDACTED_VALUE = "[REDACTED]"
_SENSITIVE_KEY_PATTERN = re.compile(
    r"(password|pwd|secret|token|api_?key|client_?secret|access_?token|credential|private_?key|auth_?token)",
    re.IGNORECASE,
)
_CONN_STRING_SECRET_PATTERN = re.compile(
    r"(password|pwd|secret|token|api_?key|client_?secret|access_?token)\s*=\s*([^;,\s\"\'<>]+)",
    re.IGNORECASE,
)
_XML_SECRET_TAG_PATTERN = re.compile(
    r"(<(?:[a-zA-Z0-9_:]*)(?:password|pwd|secret|token|api_?key|client_?secret|access_?token|credential|private_?key|auth_?token)(?:[a-zA-Z0-9_:]*)[^>]*>)([^<]*)(</)",
    re.IGNORECASE,
)
_XML_SECRET_ATTR_PATTERN = re.compile(
    r'((?:password|pwd|secret|token|api_?key|client_?secret|access_?token)\s*=\s*["\'])[^"\']*(["\'])',
    re.IGNORECASE,
)


def redact_sensitive_xml(xml_str: str) -> str:
    """Scrub sensitive credentials, passwords, and tokens from raw XML strings."""
    if not xml_str:
        return ""
    # Redact text inside tags: <ApiKey>secret</ApiKey> -> <ApiKey>[REDACTED]</ApiKey>
    redacted = _XML_SECRET_TAG_PATTERN.sub(r"\1[REDACTED]\3", xml_str)
    # Redact XML attributes: Password="secret" -> Password="[REDACTED]"
    redacted = _XML_SECRET_ATTR_PATTERN.sub(r"\1[REDACTED]\2", redacted)
    # Redact connection strings
    redacted = _CONN_STRING_SECRET_PATTERN.sub(r"\1=[REDACTED]", redacted)
    return redacted


def redact_sensitive_data(obj: Any) -> Any:
    """Recursively redact passwords, tokens, API keys, and credentials."""
    if isinstance(obj, dict):
        redacted = {}
        for k, v in obj.items():
            if _SENSITIVE_KEY_PATTERN.search(str(k)):
                redacted[k] = REDACTED_VALUE
            else:
                redacted[k] = redact_sensitive_data(v)
        return redacted
    elif isinstance(obj, list):
        return [redact_sensitive_data(item) for item in obj]
    elif isinstance(obj, str):
        if _CONN_STRING_SECRET_PATTERN.search(obj):
            return _CONN_STRING_SECRET_PATTERN.sub(r"\1=[REDACTED]", obj)
        return obj
    return obj


def extract_tool_config(
    config_el: ET.Element | None,
    tool_type: str,
) -> ToolConfiguration:
    """Extract tool configuration from an XML Configuration element.

    Always preserves raw XML (with sensitive credentials scrubbed).
    Dispatches to tool-specific extractors or generic XML-to-dict parser,
    and strictly redacts credentials.

    Args:
        config_el: The <Configuration> XML element, or None.
        tool_type: The derived tool type name.

    Returns:
        ToolConfiguration with sanitized raw_xml and parsed dict.
    """
    if config_el is None:
        return ToolConfiguration(raw_xml="", parsed={})

    raw_xml = ET.tostring(config_el, encoding="unicode")
    sanitized_raw_xml = redact_sensitive_xml(raw_xml)

    extractor = _CONFIG_EXTRACTORS.get(tool_type)
    if extractor:
        parsed = extractor(config_el)
    else:
        parsed = _generic_xml_to_dict(config_el)

    sanitized_parsed = redact_sensitive_data(parsed)
    return ToolConfiguration(raw_xml=sanitized_raw_xml, parsed=sanitized_parsed)


def _generic_xml_to_dict(el: ET.Element) -> dict:
    """Generic fallback parser converting XML elements into nested dictionary."""
    result: dict = {}
    if el.attrib:
        result.update(dict(el.attrib))

    children = list(el)
    if not children:
        if el.text and el.text.strip():
            result["value"] = el.text.strip()
        return result

    for child in children:
        child_dict = _generic_xml_to_dict(child)
        if child.tag in result:
            if not isinstance(result[child.tag], list):
                result[child.tag] = [result[child.tag]]
            result[child.tag].append(child_dict)
        else:
            result[child.tag] = child_dict
    return result


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


def _extract_text_input_config(config_el: ET.Element) -> dict:
    """Extract TextInput configuration."""
    config: dict = {}
    fields = []
    for f_el in config_el.findall(".//Fields/Field"):
        fields.append(f_el.get("name", ""))
    if fields:
        config["fields"] = fields

    rows = []
    for r_el in config_el.findall(".//Data/r"):
        row = [c.text or "" for c in r_el.findall("c")]
        rows.append(row)
    if rows:
        config["rows"] = rows
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

    if not fields:
        # Fallback for text-formatted FormulaFields: "Field1=expr1;Field2=expr2"
        ff_el = config_el.find(".//FormulaFields")
        if ff_el is not None and ff_el.text and ff_el.text.strip():
            raw_text = ff_el.text.strip()
            # Split on semicolons that separate field assignments
            for chunk in re.split(r";(?=[a-zA-Z0-9_\s]+=)", raw_text):
                chunk = chunk.strip()
                if "=" in chunk:
                    fname, fexpr = chunk.split("=", 1)
                    fields.append({
                        "field": fname.strip(),
                        "expression": fexpr.strip(),
                        "type": "",
                        "size": "",
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

    if not fields:
        # Fallback for text-formatted SelectFields: "Field1;Field2;Field3" or "Old:New;F2"
        sf_el = config_el.find(".//SelectFields")
        if sf_el is not None and sf_el.text and sf_el.text.strip():
            for item in sf_el.text.strip().split(";"):
                item = item.strip()
                if not item:
                    continue
                if ":" in item:
                    orig, ren = item.split(":", 1)
                    fields.append({
                        "field": orig.strip(),
                        "selected": "True",
                        "rename": ren.strip(),
                        "type": "",
                        "size": "",
                    })
                else:
                    fields.append({
                        "field": item,
                        "selected": "True",
                        "rename": "",
                        "type": "",
                        "size": "",
                    })

    config: dict = {}
    if fields:
        config["select_fields"] = fields
    return config


def _extract_join_config(config_el: ET.Element) -> dict:
    """Extract Join configuration."""
    config: dict = {}
    join_fields = []

    left_join_info = config_el.find(".//JoinInfo[@connection='Left']")
    right_join_info = config_el.find(".//JoinInfo[@connection='Right']")

    if left_join_info is not None and right_join_info is not None:
        left_fields = [f.get("field", "") for f in left_join_info.findall("Field") if f.get("field")]
        right_fields = [f.get("field", "") for f in right_join_info.findall("Field") if f.get("field")]
        for l, r in zip(left_fields, right_fields):
            join_fields.append({"left": l, "right": r})
    else:
        for join_el in config_el.findall(".//JoinInfo"):
            connection = join_el.get("connection", "")
            for field_el in join_el.findall("Field"):
                left = field_el.get("left", "")
                right = field_el.get("right", "")
                if left and right:
                    join_fields.append({"left": left, "right": right})
            if connection:
                config["join_connection"] = connection

    if not join_fields:
        # Fallback for direct LeftField / RightField tags
        left_el = config_el.find(".//LeftField")
        right_el = config_el.find(".//RightField")
        if left_el is not None and right_el is not None and left_el.text and right_el.text:
            join_fields.append({"left": left_el.text.strip(), "right": right_el.text.strip()})

    if join_fields:
        config["join_fields"] = join_fields

    by_pos = config_el.find("JoinByRecordPos")
    if by_pos is not None:
        config["join_by_position"] = by_pos.get("value", "False") == "True"

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
    if not mode:
        mode_el = config_el.find("Mode")
        if mode_el is not None and mode_el.text:
            mode = mode_el.text.strip()
    for tag in ("ByName_or_ByPos", "ByNameOrPos", "ByName_or_Pos"):
        el = config_el.find(f".//{tag}")
        if el is not None and el.text:
            config["by_name_or_pos"] = el.text.strip()
            break
        if tag in config_el.attrib:
            config["by_name_or_pos"] = config_el.attrib[tag].strip()
            break

    if "by_name_or_pos" not in config and mode:
        config["by_name_or_pos"] = mode

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

    if not fields:
        # Fallback for text-formatted SummarizeFields: "Field1:Action:Rename;Field2:GroupBy"
        sf_el = config_el.find(".//SummarizeFields")
        if sf_el is not None and sf_el.text and sf_el.text.strip():
            for item in sf_el.text.strip().split(";"):
                item = item.strip()
                if not item:
                    continue
                parts = [p.strip() for p in item.split(":")]
                if len(parts) == 1:
                    fields.append({"field": parts[0], "action": "GroupBy", "rename": ""})
                elif len(parts) == 2:
                    fields.append({"field": parts[0], "action": parts[1], "rename": ""})
                elif len(parts) >= 3:
                    fields.append({"field": parts[0], "action": parts[1], "rename": parts[2]})

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
        if not fields and sort_info.text and sort_info.text.strip():
            for item in sort_info.text.strip().split(";"):
                item = item.strip()
                if not item:
                    continue
                parts = item.split()
                if len(parts) >= 2 and parts[-1].lower() in ("ascending", "descending"):
                    fields.append({"field": " ".join(parts[:-1]), "order": parts[-1].capitalize()})
                else:
                    fields.append({"field": item, "order": "Ascending"})

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
    if not group_fields:
        gf_el = config_el.find("GroupField")
        if gf_el is not None and gf_el.text and gf_el.text.strip():
            group_fields = [f.strip() for f in gf_el.text.strip().split(";") if f.strip()]
    if group_fields:
        config["group_fields"] = group_fields

    header_el = config_el.find("HeaderField")
    if header_el is not None:
        val = header_el.get("field", "") or (header_el.text.strip() if header_el.text else "")
        if val:
            config["header_field"] = val

    data_el = config_el.find("DataField")
    if data_el is not None:
        val = data_el.get("field", "") or (data_el.text.strip() if data_el.text else "")
        if val:
            config["data_field"] = val

    method_el = config_el.find("Method")
    if method_el is not None:
        val = method_el.get("method", "") or (method_el.text.strip() if method_el.text else "")
        if val:
            config["method"] = val

    return config


def _extract_date_time_config(config_el: ET.Element) -> dict:
    """Extract DateTime tool configuration."""
    config: dict = {}
    for tag in ("IsInputDate", "InputFormat", "OutputFormat", "InputFieldName", "OutputFieldName"):
        el = config_el.find(tag)
        if el is not None and el.text:
            config[tag.lower()] = el.text
    return config


def _extract_regex_config(config_el: ET.Element) -> dict:
    """Extract RegEx tool configuration."""
    config: dict = {}
    for tag in ("Field", "RegExExpression", "CaseInsensitve", "Method", "ReplaceString"):
        el = config_el.find(tag)
        if el is not None and el.text:
            config[tag.lower()] = el.text
    return config


def _extract_text_to_columns_config(config_el: ET.Element) -> dict:
    """Extract TextToColumns tool configuration."""
    config: dict = {}
    for tag in ("Field", "Delimeters", "NumFields", "Flags"):
        el = config_el.find(tag)
        if el is not None and el.text:
            config[tag.lower()] = el.text
    return config


# ── Dispatch table ───────────────────────────────────────────────────

_CONFIG_EXTRACTORS: dict[str, Callable[[ET.Element], dict]] = {
    # I/O
    "DbFileInput": _extract_file_input_config,
    "InputData": _extract_file_input_config,
    "DbFileOutput": _extract_file_output_config,
    "OutputData": _extract_file_output_config,
    "TextInput": _extract_text_input_config,
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
    # Parse
    "DateTime": _extract_date_time_config,
    "RegEx": _extract_regex_config,
    "TextToColumns": _extract_text_to_columns_config,
}
