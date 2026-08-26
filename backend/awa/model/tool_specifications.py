"""Tool Specifications data model and extraction helpers.

Defines the structure for Tool Specifications XLSX document where deterministic
facts (Tool ID, XML name, tool type, inputs, outputs, topology) are strictly separated
from LLM-generated workflow explanations (Role, Data Flow Explanation).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import networkx as nx

from awa.model.workflow import Workflow, Tool
from awa.graph.builder import execution_order


@dataclass
class ToolSpecificationRow:
    """Represents a single row in the Tool Specifications worksheet."""
    tool_id: int
    tool_id_formatted: str               # e.g. "#1"
    xml_tool_name: str                   # e.g. "AlteryxBasePluginsGui.DbFileInput.DbFileInput"
    tool_type: str                       # e.g. "DbFileInput"
    role: str                            # LLM-generated "Role — What It Does"
    data_flow_explanation: str           # LLM-generated "Data Flow Explanation"
    input_tool: str                      # Deterministic: "Source" or "#3 Summarize; #7 Join"
    output_tool: str                     # Deterministic: "None" or "#2 Filter; #5 Browse"


@dataclass
class ToolSpecificationsDocument:
    """Represents the complete Tool Specifications document."""
    workflow_name: str
    rows: list[ToolSpecificationRow] = field(default_factory=list)


def format_input_tools(workflow: Workflow, graph: nx.DiGraph | None, tool_id: int) -> str:
    """Format immediate upstream tools deterministically (e.g. 'Source' or '#1 DbFileInput; #3 Filter')."""
    if graph is None or not graph.has_node(tool_id):
        return "Source"

    predecessors = sorted(list(graph.predecessors(tool_id)))
    if not predecessors:
        return "Source"

    parts = []
    for pred_id in predecessors:
        pred_tool = workflow.tools.get(pred_id)
        ttype = pred_tool.tool_type if pred_tool else "Tool"
        parts.append(f"#{pred_id} {ttype}")

    return "; ".join(parts)


def format_output_tools(workflow: Workflow, graph: nx.DiGraph | None, tool_id: int) -> str:
    """Format immediate downstream tools deterministically (e.g. 'None' or '#2 Filter; #5 Browse')."""
    if graph is None or not graph.has_node(tool_id):
        return "None"

    successors = sorted(list(graph.successors(tool_id)))
    if not successors:
        return "None"

    parts = []
    for succ_id in successors:
        succ_tool = workflow.tools.get(succ_id)
        ttype = succ_tool.tool_type if succ_tool else "Tool"
        parts.append(f"#{succ_id} {ttype}")

    return "; ".join(parts)


def build_tool_specifications_document(
    workflow: Workflow,
    graph: nx.DiGraph | None,
    tool_specs: dict[int, dict[str, str]] | None = None,
) -> ToolSpecificationsDocument:
    """Build a ToolSpecificationsDocument from workflow, graph, and generated tool specs.

    Args:
        workflow: Canonical Workflow model.
        graph: Workflow directed acyclic graph.
        tool_specs: Optional dictionary mapping tool_id -> {'role': str, 'data_flow_explanation': str}.
    """
    tool_specs = tool_specs or {}
    workflow_name = workflow.metadata.name or "Alteryx Workflow"

    # Order tools by topological execution order, with any leftover tools appended by ID
    ordered_tool_ids: list[int] = []
    if graph is not None:
        try:
            exec_steps = execution_order(graph)
            ordered_tool_ids = [step.tool_id for step in exec_steps if step.tool_id in workflow.tools]
        except Exception:
            ordered_tool_ids = []

    # Include any remaining tools not in execution steps
    for tid in sorted(workflow.tools.keys()):
        if tid not in ordered_tool_ids:
            ordered_tool_ids.append(tid)

    rows: list[ToolSpecificationRow] = []
    for tid in ordered_tool_ids:
        tool = workflow.tools[tid]
        xml_name = tool.plugin or tool.tool_type
        tool_type = tool.tool_type or "Tool"
        inp_str = format_input_tools(workflow, graph, tid)
        out_str = format_output_tools(workflow, graph, tid)

        spec = tool_specs.get(tid, {})
        role = spec.get("role", "")
        data_flow = spec.get("data_flow_explanation", "")

        # Fallback if empty
        if not role:
            role = f"Applies the configured {tool_type} operation to the incoming data stream."
        if not data_flow:
            if inp_str == "Source" and out_str == "None":
                data_flow = "Ingests source records and performs localized processing."
            elif inp_str == "Source":
                data_flow = f"Ingests source records and passes the data stream to {out_str}."
            elif out_str == "None":
                data_flow = f"Receives processed data from {inp_str} and writes to the final output destination."
            else:
                data_flow = f"Receives data from {inp_str} and passes the resulting stream to {out_str}."

        rows.append(
            ToolSpecificationRow(
                tool_id=tid,
                tool_id_formatted=f"#{tid}",
                xml_tool_name=xml_name,
                tool_type=tool_type,
                role=role,
                data_flow_explanation=data_flow,
                input_tool=inp_str,
                output_tool=out_str,
            )
        )

    return ToolSpecificationsDocument(
        workflow_name=workflow_name,
        rows=rows,
    )
