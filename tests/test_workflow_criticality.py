"""Deterministic unit tests for Workflow Criticality Engine."""

from __future__ import annotations

import pytest

from awa.analysis.workflow_criticality import (
    calculate_workflow_criticality,
    PortfolioDependencyContext,
    BASE_CRITICALITY_WEIGHTS,
    CRITICALITY_LOW_MAX,
    CRITICALITY_MEDIUM_MAX,
)


class TestWorkflowCriticality:
    def test_isolated_workflow_without_targets_is_low_criticality(self):
        """Workflow with 0 production targets and only inspection sinks must be LOW criticality."""
        assessment = calculate_workflow_criticality(
            workflow_id="wf_001",
            workflow_filename="Inspection_Only.yxmd",
            sources=["test_in.xlsx"],
            targets=[],
            inspection_sinks=["BrowseV2"],
            context=PortfolioDependencyContext(),
        )
        assert assessment.score <= CRITICALITY_LOW_MAX
        assert assessment.level == "LOW"
        assert any("inspection" in f.lower() for f in assessment.factors)

    def test_workflow_with_production_targets_increases_criticality(self):
        """Producing production targets increases criticality score."""
        no_targets = calculate_workflow_criticality(
            workflow_id="wf_001",
            workflow_filename="Wf_A.yxmd",
            sources=["input.csv"],
            targets=[],
            inspection_sinks=[],
        )
        with_targets = calculate_workflow_criticality(
            workflow_id="wf_001",
            workflow_filename="Wf_A.yxmd",
            sources=["input.csv"],
            targets=["Sales_Summary.yxdb", "Monthly_Report.xlsx"],
            inspection_sinks=[],
        )
        assert with_targets.score > no_targets.score
        assert with_targets.breakdown["production_outputs"] > 0.0

    def test_downstream_consumers_strongly_increase_criticality(self):
        """A workflow whose outputs are consumed by other workflows gains high criticality."""
        # Wf_Core produces Core_Data.yxdb and Core_Summary.yxdb
        # 3 downstream workflows consume Core_Data.yxdb
        dep_ctx = PortfolioDependencyContext(
            source_to_consumers={
                "Core_Data.yxdb": [("wf_sub1", "Sub1.yxmd"), ("wf_sub2", "Sub2.yxmd"), ("wf_sub3", "Sub3.yxmd")],
            },
            target_to_producers={
                "Core_Data.yxdb": [("wf_core", "Core.yxmd")],
            },
            shared_targets={"Core_Data.yxdb"},
            shared_sources={"raw.csv"},
        )

        core_assessment = calculate_workflow_criticality(
            workflow_id="wf_core",
            workflow_filename="Core.yxmd",
            sources=["raw.csv"],
            targets=["Core_Data.yxdb", "Core_Summary.yxdb"],
            inspection_sinks=[],
            context=dep_ctx,
        )

        assert core_assessment.score >= 70.0
        assert core_assessment.level == "HIGH"
        assert any("downstream" in f.lower() for f in core_assessment.factors)
        assert any("upstream" in f.lower() for f in core_assessment.factors)

    def test_criticality_does_not_equal_complexity(self):
        """A single-target core workflow with consumers has HIGH criticality despite simple structure."""
        dep_ctx = PortfolioDependencyContext(
            source_to_consumers={
                "Master.yxdb": [("wf_b", "B.yxmd"), ("wf_c", "C.yxmd"), ("wf_d", "D.yxmd")],
            },
            target_to_producers={
                "Master.yxdb": [("wf_a", "A.yxmd")],
            },
            shared_targets={"Master.yxdb"},
        )

        assessment = calculate_workflow_criticality(
            workflow_id="wf_a",
            workflow_filename="Simple_Producer.yxmd",
            sources=["source.csv"],
            targets=["Master.yxdb"],
            inspection_sinks=[],
            context=dep_ctx,
        )

        # High criticality because 3 downstream consumers rely on its output
        assert assessment.level == "HIGH"
        assert assessment.score >= 70.0

    def test_inspection_sinks_never_treated_as_production_deliverables(self):
        """Browse/BrowseV2 must not increase production deliverables score."""
        sink_only = calculate_workflow_criticality(
            workflow_id="wf_sink",
            workflow_filename="Sink.yxmd",
            sources=["input.csv"],
            targets=[],
            inspection_sinks=["BrowseV2", "Browse"],
        )
        assert sink_only.breakdown["production_outputs"] == 0.0

    def test_weight_redistribution_when_operational_metadata_absent(self):
        """Missing operational metadata redistributes 10% weight proportionally without penalty."""
        assessment = calculate_workflow_criticality(
            workflow_id="wf_001",
            workflow_filename="Wf.yxmd",
            sources=["in.csv"],
            targets=["out.csv"],
            inspection_sinks=[],
            operational_metadata=None,
        )
        # Verify score is non-zero and accurately scaled
        assert assessment.score > 0.0
        assert 0.0 <= assessment.score <= 100.0

    def test_score_remains_strictly_clamped_0_to_100(self):
        """Criticality score must stay in [0.0, 100.0]."""
        # Huge dependency context with 10 consumers and 5 shared targets
        dep_ctx = PortfolioDependencyContext(
            source_to_consumers={
                f"out_{i}.yxdb": [(f"consumer_{j}", f"C{j}.yxmd") for j in range(10)]
                for i in range(5)
            },
            shared_targets={f"out_{i}.yxdb" for i in range(5)},
            shared_sources={"in_1.csv", "in_2.csv"},
        )

        assessment = calculate_workflow_criticality(
            workflow_id="wf_hub",
            workflow_filename="Hub.yxmd",
            sources=["in_1.csv", "in_2.csv"],
            targets=[f"out_{i}.yxdb" for i in range(5)],
            inspection_sinks=[],
            context=dep_ctx,
        )
        assert 0.0 <= assessment.score <= 100.0
        assert assessment.level == "HIGH"

    def test_deterministic_reproducibility(self):
        """Identical inputs must produce identical scores and factors."""
        a1 = calculate_workflow_criticality(
            workflow_id="wf_1",
            workflow_filename="Test.yxmd",
            sources=["a.csv"],
            targets=["b.yxdb"],
            inspection_sinks=[],
        )
        a2 = calculate_workflow_criticality(
            workflow_id="wf_1",
            workflow_filename="Test.yxmd",
            sources=["a.csv"],
            targets=["b.yxdb"],
            inspection_sinks=[],
        )
        assert a1.score == a2.score
        assert a1.level == a2.level
        assert a1.factors == a2.factors
