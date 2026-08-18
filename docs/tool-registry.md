# AWA Tool Registry Architecture

The **AWA Tool Registry** is a centralized, deterministic catalog covering the **100 highest-priority and most common tools** across Alteryx Designer workflows.

---

## 1. Registry Design Principles

1. **Deterministic & LLM-Free**: Tool resolution, classification, parsing, and code generation operate without external AI models or heuristic hallucinations.
2. **Canonical Identifiers**: Every tool is uniquely identified by its official Alteryx XML Tool Name (e.g., `AlteryxBasePluginsGui.DbFileInput.DbFileInput`).
3. **Graceful Fallback**: Workflows referencing unknown or proprietary vendor plugins are safely parsed into graph nodes with `UNSUPPORTED` support level and structured fallback diagnostics without crashing the engine.
4. **Automated Security Redaction**: Credentials, tokens, passwords, and private connection strings are scrubbed to `[REDACTED]` from raw XML and configuration dictionaries.

---

## 2. Category Model

The registry models the **11 standard Alteryx Designer tool categories**:

| Category | Tool Count | Visual Color Code | Primary Description |
|---|---|---|---|
| **In/Out** | 6 | Blue (`#4fc3f7`) | Reading and writing file formats, databases, text input, directory listings, and timestamps. |
| **Preparation** | 19 | Amber / Teal | Data cleaning, filtering, formulas, record ID assignment, sampling, deduplication, sorting, ranking. |
| **Join** | 7 | Cyan (`#26c6da`) | Relational joins, multiple joins, append fields (Cartesian products), find and replace. |
| **Parse** | 4 | Red (`#ef5350`) | DateTime parsing, RegEx pattern extraction, Text to Columns splitting, XML parsing. |
| **Transform** | 7 | Green (`#66bb6a`) | Summarization, aggregation, pivot/crosstab, unpivot/transpose, running totals, counting records. |
| **Developer** | 15 | Purple (`#ab47bc`) | Dynamic input/rename/select, block until done, field info, message logging, Python/R scripts, run command. |
| **Documentation** | 2 | Slate (`#b0bec5`) | Comment annotations and Tool Containers. |
| **Reporting** | 10 | Deep Orange (`#ff8a65`) | Charts, tables, email delivery, map renderers, header/footer layout components. |
| **Spatial** | 14 | Teal (`#00bfa5`) | Spatial object creation, buffer generation, point-in-polygon matches, spatial process overlays. |
| **In-Database** | 7 | Indigo (`#536dfe`) | Pushdown query builders: Connect In-DB, Filter In-DB, Formula In-DB, Join In-DB, Select In-DB. |
| **Connectors** | 9 | Rust (`#ff7043`) | Cloud and third-party service connectors (Amazon S3, SharePoint Files, Salesforce, MongoDB, Tableau). |

---

## 3. Support Classifications

Every tool definition is classified into one of six **Support Levels**:

| Support Level | Canonical String | Description | Code Generation Behavior |
|---|---|---|---|
| **FULL** | `full` | Complete deterministic Python/pandas implementation. | Generates production-grade pandas/NumPy logic with exact semantics. |
| **PARTIAL** | `partial` | Translates supported subsets; warns on advanced modes. | Generates pandas translation where applicable with explicit advisory diagnostic. |
| **PASS_THROUGH** | `pass_through` | Non-transforming pipeline controls (Browse, Block Until Done). | Passes input DataFrame forward with traceability comments. |
| **DOCUMENTATION_ONLY** | `documentation_only` | Design-time documentation (Comment, Tool Container, Layout). | Generates markdown/python documentation comments without manipulating runtime data. |
| **EXTERNAL_EXECUTION** | `external_execution` | External runtimes, cloud platforms, or database engines. | Emits detailed environment notice and fallback stub. |
| **UNSUPPORTED** | `unsupported` | Proprietary, legacy, or unsupported custom plugins. | Emits `raise NotImplementedError` placeholder with diagnostic. |

---

## 4. Tool Lookup & Resolution Flow

```
Workflow XML Node <GuiSettings Plugin="...">
         │
         ▼
`catalog.resolve(plugin_or_name)`
         │
         ├── 1. Exact XML Name match (e.g., "AlteryxBasePluginsGui.Filter.Filter")
         ├── 2. Short Name match (e.g., "Filter")
         ├── 3. Alias match (e.g., "InputData" -> "DbFileInput")
         ├── 4. Normalized display name match (e.g., "data cleansing" -> "Data Cleansing")
         │
         └── Fallback (Unknown Tool) ──> `create_fallback_tool_definition(plugin)`
                                          [SupportLevel = UNSUPPORTED, parsed = raw XML dict]
```

---

## 5. Security & Credential Redaction

The registry ensures secret safety:
- **XML Sanitization**: Tags like `<ApiKey>`, `<Password>`, `<Token>`, and attributes like `Password="..."` are scrubbed to `[REDACTED]`.
- **Configuration Sanitization**: All nested dictionaries and connection strings (`pwd=...;secret=...`) are recursively scrubbed before JSON or DOCX serialization.
- **Traceability & Diagnostics**: Secrets never appear in generated `workflow.py`, `workflow.json`, or `diagnostics.json`.

---

## 6. How to Add a New Tool Definition

1. Locate the appropriate category under `backend/src/awa/tools/definitions/<category>.py`.
2. Define a `ToolDefinition` instance with:
   - `xml_name`: Canonical plugin name.
   - `display_name`: Official designer label.
   - `category`: `ToolCategory` enum.
   - `support_level`: `SupportLevel` enum.
   - `alters_data`: Boolean flag.
   - `input_anchors` / `output_anchors`: Anchor name tuples.
   - `description`: Plain-text explanation.
3. If Python translation is supported, implement the translator class under `backend/src/awa/translators/` and register it using `register_plugin` and `register_type`.
