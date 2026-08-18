"""Select / AlteryxSelect translator."""

from __future__ import annotations

from backend.src.awa.model.tool import Tool
from backend.src.awa.model.workflow import Workflow
from backend.src.awa.model.translation import TranslationResult
from backend.src.awa.model.diagnostic import SupportLevel
from backend.src.awa.model.types import alteryx_to_pandas_dtype

from .base import ToolTranslator
from .registry import register_type


class SelectTranslator(ToolTranslator):
    """Translates Select tools to pandas column operations.

    Handles:
    - Column selection (include/exclude)
    - Column renaming
    - Type casting (using the type mapping system per C5)
    """

    def translate(
        self,
        tool: Tool,
        input_variables: list[str],
        workflow: Workflow,
    ) -> TranslationResult:
        config = tool.configuration.parsed
        select_fields = config.get("select_fields", [])
        input_var = input_variables[0] if input_variables else "df_unknown"
        output_var = f"df_{tool.tool_id}"

        if not select_fields:
            # No fields specified — pass through
            code = f"{output_var} = {input_var}.copy()"
            return TranslationResult(
                tool_id=tool.tool_id,
                tool_type=tool.tool_type,
                support_level=SupportLevel.SUPPORTED,
                python_code=code,
                imports={"import pandas as pd"},
                input_variables=[input_var],
                output_map={"Output": output_var},
                diagnostics=[],
                description="Select: passthrough (no fields specified)",
            )

        lines: list[str] = []
        selected_cols: list[str] = []
        renames: dict[str, str] = {}
        type_casts: dict[str, str] = {}

        for sf in select_fields:
            field_name = sf.get("field", "")
            selected = sf.get("selected", "True")
            rename = sf.get("rename", "")
            field_type = sf.get("type", "")

            # Skip deselected fields or wildcard entries
            if selected != "True" or field_name.startswith("*"):
                continue

            selected_cols.append(field_name)

            if rename:
                renames[field_name] = rename

            if field_type:
                pandas_dtype = alteryx_to_pandas_dtype(field_type)
                if pandas_dtype != "object":  # Only cast if meaningful
                    effective_name = rename if rename else field_name
                    type_casts[effective_name] = pandas_dtype

        # Build code
        if selected_cols:
            cols_repr = repr(selected_cols)
            lines.append(f"{output_var} = {input_var}[{cols_repr}].copy()")
        else:
            lines.append(f"{output_var} = {input_var}.copy()")

        if renames:
            renames_repr = repr(renames)
            lines.append(f"{output_var} = {output_var}.rename(columns={renames_repr})")

        if type_casts:
            for col, dtype in type_casts.items():
                lines.append(f'{output_var}["{col}"] = {output_var}["{col}"].astype("{dtype}")')

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
            description=f"Select {len(selected_cols)} columns" + (f", rename {len(renames)}" if renames else ""),
        )


register_type("Select", SelectTranslator)
register_type("AlteryxSelect", SelectTranslator)
