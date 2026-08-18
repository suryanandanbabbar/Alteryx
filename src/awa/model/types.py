"""Alteryx → canonical → pandas type mapping.

This module provides a formal, tested mapping between Alteryx XML type strings,
AWA canonical type names, and pandas/numpy dtypes.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CanonicalType(Enum):
    """AWA canonical types — the intermediate between Alteryx and pandas."""
    STRING = "string"
    INT16 = "int16"
    INT32 = "int32"
    INT64 = "int64"
    FLOAT = "float"
    DOUBLE = "double"
    FIXED_DECIMAL = "fixed_decimal"
    BOOL = "bool"
    DATE = "date"
    TIME = "time"
    DATETIME = "datetime"
    BLOB = "blob"
    SPATIAL = "spatial"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class TypeMapping:
    """Maps an Alteryx type to its canonical and pandas representations."""
    alteryx_type: str
    canonical: CanonicalType
    pandas_dtype: str
    nullable_pandas_dtype: str  # pandas nullable dtype for null-safe operations


# Comprehensive Alteryx → canonical → pandas mapping.
# Sources: Alteryx documentation, observed .yxmd files.
TYPE_MAPPING: dict[str, TypeMapping] = {
    # String types
    "String": TypeMapping("String", CanonicalType.STRING, "object", "string"),
    "V_String": TypeMapping("V_String", CanonicalType.STRING, "object", "string"),
    "WString": TypeMapping("WString", CanonicalType.STRING, "object", "string"),
    "V_WString": TypeMapping("V_WString", CanonicalType.STRING, "object", "string"),
    # Integer types
    "Byte": TypeMapping("Byte", CanonicalType.INT16, "int16", "Int16"),
    "Int16": TypeMapping("Int16", CanonicalType.INT16, "int16", "Int16"),
    "Int32": TypeMapping("Int32", CanonicalType.INT32, "int32", "Int32"),
    "Int64": TypeMapping("Int64", CanonicalType.INT64, "int64", "Int64"),
    # Float types
    "Float": TypeMapping("Float", CanonicalType.FLOAT, "float32", "Float32"),
    "Double": TypeMapping("Double", CanonicalType.DOUBLE, "float64", "Float64"),
    "FixedDecimal": TypeMapping("FixedDecimal", CanonicalType.FIXED_DECIMAL, "float64", "Float64"),
    # Boolean
    "Bool": TypeMapping("Bool", CanonicalType.BOOL, "bool", "boolean"),
    # Date/Time types
    "Date": TypeMapping("Date", CanonicalType.DATE, "datetime64[ns]", "datetime64[ns]"),
    "Time": TypeMapping("Time", CanonicalType.TIME, "object", "object"),
    "DateTime": TypeMapping("DateTime", CanonicalType.DATETIME, "datetime64[ns]", "datetime64[ns]"),
    # Binary/Spatial
    "Blob": TypeMapping("Blob", CanonicalType.BLOB, "object", "object"),
    "SpatialObj": TypeMapping("SpatialObj", CanonicalType.SPATIAL, "object", "object"),
}


def get_type_mapping(alteryx_type: str) -> TypeMapping | None:
    """Look up the type mapping for an Alteryx type string.
    
    Returns None if the type is not recognized.
    """
    return TYPE_MAPPING.get(alteryx_type)


def canonical_to_pandas_dtype(canonical: CanonicalType, nullable: bool = False) -> str:
    """Get the pandas dtype string for a canonical type.
    
    Args:
        canonical: The canonical type.
        nullable: If True, return the nullable pandas dtype variant.
    
    Returns:
        pandas dtype string.
    """
    # Reverse lookup — find first mapping with this canonical type
    for mapping in TYPE_MAPPING.values():
        if mapping.canonical == canonical:
            return mapping.nullable_pandas_dtype if nullable else mapping.pandas_dtype
    return "object"


def alteryx_to_pandas_dtype(alteryx_type: str, nullable: bool = False) -> str:
    """Convert an Alteryx type string directly to a pandas dtype string.
    
    Args:
        alteryx_type: The Alteryx type string (e.g., 'V_WString', 'Double').
        nullable: If True, return the nullable pandas dtype variant.
    
    Returns:
        pandas dtype string. Defaults to 'object' for unknown types.
    """
    mapping = TYPE_MAPPING.get(alteryx_type)
    if mapping is None:
        return "object"
    return mapping.nullable_pandas_dtype if nullable else mapping.pandas_dtype
