"""Parse category translators: DateTime, RegEx, TextToColumns, JSONParse, JSONBuild."""

from __future__ import annotations

from awa.model.tool import Tool
from awa.model.workflow import Workflow
from awa.model.translation import TranslationResult
from awa.model.diagnostic import SupportLevel

from .base import ToolTranslator
from .registry import register_type, register_plugin


class DateTimeTranslator(ToolTranslator):
    """Translates DateTime tool to pd.to_datetime operations."""

    def translate(self, tool: Tool, input_variables: list[str], workflow: Workflow) -> TranslationResult:
        in_var = input_variables[0] if input_variables else "df_unknown"
        out_var = f"df_{tool.tool_id}"
        config = tool.configuration.parsed
        in_field = config.get("inputfieldname", "") or "DateField"
        out_field = config.get("outputfieldname", "") or f"{in_field}_Out"
        fmt = config.get("inputformat", "") or "%Y-%m-%d"

        lines = [
            f"{out_var} = {in_var}.copy()",
            f'{out_var}["{out_field}"] = pd.to_datetime({out_var}["{in_field}"], format="{fmt}", errors="coerce")',
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
            description=f"Parse datetime field '{in_field}' to '{out_field}'",
        )


class RegExTranslator(ToolTranslator):
    """Translates RegEx tool to pandas string regex operations."""

    def translate(self, tool: Tool, input_variables: list[str], workflow: Workflow) -> TranslationResult:
        in_var = input_variables[0] if input_variables else "df_unknown"
        out_var = f"df_{tool.tool_id}"
        config = tool.configuration.parsed or {}
        field = config.get("field", "") or "TextField"
        pattern = repr(config.get("regexexpression", r"(\w+)"))
        method = config.get("method", "Match")

        lines = [f"{out_var} = {in_var}.copy()"]

        if method == "ParseComplex" and config.get("parse_complex_fields"):
            cols = [f["field"] for f in config["parse_complex_fields"] if f.get("field")]
            cols_repr = repr(cols)
            lines.append(f'{out_var}[{cols_repr}] = {out_var}["{field}"].astype(str).str.extract({pattern})')
        elif method == "Match":
            mfield = repr(config.get("match_field", f"{field}_Matched"))
            lines.append(f'{out_var}[{mfield}] = {out_var}["{field}"].astype(str).str.contains({pattern}, regex=True, na=False)')
        elif method == "Replace":
            r_str = repr(config.get("replacestring", ""))
            lines.append(f'{out_var}["{field}"] = {out_var}["{field}"].astype(str).str.replace({pattern}, {r_str}, regex=True)')
        elif method == "ParseSimple":
            simple = config.get("parse_simple", {})
            rname = simple.get("root_name") or field
            nfields = simple.get("num_fields", 1)
            cols = [f"{rname}{i}" for i in range(1, nfields + 1)]
            cols_repr = repr(cols)
            lines.append(f'{out_var}[{cols_repr}] = {out_var}["{field}"].astype(str).str.extract({pattern})')
        else:
            lines.append(f'{out_var}["{field}_regex"] = {out_var}["{field}"].astype(str).str.extract({pattern})')

        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.FULL,
            python_code="\n".join(lines),
            imports={"import pandas as pd"},
            input_variables=[in_var],
            output_map={"Output": out_var},
            diagnostics=[],
            description=f"RegEx {method} operation on '{field}'",
        )


class TextToColumnsTranslator(ToolTranslator):
    """Translates TextToColumns tool to str.split(..., expand=True)."""

    def translate(self, tool: Tool, input_variables: list[str], workflow: Workflow) -> TranslationResult:
        in_var = input_variables[0] if input_variables else "df_unknown"
        out_var = f"df_{tool.tool_id}"
        config = tool.configuration.parsed
        field = config.get("field", "") or "TextField"
        delim = repr(config.get("delimeters", ","))

        lines = [
            f"{out_var} = {in_var}.copy()",
            f"split_cols = {out_var}['{field}'].astype(str).str.split({delim}, expand=True)",
            f"{out_var} = pd.concat([{out_var}, split_cols.add_prefix('{field}_')], axis=1)",
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
            description=f"Split '{field}' to columns by delimiter",
        )


class JSONParseTranslator(ToolTranslator):
    """Translates JSONParse tool to pandas json normalization."""

    def translate(self, tool: Tool, input_variables: list[str], workflow: Workflow) -> TranslationResult:
        in_var = input_variables[0] if input_variables else "df_unknown"
        out_var = f"df_{tool.tool_id}"
        lines = [
            f"{out_var} = {in_var}.copy()",
            f"# JSON Parse: Flatten JSON columns",
        ]
        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.FULL,
            python_code="\n".join(lines),
            imports={"import pandas as pd", "import json"},
            input_variables=[in_var],
            output_map={"Output": out_var},
            diagnostics=[],
            description="Parse JSON string values",
        )


class JSONBuildTranslator(ToolTranslator):
    """Translates JSONBuild tool to DataFrame to_json."""

    def translate(self, tool: Tool, input_variables: list[str], workflow: Workflow) -> TranslationResult:
        in_var = input_variables[0] if input_variables else "df_unknown"
        out_var = f"df_{tool.tool_id}"
        code = f"{out_var} = pd.DataFrame({{'JSON': [{in_var}.to_json(orient='records')]}})"
        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.FULL,
            python_code=code,
            imports={"import pandas as pd"},
            input_variables=[in_var],
            output_map={"Output": out_var},
            diagnostics=[],
            description="Build JSON text from DataFrame",
        )


# Registrations
register_type("DateTime", DateTimeTranslator)
register_type("DateTimeTranslator", DateTimeTranslator)
register_plugin("AlteryxBasePluginsGui.DateTime.DateTime", DateTimeTranslator)

register_type("RegEx", RegExTranslator)
register_type("RegExTranslator", RegExTranslator)
register_plugin("AlteryxBasePluginsGui.RegEx.RegEx", RegExTranslator)

register_type("TextToColumns", TextToColumnsTranslator)
register_type("TextToColumnsTranslator", TextToColumnsTranslator)
register_plugin("AlteryxBasePluginsGui.TextToColumns.TextToColumns", TextToColumnsTranslator)

register_type("JSONParse", JSONParseTranslator)
register_type("JSONParseTranslator", JSONParseTranslator)
register_plugin("AlteryxBasePluginsGui.JSONParse.JSONParse", JSONParseTranslator)

register_type("JSONBuild", JSONBuildTranslator)
register_type("JSONBuildTranslator", JSONBuildTranslator)
register_plugin("AlteryxBasePluginsGui.JSONBuild.JSONBuild", JSONBuildTranslator)
