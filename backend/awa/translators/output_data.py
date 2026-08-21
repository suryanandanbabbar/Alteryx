"""OutputData / DbFileOutput translator."""

from __future__ import annotations

import os

from awa.model.tool import Tool
from awa.model.workflow import Workflow
from awa.model.translation import TranslationResult
from awa.model.diagnostic import Diagnostic, DiagnosticLevel, SupportLevel, Dependency

from .base import ToolTranslator
from .registry import register_type, register_plugin


_FILE_FORMAT_MAP = {
    "0": "csv",
    "19": "xlsx",
    "25": "yxdb",
}


def _parse_output_path(raw_path: str, file_format_code: str) -> tuple[str, str, str]:
    """Parse Alteryx output connection string into (clean_path, sheet_name, format)."""
    if not raw_path:
        return ("output.csv", "", "csv")

    sheet_name = ""
    file_path = raw_path
    if "|||" in raw_path:
        file_path, sheet_name = raw_path.split("|||", 1)
        sheet_name = sheet_name.replace("$", "").strip()

    file_path = file_path.strip()
    if not file_path.startswith(("\\\\", "//")):
        file_path = file_path.replace("\\", "/")

    fmt = ""
    if file_format_code:
        fmt = _FILE_FORMAT_MAP.get(str(file_format_code), "")

    if not fmt:
        ext = os.path.splitext(file_path)[1].lower()
        ext_map = {
            ".csv": "csv",
            ".tsv": "csv",
            ".txt": "csv",
            ".xlsx": "xlsx",
            ".xls": "xlsx",
            ".xlsm": "xlsx",
            ".json": "json",
            ".parquet": "parquet",
        }
        fmt = ext_map.get(ext, "csv")

    return (file_path, sheet_name, fmt)


class OutputDataTranslator(ToolTranslator):
    """Translates OutputData / DbFileOutput tools to pandas write operations."""

    def translate(
        self,
        tool: Tool,
        input_variables: list[str],
        workflow: Workflow,
    ) -> TranslationResult:
        config = tool.configuration.parsed
        raw_path = config.get("file_path", "output.csv")
        file_format_code = config.get("file_format", "")
        input_var = input_variables[0] if input_variables else "df_unknown"

        file_path, sheet_name, fmt = _parse_output_path(raw_path, file_format_code)
        diagnostics: list[Diagnostic] = []

        is_unc = file_path.startswith(("\\\\", "//"))
        is_resolved = os.path.exists(os.path.dirname(file_path)) if (os.path.dirname(file_path) and not is_unc) else False

        if is_unc or not is_resolved:
            diagnostics.append(
                Diagnostic(
                    level=DiagnosticLevel.INFO,
                    category="external_dependency",
                    tool_id=tool.tool_id,
                    tool_type=tool.tool_type,
                    message=f"External file destination: '{file_path}' is referenced by Tool #{tool.tool_id}",
                    detail="Translation logic is fully supported (FULL), but runtime execution requires write access to the target path.",
                )
            )

        path_repr = repr(file_path)
        imports = {"import pandas as pd"}

        if fmt == "csv":
            code = f'{input_var}.to_csv({path_repr}, index=False)'
        elif fmt == "xlsx":
            imports.add("import openpyxl")
            s_name = sheet_name or "Sheet1"
            code = (
                f'try:\n'
                f'    with pd.ExcelWriter({path_repr}, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:\n'
                f'        {input_var}.to_excel(writer, sheet_name={repr(s_name)}, index=False)\n'
                f'except FileNotFoundError:\n'
                f'    with pd.ExcelWriter({path_repr}, engine="openpyxl", mode="w") as writer:\n'
                f'        {input_var}.to_excel(writer, sheet_name={repr(s_name)}, index=False)'
            )
        elif fmt == "json":
            code = f'{input_var}.to_json({path_repr}, orient="records")'
        elif fmt == "parquet":
            code = f'{input_var}.to_parquet({path_repr}, index=False)'
        else:
            code = f'{input_var}.to_csv({path_repr}, index=False)'

        workflow.dependencies.append(
            Dependency(
                dep_type="file",
                reference=file_path,
                tool_id=tool.tool_id,
                resolved=is_resolved,
            )
        )

        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.FULL,
            python_code=code,
            imports=imports,
            input_variables=[input_var],
            output_map={},
            diagnostics=diagnostics,
            description=f"Write {fmt.upper()} file: {os.path.basename(file_path)}",
        )


register_type("DbFileOutput", OutputDataTranslator)
register_type("OutputData", OutputDataTranslator)
register_type("OutputDataTranslator", OutputDataTranslator)
register_plugin("AlteryxBasePluginsGui.DbFileOutput.DbFileOutput", OutputDataTranslator)
