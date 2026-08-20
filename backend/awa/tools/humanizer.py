"""Central configuration humanizer and code resolver for Alteryx tools.

Translates machine-oriented configuration codes, numeric enums, raw dictionaries,
and internal flags into clear, business-friendly terminology for reports and UI.
"""

from __future__ import annotations

import re
from typing import Any

# Alteryx FileFormat numeric enumeration mapping
ALTERYX_FILE_FORMAT_MAP: dict[str, str] = {
    "0": "CSV / Delimited (.csv)",
    "1": "Delimited Text (.csv / .txt)",
    "2": "dBase / DBF Database (.dbf)",
    "6": "Microsoft Access Database (.mdb)",
    "7": "Microsoft Excel 97-2003 (.xls)",
    "8": "Microsoft Excel (.xlsx / .xlsm)",
    "12": "XML Data File (.xml)",
    "14": "Spatial Data (.shp / .tab)",
    "19": "Alteryx Database (.yxdb)",
    "21": "ESRI Shapefile (.shp)",
    "22": "MapInfo File (.tab / .mif)",
    "24": "Tableau Data Extract (.tde)",
    "25": "Microsoft Excel (.xlsx)",
    "27": "Alteryx Spatial Zip (.sz)",
    "28": "Tableau Hyper Data Extract (.hyper)",
    "29": "Apache Spark / Hadoop (.csv)",
    "32": "GML Data (.gml)",
    "34": "GeoJSON (.geojson)",
    "36": "Apache Parquet (.parquet)",
    "37": "Apache ORC (.orc)",
    "38": "Apache Avro (.avro)",
    "48": "Alteryx Package (.yxzp)",
    "54": "JSON Data (.json)",
    "55": "SAS Data File (.sas7bdat)",
    "56": "SPSS Data File (.sav)",
    "57": "Google Sheets",
}

# Common configuration key display names
CONFIG_KEY_DISPLAY_NAMES: dict[str, str] = {
    "file_path": "File Path",
    "file_format": "File Format",
    "record_limit": "Record Limit",
    "max_records": "Maximum Records",
    "expression": "Expression",
    "filter_expression": "Filter Expression",
    "mode": "Mode",
    "filter_mode": "Filter Mode",
    "search_subdirs": "Search Subdirectories",
    "keep_source_cols": "Retain Source Columns",
    "ignore_errors": "Ignore Errors",
    "join_by_pos": "Join Method",
    "by_name_or_pos": "Union Alignment Mode",
    "delimiters": "Delimiter(s)",
    "num_fields": "Number of Columns",
    "root_element": "Root XML Element",
    "case_sensitive": "Case Sensitive",
    "date_time_format": "Date/Time Format",
    "input_column": "Input Column",
    "output_column": "Output Column",
    "tile_method": "Tiling Method",
    "num_tiles": "Number of Tiles",
    "group_fields": "Group By Fields",
    "source_field": "Source Field",
    "target_field": "Target Field",
    "format_codepage": "Character Encoding (Code Page)",
    "format_delimeter": "Delimiter",
    "format_firstrowdata": "First Row Is Data",
    "format_quotechar": "Quote Character",
    "format_headerrow": "Header Row",
    "format_noprogress": "Show Progress",
    "fields": "Selected Fields",
    "formula_fields": "Calculated Columns",
    "summarize_fields": "Aggregation Summary",
    "join_fields": "Join Key Conditions",
    "sort_fields": "Sort Order",
    "select_fields": "Column Selection & Renaming",
    "unique_fields": "Deduplication Key Fields",
    "sample_type": "Sampling Method",
    "sample_n": "Sample Record Count",
    "sample_percent": "Sample Percentage",
}


def resolve_file_format(format_code: Any) -> str:
    """Resolve an Alteryx FileFormat enumeration code into a friendly format name.

    Examples:
        resolve_file_format(19) -> "Alteryx Database (.yxdb)"
        resolve_file_format("19") -> "Alteryx Database (.yxdb)"
        resolve_file_format(8) -> "Microsoft Excel (.xlsx / .xlsm)"
    """
    if format_code is None:
        return "Auto-Detect / Default"

    code_str = str(format_code).strip()
    if code_str in ALTERYX_FILE_FORMAT_MAP:
        return ALTERYX_FILE_FORMAT_MAP[code_str]

    # If it's already a descriptive text or file extension
    if code_str.startswith("."):
        ext = code_str.lower()
        if ext == ".yxdb":
            return "Alteryx Database (.yxdb)"
        if ext in (".xlsx", ".xlsm", ".xls"):
            return "Microsoft Excel (.xlsx)"
        if ext == ".csv":
            return "CSV / Delimited (.csv)"
        if ext == ".hyper":
            return "Tableau Hyper Data Extract (.hyper)"
        if ext == ".parquet":
            return "Apache Parquet (.parquet)"
        if ext == ".json":
            return "JSON Data (.json)"
        return f"File ({code_str})"

    return f"Format Code {code_str}"


def humanize_config_key(key: str) -> str:
    """Convert snake_case or camelCase configuration keys to clean Title Case."""
    if not key:
        return ""

    lower_k = key.lower().replace("-", "_")
    if lower_k in CONFIG_KEY_DISPLAY_NAMES:
        return CONFIG_KEY_DISPLAY_NAMES[lower_k]

    # Convert camelCase to snake_case
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", key)
    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1)
    words = s2.replace("-", "_").split("_")
    return " ".join(w.capitalize() for w in words if w)


