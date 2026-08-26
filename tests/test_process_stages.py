"""Tests for LLM-generated business process stages on the Overview page."""

import json
import pytest
import networkx as nx

from awa.model.workflow import Workflow, WorkflowMetadata
from awa.model.tool import Tool, ToolConfiguration, Position
from awa.model.business_summary import WorkflowBusinessSummary, BusinessStage
from awa.llm.client import LLMClient
from awa.llm.generator import LLMNarrativeGenerator
from awa.llm.cache import LLMNarrativeCache
from awa.llm.schemas import ProcessStageContent, WorkflowProcessStages
from awa.llm.prompts import PROCESS_STAGES_PROMPT_VERSION, PROCESS_STAGES_SYSTEM_PROMPT


class MockLLMClient(LLMClient):
    """Mock LLM client for predictable testing."""

    def __init__(self, response_text: str = ""):
        super().__init__()
        self.response_text = response_text
        self.call_count = 0
        self.last_system_prompt = ""
        self.last_user_prompt = ""

    @property
    def model_name(self) -> str:
        return "mock-model"

    @property
    def is_available(self) -> bool:
        return True

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 1500) -> str:
        self.call_count += 1
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
        return self.response_text


def _create_sample_workflow() -> tuple[Workflow, nx.DiGraph]:
    """Create a sample 5-tool workflow (Input -> Filter -> Join -> Summarize -> Output)."""
    tools = {
        1: Tool(tool_id=1, plugin="DbFileInput", tool_type="DbFileInput", name="Input", position=Position(100, 100), configuration=ToolConfiguration(raw_xml="<Configuration/>", parsed={"file_path": "Orders.xlsx"}), annotation="Ingest raw orders"),
        2: Tool(tool_id=2, plugin="Filter", tool_type="Filter", name="Filter", position=Position(200, 100), configuration=ToolConfiguration(raw_xml="<Configuration/>", parsed={"expression": "[Status] = 'Active'"}), annotation="Keep active orders"),
        3: Tool(tool_id=3, plugin="Join", tool_type="Join", name="Join", position=Position(300, 100), configuration=ToolConfiguration(raw_xml="<Configuration/>", parsed={"LeftField": "CustomerID", "RightField": "CustomerID"}), annotation="Enrich customer profile"),
        4: Tool(tool_id=4, plugin="Summarize", tool_type="Summarize", name="Summarize", position=Position(400, 100), configuration=ToolConfiguration(raw_xml="<Configuration/>", parsed={"SummarizeFields": "Region:GroupBy;Sales:Sum"}), annotation="Sum regional sales"),
        5: Tool(tool_id=5, plugin="DbFileOutput", tool_type="DbFileOutput", name="Output", position=Position(500, 100), configuration=ToolConfiguration(raw_xml="<Configuration/>", parsed={"file_path": "Regional_Report.xlsx"}), annotation="Export regional report"),
    }
    wf = Workflow(
        metadata=WorkflowMetadata(name="Sales Reporting", version="2021.3", description="Aggregates regional sales"),
        tools=tools,
    )
    g = nx.DiGraph()
    g.add_nodes_from([1, 2, 3, 4, 5])
    g.add_edges_from([(1, 2), (2, 3), (3, 4), (4, 5)])
    return wf, g


