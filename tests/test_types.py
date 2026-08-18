"""Type mapping tests — validates Alteryx → canonical → pandas mapping (C5)."""

import pytest

from awa.model.types import (
    TYPE_MAPPING,
    CanonicalType,
    get_type_mapping,
    alteryx_to_pandas_dtype,
    canonical_to_pandas_dtype,
)


class TestTypeMappingCompleteness:
    """Verify all common Alteryx types are mapped."""

    @pytest.mark.parametrize("alteryx_type", [
        "String", "V_String", "WString", "V_WString",
        "Byte", "Int16", "Int32", "Int64",
        "Float", "Double", "FixedDecimal",
        "Bool",
        "Date", "Time", "DateTime",
        "Blob", "SpatialObj",
    ])
    def test_type_is_mapped(self, alteryx_type):
        mapping = get_type_mapping(alteryx_type)
        assert mapping is not None, f"Alteryx type '{alteryx_type}' is not mapped"
        assert mapping.alteryx_type == alteryx_type
        assert mapping.canonical is not None
        assert mapping.pandas_dtype != ""
        assert mapping.nullable_pandas_dtype != ""


class TestTypeMappingCorrectness:
    """Verify specific type mappings are correct."""

    def test_v_wstring_is_string(self):
        m = get_type_mapping("V_WString")
        assert m.canonical == CanonicalType.STRING
        assert m.pandas_dtype == "object"

    def test_double_is_float64(self):
        m = get_type_mapping("Double")
        assert m.canonical == CanonicalType.DOUBLE
        assert m.pandas_dtype == "float64"

    def test_int32_is_int32(self):
        m = get_type_mapping("Int32")
        assert m.canonical == CanonicalType.INT32
        assert m.pandas_dtype == "int32"
        assert m.nullable_pandas_dtype == "Int32"  # Capital I = nullable

    def test_bool_mapping(self):
        m = get_type_mapping("Bool")
        assert m.canonical == CanonicalType.BOOL
        assert m.pandas_dtype == "bool"
        assert m.nullable_pandas_dtype == "boolean"

    def test_date_is_datetime64(self):
        m = get_type_mapping("Date")
        assert m.canonical == CanonicalType.DATE
        assert m.pandas_dtype == "datetime64[ns]"


class TestConvenienceFunctions:
    """Test the shortcut conversion functions."""

    def test_alteryx_to_pandas_known(self):
        assert alteryx_to_pandas_dtype("V_WString") == "object"
        assert alteryx_to_pandas_dtype("Double") == "float64"
        assert alteryx_to_pandas_dtype("Int32") == "int32"

    def test_alteryx_to_pandas_unknown(self):
        assert alteryx_to_pandas_dtype("UnknownType") == "object"

    def test_alteryx_to_pandas_nullable(self):
        assert alteryx_to_pandas_dtype("Int32", nullable=True) == "Int32"
        assert alteryx_to_pandas_dtype("Bool", nullable=True) == "boolean"
