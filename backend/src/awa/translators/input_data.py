"""InputData / DbFileInput / TextInput / DateTimeNow translators."""

from __future__ import annotations

import os

from awa.model.tool import Tool
from awa.model.workflow import Workflow
from awa.model.translation import TranslationResult
from awa.model.diagnostic import Diagnostic, DiagnosticLevel, SupportLevel, Dependency

from .base import ToolTranslator
from .registry import register_type, register_plugin


# Known FileFormat codes from Alteryx
_FILE_FORMAT_MAP = {
    "0": "csv",
    "19": "xlsx",
    "25": "yxdb",
}


def _infer_format(file_path: str, file_format_code: str) -> str:
    """Infer file format from the path extension or format code."""
    if file_format_code:
        fmt = _FILE_FORMAT_MAP.get(file_format_code)
        if fmt:
            return fmt

    ext = os.path.splitext(file_path)[1].lower()
    ext_map = {
        ".csv": "csv",
        ".tsv": "csv",
        ".txt": "csv",
        ".xlsx": "xlsx",
        ".xls": "xlsx",
        ".json": "json",
        ".parquet": "parquet",
        ".yxdb": "yxdb",
    }
    return ext_map.get(ext, "csv")


class InputDataTranslator(ToolTranslator):
    """Translates InputData / DbFileInput tools to pandas read operations."""

    def translate(
        self,
        tool: Tool,
        input_variables: list[str],
        workflow: Workflow,
    ) -> TranslationResult:
        config = tool.configuration.parsed
        file_path = config.get("file_path", "input.csv")
        file_format_code = config.get("file_format", "")

        fmt = _infer_format(file_path, file_format_code)
        output_var = f"df_{tool.tool_id}"
        diagnostics: list[Diagnostic] = []

        is_unc = file_path.startswith(("\\\\", "//"))
        is_resolved = os.path.exists(file_path) if not is_unc else False

        if not is_resolved or is_unc:
            diagnostics.append(
                Diagnostic(
                    level=DiagnosticLevel.INFO,
                    category="external_dependency",
                    tool_id=tool.tool_id,
                    tool_type=tool.tool_type,
                    message=f"External file dependency: '{file_path}' is referenced by Tool #{tool.tool_id}",
                    detail="Translation logic is fully supported (FULL), but runtime execution requires the external source file to be accessible.",
                )
            )

        path_repr = repr(file_path)
        if fmt == "csv":
            code = f'{output_var} = pd.read_csv({path_repr})'
        elif fmt == "xlsx":
            code = f'{output_var} = pd.read_excel({path_repr})'
        elif fmt == "json":
            code = f'{output_var} = pd.read_json({path_repr})'
        elif fmt == "parquet":
            code = f'{output_var} = pd.read_parquet({path_repr})'
        elif fmt == "yxdb":
            csv_path = repr(file_path.replace(".yxdb", ".csv"))
            code = (
                f'# NOTE: .yxdb is an Alteryx native format.\n'
                f'# Convert to CSV/Excel before running this script.\n'
                f'{output_var} = pd.read_csv({csv_path})  # PLACEHOLDER'
            )
            diagnostics.append(Diagnostic(
                level=DiagnosticLevel.WARNING,
                category="external_dependency",
                tool_id=tool.tool_id,
                tool_type=tool.tool_type,
                message=f"File format .yxdb requires conversion before execution",
                detail=f"Original path: {file_path}",
            ))
        else:
            code = f'{output_var} = pd.read_csv({path_repr})  # Unknown format, defaulting to CSV'
            diagnostics.append(Diagnostic(
                level=DiagnosticLevel.INFO,
                category="format_assumption",
                tool_id=tool.tool_id,
                tool_type=tool.tool_type,
                message=f"Unknown file format code '{file_format_code}', defaulting to CSV",
            ))

        workflow.dependencies.append(Dependency(
            dep_type="file",
            reference=file_path,
            tool_id=tool.tool_id,
            resolved=is_resolved,
        ))

        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.FULL,
            python_code=code,
            imports={"import pandas as pd"},
            input_variables=[],
            output_map={"Output": output_var},
            diagnostics=diagnostics,
            description=f"Read {fmt.upper()} file: {os.path.basename(file_path)}",
        )


class TextInputTranslator(ToolTranslator):
    """Translates TextInput tools into in-memory pandas DataFrames."""

    def translate(
        self,
        tool: Tool,
        input_variables: list[str],
        workflow: Workflow,
    ) -> TranslationResult:
        config = tool.configuration.parsed
        fields = config.get("fields", [])
        rows = config.get("rows", [])
        output_var = f"df_{tool.tool_id}"

        data_dict = {f: [r[i] if i < len(r) else None for r in rows] for i, f in enumerate(fields)}
        code = f"{output_var} = pd.DataFrame({repr(data_dict)})"

        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.FULL,
            python_code=code,
            imports={"import pandas as pd"},
            input_variables=[],
            output_map={"Output": output_var},
            diagnostics=[],
            description=f"Text input table ({len(rows)} rows, {len(fields)} columns)",
        )


class DateTimeNowTranslator(ToolTranslator):
    """Translates DateTimeNow tools to current timestamp generator."""

    def translate(
        self,
        tool: Tool,
        input_variables: list[str],
        workflow: Workflow,
    ) -> TranslationResult:
        output_var = f"df_{tool.tool_id}"
        code = f"{output_var} = pd.DataFrame({{'DateTimeNow': [pd.Timestamp.now()]}})"

        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.FULL,
            python_code=code,
            imports={"import pandas as pd"},
            input_variables=[],
            output_map={"Output": output_var},
            diagnostics=[],
            description="Generate current date/time record",
        )


# Registrations
register_type("DbFileInput", InputDataTranslator)
register_type("InputData", InputDataTranslator)
register_type("InputDataTranslator", InputDataTranslator)
register_plugin("AlteryxBasePluginsGui.DbFileInput.DbFileInput", InputDataTranslator)

register_type("TextInput", TextInputTranslator)
register_type("TextInputTranslator", TextInputTranslator)
register_plugin("AlteryxBasePluginsGui.TextInput.TextInput", TextInputTranslator)

register_type("DateTimeNow", DateTimeNowTranslator)
register_type("DateTimeNowTranslator", DateTimeNowTranslator)
register_plugin("DateTimeNow", DateTimeNowTranslator)
register_plugin("DateTimeNow.yxmc", DateTimeNowTranslator)
