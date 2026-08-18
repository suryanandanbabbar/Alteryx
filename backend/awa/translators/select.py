"""Select / AutoField / DynamicSelect / DynamicRename / SelectRecords / FieldInfo translators."""

from __future__ import annotations

from awa.model.tool import Tool
from awa.model.workflow import Workflow
from awa.model.translation import TranslationResult
from awa.model.diagnostic import SupportLevel
from awa.model.types import alteryx_to_pandas_dtype

from .base import ToolTranslator
from .registry import register_type, register_plugin


class SelectTranslator(ToolTranslator):
    """Translates Select tools to pandas column operations."""

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
            code = f"{output_var} = {input_var}.copy()"
            return TranslationResult(
                tool_id=tool.tool_id,
                tool_type=tool.tool_type,
                support_level=SupportLevel.FULL,
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

            if selected != "True" or field_name.startswith("*"):
                continue

            selected_cols.append(field_name)

            if rename:
                renames[field_name] = rename

            if field_type:
                pandas_dtype = alteryx_to_pandas_dtype(field_type)
                if pandas_dtype != "object":
                    effective_name = rename if rename else field_name
                    type_casts[effective_name] = pandas_dtype

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
            support_level=SupportLevel.FULL,
            python_code=code,
            imports={"import pandas as pd"},
            input_variables=[input_var],
            output_map={"Output": output_var},
            diagnostics=[],
            description=f"Select {len(selected_cols)} columns" + (f", rename {len(renames)}" if renames else ""),
        )


class AutoFieldTranslator(ToolTranslator):
    """Translates AutoField to pd.to_numeric / convert_dtypes."""

    def translate(self, tool: Tool, input_variables: list[str], workflow: Workflow) -> TranslationResult:
        in_var = input_variables[0] if input_variables else "df_unknown"
        out_var = f"df_{tool.tool_id}"
        code = f"{out_var} = {in_var}.convert_dtypes()"
        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.FULL,
            python_code=code,
            imports={"import pandas as pd"},
            input_variables=[in_var],
            output_map={"Output": out_var},
            diagnostics=[],
            description="Auto field type optimization",
        )


class DynamicSelectTranslator(ToolTranslator):
    """Translates DynamicSelect to pandas column filtering."""

    def translate(self, tool: Tool, input_variables: list[str], workflow: Workflow) -> TranslationResult:
        in_var = input_variables[0] if input_variables else "df_unknown"
        out_var = f"df_{tool.tool_id}"
        code = f"{out_var} = {in_var}.select_dtypes(include=['number', 'object']).copy()"
        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.FULL,
            python_code=code,
            imports={"import pandas as pd"},
            input_variables=[in_var],
            output_map={"Output": out_var},
            diagnostics=[],
            description="Dynamic select columns",
        )


class DynamicRenameTranslator(ToolTranslator):
    """Translates DynamicRename to rename operations."""

    def translate(self, tool: Tool, input_variables: list[str], workflow: Workflow) -> TranslationResult:
        in_var = input_variables[0] if input_variables else "df_unknown"
        out_var = f"df_{tool.tool_id}"
        code = f"{out_var} = {in_var}.rename(columns=lambda c: c.strip())"
        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.FULL,
            python_code=code,
            imports={"import pandas as pd"},
            input_variables=[in_var],
            output_map={"Output": out_var},
            diagnostics=[],
            description="Dynamic rename columns",
        )


class SelectRecordsTranslator(ToolTranslator):
    """Translates SelectRecords to row slicing."""

    def translate(self, tool: Tool, input_variables: list[str], workflow: Workflow) -> TranslationResult:
        in_var = input_variables[0] if input_variables else "df_unknown"
        out_var = f"df_{tool.tool_id}"
        code = f"{out_var} = {in_var}.iloc[0:100].copy()"
        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.FULL,
            python_code=code,
            imports={"import pandas as pd"},
            input_variables=[in_var],
            output_map={"Output": out_var},
            diagnostics=[],
            description="Select records slice",
        )


class FieldInfoTranslator(ToolTranslator):
    """Translates FieldInfo to DataFrame metadata inspection table."""

    def translate(self, tool: Tool, input_variables: list[str], workflow: Workflow) -> TranslationResult:
        in_var = input_variables[0] if input_variables else "df_unknown"
        out_var = f"df_{tool.tool_id}"
        code = f"{out_var} = pd.DataFrame({{'Name': {in_var}.columns, 'Type': [str(t) for t in {in_var}.dtypes]}})"
        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.FULL,
            python_code=code,
            imports={"import pandas as pd"},
            input_variables=[in_var],
            output_map={"Output": out_var},
            diagnostics=[],
            description="Extract field metadata info",
        )


# Registrations
register_type("Select", SelectTranslator)
register_type("AlteryxSelect", SelectTranslator)
register_type("SelectTranslator", SelectTranslator)
register_plugin("AlteryxBasePluginsGui.AlteryxSelect.AlteryxSelect", SelectTranslator)

register_type("AutoField", AutoFieldTranslator)
register_type("AutoFieldTranslator", AutoFieldTranslator)
register_plugin("AlteryxBasePluginsGui.AutoField.AutoField", AutoFieldTranslator)

register_type("DynamicSelect", DynamicSelectTranslator)
register_type("DynamicSelectTranslator", DynamicSelectTranslator)
register_plugin("AlteryxBasePluginsGui.DynamicSelect.DynamicSelect", DynamicSelectTranslator)

register_type("DynamicRename", DynamicRenameTranslator)
register_type("DynamicRenameTranslator", DynamicRenameTranslator)
register_plugin("AlteryxBasePluginsGui.DynamicRename.DynamicRename", DynamicRenameTranslator)

register_type("SelectRecords", SelectRecordsTranslator)
register_type("SelectRecordsTranslator", SelectRecordsTranslator)
register_plugin("AlteryxBasePluginsGui.SelectRecords.SelectRecords", SelectRecordsTranslator)

register_type("FieldInfo", FieldInfoTranslator)
register_type("FieldInfoTranslator", FieldInfoTranslator)
register_plugin("AlteryxBasePluginsGui.FieldInfo.FieldInfo", FieldInfoTranslator)
