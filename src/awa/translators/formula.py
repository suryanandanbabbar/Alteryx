"""Formula translator."""

from __future__ import annotations

from awa.model.tool import Tool
from awa.model.workflow import Workflow
from awa.model.translation import TranslationResult
from awa.model.diagnostic import Diagnostic, DiagnosticLevel, SupportLevel
from awa.expressions.pandas_emitter import emit_pandas

from .base import ToolTranslator
from .registry import register_type


class FormulaTranslator(ToolTranslator):
    """Translates Formula tools to pandas column assignments.

    Each FormulaField in the configuration creates or updates a column
    using the translated expression.
    """

    def translate(
        self,
        tool: Tool,
        input_variables: list[str],
        workflow: Workflow,
    ) -> TranslationResult:
        config = tool.configuration.parsed
        formula_fields = config.get("formula_fields", [])
        input_var = input_variables[0] if input_variables else "df_unknown"
        output_var = f"df_{tool.tool_id}"

        diagnostics: list[Diagnostic] = []
        imports: set[str] = {"import pandas as pd"}
        lines: list[str] = [f"{output_var} = {input_var}.copy()"]

        if not formula_fields:
            diagnostics.append(Diagnostic(
                level=DiagnosticLevel.WARNING,
                category="missing_configuration",
                tool_id=tool.tool_id,
                tool_type=tool.tool_type,
                message="Formula has no formula fields",
            ))
        else:
            for ff in formula_fields:
                field_name = ff.get("field", "")
                expression = ff.get("expression", "")

                if not field_name or not expression:
                    diagnostics.append(Diagnostic(
                        level=DiagnosticLevel.WARNING,
                        category="incomplete_formula",
                        tool_id=tool.tool_id,
                        tool_type=tool.tool_type,
                        message=f"Empty field or expression in formula: field='{field_name}'",
                    ))
                    continue

                try:
                    pandas_expr, expr_imports = emit_pandas(expression, output_var)
                    imports.update(expr_imports)
                    lines.append(f'{output_var}["{field_name}"] = {pandas_expr}')
                except Exception as e:
                    lines.append(
                        f'# ERROR: Could not translate expression for [{field_name}]: {expression}\n'
                        f'# Parse error: {e}'
                    )
                    diagnostics.append(Diagnostic(
                        level=DiagnosticLevel.ERROR,
                        category="expression_error",
                        tool_id=tool.tool_id,
                        tool_type=tool.tool_type,
                        message=f"Failed to parse formula expression for [{field_name}]",
                        detail=f"Expression: {expression}, Error: {e}",
                    ))

        code = "\n".join(lines)

        has_errors = any(d.level == DiagnosticLevel.ERROR for d in diagnostics)
        support = SupportLevel.PARTIAL if has_errors else SupportLevel.SUPPORTED

        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=support,
            python_code=code,
            imports=imports,
            input_variables=[input_var],
            output_map={"Output": output_var},
            diagnostics=diagnostics,
            description=f"Formula: {len(formula_fields)} field(s)",
        )


register_type("Formula", FormulaTranslator)
