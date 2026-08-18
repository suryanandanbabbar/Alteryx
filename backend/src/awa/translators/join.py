"""Join tool translator.

Alteryx Join tool takes two inputs (Left and Right) and outputs three streams:
- L: Records in Left that did not match Right (left outer anti-join)
- J: Records in Left that matched Right (inner join)
- R: Records in Right that did not match Left (right outer anti-join)

Per constraint C3 & C4:
The IR & output_map model all three anchors ('Left', 'Join', 'Right').
"""

from __future__ import annotations

from backend.src.awa.model.tool import Tool
from backend.src.awa.model.workflow import Workflow
from backend.src.awa.model.translation import TranslationResult
from backend.src.awa.model.diagnostic import Diagnostic, DiagnosticLevel, SupportLevel

from .base import ToolTranslator
from .registry import register_type


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
            # Join by record position
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
                f"# Left-only (L anchor - unjoined left records)\n"
                f"{left_only_var} = {left_var}[~{left_var}[{left_on_repr}].isin({right_var}[{right_on_repr}])].copy()\n"
                f"# Right-only (R anchor - unjoined right records)\n"
                f"{right_only_var} = {right_var}[~{right_var}[{right_on_repr}].isin({left_var}[{left_on_repr}])].copy()"
            )
            desc = f"Join on left={left_on} == right={right_on}"
        else:
            code = (
                f"# Fallback join (no join keys specified)\n"
                f"{joined_var} = pd.merge({left_var}, {right_var}, how='inner')\n"
                f"{left_only_var} = {left_var}.iloc[0:0].copy()\n"
                f"{right_only_var} = {right_var}.iloc[0:0].copy()"
            )
            diagnostics.append(Diagnostic(
                level=DiagnosticLevel.WARNING,
                category="missing_join_keys",
                tool_id=tool.tool_id,
                tool_type=tool.tool_type,
                message="Join has no explicit join keys configured",
            ))
            desc = "Join (no explicit keys)"

        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.SUPPORTED,
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


register_type("Join", JoinTranslator)
