# AWA — Alteryx Workflow Analyzer & Python Translator

> Production-grade, deterministic static analysis and Python/pandas translator for Alteryx workflows (`.yxmd`, `.yxwz`, `.xml`) with a FastAPI backend and React frontend.

---

## ⚡ Non-Negotiable Core Principles

1. **NO LLMs / Generative AI**: Analysis, translations, DAG layout, and "why" explanations are 100% deterministic and derived strictly from workflow XML.
2. **Single Source of Truth**: All endpoints, visualizations, and generated files derive from `CanonicalAnalysisResult`.
3. **Targets Idiomatic Python/pandas**: Produces clean, readable pandas scripts with line-level traceability headers.
4. **Security Hardened**: Safe package handling, ZIP traversal protection, structural XML validation, and zero code execution of workflow contents.

---

## 📦 Features & Output Artifacts

- **Interactive React Dashboard**: Dark navy glassmorphism UI reproducing the 6 specification application states pixel-for-pixel:
  - `01 Workflow Overview`: Stat metrics, topological execution order pipeline, metadata table.
  - `02 Workflow Diagram`: Interactive SVG DAG viewer with zoom/pan and expandable key-value node configs.
  - `03 Structured JSON Output`: Full canonical intermediate representation JSON.
  - `04 Python Pipeline Output`: Executable pandas pipeline with line-level traceability and library disclosure.
  - `05 Download All Files`: Individual artifact downloads plus master bundle ZIP.
- **Export Artifacts Generated**:
  1. `workflow.json` — Machine-readable workflow IR.
  2. `workflow.py` — Executable pandas pipeline with line-level traceability.
  3. `workflow.docx` — Complete Word documentation report.
  4. `workflow.svg` — Scalable vector DAG diagram.
  5. `diagnostics.json` — Structured diagnostics and support summary.
  6. `workflow_bundle.zip` — Single download archive containing all 5 files.

---

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Install Python dependencies
pip3 install -e ".[dev]"

# Install Frontend dependencies
cd frontend
npm install
cd ..
```

### 2. Run the Full-Stack Application

**Terminal 1: Start FastAPI Backend**
```bash
python3 -m uvicorn backend.app.main:app --reload --port 8000
```

**Terminal 2: Start React Frontend**
```bash
cd frontend
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## 🛠️ CLI Usage

AWA also works as a standalone command-line tool:

```bash
# Analyze a workflow and generate all artifacts in ./output_dir
awa analyze fixtures/joins/join_workflow.yxmd -o output_dir

# Inspect a workflow DAG without generating files
awa inspect fixtures/joins/join_workflow.yxmd
```

---

## 🧪 Testing & Validation

AWA includes a comprehensive suite of 158 tests covering parser integrity, graph construction, expression translation, null semantics, format detection, package security, DOCX/SVG generators, API contracts, and real semantic validation:

```bash
# Run the complete test suite
python3 -m pytest -v

# Run backend API & security tests
python3 -m pytest backend/tests/ -v

# Run frontend build verification
cd frontend && npm run build
```

---

## 📚 Documentation

- [Architecture & System Design](docs/architecture.md)
- [REST API Reference](docs/api-reference.md)
- [Full-Stack Audit & Pre-Implementation Report](docs/fullstack-audit.md)
- [Supported Alteryx Tools & Semantics](docs/supported-tools.md)
