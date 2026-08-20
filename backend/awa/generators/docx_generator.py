"""DOCX documentation generator — produces polished, business-facing workflow.docx.

Renders an executive-ready business report from the canonical DocumentModel,
including an embedded high-resolution visual DAG diagram, one-line business
summaries for each tool, data lineage, and configuration appendices.
"""

from __future__ import annotations

import io
import math
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

from awa.model.doc_model import DocumentModel
from awa.model.dag_layout import DagLayout
from awa.model.visual_category import get_category_colors

# Brand Colors
COLOR_PRIMARY_HEX = "EA580C"       # AWA Orange
COLOR_NAVY_HEX = "0F172A"          # Deep Slate / Navy
COLOR_SECONDARY_HEX = "1E293B"     # Slate 800
COLOR_MUTED_HEX = "64748B"         # Slate 500
COLOR_BG_LIGHT_HEX = "F8FAFC"      # Light background
COLOR_BORDER_HEX = "E2E8F0"        # Subtle border

RGB_PRIMARY = RGBColor(0xEA, 0x58, 0x0C)
RGB_NAVY = RGBColor(0x0F, 0x17, 0x2A)
RGB_MUTED = RGBColor(0x64, 0x74, 0x8B)
RGB_TEXT = RGBColor(0x1E, 0x29, 0x3B)
RGB_WHITE = RGBColor(0xFF, 0xFF, 0xFF)


def set_cell_background(cell, fill_hex: str) -> None:
    """Set background color of a table cell."""
    tc_pr = cell._element.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tc_pr.append(shd)


def set_cell_margins(cell, top: int = 100, bottom: int = 100, left: int = 150, right: int = 150) -> None:
    """Set inner cell padding in dxa (1 pt = 20 dxa)."""
    tc_pr = cell._element.get_or_add_tcPr()
    tc_mar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tc_pr.append(tc_mar)


