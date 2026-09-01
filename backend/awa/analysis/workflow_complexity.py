"""Deterministic Workflow Complexity Engine.

Evaluates workflow complexity using multi-dimensional canonical IR facts:
1. Workflow Structural Size (20%)
2. Transformation Complexity (25%)
3. DAG Topology Complexity (25%)
4. Expression Complexity (15%)
5. Runtime / Integration Complexity (15%)

CRITICAL INVARIANTS:
1. Zero LLM involvement. Purely deterministic and auditable.
2. Clamped normalized score between 0.0 and 100.0.
3. Centralized configurable weights and thresholds:
   - 0–34: LOW
   - 35–69: MEDIUM
   - 70–100: HIGH
4. Explanatory factors derived strictly from actual workflow evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import networkx as nx
from typing import Any, Literal

from awa.model.analysis_result import CanonicalAnalysisResult

# ---------------------------------------------------------------------------
# Central Configuration (No magic constants scattered in code)
# ---------------------------------------------------------------------------

COMPLEXITY_WEIGHTS: dict[str, float] = {
    "size": 0.20,
    "transformation": 0.25,
    "topology": 0.25,
    "expression": 0.15,
    "runtime": 0.15,
}

COMPLEXITY_LOW_MAX: float = 34.0
COMPLEXITY_MEDIUM_MAX: float = 69.0

# Alteryx tool complexity weights based on transformation semantics
TOOL_COMPLEXITY_WEIGHTS: dict[str, int] = {
    # 1: Basic pass-through, field renaming, sorting, sampling
    "Select": 1,
    "AlteryxSelect": 1,
    "Filter": 1,
    "Sort": 1,
    "Sample": 1,
    "Unique": 1,
    "DbFileInput": 1,
    "FileInput": 1,
    "TextInput": 1,
    "DbFileOutput": 1,
    "FileOutput": 1,
    "BrowseV2": 1,
    "Browse": 1,
    "RecordID": 1,
    "Directory": 2,
    # 2: Expressions, formatting, and aggregations
    "Formula": 2,
    "Summarize": 2,
    "RegEx": 2,
    "DateTime": 2,
    "TextToColumns": 2,
    "AutoField": 1,
    # 3: Relational restructuring, multi-stream joins and appends
    "Join": 3,
    "Union": 3,
    "JoinMultiple": 3,
    "AppendFields": 3,
    "FindReplace": 3,
    "RunningTotal": 3,
    # 4: Pivoting, transpose, and advanced multi-row/field logic
    "CrossTab": 4,
    "Transpose": 4,
    "MultiRowFormula": 4,
    "Multi-Row Formula": 4,
    "MultiFieldFormula": 4,
    "Multi-Field Formula": 4,
    "Tile": 4,
    "DynamicSelect": 3,
    "DynamicRename": 3,
    "Dynamic Rename": 3,
    # 5: Dynamic execution, macros & scripting
    "DynamicInput": 5,
    "Dynamic Input": 5,
    "DynamicOutput": 5,
    "Dynamic Output": 5,
    "Macro": 5,
    "Python": 5,
    "R": 5,
}

DEFAULT_TOOL_WEIGHT: int = 2


@dataclass
class ComplexityAssessment:
    """Deterministic complexity assessment result."""
    score: float
    level: Literal["HIGH", "MEDIUM", "LOW"]
    factors: list[str] = field(default_factory=list)
    breakdown: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "level": self.level,
            "factors": self.factors,
            "breakdown": self.breakdown,
        }


def _get_cfg_dict(tool: Any) -> dict:
    if not tool or not tool.configuration:
        return {}
    if hasattr(tool.configuration, "parsed") and isinstance(tool.configuration.parsed, dict):
        return tool.configuration.parsed
    if isinstance(tool.configuration, dict):
        return tool.configuration
    return {}


def calculate_workflow_complexity(result: Any) -> ComplexityAssessment:
    """Deterministically compute workflow complexity from CanonicalAnalysisResult or workflow IR."""
    wf = getattr(result, "workflow", None)
    tools = wf.tools if wf and hasattr(wf, "tools") else {}
    connections = wf.connections if wf and hasattr(wf, "connections") else []
    graph = result.graph if isinstance(getattr(result, "graph", None), nx.DiGraph) else nx.DiGraph()

    total_tools = len(tools)
    metrics = getattr(result, "metrics", None)
    total_connections = metrics.total_connections if metrics and hasattr(metrics, "total_connections") else len(connections)
    factors: list[str] = []

    if total_tools == 0:
        return ComplexityAssessment(
            score=0.0,
            level="LOW",
            factors=["Empty workflow (0 tools)"],
            breakdown={"size": 0.0, "transformation": 0.0, "topology": 0.0, "expression": 0.0, "runtime": 0.0},
        )

    # -----------------------------------------------------------------------
    # 1. Structural Size (20%)
    # -----------------------------------------------------------------------
    distinct_tool_types = len(set(t.tool_type for t in tools.values()))
    tool_pts = min(100.0, (total_tools / 25.0) * 100.0)
    conn_pts = min(100.0, (total_connections / 28.0) * 100.0)
    type_pts = min(100.0, (distinct_tool_types / 8.0) * 100.0)

    size_score = round(0.45 * tool_pts + 0.35 * conn_pts + 0.20 * type_pts, 1)

    factors.append(f"{total_tools} tools")
    factors.append(f"{total_connections} connections")
    if distinct_tool_types >= 5:
        factors.append(f"{distinct_tool_types} distinct tool types")

    # -----------------------------------------------------------------------
    # 2. Transformation Complexity (25%)
    # -----------------------------------------------------------------------
    raw_weights = [TOOL_COMPLEXITY_WEIGHTS.get(t.tool_type, DEFAULT_TOOL_WEIGHT) for t in tools.values()]
    total_weight_sum = sum(raw_weights)
    high_order_count = sum(1 for w in raw_weights if w >= 3)
    joins_count = sum(1 for t in tools.values() if "Join" in t.tool_type)
    unions_count = sum(1 for t in tools.values() if t.tool_type == "Union")
    pivots_count = sum(1 for t in tools.values() if t.tool_type in ("CrossTab", "Transpose"))
    multi_formula_count = sum(1 for t in tools.values() if "Multi" in t.tool_type)

    weight_score = min(100.0, (total_weight_sum / 35.0) * 75.0 + (high_order_count * 5.0))
    transformation_score = round(min(100.0, weight_score), 1)

    if joins_count > 0:
        factors.append(f"{joins_count} join{'s' if joins_count > 1 else ''}")
    if unions_count > 0:
        factors.append(f"{unions_count} union{'s' if unions_count > 1 else ''}")
    if pivots_count > 0:
        factors.append(f"{pivots_count} pivoting operation{'s' if pivots_count > 1 else ''}")
    if multi_formula_count > 0:
        factors.append(f"{multi_formula_count} multi-row/field transformation{'s' if multi_formula_count > 1 else ''}")

    # -----------------------------------------------------------------------
    # 3. DAG Topology Complexity (25%)
    # -----------------------------------------------------------------------
    branch_points = 0
    merge_points = 0
    max_fan_out = 0
    max_fan_in = 0
    dag_depth = 0

    if graph.number_of_nodes() > 0:
        for node in graph.nodes():
            out_deg = graph.out_degree(node)
            in_deg = graph.in_degree(node)
            if out_deg > 1:
                branch_points += 1
            if in_deg > 1:
                merge_points += 1
            if out_deg > max_fan_out:
                max_fan_out = out_deg
            if in_deg > max_fan_in:
                max_fan_in = in_deg

        if nx.is_directed_acyclic_graph(graph):
            try:
                dag_depth = nx.dag_longest_path_length(graph)
            except Exception:
                dag_depth = 0
        else:
            dag_depth = 0

    branch_pts = min(40.0, branch_points * 10.0)
    merge_pts = min(40.0, merge_points * 12.0)
    depth_pts = min(35.0, (dag_depth / 12.0) * 35.0)

    topology_score = round(min(100.0, branch_pts + merge_pts + depth_pts), 1)

    if branch_points > 0:
        factors.append(f"{branch_points} branch point{'s' if branch_points > 1 else ''}")
    if merge_points > 0:
        factors.append(f"{merge_points} merge point{'s' if merge_points > 1 else ''}")
    if dag_depth >= 6:
        factors.append(f"DAG depth of {dag_depth}")

    # -----------------------------------------------------------------------
    # 4. Expression Complexity (15%)
    # -----------------------------------------------------------------------
    total_expressions = 0
    complex_conditional_count = 0
    expression_char_len = 0

    for tool in tools.values():
        cfg = _get_cfg_dict(tool)
        formula_fields = cfg.get("formula_fields", [])
        if isinstance(formula_fields, list):
            for ff in formula_fields:
                if isinstance(ff, dict):
                    expr = str(ff.get("expression", "") or "")
                    if expr.strip():
                        total_expressions += 1
                        expression_char_len += len(expr)
                        upper_expr = expr.upper()
                        if "IF " in upper_expr or "IIF(" in upper_expr or "THEN " in upper_expr:
                            complex_conditional_count += 1

        filter_expr = str(cfg.get("expression", "") or "")
        if tool.tool_type == "Filter" and filter_expr.strip():
            total_expressions += 1
            expression_char_len += len(filter_expr)
            if " AND " in filter_expr.upper() or " OR " in filter_expr.upper():
                complex_conditional_count += 1

    expr_count_pts = min(50.0, total_expressions * 12.0)
    expr_cond_pts = min(30.0, complex_conditional_count * 15.0)
    expr_len_pts = min(20.0, (expression_char_len / 200.0) * 20.0)

    expression_score = round(min(100.0, expr_count_pts + expr_cond_pts + expr_len_pts), 1)

    if total_expressions > 0:
        factors.append(f"{total_expressions} formula/filter expression{'s' if total_expressions > 1 else ''}")
    if complex_conditional_count > 0:
        factors.append(f"{complex_conditional_count} conditional logic block{'s' if complex_conditional_count > 1 else ''}")

    # -----------------------------------------------------------------------
    # 5. Runtime / Integration Complexity (15%)
    # -----------------------------------------------------------------------
    runtime_score_accum = 0.0

    python_count = sum(1 for t in tools.values() if t.tool_type == "Python")
    r_count = sum(1 for t in tools.values() if t.tool_type == "R")
    macro_count = sum(1 for t in tools.values() if t.tool_type == "Macro" or "Macro" in getattr(t, "plugin", ""))
    dynamic_count = sum(1 for t in tools.values() if "Dynamic" in t.tool_type)
    db_conn_count = 0

    for t in tools.values():
        cfg = _get_cfg_dict(t)
        file_path = str(cfg.get("file_path", "") or "")
        if any(db_prefix in file_path.lower() for db_prefix in ("odbc:", "oledb:", "oracle", "sqlserver", "postgres")):
            db_conn_count += 1

    if python_count > 0:
        runtime_score_accum += min(100.0, 45.0 + (python_count - 1) * 15.0)
        factors.append(f"{python_count} Python script execution{'s' if python_count > 1 else ''} detected")
    if r_count > 0:
        runtime_score_accum += min(100.0, 45.0 + (r_count - 1) * 15.0)
        factors.append(f"{r_count} R script execution{'s' if r_count > 1 else ''} detected")
    if macro_count > 0:
        runtime_score_accum += min(50.0, macro_count * 20.0)
        factors.append(f"{macro_count} macro dependency{'ies' if macro_count > 1 else ''}")
    if dynamic_count > 0:
        runtime_score_accum += min(45.0, dynamic_count * 20.0)
        factors.append(f"{dynamic_count} dynamic data connector{'s' if dynamic_count > 1 else ''}")
    if db_conn_count > 0:
        runtime_score_accum += min(35.0, db_conn_count * 15.0)
        factors.append(f"{db_conn_count} database connection{'s' if db_conn_count > 1 else ''}")

    runtime_score = round(min(100.0, runtime_score_accum), 1)

    # -----------------------------------------------------------------------
    # Final Normalized Score & Level Classification
    # -----------------------------------------------------------------------
    final_score = (
        COMPLEXITY_WEIGHTS["size"] * size_score
        + COMPLEXITY_WEIGHTS["transformation"] * transformation_score
        + COMPLEXITY_WEIGHTS["topology"] * topology_score
        + COMPLEXITY_WEIGHTS["expression"] * expression_score
        + COMPLEXITY_WEIGHTS["runtime"] * runtime_score
    )

    final_score = round(max(0.0, min(100.0, final_score)), 1)

    if final_score >= COMPLEXITY_MEDIUM_MAX + 1:
        level: Literal["HIGH", "MEDIUM", "LOW"] = "HIGH"
    elif final_score >= COMPLEXITY_LOW_MAX + 1:
        level = "MEDIUM"
    else:
        level = "LOW"

    return ComplexityAssessment(
        score=final_score,
        level=level,
        factors=factors[:7],  # Keep top concise factors
        breakdown={
            "size": size_score,
            "transformation": transformation_score,
            "topology": topology_score,
            "expression": expression_score,
            "runtime": runtime_score,
        },
    )
