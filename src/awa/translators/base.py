"""Base translator interface and unsupported tool handler."""

from __future__ import annotations

from abc import ABC, abstractmethod

from awa.model.tool import Tool
from awa.model.workflow import Workflow
from awa.model.translation import TranslationResult
from awa.model.diagnostic import Diagnostic, DiagnosticLevel, SupportLevel
from awa.model.python_trace import ToolExplanation


class ToolTranslator(ABC):
    """Abstract base class for tool translators.

    Each translator converts an Alteryx tool's configuration into
    Python/pandas code. Translators produce TranslationResult objects
    with output_map (anchor → variable name) per constraint C4.
    """

    @abstractmethod
    def translate(
        self,
        tool: Tool,
        input_variables: list[str],
        workflow: Workflow,
    ) -> TranslationResult:
        """Translate a tool into Python/pandas code.

        Args:
            tool: The Alteryx tool to translate.
            input_variables: DataFrame variable names feeding into this tool.
            workflow: The full workflow (for context).

        Returns:
            TranslationResult with generated code and output_map.
        """
        ...

    def explain(
        self,
        tool: Tool,
        translation: TranslationResult,
    ) -> ToolExplanation:
        """Produce a deterministic explanation of why this translation was chosen.

        Never uses LLMs or generative AI.
        """
        libs = []
        for imp in translation.imports:
            if "pandas" in imp:
                libs.append("pandas")
            elif "numpy" in imp:
                libs.append("numpy")
            elif "openpyxl" in imp:
                libs.append("openpyxl")
        libs = sorted(set(libs))

        return ToolExplanation(
            what_alteryx_does=f"Executes {tool.tool_type} logic: {tool.name or tool.annotation or 'standard operation'}",
            what_pandas_does=f"Translates to equivalent pandas dataframe manipulation ({translation.description})",
            why_selected=f"Deterministic pandas mapping for Alteryx {tool.tool_type} node.",
            libraries=libs,
        )


class UnsupportedTranslator(ToolTranslator):
    """Fallback translator for unrecognized or unsupported tools.

    Never silently passes through. Always emits explicit diagnostics
    with the tool's raw XML configuration preserved (C9).
    """

    def translate(
        self,
        tool: Tool,
        input_variables: list[str],
        workflow: Workflow,
    ) -> TranslationResult:
        lines = [
            f"# ⚠️ UNSUPPORTED TOOL",
            f"# Tool ID: {tool.tool_id}",
            f"# Type: {tool.tool_type}",
            f"# Plugin: {tool.plugin}",
            f"# Name: {tool.name}",
            f"#",
            f"# This tool has no deterministic Python/pandas equivalent implemented.",
            f"# Original XML configuration is preserved in workflow.json.",
            f"#",
            f"# Raw configuration:",
        ]

        # Include raw XML as comments (truncated if very long)
        raw_xml = tool.configuration.raw_xml
        if raw_xml:
            xml_lines = raw_xml.split("\n")
            for xml_line in xml_lines[:30]:  # Cap at 30 lines
                lines.append(f"#   {xml_line}")
            if len(xml_lines) > 30:
                lines.append(f"#   ... ({len(xml_lines) - 30} more lines)")

        lines.append(f"#")
        lines.append(f"# TODO: Implement this transformation manually.")

        code = "\n".join(lines)

        diagnostic = Diagnostic(
            level=DiagnosticLevel.WARNING,
            category="unsupported_tool",
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            message=f"Unsupported tool: {tool.tool_type} ({tool.plugin})",
            detail="No deterministic Python/pandas equivalent is currently implemented.",
        )

        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.UNSUPPORTED,
            python_code=code,
            imports=set(),
            input_variables=input_variables,
            output_map={},  # No output — explicitly unsupported
            diagnostics=[diagnostic],
            description=f"Unsupported tool: {tool.tool_type}",
        )
