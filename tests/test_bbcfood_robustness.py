"""Regression tests for YXMD pipeline hardening and BBCFood v2 workflow robustness.

Covers:
1. Multiline diagnostics in generated Python (indentation & AST safety)
2. String expressions: Trim, LTrim, RTrim, Upper, Lower, Length, etc. with bare & bracketed fields
3. External/dynamic schema propagation (no false 'field missing' warnings)
4. Known missing field validation (genuine missing fields correctly flagged)
5. Arbitrary multiline diagnostics helper (tabs, carets, blank lines, tracebacks, Unicode)
6. Full end-to-end regression on BBCFood v2.yxmd upload & DTO generation
"""

import ast
from pathlib import Path
import pytest

from awa.analysis.workflow_analyzer import analyze_canonical
from awa.expressions.pandas_emitter import emit_pandas
from awa.generators.python_generator import append_multiline_comment, generate_python_code
from awa.model.diagnostic import Diagnostic, DiagnosticLevel, SupportLevel
from awa.model.tool import Tool, ToolConfiguration
from awa.model.translation import TranslationResult
from awa.model.workflow import Workflow, WorkflowMetadata
from backend.app.services.analyzer import process_uploaded_workflow, to_overview_dto


def test_append_multiline_comment_arbitrary_content():
    """Test append_multiline_comment with carets, tabs, blank lines, tracebacks, Unicode, None."""
    lines: list[str] = ["# Header line"]

    # None and empty
    append_multiline_comment(lines, None)
    append_multiline_comment(lines, "")

    # Normal one-line
    append_multiline_comment(lines, "Simple message")

    # Multiline with carets, tabs, and blank lines
    lark_error = (
        "Failed to translate formula expression for 'Title': No terminal matches ')'\n"
        "\n"
        "Trim(Title)\n"
        "          ^\n"
        "Expected one of:\n"
        "\t* LPAR\n"
    )
    append_multiline_comment(lines, lark_error)

    # Traceback snippet with indentation
    tb_snippet = (
        "Traceback (most recent call last):\n"
        "  File 'analyzer.py', line 120, in parse\n"
        "    return evaluate(node)\n"
        "ValueError: invalid literal for int() with base 10: 'abc'"
    )
    append_multiline_comment(lines, tb_snippet)

    # Unicode characters
    append_multiline_comment(lines, "Unicode check: café, résumé, 🚀, ñoño, 中文")

    # Verify every appended line starts with '#' or is a clean comment
    for line in lines:
        assert line.startswith("#"), f"Line does not start with '#': {repr(line)}"

    # When embedded in valid Python, AST parsing must succeed
    code = "\n".join(lines) + "\nx = 1\n"
    parsed_ast = ast.parse(code)
    assert parsed_ast is not None


def test_multiline_diagnostics_in_generated_python():
    """Verify that multiline messages on translation results do not break AST validation."""
    tool = Tool(
        tool_id=1,
        plugin="AlteryxBasePluginsGui.Formula.Formula",
        tool_type="Formula",
        name="TestFormula",
        position=None,
        configuration=ToolConfiguration(raw_xml="", parsed={}),
    )
    workflow = Workflow(
        metadata=WorkflowMetadata(name="DiagnosticTest", version="2021.1"),
        tools={1: tool},
        connections=[],
    )

    tr = TranslationResult(
        tool_id=1,
        tool_type="Formula",
        support_level=SupportLevel.PARTIAL,
        python_code="df_1 = pd.DataFrame({'a': [1, 2, 3]})\ndf_1['b'] = None",
        imports={"import pandas as pd"},
        input_variables=[],
        output_map={"Output": "df_1"},
        diagnostics=[
            Diagnostic(
                level=DiagnosticLevel.ERROR,
                category="expression_error",
                tool_id=1,
                tool_type="Formula",
                message=(
                    "Expression error in Title:\n"
                    "Trim(Title)\n"
                    "     ^\n"
                    "IndentationError: unexpected indent\n"
                    "\tExpected one of: LPAR"
                ),
            )
        ],
        description="Formula with\nmultiple description\nlines\n\tand tabs",
    )

    code, trace_map, libs = generate_python_code(
        workflow=workflow,
        execution_order=[1],
        translations={1: tr},
        consumed={},
    )

    # Must parse without SyntaxError or IndentationError
    parsed = ast.parse(code)
    assert parsed is not None
    assert trace_map.total_lines == len(code.splitlines())


