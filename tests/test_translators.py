"""Tests for individual tool translators."""

import pandas as pd
import pytest

from awa.model.tool import Tool, ToolConfiguration
from awa.model.workflow import Workflow, WorkflowMetadata
from awa.model.diagnostic import SupportLevel
from awa.translators.registry import get_translator
import awa.translators  # noqa: F401


@pytest.fixture
def empty_workflow():
    return Workflow(
        metadata=WorkflowMetadata(name="test", version="2024.1"),
        tools={},
        connections=[],
    )


class TestTranslators:
    """Test unit code generation for each core ETL tool translator."""

    def test_join_translator(self, empty_workflow):
        tool = Tool(
            tool_id=10,
            plugin="AlteryxBasePluginsGui.Join.Join",
            tool_type="Join",
            name="Join Data",
            position=None,
            configuration=ToolConfiguration(
                raw_xml="",
                parsed={"join_fields": [{"left": "id", "right": "id"}]}
            ),
        )
        translator = get_translator(tool)
        res = translator.translate(tool, ["df_left", "df_right"], empty_workflow)
        assert res.support_level == SupportLevel.SUPPORTED
        assert "Join" in res.output_map
        assert "Left" in res.output_map
        assert "Right" in res.output_map
        assert "pd.merge(df_left, df_right" in res.python_code

    def test_union_translator(self, empty_workflow):
        tool = Tool(
            tool_id=11,
            plugin="AlteryxBasePluginsGui.Union.Union",
            tool_type="Union",
            name="Union Streams",
            position=None,
            configuration=ToolConfiguration(raw_xml="", parsed={"by_name_or_pos": "ByName"}),
        )
        translator = get_translator(tool)
        res = translator.translate(tool, ["df_1", "df_2"], empty_workflow)
        assert "pd.concat([df_1, df_2]" in res.python_code

    def test_summarize_translator(self, empty_workflow):
        tool = Tool(
            tool_id=12,
            plugin="AlteryxBasePluginsGui.Summarize.Summarize",
            tool_type="Summarize",
            name="Sum Amounts",
            position=None,
            configuration=ToolConfiguration(
                raw_xml="",
                parsed={
                    "summarize_fields": [
                        {"field": "region", "action": "GroupBy", "rename": "region"},
                        {"field": "sales", "action": "Sum", "rename": "total_sales"},
                    ]
                }
            ),
        )
        translator = get_translator(tool)
        res = translator.translate(tool, ["df_input"], empty_workflow)
        assert "groupby(['region'], as_index=False)" in res.python_code
        assert "'total_sales': ('sales', 'sum')" in res.python_code

    def test_sort_translator(self, empty_workflow):
        tool = Tool(
            tool_id=13,
            plugin="AlteryxBasePluginsGui.Sort.Sort",
            tool_type="Sort",
            name="Sort Results",
            position=None,
            configuration=ToolConfiguration(
                raw_xml="",
                parsed={
                    "sort_fields": [{"field": "total_sales", "order": "Descending"}]
                }
            ),
        )
        translator = get_translator(tool)
        res = translator.translate(tool, ["df_input"], empty_workflow)
        assert "sort_values(by='total_sales', ascending=False)" in res.python_code

    def test_unique_translator(self, empty_workflow):
        tool = Tool(
            tool_id=14,
            plugin="AlteryxBasePluginsGui.Unique.Unique",
            tool_type="Unique",
            name="Deduplicate",
            position=None,
            configuration=ToolConfiguration(
                raw_xml="",
                parsed={"unique_fields": ["email"]}
            ),
        )
        translator = get_translator(tool)
        res = translator.translate(tool, ["df_input"], empty_workflow)
        assert "Unique" in res.output_map
        assert "Duplicates" in res.output_map
        assert "duplicated(subset=['email'], keep='first')" in res.python_code

    def test_data_cleansing_translator(self, empty_workflow):
        tool = Tool(
            tool_id=15,
            plugin="AlteryxBasePluginsGui.DataCleansing.DataCleansing",
            tool_type="DataCleansing",
            name="Cleanse",
            position=None,
            configuration=ToolConfiguration(
                raw_xml="",
                parsed={"cleansing_fields": ["name"], "trimwhitespace": True, "modify_case": "upper"}
            ),
        )
        translator = get_translator(tool)
        res = translator.translate(tool, ["df_input"], empty_workflow)
        assert ".str.strip()" in res.python_code
        assert ".str.upper()" in res.python_code

    def test_record_id_translator(self, empty_workflow):
        tool = Tool(
            tool_id=16,
            plugin="AlteryxBasePluginsGui.RecordID.RecordID",
            tool_type="RecordID",
            name="Add ID",
            position=None,
            configuration=ToolConfiguration(
                raw_xml="",
                parsed={"field_name": "RowID", "start_value": 1}
            ),
        )
        translator = get_translator(tool)
        res = translator.translate(tool, ["df_input"], empty_workflow)
        assert "insert(0, 'RowID'" in res.python_code

    def test_transpose_translator(self, empty_workflow):
        tool = Tool(
            tool_id=17,
            plugin="AlteryxBasePluginsGui.Transpose.Transpose",
            tool_type="Transpose",
            name="Unpivot",
            position=None,
            configuration=ToolConfiguration(
                raw_xml="",
                parsed={"key_fields": ["id"], "data_fields": ["jan", "feb"]}
            ),
        )
        translator = get_translator(tool)
        res = translator.translate(tool, ["df_input"], empty_workflow)
        assert "pd.melt" in res.python_code
        assert "id_vars=['id']" in res.python_code

    def test_cross_tab_translator(self, empty_workflow):
        tool = Tool(
            tool_id=18,
            plugin="AlteryxBasePluginsGui.CrossTab.CrossTab",
            tool_type="CrossTab",
            name="Pivot",
            position=None,
            configuration=ToolConfiguration(
                raw_xml="",
                parsed={
                    "group_fields": ["id"],
                    "header_field": "month",
                    "data_field": "revenue",
                    "method": "Sum"
                }
            ),
        )
        translator = get_translator(tool)
        res = translator.translate(tool, ["df_input"], empty_workflow)
        assert "pd.pivot_table" in res.python_code
        assert "columns='month'" in res.python_code