def render_dag_image(layout: DagLayout, scale: float = 2.0) -> bytes:
    """Render the canonical DagLayout as a high-resolution raster PNG image.

    Args:
        layout: Canonical DAG layout.
        scale: Resolution multiplier for sharp print quality (default 2.0).

    Returns:
        PNG image bytes.
    """
    width = int(max(layout.width, 500.0) * scale)
    height = int(max(layout.height + 70.0, 280.0) * scale)

    img = Image.new("RGB", (width, height), color="#0d1326")
    draw = ImageDraw.Draw(img)

    # 1. Header Title
    title_text = f"Workflow DAG — {layout.title}"
    sub_text = f"{len(layout.nodes)} workflow tools · {len(layout.edges)} data connections"

    draw.text(
        (int(24 * scale), int(20 * scale)),
        title_text,
        fill="#f8fafc",
    )
    draw.text(
        (int(24 * scale), int(40 * scale)),
        sub_text,
        fill="#94a3b8",
    )

    offset_y = 50.0 * scale

    # 2. Render Edges with Arrowheads
    for edge in layout.edges:
        if not edge.path_points or len(edge.path_points) < 2:
            continue

        pts = [(int(p[0] * scale), int(p[1] * scale + offset_y)) for p in edge.path_points]
        has_label = bool(edge.source_anchor and edge.source_anchor not in ("Output", "0", "#1"))
        edge_color = "#38bdf8" if has_label else "#475569"

        # Draw line segments along waypoints
        for i in range(len(pts) - 1):
            draw.line([pts[i], pts[i + 1]], fill=edge_color, width=max(2, int(2 * scale)))

        # Draw arrowhead at the end point
        end_pt = pts[-1]
        prev_pt = pts[-2]
        dx = end_pt[0] - prev_pt[0]
        dy = end_pt[1] - prev_pt[1]
        angle = math.atan2(dy, dx)
        arrow_len = 10.0 * scale
        arrow_width = 5.0 * scale

        arrow_p1 = (
            int(end_pt[0] - arrow_len * math.cos(angle) + arrow_width * math.sin(angle)),
            int(end_pt[1] - arrow_len * math.sin(angle) - arrow_width * math.cos(angle)),
        )
        arrow_p2 = (
            int(end_pt[0] - arrow_len * math.cos(angle) - arrow_width * math.sin(angle)),
            int(end_pt[1] - arrow_len * math.sin(angle) + arrow_width * math.cos(angle)),
        )
        draw.polygon([end_pt, arrow_p1, arrow_p2], fill=edge_color)

        # Draw edge label badge if branching
        if has_label and len(pts) >= 2:
            mid_x = (pts[0][0] + pts[-1][0]) // 2
            mid_y = (pts[0][1] + pts[-1][1]) // 2 - int(8 * scale)
            badge_w = int(36 * scale)
            badge_h = int(14 * scale)
            draw.rounded_rectangle(
                [
                    mid_x - badge_w // 2,
                    mid_y - badge_h // 2,
                    mid_x + badge_w // 2,
                    mid_y + badge_h // 2,
                ],
                radius=int(3 * scale),
                fill="#0f172a",
                outline="#38bdf8",
                width=1,
            )
            draw.text(
                (mid_x - int(10 * scale), mid_y - int(5 * scale)),
                edge.source_anchor,
                fill="#38bdf8",
            )

    # 3. Render Nodes
    for node in layout.nodes:
        cat_color = get_category_colors(node.visual_category)

        nx = int(node.x * scale)
        ny = int(node.y * scale + offset_y)
        nw = int(node.width * scale)
        nh = int(node.height * scale)

        # Outer rounded box
        draw.rounded_rectangle(
            [nx, ny, nx + nw, ny + nh],
            radius=int(8 * scale),
            fill=cat_color["fill"],
            outline=cat_color["stroke"],
            width=max(2, int(1.5 * scale)),
        )

        # Tool ID circle badge
        cx = nx + int(24 * scale)
        cy = ny + nh // 2
        r = int(12 * scale)
        draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            fill=cat_color["stroke"],
            outline=None,
        )

        # Tool ID text
        id_str = str(node.tool_id)
        draw.text(
            (cx - int(4 * scale), cy - int(6 * scale)),
            id_str,
            fill="#0a0f1d",
        )

        # Tool Type Text
        type_display = node.tool_type if len(node.tool_type) <= 16 else node.tool_type[:14] + ".."
        draw.text(
            (nx + int(44 * scale), cy - int(10 * scale)),
            type_display,
            fill=cat_color["text"],
        )

        # Tool Name Subtitle
        label_display = node.label if len(node.label) <= 18 else node.label[:16] + ".."
        draw.text(
            (nx + int(44 * scale), cy + int(4 * scale)),
            label_display,
            fill="#94a3b8",
        )

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generate_docx(
    doc_model: DocumentModel,
    output_path: Path | str,
    svg_content: str | None = None,
) -> None:
    """Generate workflow.docx from a DocumentModel with an executive business structure.

    Args:
        doc_model: Canonical format-independent documentation model.
        output_path: Target path for the .docx file.
        svg_content: Optional SVG string.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = Document()

    # Configure Margins (1 inch all around)
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    # -------------------------------------------------------------
    # Cover Section / Document Header Banner
    # -------------------------------------------------------------
    p_brand = doc.add_paragraph()
    p_brand.paragraph_format.space_before = Pt(0)
    p_brand.paragraph_format.space_after = Pt(4)
    run_brand = p_brand.add_run("AWA — ALTERYX WORKFLOW ANALYZER")
    run_brand.font.size = Pt(9.5)
    run_brand.font.bold = True
    run_brand.font.color.rgb = RGB_PRIMARY

    p_title = doc.add_paragraph()
    p_title.paragraph_format.space_before = Pt(0)
    p_title.paragraph_format.space_after = Pt(6)
    workflow_name = doc_model.metadata.get("Workflow Name", "Alteryx Workflow")
    run_title = p_title.add_run(f"Workflow Analysis Report: {workflow_name}")
    run_title.font.size = Pt(22)
    run_title.font.bold = True
    run_title.font.color.rgb = RGB_NAVY

    p_subtitle = doc.add_paragraph()
    p_subtitle.paragraph_format.space_after = Pt(18)
    run_sub = p_subtitle.add_run("Business Process Specification, Tool Catalog & Data Lineage Documentation")
    run_sub.font.size = Pt(11)
    run_sub.font.color.rgb = RGB_MUTED

    # -------------------------------------------------------------
    # 1. Executive Summary & Properties
    # -------------------------------------------------------------
    h1 = doc.add_heading("1. Executive Summary", level=1)
    h1.paragraph_format.space_before = Pt(12)
    h1.paragraph_format.space_after = Pt(8)

    p_exec = doc.add_paragraph()
    p_exec.paragraph_format.space_after = Pt(10)
    total_tools = doc_model.metrics.get("Total Tools", len(doc_model.nodes))
    total_conns = doc_model.metrics.get("Total Connections", 0)
    inputs_count = doc_model.metrics.get("Data Inputs", 0)
    outputs_count = doc_model.metrics.get("Data Outputs", 0)
    
    p_exec.add_run(
        f"This report presents an automated structural analysis and business-level specification "
        f"for the '{workflow_name}' Alteryx workflow. The workflow comprises {total_tools} discrete "
        f"tools and {total_conns} data connections, executing from {inputs_count} source input(s) "
        f"to {outputs_count} destination output(s)."
    )

    # Summary Metrics Table
    summary_table = doc.add_table(rows=1, cols=4)
    summary_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    summary_table.autofit = False

    metrics_headers = ["Total Tools", "Connections", "Data Inputs", "Data Outputs"]
    metrics_values = [str(total_tools), str(total_conns), str(inputs_count), str(outputs_count)]

    # Header Row
    for idx, (cell, text) in enumerate(zip(summary_table.rows[0].cells, metrics_headers)):
        set_cell_background(cell, COLOR_NAVY_HEX)
        set_cell_margins(cell, top=120, bottom=120, left=140, right=140)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(text)
        run.font.size = Pt(10)
        run.font.bold = True
        run.font.color.rgb = RGB_WHITE

    # Values Row
    row_cells = summary_table.add_row().cells
    for idx, (cell, val) in enumerate(zip(row_cells, metrics_values)):
        set_cell_background(cell, COLOR_BG_LIGHT_HEX)
        set_cell_margins(cell, top=140, bottom=140, left=140, right=140)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(val)
        run.font.size = Pt(14)
        run.font.bold = True
        run.font.color.rgb = RGB_PRIMARY if idx == 0 else RGB_NAVY

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # Workflow Properties Table
    p_props = doc.add_paragraph()
    p_props.add_run("Workflow Properties").bold = True
    p_props.paragraph_format.space_after = Pt(6)

    prop_table = doc.add_table(rows=1, cols=2)
    prop_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr_cells = prop_table.rows[0].cells
    hdr_cells[0].text = "Attribute"
    hdr_cells[1].text = "Details"
    set_cell_background(hdr_cells[0], COLOR_SECONDARY_HEX)
    set_cell_background(hdr_cells[1], COLOR_SECONDARY_HEX)
    for c in hdr_cells:
        c.paragraphs[0].runs[0].font.bold = True
        c.paragraphs[0].runs[0].font.color.rgb = RGB_WHITE
        c.paragraphs[0].runs[0].font.size = Pt(10)
        set_cell_margins(c, top=100, bottom=100, left=140, right=140)

    for prop_name, prop_val in doc_model.metadata.items():
        row = prop_table.add_row().cells
        set_cell_background(row[0], COLOR_BG_LIGHT_HEX)
        set_cell_margins(row[0], top=80, bottom=80, left=140, right=140)
        set_cell_margins(row[1], top=80, bottom=80, left=140, right=140)
        r0 = row[0].paragraphs[0].add_run(str(prop_name))
        r0.font.bold = True
        r0.font.size = Pt(9.5)
        r1 = row[1].paragraphs[0].add_run(str(prop_val))
        r1.font.size = Pt(9.5)

    doc.add_paragraph().paragraph_format.space_after = Pt(14)

    # -------------------------------------------------------------
    # 2. Workflow at a Glance (DAG Diagram)
    # -------------------------------------------------------------
    h2 = doc.add_heading("2. Workflow at a Glance", level=1)
    h2.paragraph_format.space_before = Pt(14)
    h2.paragraph_format.space_after = Pt(8)

    p_dag_intro = doc.add_paragraph()
    p_dag_intro.add_run(
        "The following diagram illustrates the complete data-flow topology and transformation stages "
        "of the workflow:"
    )

    if doc_model.dag_layout.nodes:
        dag_png_bytes = render_dag_image(doc_model.dag_layout)
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_before = Pt(6)
        p_img.paragraph_format.space_after = Pt(4)
        doc.add_picture(io.BytesIO(dag_png_bytes), width=Inches(6.2))
        
        p_caption = doc.add_paragraph()
        p_caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_caption.paragraph_format.space_after = Pt(16)
        r_cap = p_caption.add_run(f"Figure 1: Workflow Execution Diagram — {workflow_name}")
        r_cap.font.size = Pt(9)
        r_cap.font.italic = True
        r_cap.font.color.rgb = RGB_MUTED
    else:
        doc.add_paragraph("No nodes present in workflow graph.")

    # -------------------------------------------------------------
    # 3. Workflow Steps (Execution Order with Business Summaries)
    # -------------------------------------------------------------
    h3 = doc.add_heading("3. Workflow Steps", level=1)
    h3.paragraph_format.space_before = Pt(14)
    h3.paragraph_format.space_after = Pt(8)

    doc.add_paragraph(
        "Each tool in the workflow executes in sequential data-flow order. The table and step breakdown "
        "below describe the business function performed at each stage:"
    )

    # Steps Summary Table
    steps_table = doc.add_table(rows=1, cols=4)
    steps_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    s_hdrs = ["Step", "Tool Name", "Tool Type", "Business Function"]
    for idx, (cell, text) in enumerate(zip(steps_table.rows[0].cells, s_hdrs)):
        set_cell_background(cell, COLOR_NAVY_HEX)
        set_cell_margins(cell, top=100, bottom=100, left=120, right=120)
        p = cell.paragraphs[0]
        run = p.add_run(text)
        run.font.bold = True
        run.font.color.rgb = RGB_WHITE
        run.font.size = Pt(9.5)

    for step in doc_model.execution_order:
        row = steps_table.add_row().cells
        set_cell_background(row[0], COLOR_BG_LIGHT_HEX)
        for c in row:
            set_cell_margins(c, top=80, bottom=80, left=120, right=120)
        
        p0 = row[0].paragraphs[0]
        p0.add_run(f"{step.step_number:02d}").bold = True
        p0.runs[0].font.size = Pt(9)

        p1 = row[1].paragraphs[0]
        p1.add_run(step.name).bold = True
        p1.runs[0].font.size = Pt(9)

        p2 = row[2].paragraphs[0]
        p2.add_run(step.tool_type)
        p2.runs[0].font.size = Pt(9)

        p3 = row[3].paragraphs[0]
        p3.add_run(step.summary or "Processes data in the workflow.")
        p3.runs[0].font.size = Pt(9)

    doc.add_paragraph().paragraph_format.space_after = Pt(14)

    # Detailed Step-by-Step Cards
    p_detail_hdr = doc.add_paragraph()
    p_detail_hdr.add_run("Step-by-Step Overview").bold = True
    p_detail_hdr.paragraph_format.space_after = Pt(8)

    for step in doc_model.execution_order:
        # Find corresponding node entry
        matching_node = next((n for n in doc_model.nodes if n.tool_id == step.tool_id), None)
        summary_text = step.summary or (matching_node.summary if matching_node else "Processes data in the workflow.")

        p_step = doc.add_paragraph()
        p_step.paragraph_format.space_before = Pt(8)
        p_step.paragraph_format.space_after = Pt(2)
        r_num = p_step.add_run(f"Step {step.step_number:02d}: ")
        r_num.bold = True
        r_num.font.color.rgb = RGB_PRIMARY
        r_num.font.size = Pt(11)

        r_name = p_step.add_run(f"{step.name} ")
        r_name.bold = True
        r_name.font.color.rgb = RGB_NAVY
        r_name.font.size = Pt(11)

        r_type = p_step.add_run(f"({step.tool_type})")
        r_type.font.color.rgb = RGB_MUTED
        r_type.font.size = Pt(10)

        p_desc = doc.add_paragraph()
        p_desc.paragraph_format.left_indent = Inches(0.25)
        p_desc.paragraph_format.space_after = Pt(6)
        r_what = p_desc.add_run("What it does: ")
        r_what.bold = True
        r_what.font.size = Pt(9.5)
        r_summary = p_desc.add_run(summary_text)
        r_summary.font.size = Pt(9.5)

        if matching_node and matching_node.annotation:
            p_ann = doc.add_paragraph()
            p_ann.paragraph_format.left_indent = Inches(0.25)
            p_ann.paragraph_format.space_after = Pt(6)
            r_ann_lbl = p_ann.add_run("Annotation: ")
            r_ann_lbl.italic = True
            r_ann_lbl.font.size = Pt(9)
            r_ann_txt = p_ann.add_run(matching_node.annotation)
            r_ann_txt.font.size = Pt(9)

    doc.add_paragraph().paragraph_format.space_after = Pt(14)

    # -------------------------------------------------------------
    # 4. Data Flow & Lineage Paths
    # -------------------------------------------------------------
    h4 = doc.add_heading("4. Data Flow & Lineage Paths", level=1)
    h4.paragraph_format.space_before = Pt(14)
    h4.paragraph_format.space_after = Pt(8)

    doc.add_paragraph(
        "Data lineage tracks the complete progression of records from source inputs through intermediate "
        "transformations to terminal outputs:"
    )

    if doc_model.lineage_paths:
        for idx, lp in enumerate(doc_model.lineage_paths, start=1):
            p_lineage = doc.add_paragraph(style="List Bullet")
            p_lineage.paragraph_format.space_after = Pt(4)
            path_str = "  ➔  ".join(
                f"{name}" for name in lp.tool_names
            )
            r_path = p_lineage.add_run(f"Path {idx}: {path_str}")
            r_path.font.size = Pt(9.5)
    else:
        doc.add_paragraph("No source-to-destination lineage paths detected.")

    doc.add_paragraph().paragraph_format.space_after = Pt(14)

    # -------------------------------------------------------------
    # 5. Inputs, Outputs & External Dependencies
    # -------------------------------------------------------------
    h5 = doc.add_heading("5. Inputs, Outputs & Data Dependencies", level=1)
    h5.paragraph_format.space_before = Pt(14)
    h5.paragraph_format.space_after = Pt(8)

    if doc_model.dependencies:
        dep_table = doc.add_table(rows=1, cols=3)
        dep_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        d_hdrs = ["Category", "File / Database Reference", "Associated Tool"]
        for cell, text in zip(dep_table.rows[0].cells, d_hdrs):
            set_cell_background(cell, COLOR_NAVY_HEX)
            set_cell_margins(cell, top=100, bottom=100, left=120, right=120)
            p = cell.paragraphs[0]
            run = p.add_run(text)
            run.font.bold = True
            run.font.color.rgb = RGB_WHITE
            run.font.size = Pt(9.5)

        for dep in doc_model.dependencies:
            row = dep_table.add_row().cells
            set_cell_background(row[0], COLOR_BG_LIGHT_HEX)
            for c in row:
                set_cell_margins(c, top=80, bottom=80, left=120, right=120)
            
            p0 = row[0].paragraphs[0]
            p0.add_run(str(dep.dep_type).capitalize())
            p0.runs[0].font.size = Pt(9)

            p1 = row[1].paragraphs[0]
            p1.add_run(str(dep.reference))
            p1.runs[0].font.size = Pt(9)

            p2 = row[2].paragraphs[0]
            matching = next((s for s in doc_model.execution_order if s.tool_id == dep.tool_id), None)
            tool_label = f"{matching.name} (#{dep.tool_id})" if matching else (f"Tool #{dep.tool_id}" if dep.tool_id else "Workflow")
            p2.add_run(tool_label)
            p2.runs[0].font.size = Pt(9)
    else:
        doc.add_paragraph("No external file, database, or network dependencies referenced in this workflow.")

    doc.add_paragraph().paragraph_format.space_after = Pt(14)

    # -------------------------------------------------------------
    # 6. Technical Configuration Appendix
    # -------------------------------------------------------------
    h6 = doc.add_heading("6. Technical Configuration Appendix", level=1)
    h6.paragraph_format.space_before = Pt(16)
    h6.paragraph_format.space_after = Pt(8)

    doc.add_paragraph(
        "This appendix documents the parsed configuration parameters for each workflow tool for technical review:"
    )

    for node in doc_model.nodes:
        p_node_title = doc.add_paragraph()
        p_node_title.paragraph_format.space_before = Pt(10)
        p_node_title.paragraph_format.space_after = Pt(4)
        r_nh = p_node_title.add_run(f"Tool #{node.tool_id} — {node.name} ({node.tool_type})")
        r_nh.bold = True
        r_nh.font.size = Pt(10.5)
        r_nh.font.color.rgb = RGB_NAVY

        # Configuration Table
        if node.configuration:
            cfg_table = doc.add_table(rows=1, cols=2)
            cfg_table.alignment = WD_TABLE_ALIGNMENT.CENTER
            c_hdr = cfg_table.rows[0].cells
            c_hdr[0].text = "Parameter"
            c_hdr[1].text = "Value"
            set_cell_background(c_hdr[0], COLOR_SECONDARY_HEX)
            set_cell_background(c_hdr[1], COLOR_SECONDARY_HEX)
            for c in c_hdr:
                c.paragraphs[0].runs[0].font.bold = True
                c.paragraphs[0].runs[0].font.color.rgb = RGB_WHITE
                c.paragraphs[0].runs[0].font.size = Pt(9)
                set_cell_margins(c, top=80, bottom=80, left=100, right=100)

            for k, v in sorted(node.configuration.items()):
                val_str = str(v) if not isinstance(v, (dict, list)) else str(v)[:120]
                row = cfg_table.add_row().cells
                set_cell_background(row[0], COLOR_BG_LIGHT_HEX)
                set_cell_margins(row[0], top=60, bottom=60, left=100, right=100)
                set_cell_margins(row[1], top=60, bottom=60, left=100, right=100)
                r0 = row[0].paragraphs[0].add_run(str(k))
                r0.font.size = Pt(8.5)
                r1 = row[1].paragraphs[0].add_run(val_str)
                r1.font.size = Pt(8.5)
        else:
            p_none = doc.add_paragraph()
            p_none.paragraph_format.left_indent = Inches(0.2)
            p_none.add_run("No custom parameters configured.").italic = True
            p_none.runs[0].font.size = Pt(8.5)

    doc.save(str(output_path))
