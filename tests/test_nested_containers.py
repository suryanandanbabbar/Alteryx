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
        assert canonical.metrics.terminal_node_count == 7
        assert canonical.metrics.business_output_count == 5
        assert canonical.metrics.business_output_node_ids == [17, 18, 132, 142, 152]

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

        # Check DiagramDTO and exact source <Node> extraction
        diag_dto = to_diagram_dto(canonical)
        assert len(diag_dto.nodes) == 39
        node_map = {n.tool_id: n for n in diag_dto.nodes}

        # Tool 1: nested in Container #210
        assert 1 in node_map
        t1 = node_map[1]
        assert t1.container_id == 210
        assert t1.plugin == "AlteryxBasePluginsGui.DbFileInput.DbFileInput"
        assert t1.xml_tool_name == "AlteryxBasePluginsGui.DbFileInput.DbFileInput"
        assert t1.raw_node_xml.startswith('<Node ToolID="1">')
        assert t1.raw_node_xml.endswith("</Node>")
        assert "Claims_Volume_Extract_Demo.xlsx" in t1.raw_node_xml

        # Tool 2: child in Container #210
        assert 2 in node_map
        t2 = node_map[2]
        assert t2.container_id == 210
        assert t2.raw_node_xml.startswith('<Node ToolID="2">')
        assert t2.raw_node_xml.endswith("</Node>")

        # Tool 3 & 4: child in Container #220
        assert 3 in node_map and 4 in node_map
        t3 = node_map[3]
        t4 = node_map[4]
        assert t3.container_id == 220
        assert t4.container_id == 220
        assert t3.raw_node_xml.startswith('<Node ToolID="3">')
        assert t4.raw_node_xml.startswith('<Node ToolID="4">')

        # Tool 114: deep tool in Container #310
        assert 114 in node_map
        t114 = node_map[114]
        assert t114.container_id == 310
        assert t114.plugin == "AlteryxBasePluginsGui.Formula.Formula"
        assert t114.xml_tool_name == "AlteryxBasePluginsGui.Formula.Formula"
        assert t114.raw_node_xml.startswith('<Node ToolID="114">')
        assert "FormulaFields" in t114.raw_node_xml
        assert t114.raw_node_xml.endswith("</Node>")

        # Tool 16 & 17: children in Container #230
        assert 16 in node_map and 17 in node_map
        t16 = node_map[16]
        t17 = node_map[17]
        assert t16.container_id == 230
        assert t16.plugin == "AlteryxBasePluginsGui.Sort.Sort"
        assert t16.xml_tool_name == "AlteryxBasePluginsGui.Sort.Sort"
        assert t16.raw_node_xml.startswith('<Node ToolID="16">')
        assert "Quarter End Date Descending" in t16.raw_node_xml
        assert t16.raw_node_xml.endswith("</Node>")

        assert t17.container_id == 230
        assert t17.plugin == "AlteryxBasePluginsGui.DbFileOutput.DbFileOutput"
        assert t17.xml_tool_name == "AlteryxBasePluginsGui.DbFileOutput.DbFileOutput"
        assert t17.raw_node_xml.startswith('<Node ToolID="17">')
        assert t17.raw_node_xml.endswith("</Node>")

        # Ensure execution step numbers are 1..39 sequential
        for idx, step in enumerate(overview_dto.execution_order, start=1):
            assert step.step_number == idx
            assert step.tool_id != 0
            assert step.summary != ""

    def test_exact_source_substring_integrity_on_demo_workflow(self):
        """Regression test verifying that extracted Node snippets are exact substrings of the raw uploaded .yxmd."""
        wf_path = Path("Demo_Claims_Volume_Extract_reconstructed.yxmd")
        assert wf_path.exists()
        raw_source = wf_path.read_text(encoding="utf-8")

        canonical = analyze_canonical(wf_path)
        diag = to_diagram_dto(canonical)
        nodes = {n.tool_id: n for n in diag.nodes}

        # Tool 1: DbFileInput in Container 210
        assert 1 in nodes
        n1 = nodes[1]
        assert n1.container_id == 210
        assert n1.xml_tool_name == "AlteryxBasePluginsGui.DbFileInput.DbFileInput"
        assert n1.raw_node_xml in raw_source
        assert 'ToolID="1"' in n1.raw_node_xml
        assert 'AlteryxBasePluginsGui.DbFileInput.DbFileInput' in n1.raw_node_xml
        assert 'Claims_Volume_Extract_Demo.xlsx' in n1.raw_node_xml
        assert 'AlteryxDbFileInput' in n1.raw_node_xml

        # Tool 16: Sort in Container 230
        assert 16 in nodes
        n16 = nodes[16]
        assert n16.container_id == 230
        assert n16.xml_tool_name == "AlteryxBasePluginsGui.Sort.Sort"
        assert n16.raw_node_xml in raw_source
        assert 'ToolID="16"' in n16.raw_node_xml
        assert 'AlteryxBasePluginsGui.Sort.Sort' in n16.raw_node_xml
        assert 'Quarter End Date Descending' in n16.raw_node_xml
        assert 'AlteryxSort' in n16.raw_node_xml

        # Tool 17: DbFileOutput in Container 230
        assert 17 in nodes
        n17 = nodes[17]
        assert n17.container_id == 230
        assert n17.xml_tool_name == "AlteryxBasePluginsGui.DbFileOutput.DbFileOutput"
        assert n17.raw_node_xml in raw_source
        assert 'ToolID="17"' in n17.raw_node_xml
        assert 'Claims_Historical_Extract_Demo_Output.xlsx' in n17.raw_node_xml

        # Tool 114: Formula in Container 310
        assert 114 in nodes
        n114 = nodes[114]
        assert n114.container_id == 310
        assert n114.xml_tool_name == "AlteryxBasePluginsGui.Formula.Formula"
        assert n114.raw_node_xml in raw_source
        assert 'ToolID="114"' in n114.raw_node_xml
        assert 'Total Paid=if isnull' in n114.raw_node_xml

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

    def test_source_node_extraction_root_level(self, tmp_path: Path):
        """Test 1: Root-level Node exact source substring extraction."""
        xml_content = """<?xml version="1.0"?>
<AlteryxDocument yxmdVer="2024.1">
  <Nodes>
    <Node ToolID="42">
      <GuiSettings Plugin="AlteryxBasePluginsGui.Sort.Sort">
        <Position x="100" y="200" />
      </GuiSettings>
      <Properties>
        <Configuration>
          <SortInfo>Revenue Descending</SortInfo>
        </Configuration>
        <Annotation DisplayMode="0">
          <Name>Custom Sort Tool</Name>
          <DefaultAnnotationText>Sort by Revenue</DefaultAnnotationText>
        </Annotation>
      </Properties>
      <EngineSettings EngineDll="AlteryxBasePluginsEngine.dll" EngineDllEntryPoint="AlteryxSort" />
    </Node>
  </Nodes>
  <Connections />
</AlteryxDocument>
"""
        wf_file = tmp_path / "root_tool.yxmd"
        wf_file.write_text(xml_content, encoding="utf-8")

        wf = parse_workflow(wf_file)
        assert 42 in wf.tools
        tool = wf.tools[42]
        assert tool.container_id is None
        assert tool.raw_node_xml.startswith('<Node ToolID="42">')
        assert tool.raw_node_xml.endswith("</Node>")
        assert "<SortInfo>Revenue Descending</SortInfo>" in tool.raw_node_xml
        assert "<Name>Custom Sort Tool</Name>" in tool.raw_node_xml

    def test_source_node_extraction_child_nodes_and_deep_nesting(self, tmp_path: Path):
        """Test 2, 3, 5: ChildNodes, deeper nested ChildNodes, and container ancestry."""
        xml_content = """<?xml version="1.0"?>
<AlteryxDocument yxmdVer="2024.1">
  <Nodes>
    <Node ToolID="200">
      <GuiSettings Plugin="AlteryxGuiToolkit.ToolContainer.ToolContainer">
        <Position x="50" y="50" />
      </GuiSettings>
      <Properties>
        <Configuration><Caption>Level 1 Container</Caption></Configuration>
        <ChildNodes>
          <Node ToolID="16">
            <GuiSettings Plugin="AlteryxBasePluginsGui.Sort.Sort"><Position x="75" y="75" /></GuiSettings>
            <Properties><Configuration><SortInfo>ID Ascending</SortInfo></Configuration></Properties>
            <EngineSettings EngineDll="AlteryxBasePluginsEngine.dll" EngineDllEntryPoint="AlteryxSort" />
          </Node>
          <Node ToolID="300">
            <GuiSettings Plugin="AlteryxGuiToolkit.ToolContainer.ToolContainer"><Position x="120" y="120" /></GuiSettings>
            <Properties>
              <Configuration><Caption>Level 2 Container</Caption></Configuration>
              <ChildNodes>
                <Node ToolID="99">
                  <GuiSettings Plugin="AlteryxBasePluginsGui.Formula.Formula"><Position x="150" y="150" /></GuiSettings>
                  <Properties><Configuration><FormulaFields><FormulaField field="X" expression="1+1" /></FormulaFields></Configuration></Properties>
                  <EngineSettings EngineDll="AlteryxBasePluginsEngine.dll" EngineDllEntryPoint="AlteryxFormula" />
                </Node>
              </ChildNodes>
            </Properties>
          </Node>
        </ChildNodes>
      </Properties>
    </Node>
  </Nodes>
  <Connections />
</AlteryxDocument>
"""
        wf_file = tmp_path / "nested_hierarchy.yxmd"
        wf_file.write_text(xml_content, encoding="utf-8")

        wf = parse_workflow(wf_file)
        assert 16 in wf.tools
        assert 99 in wf.tools

        # Tool 16 has parent container 200
        assert wf.tools[16].container_id == 200
        assert wf.tools[16].container_name == "Level 1 Container"
        assert wf.tools[16].raw_node_xml.startswith('<Node ToolID="16">')
        assert wf.tools[16].raw_node_xml.endswith("</Node>")
        assert "<SortInfo>ID Ascending</SortInfo>" in wf.tools[16].raw_node_xml

        # Tool 99 has parent container 300
        assert wf.tools[99].container_id == 300
        assert wf.tools[99].container_name == "Level 2 Container"
        assert wf.tools[99].raw_node_xml.startswith('<Node ToolID="99">')
        assert wf.tools[99].raw_node_xml.endswith("</Node>")
        assert 'expression="1+1"' in wf.tools[99].raw_node_xml

    def test_exact_source_preservation_and_nonexistent_fallback(self, tmp_path: Path):
        """Test 4 & 6: Preserves exact formatting/attributes; missing nodes handled safely."""
        from awa.parser.xml_parser import _extract_node_xml_snippet
        raw_xml = '<AlteryxDocument><Nodes><Node ToolID="123" CustomAttr="PreserveMe"   >\n  <GuiSettings Plugin="Custom.Plugin" />\n  <Properties><Configuration /></Properties>\n</Node></Nodes></AlteryxDocument>'
        
        # Exact snippet preservation
        extracted = _extract_node_xml_snippet(raw_xml, 123)
        assert extracted == '<Node ToolID="123" CustomAttr="PreserveMe"   >\n  <GuiSettings Plugin="Custom.Plugin" />\n  <Properties><Configuration /></Properties>\n</Node>'
        assert 'CustomAttr="PreserveMe"' in extracted
        
        # Missing tool ID returns empty string
        missing = _extract_node_xml_snippet(raw_xml, 999)
        assert missing == ""
