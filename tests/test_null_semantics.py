"""Dedicated null/semantic tests (Constraint C6).

Verifies that the generated pandas code executes and handles NULL/None/NaN
semantics appropriately for Filter, Formula, and expression functions.
"""

import numpy as np
import pandas as pd
import pytest

from backend.src.awa.expressions.pandas_emitter import emit_pandas


class TestNullSemanticsInExpressions:
    """Test execution of generated pandas code against DataFrames with nulls."""

    def test_isnull_execution(self):
        df = pd.DataFrame({"Revenue": [100.0, None, 250.0, np.nan]})
        expr, imports = emit_pandas("IsNull([Revenue])", "df")
        # Evaluate expr
        mask = eval(expr, {"df": df, "np": np, "pd": pd})
        assert list(mask) == [False, True, False, True]

    def test_isnotnull_execution(self):
        df = pd.DataFrame({"Revenue": [100.0, None, 250.0, np.nan]})
        expr, imports = emit_pandas("IsNotNull([Revenue])", "df")
        mask = eval(expr, {"df": df, "np": np, "pd": pd})
        assert list(mask) == [True, False, True, False]

    def test_coalesce_execution(self):
        df = pd.DataFrame({"A": [None, 20.0, None, 40.0], "B": [1.0, 2.0, 3.0, 4.0]})
        expr, imports = emit_pandas("Coalesce([A], [B])", "df")
        result = eval(expr, {"df": df, "np": np, "pd": pd})
        assert list(result) == [1.0, 20.0, 3.0, 40.0]

    def test_if_else_with_nulls(self):
        df = pd.DataFrame({"Status": ["active", None, "inactive", "active"]})
        expr, imports = emit_pandas('IF [Status] = "active" THEN "Yes" ELSE "No" ENDIF', "df")
        result = eval(expr, {"df": df, "np": np, "pd": pd})
        # Null compared with "active" is False in boolean comparison, resulting in "No"
        assert list(result) == ["Yes", "No", "No", "Yes"]

    def test_filter_with_null_and_boolean_mask(self):
        df = pd.DataFrame({
            "name": ["Alice", "Bob", "Charlie", "David"],
            "status": ["active", None, "active", "inactive"],
            "revenue": [150.0, 200.0, np.nan, 50.0]
        })
        expr, imports = emit_pandas('[status] = "active" AND [revenue] > 100', "df")
        mask = eval(expr, {"df": df, "np": np, "pd": pd})
        filtered_true = df[mask]
        # Only Alice has status=="active" AND revenue > 100 (Charlie has revenue NaN which is not > 100)
        assert len(filtered_true) == 1
        assert list(filtered_true["name"]) == ["Alice"]

    def test_arithmetic_with_null_propagates(self):
        df = pd.DataFrame({"Quantity": [10, None, 5], "UnitPrice": [2.5, 3.0, None]})
        expr, imports = emit_pandas("[Quantity] * [UnitPrice]", "df")
        result = eval(expr, {"df": df, "np": np, "pd": pd})
        assert result.iloc[0] == 25.0
        assert pd.isna(result.iloc[1])
        assert pd.isna(result.iloc[2])

    def test_string_trim_with_null_handling(self):
        df = pd.DataFrame({"Name": ["  Alice  ", None, "Bob "]})
        expr, imports = emit_pandas("Trim([Name])", "df")
        result = eval(expr, {"df": df, "np": np, "pd": pd})
        assert result.iloc[0] == "Alice"
        assert pd.isna(result.iloc[1])
        assert result.iloc[2] == "Bob"
