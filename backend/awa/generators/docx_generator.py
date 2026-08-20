"""Business-oriented DOCX report generator for AWA.

Generates a publication-quality Executive Business Analysis Report (.docx)
with an executive business assessment on page 1, process flow, inputs, deliverables,
key business rules, source-to-target lineage, governance assessment,
embedded DAG diagram, tool specifications (business action first),
and technical configuration appendix.

LLM-free and 100% deterministic.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any
from PIL import Image, ImageDraw

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls

from awa.model.doc_model import DocumentModel
from awa.model.dag_layout import DagLayout
from awa.model.visual_category import get_category_colors


# Brand Color Palette
COLOR_NAVY_HEX = "0f172a"
COLOR_PRIMARY_HEX = "ea580c"
COLOR_SECONDARY_HEX = "1e293b"
COLOR_BORDER_HEX = "cbd5e1"
COLOR_BG_LIGHT_HEX = "f8fafc"
COLOR_MUTED_HEX = "64748b"

RGB_NAVY = RGBColor(15, 23, 42)
RGB_PRIMARY = RGBColor(234, 88, 12)
RGB_MUTED = RGBColor(100, 116, 139)
RGB_DARK = RGBColor(30, 41, 59)
RGB_WHITE = RGBColor(255, 255, 255)


def set_cell_background(cell: Any, fill_hex: str) -> None:
    """Set background color of a table cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:val="clear" w:color="auto" w:fill="{fill_hex}"/>')
    tcPr.append(shd)