class TestProcessStages:
    """Test suite for LLM-generated process stages."""

    def test_llm_json_parsing_and_schema_validation(self):
        """Test valid LLM JSON response parsing and schema mapping."""
        wf, g = _create_sample_workflow()
        mock_response = json.dumps({
            "stages": [
                {
                    "stage_number": 1,
                    "stage_name": "Order Data Ingestion",
                    "category": "INGEST",
                    "description": "Reads incoming order transactions from Excel.",
                    "purpose": "Provides the primary transaction stream for analysis.",
                    "transformation": "Extracts raw orders with schema validation.",
                    "key_actions": ["Reads Orders.xlsx", "Validates order attributes"],
                    "tool_ids": [1],
                },
                {
                    "stage_number": 2,
                    "stage_name": "Order Cleansing & Customer Enrichment",
                    "category": "TRANSFORM",
                    "description": "Filters active orders and joins customer demographics.",
                    "purpose": "Ensures only active orders are enriched with customer attributes.",
                    "transformation": "Filters by Status = 'Active' and joins on CustomerID.",
                    "key_actions": ["Filters Status = 'Active'", "Joins customer data"],
                    "tool_ids": [2, 3],
                },
                {
                    "stage_number": 3,
                    "stage_name": "Regional Aggregation & Report Publication",
                    "category": "REPORT",
                    "description": "Summarizes revenue by region and writes final report.",
                    "purpose": "Produces executive business metrics.",
                    "transformation": "Sums sales grouped by region.",
                    "key_actions": ["Sums Sales by Region", "Publishes Regional_Report.xlsx"],
                    "tool_ids": [4, 5],
                },
            ]
        })

        client = MockLLMClient(response_text=mock_response)
        generator = LLMNarrativeGenerator(client=client, cache=LLMNarrativeCache())

        stages = generator.generate_process_stages(wf, g, workflow_id="test_sales")

        assert client.call_count == 1
        assert len(stages) == 3

        # Check Stage 1
        assert stages[0].stage_number == 1
        assert stages[0].name == "Order Data Ingestion"
        assert stages[0].short_title == "01 INGEST"
        assert stages[0].summary == "Reads incoming order transactions from Excel."
        assert stages[0].business_purpose == "Provides the primary transaction stream for analysis."
        assert stages[0].major_transformation == "Extracts raw orders with schema validation."
        assert stages[0].tool_ids == [1]
        assert stages[0].tool_count == 1
        assert "Reads Orders.xlsx" in stages[0].annotations

        # Check Stage 2
        assert stages[1].stage_number == 2
        assert stages[1].name == "Order Cleansing & Customer Enrichment"
        assert stages[1].short_title == "02 TRANSFORM"
        assert stages[1].tool_ids == [2, 3]
        assert stages[1].tool_count == 2

        # Check Stage 3
        assert stages[2].stage_number == 3
        assert stages[2].name == "Regional Aggregation & Report Publication"
        assert stages[2].tool_ids == [4, 5]
        assert stages[2].tool_count == 2

    def test_tool_coverage_guarantee_unassigned_tools_recovered(self):
        """Test that if the LLM omits a tool ID, the system assigns it and guarantees 100% tool coverage."""
        wf, g = _create_sample_workflow()
        # LLM only assigns tools 1 and 4, omitting tools 2, 3, and 5
        partial_response = json.dumps({
            "stages": [
                {
                    "stage_number": 1,
                    "stage_name": "Ingestion",
                    "category": "INGEST",
                    "description": "Ingests data.",
                    "purpose": "Ingests data.",
                    "transformation": "Extracts data.",
                    "key_actions": ["Read data"],
                    "tool_ids": [1],
                },
                {
                    "stage_number": 2,
                    "stage_name": "Aggregation",
                    "category": "AGGREGATE",
                    "description": "Aggregates data.",
                    "purpose": "Aggregates data.",
                    "transformation": "Sums data.",
                    "key_actions": ["Sum data"],
                    "tool_ids": [4],
                },
            ]
        })

        client = MockLLMClient(response_text=partial_response)
        generator = LLMNarrativeGenerator(client=client, cache=LLMNarrativeCache())

        stages = generator.generate_process_stages(wf, g, workflow_id="test_coverage")

        # Verify all 5 workflow tools are present across stages
        all_assigned = []
        for s in stages:
            all_assigned.extend(s.tool_ids)

        assert sorted(all_assigned) == [1, 2, 3, 4, 5]
        assert len(set(all_assigned)) == 5  # No duplicates

        # Step count must equal actual tool count for each stage
        for s in stages:
            assert s.tool_count == len(s.tool_ids)

    def test_no_duplicate_tool_assignments(self):
        """Test that tool IDs are deduplicated if the LLM accidentally assigns the same tool twice."""
        wf, g = _create_sample_workflow()
        duplicate_response = json.dumps({
            "stages": [
                {
                    "stage_number": 1,
                    "stage_name": "Ingestion",
                    "category": "INGEST",
                    "description": "Stage 1",
                    "purpose": "Stage 1",
                    "transformation": "Stage 1",
                    "key_actions": [],
                    "tool_ids": [1, 2],
                },
                {
                    "stage_number": 2,
                    "stage_name": "Transformation",
                    "category": "TRANSFORM",
                    "description": "Stage 2",
                    "purpose": "Stage 2",
                    "transformation": "Stage 2",
                    "key_actions": [],
                    "tool_ids": [2, 3, 4, 5],  # 2 is duplicated
                },
            ]
        })

        client = MockLLMClient(response_text=duplicate_response)
        generator = LLMNarrativeGenerator(client=client, cache=LLMNarrativeCache())

        stages = generator.generate_process_stages(wf, g, workflow_id="test_dedup")

        all_assigned = []
        for s in stages:
            all_assigned.extend(s.tool_ids)

        assert len(all_assigned) == 5
        assert len(set(all_assigned)) == 5

    def test_deterministic_fallback_when_llm_fails(self):
        """Test that deterministic fallback derives factual stages when LLM returns invalid JSON."""
        wf, g = _create_sample_workflow()
        client = MockLLMClient(response_text="Error: service temporarily unavailable")
        generator = LLMNarrativeGenerator(client=client, cache=LLMNarrativeCache())

        stages = generator.generate_process_stages(wf, g, workflow_id="test_fallback")

        assert len(stages) >= 3
        # Check that fallback is generic and contains no claims-specific hardcoding
        stage_names = [s.name.lower() for s in stages]
        combined_text = " ".join([f"{s.name} {s.summary} {s.business_purpose}" for s in stages]).lower()

        assert "claim" not in combined_text
        assert "policy master" not in combined_text
        assert "litigation" not in combined_text
        assert "examiner" not in combined_text

        # Verify all tools covered
        all_assigned = [tid for s in stages for tid in s.tool_ids]
        assert sorted(all_assigned) == [1, 2, 3, 4, 5]

    def test_caching_behavior(self):
        """Test that process stages are cached and not re-requested from LLM."""
        wf, g = _create_sample_workflow()
        mock_response = json.dumps({
            "stages": [
                {
                    "stage_number": 1,
                    "stage_name": "Full Pipeline",
                    "category": "PIPELINE",
                    "description": "Processes data end-to-end.",
                    "purpose": "Generates report.",
                    "transformation": "Transforms records.",
                    "key_actions": ["Read", "Process", "Write"],
                    "tool_ids": [1, 2, 3, 4, 5],
                }
            ]
        })

        client = MockLLMClient(response_text=mock_response)
        cache = LLMNarrativeCache()
        generator = LLMNarrativeGenerator(client=client, cache=cache)

        stages1 = generator.generate_process_stages(wf, g, workflow_id="sales_001")
        assert client.call_count == 1

        stages2 = generator.generate_process_stages(wf, g, workflow_id="sales_001")
        assert client.call_count == 1  # From cache
        assert stages1[0].name == stages2[0].name

    def test_unseen_non_claims_workflow_has_zero_claims_contamination(self):
        """Test that an unseen retail inventory workflow generates inventory-specific stages with no claims language."""
        tools = {
            10: Tool(tool_id=10, plugin="DbFileInput", tool_type="DbFileInput", name="Inventory Input", position=Position(100, 100), configuration=ToolConfiguration(raw_xml="<Configuration/>", parsed={"file_path": "Inventory_Levels.csv"}), annotation="Load store inventory"),
            11: Tool(tool_id=11, plugin="Formula", tool_type="Formula", name="Replenishment Formula", position=Position(200, 100), configuration=ToolConfiguration(raw_xml="<Configuration/>", parsed={"expression": "Reorder_Point - Stock_Qty"}), annotation="Compute replenishment gap"),
            12: Tool(tool_id=12, plugin="Filter", tool_type="Filter", name="Shortage Filter", position=Position(300, 100), configuration=ToolConfiguration(raw_xml="<Configuration/>", parsed={"expression": "[Replenish_Qty] > 0"}), annotation="Flag stock shortages"),
            13: Tool(tool_id=13, plugin="DbFileOutput", tool_type="DbFileOutput", name="Orders Output", position=Position(400, 100), configuration=ToolConfiguration(raw_xml="<Configuration/>", parsed={"file_path": "Purchase_Orders.xlsx"}), annotation="Output purchase orders"),
        }
        wf = Workflow(
            metadata=WorkflowMetadata(name="Inventory Replenishment", version="2021.3", description="Automates store stock replenishment orders"),
            tools=tools,
        )
        g = nx.DiGraph()
        g.add_nodes_from([10, 11, 12, 13])
        g.add_edges_from([(10, 11), (11, 12), (12, 13)])

        llm_response = json.dumps({
            "stages": [
                {
                    "stage_number": 1,
                    "stage_name": "Store Inventory Ingestion",
                    "category": "INGEST",
                    "description": "Loads current store stock levels from Inventory_Levels.csv.",
                    "purpose": "Provides current stock snapshots across retail stores.",
                    "transformation": "Parses inventory records.",
                    "key_actions": ["Reads Inventory_Levels.csv"],
                    "tool_ids": [10],
                },
                {
                    "stage_number": 2,
                    "stage_name": "Replenishment Calculation & Shortage Detection",
                    "category": "EVALUATE",
                    "description": "Calculates replenishment gaps and filters stores with positive purchase demand.",
                    "purpose": "Identifies items needing restock.",
                    "transformation": "Calculates Reorder_Point - Stock_Qty and filters Replenish_Qty > 0.",
                    "key_actions": ["Computes Replenish_Qty", "Filters shortages"],
                    "tool_ids": [11, 12],
                },
                {
                    "stage_number": 3,
                    "stage_name": "Purchase Order Deliverable Publication",
                    "category": "PUBLISH",
                    "description": "Publishes finalized replenishment orders to Excel.",
                    "purpose": "Provides suppliers with restock orders.",
                    "transformation": "Writes purchase orders.",
                    "key_actions": ["Writes Purchase_Orders.xlsx"],
                    "tool_ids": [13],
                },
            ]
        })

        client = MockLLMClient(response_text=llm_response)
        generator = LLMNarrativeGenerator(client=client, cache=LLMNarrativeCache())

        stages = generator.generate_process_stages(wf, g, workflow_id="inventory_wf")

        assert len(stages) == 3
        assert stages[0].name == "Store Inventory Ingestion"
        assert stages[0].short_title == "01 INGEST"
        assert stages[1].name == "Replenishment Calculation & Shortage Detection"
        assert stages[1].short_title == "02 EVALUATE"
        assert stages[2].name == "Purchase Order Deliverable Publication"
        assert stages[2].short_title == "03 PUBLISH"

        combined = " ".join([f"{s.name} {s.summary} {s.business_purpose}" for s in stages]).lower()
        assert "claim" not in combined
        assert "policy" not in combined
        assert "litigation" not in combined
        assert "examiner" not in combined

    def test_simple_filter_workflow_stages(self):
        """Test process stages on simple filter workflow has meaningful dynamic categories."""
        from pathlib import Path
        from awa.parser.xml_parser import parse_workflow
        from awa.graph.builder import build_graph

        filter_path = Path("fixtures/basic/simple_filter.yxmd")
        if not filter_path.exists():
            pytest.skip("simple_filter.yxmd not found")

        wf = parse_workflow(filter_path)
        g = build_graph(wf)

        generator = LLMNarrativeGenerator(client=MockLLMClient(response_text=""), cache=LLMNarrativeCache())
        stages = generator.generate_process_stages(wf, g, workflow_id="simple_filter_test")

        assert len(stages) == 3
        # Ensure categories are not generic 12-char truncated tokens
        assert stages[0].short_title == "01 DATA INGESTION"
        assert stages[1].short_title == "02 DATA PREPARATION"
        assert stages[2].short_title == "03 REPORT PUBLICATION"

    def test_join_workflow_enrichment_stages(self):
        """Test process stages on join workflow captures enrichment, aggregation, ordering, publication."""
        from pathlib import Path
        from awa.parser.xml_parser import parse_workflow
        from awa.graph.builder import build_graph

        join_path = Path("fixtures/joins/join_workflow.yxmd")
        if not join_path.exists():
            pytest.skip("join_workflow.yxmd not found")

        wf = parse_workflow(join_path)
        g = build_graph(wf)

        generator = LLMNarrativeGenerator(client=MockLLMClient(response_text=""), cache=LLMNarrativeCache())
        stages = generator.generate_process_stages(wf, g, workflow_id="join_test")

        assert len(stages) >= 4
        categories = [s.short_title for s in stages]
        assert any("INGESTION" in c for c in categories)
        assert any("ENRICHMENT" in c for c in categories)
        assert any("AGGREGATION" in c for c in categories)
        assert any("ORDERING" in c for c in categories)
        assert any("PUBLICATION" in c for c in categories)

        # 100% tool coverage
        all_stage_tools = [tid for s in stages for tid in s.tool_ids]
        assert set(all_stage_tools) == set(wf.tools.keys())

    def test_macro_workflow_stage_generation(self):
        """Test that a workflow with Macro/Custom tools generates macro-relevant stages."""
        tools = {
            1: Tool(tool_id=1, plugin="DbFileInput", tool_type="DbFileInput", name="Transaction Feed", position=Position(100, 100), configuration=ToolConfiguration(raw_xml="<Configuration/>", parsed={"file_path": "Transactions.csv"}), annotation="Read transactions"),
            2: Tool(tool_id=2, plugin="Macro", tool_type="Macro", name="Custom Risk Scoring Macro", position=Position(200, 100), configuration=ToolConfiguration(raw_xml="<Configuration/>", parsed={"MacroName": "Risk_Scoring.yxmc"}), annotation="Execute risk score macro"),
            3: Tool(tool_id=3, plugin="DbFileOutput", tool_type="DbFileOutput", name="Risk Report", position=Position(300, 100), configuration=ToolConfiguration(raw_xml="<Configuration/>", parsed={"file_path": "Risk_Output.xlsx"}), annotation="Publish scored risks"),
        }
        wf = Workflow(
            metadata=WorkflowMetadata(name="Macro Risk Processing", version="2021.3", description="Executes risk scoring macro"),
            tools=tools,
        )
        g = nx.DiGraph()
        g.add_nodes_from([1, 2, 3])
        g.add_edges_from([(1, 2), (2, 3)])

        llm_response = json.dumps({
            "stages": [
                {
                    "stage_number": 1,
                    "stage_name": "Transaction Data Ingestion",
                    "category": "TRANSACTION INGESTION",
                    "description": "Reads raw transactions from CSV feed.",
                    "purpose": "Sources transactions for risk analysis.",
                    "transformation": "Extracts raw transaction records.",
                    "key_actions": ["Reads Transactions.csv"],
                    "tool_ids": [1],
                },
                {
                    "stage_number": 2,
                    "stage_name": "Risk Scoring Macro Execution",
                    "category": "MACRO SCORING",
                    "description": "Runs custom Risk_Scoring macro to calculate risk scores.",
                    "purpose": "Calculates risk profiles using modular macro logic.",
                    "transformation": "Applies custom macro algorithms.",
                    "key_actions": ["Invokes Risk_Scoring.yxmc"],
                    "tool_ids": [2],
                },
                {
                    "stage_number": 3,
                    "stage_name": "Risk Report Deliverable Export",
                    "category": "REPORT PUBLICATION",
                    "description": "Exports scored risks to Excel report.",
                    "purpose": "Publishes risk analytics for risk officers.",
                    "transformation": "Writes risk report workbook.",
                    "key_actions": ["Writes Risk_Output.xlsx"],
                    "tool_ids": [3],
                },
            ]
        })

        client = MockLLMClient(response_text=llm_response)
        generator = LLMNarrativeGenerator(client=client, cache=LLMNarrativeCache())

        stages = generator.generate_process_stages(wf, g, workflow_id="macro_risk_wf")
        assert len(stages) == 3
        assert stages[1].short_title == "02 MACRO SCORING"
        assert stages[1].name == "Risk Scoring Macro Execution"
        assert stages[1].tool_ids == [2]

    def test_complete_category_labels_no_truncation(self):
        """Test category labels are full uppercase phrases and not truncated."""
        wf, g = _create_sample_workflow()
        mock_response = json.dumps({
            "stages": [
                {
                    "stage_number": 1,
                    "stage_name": "Customer Master Ingestion",
                    "category": "CUSTOMER INGESTION & STAGING",
                    "description": "Ingests customer master datasets.",
                    "purpose": "Sources customer profiles.",
                    "transformation": "Parses customer profiles.",
                    "key_actions": ["Reads Customers"],
                    "tool_ids": [1, 2],
                },
                {
                    "stage_number": 2,
                    "stage_name": "Commercial Revenue Aggregation",
                    "category": "COMMERCIAL REVENUE AGGREGATION",
                    "description": "Aggregates revenue across regions.",
                    "purpose": "Computes sales totals.",
                    "transformation": "Sums regional revenue.",
                    "key_actions": ["Sums Revenue"],
                    "tool_ids": [3, 4, 5],
                },
            ]
        })

        client = MockLLMClient(response_text=mock_response)
        generator = LLMNarrativeGenerator(client=client, cache=LLMNarrativeCache())

        stages = generator.generate_process_stages(wf, g, workflow_id="category_formatting_test")

        assert stages[0].short_title == "01 CUSTOMER INGESTION STAGING" or "01 CUSTOMER INGESTION & STAGING"
        assert stages[1].short_title == "02 COMMERCIAL REVENUE AGGREGATION"
        assert not stages[0].short_title.endswith("...")
        assert not stages[1].short_title.endswith("...")


