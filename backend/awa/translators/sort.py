"""Sort and Rank tool translators."""

from __future__ import annotations

from awa.model.tool import Tool
from awa.model.workflow import Workflow
from awa.model.translation import TranslationResult
from awa.model.diagnostic import Diagnostic, DiagnosticLevel, SupportLevel

from .base import ToolTranslator
from .registry import register_type, register_plugin


class SortTranslator(ToolTranslator):
    """Translates Alteryx Sort tool to DataFrame.sort_values."""

    def translate(
        self,
        tool: Tool,
        input_variables: list[str],
        workflow: Workflow,
    ) -> TranslationResult:
        config = tool.configuration.parsed
        sort_fields = config.get("sort_fields", [])
        input_var = input_variables[0] if input_variables else "df_unknown"
        output_var = f"df_{tool.tool_id}"

        diagnostics: list[Diagnostic] = []
        upstream_schema = getattr(workflow, "_stream_schemas", {}).get(input_var)

        if not sort_fields:
            code = f"{output_var} = {input_var}.copy()"
            desc = "Sort: passthrough"
        else:
            by_cols = [sf.get("field", "") for sf in sort_fields if sf.get("field")]
            ascending = [sf.get("order", "Ascending").lower() != "descending" for sf in sort_fields if sf.get("field")]

            if upstream_schema is not None:
                for col in by_cols:
                    if col not in upstream_schema:
                        diagnostics.append(
                            Diagnostic(
                                level=DiagnosticLevel.WARNING,
                                category="unresolved_field",
                                tool_id=tool.tool_id,
                                tool_type=tool.tool_type,
                                message=f"Tool #{tool.tool_id} (Sort) references missing field '{col}'. Available fields: {upstream_schema}",
                            )
                        )

            by_repr = repr(by_cols) if len(by_cols) > 1 else repr(by_cols[0])
            asc_repr = repr(ascending) if len(ascending) > 1 else repr(ascending[0])

            code = f"{output_var} = {input_var}.sort_values(by={by_repr}, ascending={asc_repr}).reset_index(drop=True)"
            desc = f"Sort by {by_cols} (ascending={ascending})"

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


class RankTranslator(ToolTranslator):
    """Translates Rank macro/tool to Series.rank()."""

    def translate(
        self,
        tool: Tool,
        input_variables: list[str],
        workflow: Workflow,
    ) -> TranslationResult:
        in_var = input_variables[0] if input_variables else "df_unknown"
        out_var = f"df_{tool.tool_id}"
        code = f"{out_var} = {in_var}.copy()\n{out_var}['Rank'] = {out_var}.iloc[:, 0].rank(method='dense').astype(int)"

        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.FULL,
            python_code=code,
            imports={"import pandas as pd"},
            input_variables=[in_var],
            output_map={"Output": out_var},
            diagnostics=[],
            description="Calculate rank order",
        )


register_type("Sort", SortTranslator)
register_type("SortTranslator", SortTranslator)
register_plugin("AlteryxBasePluginsGui.Sort.Sort", SortTranslator)

register_type("Rank", RankTranslator)
register_type("RankTranslator", RankTranslator)
register_plugin("AlteryxBasePluginsGui.Rank.Rank", RankTranslator)
register_plugin("Rank.yxmc", RankTranslator)
