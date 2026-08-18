"""Union tool translator.

Combines multiple incoming data streams by column name or by position.
"""

from __future__ import annotations

from awa.model.tool import Tool
from awa.model.workflow import Workflow
from awa.model.translation import TranslationResult
from awa.model.diagnostic import SupportLevel

from .base import ToolTranslator
from .registry import register_type


class UnionTranslator(ToolTranslator):
    """Translates Alteryx Union tool to pd.concat."""

    def translate(
        self,
        tool: Tool,
        input_variables: list[str],
        workflow: Workflow,
    ) -> TranslationResult:
        output_var = f"df_{tool.tool_id}"
        config = tool.configuration.parsed
        by_name_or_pos = config.get("by_name_or_pos", "ByName")

        if not input_variables:
            code = f"{output_var} = pd.DataFrame()"
        elif len(input_variables) == 1:
            code = f"{output_var} = {input_variables[0]}.copy()"
        else:
            inputs_list = ", ".join(input_variables)
            if by_name_or_pos.lower() == "bypos":
                # Align by position: standard concat with ignore_index, assuming identical positional columns
                code = f"{output_var} = pd.concat([{inputs_list}], ignore_index=True, axis=0)"
            else:
                code = f"{output_var} = pd.concat([{inputs_list}], ignore_index=True, sort=False)"

        return TranslationResult(
            tool_id=tool.tool_id,
            tool_type=tool.tool_type,
            support_level=SupportLevel.SUPPORTED,
            python_code=code,
            imports={"import pandas as pd"},
            input_variables=input_variables,
            output_map={"Output": output_var},
            diagnostics=[],
            description=f"Union {len(input_variables)} stream(s)",
        )


register_type("Union", UnionTranslator)
