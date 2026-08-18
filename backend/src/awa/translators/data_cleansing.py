"""DataCleansing tool translator."""

from __future__ import annotations

from awa.model.tool import Tool
from awa.model.workflow import Workflow
from awa.model.translation import TranslationResult
from awa.model.diagnostic import SupportLevel

from .base import ToolTranslator
from .registry import register_type


class DataCleansingTranslator(ToolTranslator):
    """Translates Alteryx DataCleansing tool (nulls, whitespace, case)."""

    def translate(
        self,
        tool: Tool,
        input_variables: list[str],
        workflow: Workflow,
    ) -> TranslationResult:
        config = tool.configuration.parsed
        fields = config.get("cleansing_fields", [])
        remove_null = config.get("removenull", False)
        remove_ws = config.get("removewhitespace", False)
        trim_ws = config.get("trimwhitespace", True)
        modify_case = config.get("modify_case", "").lower()

        input_var = input_variables[0] if input_variables else "df_unknown"
        output_var = f"df_{tool.tool_id}"

        lines = [f"{output_var} = {input_var}.copy()"]

        target_cols = fields if fields else []

        if target_cols:
            for col in target_cols:
                col_repr = repr(col)
                if trim_ws:
                    lines.append(f'if {col_repr} in {output_var}.columns and {output_var}[{col_repr}].dtype == "object":')
                    lines.append(f'    {output_var}[{col_repr}] = {output_var}[{col_repr}].str.strip()')
                if remove_ws:
                    lines.append(f'if {col_repr} in {output_var}.columns and {output_var}[{col_repr}].dtype == "object":')
                    lines.append(f'    {output_var}[{col_repr}] = {output_var}[{col_repr}].str.replace(r"\\s+", "", regex=True)')
                if modify_case == "upper":
                    lines.append(f'if {col_repr} in {output_var}.columns and {output_var}[{col_repr}].dtype == "object":')
                    lines.append(f'    {output_var}[{col_repr}] = {output_var}[{col_repr}].str.upper()')
                elif modify_case == "lower":
                    lines.append(f'if {col_repr} in {output_var}.columns and {output_var}[{col_repr}].dtype == "object":')
                    lines.append(f'    {output_var}[{col_repr}] = {output_var}[{col_repr}].str.lower()')
                elif modify_case == "title":
                    lines.append(f'if {col_repr} in {output_var}.columns and {output_var}[{col_repr}].dtype == "object":')
                    lines.append(f'    {output_var}[{col_repr}] = {output_var}[{col_repr}].str.title()')
                if remove_null:
                    lines.append(f'if {col_repr} in {output_var}.columns:')
                    lines.append(f'    {output_var} = {output_var}[{output_var}[{col_repr}].notna()]')
        else:
            # Apply to all string columns
            if trim_ws:
                lines.append(f'for _c in {output_var}.select_dtypes(include=["object"]).columns:')
                lines.append(f'    {output_var}[_c] = {output_var}[_c].str.strip()')
            if remove_null:
                lines.append(f'{output_var} = {output_var}.dropna()')

        code = "\n".join(lines)

        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.SUPPORTED,
            python_code=code,
            imports={"import pandas as pd"},
            input_variables=[input_var],
            output_map={"Output": output_var},
            diagnostics=[],
            description=f"DataCleansing: trim={trim_ws}, remove_null={remove_null}",
        )


register_type("DataCleansing", DataCleansingTranslator)
