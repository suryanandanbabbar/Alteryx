"""Expression engine tests — validates parsing and pandas emission."""

import pytest

from backend.src.awa.expressions.parser import parse_expression
from backend.src.awa.expressions.pandas_emitter import PandasEmitter, emit_pandas


class TestExpressionParsing:
    """Test that Alteryx expressions parse without errors."""

    @pytest.mark.parametrize("expr", [
        "[Revenue] > 100",
        "[Quantity] * [UnitPrice]",
        '[FirstName] + " " + [LastName]',
        '[status] = "active"',
        "[A] > 0 AND [B] < 100",
        "[X] = 1 OR [Y] = 2",
        "NOT [Flag]",
        "IF [Revenue] > 100000 THEN \"High\" ELSE \"Low\" ENDIF",
        "IsNull([Revenue])",
        "Trim([Name])",
        "[A] + [B] - [C]",
        "[A] * [B] / [C]",
        "[A] >= 10",
        "[A] <= 10",
        "[A] != [B]",
    ])
    def test_parse_succeeds(self, expr):
        tree = parse_expression(expr)
        assert tree is not None


class TestPandasEmission:
    """Test pandas code emission for various expression patterns."""

    def test_field_reference(self):
        code, _ = emit_pandas("[Revenue]")
        assert 'df["Revenue"]' in code

    def test_arithmetic(self):
        code, _ = emit_pandas("[Quantity] * [UnitPrice]")
        assert 'df["Quantity"]' in code
        assert 'df["UnitPrice"]' in code
        assert "*" in code

    def test_comparison(self):
        code, _ = emit_pandas("[Revenue] > 100")
        assert 'df["Revenue"]' in code
        assert "> 100" in code

    def test_string_concatenation(self):
        code, _ = emit_pandas('[FirstName] + " " + [LastName]')
        assert 'df["FirstName"]' in code
        assert 'df["LastName"]' in code
        assert "+" in code

    def test_and_expression(self):
        code, _ = emit_pandas('[status] = "active" AND [revenue] > 100')
        assert "&" in code
        assert 'df["status"]' in code
        assert 'df["revenue"]' in code

    def test_or_expression(self):
        code, _ = emit_pandas("[A] = 1 OR [B] = 2")
        assert "|" in code

    def test_not_expression(self):
        code, _ = emit_pandas("NOT [Flag]")
        assert "~" in code

    def test_if_else(self):
        code, imports = emit_pandas(
            'IF [Revenue] > 100000 THEN "High" ELSE "Low" ENDIF'
        )
        assert "np.where" in code
        assert "import numpy as np" in imports

    def test_isnull(self):
        code, _ = emit_pandas("IsNull([Revenue])")
        assert ".isna()" in code

    def test_trim(self):
        code, _ = emit_pandas("Trim([Name])")
        assert ".str.strip()" in code

    def test_custom_df_var(self):
        code, _ = emit_pandas("[Amount]", df_var="sales")
        assert 'sales["Amount"]' in code

    def test_nested_arithmetic(self):
        code, _ = emit_pandas("([A] + [B]) * [C]")
        assert 'df["A"]' in code
        assert 'df["B"]' in code
        assert 'df["C"]' in code

    def test_number_literal(self):
        code, _ = emit_pandas("[Revenue] > 100000")
        assert "100000" in code

    def test_uppercase_function(self):
        code, _ = emit_pandas("Uppercase([Name])")
        assert ".str.upper()" in code

    def test_lowercase_function(self):
        code, _ = emit_pandas("Lowercase([Name])")
        assert ".str.lower()" in code

    def test_length_function(self):
        code, _ = emit_pandas("Length([Name])")
        assert ".str.len()" in code

    def test_abs_function(self):
        code, _ = emit_pandas("ABS([Amount])")
        assert ".abs()" in code

    def test_round_function(self):
        code, _ = emit_pandas("Round([Price], 2)")
        assert ".round(" in code

    def test_coalesce_function(self):
        code, _ = emit_pandas("Coalesce([A], 0)")
        assert ".fillna(" in code
