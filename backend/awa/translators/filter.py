"""Filter translator."""

from __future__ import annotations

from awa.model.tool import Tool
from awa.model.workflow import Workflow
from awa.model.translation import TranslationResult
from awa.model.diagnostic import Diagnostic, DiagnosticLevel, SupportLevel
from awa.expressions.pandas_emitter import emit_pandas

from .base import ToolTranslator
from .registry import register_type, register_plugin


class FilterTranslator(ToolTranslator):
    """Translates Filter tools to pandas boolean indexing."""

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
        upstream_schema = getattr(workflow, "_stream_schemas", {}).get(input_var)

        if not expression:
            code = (
                f"{true_var} = {input_var}.copy()\n"
                f"{false_var} = {input_var}.iloc[0:0].copy()"
            )
            diagnostics.append(Diagnostic(
                level=DiagnosticLevel.WARNING,
                category="missing_configuration",
                tool_id=tool.tool_id,
                tool_type=tool.tool_type,
                message="Filter has no expression — all records pass to True branch",
            ))
        else:
            if upstream_schema is not None:
                import re
                bracketed = re.findall(r"\[([^\]]+)\]", expression)
                for ref_field in bracketed:
                    if ref_field not in upstream_schema:
                        diagnostics.append(
                            Diagnostic(
                                level=DiagnosticLevel.WARNING,
                                category="unresolved_field",
                                tool_id=tool.tool_id,
                                tool_type=tool.tool_type,
                                message=f"Tool #{tool.tool_id} (Filter) references missing field '{ref_field}'. Available fields: {upstream_schema}",
                            )
                        )

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
            support_level=SupportLevel.FULL if not diagnostics else SupportLevel.PARTIAL,
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
register_type("FilterTranslator", FilterTranslator)
register_plugin("AlteryxBasePluginsGui.Filter.Filter", FilterTranslator)
