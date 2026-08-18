"""Translation result model."""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field

from .diagnostic import Diagnostic, SupportLevel


@dataclass
class TranslationResult:
    """Result of translating a single Alteryx tool to Python/pandas.
    
    Attributes:
        tool_id: The Alteryx tool ID.
        tool_type: The Alteryx tool type string.
        support_level: Classification of translation support.
        python_code: Generated Python/pandas code.
        imports: Set of import statements required.
        input_variables: List of input DataFrame variable names.
        output_map: Mapping of output anchor names to DataFrame variable names.
                    e.g., {'True': 'df_2_true', 'False': 'df_2_false'} for Filter,
                    or {'Output': 'df_1'} for single-output tools.
        diagnostics: Tool-specific diagnostic messages.
        description: Human-readable description of the transformation.
    """
    tool_id: int
    tool_type: str
    support_level: SupportLevel
    python_code: str
    imports: set[str] = dc_field(default_factory=set)
    input_variables: list[str] = dc_field(default_factory=list)
    output_map: dict[str, str] = dc_field(default_factory=dict)
    diagnostics: list[Diagnostic] = dc_field(default_factory=list)
    description: str = ""

    def primary_output(self) -> str | None:
        """Return the primary output variable name, if any.
        
        For single-output tools, this is the only output.
        For multi-output tools, this returns the first output alphabetically.
        """
        if not self.output_map:
            return None
        if len(self.output_map) == 1:
            return next(iter(self.output_map.values()))
        # Convention: return the 'main' output for known multi-output tools
        # Join: 'Join' is primary, Filter: 'True' is primary, Unique: 'Unique' is primary
        for preferred in ("Join", "True", "Unique", "Output"):
            if preferred in self.output_map:
                return self.output_map[preferred]
        return next(iter(self.output_map.values()))