def test_trim_and_string_expressions_handling():
    """Verify Trim and related string functions translate correctly with bare and bracketed fields."""
    # 1. Bare field Trim
    code1, _ = emit_pandas("Trim(Title)")
    assert code1 == 'df["Title"].str.strip()'

    # 2. Bracketed field Trim
    code2, _ = emit_pandas("Trim([Title])")
    assert code2 == 'df["Title"].str.strip()'

    # 3. Trim with custom characters
    code3, _ = emit_pandas('Trim([Title], " #")')
    assert code3 == 'df["Title"].str.strip(" #")'

    # 4. LTrim / RTrim
    code_l, _ = emit_pandas("LTrim(Chef)")
    assert code_l == 'df["Chef"].str.lstrip()'
    code_r, _ = emit_pandas("RTrim(Chef)")
    assert code_r == 'df["Chef"].str.rstrip()'

    # 5. Upper / Lower / TitleCase / Length
    code_u, _ = emit_pandas("Upper(Title)")
    assert code_u == 'df["Title"].str.upper()'
    code_low, _ = emit_pandas("Lower(Title)")
    assert code_low == 'df["Title"].str.lower()'
    code_len, _ = emit_pandas("Length(Title)")
    assert code_len == 'df["Title"].str.len()'

    # 6. Left / Right / Substring / Replace
    code_left, _ = emit_pandas("Left(Title, 5)")
    assert code_left == 'df["Title"].str[:int(5)]'
    code_sub, _ = emit_pandas("Substring(Title, 1, 4)")
    assert "df[\"Title\"].str[int(1)-1:int(1)-1+int(4)]" in code_sub


def test_unknown_external_schema_propagation():
    """Verify that external/dynamic schemas do not produce false 'unresolved_field' warnings."""
    bbcfood_path = Path("BBCFood v2.yxmd")
    if not bbcfood_path.exists():
        pytest.skip("BBCFood v2.yxmd not found in workspace")

    res = analyze_canonical(bbcfood_path)

    # Tool #9 and Tool #37 should NOT have unresolved_field warnings
    tool9_diags = [
        d for d in res.diagnostics
        if d.tool_id == 9 and d.category == "unresolved_field"
    ]
    tool37_diags = [
        d for d in res.diagnostics
        if d.tool_id == 37 and d.category == "unresolved_field"
    ]
    assert len(tool9_diags) == 0, f"False missing field warnings in Tool #9: {tool9_diags}"
    assert len(tool37_diags) == 0, f"False missing field warnings in Tool #37: {tool37_diags}"


def test_known_missing_field_validation():
    """Verify that genuine missing fields in closed known schemas still raise diagnostics."""
    tool_select = Tool(
        tool_id=99,
        plugin="AlteryxBasePluginsGui.AlteryxSelect.AlteryxSelect",
        tool_type="AlteryxSelect",
        name="Select",
        position=None,
        configuration=ToolConfiguration(
            raw_xml="",
            parsed={
                "select_fields": [
                    {"field": "NonExistentColumn", "selected": "True"},
                ]
            },
        ),
    )
    workflow = Workflow(
        metadata=WorkflowMetadata(name="TestKnownMissing", version="2021.1"),
        tools={99: tool_select},
        connections=[],
    )
    # Stream schema is explicitly closed without NonExistentColumn
    workflow._stream_schemas = {"df_input": ["KnownCol1", "KnownCol2"]}
    workflow._unknown_schema_streams = set()

    from awa.translators.select import SelectTranslator
    tr = SelectTranslator().translate(tool_select, ["df_input"], workflow)

    unresolved = [d for d in tr.diagnostics if d.category == "unresolved_field"]
    assert len(unresolved) >= 1
    assert "NonExistentColumn" in unresolved[0].message


def test_bbcfood_v2_regression_end_to_end():
    """Full end-to-end regression: BBCFood v2.yxmd parses, validates AST, and generates DTOs."""
    bbcfood_path = Path("BBCFood v2.yxmd")
    if not bbcfood_path.exists():
        pytest.skip("BBCFood v2.yxmd not found in workspace")

    content = bbcfood_path.read_bytes()

    # 1. process_uploaded_workflow succeeds (no HTTP 500)
    res = process_uploaded_workflow("BBCFood v2.yxmd", content)
    assert res is not None
    assert res.workflow.metadata.name == "BBCFood v2"
    assert len(res.workflow.tools) == 44

    # 2. Formula translations for Title and Chef succeeded with SupportLevel.FULL
    tr11 = res.translations.get(11)
    assert tr11 is not None
    assert tr11.support_level == SupportLevel.FULL
    assert 'df_11["Title"] = df_11["Title"].str.strip()' in tr11.python_code

    tr39 = res.translations.get(39)
    assert tr39 is not None
    assert tr39.support_level == SupportLevel.FULL
    assert 'df_39["Chef"] = df_39["Chef"].str.strip()' in tr39.python_code

    # 3. Python code AST validation passes
    assert res.python_trace is not None
    assert res.python_trace.total_lines > 0

    # 4. Overview DTO generation succeeds
    dto = to_overview_dto(res)
    assert dto is not None
    assert dto.metadata.name == "BBCFood v2"
    assert dto.metrics.total_nodes == 44
