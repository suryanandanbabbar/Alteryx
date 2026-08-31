"""Base translator interface and specialized category translators."""

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


class PassThroughTranslator(ToolTranslator):
    """Pass-through translator for inspection, sequencing, and routing tools (e.g. Browse, BlockUntilDone, Message)."""

    def translate(
        self,
        tool: Tool,
        input_variables: list[str],
        workflow: Workflow,
    ) -> TranslationResult:
        in_var = input_variables[0] if input_variables else "None"
        lines = [
            f"# Tool #{tool.tool_id}: {tool.tool_type} (Pass-through / Inspection)",
            f"# Operation does not modify dataset semantics; passes incoming dataframe through.",
        ]
        code = "\n".join(lines)

        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.PASS_THROUGH,
            python_code=code,
            imports=set(),
            input_variables=input_variables,
            output_map={
                "Output": in_var,
                "Output1": in_var,
                "Output2": in_var,
                "Output3": in_var,
            },
            diagnostics=[],
            description=f"Pass-through / Inspection tool ({tool.tool_type})",
        )


class DocumentationTranslator(ToolTranslator):
    """Translator for presentation, documentation, and annotation tools (e.g. Comment, Tool Container)."""

    def translate(
        self,
        tool: Tool,
        input_variables: list[str],
        workflow: Workflow,
    ) -> TranslationResult:
        lines = [
            f"# Tool #{tool.tool_id}: {tool.tool_type} (Documentation / Presentation only)",
            f"# No executable data transformation generated.",
        ]
        code = "\n".join(lines)

        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.DOCUMENTATION_ONLY,
            python_code=code,
            imports=set(),
            input_variables=input_variables,
            output_map={},
            diagnostics=[],
            description=f"Documentation tool ({tool.tool_type})",
        )


class ExternalExecutionTranslator(ToolTranslator):
    """Translator for tools that execute externally (e.g. Python, R, Run Command, Download, In-DB, Connectors)."""

    def translate(
        self,
        tool: Tool,
        input_variables: list[str],
        workflow: Workflow,
    ) -> TranslationResult:
        out_var = f"df_{tool.tool_id}"
        lines = [
            f"# External execution tool: {tool.tool_type} (Tool #{tool.tool_id})",
            f"# Plugin: {tool.plugin}",
            f"# This tool operates externally or depends on an external runtime environment.",
            f"{out_var} = pd.DataFrame()  # External execution placeholder",
            f"raise NotImplementedError(",
            f"    \"Tool #{tool.tool_id} ({tool.tool_type}) requires external execution ({tool.plugin}).\"",
            f")",
        ]
        code = "\n".join(lines)

        diagnostic = Diagnostic(
            level=DiagnosticLevel.WARNING,
            category="external_execution",
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            message=f"External execution tool: {tool.tool_type} ({tool.plugin})",
            detail="Executes externally or requires an external service/runtime.",
        )

        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.EXTERNAL_EXECUTION,
            python_code=code,
            imports={"import pandas as pd"},
            input_variables=input_variables,
            output_map={"Output": out_var},
            diagnostics=[diagnostic],
            description=f"External execution tool ({tool.tool_type})",
        )


class PartialSupportTranslator(ToolTranslator):
    """Translator for partially supported tools with explicit configuration warnings."""

    def translate(
        self,
        tool: Tool,
        input_variables: list[str],
        workflow: Workflow,
    ) -> TranslationResult:
        lines = [
            f"# Partially supported Alteryx tool: {tool.tool_type} (Tool #{tool.tool_id})",
            f"# Plugin: {tool.plugin}",
            f"# Only specific configurations can be deterministically reproduced in pandas.",
            f"raise NotImplementedError(",
            f"    \"Partial support: No deterministic pandas equivalent for current {tool.tool_type} configuration.\"",
            f")",
        ]
        code = "\n".join(lines)

        diagnostic = Diagnostic(
            level=DiagnosticLevel.WARNING,
            category="partial_support",
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            message=f"Partially supported tool: {tool.tool_type} ({tool.plugin})",
            detail="Only specific matching, spatial, or dynamic configurations can be translated.",
        )

        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.PARTIAL,
            python_code=code,
            imports=set(),
            input_variables=input_variables,
            output_map={},
            diagnostics=[diagnostic],
            description=f"Partially supported tool ({tool.tool_type})",
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
