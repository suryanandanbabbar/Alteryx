# AWA — Alteryx Workflow Analyzer & Python Translator

A deterministic static analysis and Python/pandas translation tool for Alteryx Designer workflows (`.yxmd`, `.yxwz`, `.xml`) with a FastAPI backend and React frontend.

---

## Overview

AWA performs static analysis on Alteryx workflow files to extract graph topology, tool configurations, and data lineage without executing workflow contents. It translates supported Alteryx data transformation tools into idiomatic Python/pandas code, generates visual SVG DAG diagrams, produces structured JSON representations, and renders complete Word (`.docx`) documentation reports.

Workflow analysis and translation are deterministic and derived directly from the workflow definition.

---

## Supported Input Formats

- **`.yxmd`**: Standard Alteryx Designer workflow XML files.
- **`.yxwz`**: Packaged Alteryx analytic app/workflow archives (ZIP format, safely extracted).
- **`.xml`**: Standalone XML workflow extracts verified against Alteryx schema structure.

---

## Generated Output Artifacts

| Artifact | Format | Description |
|---|---|---|
| `workflow.json` | JSON | Canonical intermediate representation (graph, nodes, connections, metadata, lineage, trace mapping). |
| `workflow.py` | Python | Executable Python script using pandas and NumPy with line-level traceability comments. |
| `workflow.svg` | SVG | Scalable vector DAG diagram computed from topological layout. |
| `workflow.docx` | DOCX | Word documentation report with embedded visual DAG and node configuration tables. |
| `diagnostics.json` | JSON | Structured diagnostics covering unsupported tools, warnings, and external dependencies. |
| `workflow_bundle.zip`| ZIP | Single downloadable archive containing all 5 primary artifacts. |

---

## Architecture

The system uses a single source of truth design:

```
.yxmd / .yxwz / .xml
        ↓
  Format Handler (Magic bytes, ZIP safety, structural XML validation)
        ↓
    AWA Parser (Single-pass XML parsing to canonical Workflow IR)
        ↓
   Graph Engine (NetworkX DiGraph, topological sort, lineage computation)
        ↓
 Tool Translators (Deterministic pandas code generation + diagnostics)
        ↓
CanonicalAnalysisResult (Single Source of Truth)
        ↓
┌───────────────┬──────────────┬───────────────┬───────────────┐
│               │              │               │               │
SVG Generator   DOCX Generator Python Pipeline Structured JSON
(Vector DAG)    (python-docx)  (Traceability)  (Canonical IR)
└───────┬───────┴──────┬───────┴───────┬───────┴───────┬───────┘
        ▼              ▼               ▼               ▼
FastAPI REST API (/api/upload, /api/analysis/{id}/*, /api/download/{id}/*)
        ↓
React / TypeScript / Vite Dashboard (Interactive DAG, Code Viewer, Downloads)
```

### Project Layout

```text
backend/
├── app/       # FastAPI application and REST endpoints
└── src/
    └── awa/   # AWA analysis engine (parser, graph, translators, generators)
frontend/      # React / TypeScript user interface
tests/         # End-to-end and vertical slice tests
fixtures/      # Sample Alteryx workflow files
```

---

## Installation & Setup

### Prerequisites

- Python 3.11+
- Node.js 18+ and npm 9+

### 1. Python Backend Installation

```bash
# Install core library and server dependencies
python -m pip install -e ".[server,dev]"
```

### 2. Frontend Installation

```bash
cd frontend
npm ci
cd ..
```

---

## Running the Application

### Development Mode

**Terminal 1 — Backend:**
```bash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

Open `http://localhost:5173` in your browser.

### Production / Deployment Mode

