"""Unique tool translator."""

from __future__ import annotations

from awa.model.tool import Tool
from awa.model.workflow import Workflow
from awa.model.translation import TranslationResult
from awa.model.diagnostic import SupportLevel

from .base import ToolTranslator
from .registry import register_type, register_plugin


class UniqueTranslator(ToolTranslator):
    """Translates Alteryx Unique tool to pandas drop_duplicates / duplicated."""

    def translate(
        self,
        tool: Tool,
        input_variables: list[str],
        workflow: Workflow,
    ) -> TranslationResult:
        config = tool.configuration.parsed
        unique_fields = config.get("unique_fields", [])
        input_var = input_variables[0] if input_variables else "df_unknown"

        unique_var = f"df_{tool.tool_id}_unique"
        dups_var = f"df_{tool.tool_id}_duplicates"

        if unique_fields:
            subset_repr = repr(unique_fields)
            code = (
                f"_dup_mask_{tool.tool_id} = {input_var}.duplicated(subset={subset_repr}, keep='first')\n"
                f"{unique_var} = {input_var}[~_dup_mask_{tool.tool_id}].copy().reset_index(drop=True)\n"
                f"{dups_var} = {input_var}[_dup_mask_{tool.tool_id}].copy().reset_index(drop=True)"
            )
            desc = f"Unique on {unique_fields}"
        else:
            code = (
                f"_dup_mask_{tool.tool_id} = {input_var}.duplicated(keep='first')\n"
                f"{unique_var} = {input_var}[~_dup_mask_{tool.tool_id}].copy().reset_index(drop=True)\n"
                f"{dups_var} = {input_var}[_dup_mask_{tool.tool_id}].copy().reset_index(drop=True)"
            )
            desc = "Unique on all columns"

        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.FULL,
            python_code=code,
            imports={"import pandas as pd"},
            input_variables=[input_var],
            output_map={
                "Unique": unique_var,
                "Duplicates": dups_var,
            },
            diagnostics=[],
            description=desc,
        )


register_type("Unique", UniqueTranslator)
register_type("UniqueTranslator", UniqueTranslator)
register_plugin("AlteryxBasePluginsGui.Unique.Unique", UniqueTranslator)
