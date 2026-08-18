"""Visual category mapping and color palette for tool types.

Centralizes the mapping from Alteryx tool types to visual categories
and the color scheme used consistently across SVG, React, and DOCX.
Colors are approximated from the supplied reference screenshots.
"""

from __future__ import annotations


# --- Tool type → visual category mapping ---

TOOL_VISUAL_CATEGORIES: dict[str, str] = {
    # Input tools
    "DbFileInput": "input",
    "InputData": "input",
    "TextInput": "input",
    "DynamicInput": "input",
    "Directory": "input",
    "DateTimeNow": "datetime",
    # Output tools
    "DbFileOutput": "output",
    "OutputData": "output",
    "Browse": "output",
    "BrowseV2": "output",
    # Filter
    "Filter": "filter",
    # DateTime
    "DateTime": "datetime",
    # Summarize / Aggregate
    "Summarize": "summarize",
    # Join / Merge
    "Join": "join",
    "JoinMultiple": "join",
    "Union": "join",
    "AppendFields": "join",
    "FindReplace": "join",
    "FuzzyMatch": "join",
    "MakeGroup": "join",
    # Sort
    "Sort": "sort",
    # Unique
    "Unique": "unique",
    # Select / Schema
    "Select": "select",
    "AlteryxSelect": "select",
    "AutoField": "select",
    "SelectRecords": "select",
    # Formula
    "Formula": "formula",
    "MultiFieldFormula": "formula",
    "MultiRowFormula": "formula",
    # Data Cleansing
    "DataCleansing": "cleansing",
    "DataCleansePro": "cleansing",
    # Reshape
    "Sample": "reshape",
    "RecordID": "reshape",
    "Transpose": "reshape",
    "CrossTab": "reshape",
    "Arrange": "reshape",
    "MakeColumns": "reshape",
    "RandomSample": "reshape",
    "CreateSamples": "reshape",
    # Regex / Parse
    "RegEx": "regex",
    "TextToColumns": "regex",
    "XMLParse": "regex",
    # Generate Rows
    "GenerateRows": "generate",
    # Running Total
    "RunningTotal": "aggregate",
    # Count Records
    "CountRecords": "aggregate",
}

# Default category for unmapped tool types
DEFAULT_VISUAL_CATEGORY = "transform"


def get_visual_category(tool_type: str) -> str:
    """Return the visual category for a given tool type.

    Falls back to Tool Registry catalog or 'transform' for unmapped types.
    """
    if tool_type in TOOL_VISUAL_CATEGORIES:
        return TOOL_VISUAL_CATEGORIES[tool_type]

    try:
        from awa.tools.catalog import get_tool_catalog
        catalog = get_tool_catalog()
        tool_def = catalog.get(tool_type) or catalog.get_by_display_name(tool_type)
        if tool_def:
            return tool_def.get_visual_category()
    except Exception:
        pass

    return DEFAULT_VISUAL_CATEGORY


# --- Color palette per visual category ---

CATEGORY_COLORS: dict[str, dict[str, str]] = {
    "input": {
        "fill": "#1a3a5c",
        "stroke": "#4fc3f7",
        "badge": "#4fc3f7",
        "text": "#e0f7fa",
    },
    "output": {
        "fill": "#3c1a5c",
        "stroke": "#e040fb",
        "badge": "#e040fb",
        "text": "#f3e5f5",
    },
    "filter": {
        "fill": "#5c4a1a",
        "stroke": "#ffb74d",
        "badge": "#ffb74d",
        "text": "#fff3e0",
    },
    "datetime": {
        "fill": "#2a1a5c",
        "stroke": "#b388ff",
        "badge": "#b388ff",
        "text": "#ede7f6",
    },
    "summarize": {
        "fill": "#1a5c3a",
        "stroke": "#66bb6a",
        "badge": "#66bb6a",
        "text": "#e8f5e9",
    },
    "join": {
        "fill": "#1a4a5c",
        "stroke": "#26c6da",
        "badge": "#26c6da",
        "text": "#e0f2f1",
    },
    "sort": {
        "fill": "#1a3a4c",
        "stroke": "#4dd0e1",
        "badge": "#4dd0e1",
        "text": "#e0f7fa",
    },
    "unique": {
        "fill": "#2a4a3c",
        "stroke": "#81c784",
        "badge": "#81c784",
        "text": "#e8f5e9",
    },
    "select": {
        "fill": "#2a3a4c",
        "stroke": "#78909c",
        "badge": "#78909c",
        "text": "#eceff1",
    },
    "formula": {
        "fill": "#3c2a1a",
        "stroke": "#ffa726",
        "badge": "#ffa726",
        "text": "#fff3e0",
    },
    "cleansing": {
        "fill": "#1a3c3c",
        "stroke": "#4db6ac",
        "badge": "#4db6ac",
        "text": "#e0f2f1",
    },
    "reshape": {
        "fill": "#2a2a4c",
        "stroke": "#9575cd",
        "badge": "#9575cd",
        "text": "#ede7f6",
    },
    "regex": {
        "fill": "#4c2a2a",
        "stroke": "#ef5350",
        "badge": "#ef5350",
        "text": "#ffebee",
    },
    "generate": {
        "fill": "#3c3a1a",
        "stroke": "#d4e157",
        "badge": "#d4e157",
        "text": "#f9fbe7",
    },
    "aggregate": {
        "fill": "#1a4c3a",
        "stroke": "#26a69a",
        "badge": "#26a69a",
        "text": "#e0f2f1",
    },
    "transform": {
        "fill": "#1a2a3c",
        "stroke": "#90a4ae",
        "badge": "#90a4ae",
        "text": "#eceff1",
    },
    "developer": {
        "fill": "#2c223b",
        "stroke": "#ab47bc",
        "badge": "#ab47bc",
        "text": "#f3e5f5",
    },
    "documentation": {
        "fill": "#263238",
        "stroke": "#b0bec5",
        "badge": "#b0bec5",
        "text": "#eceff1",
    },
    "reporting": {
        "fill": "#3e2723",
        "stroke": "#ff8a65",
        "badge": "#ff8a65",
        "text": "#fbe9e7",
    },
    "spatial": {
        "fill": "#004d40",
        "stroke": "#00bfa5",
        "badge": "#00bfa5",
        "text": "#e0f2f1",
    },
    "in_database": {
        "fill": "#1a237e",
        "stroke": "#536dfe",
        "badge": "#536dfe",
        "text": "#e8eaf6",
    },
    "connector": {
        "fill": "#bf360c",
        "stroke": "#ff7043",
        "badge": "#ff7043",
        "text": "#fbe9e7",
    },
}

# Default colors for unknown categories
DEFAULT_CATEGORY_COLORS = CATEGORY_COLORS["transform"]


def get_category_colors(category: str) -> dict[str, str]:
    """Return the color dict for a given visual category.

    Falls back to 'transform' colors for unknown categories.
    """
    return CATEGORY_COLORS.get(category, DEFAULT_CATEGORY_COLORS)


def get_tool_colors(tool_type: str) -> dict[str, str]:
    """Return the color dict for a given tool type.

    Convenience function combining category lookup + color lookup.
    """
    category = get_visual_category(tool_type)
    return get_category_colors(category)
