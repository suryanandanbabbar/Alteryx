"""Business-oriented DOCX report generator for AWA.

Generates a publication-quality Executive Business Assessment (.docx)
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


# Brand Color Palette (Corporate Consulting Style)
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


def set_cell_margins(cell: Any, top: int = 80, bottom: int = 80, left: int = 120, right: int = 120) -> None:
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
    """Generate workflow.docx with a comprehensive Executive Business Assessment structure.

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
    run_title = p_title.add_run(f"EXECUTIVE BUSINESS ASSESSMENT\n{workflow_name}")
    run_title.font.size = Pt(20)
    run_title.font.bold = True
    run_title.font.color.rgb = RGB_NAVY

    p_subtitle = doc.add_paragraph()
    p_subtitle.paragraph_format.space_after = Pt(14)
    one_line = bs.one_line_purpose if bs and bs.one_line_purpose else "Data preparation and business reporting workflow"
    run_sub = p_subtitle.add_run(one_line)
    run_sub.font.size = Pt(11)
    run_sub.font.color.rgb = RGB_MUTED

    # =============================================================
    # SECTION 1: EXECUTIVE BUSINESS ASSESSMENT
    # =============================================================
    h1 = doc.add_heading("1. Executive Business Assessment", level=1)
    h1.paragraph_format.space_before = Pt(8)
    h1.paragraph_format.space_after = Pt(6)

    # 1.1 Workflow at a Glance
    p_glance_hdr = doc.add_paragraph()
    p_glance_hdr.paragraph_format.space_after = Pt(3)
    r_gh = p_glance_hdr.add_run("1.1 Workflow at a Glance")
    r_gh.bold = True
    r_gh.font.color.rgb = RGB_NAVY
    r_gh.font.size = Pt(10.5)

    glance_table = doc.add_table(rows=1, cols=2)
    glance_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    g_hdr = glance_table.rows[0].cells
    g_hdr[0].text = "Dimension"
    g_hdr[1].text = "Workflow Status / Detail"
    set_cell_background(g_hdr[0], COLOR_NAVY_HEX)
    set_cell_background(g_hdr[1], COLOR_NAVY_HEX)
    for c in g_hdr:
        c.paragraphs[0].runs[0].font.bold = True
        c.paragraphs[0].runs[0].font.color.rgb = RGB_WHITE
        c.paragraphs[0].runs[0].font.size = Pt(8.5)
        set_cell_margins(c, top=60, bottom=60, left=90, right=90)

    input_count = len(bs.source_inputs) if bs and bs.source_inputs else doc_model.metrics.get("Data Inputs", 0)
    output_count = len(bs.business_outputs) if bs and bs.business_outputs else doc_model.metrics.get("Data Outputs", 0)

    glance_rows = [
        ("Workflow Name", workflow_name),
        ("Business Purpose", bs.business_purpose if bs else one_line),
        ("Platform", assessment.platform if assessment else "Alteryx Designer"),
        ("Source Data Inputs", f"{input_count} upstream source dataset(s)"),
        ("Business Outputs", f"{output_count} published reporting deliverable(s)"),
        ("Business Owner", assessment.business_owner if assessment else "Not documented"),
        ("Frequency / Schedule", assessment.schedule if assessment else "Not documented"),
        ("Operational Criticality", assessment.criticality if assessment else "Not documented"),
        ("Assessment Status", assessment.assessment_status if assessment else "Automated assessment"),
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
    r_ph = p_purp_hdr.add_run("1.2 Business Purpose")
    r_ph.bold = True
    r_ph.font.color.rgb = RGB_NAVY
    r_ph.font.size = Pt(10.5)

    p_purp = doc.add_paragraph()
    p_purp.paragraph_format.space_after = Pt(8)
    if bs and bs.business_purpose:
        p_purp.add_run(bs.business_purpose)
    else:
        p_purp.add_run(
            "The workflow ingests source operational records, applies business transformation "
            "and enrichment rules, and publishes consolidated reporting datasets."
        )

    # 1.3 Business Process
    p_proc_hdr = doc.add_paragraph()
    p_proc_hdr.paragraph_format.space_after = Pt(2)
    r_prh = p_proc_hdr.add_run("1.3 Business Process")
    r_prh.bold = True
    r_prh.font.color.rgb = RGB_NAVY
    r_prh.font.size = Pt(10.5)

    p_proc_desc = doc.add_paragraph()
    p_proc_desc.paragraph_format.space_after = Pt(4)
    p_proc_desc.add_run(
        "The workflow executes a sequential multi-stage business process, moving from source data ingestion "
        "through cross-source reconciliation and multi-dimensional reporting deliverable generation:"
    )

    if bs and bs.processing_stages:
        for stg in bs.processing_stages:
            p_stg = doc.add_paragraph()
            p_stg.paragraph_format.left_indent = Inches(0.2)
            p_stg.paragraph_format.space_after = Pt(3)
            r_num = p_stg.add_run(f"Stage {stg.stage_number:02d} — {stg.name}: ")
            r_num.bold = True
            r_num.font.size = Pt(8.5)
            r_num.font.color.rgb = RGB_NAVY

            r_desc = p_stg.add_run(f"{stg.summary or stg.description}. ")
            r_desc.font.size = Pt(8.5)

            if stg.major_transformation:
                r_t = p_stg.add_run(f"({stg.major_transformation})")
                r_t.font.size = Pt(8.0)
                r_t.font.color.rgb = RGB_MUTED
                r_t.font.italic = True

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # 1.4 Inputs & Dependencies
    p_in_hdr = doc.add_paragraph()
    p_in_hdr.paragraph_format.space_after = Pt(3)
    r_ih = p_in_hdr.add_run("1.4 Inputs & Dependencies")
    r_ih.bold = True
    r_ih.font.color.rgb = RGB_NAVY
    r_ih.font.size = Pt(10.5)

    if bs and bs.source_inputs:
        in_table = doc.add_table(rows=1, cols=4)
        in_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        in_hdr = in_table.rows[0].cells
        in_hdr[0].text = "Source Dataset"
        in_hdr[1].text = "Business Role"
        in_hdr[2].text = "Source Format"
        in_hdr[3].text = "Dependency Significance"

        for c in in_hdr:
            set_cell_background(c, COLOR_SECONDARY_HEX)
            c.paragraphs[0].runs[0].font.bold = True
            c.paragraphs[0].runs[0].font.color.rgb = RGB_WHITE
            c.paragraphs[0].runs[0].font.size = Pt(8.0)
            set_cell_margins(c, top=60, bottom=60, left=80, right=80)

        for inp in bs.source_inputs:
            row = in_table.add_row().cells
            set_cell_background(row[0], COLOR_BG_LIGHT_HEX)
            for c in row:
                set_cell_margins(c, top=50, bottom=50, left=80, right=80)

            p0 = row[0].paragraphs[0]
            p0.add_run(inp.name).bold = True
            p0.runs[0].font.size = Pt(8.0)

            p1 = row[1].paragraphs[0]
            p1.add_run(inp.business_role or inp.description or "Source input stream")
            p1.runs[0].font.size = Pt(8.0)

            p2 = row[2].paragraphs[0]
            p2.add_run(inp.source_type)
            p2.runs[0].font.size = Pt(8.0)

            p3 = row[3].paragraphs[0]
            p3.add_run(getattr(inp, "dependency_significance", "Primary source input required for downstream processing"))
            p3.runs[0].font.size = Pt(8.0)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # 1.5 Outputs & Business Use
    p_out_hdr = doc.add_paragraph()
    p_out_hdr.paragraph_format.space_after = Pt(3)
    r_oh = p_out_hdr.add_run("1.5 Outputs & Business Use")
    r_oh.bold = True
    r_oh.font.color.rgb = RGB_NAVY
    r_oh.font.size = Pt(10.5)

    if bs and bs.business_outputs:
        out_table = doc.add_table(rows=1, cols=4)
        out_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        out_hdr = out_table.rows[0].cells
        out_hdr[0].text = "Output Deliverable"
        out_hdr[1].text = "What it Represents"
        out_hdr[2].text = "Business Use"
        out_hdr[3].text = "Destination Format"

        for c in out_hdr:
            set_cell_background(c, COLOR_NAVY_HEX)
            c.paragraphs[0].runs[0].font.bold = True
            c.paragraphs[0].runs[0].font.color.rgb = RGB_WHITE
            c.paragraphs[0].runs[0].font.size = Pt(8.0)
            set_cell_margins(c, top=60, bottom=60, left=80, right=80)

        for out in bs.business_outputs:
            row = out_table.add_row().cells
            set_cell_background(row[0], COLOR_BG_LIGHT_HEX)
            for c in row:
                set_cell_margins(c, top=50, bottom=50, left=80, right=80)

            p0 = row[0].paragraphs[0]
            p0.add_run(out.name).bold = True
            p0.runs[0].font.size = Pt(8.0)

            p1 = row[1].paragraphs[0]
            p1.add_run(out.business_meaning or out.business_purpose)
            p1.runs[0].font.size = Pt(8.0)

            p2 = row[2].paragraphs[0]
            use_val = out.likely_use if out.likely_use and out.likely_use != "Use not documented" else "Business use: Not documented"
            p2.add_run(use_val)
            p2.runs[0].font.size = Pt(8.0)
            if "Not documented" in use_val:
                p2.runs[0].font.italic = True
                p2.runs[0].font.color.rgb = RGB_MUTED

            p3 = row[3].paragraphs[0]
            p3.add_run(out.destination_type)
            p3.runs[0].font.size = Pt(8.0)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # 1.6 Business Lineage
    p_lin_hdr = doc.add_paragraph()
    p_lin_hdr.paragraph_format.space_after = Pt(3)
    r_lh = p_lin_hdr.add_run("1.6 Business Lineage (Impact Mapping)")
    r_lh.bold = True
    r_lh.font.color.rgb = RGB_NAVY
    r_lh.font.size = Pt(10.5)

    if bs and bs.lineage:
        lin_table = doc.add_table(rows=1, cols=3)
        lin_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        l_hdr = lin_table.rows[0].cells
        l_hdr[0].text = "Source Dataset(s)"
        l_hdr[1].text = "Major Business Transformation"
        l_hdr[2].text = "Target Deliverable"

        for c in l_hdr:
            set_cell_background(c, COLOR_SECONDARY_HEX)
            c.paragraphs[0].runs[0].font.bold = True
            c.paragraphs[0].runs[0].font.color.rgb = RGB_WHITE
            c.paragraphs[0].runs[0].font.size = Pt(8.0)
            set_cell_margins(c, top=60, bottom=60, left=80, right=80)

        for lin in bs.lineage:
            row = lin_table.add_row().cells
            set_cell_background(row[0], COLOR_BG_LIGHT_HEX)
            for c in row:
                set_cell_margins(c, top=50, bottom=50, left=80, right=80)

            p0 = row[0].paragraphs[0]
            p0.add_run(lin.source_name).bold = True
            p0.runs[0].font.size = Pt(8.0)

            p1 = row[1].paragraphs[0]
            p1.add_run(lin.transformation or lin.transformation_summary)
            p1.runs[0].font.size = Pt(8.0)

            p2 = row[2].paragraphs[0]
            p2.add_run(lin.target_name).bold = True
            p2.runs[0].font.size = Pt(8.0)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # 1.7 Business Role & Value
    p_rv_hdr = doc.add_paragraph()
    p_rv_hdr.paragraph_format.space_after = Pt(2)
    r_rvh = p_rv_hdr.add_run("1.7 Business Role & Value")
    r_rvh.bold = True
    r_rvh.font.color.rgb = RGB_NAVY
    r_rvh.font.size = Pt(10.5)

    role_values = getattr(assessment, "role_and_value", []) if assessment else []
    if not role_values and assessment and assessment.why_it_matters:
        role_values = [assessment.why_it_matters]

    for rv in role_values:
        p_rv = doc.add_paragraph(style='List Bullet')
        p_rv.paragraph_format.space_after = Pt(2)
        r_rv = p_rv.add_run(rv)
        r_rv.font.size = Pt(8.5)

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # 1.8 Key Findings
    p_fnd_hdr = doc.add_paragraph()
    p_fnd_hdr.paragraph_format.space_after = Pt(2)
    r_fndh = p_fnd_hdr.add_run("1.8 Key Findings")
    r_fndh.bold = True
    r_fndh.font.color.rgb = RGB_NAVY
    r_fndh.font.size = Pt(10.5)

    findings = getattr(assessment, "key_findings", []) if assessment else []
    if not findings and assessment and assessment.key_observations:
        findings = assessment.key_observations

    for fnd in findings:
        p_f = doc.add_paragraph(style='List Bullet')
        p_f.paragraph_format.space_after = Pt(2)
        r_f = p_f.add_run(fnd)
        r_f.font.size = Pt(8.5)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # 1.9 Assessment Gaps
    p_gap_hdr = doc.add_paragraph()
    p_gap_hdr.paragraph_format.space_after = Pt(3)
    r_gaph = p_gap_hdr.add_run("1.9 Assessment Gaps (Unestablished Facts)")
    r_gaph.bold = True
    r_gaph.font.color.rgb = RGB_NAVY
    r_gaph.font.size = Pt(10.5)

    gaps = getattr(assessment, "assessment_gaps", []) if assessment else []
    if gaps:
        gap_table = doc.add_table(rows=1, cols=3)
        gap_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        gp_hdr = gap_table.rows[0].cells
        gp_hdr[0].text = "Governance & Operational Dimension"
        gp_hdr[1].text = "Workflow Status"
        gp_hdr[2].text = "Validation Action Required"

        for c in gp_hdr:
            set_cell_background(c, COLOR_NAVY_HEX)
            c.paragraphs[0].runs[0].font.bold = True
            c.paragraphs[0].runs[0].font.color.rgb = RGB_WHITE
            c.paragraphs[0].runs[0].font.size = Pt(8.0)
            set_cell_margins(c, top=60, bottom=60, left=80, right=80)

        for gap in gaps:
            row = gap_table.add_row().cells
            set_cell_background(row[0], COLOR_BG_LIGHT_HEX)
            for c in row:
                set_cell_margins(c, top=50, bottom=50, left=80, right=80)

            p0 = row[0].paragraphs[0]
            p0.add_run(gap.get("dimension", "")).bold = True
            p0.runs[0].font.size = Pt(8.0)

            p1 = row[1].paragraphs[0]
            status_txt = gap.get("status", "Not documented")
            p1.add_run(status_txt)
            p1.runs[0].font.size = Pt(8.0)
            if status_txt == "Not documented":
                p1.runs[0].font.italic = True
                p1.runs[0].font.color.rgb = RGB_MUTED

            p2 = row[2].paragraphs[0]
            p2.add_run(gap.get("action", "Confirm with business owner"))
            p2.runs[0].font.size = Pt(8.0)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # 1.10 Preliminary Disposition
    p_disp_hdr = doc.add_paragraph()
    p_disp_hdr.paragraph_format.space_after = Pt(2)
    r_disph = p_disp_hdr.add_run("1.10 Preliminary Disposition")
    r_disph.bold = True
    r_disph.font.color.rgb = RGB_NAVY
    r_disph.font.size = Pt(10.5)

    disp_val = getattr(assessment, "preliminary_disposition", "Further assessment required") if assessment else "Further assessment required"
    disp_rat = getattr(assessment, "disposition_rationale", "") if assessment else ""

    p_disp = doc.add_paragraph()
    p_disp.paragraph_format.space_after = Pt(4)
    r_dv = p_disp.add_run(f"Recommendation: {disp_val}\n")
    r_dv.bold = True
    r_dv.font.size = Pt(9.0)
    r_dv.font.color.rgb = RGB_PRIMARY

    r_dr = p_disp.add_run(f"Rationale: {disp_rat}")
    r_dr.font.size = Pt(8.5)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # 1.11 Business Validation Required
    p_val_hdr = doc.add_paragraph()
    p_val_hdr.paragraph_format.space_after = Pt(3)
    r_valh = p_val_hdr.add_run("1.11 Business Validation Required")
    r_valh.bold = True
    r_valh.font.color.rgb = RGB_NAVY
    r_valh.font.size = Pt(10.5)

    p_val_intro = doc.add_paragraph()
    p_val_intro.paragraph_format.space_after = Pt(4)
    p_val_intro.add_run(
        "Automated static workflow analysis confirms the technical structure and derived business flow, "
        "but cannot reliably establish organizational governance. The following items require formal business stakeholder confirmation:"
    )

    checklist_items = getattr(assessment, "validation_checklist", []) if assessment else []
    if not checklist_items:
        checklist_items = [
            "Business Owner: Confirm",
            "Frequency / Schedule: Confirm",
            "Criticality: Confirm",
            "Downstream Consumers: Confirm",
            "Current Usage: Confirm",
            "Redundancy / Duplicate Flow: Confirm",
            "Business Value: Confirm",
            "Final Disposition: Confirm",
        ]

    val_table = doc.add_table(rows=1, cols=3)
    val_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    v_hdr = val_table.rows[0].cells
    v_hdr[0].text = "Validation Dimension"
    v_hdr[1].text = "Action Description"
    v_hdr[2].text = "Status / Sign-off"

    for c in v_hdr:
        set_cell_background(c, COLOR_SECONDARY_HEX)
        c.paragraphs[0].runs[0].font.bold = True
        c.paragraphs[0].runs[0].font.color.rgb = RGB_WHITE
        c.paragraphs[0].runs[0].font.size = Pt(8.0)
        set_cell_margins(c, top=60, bottom=60, left=80, right=80)

    for item in checklist_items:
        dim_name = item.split(":")[0].strip() if ":" in item else item
        row = val_table.add_row().cells
        set_cell_background(row[0], COLOR_BG_LIGHT_HEX)
        for c in row:
            set_cell_margins(c, top=50, bottom=50, left=80, right=80)

        p0 = row[0].paragraphs[0]
        p0.add_run(dim_name).bold = True
        p0.runs[0].font.size = Pt(8.0)

        p1 = row[1].paragraphs[0]
        p1.add_run(f"Confirm and validate {dim_name.lower()} with designated business owner")
        p1.runs[0].font.size = Pt(8.0)

        p2 = row[2].paragraphs[0]
        p2.add_run("[  ] Pending Validation")
        p2.runs[0].font.size = Pt(8.0)
        p2.runs[0].font.color.rgb = RGB_MUTED

    doc.add_paragraph().paragraph_format.space_after = Pt(16)

    # =============================================================
    # SECTION 2: VISUAL WORKFLOW GRAPH (DAG)
    # =============================================================
    h2 = doc.add_heading("2. Visual Workflow Graph (DAG Architecture)", level=1)
    h2.paragraph_format.space_before = Pt(16)
    h2.paragraph_format.space_after = Pt(6)

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

    doc.add_paragraph().paragraph_format.space_after = Pt(16)

    # =============================================================
    # SECTION 3: STEP-BY-STEP TOOL SPECIFICATIONS
    # =============================================================
    h3 = doc.add_heading("3. Step-by-Step Tool Specifications", level=1)
    h3.paragraph_format.space_before = Pt(16)
    h3.paragraph_format.space_after = Pt(6)

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
        r_num.font.size = Pt(9.5)

        r_name = p_step.add_run(f"{step.name} ")
        r_name.bold = True
        r_name.font.color.rgb = RGB_NAVY
        r_name.font.size = Pt(9.5)

        r_type = p_step.add_run(f"({step.tool_type})")
        r_type.font.color.rgb = RGB_MUTED
        r_type.font.size = Pt(8.5)

        if step.container_name:
            r_cont = p_step.add_run(f"  [Container: {step.container_name}]")
            r_cont.font.color.rgb = RGB_MUTED
            r_cont.font.size = Pt(8.0)
            r_cont.font.italic = True

        p_desc = doc.add_paragraph()
        p_desc.paragraph_format.left_indent = Inches(0.25)
        p_desc.paragraph_format.space_after = Pt(2)
        r_ba = p_desc.add_run("Business Action: ")
        r_ba.bold = True
        r_ba.font.size = Pt(8.5)
        r_bat = p_desc.add_run(business_action)
        r_bat.font.size = Pt(8.5)

        p_tech = doc.add_paragraph()
        p_tech.paragraph_format.left_indent = Inches(0.25)
        p_tech.paragraph_format.space_after = Pt(4)
        r_ta = p_tech.add_run("Technical Function: ")
        r_ta.italic = True
        r_ta.font.size = Pt(8.0)
        r_ta.font.color.rgb = RGB_MUTED
        r_tat = p_tech.add_run(technical_summary)
        r_tat.font.size = Pt(8.0)
        r_tat.font.color.rgb = RGB_MUTED

    doc.add_paragraph().paragraph_format.space_after = Pt(16)

    # =============================================================
    # SECTION 4: TECHNICAL CONFIGURATION APPENDIX
    # =============================================================
    h4 = doc.add_heading("4. Technical Configuration Appendix", level=1)
    h4.paragraph_format.space_before = Pt(16)
    h4.paragraph_format.space_after = Pt(6)

    doc.add_paragraph(
        "This appendix documents the parsed configuration parameters and connection strings for each workflow tool for engineering review:"
    )

    for node in doc_model.nodes:
        p_node_title = doc.add_paragraph()
        p_node_title.paragraph_format.space_before = Pt(10)
        p_node_title.paragraph_format.space_after = Pt(4)
        cont_str = f" [Container: {node.container_name}]" if node.container_name else ""
        r_nh = p_node_title.add_run(f"Tool #{node.tool_id} — {node.name} ({node.tool_type}){cont_str}")
        r_nh.bold = True
        r_nh.font.size = Pt(9.0)
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
                c.paragraphs[0].runs[0].font.size = Pt(8.0)
                set_cell_margins(c, top=50, bottom=50, left=80, right=80)

            for key, val in node.configuration.items():
                r_cells = cfg_table.add_row().cells
                set_cell_background(r_cells[0], COLOR_BG_LIGHT_HEX)
                for c in r_cells:
                    set_cell_margins(c, top=50, bottom=50, left=80, right=80)

                pk = r_cells[0].paragraphs[0]
                pk.add_run(str(key))
                pk.runs[0].font.size = Pt(8.0)
                pk.runs[0].font.bold = True

                pv = r_cells[1].paragraphs[0]
                val_str = str(val) if not isinstance(val, (dict, list)) else str(val)[:120]
                pv.add_run(val_str)
                pv.runs[0].font.size = Pt(8.0)

    doc.save(str(output_path))
