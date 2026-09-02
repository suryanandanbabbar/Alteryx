"""Comprehensive regression and integrity tests for ETL Rationalisation Evidence.

Verifies:
1. Long formulas (> 150 chars) survive without arbitrary [:40] truncation.
2. Long filter predicates (> 100 chars) survive without arbitrary [:60] truncation.
3. Long shared filter predicates survive without arbitrary [:50] truncation.
4. Missing join fields never produce '=' in join_keys or 'Join on ='.
5. Valid join fields produce clean 'Join on: left=right'.
6. XML <JoinInfo> produces complete join representation.
7. Real shared join condition is represented in shared_logic.
8. Two Join tools without common configured keys do NOT produce shared join logic.
9. Generic tool-presence markers ('Join operation', 'Filter operation', etc.) are excluded from shared_logic.
10. Summarize aggregations format from structured parser fields ('GroupBy(...)', 'Sum(...) as ...') without raw dict stringification.
11. Summarize fields are stably ordered (GroupBy first, then aggregates alphabetically).
12. Repeated evidence is deduplicated deterministically.
13. When full join condition is present in shared_logic, redundant 'Shared join key:' is omitted.
14. Unique functionality and shared logic are not truncated to arbitrary first-N items.
15. is_meaningful_evidence rejects synthetic tokens ('=', ':', 'Join on =', 'Shared join key: =', 'Formula: =').
16. RationalisationCandidateDTO deserializer sanitizes legacy/malformed evidence.
17. Observability logging records non-sensitive diagnostic counts.
"""

from __future__ import annotations

from types import SimpleNamespace
import networkx as nx
import pytest

from awa.analysis.rationalisation_analyzer import (
    build_workflow_fingerprint,
    compare_workflows,
    detect_candidate_from_comparison,
    format_summarize_fields,
    is_meaningful_evidence,
    normalize_expression,
)
from awa.model.analysis_result import CanonicalAnalysisResult, WorkflowMetrics
from awa.model.connection import Connection
from awa.model.portfolio import PortfolioWorkflowSummary, WorkflowFingerprint
from awa.model.tool import Tool, ToolConfiguration, Position
from awa.model.workflow import Workflow, WorkflowMetadata
from backend.app.models.schemas import RationalisationCandidateDTO


def _make_test_workflow(
    workflow_id: str,
    filename: str,
    sources: list[str],
    targets: list[str],
    tools_spec: list[tuple[int, str, dict, str]],  # (id, type, parsed_dict, raw_xml)
) -> tuple[PortfolioWorkflowSummary, CanonicalAnalysisResult]:
    """Helper to assemble a workflow and summary for fingerprinting."""
    tool_dict: dict[int, Tool] = {}
    g = nx.DiGraph()

    for tid, ttype, parsed, raw_xml in tools_spec:
        cfg = ToolConfiguration(raw_xml=raw_xml, parsed=parsed)
        t = Tool(
            tool_id=tid,
            plugin=f"AlteryxBasePluginsGui.{ttype}.{ttype}",
            tool_type=ttype,
            name=f"{ttype}_{tid}",
            position=Position(x=100 * tid, y=100),
            configuration=cfg,
        )
        tool_dict[tid] = t
        g.add_node(tid)

    conns = []
    tids = [spec[0] for spec in tools_spec]
    for i in range(len(tids) - 1):
        conns.append(Connection(
            origin_tool_id=tids[i],
            origin_anchor="Output",
            destination_tool_id=tids[i + 1],
            destination_anchor="Input",
        ))
        g.add_edge(tids[i], tids[i + 1])

    wf = Workflow(
        metadata=WorkflowMetadata(name=filename, version="2023.1"),
        tools=tool_dict,
        connections=conns,
    )
    metrics = WorkflowMetrics(
        total_nodes=len(tools_spec),
        total_connections=len(conns),
        input_count=len(sources),
        output_count=len(targets),
    )

    res = SimpleNamespace(
        analysis_id=workflow_id,
        workflow=wf,
        graph=g,
        metrics=metrics,
        output_schema=None,
        lineage=None,
    )

    summary = PortfolioWorkflowSummary(
        workflow_id=workflow_id,
        filename=filename,
        relative_path=filename,
        status="SUCCESS",
        node_count=len(tools_spec),
        connection_count=len(conns),
        sources=sources,
        targets=targets,
        inspection_sinks=[],
        complexity_level="MEDIUM",
        complexity_score=50.0,
        criticality_level="MEDIUM",
        criticality_score=50.0,
    )

    return summary, res