**Backend:**
```bash
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

**Frontend Build:**
```bash
cd frontend
npm run build
```

The compiled static assets are generated in `frontend/dist/`.

---

## Configuration

Server settings are configured via environment variables. See `.env.example`:

| Variable | Default | Description |
|---|---|---|
| `AWA_CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated list of allowed CORS origins. |
| `AWA_MAX_UPLOAD_BYTES` | `52428800` (50 MB) | Maximum upload file size in bytes. |
| `AWA_STORAGE_TTL_SECONDS` | `3600` (1 hour) | In-memory session time-to-live. |
| `AWA_LOG_LEVEL` | `INFO` | Python logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |

---

## Command-Line Interface (CLI)

AWA includes a command-line tool:

```bash
# Analyze a workflow and generate all artifacts in ./output_dir
awa analyze fixtures/basic/simple_filter.yxmd -o output_dir

# Inspect workflow structure and topological execution order without generating files
awa inspect fixtures/basic/simple_filter.yxmd
```

---

## REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check endpoint. |
| `POST` | `/api/upload` | Upload `.yxmd`, `.yxwz`, or `.xml` and initiate analysis. |
| `GET` | `/api/analysis/{id}/overview` | Workflow metadata, node metrics, and execution order. |
| `GET` | `/api/analysis/{id}/diagram` | Vector SVG string and node configuration list. |
| `GET` | `/api/analysis/{id}/json` | Full canonical workflow JSON. |
| `GET` | `/api/analysis/{id}/python` | Python pipeline code with line-level traceability map. |
| `GET` | `/api/analysis/{id}/diagnostics` | Diagnostics list and tool support summary. |
| `GET` | `/api/download/{id}/docx` | Download Word documentation report. |
| `GET` | `/api/download/{id}/json` | Download `workflow.json`. |
| `GET` | `/api/download/{id}/python` | Download `workflow.py`. |
| `GET` | `/api/download/{id}/svg` | Download `workflow.svg`. |
| `GET` | `/api/download/{id}/zip` | Download complete bundle ZIP containing all artifacts. |

---

## Testing

Run the automated test suite with pytest:

```bash
# Run all tests
pytest -v

# Run backend API and security tests
pytest backend/tests/ -v

# Run frontend type check and build
cd frontend && npm run lint && npm run build
```

Test categories covered:
- **XML Parsing & Schema Extraction**: Verifies correct node, connection, and metadata parsing.
- **Expression Engine**: Lark grammar and pandas expression emission.
- **Tool Translators**: Deterministic pandas code generation across tool types.
- **Type Mapping & Null Semantics**: Canonical type conversion and null handling.
- **Graph & Topological Traversal**: DAG construction, sorting, and cycle detection.
- **Package Security**: Safe ZIP extraction and path traversal prevention.
- **Artifact Generators**: DOCX, SVG, JSON, and Python output validation.
- **Backend API & Storage**: Endpoint contracts, TTL expiration, and upload size limits.
- **Semantic Validation**: Execution of generated Python transformations against test data.

---

## Security & Operational Considerations

- **No Code Execution**: Workflow files are parsed strictly as data. Embedded scripts, macros, or binaries are never executed.
- **Package Safety**: Archive uploads are protected against directory traversal attacks (`..`), absolute path targets, and zip bombs.
- **Input Size Limits**: Configurable upload streaming limit (`AWA_MAX_UPLOAD_BYTES`) rejects oversized files before buffering into memory.
- **CORS Protection**: Explicit allowed origins configured via environment variables.

---

## Known Limitations

- **Session Storage**: The default storage service uses an in-memory TTL cache suitable for single-instance deployments. Multi-instance horizontal scaling requires an external shared storage provider.
- **External Data Dependencies**: Workflows referencing network paths (e.g. UNC shares) or external database connections produce valid translation code and `EXTERNAL_DEPENDENCY` diagnostics, but runtime execution requires access to the underlying data sources.
- **Unsupported Tools**: Tools without deterministic pandas equivalents (e.g., custom C++ plugins, geospatial macros) are classified as `UNSUPPORTED` and raise `NotImplementedError` in generated code while preserving raw XML configuration in `workflow.json`.
