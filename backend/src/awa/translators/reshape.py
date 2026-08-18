"""Sample, RecordID, Transpose, and CrossTab translators."""

from __future__ import annotations

from backend.src.awa.model.tool import Tool
from backend.src.awa.model.workflow import Workflow
from backend.src.awa.model.translation import TranslationResult
from backend.src.awa.model.diagnostic import SupportLevel

from .base import ToolTranslator
from .registry import register_type


class SampleTranslator(ToolTranslator):
    """Translates Alteryx Sample tool (first N, last N, random %, 1 of N)."""

    def translate(
        self,
        tool: Tool,
        input_variables: list[str],
        workflow: Workflow,
    ) -> TranslationResult:
        config = tool.configuration.parsed
        mode = config.get("sample_mode", "First").lower()
        n = config.get("sample_n", 100)
        pct = config.get("sample_pct")

        input_var = input_variables[0] if input_variables else "df_unknown"
        output_var = f"df_{tool.tool_id}"

        if "last" in mode:
            code = f"{output_var} = {input_var}.tail({n}).copy()"
            desc = f"Sample last {n} rows"
        elif "random" in mode:
            if pct is not None:
                frac = float(pct) / 100.0
                code = f"{output_var} = {input_var}.sample(frac={frac}, random_state=42).copy()"
                desc = f"Sample random {pct}%"
            else:
                code = f"{output_var} = {input_var}.sample(n=min({n}, len({input_var})), random_state=42).copy()"
                desc = f"Sample random {n} rows"
        elif "skip" in mode:
            code = f"{output_var} = {input_var}.iloc[{n}:].copy()"
            desc = f"Sample skip first {n} rows"
        else:
            # Default: First N
            code = f"{output_var} = {input_var}.head({n}).copy()"
            desc = f"Sample first {n} rows"

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


class RecordIDTranslator(ToolTranslator):
    """Translates Alteryx RecordID tool (adds sequential integer ID column)."""

    def translate(
        self,
        tool: Tool,
        input_variables: list[str],
        workflow: Workflow,
    ) -> TranslationResult:
        config = tool.configuration.parsed
        field_name = config.get("field_name", "RecordID")
        start_val = config.get("start_value", 1)

        input_var = input_variables[0] if input_variables else "df_unknown"
        output_var = f"df_{tool.tool_id}"

        field_repr = repr(field_name)
        code = (
            f"{output_var} = {input_var}.copy()\n"
            f'{output_var}.insert(0, {field_repr}, range({start_val}, {start_val} + len({output_var})))'
        )

        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.SUPPORTED,
            python_code=code,
            imports={"import pandas as pd"},
            input_variables=[input_var],
            output_map={"Output": output_var},
            diagnostics=[],
            description=f"RecordID: Add '{field_name}' starting at {start_val}",
        )


class TransposeTranslator(ToolTranslator):
    """Translates Alteryx Transpose tool (unpivoting columns to rows via pd.melt)."""

    def translate(
        self,
        tool: Tool,
        input_variables: list[str],
        workflow: Workflow,
    ) -> TranslationResult:
        config = tool.configuration.parsed
        key_fields = config.get("key_fields", [])
        data_fields = config.get("data_fields", [])

        input_var = input_variables[0] if input_variables else "df_unknown"
        output_var = f"df_{tool.tool_id}"

        id_vars_repr = repr(key_fields)
        val_vars_repr = repr(data_fields) if data_fields else "None"

        code = (
            f"{output_var} = pd.melt(\n"
            f"    {input_var},\n"
            f"    id_vars={id_vars_repr},\n"
            f"    value_vars={val_vars_repr},\n"
            f"    var_name='Name',\n"
            f"    value_name='Value'\n"
            f")"
        )

        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.SUPPORTED,
            python_code=code,
            imports={"import pandas as pd"},
            input_variables=[input_var],
            output_map={"Output": output_var},
            diagnostics=[],
            description=f"Transpose: keys={key_fields}, data={data_fields}",
        )


class CrossTabTranslator(ToolTranslator):
    """Translates Alteryx CrossTab tool (pivoting rows to columns via pd.pivot_table)."""

    def translate(
        self,
        tool: Tool,
        input_variables: list[str],
        workflow: Workflow,
    ) -> TranslationResult:
        config = tool.configuration.parsed
        group_fields = config.get("group_fields", [])
        header_field = config.get("header_field", "")
        data_field = config.get("data_field", "")
        method = config.get("method", "Sum").lower()

        aggfunc = "sum" if "sum" in method else ("count" if "count" in method else "first")

        input_var = input_variables[0] if input_variables else "df_unknown"
        output_var = f"df_{tool.tool_id}"

        index_repr = repr(group_fields)
        columns_repr = repr(header_field)
        values_repr = repr(data_field)

        code = (
            f"{output_var} = pd.pivot_table(\n"
            f"    {input_var},\n"
            f"    index={index_repr},\n"
            f"    columns={columns_repr},\n"
            f"    values={values_repr},\n"
            f"    aggfunc='{aggfunc}'\n"
            f").reset_index()\n"
            f"{output_var}.columns.name = None"
        )

        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.SUPPORTED,
            python_code=code,
            imports={"import pandas as pd"},
            input_variables=[input_var],
            output_map={"Output": output_var},
            diagnostics=[],
            description=f"CrossTab: rows={group_fields}, cols={header_field}, val={data_field}",
        )


register_type("Sample", SampleTranslator)
register_type("RecordID", RecordIDTranslator)
register_type("Transpose", TransposeTranslator)
register_type("CrossTab", CrossTabTranslator)
