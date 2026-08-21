"""Summarize / CountRecords / RunningTotal translators."""

from __future__ import annotations

from awa.model.tool import Tool
from awa.model.workflow import Workflow
from awa.model.translation import TranslationResult
from awa.model.diagnostic import Diagnostic, DiagnosticLevel, SupportLevel

from .base import ToolTranslator
from .registry import register_type, register_plugin


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
        group_by_renames: dict[str, str] = {}
        agg_specs: list[tuple[str, str, str]] = []

        upstream_schema = getattr(workflow, "_stream_schemas", {}).get(input_var)
        if upstream_schema is not None:
            for sf in summarize_fields:
                field = sf.get("field", "")
                if field and field not in upstream_schema:
                    diagnostics.append(
                        Diagnostic(
                            level=DiagnosticLevel.WARNING,
                            category="unresolved_field",
                            tool_id=tool.tool_id,
                            tool_type=tool.tool_type,
                            message=f"Tool #{tool.tool_id} (Summarize) references missing field '{field}'. Available fields: {upstream_schema}",
                        )
                    )

        for sf in summarize_fields:
            field = sf.get("field", "")
            action = sf.get("action", "")
            rename = sf.get("rename", "")
            action_lower = action.lower()

            if action_lower == "groupby":
                group_by_cols.append(field)
                if rename and rename != field:
                    group_by_renames[field] = rename
            else:
                out_name = rename or f"{action}_{field}"
                agg_func = _ACTION_MAP.get(action_lower, "first")
                agg_specs.append((out_name, field, agg_func))

        rename_suffix = f".rename(columns={repr(group_by_renames)})" if group_by_renames else ""

        if not summarize_fields:
            code = f"{output_var} = {input_var}.copy()"
            desc = "Summarize (empty)"
        elif group_by_cols and agg_specs:
            agg_entries = ", ".join(f'{repr(out_col)}: ({repr(in_col)}, {repr(func)})' for out_col, in_col, func in agg_specs)
            grp_repr = repr(group_by_cols)
            code = f"{output_var} = {input_var}.groupby({grp_repr}, as_index=False).agg(**{{{agg_entries}}}){rename_suffix}"
            desc = f"Summarize: Group by {group_by_cols} with {len(agg_specs)} aggregation(s)"
        elif group_by_cols and not agg_specs:
            grp_repr = repr(group_by_cols)
            code = f"{output_var} = {input_var}[{grp_repr}].drop_duplicates().reset_index(drop=True){rename_suffix}"
            desc = f"Summarize: Distinct on {group_by_cols}"
        elif not group_by_cols and agg_specs:
            dict_entries = ", ".join(f'{repr(out_col)}: [{input_var}[{repr(in_col)}].{func}()]' for out_col, in_col, func in agg_specs)
            code = f"{output_var} = pd.DataFrame({{{dict_entries}}})"
            desc = f"Summarize: Global aggregation ({len(agg_specs)} metric(s))"
        else:
            code = f"{output_var} = {input_var}.copy()"
            desc = "Summarize passthrough"

        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.FULL,
            python_code=code,
            imports={"import pandas as pd"},
            input_variables=[input_var],
            output_map={"Output": output_var},
            diagnostics=diagnostics,
            description=desc,
        )


class CountRecordsTranslator(ToolTranslator):
    """Translates CountRecords macro/tool to DataFrame row count."""

    def translate(self, tool: Tool, input_variables: list[str], workflow: Workflow) -> TranslationResult:
        in_var = input_variables[0] if input_variables else "df_unknown"
        out_var = f"df_{tool.tool_id}"
        code = f"{out_var} = pd.DataFrame({{'Count': [len({in_var})]}})"
        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.FULL,
            python_code=code,
            imports={"import pandas as pd"},
            input_variables=[in_var],
            output_map={"Output": out_var},
            diagnostics=[],
            description="Count total records",
        )


class RunningTotalTranslator(ToolTranslator):
    """Translates RunningTotal tool to Series.cumsum()."""

    def translate(self, tool: Tool, input_variables: list[str], workflow: Workflow) -> TranslationResult:
        in_var = input_variables[0] if input_variables else "df_unknown"
        out_var = f"df_{tool.tool_id}"
        code = f"{out_var} = {in_var}.copy()\n{out_var}['RunningTotal'] = {out_var}.iloc[:, 0].cumsum()"
        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.FULL,
            python_code=code,
            imports={"import pandas as pd"},
            input_variables=[in_var],
            output_map={"Output": out_var},
            diagnostics=[],
            description="Calculate cumulative running total",
        )


# Registrations
register_type("Summarize", SummarizeTranslator)
register_type("SummarizeTranslator", SummarizeTranslator)
register_plugin("AlteryxSpatialPluginsGui.Summarize.Summarize", SummarizeTranslator)
register_plugin("AlteryxBasePluginsGui.Summarize.Summarize", SummarizeTranslator)

register_type("CountRecords", CountRecordsTranslator)
register_type("CountRecordsTranslator", CountRecordsTranslator)
register_plugin("CountRecords.yxmc", CountRecordsTranslator)
register_plugin("AlteryxBasePluginsGui.CountRecords.CountRecords", CountRecordsTranslator)

register_type("RunningTotal", RunningTotalTranslator)
register_type("RunningTotalTranslator", RunningTotalTranslator)
register_plugin("AlteryxBasePluginsGui.RunningTotal.RunningTotal", RunningTotalTranslator)
