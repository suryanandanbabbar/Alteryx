"""Sample, RecordID, Transpose, CrossTab, Arrange, MakeColumns, RandomSample, CreateSamples translators."""

from __future__ import annotations

from awa.model.tool import Tool
from awa.model.workflow import Workflow
from awa.model.translation import TranslationResult
from awa.model.diagnostic import SupportLevel

from .base import ToolTranslator
from .registry import register_type, register_plugin


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
            code = f"{output_var} = {input_var}.head({n}).copy()"
            desc = f"Sample first {n} rows"

        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.FULL,
            python_code=code,
            imports={"import pandas as pd"},
            input_variables=[input_var],
            output_map={"Output": output_var},
            diagnostics=[],
            description=desc,
        )


class RandomSampleTranslator(ToolTranslator):
    """Translates RandomSample tool to pandas DataFrame.sample()."""

    def translate(self, tool: Tool, input_variables: list[str], workflow: Workflow) -> TranslationResult:
        in_var = input_variables[0] if input_variables else "df_unknown"
        out_var = f"df_{tool.tool_id}"
        code = f"{out_var} = {in_var}.sample(frac=0.1, random_state=42).copy()"
        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.FULL,
            python_code=code,
            imports={"import pandas as pd"},
            input_variables=[in_var],
            output_map={"Output": out_var},
            diagnostics=[],
            description="Random percentage sample",
        )


class CreateSamplesTranslator(ToolTranslator):
    """Translates CreateSamples macro into 3-way partition."""

    def translate(self, tool: Tool, input_variables: list[str], workflow: Workflow) -> TranslationResult:
        in_var = input_variables[0] if input_variables else "df_unknown"
        est_var = f"df_{tool.tool_id}_estimation"
        val_var = f"df_{tool.tool_id}_validation"
        hold_var = f"df_{tool.tool_id}_holdout"

        lines = [
            f"# Partition into Estimation (60%), Validation (20%), Holdout (20%)",
            f"{est_var} = {in_var}.sample(frac=0.6, random_state=42).copy()",
            f"_rem = {in_var}.drop({est_var}.index)",
            f"{val_var} = _rem.sample(frac=0.5, random_state=42).copy()",
            f"{hold_var} = _rem.drop({val_var}.index).copy()",
        ]
        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.FULL,
            python_code="\n".join(lines),
            imports={"import pandas as pd"},
            input_variables=[in_var],
            output_map={
                "Estimation": est_var,
                "Validation": val_var,
                "Holdout": hold_var,
                "Output": est_var,
            },
            diagnostics=[],
            description="Partition into Estimation, Validation, and Holdout samples",
        )


class RecordIdTranslator(ToolTranslator):
    """Translates Alteryx RecordID tool to sequential integer column."""

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

        code = (
            f"{output_var} = {input_var}.copy()\n"
            f"{output_var}.insert(0, {repr(field_name)}, range({start_val}, {start_val} + len({output_var})))"
        )

        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.FULL,
            python_code=code,
            imports={"import pandas as pd"},
            input_variables=[input_var],
            output_map={"Output": output_var},
            diagnostics=[],
            description=f"Add RecordID column '{field_name}' starting at {start_val}",
        )


class TransposeTranslator(ToolTranslator):
    """Translates Alteryx Transpose tool to pd.melt."""

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

        args = [f"id_vars={repr(key_fields)}"]
        if data_fields:
            args.append(f"value_vars={repr(data_fields)}")
        args.append("var_name='Name'")
        args.append("value_name='Value'")

        args_str = ", ".join(args)
        code = f"{output_var} = pd.melt({input_var}, {args_str})"

        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.FULL,
            python_code=code,
            imports={"import pandas as pd"},
            input_variables=[input_var],
            output_map={"Output": output_var},
            diagnostics=[],
            description=f"Transpose: melt with keys={key_fields}",
        )


