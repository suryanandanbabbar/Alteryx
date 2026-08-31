"""Python generator — assembles translations into workflow.py.

Generates only consumed branches and provides line-level source mapping.
"""

from __future__ import annotations

from pathlib import Path

from awa.model.workflow import Workflow
from awa.model.translation import TranslationResult
from awa.model.python_trace import PythonTraceEntry, PythonTraceMap
from awa.tools.catalog import get_tool_catalog


def append_multiline_comment(lines: list[str], message: object, prefix: str = "#") -> None:
    """Safely append a potentially multiline message as valid Python comments line-by-line.

    Handles:
    - None or non-string values
    - Embedded newlines (\n, \r\n, \r)
    - Blank lines (rendered cleanly as '#')
    - Indented text or tracebacks
    - Unicode characters
    """
    if message is None:
        return
    text = str(message)
    if not text:
        return
    for line in text.splitlines():
        line_clean = line.rstrip("\r\n")
        if line_clean.strip():
            lines.append(f"{prefix} {line_clean}")
        else:
            lines.append(prefix)


def generate_python_code(
    workflow: Workflow,
    execution_order: list[int],
    translations: dict[int, TranslationResult],
    consumed: dict[int, set[str]],
) -> tuple[str, PythonTraceMap, list[str]]:
    """Assemble generated Python code and compute line-level traceability map.

    Args:
        workflow: Canonical Workflow IR.
        execution_order: Tool IDs in topological order.
        translations: Translation results keyed by tool_id.
        consumed: Consumed anchors per tool.

    Returns:
        tuple of (generated_python_code_str, PythonTraceMap, required_libraries_list)
    """
    lines: list[str] = []
    catalog = get_tool_catalog()

    # File Header
    clean_wf_name = (workflow.metadata.name or "Workflow").replace("\n", " ").replace("\r", " ")
    lines.append('"""')
    lines.append(f"Auto-generated Python translation of Alteryx workflow '{clean_wf_name}'.")
    lines.append('"""')
    lines.append("")

    # Collect all imports
    all_imports: set[str] = set()
    for tid in execution_order:
        if tid in translations:
            all_imports.update(translations[tid].imports)

    # Write imports
    for imp in sorted(all_imports):
        lines.append(imp)
    if all_imports:
        lines.append("")

    # Detect required external libraries strictly from generated imports
    required_libs: set[str] = set()
    for imp in all_imports:
        if "pandas" in imp:
            required_libs.add("pandas")
        elif "numpy" in imp:
            required_libs.add("numpy")
        elif "openpyxl" in imp:
            required_libs.add("openpyxl")
        elif "pyarrow" in imp:
            required_libs.add("pyarrow")
    required_libraries = sorted(required_libs)

    # Track trace entries
    trace_entries: list[PythonTraceEntry] = []

    # Write each tool in execution order
    for tid in execution_order:
        tool = workflow.tools.get(tid)
        tr = translations.get(tid)
        if tool is None or tr is None:
            continue

        tool_def = catalog.resolve(tool.plugin or tool.tool_type)

        # Traceability header
        lines.append("")
        start_line = len(lines) + 1  # 1-indexed, starts at the tool comment header
        name_part = f" ({tool.name})" if tool.name and tool.name != tool.tool_type else ""
        append_multiline_comment(lines, f"Alteryx Tool #{tool.tool_id}: {tool.tool_type}{name_part}")
        append_multiline_comment(lines, f"Plugin: {tool.plugin or tool_def.xml_name}")
        append_multiline_comment(lines, f"Translation: {tr.support_level.name}")
        if tr.description:
            append_multiline_comment(lines, tr.description)

        # Add diagnostic notes safely line-by-line
        for diag in tr.diagnostics:
            append_multiline_comment(lines, f"{diag.level.value.upper()}: {diag.message}")

        # Code block
        code = tr.python_code
        for code_line in code.split("\n"):
            lines.append(code_line)

        end_line = len(lines)

        # Extract tool libraries
        tool_libs = []
        for imp in tr.imports:
            if "pandas" in imp:
                tool_libs.append("pandas")
            elif "numpy" in imp:
                tool_libs.append("numpy")
            elif "openpyxl" in imp:
                tool_libs.append("openpyxl")
        tool_libs = sorted(set(tool_libs))

        trace_entries.append(
            PythonTraceEntry(
                tool_id=tool.tool_id,
                tool_type=tool.tool_type,
                tool_name=tool.name or tool.tool_type,
                start_line=start_line,
                end_line=end_line,
                description=tr.description or f"{tool.tool_type} operation",
                pandas_op=tr.description or f"pandas {tool.tool_type.lower()}",
                reason=f"Deterministic {tool.tool_type} translation ({tr.support_level.value})",
                libraries=tool_libs,
            )
        )

    # Ensure single trailing newline
    full_code = "\n".join(lines).rstrip() + "\n"

    # Strictly validate that the emitted Python is 100% syntactically valid
    import ast
    try:
        ast.parse(full_code)
    except (SyntaxError, IndentationError) as e:
        lineno = e.lineno or 1
        all_lines = full_code.splitlines()
        ctx_start = max(1, lineno - 3)
        ctx_end = min(len(all_lines), lineno + 3)
        nearby_lines = []
        for i in range(ctx_start, ctx_end + 1):
            marker = ">>>" if i == lineno else "   "
            content = all_lines[i - 1] if i - 1 < len(all_lines) else ""
            nearby_lines.append(f"{marker} {i:4d} | {content}")
        context_block = "\n".join(nearby_lines)

        origin_tool = "unknown tool"
        for te in trace_entries:
            if te.start_line <= lineno <= te.end_line:
                origin_tool = f"Tool #{te.tool_id} ({te.tool_type}: {te.tool_name})"
                break

        msg = (
            f"Generated Python contains {type(e).__name__} at line {lineno} "
            f"(originating from {origin_tool}): {e.msg}\n"
            f"Offending line: {repr(e.text or (all_lines[lineno - 1] if lineno <= len(all_lines) else ''))}\n"
            f"Nearby code context:\n{context_block}"
        )
        raise SyntaxError(msg) from e

    # Calculate exact total_lines from final string
    total_lines = len(full_code.splitlines())
    trace_map = PythonTraceMap(entries=trace_entries, total_lines=total_lines)

    return full_code, trace_map, required_libraries


def generate_python(
    workflow: Workflow,
    execution_order: list[int],
    translations: dict[int, TranslationResult],
    consumed: dict[int, set[str]],
    output_path: Path,
) -> tuple[str, PythonTraceMap, list[str]]:
    """Generate workflow.py and write to disk, returning the code, trace map, and libraries."""
    code, trace_map, required_libs = generate_python_code(
        workflow, execution_order, translations, consumed
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(code)

    return code, trace_map, required_libs
