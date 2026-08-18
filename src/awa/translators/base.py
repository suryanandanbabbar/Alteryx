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
    with output_map (anchor → variable name).
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
        """Produce an explanation of why this translation was chosen."""
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
    """Fallback translator for unrecognized or unsupported tools."""

    def translate(
        self,
        tool: Tool,
        input_variables: list[str],
        workflow: Workflow,
    ) -> TranslationResult:
        lines = [
            f"# Unsupported Alteryx tool: {tool.tool_type} (Tool #{tool.tool_id})",
            f"# Plugin: {tool.plugin}",
            f"# Raw XML configuration is preserved in workflow.json",
            f"raise NotImplementedError(",
            f"    \"No deterministic Python translation is available for {tool.tool_type} (Tool #{tool.tool_id}).\"",
            f")",
        ]

        code = "\n".join(lines)

        diagnostic = Diagnostic(
            level=DiagnosticLevel.WARNING,
            category="unsupported_tool",
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            message=f"Unsupported tool: {tool.tool_type} ({tool.plugin})",
            detail="No deterministic Python translation is available for this tool.",
        )

        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.UNSUPPORTED,
            python_code=code,
            imports=set(),
            input_variables=input_variables,
            output_map={},
            diagnostics=[diagnostic],
            description=f"Unsupported tool: {tool.tool_type}",
        )
