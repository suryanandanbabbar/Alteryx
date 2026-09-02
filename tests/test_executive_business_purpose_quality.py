"""Tests for Executive Business Summary (Business Purpose) generation and quality.

Validates:
- Evidence-grounded Executive Business Summary structure (Newcastle standard)
- HOW not just WHAT (translating tools, joins, formulas, filters, aggregations into business language)
- Banned buzzword rejection
- Generic filler / one-liner rejection
- Hallucination prevention (dollar figures, strict SLAs, statutory acts)
- Sparse evidence factual bounding
- Deterministic fallback quality
- Business function and business area tag preservation
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from awa.analysis.business_area_classifier import (
    compose_deterministic_business_purpose,
    classify_business_area_deterministic,
    classify_business_function_deterministic,
)
from awa.llm.client import FakeLLMClient
from awa.llm.cache import LLMNarrativeCache
from awa.llm.generator import (
    LLMNarrativeGenerator,
    _is_clean_business_purpose,
    extract_workflow_facts,
    BANNED_PURPOSE_BUZZWORDS,
    GENERIC_PURPOSE_FILLER_PATTERNS,
)
from awa.llm.prompts import (
    WORKFLOW_PURPOSE_PROMPT_VERSION,
    build_workflow_purpose_system_prompt,
    build_workflow_purpose_user_prompt,
)
from awa.llm.schemas import WorkflowFacts
from awa.model.business_summary import (
    BusinessInput,
    BusinessOutput,
    BusinessRule,
    BusinessStage,
    BusinessTransformation,
    WorkflowBusinessSummary,
)
from awa.model.workflow import Workflow, WorkflowMetadata
from awa.model.tool import Tool, ToolConfiguration, Position


def _make_sample_underwriting_workflow() -> tuple[Workflow, WorkflowBusinessSummary]:
    tools = {
        1: Tool(
            tool_id=1,
            plugin="DbFileInput",
            tool_type="DbFileInput",
            name="Commercial Applications Input",
            position=Position(0, 0),
            configuration=ToolConfiguration(raw_xml="", parsed={"file_path": "Commercial_Applications.xlsx"}),
        ),
        2: Tool(
            tool_id=2,
            plugin="DbFileInput",
            tool_type="DbFileInput",
            name="Historical Claims Loss Input",
            position=Position(100, 0),
            configuration=ToolConfiguration(raw_xml="", parsed={"file_path": "Historical_Claims_Loss.csv"}),
        ),
        3: Tool(
            tool_id=3,
            plugin="Join",
            tool_type="Join",
            name="Join On Tax ID",
            position=Position(200, 0),
            configuration=ToolConfiguration(raw_xml="", parsed={"left_keys": ["Tax_ID"], "right_keys": ["Tax_ID"]}),
        ),
        4: Tool(
            tool_id=4,
            plugin="Filter",
            tool_type="Filter",
            name="Filter Active Accounts",
            position=Position(300, 0),
            configuration=ToolConfiguration(raw_xml="", parsed={"expression": "[Active_Status] = 'Y' AND [Loss_Amount] >= 0"}),
        ),
        5: Tool(
            tool_id=5,
            plugin="Formula",
            tool_type="Formula",
            name="Calculate Risk Score",
            position=Position(400, 0),
            configuration=ToolConfiguration(raw_xml="", parsed={"formula_fields": [
                {"field": "Risk_Score", "expression": "[Base_Score] * [Loss_Ratio_Factor]"}
            ]}),
        ),
        6: Tool(
            tool_id=6,
            plugin="Summarize",
            tool_type="Summarize",
            name="Average Risk Score Summary",
            position=Position(500, 0),
            configuration=ToolConfiguration(raw_xml="", parsed={"summarize_fields": [
                {"field": "Risk_Score", "action": "Avg", "rename": "Avg_Risk_Score"}
            ]}),
        ),
        7: Tool(
            tool_id=7,
            plugin="DbFileOutput",
            tool_type="DbFileOutput",
            name="Risk Schedule Output",
            position=Position(600, 0),
            configuration=ToolConfiguration(raw_xml="", parsed={"file_path": "Underwriting_Risk_Schedule.xlsx"}),
        ),
    }
    wf = Workflow(
        metadata=WorkflowMetadata(
            name="Commercial_Underwriting_Rating_Engine.yxmd",
            version="2023.2",
            description="Evaluates applicant exposure and historical loss records to compute commercial policy rating factors.",
        ),
        tools=tools,
        connections=[],
    )
    bs = WorkflowBusinessSummary(
        business_purpose="",
        one_line_purpose="Commercial underwriting risk rating engine",
        why_it_matters="Provides binding risk rates for commercial policies",
        business_function="Commercial Underwriting Rating & Risk Evaluation",
        source_inputs=[
            BusinessInput(tool_id=1, name="Commercial Applications", raw_source="Commercial_Applications.xlsx", source_type="Excel"),
            BusinessInput(tool_id=2, name="Historical Claims Loss", raw_source="Historical_Claims_Loss.csv", source_type="CSV"),
        ],
        business_outputs=[
            BusinessOutput(tool_id=7, name="Underwriting Risk Schedule", raw_destination="Underwriting_Risk_Schedule.xlsx", destination_type="Excel"),
        ],
        business_rules=[
            BusinessRule(rule_name="Eligibility Filtering", category="Filtering", description="Excludes inactive policies"),
            BusinessRule(rule_name="Risk Multiplier", category="Calculation", description="Applies loss ratio factor to calculate final risk score"),
        ],
        transformations=[
            BusinessTransformation(category="Join / Enrichment", description="Combines applicant applications with historical claims"),
            BusinessTransformation(category="Calculation / Derivation", description="Calculates risk score from base score and loss ratio"),
        ],
    )
    return wf, bs


class TestExecutiveBusinessPurposeQuality:
    """Test suite verifying Executive Business Summary standards."""

    def test_banned_buzzwords_rejected(self):
        """Every banned corporate buzzword must be rejected by validation."""
        template = "The workflow supports underwriting by ingesting applicant data and {buzzword} to generate the policy output."
        for bw in BANNED_PURPOSE_BUZZWORDS:
            test_text = template.format(buzzword=bw)
            assert not _is_clean_business_purpose(test_text), f"Failed to reject banned buzzword: '{bw}'"

    def test_generic_filler_patterns_rejected(self):
        """Vague generic templates and filler patterns must be rejected."""
        for pattern in GENERIC_PURPOSE_FILLER_PATTERNS:
            assert not _is_clean_business_purpose(pattern), f"Failed to reject generic filler: '{pattern}'"

    def test_weak_one_liners_rejected(self):
        """Trivial one-liners without explanation must be rejected."""
        weak_samples = [
            "Processes data.",
            "Transforms data to support decisions.",
            "Automates data processing.",
            "Processes operational data to generate business deliverables and decision outputs.",
            "Automates underwriting data processing to generate business deliverables and decision outputs.",
        ]
        for s in weak_samples:
            assert not _is_clean_business_purpose(s), f"Failed to reject weak sample: '{s}'"

    def test_tool_id_dumping_rejected(self):
        """Raw tool ID dumps without business translation must be rejected."""
        tool_dumps = [
            "The workflow uses Tool #1 to read data, then Tool #2 to join, and Tool #3 to output.",
            "Data enters Tool_1 and flows into Tool_2 where calculations occur before writing to Tool_3.",
        ]
        for td in tool_dumps:
            assert not _is_clean_business_purpose(td), f"Failed to reject tool dumping: '{td}'"

    def test_hallucinated_dollar_figures_rejected(self):
        """Specific ungrounded dollar figures must be rejected when facts have none."""
        wf, bs = _make_sample_underwriting_workflow()
        facts = extract_workflow_facts(wf, bs)

        hallucinated = (
            "The workflow processes commercial applications and historical claims to generate underwriting ratings, "
            "saving $4,500,000 annually across the commercial underwriting division."
        )
        assert not _is_clean_business_purpose(hallucinated, facts)

    def test_hallucinated_strict_sla_rejected(self):
        """Fabricated strict SLAs must be rejected when facts have no SLA evidence."""
        wf, bs = _make_sample_underwriting_workflow()
        facts = extract_workflow_facts(wf, bs)

        hallucinated = (
            "The workflow processes commercial applications under a strict SLA of 15 minutes to generate "
            "underwriting ratings for downstream policy administration."
        )
        assert not _is_clean_business_purpose(hallucinated, facts)

    def test_hallucinated_statutory_mandate_rejected(self):
        """Fabricated statutory/regulatory acts must be rejected when facts have no compliance evidence."""
        wf, bs = _make_sample_underwriting_workflow()
        facts = extract_workflow_facts(wf, bs)

        hallucinated = (
            "The workflow processes commercial applications to satisfy Dodd-Frank regulatory mandate compliance "
            "reporting for institutional risk oversight."
        )
        assert not _is_clean_business_purpose(hallucinated, facts)

    def test_extract_workflow_facts_includes_rich_operations(self):
        """extract_workflow_facts captures formulas, filters, joins, and aggregations from tools."""
        wf, bs = _make_sample_underwriting_workflow()
        facts = extract_workflow_facts(wf, bs)

        assert any("Risk_Score" in calc for calc in facts.key_calculations)
        assert any("Active_Status" in flt for flt in facts.filtering_criteria)
        assert any("Tax_ID" in jn for jn in facts.joins_and_merges)
        assert any("Risk_Score" in agg for agg in facts.aggregations)

    def test_deterministic_fallback_uses_executive_summary_structure(self):
        """Deterministic fallback produces an evidence-grounded summary without buzzwords."""
        wf, bs = _make_sample_underwriting_workflow()
        purpose = compose_deterministic_business_purpose(
            wf,
            business_summary=bs,
            business_function=bs.business_function,
            business_area="Underwriting",
            workflow_name=wf.metadata.name,
        )

        # Invariants:
        # 1. Names business function / process
        assert "commercial underwriting rating & risk evaluation" in purpose.lower()
        # 2. Names concrete inputs
        assert "Commercial Applications" in purpose or "Historical Claims Loss" in purpose
        # 3. Names concrete rules / processing
        assert "business rules" in purpose or "combines" in purpose or "calculates" in purpose
        # 4. Names output deliverable
        assert "Underwriting Risk Schedule" in purpose
        # 5. Connects to operational outcome
        assert "underwriting policy decisions" in purpose
        # 6. Zero banned buzzwords
        for bw in BANNED_PURPOSE_BUZZWORDS:
            assert bw not in purpose.lower()
        # 7. Appropriate length (35-75 words)
        words = purpose.split()
        assert 35 <= len(words) <= 75

    def test_sparse_evidence_produces_bounded_factual_summary(self):
        """Workflows with sparse evidence produce a bounded summary without invented context."""
        wf = Workflow(metadata=WorkflowMetadata(name="Internal_Batch_Job.yxmd", version="2021.1"), tools={}, connections=[])
        bs = WorkflowBusinessSummary(business_purpose="", one_line_purpose="", why_it_matters="")

        purpose = compose_deterministic_business_purpose(
            wf,
            business_summary=bs,
            business_function="",
            business_area="Other / Unclassified",
            workflow_name="Internal_Batch_Job.yxmd",
        )

        assert "automated operational data processing" in purpose
        assert "does not specify external input datasets" in purpose
        assert "Underwriting" not in purpose
        assert "Claims" not in purpose
        for bw in BANNED_PURPOSE_BUZZWORDS:
            assert bw not in purpose.lower()

    def test_generator_accepts_valid_executive_business_summary(self):
        """Valid executive business summary following Newcastle standard is accepted."""
        wf, bs = _make_sample_underwriting_workflow()
        valid_summary = (
            "The workflow supports commercial underwriting risk evaluation by ingesting applicant records and historical claims. "
            "It combines policyholder submissions with historical loss experience on Tax ID, filters active accounts, "
            "calculates risk score metrics using loss ratio factors, and aggregates risk ratings. The resulting "
            "Underwriting Risk Schedule provides standardized risk evaluation criteria to support underwriting policy decisions."
        )
        payload = json.dumps({
            "business_purpose": valid_summary,
            "business_function": "Commercial Underwriting Rating & Risk Evaluation",
            "business_area_tag": "Underwriting",
        })
        client = FakeLLMClient(response=payload, is_available=True)
        gen = LLMNarrativeGenerator(client=client, cache=LLMNarrativeCache())

        res = gen.generate_business_purpose(wf, bs, workflow_id="wf_exec_test_01")
        assert res.source == "llm"
        assert res.business_purpose == valid_summary
        assert res.business_area_tag == "Underwriting"
        assert res.business_function == "Commercial Underwriting Rating & Risk Evaluation"

    def test_generator_rejects_buzzwordy_llm_output_and_falls_back(self):
        """LLM response loaded with buzzwords is rejected and safely replaced with clean fallback."""
        wf, bs = _make_sample_underwriting_workflow()
        buzzwordy_summary = (
            "The workflow leverages data to streamline processes and drive insights for underwriting operations, "
            "enhancing efficiency and providing actionable insights to optimize operations and support informed decision-making."
        )
        payload = json.dumps({
            "business_purpose": buzzwordy_summary,
            "business_function": "Underwriting",
            "business_area_tag": "Underwriting",
        })
        client = FakeLLMClient(response=payload, is_available=True)
        gen = LLMNarrativeGenerator(client=client, cache=LLMNarrativeCache())

        res = gen.generate_business_purpose(wf, bs, workflow_id="wf_buzzword_reject_test")
        assert res.source == "deterministic_fallback"
        assert "leverages data" not in res.business_purpose
        assert "actionable insights" not in res.business_purpose
        assert "Commercial Applications" in res.business_purpose or "Underwriting Risk Schedule" in res.business_purpose

    def test_prompt_version_is_updated(self):
        """WORKFLOW_PURPOSE_PROMPT_VERSION is 4.0."""
        assert WORKFLOW_PURPOSE_PROMPT_VERSION == "4.0"