def set_cell_margins(cell: Any, top: int = 100, bottom: int = 100, left: int = 150, right: int = 150) -> None:
    """Set inner cell padding in dxa (1 pt = 20 dxa)."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in (('w:top', top), ('w:bottom', bottom), ('w:left', left), ('w:right', right)):
        node = OxmlElement(m)
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)


def render_dag_to_png(layout: DagLayout, scale: float = 1.0) -> bytes:
    """Render the DagLayout into a high-resolution PNG image for DOCX embedding."""
    width = int(max(layout.width, 400.0) * scale)
    height = int(max(layout.height + 60.0, 260.0) * scale)

    img = Image.new("RGB", (width, height), color="#0d1326")
    draw = ImageDraw.Draw(img)

    # Header Text
    draw.text(
        (int(20 * scale), int(16 * scale)),
        f"Alteryx Workflow DAG — {layout.title}",
        fill="#f8fafc",
    )
    draw.text(
        (int(20 * scale), int(34 * scale)),
        f"{len(layout.nodes)} workflow tools · {len(layout.edges)} data connections",
        fill="#94a3b8",
    )

    y_offset = int(45 * scale)

    # Draw Edges
    for edge in layout.edges:
        if not edge.path_points or len(edge.path_points) < 2:
            continue
        pts = [(int(p[0] * scale), int(p[1] * scale + y_offset)) for p in edge.path_points]
        has_label = bool(edge.source_anchor and edge.source_anchor not in ("Output", "0", "#1"))
        edge_color = "#38bdf8" if has_label else "#64748b"

        for i in range(len(pts) - 1):
            draw.line([pts[i], pts[i + 1]], fill=edge_color, width=max(1, int(1.5 * scale)))

    # Draw Nodes
    for node in layout.nodes:
        cat_color = get_category_colors(node.visual_category)
        nx = int(node.x * scale)
        ny = int(node.y * scale + y_offset)
        nw = int(node.width * scale)
        nh = int(node.height * scale)

        # Card body
        draw.rounded_rectangle(
            [nx, ny, nx + nw, ny + nh],
            radius=int(6 * scale),
            fill=cat_color["fill"],
            outline=cat_color["stroke"],
            width=max(1, int(1.5 * scale)),
        )

        # Badge circle
        cx = nx + int(20 * scale)
        cy = ny + int(nh / 2)
        r = int(10 * scale)
        draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            fill=cat_color["stroke"],
            outline=cat_color["stroke"],
        )

        id_str = str(node.tool_id)
        draw.text(
            (cx - int(4 * scale), cy - int(6 * scale)),
            id_str,
            fill="#0a0f1d",
        )

        # Tool Type Text
        type_display = node.tool_type if len(node.tool_type) <= 16 else node.tool_type[:14] + ".."
        draw.text(
            (nx + int(36 * scale), cy - int(10 * scale)),
            type_display,
            fill=cat_color["text"],
        )

        # Tool Name Subtitle
        label_display = node.label if len(node.label) <= 18 else node.label[:16] + ".."
        draw.text(
            (nx + int(36 * scale), cy + int(4 * scale)),
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
    """Generate workflow.docx with an Executive Business Analysis structure.

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

    workflow_name = doc_model.metadata.get("Workflow Name", "Alteryx Workflow")
    bs = doc_model.business_summary
    assessment = bs.assessment if bs else None

    # -------------------------------------------------------------
    # Cover Section / Document Header Banner
    # -------------------------------------------------------------
    p_brand = doc.add_paragraph()
    p_brand.paragraph_format.space_before = Pt(0)
    p_brand.paragraph_format.space_after = Pt(2)
    run_brand = p_brand.add_run("AWA — ALTERYX WORKFLOW ANALYZER")
    run_brand.font.size = Pt(9)
    run_brand.font.bold = True
    run_brand.font.color.rgb = RGB_PRIMARY

    p_title = doc.add_paragraph()
    p_title.paragraph_format.space_before = Pt(0)
    p_title.paragraph_format.space_after = Pt(4)
    run_title = p_title.add_run(f"WORKFLOW BUSINESS ASSESSMENT\n{workflow_name}")
    run_title.font.size = Pt(20)
    run_title.font.bold = True
    run_title.font.color.rgb = RGB_NAVY

    p_subtitle = doc.add_paragraph()
    p_subtitle.paragraph_format.space_after = Pt(14)
    one_line = bs.one_line_purpose if bs and bs.one_line_purpose else "Data preparation and business reporting workflow"
    run_sub = p_subtitle.add_run(one_line)
    run_sub.font.size = Pt(11)
    run_sub.font.color.rgb = RGB_MUTED

    # -------------------------------------------------------------
    # 1. Executive Business Assessment (Page 1 Target)
    # -------------------------------------------------------------
    h1 = doc.add_heading("1. Executive Summary & Assessment", level=1)
    h1.paragraph_format.space_before = Pt(8)
    h1.paragraph_format.space_after = Pt(6)

    # 1.1 Workflow at a Glance
    p_glance_hdr = doc.add_paragraph()
    p_glance_hdr.paragraph_format.space_after = Pt(3)
    r_gh = p_glance_hdr.add_run("Workflow at a Glance")
    r_gh.bold = True
    r_gh.font.color.rgb = RGB_NAVY
    r_gh.font.size = Pt(10.5)

    glance_table = doc.add_table(rows=1, cols=2)
    glance_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    g_hdr = glance_table.rows[0].cells
    g_hdr[0].text = "Dimension"
    g_hdr[1].text = "Workflow Status / Value"
    set_cell_background(g_hdr[0], COLOR_NAVY_HEX)
    set_cell_background(g_hdr[1], COLOR_NAVY_HEX)
    for c in g_hdr:
        c.paragraphs[0].runs[0].font.bold = True
        c.paragraphs[0].runs[0].font.color.rgb = RGB_WHITE
        c.paragraphs[0].runs[0].font.size = Pt(8.5)
        set_cell_margins(c, top=60, bottom=60, left=90, right=90)

    total_tools = doc_model.metrics.get("Total Tools", len(doc_model.nodes))
    total_conns = doc_model.metrics.get("Total Connections", 0)
    input_count = len(bs.source_inputs) if bs and bs.source_inputs else doc_model.metrics.get("Data Inputs", 0)
    output_count = len(bs.business_outputs) if bs and bs.business_outputs else doc_model.metrics.get("Data Outputs", 0)
    stage_count = len(bs.processing_stages) if bs and bs.processing_stages else 0

    glance_rows = [
        ("Business Purpose", bs.business_purpose if bs else one_line),
        ("Workflow Scale", f"{total_tools} Tools  |  {total_conns} Data Connections"),
        ("Source Data Inputs", f"{input_count} upstream input source(s)"),
        ("Business Outputs", f"{output_count} published reporting deliverable(s)"),
        ("Operational Stages", f"{stage_count} processing stage(s)"),
        ("Business Owner", assessment.business_owner if assessment else "Not documented"),
        ("Schedule / Frequency", assessment.schedule if assessment else "Not documented"),
        ("Operational Criticality", assessment.criticality if assessment else "Not documented"),
        ("Documentation Quality", assessment.documentation_quality if assessment else "Partially documented"),
    ]

    for dim, val in glance_rows:
        row = glance_table.add_row().cells
        set_cell_background(row[0], COLOR_BG_LIGHT_HEX)
        set_cell_margins(row[0], top=50, bottom=50, left=90, right=90)
        set_cell_margins(row[1], top=50, bottom=50, left=90, right=90)

        p0 = row[0].paragraphs[0]
        p0.add_run(dim).bold = True
        p0.runs[0].font.size = Pt(8.5)

        p1 = row[1].paragraphs[0]
        p1.add_run(str(val))
        p1.runs[0].font.size = Pt(8.5)
        if val == "Not documented":
            p1.runs[0].font.italic = True
            p1.runs[0].font.color.rgb = RGB_MUTED

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # 1.2 Business Purpose
    p_purp_hdr = doc.add_paragraph()
    p_purp_hdr.paragraph_format.space_after = Pt(2)
    r_ph = p_purp_hdr.add_run("Business Purpose")
    r_ph.bold = True
    r_ph.font.color.rgb = RGB_NAVY
    r_ph.font.size = Pt(10.5)

    p_purp = doc.add_paragraph()
    p_purp.paragraph_format.space_after = Pt(8)
    if bs and bs.business_purpose:
        p_purp.add_run(bs.business_purpose)
    else:
        p_purp.add_run(f"Ingests source records, applies validation and transformation rules, and publishes reporting datasets.")

    # 1.3 Why the Workflow Matters
    p_why_hdr = doc.add_paragraph()
    p_why_hdr.paragraph_format.space_after = Pt(2)
    r_wh = p_why_hdr.add_run("Why the Workflow Matters")
    r_wh.bold = True
    r_wh.font.color.rgb = RGB_NAVY
    r_wh.font.size = Pt(10.5)

    p_why = doc.add_paragraph()
    p_why.paragraph_format.space_after = Pt(8)
    if assessment and assessment.why_it_matters:
        p_why.add_run(assessment.why_it_matters)
    else:
        p_why.add_run(
            "Business value is not explicitly documented; the assessment is derived from workflow inputs, transformations, and outputs."
        )

    # 1.4 High-Level Process Flow Box (WHAT GOES IN → WHAT HAPPENS → WHAT COMES OUT)
    p_flow_hdr = doc.add_paragraph()
    p_flow_hdr.paragraph_format.space_after = Pt(3)
    r_fh = p_flow_hdr.add_run("What Goes In  ➔  What Happens  ➔  What Comes Out")
    r_fh.bold = True
    r_fh.font.color.rgb = RGB_NAVY
    r_fh.font.size = Pt(10.5)

    flow_box = doc.add_table(rows=1, cols=3)
    flow_box.alignment = WD_TABLE_ALIGNMENT.CENTER
    fb_cells = flow_box.rows[0].cells
    set_cell_background(fb_cells[0], COLOR_BG_LIGHT_HEX)
    set_cell_background(fb_cells[1], COLOR_BG_LIGHT_HEX)
    set_cell_background(fb_cells[2], COLOR_BG_LIGHT_HEX)
    for c in fb_cells:
        set_cell_margins(c, top=80, bottom=80, left=100, right=100)

    # In Col
    p_in = fb_cells[0].paragraphs[0]
    p_in.add_run("SOURCES\n").bold = True
    p_in.runs[0].font.size = Pt(9)
    p_in.runs[0].font.color.rgb = RGB_PRIMARY
    if bs and bs.source_inputs:
        for inp in bs.source_inputs:
            p_in.add_run(f"• {inp.name}\n").font.size = Pt(8)

    # Process Col
    p_pr = fb_cells[1].paragraphs[0]
    p_pr.add_run("CORE PROCESSING\n").bold = True
    p_pr.runs[0].font.size = Pt(9)
    p_pr.runs[0].font.color.rgb = RGB_PRIMARY
    if bs and bs.processing_stages:
        for stg in bs.processing_stages[:4]:
            p_pr.add_run(f"• {stg.name}\n").font.size = Pt(8)

    # Out Col
    p_ou = fb_cells[2].paragraphs[0]
    p_ou.add_run("DELIVERABLES\n").bold = True
    p_ou.runs[0].font.size = Pt(9)
    p_ou.runs[0].font.color.rgb = RGB_PRIMARY
    if bs and bs.business_outputs:
        for out in bs.business_outputs:
            p_ou.add_run(f"• {out.name}\n").font.size = Pt(8)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # 1.5 Key Business Activities
    if assessment and assessment.key_activities:
        p_act_hdr = doc.add_paragraph()
        p_act_hdr.paragraph_format.space_after = Pt(2)
        r_ah = p_act_hdr.add_run("Key Business Activities")
        r_ah.bold = True
        r_ah.font.color.rgb = RGB_NAVY
        r_ah.font.size = Pt(10.5)

        for act in assessment.key_activities:
            p_act = doc.add_paragraph(style='List Bullet')
            p_act.paragraph_format.space_after = Pt(2)
            r_a = p_act.add_run(act)
            r_a.font.size = Pt(9)

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # 1.6 Key Observations
    if assessment and assessment.key_observations:
        p_obs_hdr = doc.add_paragraph()
        p_obs_hdr.paragraph_format.space_after = Pt(2)
        r_oh = p_obs_hdr.add_run("Key Observations")
        r_oh.bold = True
        r_oh.font.color.rgb = RGB_NAVY
        r_oh.font.size = Pt(10.5)

        for obs in assessment.key_observations:
            p_obs = doc.add_paragraph(style='List Bullet')
            p_obs.paragraph_format.space_after = Pt(2)
            r_o = p_obs.add_run(obs)
            r_o.font.size = Pt(9)

    doc.add_paragraph().paragraph_format.space_after = Pt(14)

    # -------------------------------------------------------------
    # 2. Inputs & Target Business Deliverables
    # -------------------------------------------------------------
    h2 = doc.add_heading("2. Inputs & Target Business Deliverables", level=1)
    h2.paragraph_format.space_before = Pt(14)
    h2.paragraph_format.space_after = Pt(6)

    # 2.1 What Goes In (Source Data Ingestion)
    p_in_hdr = doc.add_paragraph()
    p_in_hdr.paragraph_format.space_after = Pt(3)
    r_ih = p_in_hdr.add_run("What Goes In (Source Data Ingestion)")
    r_ih.bold = True
    r_ih.font.color.rgb = RGB_NAVY
    r_ih.font.size = Pt(10.5)

    if bs and bs.source_inputs:
        in_table = doc.add_table(rows=1, cols=3)
        in_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        in_hdr = in_table.rows[0].cells
        in_hdr[0].text = "Source Dataset"
        in_hdr[1].text = "Type / Format"
        in_hdr[2].text = "Business Role"

        for c in in_hdr:
            set_cell_background(c, COLOR_SECONDARY_HEX)
            c.paragraphs[0].runs[0].font.bold = True
            c.paragraphs[0].runs[0].font.color.rgb = RGB_WHITE
            c.paragraphs[0].runs[0].font.size = Pt(8.5)
            set_cell_margins(c, top=70, bottom=70, left=90, right=90)

        for inp in bs.source_inputs:
            row = in_table.add_row().cells
            set_cell_background(row[0], COLOR_BG_LIGHT_HEX)
            for c in row:
                set_cell_margins(c, top=60, bottom=60, left=90, right=90)

            p0 = row[0].paragraphs[0]
            p0.add_run(inp.name).bold = True
            p0.runs[0].font.size = Pt(8.5)

            p1 = row[1].paragraphs[0]
            p1.add_run(inp.source_type)
            p1.runs[0].font.size = Pt(8.5)

            p2 = row[2].paragraphs[0]
            p2.add_run(inp.business_role or inp.description or "Source input stream.")
            p2.runs[0].font.size = Pt(8.5)

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # 2.2 What Comes Out (Business Reporting Deliverables)
    p_out_hdr = doc.add_paragraph()
    p_out_hdr.paragraph_format.space_after = Pt(3)
    r_oh = p_out_hdr.add_run("What Comes Out (Business Reporting Deliverables)")
    r_oh.bold = True
    r_oh.font.color.rgb = RGB_NAVY
    r_oh.font.size = Pt(10.5)

    if bs and bs.business_outputs:
        out_table = doc.add_table(rows=1, cols=3)
        out_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        out_hdr = out_table.rows[0].cells
        out_hdr[0].text = "Output Deliverable"
        out_hdr[1].text = "Business Meaning"
        out_hdr[2].text = "Likely Use"

        for c in out_hdr:
            set_cell_background(c, COLOR_NAVY_HEX)
            c.paragraphs[0].runs[0].font.bold = True
            c.paragraphs[0].runs[0].font.color.rgb = RGB_WHITE
            c.paragraphs[0].runs[0].font.size = Pt(8.5)
            set_cell_margins(c, top=70, bottom=70, left=90, right=90)

        for out in bs.business_outputs:
            row = out_table.add_row().cells
            set_cell_background(row[0], COLOR_BG_LIGHT_HEX)
            for c in row:
                set_cell_margins(c, top=60, bottom=60, left=90, right=90)

            p0 = row[0].paragraphs[0]
            p0.add_run(out.name).bold = True
            p0.runs[0].font.size = Pt(8.5)

            p1 = row[1].paragraphs[0]
            p1.add_run(out.business_meaning or out.business_purpose)
            p1.runs[0].font.size = Pt(8.5)

            p2 = row[2].paragraphs[0]
            p2.add_run(out.likely_use or "Use not documented")
            p2.runs[0].font.size = Pt(8.5)
            if out.likely_use == "Use not documented":
                p2.runs[0].font.italic = True
                p2.runs[0].font.color.rgb = RGB_MUTED

    doc.add_paragraph().paragraph_format.space_after = Pt(14)

    # -------------------------------------------------------------
    # 3. What the Workflow Does (Business Process & Stages)
    # -------------------------------------------------------------
    h3 = doc.add_heading("3. What the Workflow Does (Business Process Stages)", level=1)
    h3.paragraph_format.space_before = Pt(14)
    h3.paragraph_format.space_after = Pt(6)

    if bs and bs.processing_stages:
        for stg in bs.processing_stages:
            p_stg = doc.add_paragraph()
            p_stg.paragraph_format.space_before = Pt(4)
            p_stg.paragraph_format.space_after = Pt(2)
            r_snum = p_stg.add_run(f"{stg.stage_number}. {stg.name}: ")
            r_snum.bold = True
            r_snum.font.color.rgb = RGB_NAVY
            r_snum.font.size = Pt(9.5)

            r_sdesc = p_stg.add_run(f"{stg.summary or stg.description}. ")
            r_sdesc.font.size = Pt(9.5)

            p_detail = doc.add_paragraph()
            p_detail.paragraph_format.left_indent = Inches(0.25)
            p_detail.paragraph_format.space_after = Pt(6)
            r_trans = p_detail.add_run(f"Transformation: {stg.major_transformation or stg.business_purpose}")
            r_trans.font.size = Pt(8.5)
            r_trans.font.color.rgb = RGB_MUTED

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # -------------------------------------------------------------
    # 4. Key Business Rules
    # -------------------------------------------------------------
    h4 = doc.add_heading("4. Key Business Rules", level=1)
    h4.paragraph_format.space_before = Pt(14)
    h4.paragraph_format.space_after = Pt(6)

    doc.add_paragraph(
        "The following business rules and operational derivations have been extracted directly from workflow tool configurations and annotations:"
    )

    if bs and bs.business_rules:
        rules_table = doc.add_table(rows=1, cols=3)
        rules_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        r_hdr = rules_table.rows[0].cells
        r_hdr[0].text = "Business Rule"
        r_hdr[1].text = "Category"
        r_hdr[2].text = "Evidence / Source Tool"

        for c in r_hdr:
            set_cell_background(c, COLOR_SECONDARY_HEX)
            c.paragraphs[0].runs[0].font.bold = True
            c.paragraphs[0].runs[0].font.color.rgb = RGB_WHITE
            c.paragraphs[0].runs[0].font.size = Pt(8.5)
            set_cell_margins(c, top=70, bottom=70, left=90, right=90)

        for rule in bs.business_rules:
            row = rules_table.add_row().cells
            set_cell_background(row[0], COLOR_BG_LIGHT_HEX)
            for c in row:
                set_cell_margins(c, top=60, bottom=60, left=90, right=90)

            p0 = row[0].paragraphs[0]
            p0.add_run(rule.description).bold = True
            p0.runs[0].font.size = Pt(8.5)

            p1 = row[1].paragraphs[0]
            p1.add_run(rule.category)
            p1.runs[0].font.size = Pt(8.5)

            p2 = row[2].paragraphs[0]
            p2.add_run(rule.evidence)
            p2.runs[0].font.size = Pt(8.5)

    doc.add_paragraph().paragraph_format.space_after = Pt(14)

    # -------------------------------------------------------------
    # 5. Source-to-Target Data Lineage
    # -------------------------------------------------------------
    h5 = doc.add_heading("5. Source-to-Target Data Lineage", level=1)
    h5.paragraph_format.space_before = Pt(14)
    h5.paragraph_format.space_after = Pt(6)

    doc.add_paragraph(
        "The following matrix maps source datasets through intermediate transformation operations to finalized published deliverables:"
    )

    if bs and bs.lineage:
        lin_table = doc.add_table(rows=1, cols=3)
        lin_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        l_hdr = lin_table.rows[0].cells
        l_hdr[0].text = "Source Dataset"
        l_hdr[1].text = "Transformation Operation"
        l_hdr[2].text = "Target Deliverable"

        for c in l_hdr:
            set_cell_background(c, COLOR_NAVY_HEX)
            c.paragraphs[0].runs[0].font.bold = True
            c.paragraphs[0].runs[0].font.color.rgb = RGB_WHITE
            c.paragraphs[0].runs[0].font.size = Pt(8.5)
            set_cell_margins(c, top=70, bottom=70, left=90, right=90)

        for lin in bs.lineage:
            row = lin_table.add_row().cells
            set_cell_background(row[0], COLOR_BG_LIGHT_HEX)
            for c in row:
                set_cell_margins(c, top=60, bottom=60, left=90, right=90)

            p0 = row[0].paragraphs[0]
            p0.add_run(lin.source_name).bold = True
            p0.runs[0].font.size = Pt(8.5)

            p1 = row[1].paragraphs[0]
            p1.add_run(lin.transformation or lin.transformation_summary)
            p1.runs[0].font.size = Pt(8.5)

            p2 = row[2].paragraphs[0]
            p2.add_run(lin.target_name).bold = True
            p2.runs[0].font.size = Pt(8.5)

    doc.add_paragraph().paragraph_format.space_after = Pt(14)

    # -------------------------------------------------------------
    # 6. Initial Complexity & Governance Assessment
    # -------------------------------------------------------------
    h6 = doc.add_heading("6. Initial Complexity & Governance Assessment", level=1)
    h6.paragraph_format.space_before = Pt(14)
    h6.paragraph_format.space_after = Pt(6)

    if assessment:
        p_c = doc.add_paragraph()
        p_c.add_run("Overall Complexity: ").bold = True
        p_c.add_run(f"{assessment.complexity}\n")
        p_c.add_run("Rationale: ").bold = True
        p_c.add_run(f"{assessment.complexity_reason}\n")
        p_c.paragraph_format.space_after = Pt(6)

        p_cf = doc.add_paragraph()
        p_cf.add_run("Complexity Drivers:").bold = True
        p_cf.paragraph_format.space_after = Pt(2)
        for f in assessment.complexity_factors:
            p_f = doc.add_paragraph(style='List Bullet')
            p_f.paragraph_format.space_after = Pt(2)
            p_f.add_run(f).font.size = Pt(9)

    doc.add_paragraph().paragraph_format.space_after = Pt(14)

    # -------------------------------------------------------------
    # 7. Visual Workflow Graph (DAG Architecture)
    # -------------------------------------------------------------
    h7 = doc.add_heading("7. Visual Workflow Graph (DAG)", level=1)
    h7.paragraph_format.space_before = Pt(14)
    h7.paragraph_format.space_after = Pt(6)

    doc.add_paragraph(
        "The following diagram illustrates the complete directed acyclic graph (DAG) representing all "
        "data flows, transformation nodes, and execution branches across the workflow:"
    )

    try:
        png_bytes = render_dag_to_png(doc_model.dag_layout, scale=1.5)
        image_stream = io.BytesIO(png_bytes)
        doc.add_picture(image_stream, width=Inches(6.5))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    except Exception as e:
        doc.add_paragraph(f"[Graph rendering note: DAG preview could not be generated: {e}]")

    doc.add_paragraph().paragraph_format.space_after = Pt(14)

    # -------------------------------------------------------------
    # 8. Step-by-Step Tool Specifications (Business Action First)
    # -------------------------------------------------------------
    h8 = doc.add_heading("8. Step-by-Step Tool Specifications", level=1)
    h8.paragraph_format.space_before = Pt(16)
    h8.paragraph_format.space_after = Pt(6)

    doc.add_paragraph(
        "This section documents each workflow execution step in topological sequence, detailing the "
        "business action and operational function of every individual tool:"
    )

    for step in doc_model.execution_order:
        matching_node = next((n for n in doc_model.nodes if n.tool_id == step.tool_id), None)
        annotation_text = matching_node.annotation if matching_node and matching_node.annotation else ""
        technical_summary = step.summary or (matching_node.summary if matching_node else "Processes records in the workflow pipeline.")

        # Business action priority: Annotation or synthesized action
        business_action = annotation_text or f"Executes {step.tool_type} operation in the data pipeline."

        p_step = doc.add_paragraph()
        p_step.paragraph_format.space_before = Pt(8)
        p_step.paragraph_format.space_after = Pt(2)
        r_num = p_step.add_run(f"Step {step.step_number:02d}: ")
        r_num.bold = True
        r_num.font.color.rgb = RGB_PRIMARY
        r_num.font.size = Pt(10)

        r_name = p_step.add_run(f"{step.name} ")
        r_name.bold = True
        r_name.font.color.rgb = RGB_NAVY
        r_name.font.size = Pt(10)

        r_type = p_step.add_run(f"({step.tool_type})")
        r_type.font.color.rgb = RGB_MUTED
        r_type.font.size = Pt(9)

        if step.container_name:
            r_cont = p_step.add_run(f"  [Container: {step.container_name}]")
            r_cont.font.color.rgb = RGB_MUTED
            r_cont.font.size = Pt(8.5)
            r_cont.font.italic = True

        p_desc = doc.add_paragraph()
        p_desc.paragraph_format.left_indent = Inches(0.25)
        p_desc.paragraph_format.space_after = Pt(2)
        r_ba = p_desc.add_run("Business Action: ")
        r_ba.bold = True
        r_ba.font.size = Pt(9)
        r_bat = p_desc.add_run(business_action)
        r_bat.font.size = Pt(9)

        p_tech = doc.add_paragraph()
        p_tech.paragraph_format.left_indent = Inches(0.25)
        p_tech.paragraph_format.space_after = Pt(4)
        r_ta = p_tech.add_run("Technical Function: ")
        r_ta.italic = True
        r_ta.font.size = Pt(8.5)
        r_ta.font.color.rgb = RGB_MUTED
        r_tat = p_tech.add_run(technical_summary)
        r_tat.font.size = Pt(8.5)
        r_tat.font.color.rgb = RGB_MUTED

    doc.add_paragraph().paragraph_format.space_after = Pt(14)

    # -------------------------------------------------------------
    # 9. Technical Configuration Appendix
    # -------------------------------------------------------------
    h9 = doc.add_heading("9. Technical Configuration Appendix", level=1)
    h9.paragraph_format.space_before = Pt(16)
    h9.paragraph_format.space_after = Pt(6)

    doc.add_paragraph(
        "This appendix documents the parsed configuration parameters for each workflow tool for engineering review:"
    )

    for node in doc_model.nodes:
        p_node_title = doc.add_paragraph()
        p_node_title.paragraph_format.space_before = Pt(10)
        p_node_title.paragraph_format.space_after = Pt(4)
        cont_str = f" [Container: {node.container_name}]" if node.container_name else ""
        r_nh = p_node_title.add_run(f"Tool #{node.tool_id} — {node.name} ({node.tool_type}){cont_str}")
        r_nh.bold = True
        r_nh.font.size = Pt(9.5)
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
                c.paragraphs[0].runs[0].font.size = Pt(8.5)
                set_cell_margins(c, top=50, bottom=50, left=80, right=80)

            for key, val in node.configuration.items():
                r_cells = cfg_table.add_row().cells
                set_cell_background(r_cells[0], COLOR_BG_LIGHT_HEX)
                for c in r_cells:
                    set_cell_margins(c, top=50, bottom=50, left=80, right=80)

                pk = r_cells[0].paragraphs[0]
                pk.add_run(str(key))
                pk.runs[0].font.size = Pt(8.5)
                pk.runs[0].font.bold = True

                pv = r_cells[1].paragraphs[0]
                val_str = str(val) if not isinstance(val, (dict, list)) else str(val)[:120]
                pv.add_run(val_str)
                pv.runs[0].font.size = Pt(8.5)

    doc.save(str(output_path))