def humanize_config_value(key: str, value: Any, tool_type: str = "") -> str:
    """Translate raw, machine-oriented configuration values into business-friendly strings."""
    if value is None:
        return "None"

    k_lower = key.lower().replace("-", "_")

    # 1. File Format resolver
    if k_lower in ("file_format", "fileformat", "format"):
        return resolve_file_format(value)

    # 2. Record Limits / Max Records
    if k_lower in ("record_limit", "recordlimit", "max_records", "maxrecords"):
        val_str = str(value).strip()
        if val_str in ("0", "", "None"):
            return "All records (No limit)"
        return f"{val_str} records"

    # 3. Join Method
    if k_lower in ("join_by_pos", "joinbypos"):
        is_pos = str(value).strip().lower() in ("true", "1", "yes")
        return "Join by record position" if is_pos else "Join by matching specific key fields"

    # 4. Union Alignment
    if k_lower in ("by_name_or_pos", "bynameorpos"):
        val_str = str(value).strip().lower()
        if "name" in val_str:
            return "Align by column name"
        if "pos" in val_str:
            return "Align by column position"
        return str(value)

    # 5. Search Subdirectories
    if k_lower in ("search_subdirs", "searchsubdirs"):
        is_sub = str(value).strip().lower() in ("true", "1", "yes")
        return "Search subdirectories (Recursive)" if is_sub else "Top-level directory only"

    # 6. Generic Booleans
    if isinstance(value, bool):
        return "Yes (Enabled)" if value else "No (Disabled)"
    if isinstance(value, str) and value.strip().lower() in ("true", "false"):
        return "Yes (Enabled)" if value.strip().lower() == "true" else "No (Disabled)"

    # 7. Structured list / formula / summarize / select fields
    if isinstance(value, list):
        if not value:
            return "None configured"
        # List of strings
        if all(isinstance(x, str) for x in value):
            return ", ".join(value)
        # List of dictionaries
        if all(isinstance(x, dict) for x in value):
            items = []
            for item in value:
                # Formula Field: {'field': 'A', 'expression': 'B', 'type': 'Double'}
                if "field" in item and "expression" in item:
                    f = item.get("field", "")
                    e = item.get("expression", "")
                    t = item.get("type", "")
                    type_str = f" : {t}" if t else ""
                    items.append(f"{f}{type_str} = {e}")
                # Summarize Field: {'field': 'A', 'action': 'Sum', 'rename': 'B'}
                elif "field" in item and "action" in item:
                    f = item.get("field", "")
                    a = item.get("action", "")
                    r = item.get("rename", "")
                    ren_str = f" → {r}" if r and r != f else ""
                    items.append(f"{f} ({a}{ren_str})")
                # Join Condition: {'left': 'A', 'right': 'B'}
                elif "left" in item and "right" in item:
                    items.append(f"{item.get('left')} = {item.get('right')}")
                # Sort Field: {'field': 'A', 'order': 'Descending'}
                elif "field" in item and "order" in item:
                    f = item.get("field", "")
                    o = item.get("order", "Ascending")
                    items.append(f"{f} ({o})")
                # Select Field: {'field': 'A', 'selected': True, 'rename': 'B', 'type': 'C'}
                elif "field" in item and ("selected" in item or "rename" in item or "type" in item):
                    f = item.get("field", "*Unknown*")
                    sel = item.get("selected", True)
                    ren = item.get("rename", "")
                    typ = item.get("type", "")
                    if str(sel).lower() == "false":
                        items.append(f"{f} (Dropped)")
                    elif ren and ren != f:
                        type_str = f", {typ}" if typ else ""
                        items.append(f"{f} → {ren}{type_str}")
                    elif typ:
                        items.append(f"{f} ({typ})")
                    else:
                        items.append(f"{f} (Kept)")
                elif "name" in item and "action" in item:
                    items.append(f"{item.get('name')}: {item.get('action')}")
                else:
                    # Fallback to humanized key-value pairs
                    kv = ", ".join(f"{humanize_config_key(k)}: {humanize_config_value(k, v)}" for k, v in item.items() if v)
                    items.append(kv)
            return "; ".join(items) if items else str(value)

    # 8. Nested dictionary (e.g. Cleansing tool params: {'TrimWhitespace': {'value': 'True'}})
    if isinstance(value, dict):
        if not value:
            return "None"
        if len(value) == 1 and "value" in value:
            return humanize_config_value(key, value["value"], tool_type)
        items = []
        for k, v in value.items():
            h_k = humanize_config_key(str(k))
            h_v = humanize_config_value(str(k), v, tool_type)
            items.append(f"{h_k}: {h_v}")
        return ", ".join(items)

    return str(value)


def humanize_tool_configuration(tool_type: str, config: dict[str, Any]) -> dict[str, str]:
    """Transform an entire raw configuration dictionary into humanized key-value pairs."""
    if not config:
        return {}

    humanized: dict[str, str] = {}
    for k, v in config.items():
        hk = humanize_config_key(str(k))
        hv = humanize_config_value(str(k), v, tool_type)
        humanized[hk] = hv

    return humanized
