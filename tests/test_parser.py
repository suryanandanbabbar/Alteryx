"""Parser tests — validates XML parsing against real .yxmd fixtures.

Tests use ONLY real fixtures from the reference repository (C1).
Assertions check actual extracted data, not just 'is not None' (§32).
"""

import pytest
from pathlib import Path

from backend.src.awa.parser.xml_parser import parse_workflow
from backend.src.awa.model.workflow import Workflow
from backend.src.awa.model.connection import Connection


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestSimpleFilterWorkflow:
    """Tests against fixtures/basic/simple_filter.yxmd.

    This fixture contains:
    - Tool 1: DbFileInput (customers.xlsx)
    - Tool 2: Filter ([status] = "active" AND [revenue] > 100)
    - Tool 3: DbFileOutput (active_customers.xlsx)
    - 2 connections: 1→2 (Output→Input), 2→3 (True→Input)
    """

    @pytest.fixture
    def workflow(self) -> Workflow:
        path = FIXTURES_DIR / "basic" / "simple_filter.yxmd"
        assert path.exists(), f"Fixture not found: {path}"
        return parse_workflow(path)

    def test_metadata(self, workflow: Workflow):
        assert workflow.metadata.name == "simple_filter"
        assert workflow.metadata.version == "2024.1"

    def test_tool_count(self, workflow: Workflow):
        assert len(workflow.tools) == 3

    def test_tool_ids(self, workflow: Workflow):
        assert set(workflow.tools.keys()) == {1, 2, 3}

    def test_input_tool(self, workflow: Workflow):
        tool = workflow.tools[1]
        assert tool.tool_type == "DbFileInput"
        assert tool.name == "Input Customers"
        assert tool.position is not None
        assert tool.position.x == 78
        assert tool.position.y == 78
        assert "customers.xlsx" in tool.configuration.parsed.get("file_path", "")

    def test_filter_tool(self, workflow: Workflow):
        tool = workflow.tools[2]
        assert tool.tool_type == "Filter"
        assert tool.name == "Filter Active High Rev"
        assert tool.position is not None
        assert tool.position.x == 258
        # The expression contains XML-decoded entities
        expr = tool.configuration.parsed.get("expression", "")
        assert "[status]" in expr
        assert "[revenue]" in expr

    def test_output_tool(self, workflow: Workflow):
        tool = workflow.tools[3]
        assert tool.tool_type == "DbFileOutput"
        assert tool.name == "Output Active Customers"
        assert "active_customers.xlsx" in tool.configuration.parsed.get("file_path", "")

    def test_connections(self, workflow: Workflow):
        assert len(workflow.connections) == 2

        conn1 = workflow.connections[0]
        assert conn1.origin_tool_id == 1
        assert conn1.origin_anchor == "Output"
        assert conn1.destination_tool_id == 2
        assert conn1.destination_anchor == "Input"

        conn2 = workflow.connections[1]
        assert conn2.origin_tool_id == 2
        assert conn2.origin_anchor == "True"
        assert conn2.destination_tool_id == 3
        assert conn2.destination_anchor == "Input"

    def test_output_fields(self, workflow: Workflow):
        """Verify output field schema is extracted from MetaInfo/RecordInfo."""
        tool = workflow.tools[1]  # Input tool has output fields
        assert len(tool.output_fields) == 4
        field_names = [f.name for f in tool.output_fields]
        assert "customer_id" in field_names
        assert "name" in field_names
        assert "status" in field_names
        assert "revenue" in field_names

        # Check types
        revenue_field = next(f for f in tool.output_fields if f.name == "revenue")
        assert revenue_field.type == "Double"

    def test_raw_xml_preserved(self, workflow: Workflow):
        """Verify raw XML is preserved in ToolConfiguration."""
        for tool in workflow.tools.values():
            assert tool.configuration.raw_xml != ""
            assert "<" in tool.configuration.raw_xml  # It's XML


class TestJoinWorkflow:
    """Tests against fixtures/joins/join_workflow.yxmd.

    This fixture contains:
    - Tool 1: DbFileInput (customers.xlsx)
    - Tool 2: DbFileInput (orders.csv)
    - Tool 3: Join (on customer_id)
    - Tool 4: Summarize (GroupBy customer_id, Sum amount)
    - Tool 5: Sort (by total_amount Descending)
    - Tool 6: DbFileOutput (customer_totals.xlsx)
    """

    @pytest.fixture
    def workflow(self) -> Workflow:
        path = FIXTURES_DIR / "joins" / "join_workflow.yxmd"
        assert path.exists(), f"Fixture not found: {path}"
        return parse_workflow(path)

    def test_tool_count(self, workflow: Workflow):
        assert len(workflow.tools) == 6

    def test_tool_types(self, workflow: Workflow):
        types = {tid: t.tool_type for tid, t in workflow.tools.items()}
        assert types[1] == "DbFileInput"
        assert types[2] == "DbFileInput"
        assert types[3] == "Join"
        assert types[4] == "Summarize"
        assert types[5] == "Sort"
        assert types[6] == "DbFileOutput"

    def test_join_config(self, workflow: Workflow):
        """Verify join key extraction."""
        tool = workflow.tools[3]
        join_fields = tool.configuration.parsed.get("join_fields", [])
        assert len(join_fields) >= 1
        assert join_fields[0]["left"] == "customer_id"
        assert join_fields[0]["right"] == "customer_id"

    def test_summarize_config(self, workflow: Workflow):
        """Verify summarize field extraction."""
        tool = workflow.tools[4]
        fields = tool.configuration.parsed.get("summarize_fields", [])
        assert len(fields) == 3

        group_by = [f for f in fields if f["action"] == "GroupBy"]
        assert len(group_by) >= 1
        assert group_by[0]["field"] == "customer_id"

        sum_fields = [f for f in fields if f["action"] == "Sum"]
        assert len(sum_fields) >= 1
        assert sum_fields[0]["field"] == "amount"
        assert sum_fields[0]["rename"] == "total_amount"

    def test_sort_config(self, workflow: Workflow):
        """Verify sort field extraction."""
        tool = workflow.tools[5]
        fields = tool.configuration.parsed.get("sort_fields", [])
        assert len(fields) == 1
        assert fields[0]["field"] == "total_amount"
        assert fields[0]["order"] == "Descending"

    def test_connections(self, workflow: Workflow):
        """Verify all 5 connections are parsed."""
        assert len(workflow.connections) == 5

        # Verify Join receives Left and Right inputs
        join_inputs = [
            c for c in workflow.connections
            if c.destination_tool_id == 3
        ]
        assert len(join_inputs) == 2
        anchors = {c.destination_anchor for c in join_inputs}
        assert "Left" in anchors
        assert "Right" in anchors

    def test_join_output_anchor(self, workflow: Workflow):
        """Verify the Join output anchor is 'Join'."""
        join_outputs = [
            c for c in workflow.connections
            if c.origin_tool_id == 3
        ]
        assert len(join_outputs) == 1
        assert join_outputs[0].origin_anchor == "Join"


class TestParserErrors:
    """Test error handling in the parser."""

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            parse_workflow("/nonexistent/path.yxmd")
