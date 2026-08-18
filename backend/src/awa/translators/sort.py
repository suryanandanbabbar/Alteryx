"""Sort tool translator."""

from __future__ import annotations

from awa.model.tool import Tool
from awa.model.workflow import Workflow
from awa.model.translation import TranslationResult
from awa.model.diagnostic import SupportLevel

from .base import ToolTranslator
from .registry import register_type


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

        if not sort_fields:
            code = f"{output_var} = {input_var}.copy()"
            desc = "Sort: passthrough"
        else:
            by_cols = [sf.get("field", "") for sf in sort_fields if sf.get("field")]
            ascending = [sf.get("order", "Ascending").lower() != "descending" for sf in sort_fields if sf.get("field")]

            by_repr = repr(by_cols) if len(by_cols) > 1 else repr(by_cols[0])
            asc_repr = repr(ascending) if len(ascending) > 1 else repr(ascending[0])

            code = f"{output_var} = {input_var}.sort_values(by={by_repr}, ascending={asc_repr}).reset_index(drop=True)"
            desc = f"Sort by {by_cols} (ascending={ascending})"

        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.SUPPORTED,
            python_code=code,
            imports={"import pandas as pd"},
            input_variables=[input_var],
            output_map={"Output": output_var},
            diagnostics=[],
            description=desc,
        )


register_type("Sort", SortTranslator)
