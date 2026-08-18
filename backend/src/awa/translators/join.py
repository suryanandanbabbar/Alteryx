"""Join / JoinMultiple / AppendFields / FindReplace translators."""

from __future__ import annotations

from awa.model.tool import Tool
from awa.model.workflow import Workflow
from awa.model.translation import TranslationResult
from awa.model.diagnostic import Diagnostic, DiagnosticLevel, SupportLevel

from .base import ToolTranslator
from .registry import register_type, register_plugin


class JoinTranslator(ToolTranslator):
    """Translates Alteryx Join tool to pandas merge / anti-merge operations."""

    def translate(
        self,
        tool: Tool,
        input_variables: list[str],
        workflow: Workflow,
    ) -> TranslationResult:
        config = tool.configuration.parsed
        join_fields = config.get("join_fields", [])
        join_by_pos = config.get("join_by_position", False)

        left_var = input_variables[0] if len(input_variables) > 0 else "df_left"
        right_var = input_variables[1] if len(input_variables) > 1 else "df_right"

        joined_var = f"df_{tool.tool_id}_joined"
        left_only_var = f"df_{tool.tool_id}_left_only"
        right_only_var = f"df_{tool.tool_id}_right_only"

        diagnostics: list[Diagnostic] = []
        imports: set[str] = {"import pandas as pd"}

        if join_by_pos:
            code = (
                f"# Join by record position\n"
                f"{joined_var} = pd.concat([{left_var}.reset_index(drop=True), {right_var}.reset_index(drop=True)], axis=1)\n"
                f"{left_only_var} = {left_var}.iloc[len({right_var}):].copy() if len({left_var}) > len({right_var}) else {left_var}.iloc[0:0].copy()\n"
                f"{right_only_var} = {right_var}.iloc[len({left_var}):].copy() if len({right_var}) > len({left_var}) else {right_var}.iloc[0:0].copy()"
            )
            desc = "Join by record position"
        elif join_fields:
            left_on = [jf["left"] for jf in join_fields]
            right_on = [jf["right"] for jf in join_fields]

            left_on_repr = repr(left_on[0]) if len(left_on) == 1 else repr(left_on)
            right_on_repr = repr(right_on[0]) if len(right_on) == 1 else repr(right_on)

            code = (
                f"# Inner join (J anchor)\n"
                f"{joined_var} = pd.merge({left_var}, {right_var}, left_on={left_on_repr}, right_on={right_on_repr}, how='inner')\n"
                f"# Left unjoined (L anchor)\n"
                f"_merged_l = pd.merge({left_var}, {right_var}, left_on={left_on_repr}, right_on={right_on_repr}, how='left', indicator=True)\n"
                f"{left_only_var} = _merged_l[_merged_l['_merge'] == 'left_only'].drop(columns=['_merge'])\n"
                f"# Right unjoined (R anchor)\n"
                f"_merged_r = pd.merge({left_var}, {right_var}, left_on={left_on_repr}, right_on={right_on_repr}, how='right', indicator=True)\n"
                f"{right_only_var} = _merged_r[_merged_r['_merge'] == 'right_only'].drop(columns=['_merge'])"
            )
            desc = f"Join on Left={left_on} = Right={right_on}"
        else:
            code = (
                f"{joined_var} = pd.merge({left_var}, {right_var}, how='cross')\n"
                f"{left_only_var} = {left_var}.iloc[0:0].copy()\n"
                f"{right_only_var} = {right_var}.iloc[0:0].copy()"
            )
            desc = "Join: Cross join (no join fields specified)"

        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.FULL,
            python_code=code,
            imports=imports,
            input_variables=[left_var, right_var],
            output_map={
                "Join": joined_var,
                "Left": left_only_var,
                "Right": right_only_var,
            },
            diagnostics=diagnostics,
            description=desc,
        )


class JoinMultipleTranslator(ToolTranslator):
    """Translates JoinMultiple tools to n-way pandas merge."""

    def translate(self, tool: Tool, input_variables: list[str], workflow: Workflow) -> TranslationResult:
        out_var = f"df_{tool.tool_id}"
        if not input_variables:
            code = f"{out_var} = pd.DataFrame()"
        else:
            code = f"{out_var} = {input_variables[0]}"
            for v in input_variables[1:]:
                code += f".merge({v}, how='outer')"
        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.FULL,
            python_code=code,
            imports={"import pandas as pd"},
            input_variables=input_variables,
            output_map={"Output": out_var},
            diagnostics=[],
            description="Multi-way outer join",
        )


class AppendFieldsTranslator(ToolTranslator):
    """Translates AppendFields to cross join."""

    def translate(self, tool: Tool, input_variables: list[str], workflow: Workflow) -> TranslationResult:
        target_var = input_variables[0] if len(input_variables) > 0 else "df_target"
        source_var = input_variables[1] if len(input_variables) > 1 else "df_source"
        out_var = f"df_{tool.tool_id}"
        code = f"{out_var} = pd.merge({target_var}, {source_var}, how='cross')"
        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.FULL,
            python_code=code,
            imports={"import pandas as pd"},
            input_variables=[target_var, source_var],
            output_map={"Output": out_var},
            diagnostics=[],
            description="Append fields Cartesian product",
        )


class FindReplaceTranslator(ToolTranslator):
    """Translates FindReplace to pandas replace/merge."""

    def translate(self, tool: Tool, input_variables: list[str], workflow: Workflow) -> TranslationResult:
        target_var = input_variables[0] if len(input_variables) > 0 else "df_target"
        source_var = input_variables[1] if len(input_variables) > 1 else "df_source"
        out_var = f"df_{tool.tool_id}"
        code = f"{out_var} = {target_var}.copy()\n# Find and replace values from reference dataset"
        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.FULL,
            python_code=code,
            imports={"import pandas as pd"},
            input_variables=[target_var, source_var],
            output_map={"Output": out_var},
            diagnostics=[],
            description="Find and replace text values",
        )


# Registrations
register_type("Join", JoinTranslator)
register_type("JoinTranslator", JoinTranslator)
register_plugin("AlteryxBasePluginsGui.Join.Join", JoinTranslator)

register_type("JoinMultiple", JoinMultipleTranslator)
register_type("JoinMultipleTranslator", JoinMultipleTranslator)
register_plugin("AlteryxBasePluginsGui.JoinMultiple.JoinMultiple", JoinMultipleTranslator)

register_type("AppendFields", AppendFieldsTranslator)
register_type("AppendFieldsTranslator", AppendFieldsTranslator)
register_plugin("AlteryxBasePluginsGui.AppendFields.AppendFields", AppendFieldsTranslator)

register_type("FindReplace", FindReplaceTranslator)
register_type("FindReplaceTranslator", FindReplaceTranslator)
register_plugin("AlteryxBasePluginsGui.FindReplace.FindReplace", FindReplaceTranslator)
