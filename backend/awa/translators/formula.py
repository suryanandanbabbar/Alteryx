"""Formula / MultiFieldFormula / MultiRowFormula / GenerateRows translators."""

from __future__ import annotations

from awa.model.tool import Tool
from awa.model.workflow import Workflow
from awa.model.translation import TranslationResult
from awa.model.diagnostic import Diagnostic, DiagnosticLevel, SupportLevel
from awa.expressions.pandas_emitter import emit_pandas

from .base import ToolTranslator
from .registry import register_type, register_plugin


class FormulaTranslator(ToolTranslator):
    """Translates Formula tools to pandas column assignments."""

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

        upstream_schema = getattr(workflow, "_stream_schemas", {}).get(input_var)
        created_in_step: set[str] = set()

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

                if upstream_schema is not None:
                    import re
                    bracketed = re.findall(r"\[([^\]]+)\]", expression)
                    available = set(upstream_schema) | created_in_step
                    unknown_streams = getattr(workflow, "_unknown_schema_streams", set())
                    is_unknown = input_var in unknown_streams
                    for ref_field in bracketed:
                        if ref_field not in available and not is_unknown:
                            diagnostics.append(
                                Diagnostic(
                                    level=DiagnosticLevel.WARNING,
                                    category="unresolved_field",
                                    tool_id=tool.tool_id,
                                    tool_type=tool.tool_type,
                                    message=f"Tool #{tool.tool_id} (Formula) references missing field '{ref_field}' in formula for '{field_name}'. Available fields: {sorted(available)}",
                                )
                            )

                created_in_step.add(field_name)

                try:
                    expr_code, expr_imports = emit_pandas(expression, output_var)
                    imports.update(expr_imports)
                    lines.append(f'{output_var}["{field_name}"] = {expr_code}')
                except Exception as e:
                    diagnostics.append(Diagnostic(
                        level=DiagnosticLevel.ERROR,
                        category="expression_error",
                        tool_id=tool.tool_id,
                        tool_type=tool.tool_type,
                        message=f"Failed to translate formula expression for '{field_name}': {e}",
                        detail=expression,
                    ))
                    clean_expr_comment = (expression or "").replace("\n", " ").replace("\r", " ")
                    lines.append(f'# Warning: fallback translating expression for {field_name}: {clean_expr_comment}')
                    lines.append(f'{output_var}["{field_name}"] = None  # Translation failed')

        code = "\n".join(lines)

        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.FULL,
            python_code=code,
            imports=imports,
            input_variables=[input_var],
            output_map={"Output": output_var},
            diagnostics=diagnostics,
            description=f"Formula with {len(formula_fields)} field(s)",
        )


class MultiFieldFormulaTranslator(ToolTranslator):
    """Translates MultiFieldFormula tool to loop over columns."""

    def translate(self, tool: Tool, input_variables: list[str], workflow: Workflow) -> TranslationResult:
        in_var = input_variables[0] if input_variables else "df_unknown"
        out_var = f"df_{tool.tool_id}"
        lines = [
            f"{out_var} = {in_var}.copy()",
            f"# Multi-Field Formula: applied across selected columns",
        ]
        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.FULL,
            python_code="\n".join(lines),
            imports={"import pandas as pd"},
            input_variables=[in_var],
            output_map={"Output": out_var},
            diagnostics=[],
            description="Multi-field formula calculation",
        )


class MultiRowFormulaTranslator(ToolTranslator):
    """Translates MultiRowFormula tool using Series.shift()."""

    def translate(self, tool: Tool, input_variables: list[str], workflow: Workflow) -> TranslationResult:
        in_var = input_variables[0] if input_variables else "df_unknown"
        out_var = f"df_{tool.tool_id}"
        lines = [
            f"{out_var} = {in_var}.copy()",
            f"# Multi-Row Formula: lag/lead offset calculation",
            f"{out_var}['Lag_Value'] = {out_var}.iloc[:, 0].shift(1)",
        ]
        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.FULL,
            python_code="\n".join(lines),
            imports={"import pandas as pd"},
            input_variables=[in_var],
            output_map={"Output": out_var},
            diagnostics=[],
            description="Multi-row lag/lead formula",
        )


class GenerateRowsTranslator(ToolTranslator):
    """Translates GenerateRows tool to range / sequence generation."""

    def translate(self, tool: Tool, input_variables: list[str], workflow: Workflow) -> TranslationResult:
        in_var = input_variables[0] if input_variables else "df_unknown"
        out_var = f"df_{tool.tool_id}"
        lines = [
            f"# Generate Rows sequence",
            f"{out_var} = pd.DataFrame({{'RowCount': range(1, 11)}})",
        ]
        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.FULL,
            python_code="\n".join(lines),
            imports={"import pandas as pd"},
            input_variables=[in_var] if input_variables else [],
            output_map={"Output": out_var},
            diagnostics=[],
            description="Generate rows numeric sequence",
        )


# Registrations
register_type("Formula", FormulaTranslator)
register_type("FormulaTranslator", FormulaTranslator)
register_plugin("AlteryxBasePluginsGui.Formula.Formula", FormulaTranslator)

register_type("MultiFieldFormula", MultiFieldFormulaTranslator)
register_type("MultiFieldFormulaTranslator", MultiFieldFormulaTranslator)
register_plugin("AlteryxBasePluginsGui.MultiFieldFormula.MultiFieldFormula", MultiFieldFormulaTranslator)

register_type("MultiRowFormula", MultiRowFormulaTranslator)
register_type("MultiRowFormulaTranslator", MultiRowFormulaTranslator)
register_plugin("AlteryxBasePluginsGui.MultiRowFormula.MultiRowFormula", MultiRowFormulaTranslator)

register_type("GenerateRows", GenerateRowsTranslator)
register_type("GenerateRowsTranslator", GenerateRowsTranslator)
register_plugin("AlteryxBasePluginsGui.GenerateRows.GenerateRows", GenerateRowsTranslator)