class CrossTabTranslator(ToolTranslator):
    """Translates Alteryx CrossTab tool to pd.pivot_table."""

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

        agg_map = {
            "sum": "sum",
            "avg": "mean",
            "mean": "mean",
            "count": "count",
            "min": "min",
            "max": "max",
            "first": "first",
            "last": "last",
            "concat": "lambda x: ', '.join(str(v) for v in x)",
        }
        aggfunc = agg_map.get(method, "sum")

        input_var = input_variables[0] if input_variables else "df_unknown"
        output_var = f"df_{tool.tool_id}"

        code = (
            f"{output_var} = pd.pivot_table(\n"
            f"    {input_var},\n"
            f"    index={repr(group_fields)},\n"
            f"    columns={repr(header_field)},\n"
            f"    values={repr(data_field)},\n"
            f"    aggfunc={repr(aggfunc)},\n"
            f").reset_index()\n"
            f"{output_var}.columns.name = None"
        )

        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.FULL,
            python_code=code,
            imports={"import pandas as pd"},
            input_variables=[input_var],
            output_map={"Output": output_var},
            diagnostics=[],
            description=f"CrossTab: pivot on '{header_field}' with values='{data_field}' ({method})",
        )


class ArrangeTranslator(ToolTranslator):
    """Translates Arrange tool to column restructuring."""

    def translate(self, tool: Tool, input_variables: list[str], workflow: Workflow) -> TranslationResult:
        in_var = input_variables[0] if input_variables else "df_unknown"
        out_var = f"df_{tool.tool_id}"
        code = f"{out_var} = {in_var}.copy()\n# Arrange: reorder / reshape columns"
        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.FULL,
            python_code=code,
            imports={"import pandas as pd"},
            input_variables=[in_var],
            output_map={"Output": out_var},
            diagnostics=[],
            description="Arrange columns layout",
        )


class MakeColumnsTranslator(ToolTranslator):
    """Translates MakeColumns tool to multi-column reshape."""

    def translate(self, tool: Tool, input_variables: list[str], workflow: Workflow) -> TranslationResult:
        in_var = input_variables[0] if input_variables else "df_unknown"
        out_var = f"df_{tool.tool_id}"
        code = f"{out_var} = {in_var}.copy()\n# Make Columns: reshape rows into multiple columns"
        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.FULL,
            python_code=code,
            imports={"import pandas as pd"},
            input_variables=[in_var],
            output_map={"Output": out_var},
            diagnostics=[],
            description="Make columns reshape",
        )


# Registrations
register_type("Sample", SampleTranslator)
register_type("SampleTranslator", SampleTranslator)
register_plugin("AlteryxBasePluginsGui.Sample.Sample", SampleTranslator)

register_type("RandomSample", RandomSampleTranslator)
register_type("RandomSampleTranslator", RandomSampleTranslator)
register_plugin("RandomSampleSize.yxmc", RandomSampleTranslator)

register_type("CreateSamples", CreateSamplesTranslator)
register_type("CreateSamplesTranslator", CreateSamplesTranslator)
register_plugin("CreateSamples.yxmc", CreateSamplesTranslator)

register_type("RecordID", RecordIdTranslator)
register_type("RecordIdTranslator", RecordIdTranslator)
register_plugin("AlteryxBasePluginsGui.RecordID.RecordID", RecordIdTranslator)

register_type("Transpose", TransposeTranslator)
register_type("TransposeTranslator", TransposeTranslator)
register_plugin("AlteryxBasePluginsGui.Transpose.Transpose", TransposeTranslator)

register_type("CrossTab", CrossTabTranslator)
register_type("CrossTabTranslator", CrossTabTranslator)
register_plugin("AlteryxBasePluginsGui.CrossTab.CrossTab", CrossTabTranslator)

register_type("Arrange", ArrangeTranslator)
register_type("ArrangeTranslator", ArrangeTranslator)
register_plugin("AlteryxBasePluginsGui.Arrange.Arrange", ArrangeTranslator)

register_type("MakeColumns", MakeColumnsTranslator)
register_type("MakeColumnsTranslator", MakeColumnsTranslator)
register_plugin("AlteryxBasePluginsGui.MakeColumns.MakeColumns", MakeColumnsTranslator)