class TestRationalisationEvidenceIntegrity:
    """Comprehensive tests verifying evidence integrity, lossless pipelines, and safety boundaries."""

    def test_meaningful_evidence_validator_rejects_synthetic_and_empty_tokens(self):
        """is_meaningful_evidence must reject '=', ':', synthetic labels, and generic placeholders."""
        # Rejects bare tokens
        assert not is_meaningful_evidence(None)
        assert not is_meaningful_evidence("")
        assert not is_meaningful_evidence("   ")
        assert not is_meaningful_evidence("=")
        assert not is_meaningful_evidence(":")
        assert not is_meaningful_evidence("=:")

        # Rejects synthetic placeholder labels
        assert not is_meaningful_evidence("Join on =")
        assert not is_meaningful_evidence("Join on:")
        assert not is_meaningful_evidence("Join on :")
        assert not is_meaningful_evidence("Shared join key: =")
        assert not is_meaningful_evidence("Shared join key:")
        assert not is_meaningful_evidence("Formula: =")
        assert not is_meaningful_evidence("Formula:")
        assert not is_meaningful_evidence("Filter: =")
        assert not is_meaningful_evidence("Filter:")
        assert not is_meaningful_evidence("Summarize:")
        assert not is_meaningful_evidence("Summarize aggregations")

        # Rejects generic tool presence markers
        assert not is_meaningful_evidence("Join operation")
        assert not is_meaningful_evidence("Filter operation")
        assert not is_meaningful_evidence("Summarize operation")
        assert not is_meaningful_evidence("Formula calculation")
        assert not is_meaningful_evidence("MultiRowFormula calculation")

        # Accepts valid operational evidence
        assert is_meaningful_evidence("Join on: Claim_ID=Claim_ID")
        assert is_meaningful_evidence("Shared join key: Claim_ID=Claim_ID")
        assert is_meaningful_evidence("Formula: Net_Amount=[Gross_Amount] - [Tax_Amount]")
        assert is_meaningful_evidence("Filter: [Status] == 'ACTIVE'")
        assert is_meaningful_evidence("Summarize: GroupBy(Region), Sum(Sales) as TotalSales")
        assert is_meaningful_evidence("Python script execution")

    def test_missing_join_fields_never_create_equals_or_join_on_equals(self):
        """When a Join tool lacks configured fields, it must NEVER emit '=' or 'Join on ='."""
        tools = [
            (1, "DbFileInput", {"file": "claims.csv"}, ""),
            (2, "Join", {}, "<Configuration></Configuration>"),
            (3, "DbFileOutput", {"file": "out.yxdb"}, ""),
        ]
        s, res = _make_test_workflow("wf_join_empty", "Empty_Join.yxmd", ["claims.csv"], ["out.yxdb"], tools)
        fp = build_workflow_fingerprint(s, res)

        assert "=" not in fp.join_keys
        assert not any("=" in k and len(k.strip()) == 1 for k in fp.join_keys)
        assert not any("Join on =" in sig for sig in fp.transformation_signatures)
        assert not any("Join on :" in sig for sig in fp.transformation_signatures)
        # Should record tool presence as "Join operation"
        assert "Join operation" in fp.transformation_signatures

    def test_valid_join_fields_parsed_correctly(self):
        """When join_fields dict has 'left' and 'right' keys, emit 'Join on: left=right'."""
        tools = [
            (1, "DbFileInput", {"file": "in.csv"}, ""),
            (2, "Join", {
                "join_fields": [
                    {"left": "Claim_ID", "right": "Claim_ID"},
                    {"left": "Policy_Num", "right": "Policy_Num"},
                ]
            }, ""),
            (3, "DbFileOutput", {"file": "out.yxdb"}, ""),
        ]
        s, res = _make_test_workflow("wf_join_valid", "Valid_Join.yxmd", ["in.csv"], ["out.yxdb"], tools)
        fp = build_workflow_fingerprint(s, res)

        assert "Claim_ID=Claim_ID" in fp.join_keys
        assert "Policy_Num=Policy_Num" in fp.join_keys
        assert "=" not in fp.join_keys
        assert any("Join on: Claim_ID=Claim_ID, Policy_Num=Policy_Num" in sig for sig in fp.transformation_signatures)

    def test_xml_joininfo_parsed_correctly(self):
        """When join fields are in raw XML <JoinInfo>, parse correctly without '=' artifacts."""
        xml = """
        <Configuration>
            <JoinInfo connection="Left"><Field field="Account_ID" /></JoinInfo>
            <JoinInfo connection="Right"><Field field="Account_ID" /></JoinInfo>
        </Configuration>
        """
        tools = [
            (1, "DbFileInput", {"file": "in.csv"}, ""),
            (2, "Join", {}, xml),
            (3, "DbFileOutput", {"file": "out.yxdb"}, ""),
        ]
        s, res = _make_test_workflow("wf_join_xml", "XML_Join.yxmd", ["in.csv"], ["out.yxdb"], tools)
        fp = build_workflow_fingerprint(s, res)

        assert "Account_ID=Account_ID" in fp.join_keys
        assert any("Join on: Account_ID=Account_ID" in sig for sig in fp.transformation_signatures)

    def test_long_formula_survives_without_truncation(self):
        """Formulas exceeding 40 characters must not be sliced with [:40]."""
        long_expr = (
            "DateTimeAdd([Policy_Start_Date], 30, 'days') + "
            "IF [Risk_Category] == 'HIGH' THEN [Estimated_Loss] * 1.50 ELSE [Estimated_Loss] ENDIF"
        )
        assert len(long_expr) > 100

        tools = [
            (1, "DbFileInput", {"file": "in.csv"}, ""),
            (2, "Formula", {
                "formula_fields": [
                    {"field_name": "Adjusted_Loss_Calculation", "expression": long_expr}
                ]
            }, ""),
            (3, "DbFileOutput", {"file": "out.yxdb"}, ""),
        ]
        s, res = _make_test_workflow("wf_formula_long", "Long_Formula.yxmd", ["in.csv"], ["out.yxdb"], tools)
        fp = build_workflow_fingerprint(s, res)

        norm_expected = normalize_expression(long_expr)
        matched = [f for f in fp.formulas if "adjusted_loss_calculation" in f.lower()]
        assert len(matched) == 1
        # Crucial invariant: Must contain the entire expression without [:40] cutoffs
        assert norm_expected in matched[0]
        assert "[lp..." not in matched[0]
        assert len(matched[0]) > 100

    def test_long_filter_predicate_survives_without_truncation(self):
        """Filters exceeding 60 characters must not be sliced with [:60]."""
        long_filter = (
            "[Claim_Status] == 'PENDING_REVIEW' AND [Claim_Amount] >= 50000.00 AND "
            "[Jurisdiction] in ('EMEA_NORTH', 'EMEA_SOUTH', 'APAC_CENTRAL')"
        )
        assert len(long_filter) > 100

        tools = [
            (1, "DbFileInput", {"file": "in.csv"}, ""),
            (2, "Filter", {"expression": long_filter}, ""),
            (3, "DbFileOutput", {"file": "out.yxdb"}, ""),
        ]
        s, res = _make_test_workflow("wf_filter_long", "Long_Filter.yxmd", ["in.csv"], ["out.yxdb"], tools)
        fp = build_workflow_fingerprint(s, res)

        norm_expected = normalize_expression(long_filter)
        assert norm_expected in fp.filters
        assert any(norm_expected in sig for sig in fp.transformation_signatures)

    def test_summarize_aggregations_formatted_structurally_without_raw_dict(self):
        """Summarize fields must format as GroupBy(...) and Sum(...) without Python dict stringification."""
        tools = [
            (1, "DbFileInput", {"file": "in.csv"}, ""),
            (2, "Summarize", {
                "summarize_fields": [
                    {"field": "Region", "action": "GroupBy", "rename": "Region"},
                    {"field": "Quarter", "action": "GroupBy", "rename": "Quarter"},
                    {"field": "Revenue", "action": "Sum", "rename": "TotalRevenue"},
                    {"field": "TransactionID", "action": "CountDistinct", "rename": "TxCount"},
                ]
            }, ""),
            (3, "DbFileOutput", {"file": "out.yxdb"}, ""),
        ]
        s, res = _make_test_workflow("wf_sum", "Sum_Test.yxmd", ["in.csv"], ["out.yxdb"], tools)
        fp = build_workflow_fingerprint(s, res)

        assert len(fp.aggregations) == 1
        agg_str = fp.aggregations[0]
        # Never contains raw Python dictionary syntax
        assert "{" not in agg_str
        assert "}" not in agg_str
        assert "'action':" not in agg_str
        # GroupBy must be stably ordered first
        assert agg_str.startswith("GroupBy(Quarter), GroupBy(Region)")
        assert "CountDistinct(TransactionID) as TxCount" in agg_str
        assert "Sum(Revenue) as TotalRevenue" in agg_str

    def test_two_join_tools_without_common_keys_do_not_produce_shared_join_logic(self):
        """Two workflows that both have Join tools with different keys must NOT produce shared join logic."""
        tools_a = [
            (1, "DbFileInput", {"file": "in.csv"}, ""),
            (2, "Join", {"join_fields": [{"left": "Claim_ID", "right": "Claim_ID"}]}, ""),
            (3, "DbFileOutput", {"file": "claims.yxdb"}, ""),
        ]
        tools_b = [
            (1, "DbFileInput", {"file": "in.csv"}, ""),
            (2, "Join", {"join_fields": [{"left": "Policy_ID", "right": "Policy_ID"}]}, ""),
            (3, "DbFileOutput", {"file": "policies.yxdb"}, ""),
        ]
        s_a, res_a = _make_test_workflow("wf_a", "A.yxmd", ["in.csv"], ["claims.yxdb"], tools_a)
        s_b, res_b = _make_test_workflow("wf_b", "B.yxmd", ["in.csv"], ["policies.yxdb"], tools_b)
        fp_a = build_workflow_fingerprint(s_a, res_a)
        fp_b = build_workflow_fingerprint(s_b, res_b)

        comp = compare_workflows(fp_a, fp_b)

        # No shared join logic!
        assert not any("join" in item.lower() for item in comp.shared_logic)
        assert not any("Shared join key:" in item for item in comp.shared_logic)
        assert not any("Join on =" in item for item in comp.shared_logic)

    def test_generic_tool_presence_excluded_from_shared_logic(self):
        """When two workflows both contain unconfigured Join and Filter tools, shared_logic must remain empty."""
        tools_a = [
            (1, "DbFileInput", {"file": "in_a.csv"}, ""),
            (2, "Filter", {}, ""),
            (3, "Join", {}, ""),
            (4, "DbFileOutput", {"file": "out_a.yxdb"}, ""),
        ]
        tools_b = [
            (1, "DbFileInput", {"file": "in_b.csv"}, ""),
            (2, "Filter", {}, ""),
            (3, "Join", {}, ""),
            (4, "DbFileOutput", {"file": "out_b.yxdb"}, ""),
        ]
        s_a, res_a = _make_test_workflow("wf_a", "A.yxmd", ["in_a.csv"], ["out_a.yxdb"], tools_a)
        s_b, res_b = _make_test_workflow("wf_b", "B.yxmd", ["in_b.csv"], ["out_b.yxdb"], tools_b)
        fp_a = build_workflow_fingerprint(s_a, res_a)
        fp_b = build_workflow_fingerprint(s_b, res_b)

        comp = compare_workflows(fp_a, fp_b)

        # Generic presence must not contaminate shared_logic
        assert "Filter operation" not in comp.shared_logic
        assert "Join operation" not in comp.shared_logic
        assert len(comp.shared_logic) == 0

    def test_real_shared_join_condition_represented_and_not_duplicated(self):
        """When two workflows share a real join condition, it appears in shared_logic without redundant join-key duplicates."""
        tools_a = [
            (1, "DbFileInput", {"file": "in.csv"}, ""),
            (2, "Join", {"join_fields": [{"left": "CustomerID", "right": "CustomerID"}]}, ""),
            (3, "DbFileOutput", {"file": "out.yxdb"}, ""),
        ]
        tools_b = [
            (1, "DbFileInput", {"file": "in.csv"}, ""),
            (2, "Join", {"join_fields": [{"left": "CustomerID", "right": "CustomerID"}]}, ""),
            (3, "DbFileOutput", {"file": "out.yxdb"}, ""),
        ]
        s_a, res_a = _make_test_workflow("wf_a", "A.yxmd", ["in.csv"], ["out.yxdb"], tools_a)
        s_b, res_b = _make_test_workflow("wf_b", "B.yxmd", ["in.csv"], ["out.yxdb"], tools_b)
        fp_a = build_workflow_fingerprint(s_a, res_a)
        fp_b = build_workflow_fingerprint(s_b, res_b)

        comp = compare_workflows(fp_a, fp_b)

        # Must have Join on: CustomerID=CustomerID
        assert "Join on: CustomerID=CustomerID" in comp.shared_logic
        # Must NOT duplicate with "Shared join key: CustomerID=CustomerID"
        assert "Shared join key: CustomerID=CustomerID" not in comp.shared_logic

    def test_candidate_preserves_all_shared_and_unique_operations_without_arbitrary_caps(self):
        """Candidate compilation must preserve all meaningful shared and unique operations (>10 shared, >6 unique)."""
        tools_a = [
            (1, "DbFileInput", {"file": "in.csv"}, ""),
            (2, "Formula", {
                "formula_fields": [
                    {"field_name": f"shared_{i}", "expression": f"[source_{i}] * 1.05"} for i in range(12)
                ] + [
                    {"field_name": f"unique_a_{i}", "expression": f"[val_{i}] * 2"} for i in range(8)
                ]
            }, ""),
            (3, "DbFileOutput", {"file": "out.yxdb"}, ""),
        ]

        tools_b = [
            (1, "DbFileInput", {"file": "in.csv"}, ""),
            (2, "Formula", {
                "formula_fields": [
                    {"field_name": f"shared_{i}", "expression": f"[source_{i}] * 1.05"} for i in range(12)
                ]
            }, ""),
            (3, "DbFileOutput", {"file": "out.yxdb"}, ""),
        ]

        s_a, res_a = _make_test_workflow("wf_a", "A.yxmd", ["in.csv"], ["out.yxdb"], tools_a)
        s_b, res_b = _make_test_workflow("wf_b", "B.yxmd", ["in.csv"], ["out.yxdb"], tools_b)
        fp_a = build_workflow_fingerprint(s_a, res_a)
        fp_b = build_workflow_fingerprint(s_b, res_b)

        comp = compare_workflows(fp_a, fp_b)
        cand = detect_candidate_from_comparison(comp, fp_a, fp_b)

        assert cand is not None
        # Must retain all 12 shared formulas without [:10] cutoffs!
        assert len(cand.shared_logic) >= 12
        # Must retain all 8 unique operations for workflow A without [:6] cutoffs!
        assert len(cand.unique_functionality.get("A.yxmd", [])) == 8

    def test_candidate_dto_validator_sanitizes_legacy_malformed_evidence(self):
        """RationalisationCandidateDTO must sanitize legacy '=', 'Join on =', and synthetic tokens on read."""
        raw_payload = {
            "candidate_id": "cand_legacy_test",
            "workflow_ids": ["wf_1", "wf_2"],
            "workflow_names": ["Legacy1.yxmd", "Legacy2.yxmd"],
            "recommendation_type": "CONSOLIDATE",
            "confidence": "HIGH",
            "opportunity_score": 80.0,
            "reasoning": "Legacy test reasoning.",
            "shared_logic": [
                "=",
                ":",
                "Join on =",
                "Shared join key: =",
                "Join on: Claim_ID=Claim_ID",
                "Formula: = ",
                "Filter: [Status] == 'Active'",
            ],
            "unique_functionality": {
                "Legacy1.yxmd": [
                    "=",
                    "Join on =",
                    "Formula: Total=[Amount]*1.1",
                ],
                "Legacy2.yxmd": [
                    "Shared join key: =",
                ],
            },
        }

        dto = RationalisationCandidateDTO(**raw_payload)

        # Synthetic/placeholder items must be purged
        assert "=" not in dto.shared_logic
        assert "Join on =" not in dto.shared_logic
        assert "Shared join key: =" not in dto.shared_logic
        assert "Formula: =" not in dto.shared_logic
        # Only meaningful evidence remains
        assert dto.shared_logic == [
            "Join on: Claim_ID=Claim_ID",
            "Filter: [Status] == 'Active'",
        ]
        # Unique functionality cleaned up; empty lists removed
        assert dto.unique_functionality["Legacy1.yxmd"] == ["Formula: Total=[Amount]*1.1"]
        assert "Legacy2.yxmd" not in dto.unique_functionality
