"""Comprehensive End-to-End Tests for Alteryx -> Python Translation.

Validates that Python code generation is:
1. 100% syntactically valid (ast.parse, py_compile).
2. Semantically faithful and executable.
3. Stream/anchor aware (Tool ID != Dataframe variable).
4. Strictly free of positional field fallback (explicit field resolution only).
5. Generic and domain-agnostic with zero hardcoded business logic.
"""

import ast
import inspect
from pathlib import Path
import py_compile
import pandas as pd
import openpyxl
import pytest

from awa.analysis.workflow_analyzer import analyze_canonical
from awa.generators.python_generator import generate_python_code
from awa.model.diagnostic import DiagnosticLevel
import awa.generators.python_generator as py_gen_module
import awa.expressions.pandas_emitter as expr_emitter_module


class TestPythonGeneratorE2E:
    """Validate generic, production-grade Python generation across various ETL patterns."""

    def test_static_anti_hardcoding_audit(self):
        """Audit Python generation modules to ensure zero hardcoded domain terms."""
        forbidden_terms = [
            "Demo_Claims",
            "Claims Volume",
            "Policy Master",
            "Claim Payments",
            "Claim Diary Notes",
            "Claim Number",
            "Total Paid",
            "Aging Bucket",
            "Litigation Flag",
            "Preclaim",
            "Active_Pending",
            "Approved",
            "Stable_and_Mature",
            "Product Type",
        ]

        # Check python_generator.py and pandas_emitter.py
        py_gen_src = inspect.getsource(py_gen_module)
        expr_src = inspect.getsource(expr_emitter_module)

        for term in forbidden_terms:
            assert term.lower() not in py_gen_src.lower(), f"Hardcoded term '{term}' in python_generator.py!"
            assert term.lower() not in expr_src.lower(), f"Hardcoded term '{term}' in pandas_emitter.py!"

    def test_generic_join_same_name(self, tmp_path: Path):
        """TEST 1: Same-name Join generates on=['Customer_ID']."""
        xml = """<?xml version="1.0"?>
<AlteryxDocument yxmdVer="2024.1">
  <Nodes>
    <Node ToolID="1"><GuiSettings Plugin="AlteryxBasePluginsGui.TextInput.TextInput" /><Properties><Configuration>
      <Fields><Field name="Customer_ID" /><Field name="Name" /></Fields>
      <Data><r><c>1</c><c>Alice</c></r></Data>
    </Configuration></Properties></Node>
    <Node ToolID="2"><GuiSettings Plugin="AlteryxBasePluginsGui.TextInput.TextInput" /><Properties><Configuration>
      <Fields><Field name="Customer_ID" /><Field name="Balance" /></Fields>
      <Data><r><c>1</c><c>500</c></r></Data>
    </Configuration></Properties></Node>
    <Node ToolID="3"><GuiSettings Plugin="AlteryxBasePluginsGui.Join.Join" /><Properties><Configuration>
      <JoinInfo connection="Left"><Field field="Customer_ID" /></JoinInfo>
      <JoinInfo connection="Right"><Field field="Customer_ID" /></JoinInfo>
    </Configuration></Properties></Node>
  </Nodes>
  <Connections>
    <Connection><Origin ToolID="1" Connection="Output" /><Destination ToolID="3" Connection="Left" /></Connection>
    <Connection><Origin ToolID="2" Connection="Output" /><Destination ToolID="3" Connection="Right" /></Connection>
  </Connections>
</AlteryxDocument>"""
        wf_file = tmp_path / "test_same_join.yxmd"
        wf_file.write_text(xml, encoding="utf-8")

        res = analyze_canonical(wf_file)
        code = res.translations[3].python_code

        assert "on=['Customer_ID']" in code
        assert "left_on=" not in code
        assert "right_on=" not in code

    def test_generic_join_different_name(self, tmp_path: Path):
        """TEST 2: Different-name Join generates left_on=['Customer_ID'], right_on=['CustomerNumber']."""
        xml = """<?xml version="1.0"?>
<AlteryxDocument yxmdVer="2024.1">
  <Nodes>
    <Node ToolID="1"><GuiSettings Plugin="AlteryxBasePluginsGui.TextInput.TextInput" /><Properties><Configuration>
      <Fields><Field name="Customer_ID" /><Field name="Name" /></Fields>
      <Data><r><c>1</c><c>Alice</c></r></Data>
    </Configuration></Properties></Node>
    <Node ToolID="2"><GuiSettings Plugin="AlteryxBasePluginsGui.TextInput.TextInput" /><Properties><Configuration>
      <Fields><Field name="CustomerNumber" /><Field name="Balance" /></Fields>
      <Data><r><c>1</c><c>500</c></r></Data>
    </Configuration></Properties></Node>
    <Node ToolID="3"><GuiSettings Plugin="AlteryxBasePluginsGui.Join.Join" /><Properties><Configuration>
      <JoinInfo connection="Left"><Field field="Customer_ID" /></JoinInfo>
      <JoinInfo connection="Right"><Field field="CustomerNumber" /></JoinInfo>
    </Configuration></Properties></Node>
  </Nodes>
  <Connections>
    <Connection><Origin ToolID="1" Connection="Output" /><Destination ToolID="3" Connection="Left" /></Connection>
    <Connection><Origin ToolID="2" Connection="Output" /><Destination ToolID="3" Connection="Right" /></Connection>
  </Connections>
</AlteryxDocument>"""
        wf_file = tmp_path / "test_diff_join.yxmd"
        wf_file.write_text(xml, encoding="utf-8")

        res = analyze_canonical(wf_file)
        code = res.translations[3].python_code

        assert "left_on=['Customer_ID']" in code
        assert "right_on=['CustomerNumber']" in code
        # Zero unresolved field warnings
        assert len([d for d in res.translations[3].diagnostics if d.category == "unresolved_field"]) == 0

    def test_generic_join_missing_field_diagnostic(self, tmp_path: Path):
        """TEST 3: Missing Join field emits explicit unresolved_field diagnostic and does NOT guess."""
        xml = """<?xml version="1.0"?>
<AlteryxDocument yxmdVer="2024.1">
  <Nodes>
    <Node ToolID="1"><GuiSettings Plugin="AlteryxBasePluginsGui.TextInput.TextInput" /><Properties><Configuration>
      <Fields><Field name="Customer_ID" /></Fields>
      <Data><r><c>1</c></r></Data>
    </Configuration></Properties></Node>
    <Node ToolID="2"><GuiSettings Plugin="AlteryxBasePluginsGui.TextInput.TextInput" /><Properties><Configuration>
      <Fields><Field name="CustomerNumber" /></Fields>
      <Data><r><c>1</c></r></Data>
    </Configuration></Properties></Node>
    <Node ToolID="3"><GuiSettings Plugin="AlteryxBasePluginsGui.Join.Join" /><Properties><Configuration>
      <JoinInfo connection="Left"><Field field="Customer_ID" /></JoinInfo>
      <JoinInfo connection="Right"><Field field="AccountNumber" /></JoinInfo>
    </Configuration></Properties></Node>
  </Nodes>
  <Connections>
    <Connection><Origin ToolID="1" Connection="Output" /><Destination ToolID="3" Connection="Left" /></Connection>
    <Connection><Origin ToolID="2" Connection="Output" /><Destination ToolID="3" Connection="Right" /></Connection>
  </Connections>
</AlteryxDocument>"""
        wf_file = tmp_path / "test_missing_join.yxmd"
        wf_file.write_text(xml, encoding="utf-8")

        res = analyze_canonical(wf_file)
        code = res.translations[3].python_code
        diags = res.translations[3].diagnostics

        # Verify no positional guessing
        assert "right_on=['AccountNumber']" in code
        # Verify explicit diagnostic emitted
        unresolved = [d for d in diags if d.category == "unresolved_field"]
        assert len(unresolved) == 1
        assert "AccountNumber" in unresolved[0].message
        assert "CustomerNumber" in unresolved[0].message

    def test_generic_summarize_rename_propagation(self, tmp_path: Path):
        """TEST 4: Summarize explicit rename propagates and resolves cleanly in downstream Join."""
        xml = """<?xml version="1.0"?>
<AlteryxDocument yxmdVer="2024.1">
  <Nodes>
    <Node ToolID="1"><GuiSettings Plugin="AlteryxBasePluginsGui.TextInput.TextInput" /><Properties><Configuration>
      <Fields><Field name="TxDate" /></Fields>
      <Data><r><c>2023-01-01</c></r></Data>
    </Configuration></Properties></Node>
    <Node ToolID="2"><GuiSettings Plugin="AlteryxBasePluginsGui.Summarize.Summarize" /><Properties><Configuration>
      <SummarizeFields>
        <SummarizeField field="TxDate" action="Max" rename="Last Run Date" />
      </SummarizeFields>
    </Configuration></Properties></Node>
    <Node ToolID="3"><GuiSettings Plugin="AlteryxBasePluginsGui.TextInput.TextInput" /><Properties><Configuration>
      <Fields><Field name="OrderDate" /></Fields>
      <Data><r><c>2023-01-01</c></r></Data>
    </Configuration></Properties></Node>
    <Node ToolID="4"><GuiSettings Plugin="AlteryxBasePluginsGui.Join.Join" /><Properties><Configuration>
      <JoinInfo connection="Left"><Field field="OrderDate" /></JoinInfo>
      <JoinInfo connection="Right"><Field field="Last Run Date" /></JoinInfo>
    </Configuration></Properties></Node>
  </Nodes>
  <Connections>
    <Connection><Origin ToolID="1" Connection="Output" /><Destination ToolID="2" Connection="Input" /></Connection>
    <Connection><Origin ToolID="3" Connection="Output" /><Destination ToolID="4" Connection="Left" /></Connection>
    <Connection><Origin ToolID="2" Connection="Output" /><Destination ToolID="4" Connection="Right" /></Connection>
  </Connections>
</AlteryxDocument>"""
        wf_file = tmp_path / "test_sum_rename.yxmd"
        wf_file.write_text(xml, encoding="utf-8")

        res = analyze_canonical(wf_file)
        code = res.translations[4].python_code

        assert "left_on=['OrderDate']" in code
        assert "right_on=['Last Run Date']" in code
        # Zero unresolved field warnings because rename propagated through schema
        assert len([d for d in res.translations[4].diagnostics if d.category == "unresolved_field"]) == 0

    def test_generic_summarize_missing_rename_diagnostic(self, tmp_path: Path):
        """TEST 5: Summarize without rename outputs Max_TxDate; downstream requesting Last Run Date reports diagnostic."""
        xml = """<?xml version="1.0"?>
<AlteryxDocument yxmdVer="2024.1">
  <Nodes>
    <Node ToolID="1"><GuiSettings Plugin="AlteryxBasePluginsGui.TextInput.TextInput" /><Properties><Configuration>
      <Fields><Field name="TxDate" /></Fields>
      <Data><r><c>2023-01-01</c></r></Data>
    </Configuration></Properties></Node>
    <Node ToolID="2"><GuiSettings Plugin="AlteryxBasePluginsGui.Summarize.Summarize" /><Properties><Configuration>
      <SummarizeFields>
        <SummarizeField field="TxDate" action="Max" rename="" />
      </SummarizeFields>
    </Configuration></Properties></Node>
    <Node ToolID="3"><GuiSettings Plugin="AlteryxBasePluginsGui.TextInput.TextInput" /><Properties><Configuration>
      <Fields><Field name="OrderDate" /></Fields>
      <Data><r><c>2023-01-01</c></r></Data>
    </Configuration></Properties></Node>
    <Node ToolID="4"><GuiSettings Plugin="AlteryxBasePluginsGui.Join.Join" /><Properties><Configuration>
      <JoinInfo connection="Left"><Field field="OrderDate" /></JoinInfo>
      <JoinInfo connection="Right"><Field field="Last Run Date" /></JoinInfo>
    </Configuration></Properties></Node>
  </Nodes>
  <Connections>
    <Connection><Origin ToolID="1" Connection="Output" /><Destination ToolID="2" Connection="Input" /></Connection>
    <Connection><Origin ToolID="3" Connection="Output" /><Destination ToolID="4" Connection="Left" /></Connection>
    <Connection><Origin ToolID="2" Connection="Output" /><Destination ToolID="4" Connection="Right" /></Connection>
  </Connections>
</AlteryxDocument>"""
        wf_file = tmp_path / "test_sum_missing_rename.yxmd"
        wf_file.write_text(xml, encoding="utf-8")

        res = analyze_canonical(wf_file)
        diags = res.translations[4].diagnostics
        unresolved = [d for d in diags if d.category == "unresolved_field"]
        assert len(unresolved) == 1
        assert "Last Run Date" in unresolved[0].message
        assert "Max_TxDate" in unresolved[0].message

    def test_generic_multi_column_join(self, tmp_path: Path):
        """TEST 6: Multi-column join preserves configured order and uses distinct left/right lists."""
        xml = """<?xml version="1.0"?>
<AlteryxDocument yxmdVer="2024.1">
  <Nodes>
    <Node ToolID="1"><GuiSettings Plugin="AlteryxBasePluginsGui.TextInput.TextInput" /><Properties><Configuration>
      <Fields><Field name="Country" /><Field name="Customer_ID" /></Fields>
      <Data><r><c>US</c><c>101</c></r></Data>
    </Configuration></Properties></Node>
    <Node ToolID="2"><GuiSettings Plugin="AlteryxBasePluginsGui.TextInput.TextInput" /><Properties><Configuration>
      <Fields><Field name="Country_Code" /><Field name="CustomerNumber" /></Fields>
      <Data><r><c>US</c><c>101</c></r></Data>
    </Configuration></Properties></Node>
    <Node ToolID="3"><GuiSettings Plugin="AlteryxBasePluginsGui.Join.Join" /><Properties><Configuration>
      <JoinInfo connection="Left"><Field field="Country" /><Field field="Customer_ID" /></JoinInfo>
      <JoinInfo connection="Right"><Field field="Country_Code" /><Field field="CustomerNumber" /></JoinInfo>
    </Configuration></Properties></Node>
  </Nodes>
  <Connections>
    <Connection><Origin ToolID="1" Connection="Output" /><Destination ToolID="3" Connection="Left" /></Connection>
    <Connection><Origin ToolID="2" Connection="Output" /><Destination ToolID="3" Connection="Right" /></Connection>
  </Connections>
</AlteryxDocument>"""
        wf_file = tmp_path / "test_multi_join.yxmd"
        wf_file.write_text(xml, encoding="utf-8")

        res = analyze_canonical(wf_file)
        code = res.translations[3].python_code

        assert "left_on=['Country', 'Customer_ID']" in code
        assert "right_on=['Country_Code', 'CustomerNumber']" in code

    def test_generic_union_by_position(self, tmp_path: Path):
        """TEST 7: Union configured by position aligns columns to first stream ordinal positions."""
        in_1 = tmp_path / "u1.csv"
        in_2 = tmp_path / "u2.csv"
        pd.DataFrame({"ColA": [1], "ColB": ["x"]}).to_csv(in_1, index=False)
        pd.DataFrame({"OtherA": [2], "OtherB": ["y"]}).to_csv(in_2, index=False)
        out_csv = tmp_path / "union_pos_out.csv"

        xml = f"""<?xml version="1.0"?>
<AlteryxDocument yxmdVer="2024.1">
  <Nodes>
    <Node ToolID="1"><GuiSettings Plugin="AlteryxBasePluginsGui.DbFileInput.DbFileInput" /><Properties><Configuration><File>{in_1}</File></Configuration></Properties></Node>
    <Node ToolID="2"><GuiSettings Plugin="AlteryxBasePluginsGui.DbFileInput.DbFileInput" /><Properties><Configuration><File>{in_2}</File></Configuration></Properties></Node>
    <Node ToolID="3"><GuiSettings Plugin="AlteryxBasePluginsGui.Union.Union" /><Properties><Configuration>
      <ByNameOrPos>ByPos</ByNameOrPos>
    </Configuration></Properties></Node>
    <Node ToolID="4"><GuiSettings Plugin="AlteryxBasePluginsGui.DbFileOutput.DbFileOutput" /><Properties><Configuration><File>{out_csv}</File></Configuration></Properties></Node>
  </Nodes>
  <Connections>
    <Connection><Origin ToolID="1" Connection="Output" /><Destination ToolID="3" Connection="Input" /></Connection>
    <Connection><Origin ToolID="2" Connection="Output" /><Destination ToolID="3" Connection="Input" /></Connection>
    <Connection><Origin ToolID="3" Connection="Output" /><Destination ToolID="4" Connection="Input" /></Connection>
  </Connections>
</AlteryxDocument>"""
        wf_file = tmp_path / "test_union_pos.yxmd"
        wf_file.write_text(xml, encoding="utf-8")

        res = analyze_canonical(wf_file)
        code, _, _ = generate_python_code(res.workflow, res.execution_order, res.translations, res.consumed_anchors)

        ast.parse(code)
        exec(code, {})

        df_res = pd.read_csv(out_csv)
        assert list(df_res.columns) == ["ColA", "ColB"]
        assert len(df_res) == 2
        assert list(df_res["ColA"]) == [1, 2]

    def test_generic_union_by_name(self, tmp_path: Path):
        """TEST 8: Union configured by name aligns columns by name."""
        in_1 = tmp_path / "u_name1.csv"
        in_2 = tmp_path / "u_name2.csv"
        pd.DataFrame({"Region": ["East"], "Revenue": [1000]}).to_csv(in_1, index=False)
        pd.DataFrame({"Revenue": [1500], "Region": ["West"]}).to_csv(in_2, index=False)
        out_csv = tmp_path / "union_name_out.csv"

        xml = f"""<?xml version="1.0"?>
<AlteryxDocument yxmdVer="2024.1">
  <Nodes>
    <Node ToolID="1"><GuiSettings Plugin="AlteryxBasePluginsGui.DbFileInput.DbFileInput" /><Properties><Configuration><File>{in_1}</File></Configuration></Properties></Node>
    <Node ToolID="2"><GuiSettings Plugin="AlteryxBasePluginsGui.DbFileInput.DbFileInput" /><Properties><Configuration><File>{in_2}</File></Configuration></Properties></Node>
    <Node ToolID="3"><GuiSettings Plugin="AlteryxBasePluginsGui.Union.Union" /><Properties><Configuration>
      <ByNameOrPos>ByName</ByNameOrPos>
    </Configuration></Properties></Node>
    <Node ToolID="4"><GuiSettings Plugin="AlteryxBasePluginsGui.DbFileOutput.DbFileOutput" /><Properties><Configuration><File>{out_csv}</File></Configuration></Properties></Node>
  </Nodes>
  <Connections>
    <Connection><Origin ToolID="1" Connection="Output" /><Destination ToolID="3" Connection="Input" /></Connection>
    <Connection><Origin ToolID="2" Connection="Output" /><Destination ToolID="3" Connection="Input" /></Connection>
    <Connection><Origin ToolID="3" Connection="Output" /><Destination ToolID="4" Connection="Input" /></Connection>
  </Connections>
</AlteryxDocument>"""
        wf_file = tmp_path / "test_union_name.yxmd"
        wf_file.write_text(xml, encoding="utf-8")

        res = analyze_canonical(wf_file)
        code, _, _ = generate_python_code(res.workflow, res.execution_order, res.translations, res.consumed_anchors)

        ast.parse(code)
        exec(code, {})

        df_res = pd.read_csv(out_csv)
        assert len(df_res) == 2
        assert set(df_res["Region"]) == {"East", "West"}

    def test_generic_select_rename_propagation(self, tmp_path: Path):
        """TEST 9: Select rename propagates to downstream tools without retaining old names."""
        xml = """<?xml version="1.0"?>
<AlteryxDocument yxmdVer="2024.1">
  <Nodes>
    <Node ToolID="1"><GuiSettings Plugin="AlteryxBasePluginsGui.TextInput.TextInput" /><Properties><Configuration>
      <Fields><Field name="Customer_ID" /><Field name="Old_Field" /></Fields>
      <Data><r><c>101</c><c>val</c></r></Data>
    </Configuration></Properties></Node>
    <Node ToolID="2"><GuiSettings Plugin="AlteryxBasePluginsGui.AlteryxSelect.AlteryxSelect" /><Properties><Configuration>
      <SelectFields>
        <SelectField field="Customer_ID" selected="True" rename="Customer Number" />
        <SelectField field="Old_Field" selected="False" />
      </SelectFields>
    </Configuration></Properties></Node>
    <Node ToolID="3"><GuiSettings Plugin="AlteryxBasePluginsGui.TextInput.TextInput" /><Properties><Configuration>
      <Fields><Field name="Customer Number" /><Field name="Score" /></Fields>
      <Data><r><c>101</c><c>99</c></r></Data>
    </Configuration></Properties></Node>
    <Node ToolID="4"><GuiSettings Plugin="AlteryxBasePluginsGui.Join.Join" /><Properties><Configuration>
      <JoinInfo connection="Left"><Field field="Customer Number" /></JoinInfo>
      <JoinInfo connection="Right"><Field field="Customer Number" /></JoinInfo>
    </Configuration></Properties></Node>
  </Nodes>
  <Connections>
    <Connection><Origin ToolID="1" Connection="Output" /><Destination ToolID="2" Connection="Input" /></Connection>
    <Connection><Origin ToolID="2" Connection="Output" /><Destination ToolID="4" Connection="Left" /></Connection>
    <Connection><Origin ToolID="3" Connection="Output" /><Destination ToolID="4" Connection="Right" /></Connection>
  </Connections>
</AlteryxDocument>"""
        wf_file = tmp_path / "test_select_prop.yxmd"
        wf_file.write_text(xml, encoding="utf-8")

        res = analyze_canonical(wf_file)
        code = res.translations[4].python_code

        assert "on=['Customer Number']" in code
        assert len([d for d in res.translations[4].diagnostics if d.category == "unresolved_field"]) == 0

    def test_schema_source_and_passthrough(self, tmp_path: Path):
        """TEST 1 & 2: Source schema discovery & Pass-through schema preservation (BlockUntilDone)."""
        xml = """<?xml version="1.0"?>
<AlteryxDocument yxmdVer="2024.1">
  <Nodes>
    <Node ToolID="1"><GuiSettings Plugin="AlteryxBasePluginsGui.TextInput.TextInput" /><Properties><Configuration>
      <Fields><Field name="A" /><Field name="B" /></Fields>
      <Data><r><c>1</c><c>2</c></r></Data>
    </Configuration></Properties></Node>
    <Node ToolID="2"><GuiSettings Plugin="AlteryxBasePluginsGui.BlockUntilDone.BlockUntilDone" /></Node>
    <Node ToolID="3"><GuiSettings Plugin="AlteryxBasePluginsGui.AlteryxSelect.AlteryxSelect" /><Properties><Configuration>
      <SelectFields>
        <SelectField field="A" selected="True" />
        <SelectField field="B" selected="True" />
      </SelectFields>
    </Configuration></Properties></Node>
  </Nodes>
  <Connections>
    <Connection><Origin ToolID="1" Connection="Output" /><Destination ToolID="2" Connection="Input" /></Connection>
    <Connection><Origin ToolID="2" Connection="Output" /><Destination ToolID="3" Connection="Input" /></Connection>
  </Connections>
</AlteryxDocument>"""
        wf_file = tmp_path / "test_source_passthrough.yxmd"
        wf_file.write_text(xml, encoding="utf-8")

        res = analyze_canonical(wf_file)
        schemas = getattr(res.workflow, "_stream_schemas", {})

        # TEST 1: Source schema contains A, B
        assert "df_1" in schemas
        assert set(schemas["df_1"]) == {"A", "B"}

        # TEST 2: Pass-through preserves A, B (NOT [])
        # Tool 2 is pass-through, so df_1 is passed to downstream
        assert len([d for d in res.translations[3].diagnostics if d.category == "unresolved_field"]) == 0

    def test_schema_select_rename(self, tmp_path: Path):
        """TEST 3: Select rename transforms schema: A, B -> B, C."""
        xml = """<?xml version="1.0"?>
<AlteryxDocument yxmdVer="2024.1">
  <Nodes>
    <Node ToolID="1"><GuiSettings Plugin="AlteryxBasePluginsGui.TextInput.TextInput" /><Properties><Configuration>
      <Fields><Field name="A" /><Field name="B" /></Fields>
      <Data><r><c>1</c><c>2</c></r></Data>
    </Configuration></Properties></Node>
    <Node ToolID="2"><GuiSettings Plugin="AlteryxBasePluginsGui.AlteryxSelect.AlteryxSelect" /><Properties><Configuration>
      <SelectFields>
        <SelectField field="A" selected="True" rename="C" />
        <SelectField field="B" selected="True" />
      </SelectFields>
    </Configuration></Properties></Node>
  </Nodes>
  <Connections>
    <Connection><Origin ToolID="1" Connection="Output" /><Destination ToolID="2" Connection="Input" /></Connection>
  </Connections>
</AlteryxDocument>"""
        wf_file = tmp_path / "test_sel_rename.yxmd"
        wf_file.write_text(xml, encoding="utf-8")

        res = analyze_canonical(wf_file)
        schemas = getattr(res.workflow, "_stream_schemas", {})

        assert "df_2" in schemas
        assert list(schemas["df_2"]) == ["C", "B"]

    def test_schema_formula(self, tmp_path: Path):
        """TEST 4: Formula adds new calculated fields: A, B -> A, B, C."""
        xml = """<?xml version="1.0"?>
<AlteryxDocument yxmdVer="2024.1">
  <Nodes>
    <Node ToolID="1"><GuiSettings Plugin="AlteryxBasePluginsGui.TextInput.TextInput" /><Properties><Configuration>
      <Fields><Field name="A" /><Field name="B" /></Fields>
      <Data><r><c>1</c><c>2</c></r></Data>
    </Configuration></Properties></Node>
    <Node ToolID="2"><GuiSettings Plugin="AlteryxBasePluginsGui.Formula.Formula" /><Properties><Configuration>
      <FormulaFields>
        <FormulaField field="C" expression="[A] + [B]" type="Double" size="8" />
      </FormulaFields>
    </Configuration></Properties></Node>
  </Nodes>
  <Connections>
    <Connection><Origin ToolID="1" Connection="Output" /><Destination ToolID="2" Connection="Input" /></Connection>
  </Connections>
</AlteryxDocument>"""
        wf_file = tmp_path / "test_formula_schema.yxmd"
        wf_file.write_text(xml, encoding="utf-8")

        res = analyze_canonical(wf_file)
        schemas = getattr(res.workflow, "_stream_schemas", {})

        assert "df_2" in schemas
        assert list(schemas["df_2"]) == ["A", "B", "C"]

    def test_schema_join_j_l_r_outputs(self, tmp_path: Path):
        """TEST 5, 7, 8, 9: Join same-name fields & validation of J, L, R output schemas."""
        xml = """<?xml version="1.0"?>
<AlteryxDocument yxmdVer="2024.1">
  <Nodes>
    <Node ToolID="1"><GuiSettings Plugin="AlteryxBasePluginsGui.TextInput.TextInput" /><Properties><Configuration>
      <Fields><Field name="ID" /><Field name="A" /></Fields>
      <Data><r><c>1</c><c>alpha</c></r></Data>
    </Configuration></Properties></Node>
    <Node ToolID="2"><GuiSettings Plugin="AlteryxBasePluginsGui.TextInput.TextInput" /><Properties><Configuration>
      <Fields><Field name="ID" /><Field name="B" /></Fields>
      <Data><r><c>1</c><c>beta</c></r></Data>
    </Configuration></Properties></Node>
    <Node ToolID="3"><GuiSettings Plugin="AlteryxBasePluginsGui.Join.Join" /><Properties><Configuration>
      <JoinInfo connection="Left"><Field field="ID" /></JoinInfo>
      <JoinInfo connection="Right"><Field field="ID" /></JoinInfo>
    </Configuration></Properties></Node>
  </Nodes>
  <Connections>
    <Connection><Origin ToolID="1" Connection="Output" /><Destination ToolID="3" Connection="Left" /></Connection>
    <Connection><Origin ToolID="2" Connection="Output" /><Destination ToolID="3" Connection="Right" /></Connection>
  </Connections>
</AlteryxDocument>"""
        wf_file = tmp_path / "test_join_schemas.yxmd"
        wf_file.write_text(xml, encoding="utf-8")

        res = analyze_canonical(wf_file)
        schemas = getattr(res.workflow, "_stream_schemas", {})

        # TEST 5: Zero unresolved warnings
        assert len([d for d in res.translations[3].diagnostics if d.category == "unresolved_field"]) == 0

        # TEST 7: J output schema has merged fields (with suffix on right overlap)
        j_var = res.translations[3].output_map["Join"]
        assert "ID" in schemas[j_var]
        assert "A" in schemas[j_var]
        assert "B" in schemas[j_var]

        # TEST 8: L output schema has left-side fields
        l_var = res.translations[3].output_map["Left"]
        assert set(schemas[l_var]) == {"ID", "A"}

        # TEST 9: R output schema has right-side fields
        r_var = res.translations[3].output_map["Right"]
        assert set(schemas[r_var]) == {"ID", "B"}

    def test_schema_summarize_aggregation_and_rename(self, tmp_path: Path):
        """TEST 11 & 12: Summarize aggregation output fields & downstream rename resolution."""
        xml = """<?xml version="1.0"?>
<AlteryxDocument yxmdVer="2024.1">
  <Nodes>
    <Node ToolID="1"><GuiSettings Plugin="AlteryxBasePluginsGui.TextInput.TextInput" /><Properties><Configuration>
      <Fields><Field name="Claim Number" /><Field name="Payment Amount" /></Fields>
      <Data><r><c>101</c><c>500</c></r></Data>
    </Configuration></Properties></Node>
    <Node ToolID="2"><GuiSettings Plugin="AlteryxBasePluginsGui.Summarize.Summarize" /><Properties><Configuration>
      <SummarizeFields>
        <SummarizeField field="Claim Number" action="GroupBy" rename="" />
        <SummarizeField field="Payment Amount" action="Sum" rename="Total Paid" />
      </SummarizeFields>
    </Configuration></Properties></Node>
  </Nodes>
  <Connections>
    <Connection><Origin ToolID="1" Connection="Output" /><Destination ToolID="2" Connection="Input" /></Connection>
  </Connections>
</AlteryxDocument>"""
        wf_file = tmp_path / "test_sum_schema.yxmd"
        wf_file.write_text(xml, encoding="utf-8")

        res = analyze_canonical(wf_file)
        schemas = getattr(res.workflow, "_stream_schemas", {})

        # TEST 11: Output schema is Claim Number, Total Paid (NOT Payment Amount)
        assert "df_2" in schemas
        assert list(schemas["df_2"]) == ["Claim Number", "Total Paid"]
        assert "Payment Amount" not in schemas["df_2"]

    def test_schema_genuine_missing_field_diagnostic(self, tmp_path: Path):
        """TEST 13: Genuine missing field emits explicit unresolved_field diagnostic."""
        xml = """<?xml version="1.0"?>
<AlteryxDocument yxmdVer="2024.1">
  <Nodes>
    <Node ToolID="1"><GuiSettings Plugin="AlteryxBasePluginsGui.TextInput.TextInput" /><Properties><Configuration>
      <Fields><Field name="A" /><Field name="B" /></Fields>
      <Data><r><c>1</c><c>2</c></r></Data>
    </Configuration></Properties></Node>
    <Node ToolID="2"><GuiSettings Plugin="AlteryxBasePluginsGui.TextInput.TextInput" /><Properties><Configuration>
      <Fields><Field name="A" /><Field name="B" /></Fields>
      <Data><r><c>1</c><c>2</c></r></Data>
    </Configuration></Properties></Node>
    <Node ToolID="3"><GuiSettings Plugin="AlteryxBasePluginsGui.Join.Join" /><Properties><Configuration>
      <JoinInfo connection="Left"><Field field="A" /></JoinInfo>
      <JoinInfo connection="Right"><Field field="NonExistent" /></JoinInfo>
    </Configuration></Properties></Node>
  </Nodes>
  <Connections>
    <Connection><Origin ToolID="1" Connection="Output" /><Destination ToolID="3" Connection="Left" /></Connection>
    <Connection><Origin ToolID="2" Connection="Output" /><Destination ToolID="3" Connection="Right" /></Connection>
  </Connections>
</AlteryxDocument>"""
        wf_file = tmp_path / "test_missing_diag.yxmd"
        wf_file.write_text(xml, encoding="utf-8")

        res = analyze_canonical(wf_file)
        diags = res.translations[3].diagnostics
        unresolved = [d for d in diags if d.category == "unresolved_field"]
        assert len(unresolved) == 1
        assert "NonExistent" in unresolved[0].message
        assert "Available fields: ['A', 'B']" in unresolved[0].message

    def test_select_missing_field_diagnostic(self, tmp_path: Path):
        """Section 19: Select configuration containing missing field D generates explicit diagnostic and does NOT silently drop D."""
        xml = """<?xml version="1.0"?>
<AlteryxDocument yxmdVer="2024.1">
  <Nodes>
    <Node ToolID="1"><GuiSettings Plugin="AlteryxBasePluginsGui.TextInput.TextInput" /><Properties><Configuration>
      <Fields><Field name="A" /><Field name="B" /><Field name="C" /></Fields>
      <Data><r><c>1</c><c>2</c><c>3</c></r></Data>
    </Configuration></Properties></Node>
    <Node ToolID="2"><GuiSettings Plugin="AlteryxBasePluginsGui.AlteryxSelect.AlteryxSelect" /><Properties><Configuration>
      <SelectFields>
        <SelectField field="A" selected="True" />
        <SelectField field="B" selected="True" />
        <SelectField field="D" selected="True" />
      </SelectFields>
    </Configuration></Properties></Node>
  </Nodes>
  <Connections>
    <Connection><Origin ToolID="1" Connection="Output" /><Destination ToolID="2" Connection="Input" /></Connection>
  </Connections>
</AlteryxDocument>"""
        wf_file = tmp_path / "test_sel_missing.yxmd"
        wf_file.write_text(xml, encoding="utf-8")

        res = analyze_canonical(wf_file)
        code = res.translations[2].python_code
        diags = res.translations[2].diagnostics

        # 1. Verify explicit diagnostic produced for D
        unresolved = [d for d in diags if d.category == "unresolved_field"]
        assert len(unresolved) == 1
        assert "D" in unresolved[0].message
        assert "Available fields" in unresolved[0].message

        # 2. Verify generated code explicitly requested D and did not silently filter it out
        assert "['A', 'B', 'D']" in code

    def test_select_rename_propagation_success(self, tmp_path: Path):
        """Section 20: Select rename A -> Customer ID allows downstream tool to resolve Customer ID."""
        xml = """<?xml version="1.0"?>
<AlteryxDocument yxmdVer="2024.1">
  <Nodes>
    <Node ToolID="1"><GuiSettings Plugin="AlteryxBasePluginsGui.TextInput.TextInput" /><Properties><Configuration>
      <Fields><Field name="A" /><Field name="B" /></Fields>
      <Data><r><c>1</c><c>2</c></r></Data>
    </Configuration></Properties></Node>
    <Node ToolID="2"><GuiSettings Plugin="AlteryxBasePluginsGui.AlteryxSelect.AlteryxSelect" /><Properties><Configuration>
      <SelectFields>
        <SelectField field="A" selected="True" rename="Customer ID" />
        <SelectField field="B" selected="True" />
      </SelectFields>
    </Configuration></Properties></Node>
    <Node ToolID="3"><GuiSettings Plugin="AlteryxBasePluginsGui.Sort.Sort" /><Properties><Configuration>
      <SortInfo>
        <Field field="Customer ID" order="Ascending" />
      </SortInfo>
    </Configuration></Properties></Node>
  </Nodes>
  <Connections>
    <Connection><Origin ToolID="1" Connection="Output" /><Destination ToolID="2" Connection="Input" /></Connection>
    <Connection><Origin ToolID="2" Connection="Output" /><Destination ToolID="3" Connection="Input" /></Connection>
  </Connections>
</AlteryxDocument>"""
        wf_file = tmp_path / "test_sel_rename_prop.yxmd"
        wf_file.write_text(xml, encoding="utf-8")

        res = analyze_canonical(wf_file)
        schemas = getattr(res.workflow, "_stream_schemas", {})

        # Tool 2 output schema has Customer ID
        assert "df_2" in schemas
        assert list(schemas["df_2"]) == ["Customer ID", "B"]

        # Tool 3 successfully resolves Customer ID without warnings
        assert len([d for d in res.translations[3].diagnostics if d.category == "unresolved_field"]) == 0

    def test_select_remove_propagation_diagnostic(self, tmp_path: Path):
        """Section 21: Select removal of C causes downstream reference to C to fail with diagnostic."""
        xml = """<?xml version="1.0"?>
<AlteryxDocument yxmdVer="2024.1">
  <Nodes>
    <Node ToolID="1"><GuiSettings Plugin="AlteryxBasePluginsGui.TextInput.TextInput" /><Properties><Configuration>
      <Fields><Field name="A" /><Field name="B" /><Field name="C" /></Fields>
      <Data><r><c>1</c><c>2</c><c>3</c></r></Data>
    </Configuration></Properties></Node>
    <Node ToolID="2"><GuiSettings Plugin="AlteryxBasePluginsGui.AlteryxSelect.AlteryxSelect" /><Properties><Configuration>
      <SelectFields>
        <SelectField field="A" selected="True" />
        <SelectField field="B" selected="True" />
        <SelectField field="C" selected="False" />
      </SelectFields>
    </Configuration></Properties></Node>
    <Node ToolID="3"><GuiSettings Plugin="AlteryxBasePluginsGui.Sort.Sort" /><Properties><Configuration>
      <SortInfo>
        <Field field="C" order="Ascending" />
      </SortInfo>
    </Configuration></Properties></Node>
  </Nodes>
  <Connections>
    <Connection><Origin ToolID="1" Connection="Output" /><Destination ToolID="2" Connection="Input" /></Connection>
    <Connection><Origin ToolID="2" Connection="Output" /><Destination ToolID="3" Connection="Input" /></Connection>
  </Connections>
</AlteryxDocument>"""
        wf_file = tmp_path / "test_sel_remove_prop.yxmd"
        wf_file.write_text(xml, encoding="utf-8")

        res = analyze_canonical(wf_file)
        schemas = getattr(res.workflow, "_stream_schemas", {})

        # Tool 2 output schema has only A, B
        assert "df_2" in schemas
        assert list(schemas["df_2"]) == ["A", "B"]

        # Tool 3 emits unresolved diagnostic for C
        unresolved = [d for d in res.translations[3].diagnostics if d.category == "unresolved_field"]
        assert len(unresolved) == 1
        assert "C" in unresolved[0].message

    def test_formula_missing_field_diagnostic(self, tmp_path: Path):
        """Section 22: Formula referencing missing field emits explicit diagnostic."""
        xml = """<?xml version="1.0"?>
<AlteryxDocument yxmdVer="2024.1">
  <Nodes>
    <Node ToolID="1"><GuiSettings Plugin="AlteryxBasePluginsGui.TextInput.TextInput" /><Properties><Configuration>
      <Fields><Field name="Amount" /></Fields>
      <Data><r><c>100</c></r></Data>
    </Configuration></Properties></Node>
    <Node ToolID="2"><GuiSettings Plugin="AlteryxBasePluginsGui.Formula.Formula" /><Properties><Configuration>
      <FormulaFields>
        <FormulaField field="Total" expression="[Amount] * [Quantity]" type="Double" size="8" />
      </FormulaFields>
    </Configuration></Properties></Node>
  </Nodes>
  <Connections>
    <Connection><Origin ToolID="1" Connection="Output" /><Destination ToolID="2" Connection="Input" /></Connection>
  </Connections>
</AlteryxDocument>"""
        wf_file = tmp_path / "test_formula_missing.yxmd"
        wf_file.write_text(xml, encoding="utf-8")

        res = analyze_canonical(wf_file)
        diags = res.translations[2].diagnostics
        unresolved = [d for d in diags if d.category == "unresolved_field"]
        assert len(unresolved) == 1
        assert "Quantity" in unresolved[0].message

    def test_summarize_missing_field_diagnostic(self, tmp_path: Path):
        """Section 23: Summarize referencing missing field emits explicit diagnostic."""
        xml = """<?xml version="1.0"?>
<AlteryxDocument yxmdVer="2024.1">
  <Nodes>
    <Node ToolID="1"><GuiSettings Plugin="AlteryxBasePluginsGui.TextInput.TextInput" /><Properties><Configuration>
      <Fields><Field name="Claim Number" /></Fields>
      <Data><r><c>101</c></r></Data>
    </Configuration></Properties></Node>
    <Node ToolID="2"><GuiSettings Plugin="AlteryxBasePluginsGui.Summarize.Summarize" /><Properties><Configuration>
      <SummarizeFields>
        <SummarizeField field="Claim Number" action="GroupBy" rename="" />
        <SummarizeField field="Payment Amount" action="Sum" rename="Total Paid" />
      </SummarizeFields>
    </Configuration></Properties></Node>
  </Nodes>
  <Connections>
    <Connection><Origin ToolID="1" Connection="Output" /><Destination ToolID="2" Connection="Input" /></Connection>
  </Connections>
</AlteryxDocument>"""
        wf_file = tmp_path / "test_sum_missing.yxmd"
        wf_file.write_text(xml, encoding="utf-8")

        res = analyze_canonical(wf_file)
        diags = res.translations[2].diagnostics
        unresolved = [d for d in diags if d.category == "unresolved_field"]
        assert len(unresolved) == 1
        assert "Payment Amount" in unresolved[0].message

    def test_join_missing_right_key_diagnostic(self, tmp_path: Path):
        """Section 24: Join with missing right key generates explicit diagnostic and keeps right_on."""
        xml = """<?xml version="1.0"?>
<AlteryxDocument yxmdVer="2024.1">
  <Nodes>
    <Node ToolID="1"><GuiSettings Plugin="AlteryxBasePluginsGui.TextInput.TextInput" /><Properties><Configuration>
      <Fields><Field name="Customer_ID" /></Fields>
      <Data><r><c>1</c></r></Data>
    </Configuration></Properties></Node>
    <Node ToolID="2"><GuiSettings Plugin="AlteryxBasePluginsGui.TextInput.TextInput" /><Properties><Configuration>
      <Fields><Field name="Balance" /></Fields>
      <Data><r><c>100</c></r></Data>
    </Configuration></Properties></Node>
    <Node ToolID="3"><GuiSettings Plugin="AlteryxBasePluginsGui.Join.Join" /><Properties><Configuration>
      <JoinInfo connection="Left"><Field field="Customer_ID" /></JoinInfo>
      <JoinInfo connection="Right"><Field field="CustomerNumber" /></JoinInfo>
    </Configuration></Properties></Node>
  </Nodes>
  <Connections>
    <Connection><Origin ToolID="1" Connection="Output" /><Destination ToolID="3" Connection="Left" /></Connection>
    <Connection><Origin ToolID="2" Connection="Output" /><Destination ToolID="3" Connection="Right" /></Connection>
  </Connections>
</AlteryxDocument>"""
        wf_file = tmp_path / "test_join_missing_key.yxmd"
        wf_file.write_text(xml, encoding="utf-8")

        res = analyze_canonical(wf_file)
        code = res.translations[3].python_code
        diags = res.translations[3].diagnostics

        assert "left_on=['Customer_ID']" in code
        assert "right_on=['CustomerNumber']" in code

        unresolved = [d for d in diags if d.category == "unresolved_field"]
        assert len(unresolved) == 1
        assert "CustomerNumber" in unresolved[0].message

    def test_demo_claims_workflow_correctness(self, tmp_path: Path):
        """TEST 14: Full validation against Demo Claims workflow."""
        wf_path = Path("Demo_Claims_Volume_Extract_reconstructed.yxmd")
        res = analyze_canonical(wf_path)
        code, trace_map, req_libs = generate_python_code(res.workflow, res.execution_order, res.translations, res.consumed_anchors)

        # 1. AST Validation
        parsed_ast = ast.parse(code)
        assert parsed_ast is not None

        # 2. py_compile validation
        script_file = tmp_path / "demo_claims_compiled.py"
        script_file.write_text(code, encoding="utf-8")
        py_compile.compile(str(script_file), doraise=True)

        # 3. Verify no undefined df_2
        assert "df_2" not in code
        assert "/* UNSUPPORTED" not in code

        # 4. Verify no positional column fallbacks in Join code
        assert "columns[i]" not in code
        assert "columns[0]" not in code

        # 5. Verify Join #111, #112, #115 work with clean left_on/right_on or on, and ZERO false warnings
        assert "on=['Policy Number']" in res.translations[111].python_code
        assert "on=['Claim Number']" in res.translations[112].python_code
        assert "on=['Claim Number']" in res.translations[115].python_code

        assert len([d for d in res.translations[111].diagnostics if d.category == "unresolved_field"]) == 0
        assert len([d for d in res.translations[112].diagnostics if d.category == "unresolved_field"]) == 0
        assert len([d for d in res.translations[115].diagnostics if d.category == "unresolved_field"]) == 0

        # 6. Verify Tool #10 is handled faithfully to the .yxmd without guessing
        assert "left_on=['Quarter End Date']" in res.translations[10].python_code
        assert "right_on=['Last Quarter']" in res.translations[10].python_code
        unresolved = [d for d in res.translations[10].diagnostics if d.category == "unresolved_field"]
        assert len(unresolved) == 1
        assert "Last Quarter" in unresolved[0].message
        assert "Max_Quarter End Date" in unresolved[0].message


