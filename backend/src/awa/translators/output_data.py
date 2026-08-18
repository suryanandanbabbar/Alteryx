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


def _infer_output_format(file_path: str, file_format_code: str) -> str:
    """Infer output file format from path or code."""
    if file_format_code:
        fmt = _FILE_FORMAT_MAP.get(file_format_code)
        if fmt:
            return fmt

    ext = os.path.splitext(file_path)[1].lower()
    ext_map = {".csv": "csv", ".xlsx": "xlsx", ".json": "json", ".parquet": "parquet"}
    return ext_map.get(ext, "csv")


class OutputDataTranslator(ToolTranslator):
    """Translates OutputData / DbFileOutput tools to pandas write operations."""

    def translate(
        self,
        tool: Tool,
        input_variables: list[str],
        workflow: Workflow,
    ) -> TranslationResult:
        config = tool.configuration.parsed
        file_path = config.get("file_path", "output.csv")
        file_format_code = config.get("file_format", "")
        input_var = input_variables[0] if input_variables else "df_unknown"

        fmt = _infer_output_format(file_path, file_format_code)
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
        if fmt == "csv":
            code = f'{input_var}.to_csv({path_repr}, index=False)'
        elif fmt == "xlsx":
            code = f'{input_var}.to_excel({path_repr}, index=False)'
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
            imports={"import pandas as pd"},
            input_variables=[input_var],
            output_map={},
            diagnostics=diagnostics,
            description=f"Write {fmt.upper()} file: {os.path.basename(file_path)}",
        )


register_type("DbFileOutput", OutputDataTranslator)
register_type("OutputData", OutputDataTranslator)
register_type("OutputDataTranslator", OutputDataTranslator)
register_plugin("AlteryxBasePluginsGui.DbFileOutput.DbFileOutput", OutputDataTranslator)
