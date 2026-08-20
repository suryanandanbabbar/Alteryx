"""Tests for recursive node discovery, nested ToolContainer hierarchies, and node classification."""

import tempfile
from pathlib import Path
import pytest

from awa.parser.xml_parser import parse_workflow
from awa.analysis.workflow_analyzer import analyze_canonical, analyze_workflow
from backend.app.services.analyzer import to_overview_dto, to_diagram_dto


class TestNestedContainersAndNodeDiscovery:
    """Validate recursive traversal, container hierarchy preservation, and node classification."""

    def test_reconstructed_demo_claims_workflow_counts(self):
        """Verify the exact node, container, annotation, and connection counts on Demo_Claims workflow."""
        wf_path = Path("Demo_Claims_Volume_Extract_reconstructed.yxmd")
        assert wf_path.exists(), "Demo_Claims_Volume_Extract_reconstructed.yxmd fixture must exist"

        workflow = parse_workflow(wf_path)

        # 1. Executable tools must equal 39 (NOT 2)
        assert len(workflow.tools) == 39, f"Expected 39 executable tools, got {len(workflow.tools)}"

        # 2. Containers must equal 8
        assert len(workflow.containers) == 8, f"Expected 8 ToolContainers, got {len(workflow.containers)}"

        # 3. TextBoxes must equal 2
        assert len(workflow.textboxes) == 2, f"Expected 2 TextBoxes, got {len(workflow.textboxes)}"

        # 4. Total connections must equal 41
        assert len(workflow.connections) == 41, f"Expected 41 connections, got {len(workflow.connections)}"

        # 5. TextBoxes and Containers must NOT be in tools
        assert 200 not in workflow.tools  # TextBox #200
        assert 350 not in workflow.tools  # TextBox #350
        assert 210 not in workflow.tools  # ToolContainer #210
        assert 220 not in workflow.tools  # ToolContainer #220

        # 6. Check container child tracking
        assert len(workflow.containers[210].child_tool_ids) == 2
        assert workflow.containers[210].caption == "Extract Claims Data"
        assert workflow.tools[1].container_name == "Extract Claims Data"
        assert workflow.tools[1].container_id == 210

        # 7. Validate connection endpoint resolution
        for conn in workflow.connections:
            assert conn.origin_tool_id in workflow.tools, f"Connection origin {conn.origin_tool_id} not in tools"
            assert conn.destination_tool_id in workflow.tools, f"Connection destination {conn.destination_tool_id} not in tools"

    def test_canonical_analysis_pipeline_on_nested_workflow(self):
        """Verify the full analysis pipeline on the nested ToolContainer workflow."""
        canonical = analyze_canonical("Demo_Claims_Volume_Extract_reconstructed.yxmd")

        # Check metrics
        assert canonical.metrics.total_nodes == 39
        assert canonical.metrics.total_connections == 41
        assert canonical.metrics.container_count == 8
        assert canonical.metrics.annotation_count == 2
        assert canonical.metrics.input_count == 4
        assert canonical.metrics.output_count == 7

        # Check execution order length and step numbering independence
        assert len(canonical.execution_order) == 39
        # Execution order is topological: 1, 101, 102, 103, ...
        assert canonical.execution_order[0] == 1

        # Check DAG layout
        assert len(canonical.dag_layout.nodes) == 39
        assert len(canonical.dag_layout.edges) == 41

        # Check DTO conversions
        overview_dto = to_overview_dto(canonical)
        assert overview_dto.metrics.total_nodes == 39
        assert overview_dto.metrics.total_connections == 41
        assert len(overview_dto.execution_order) == 39

        # Ensure execution step numbers are 1..39 sequential
        for idx, step in enumerate(overview_dto.execution_order, start=1):
            assert step.step_number == idx
            assert step.tool_id != 0
            assert step.summary != ""

        diagram_dto = to_diagram_dto(canonical)
        assert len(diagram_dto.nodes) == 39
        assert all(n.container_name is not None for n in diagram_dto.nodes)

    def test_synthetic_deeply_nested_containers(self, tmp_path: Path):
        """Test top-level, single-nested, and doubly-nested tool containers."""
        xml_content = """<?xml version="1.0"?>
<AlteryxDocument yxmdVer="2024.1">
  <Nodes>
    <!-- Top-level tool -->
    <Node ToolID="1">
      <GuiSettings Plugin="AlteryxBasePluginsGui.DbFileInput.DbFileInput"><Position x="50" y="50" /></GuiSettings>
      <Properties><Configuration><File>input.csv</File></Configuration></Properties>
    </Node>
    <!-- Top-level TextBox -->
    <Node ToolID="99">
      <GuiSettings Plugin="AlteryxGuiToolkit.TextBox.TextBox"><Position x="10" y="10" /></GuiSettings>
      <Properties><Configuration><Text>Notes</Text></Configuration></Properties>
    </Node>
    <!-- Outer Container -->
    <Node ToolID="100">
      <GuiSettings Plugin="AlteryxGuiToolkit.ToolContainer.ToolContainer"><Position x="100" y="100" /></GuiSettings>
      <Properties>
        <Configuration><Caption>Outer Container</Caption><Disabled value="False" /></Configuration>
        <ChildNodes>
          <!-- Tool in Outer Container -->
          <Node ToolID="2">
            <GuiSettings Plugin="AlteryxBasePluginsGui.Filter.Filter"><Position x="150" y="150" /></GuiSettings>
            <Properties><Configuration><Expression>[ID] &gt; 10</Expression></Configuration></Properties>
          </Node>
          <!-- Inner Container -->
          <Node ToolID="200">
            <GuiSettings Plugin="AlteryxGuiToolkit.ToolContainer.ToolContainer"><Position x="200" y="200" /></GuiSettings>
            <Properties>
              <Configuration><Caption>Inner Container</Caption><Disabled value="False" /></Configuration>
              <ChildNodes>
                <!-- Tool in Inner Container -->
                <Node ToolID="3">
                  <GuiSettings Plugin="AlteryxBasePluginsGui.DbFileOutput.DbFileOutput"><Position x="250" y="250" /></GuiSettings>
                  <Properties><Configuration><File>output.yxdb</File></Configuration></Properties>
                </Node>
              </ChildNodes>
            </Properties>
          </Node>
        </ChildNodes>
      </Properties>
    </Node>
  </Nodes>
  <Connections>
    <Connection>
      <Origin ToolID="1" Connection="Output" />
      <Destination ToolID="2" Connection="Input" />
    </Connection>
    <Connection>
      <Origin ToolID="2" Connection="True" />
      <Destination ToolID="3" Connection="Input" />
    </Connection>
  </Connections>
</AlteryxDocument>
"""
        wf_file = tmp_path / "deeply_nested.yxmd"
        wf_file.write_text(xml_content, encoding="utf-8")

        wf = parse_workflow(wf_file)
        assert len(wf.tools) == 3
        assert sorted(wf.tools.keys()) == [1, 2, 3]
        assert len(wf.containers) == 2
        assert len(wf.textboxes) == 1

        assert wf.tools[1].container_id is None
        assert wf.tools[2].container_id == 100
        assert wf.tools[2].container_name == "Outer Container"
        assert wf.tools[3].container_id == 200
        assert wf.tools[3].container_name == "Inner Container"

        assert len(wf.connections) == 2

    def test_disabled_container_skips_children(self, tmp_path: Path):
        """Test that tools inside a disabled container are excluded from active analysis."""
        xml_content = """<?xml version="1.0"?>
<AlteryxDocument yxmdVer="2024.1">
  <Nodes>
    <Node ToolID="1">
      <GuiSettings Plugin="AlteryxBasePluginsGui.DbFileInput.DbFileInput"><Position x="50" y="50" /></GuiSettings>
      <Properties><Configuration><File>active.csv</File></Configuration></Properties>
    </Node>
    <Node ToolID="100">
      <GuiSettings Plugin="AlteryxGuiToolkit.ToolContainer.ToolContainer"><Position x="100" y="100" /></GuiSettings>
      <Properties>
        <Configuration><Caption>Disabled Archive</Caption><Disabled value="True" /></Configuration>
        <ChildNodes>
          <Node ToolID="2">
            <GuiSettings Plugin="AlteryxBasePluginsGui.DbFileInput.DbFileInput"><Position x="150" y="150" /></GuiSettings>
            <Properties><Configuration><File>disabled.csv</File></Configuration></Properties>
          </Node>
        </ChildNodes>
      </Properties>
    </Node>
  </Nodes>
  <Connections />
</AlteryxDocument>
"""
        wf_file = tmp_path / "disabled_container.yxmd"
        wf_file.write_text(xml_content, encoding="utf-8")

        wf = parse_workflow(wf_file)
        assert len(wf.tools) == 1
        assert 1 in wf.tools
        assert 2 not in wf.tools
