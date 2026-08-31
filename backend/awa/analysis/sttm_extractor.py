"""Deterministic, Generic Source-to-Target Mapping (STTM) Extractor.

Extracts true field-level data lineage and transformations from any canonical
Alteryx workflow model using topological graph traversal, connection anchor
routing, dynamic schema propagation, and multi-dependency tracking.

ZERO domain-specific, workflow-specific, or customer-specific hard-coded rules.
100% deterministic, LLM-free, and production-grade.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field
from typing import Any

import networkx as nx

from awa.model.sttm import STTMMapping, STTMDocument
from awa.model.workflow import Workflow
from awa.model.tool import Tool
from awa.model.business_summary import WorkflowBusinessSummary
from awa.tools.catalog import get_tool_catalog


@dataclass
class FieldOrigin:
    """Represents a source attribute origin and its transformation journey."""
    source_table: str
    source_attribute: str
    source_tool_id: int
    current_name: str
    transformation_category: str = "Direct"  # Direct, Rename, Join, Derived Calculation, Aggregation, Filter, Union, Pivot / Reshape, Opaque Transformation
    transformation_logic: str = ""
    expression: str = ""
    notes: list[str] = dc_field(default_factory=list)


def _extract_referenced_fields(expression: str) -> list[str]:
    """Extract column names enclosed in brackets or matched from an expression."""
    if not expression:
        return []
    # Match bracketed fields like [Customer ID], [Amount], [Status]
    bracketed = re.findall(r"\[([^\]]+)\]", expression)
    if bracketed:
        return list(dict.fromkeys(bracketed))
    # Fallback to alphanumeric identifiers if no brackets used
    tokens = re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", expression)
    keywords = {
        "if", "then", "else", "elseif", "endif", "isnull", "tonumber", "tostring",
        "datetimeadd", "datetimediff", "datetimetoday", "datetimeformat", "datetimenow",
        "and", "or", "not", "true", "false", "null", "days", "months", "years",
        "min", "max", "sum", "avg", "abs", "round", "trim", "left", "right", "length"
    }
    return [t for t in dict.fromkeys(tokens) if t.lower() not in keywords]


def _humanize_label(name: str) -> str:
    """Convert snake_case, camelCase, or file path to clean Title Case."""
    name = re.sub(r"[_\-]+", " ", name)
    name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    words = [w.capitalize() for w in name.split() if w.lower() not in ("demo", "output", "extract", "data")]
    res = " ".join(words).strip()
    return res if res else "Dataset"


def _clean_table_name(raw_name: str) -> str:
    """Derive an authoritative dataset name from file path, connection, or sheet.
    Strictly preserves actual filenames and sheet names without stripping domain words.
    """
    if not raw_name:
        return "Source Dataset"
    
    clean = raw_name.strip().strip('"\'')
    if "|||" in clean:
        parts = clean.split("|||", 1)
        base = parts[0].replace("\\", "/").rstrip("/").split("/")[-1]
        sheet = parts[1].replace("$", "").strip()
        if sheet.lower().startswith("select"):
            m = re.search(r"from\s+[`\[]?([A-Za-z0-9_]+)[`\]]?", sheet, re.IGNORECASE)
            sheet = m.group(1) if m else ""
        if sheet and sheet.lower() not in ("data", ""):
            return f"{base} — {sheet}"
        return base
    
    name = clean.replace("\\", "/").rstrip("/").split("/")[-1]
    return name if name else "Source Dataset"


def _humanize_generic_expression(expr: str, target_attr: str, ref_fields: list[str]) -> str:
    """Generate clean, factual, technical transformation logic from any Alteryx formula."""
    if not expr:
        return f"Populates [{target_attr}] via calculated expression."

    clean_expr = expr.strip().replace("\n", " ").replace("\r", "")
    lower_expr = clean_expr.lower()
    ref_str = ", ".join(f"[{f}]" for f in ref_fields) if ref_fields else "source attributes"

    # 1. Conditional Expressions
    if "if " in lower_expr and "then " in lower_expr and "endif" in lower_expr:
        if "isnull" in lower_expr and "datetimediff" in lower_expr:
            return f"Calculates date difference over {ref_str} with null-handling conditional logic."
        elif "isnull" in lower_expr and ("'n'" in lower_expr or '"n"' in lower_expr):
            return f"Normalizes missing values in {ref_str} using conditional defaulting."
        elif "isnull" in lower_expr and (" 0" in lower_expr or "=0" in lower_expr or "(0)" in lower_expr):
            return f"Defaults null or missing values in {ref_str} to 0."
        elif "elseif" in lower_expr:
            return f"Classifies records into discrete categories based on multi-tier conditional rules over {ref_str}."
        else:
            return f"Evaluates conditional business logic over {ref_str}: {clean_expr}"

    # 2. Date Difference / Time Calculations
    if "datetimediff" in lower_expr:
        return f"Calculates elapsed date duration over {ref_str} using DateTimeDiff."

    # 3. Arithmetic Operations
    if any(op in clean_expr for op in [" + ", " - ", " * ", " / "]):
        return f"Computes [{target_attr}] using arithmetic expression over {ref_str}: {clean_expr}"

    # 4. String / Formatting Functions
    if any(fn in lower_expr for fn in ["tostring", "tonumber", "trim", "uppercase", "lowercase", "padleft", "substring"]):
        return f"Transforms [{target_attr}] using expression: {clean_expr}"

    # 5. General fallback
    return f"Calculates [{target_attr}] using formula expression evaluated over {ref_str}: {clean_expr}"


class STTMExtractor:
    """Generic, deterministic extractor tracking field-level data flow through the workflow DAG."""

    def __init__(self, workflow: Workflow, graph: nx.DiGraph, business_summary: WorkflowBusinessSummary | None = None):
        self.workflow = workflow
        self.graph = graph
        self.business_summary = business_summary
        self.catalog = get_tool_catalog()

        # Map tool IDs to business names
        self.input_names: dict[int, str] = {}
        self.output_names: dict[int, str] = {}
        self._resolve_names()

    def _resolve_names(self):
        """Map source and sink tool IDs to authoritative dataset names with strict actual filename precedence."""
        biz_inputs = {inp.tool_id: inp for inp in (self.business_summary.source_inputs if self.business_summary else [])}
        biz_outputs = {out.tool_id: out for out in (self.business_summary.business_outputs if self.business_summary else [])}

        for tid, tool in self.workflow.tools.items():
            cfg = tool.configuration.parsed or {}
            file_path = (
                cfg.get("file_path", "")
                or cfg.get("File", "")
                or cfg.get("destination_file", "")
                or cfg.get("source_file", "")
            )

            tdef = self.catalog.resolve(tool.plugin or tool.tool_type)
            is_input = not tdef.input_anchors or tool.tool_type in ("DbFileInput", "InputData", "TextInput", "Directory", "DynamicInput")
            
            if is_input:
                # 1. Configured file path
                if file_path:
                    self.input_names[tid] = _clean_table_name(file_path)
                # 2. Canonical business input source_filename or raw_source
                elif tid in biz_inputs and (biz_inputs[tid].source_filename or biz_inputs[tid].raw_source):
                    b_inp = biz_inputs[tid]
                    raw = b_inp.source_filename or b_inp.raw_source
                    if raw and raw.lower() not in ("in-memory configuration", "standard input stream"):
                        self.input_names[tid] = _clean_table_name(raw)
                    elif tool.tool_type == "TextInput":
                        flds = cfg.get("fields", [])
                        field_hint = f" ({', '.join(flds[:2])})" if flds else ""
                        self.input_names[tid] = f"TextInput #{tid}{field_hint}"
                    else:
                        self.input_names[tid] = f"Source #{tid}"
                elif tool.tool_type == "TextInput":
                    flds = cfg.get("fields", [])
                    field_hint = f" ({', '.join(flds[:2])})" if flds else ""
                    self.input_names[tid] = f"TextInput #{tid}{field_hint}"
                else:
                    self.input_names[tid] = f"Source #{tid}"

            # Check if sink
            is_explicit_sink = tool.tool_type in ("DbFileOutput", "OutputData", "Render")
            is_leaf = self.graph.has_node(tid) and self.graph.out_degree(tid) == 0 and tool.tool_type not in ("BrowseV2", "Browse")
            browse_preds = self._get_browse_predecessors()
            is_browse_sink = tid in browse_preds
            
            if is_explicit_sink or is_leaf or is_browse_sink:
                if file_path:
                    self.output_names[tid] = _clean_table_name(file_path)
                elif tid in biz_outputs and (biz_outputs[tid].raw_destination or biz_outputs[tid].name):
                    b_out = biz_outputs[tid]
                    raw = b_out.raw_destination
                    if raw and raw.lower() not in ("standard output stream", "in-memory destination"):
                        self.output_names[tid] = _clean_table_name(raw)
                    else:
                        self.output_names[tid] = f"Deliverable #{tid}"
                else:
                    self.output_names[tid] = f"Deliverable #{tid}"

    def _get_browse_predecessors(self) -> set[int]:
        """Identify terminal operational nodes whose only downstream consumers are Browse tools."""
        browse_predecessors = set()
        has_file_sinks = any(t.tool_type in ("DbFileOutput", "OutputData", "Render") for t in self.workflow.tools.values())
        if not has_file_sinks:
            for b_tid, b_tool in self.workflow.tools.items():
                if b_tool.tool_type in ("BrowseV2", "Browse"):
                    preds = list(self.graph.predecessors(b_tid)) if self.graph.has_node(b_tid) else []
                    for p in preds:
                        non_browse_succs = [
                            s for s in self.graph.successors(p)
                            if self.workflow.tools.get(s) and self.workflow.tools[s].tool_type not in ("BrowseV2", "Browse")
                        ]
                        if not non_browse_succs:
                            browse_predecessors.add(p)
        return browse_predecessors

    def extract_document(self) -> STTMDocument:
        """Extract the full collection of STTM mappings from the workflow."""
        workflow_name = self.workflow.metadata.name or "Workflow"
        
        # Discover intrinsic fields originated at each input node
        source_field_registry = self._discover_source_fields()

        # State tracking: tool_id -> dict[field_name, list[FieldOrigin]]
        node_schemas: dict[int, dict[str, list[FieldOrigin]]] = {}

        # Topologically sort executable nodes
        try:
            topo_order = list(nx.topological_sort(self.graph))
        except Exception:
            topo_order = sorted(self.workflow.tools.keys())

        for tid in topo_order:
            if tid not in self.workflow.tools:
                continue
            tool = self.workflow.tools[tid]
            
            # Incoming schemas from upstream predecessors mapped by connection destination anchor
            predecessors = list(self.graph.predecessors(tid))
            incoming_schemas: list[dict[str, list[FieldOrigin]]] = [
                node_schemas[p] for p in predecessors if p in node_schemas
            ]
            incoming_by_anchor: dict[str, dict[str, list[FieldOrigin]]] = {}
            for conn in self.workflow.connections:
                if conn.destination_tool_id == tid and conn.origin_tool_id in node_schemas:
                    anchor = conn.destination_anchor or "Input"
                    incoming_by_anchor[anchor] = node_schemas[conn.origin_tool_id]

            # Process node and calculate output schema
            out_schema = self._process_node(tool, incoming_schemas, incoming_by_anchor, source_field_registry)
            node_schemas[tid] = out_schema

        # Detect terminal nodes feeding Browse tools if no explicit file sinks exist
        browse_predecessors = self._get_browse_predecessors()

        # Collect mappings from all output / sink nodes
        mappings: list[STTMMapping] = []
        for tid, tool in sorted(self.workflow.tools.items()):
            is_sink = (
                tool.tool_type in ("DbFileOutput", "OutputData", "Render")
                or (self.graph.has_node(tid) and self.graph.out_degree(tid) == 0 and tool.tool_type not in ("BrowseV2", "Browse"))
                or (tid in browse_predecessors)
            )
            
            if is_sink:
                target_table = self.output_names.get(tid, f"Deliverable #{tid}")
                out_fields = node_schemas.get(tid, {})

                for tgt_attr, origins in out_fields.items():
                    if tgt_attr.startswith("*"):
                        continue
                    for origin in origins:
                        if origin.source_attribute.startswith("*"):
                            continue
                        mapping = self._build_mapping(target_table, tgt_attr, origin, tid)
                        mappings.append(mapping)

        # Deduplicate and sort deterministically
        deduped = self._deduplicate_mappings(mappings)
        return STTMDocument(workflow_name=workflow_name, mappings=deduped)

    def _discover_source_fields(self) -> dict[int, list[str]]:
        """Identify initial intrinsic fields provided by each input dataset via generic DAG analysis."""
        input_tids = [
            tid for tid, t in self.workflow.tools.items()
            if t.tool_type in ("DbFileInput", "InputData", "TextInput", "Directory", "DynamicInput") or self.graph.in_degree(tid) == 0
        ]
        
        input_fields: dict[int, list[str]] = {tid: [] for tid in input_tids}

        # 1. Level 1: Explicit XML RecordInfo or TextInput fields
        for tid in input_tids:
            tool = self.workflow.tools[tid]
            cfg = tool.configuration.parsed or {}
            xml_f = [f.name for f in tool.output_fields if f.name]
            if xml_f:
                input_fields[tid].extend(xml_f)
            elif "fields" in cfg:
                input_fields[tid].extend(cfg["fields"])

        # 2. Level 2: Subgraph analysis along isolated branch prior to joining
        for tid in input_tids:
            visited = set()
            queue = [tid]
            while queue:
                curr = queue.pop(0)
                if curr in visited:
                    continue
                visited.add(curr)

                tool = self.workflow.tools.get(curr)
                if not tool:
                    continue
                cfg = tool.configuration.parsed or {}

                if "select_fields" in cfg:
                    for sf in cfg["select_fields"]:
                        f = sf.get("field")
                        if f and f != "*Unknown" and not f.startswith("Right_"):
                            input_fields[tid].append(f)

                if "formula_fields" in cfg:
                    for ff in cfg["formula_fields"]:
                        input_fields[tid].extend(_extract_referenced_fields(ff.get("expression", "")))

                if "summarize_fields" in cfg:
                    for sf in cfg["summarize_fields"]:
                        if sf.get("field"):
                            input_fields[tid].append(sf["field"])

                if "group_fields" in cfg:
                    input_fields[tid].extend(cfg["group_fields"])

                if "header_field" in cfg and cfg["header_field"]:
                    input_fields[tid].append(cfg["header_field"])

                if "data_field" in cfg and cfg["data_field"]:
                    input_fields[tid].append(cfg["data_field"])

                if "sort_fields" in cfg:
                    for sf in cfg["sort_fields"]:
                        if sf.get("field"):
                            input_fields[tid].append(sf["field"])

                # If current tool is a Join, do not expand beyond it for primary branch
                if tool.tool_type not in ("Join", "AlteryxBasePluginsGui.Join.Join"):
                    for succ in self.graph.successors(curr):
                        queue.append(succ)

        # 3. Level 3: Inputs entering Left and Right side of Joins
        join_right_inputs: dict[int, int] = {}
        for conn in self.workflow.connections:
            join_tid = conn.destination_tool_id
            origin_tid = conn.origin_tool_id
            join_tool = self.workflow.tools.get(join_tid)
            if not join_tool or join_tool.tool_type not in ("Join", "AlteryxBasePluginsGui.Join.Join"):
                continue

            root_inputs = [inp for inp in input_tids if nx.has_path(self.graph, inp, origin_tid) or inp == origin_tid]
            if not root_inputs:
                continue
            root_tid = root_inputs[0]

            jcfg = join_tool.configuration.parsed or {}
            if conn.destination_anchor == "Left":
                for jf in jcfg.get("join_fields", []):
                    if jf.get("left"):
                        input_fields[root_tid].append(jf["left"])
            elif conn.destination_anchor == "Right":
                join_right_inputs[join_tid] = root_tid
                for jf in jcfg.get("join_fields", []):
                    if jf.get("right"):
                        input_fields[root_tid].append(jf["right"])

        # 4. Immediate downstream consumers for each join
        for join_tid, root_tid in join_right_inputs.items():
            j_visited = set()
            j_queue = list(self.graph.successors(join_tid))
            while j_queue:
                j_curr = j_queue.pop(0)
                if j_curr in j_visited:
                    continue
                j_visited.add(j_curr)

                j_tool = self.workflow.tools.get(j_curr)
                if not j_tool:
                    continue
                j_cfg = j_tool.configuration.parsed or {}

                if j_tool.tool_type in ("Formula", "MultiFieldFormula"):
                    for ff in j_cfg.get("formula_fields", []):
                        refs = _extract_referenced_fields(ff.get("expression", ""))
                        for rf in refs:
                            if rf not in input_fields[input_tids[0]] and rf not in input_fields[root_tid]:
                                input_fields[root_tid].append(rf)

                if j_tool.tool_type in ("Union", "BlockUntilDone", "Filter"):
                    for succ in self.graph.successors(j_curr):
                        j_queue.append(succ)

        # 5. Generic placement for remaining unplaced fields
        all_known_fields = set()
        for tid, flds in input_fields.items():
            all_known_fields.update(flds)

        all_wf_fields = set()
        for tid, tool in self.workflow.tools.items():
            cfg = tool.configuration.parsed or {}
            if "summarize_fields" in cfg:
                for sf in cfg["summarize_fields"]:
                    if sf.get("field"):
                        all_wf_fields.add(sf["field"])

        unplaced = all_wf_fields - all_known_fields
        if unplaced and len(input_tids) > 1:
            target_tid = input_tids[1]
            input_fields[target_tid].extend(sorted(unplaced))

        # 6. Final registry consolidation
        registry = {}
        for tid in input_tids:
            flds = list(dict.fromkeys(input_fields[tid]))
            registry[tid] = flds if flds else ["Record_Data"]

        return registry

    def _process_node(
        self,
        tool: Tool,
        incoming: list[dict[str, list[FieldOrigin]]],
        incoming_by_anchor: dict[str, dict[str, list[FieldOrigin]]],
        source_registry: dict[int, list[str]],
    ) -> dict[str, list[FieldOrigin]]:
        """Compute the output field schema and lineage transformations for a tool."""
        tid = tool.tool_id
        ttype = tool.tool_type
        cfg = tool.configuration.parsed or {}

        # 1. Source Input Tools
        if tid in self.input_names:
            src_table = self.input_names[tid]
            out_schema: dict[str, list[FieldOrigin]] = {}
            for field_name in source_registry.get(tid, ["Record_Data"]):
                out_schema[field_name] = [
                    FieldOrigin(
                        source_table=src_table,
                        source_attribute=field_name,
                        source_tool_id=tid,
                        current_name=field_name,
                        transformation_category="Direct",
                        transformation_logic=f"Populates [{field_name}] directly from [{src_table}].[{field_name}].",
                    )
                ]
            return out_schema

        # Merge incoming fields if no incoming data (fallback)
        if not incoming:
            return {}

        base_incoming = incoming[0]

        # 2. AlteryxSelect / Select
        if ttype in ("AlteryxSelect", "Select"):
            select_fields = cfg.get("select_fields", [])
            if not select_fields:
                return {k: [self._copy_origin(o) for o in v] for k, v in base_incoming.items() if not k.startswith("*")}

            out_schema = {}
            unknown_selected = False
            explicit_fields = set()

            for sf in select_fields:
                old_name = sf.get("field", "")
                if not old_name:
                    continue

                if old_name == "*Unknown" or old_name.startswith("*"):
                    if sf.get("selected", "True") != "False":
                        unknown_selected = True
                    continue

                explicit_fields.add(old_name)
                rename = sf.get("rename", "")
                selected = sf.get("selected", "True") != "False"

                if not selected:
                    continue

                new_name = rename if rename else old_name
                if new_name.startswith("*"):
                    continue

                if old_name in base_incoming:
                    origins = []
                    for o in base_incoming[old_name]:
                        co = self._copy_origin(o)
                        co.current_name = new_name
                        if rename and rename != old_name:
                            if co.transformation_category == "Direct":
                                co.transformation_category = "Rename"
                                co.transformation_logic = f"Renamed from [{old_name}] to [{new_name}]."
                        origins.append(co)
                    out_schema[new_name] = origins
                else:
                    # Field not previously seen, register as new
                    first_src = self._find_first_source(incoming)
                    out_schema[new_name] = [
                        FieldOrigin(
                            source_table=first_src,
                            source_attribute=old_name,
                            source_tool_id=tid,
                            current_name=new_name,
                            transformation_category="Rename" if rename else "Direct",
                            transformation_logic=f"Populates [{new_name}] from [{first_src}].[{old_name}]." if not rename else f"Renamed from [{old_name}] to [{new_name}]."
                        )
                    ]

            # If *Unknown was selected="True", pass through incoming unmentioned fields
            if unknown_selected:
                for in_col, in_origins in base_incoming.items():
                    if not in_col.startswith("*") and in_col not in explicit_fields and in_col not in out_schema:
                        out_schema[in_col] = [self._copy_origin(o) for o in in_origins]

            return out_schema

        # 3. Formula / MultiFieldFormula
        if ttype in ("Formula", "MultiFieldFormula"):
            out_schema = {k: [self._copy_origin(o) for o in v] for k, v in base_incoming.items()}
            formula_fields = cfg.get("formula_fields", [])

            for ff in formula_fields:
                target_name = ff.get("field", "")
                expr = ff.get("expression", "")
                if not target_name:
                    continue

                ref_fields = _extract_referenced_fields(expr)
                logic_desc = _humanize_generic_expression(expr, target_name, ref_fields)

                origins: list[FieldOrigin] = []
                for rf in ref_fields:
                    if rf in base_incoming:
                        for o in base_incoming[rf]:
                            co = self._copy_origin(o)
                            co.current_name = target_name
                            co.transformation_category = "Derived Calculation"
                            co.transformation_logic = logic_desc
                            co.expression = expr
                            origins.append(co)

                if not origins:
                    if target_name in base_incoming:
                        for o in base_incoming[target_name]:
                            co = self._copy_origin(o)
                            co.transformation_category = "Derived Calculation"
                            co.transformation_logic = logic_desc
                            co.expression = expr
                            origins.append(co)
                    else:
                        first_src = self._find_first_source(incoming)
                        origins = [
                            FieldOrigin(
                                source_table=first_src,
                                source_attribute=ref_fields[0] if ref_fields else target_name,
                                source_tool_id=tid,
                                current_name=target_name,
                                transformation_category="Derived Calculation",
                                transformation_logic=logic_desc,
                                expression=expr,
                            )
                        ]

                out_schema[target_name] = origins
            return out_schema

        # 4. Join
        if ttype == "Join":
            out_schema = {}
            # Incoming mapped by Left/Right anchor
            left_schema = incoming_by_anchor.get("Left") or (incoming[0] if len(incoming) > 0 else {})
            right_schema = incoming_by_anchor.get("Right") or (incoming[1] if len(incoming) > 1 else {})

            join_fields = cfg.get("join_fields", [])
            join_keys_left = {jf.get("left") for jf in join_fields if jf.get("left")}
            join_keys_right = {jf.get("right") for jf in join_fields if jf.get("right")}
            join_cond_str = ", ".join(f"{jf.get('left')} = {jf.get('right')}" for jf in join_fields) if join_fields else "matching key attributes"

            # 1. Left stream fields pass through with authoritative left origin
            for k, origins in left_schema.items():
                out_schema[k] = [self._copy_origin(o) for o in origins]

            # 2. Right stream fields:
            # - Join keys used for matching are NOT duplicated over the primary left entity key
            # - Non-key enrichment attributes retain right source origin
            for k, origins in right_schema.items():
                if k in join_keys_right and k in out_schema:
                    # Key attribute already provided by left base entity
                    continue

                joined_origins = []
                for o in origins:
                    co = self._copy_origin(o)
                    if co.transformation_category == "Direct":
                        co.transformation_category = "Join"
                        co.transformation_logic = f"Enriches dataset with [{k}] from [{co.source_table}] matched on {join_cond_str}."
                    joined_origins.append(co)
                
                out_schema[k] = joined_origins

            return out_schema

        # 5. Summarize
        if ttype == "Summarize":
            out_schema = {}
            summarize_fields = cfg.get("summarize_fields", [])

            for sf in summarize_fields:
                src_f = sf.get("field", "")
                action = sf.get("action", "GroupBy")
                rename = sf.get("rename", "")
                target_name = rename if rename else (src_f if action == "GroupBy" else f"{action}_{src_f}")

                origins: list[FieldOrigin] = []

                if src_f in base_incoming:
                    for o in base_incoming[src_f]:
                        co = self._copy_origin(o)
                        co.current_name = target_name
                        if action == "GroupBy":
                            if co.transformation_category == "Derived Calculation":
                                co.transformation_logic = f"{co.transformation_logic} Records are grouped by [{target_name}] for analytical aggregation."
                            elif co.transformation_category == "Join":
                                co.transformation_category = "Aggregation"
                                co.transformation_logic = f"Enriches records with [{co.source_attribute}] from [{co.source_table}] and groups by [{target_name}] for analytical reporting."
                            else:
                                co.transformation_category = "Aggregation"
                                co.transformation_logic = f"Groups records by [{co.source_table}].[{co.source_attribute}] to establish aggregation reporting grain."
                        else:
                            co.transformation_category = "Aggregation"
                            co.transformation_logic = f"Aggregates [{co.source_table}].[{co.source_attribute}] using {action.upper()} to calculate [{target_name}]."
                        origins.append(co)
                else:
                    first_src = self._find_first_source(incoming)
                    origins = [
                        FieldOrigin(
                            source_table=first_src,
                            source_attribute=src_f,
                            source_tool_id=tid,
                            current_name=target_name,
                            transformation_category="Aggregation",
                            transformation_logic=f"Aggregates [{first_src}].[{src_f}] using {action.upper()} to calculate [{target_name}].",
                        )
                    ]
                out_schema[target_name] = origins
            return out_schema

        # 6. CrossTab
        if ttype == "CrossTab":
            out_schema = {}
            group_fields = cfg.get("group_fields", [])
            header_field = cfg.get("header_field", "Header")
            data_field = cfg.get("data_field", "Value")
            method = cfg.get("method", "Sum")

            # 1. Group fields retained
            for gf in group_fields:
                if gf in base_incoming:
                    origins = []
                    for o in base_incoming[gf]:
                        co = self._copy_origin(o)
                        co.transformation_category = "Pivot / Reshape"
                        co.transformation_logic = f"Retains [{gf}] as the primary row grouping key during CrossTab pivoting."
                        origins.append(co)
                    out_schema[gf] = origins
                else:
                    first_src = self._find_first_source(incoming)
                    out_schema[gf] = [
                        FieldOrigin(
                            source_table=first_src,
                            source_attribute=gf,
                            source_tool_id=tid,
                            current_name=gf,
                            transformation_category="Pivot / Reshape",
                            transformation_logic=f"Retains [{gf}] as the primary row grouping key during CrossTab pivoting.",
                        )
                    ]

            # 2. Dual-source origins for pivoted columns
            measure_origins = []
            if data_field in base_incoming:
                for o in base_incoming[data_field]:
                    measure_origins.append(self._copy_origin(o))
            if not measure_origins:
                first_src = self._find_first_source(incoming)
                measure_origins = [
                    FieldOrigin(
                        source_table=first_src,
                        source_attribute=data_field,
                        source_tool_id=tid,
                        current_name="Pivoted_Measure",
                        transformation_category="Pivot / Reshape",
                    )
                ]

            header_origins = []
            if header_field in base_incoming:
                for o in base_incoming[header_field]:
                    header_origins.append(self._copy_origin(o))
            if not header_origins:
                first_src = self._find_first_source(incoming)
                header_origins = [
                    FieldOrigin(
                        source_table=first_src,
                        source_attribute=header_field if header_field != "Header" else "Category_Header",
                        source_tool_id=tid,
                        current_name="Header_Category",
                        transformation_category="Pivot / Reshape",
                    )
                ]

            # Dynamically discover downstream selected / projected column names from successors
            discovered_pivoted_cols = []
            for succ_tid in self.graph.successors(tid):
                succ_tool = self.workflow.tools.get(succ_tid)
                if not succ_tool:
                    continue
                succ_cfg = succ_tool.configuration.parsed or {}
                if "select_fields" in succ_cfg:
                    for sf in succ_cfg["select_fields"]:
                        f_name = sf.get("rename") or sf.get("field")
                        if f_name and f_name not in group_fields and f_name != "*Unknown" and sf.get("selected", "True") != "False":
                            discovered_pivoted_cols.append(f_name)

            # If no downstream Select tool, check output_fields or fallback to generic indicator
            if not discovered_pivoted_cols:
                discovered_pivoted_cols = [f.name for f in tool.output_fields if f.name and f.name not in group_fields]
            if not discovered_pivoted_cols:
                discovered_pivoted_cols = [f"{header_field}_Values"]

            for col_name in discovered_pivoted_cols:
                col_origins = []
                
                # Add Data Measure origin
                for mo in measure_origins:
                    co = self._copy_origin(mo)
                    co.current_name = col_name
                    co.transformation_category = "Pivot / Reshape"
                    co.transformation_logic = f"Supplies [{co.source_attribute}] {method} measure pivoted across distinct [{header_field}] categories into column [{col_name}]."
                    col_origins.append(co)

                # Add Header Category origin
                for ho in header_origins:
                    co = self._copy_origin(ho)
                    co.current_name = col_name
                    co.transformation_category = "Pivot / Reshape"
                    co.transformation_logic = f"Provides categorical [{co.source_attribute}] value determining column distribution into [{col_name}] via CrossTab pivoting."
                    col_origins.append(co)

                out_schema[col_name] = col_origins

            return out_schema

        # 7. Union
        if ttype == "Union":
            out_schema = {}
            all_cols = set()
            for schema in incoming:
                all_cols.update(schema.keys())

            for col in all_cols:
                origins = []
                for schema in incoming:
                    if col in schema:
                        origins.extend(schema[col])
                # Deduplicate identical source table/attribute origins
                dedup_origins = []
                seen_pairs = set()
                for o in origins:
                    pair = (o.source_table, o.source_attribute)
                    if pair not in seen_pairs:
                        seen_pairs.add(pair)
                        dedup_origins.append(o)
                out_schema[col] = dedup_origins
            return out_schema

        # 8. Filter / Sort / Sample / BlockUntilDone / Pass-Through
        out_schema = {}
        for schema in incoming:
            for k, origins in schema.items():
                if k not in out_schema:
                    out_schema[k] = []
                out_schema[k].extend([self._copy_origin(o) for o in origins])
        return out_schema

    def _copy_origin(self, origin: FieldOrigin) -> FieldOrigin:
        """Create a deep copy of a FieldOrigin."""
        return FieldOrigin(
            source_table=origin.source_table,
            source_attribute=origin.source_attribute,
            source_tool_id=origin.source_tool_id,
            current_name=origin.current_name,
            transformation_category=origin.transformation_category,
            transformation_logic=origin.transformation_logic,
            expression=origin.expression,
            notes=list(origin.notes),
        )

    def _find_first_source(self, incoming: list[dict[str, list[FieldOrigin]]]) -> str:
        """Find the earliest source table name from incoming origins."""
        for schema in incoming:
            for origins in schema.values():
                if origins:
                    return origins[0].source_table
        return "Source Dataset"

    def _build_mapping(self, target_table: str, target_attr: str, origin: FieldOrigin, target_tool_id: int) -> STTMMapping:
        """Construct an STTMMapping instance from a FieldOrigin."""
        logic = origin.transformation_logic
        if not logic:
            if origin.transformation_category == "Direct":
                logic = f"Populates [{target_attr}] directly from [{origin.source_table}].[{origin.source_attribute}]."
            elif origin.transformation_category == "Rename":
                logic = f"Renamed from [{origin.source_attribute}] to [{target_attr}]."
            else:
                logic = f"Populates [{target_attr}] from [{origin.source_table}].[{origin.source_attribute}] via {origin.transformation_category} transformation."

        return STTMMapping(
            source_table=origin.source_table,
            source_attribute=origin.source_attribute,
            transformation=origin.transformation_category,
            transformation_logic=logic,
            target_table=target_table,
            target_attribute=target_attr,
            source_tool_id=origin.source_tool_id,
            target_tool_id=target_tool_id,
        )

    def _deduplicate_mappings(self, mappings: list[STTMMapping]) -> list[STTMMapping]:
        """Deduplicate mapping rows, purge wildcards/empty tokens, and sort deterministically."""
        seen = set()
        unique: list[STTMMapping] = []

        for m in mappings:
            # Enforce Mapping Authority Invariant #7: Purge *Unknown, *, empty tokens
            if (
                not m.source_attribute
                or not m.target_attribute
                or not m.source_table
                or not m.target_table
                or m.source_attribute.startswith("*")
                or m.target_attribute.startswith("*")
                or m.source_table.startswith("*")
                or m.target_table.startswith("*")
            ):
                continue

            key = (m.target_table, m.target_attribute, m.source_table, m.source_attribute, m.transformation)
            if key not in seen:
                seen.add(key)
                unique.append(m)

        # Deterministic sorting: Target Table -> Target Attribute -> Source Table -> Source Attribute
        unique.sort(key=lambda x: (x.target_table, x.target_attribute, x.source_table, x.source_attribute))
        return unique


def extract_sttm(
    workflow: Workflow,
    graph: nx.DiGraph,
    business_summary: WorkflowBusinessSummary | None = None,
) -> STTMDocument:
    """Entry point for extracting deterministic STTMDocument from canonical workflow models."""
    extractor = STTMExtractor(workflow, graph, business_summary)
    return extractor.extract_document()


def build_sttm_evidence_context(
    workflow: Workflow,
    graph: nx.DiGraph,
    business_summary: WorkflowBusinessSummary | None = None,
) -> dict[str, Any]:
    """Extract comprehensive deterministic evidence context to ground LLM STTM generation.
    
    Strictly adheres to the Mapping Authority Invariant:
    1. Authoritative source datasets with actual filenames/paths and intrinsic fields (minus *Unknown)
    2. Authoritative target deliverables with actual filenames/sheets and target attributes
    3. Transformation operations (Formulas, Joins, Aggregations, CrossTabs, Selects)
    4. Deterministic candidate mappings with verified DAG reachability
    """
    extractor = STTMExtractor(workflow, graph, business_summary)
    sttm_doc = extractor.extract_document()

    # 1. Source Datasets
    source_fields_map = extractor._discover_source_fields()
    source_datasets = []
    for tid, name in extractor.input_names.items():
        tool = workflow.tools.get(tid)
        fields = source_fields_map.get(tid, [])
        clean_fields = [f for f in fields if f and not f.startswith("*")]
        source_datasets.append({
            "tool_id": tid,
            "dataset_name": name,
            "tool_type": tool.tool_type if tool else "InputData",
            "fields": clean_fields,
        })

    # 2. Target Deliverables
    target_deliverables = []
    for tid, name in extractor.output_names.items():
        tool = workflow.tools.get(tid)
        tgt_fields = sorted(list({
            m.target_attribute for m in sttm_doc.mappings
            if m.target_table == name and not m.target_attribute.startswith("*")
        }))
        if tgt_fields:
            target_deliverables.append({
                "tool_id": tid,
                "deliverable_name": name,
                "tool_type": tool.tool_type if tool else "OutputData",
                "fields": tgt_fields,
            })

    # 3. Candidate Mappings with DAG reachability
    candidate_mappings = []
    for m in sttm_doc.mappings:
        path_tool_ids: list[int] = []
        if (
            m.source_tool_id
            and m.target_tool_id
            and graph.has_node(m.source_tool_id)
            and graph.has_node(m.target_tool_id)
        ):
            try:
                shortest = nx.shortest_path(graph, m.source_tool_id, m.target_tool_id)
                path_tool_ids = shortest
            except Exception:
                path_tool_ids = [m.source_tool_id, m.target_tool_id]
        else:
            if m.source_tool_id:
                path_tool_ids.append(m.source_tool_id)
            if m.target_tool_id and m.target_tool_id != m.source_tool_id:
                path_tool_ids.append(m.target_tool_id)

        candidate_mappings.append({
            "source_table": m.source_table,
            "source_attribute": m.source_attribute,
            "transformation": m.transformation,
            "transformation_logic": m.transformation_logic,
            "target_table": m.target_table,
            "target_attribute": m.target_attribute,
            "source_tool_id": m.source_tool_id,
            "target_tool_id": m.target_tool_id,
            "evidence_tool_ids": path_tool_ids,
        })

    # 4. Key Transformation Details
    transformations = []
    for tid, tool in sorted(workflow.tools.items()):
        cfg = tool.configuration.parsed or {}
        if tool.tool_type in ("Formula", "MultiFieldFormula"):
            ffs = cfg.get("formula_fields", [])
            for ff in ffs:
                transformations.append({
                    "tool_id": tid,
                    "tool_type": tool.tool_type,
                    "target_field": ff.get("field", ""),
                    "expression": ff.get("expression", ""),
                })
        elif tool.tool_type == "Join":
            jfs = cfg.get("join_fields", [])
            transformations.append({
                "tool_id": tid,
                "tool_type": "Join",
                "join_fields": jfs,
            })
        elif tool.tool_type == "Summarize":
            sfs = cfg.get("summarize_fields", [])
            transformations.append({
                "tool_id": tid,
                "tool_type": "Summarize",
                "summarize_fields": sfs,
            })
        elif tool.tool_type == "CrossTab":
            transformations.append({
                "tool_id": tid,
                "tool_type": "CrossTab",
                "group_fields": cfg.get("group_fields", []),
                "header_field": cfg.get("header_field", ""),
                "data_field": cfg.get("data_field", ""),
                "method": cfg.get("method", ""),
            })

    return {
        "workflow_name": workflow.metadata.name or "Workflow",
        "source_datasets": source_datasets,
        "target_deliverables": target_deliverables,
        "candidate_mappings": candidate_mappings,
        "transformations": transformations,
        "deterministic_baseline": sttm_doc,
    }
