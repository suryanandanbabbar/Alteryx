"""Summarize tool translator.

Performs aggregations: GroupBy, Sum, Count, Min, Max, Avg, First, Last, etc.
"""

from __future__ import annotations

from backend.src.awa.model.tool import Tool
from backend.src.awa.model.workflow import Workflow
from backend.src.awa.model.translation import TranslationResult
from backend.src.awa.model.diagnostic import Diagnostic, DiagnosticLevel, SupportLevel

from .base import ToolTranslator
from .registry import register_type


# Action mapping from Alteryx Summarize actions to pandas aggregation methods
_ACTION_MAP = {
    "groupby": None,
    "sum": "sum",
    "count": "count",
    "countdistinct": "nunique",
    "countnonnull": "count",
    "min": "min",
    "max": "max",
    "avg": "mean",
    "first": "first",
    "last": "last",
    "stddev": "std",
    "variance": "var",
}


class SummarizeTranslator(ToolTranslator):
    """Translates Alteryx Summarize tool to pandas groupby / agg operations."""

    def translate(
        self,
        tool: Tool,
        input_variables: list[str],
        workflow: Workflow,
    ) -> TranslationResult:
        config = tool.configuration.parsed
        summarize_fields = config.get("summarize_fields", [])
        input_var = input_variables[0] if input_variables else "df_unknown"
        output_var = f"df_{tool.tool_id}"

        diagnostics: list[Diagnostic] = []
        group_by_cols: list[str] = []
        agg_specs: list[tuple[str, str, str]] = []  # (output_col, input_col, pandas_func)

        for sf in summarize_fields:
            field = sf.get("field", "")
            action = sf.get("action", "")
            rename = sf.get("rename", "") or f"{action}_{field}"
            action_lower = action.lower()

            if action_lower == "groupby":
                group_by_cols.append(field)
            else:
                agg_func = _ACTION_MAP.get(action_lower, "first")
                agg_specs.append((rename, field, agg_func))

        if not summarize_fields:
            code = f"{output_var} = {input_var}.copy()"
            desc = "Summarize (empty)"
        elif group_by_cols and agg_specs:
            # Group by + Aggregations using named agg
            agg_kwargs = ", ".join(f'{out_col}=("{in_col}", "{func}")' for out_col, in_col, func in agg_specs)
            grp_repr = repr(group_by_cols)
            code = f"{output_var} = {input_var}.groupby({grp_repr}, as_index=False).agg({agg_kwargs})"
            desc = f"Summarize: Group by {group_by_cols} with {len(agg_specs)} aggregation(s)"
        elif group_by_cols and not agg_specs:
            # Group by only -> drop duplicates of group by keys
            grp_repr = repr(group_by_cols)
            code = f"{output_var} = {input_var}[{grp_repr}].drop_duplicates().reset_index(drop=True)"
            desc = f"Summarize: Distinct on {group_by_cols}"
        elif not group_by_cols and agg_specs:
            # Global aggregations across all rows
            agg_lines = []
            dict_entries = ", ".join(f'"{out_col}": [{input_var}["{in_col}"].{func}()]' for out_col, in_col, func in agg_specs)
            code = f"{output_var} = pd.DataFrame({{{dict_entries}}})"
            desc = f"Summarize: Global aggregation ({len(agg_specs)} metric(s))"
        else:
            code = f"{output_var} = {input_var}.copy()"
            desc = "Summarize passthrough"

        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.SUPPORTED,
            python_code=code,
            imports={"import pandas as pd"},
            input_variables=[input_var],
            output_map={"Output": output_var},
            diagnostics=diagnostics,
            description=desc,
        )


register_type("Summarize", SummarizeTranslator)
