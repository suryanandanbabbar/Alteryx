"""Filter translator.

Produces True and False branches. Per constraint C3, the IR preserves
both branches in output_map. The Python generator only emits code for
consumed branches.
"""

from __future__ import annotations

from backend.src.awa.model.tool import Tool
from backend.src.awa.model.workflow import Workflow
from backend.src.awa.model.translation import TranslationResult
from backend.src.awa.model.diagnostic import Diagnostic, DiagnosticLevel, SupportLevel
from backend.src.awa.expressions.pandas_emitter import emit_pandas

from .base import ToolTranslator
from .registry import register_type


class FilterTranslator(ToolTranslator):
    """Translates Filter tools to pandas boolean indexing.

    Always generates both True and False branches in output_map (C3).
    The Python code generates both assignments.
    The Python generator downstream decides which to include based on
    consumed_anchors.
    """

    def translate(
        self,
        tool: Tool,
        input_variables: list[str],
        workflow: Workflow,
    ) -> TranslationResult:
        config = tool.configuration.parsed
        expression = config.get("expression", "")
        input_var = input_variables[0] if input_variables else "df_unknown"

        true_var = f"df_{tool.tool_id}_true"
        false_var = f"df_{tool.tool_id}_false"

        diagnostics: list[Diagnostic] = []
        imports: set[str] = {"import pandas as pd"}

        if not expression:
            # No expression — pass everything to True branch
            code = (
                f"{true_var} = {input_var}.copy()\n"
                f"{false_var} = {input_var}.iloc[0:0].copy()  # Empty DataFrame"
            )
            diagnostics.append(Diagnostic(
                level=DiagnosticLevel.WARNING,
                category="missing_configuration",
                tool_id=tool.tool_id,
                tool_type=tool.tool_type,
                message="Filter has no expression — all records pass to True branch",
            ))
        else:
            try:
                pandas_expr, expr_imports = emit_pandas(expression, input_var)
                imports.update(expr_imports)

                code = (
                    f"_filter_mask_{tool.tool_id} = {pandas_expr}\n"
                    f"{true_var} = {input_var}[_filter_mask_{tool.tool_id}].copy()\n"
                    f"{false_var} = {input_var}[~_filter_mask_{tool.tool_id}].copy()"
                )
            except Exception as e:
                code = (
                    f"# ERROR: Could not translate filter expression: {expression}\n"
                    f"# Parse error: {e}\n"
                    f"{true_var} = {input_var}.copy()\n"
                    f"{false_var} = {input_var}.iloc[0:0].copy()"
                )
                diagnostics.append(Diagnostic(
                    level=DiagnosticLevel.ERROR,
                    category="expression_error",
                    tool_id=tool.tool_id,
                    tool_type=tool.tool_type,
                    message=f"Failed to parse filter expression: {expression}",
                    detail=str(e),
                ))

        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.SUPPORTED if not diagnostics else SupportLevel.PARTIAL,
            python_code=code,
            imports=imports,
            input_variables=[input_var],
            output_map={
                "True": true_var,
                "False": false_var,
            },
            diagnostics=diagnostics,
            description=f"Filter: {expression}" if expression else "Filter: (no expression)",
        )


register_type("Filter", FilterTranslator)
