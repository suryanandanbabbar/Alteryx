# AWA — Azure Deployment & Package Discovery Guide

This document specifies the exact configuration, packaging, and startup procedure for deploying **AWA (Alteryx Workflow Analyzer & Python Translator)** to **Azure App Service / Azure Container Apps**.

---

## 1. Architecture & Package Layout

The repository is structured into two clean layers:

```text
Alteryx/
├── backend/
│   ├── app/                    # FastAPI web application layer
│   │   ├── main.py
│   │   ├── api/
│   │   ├── models/
│   │   └── services/
│   │
│   └── awa/                    # Core deterministic analysis engine
│       ├── analysis/
│       ├── parser/
│       ├── graph/
│       ├── expressions/
│       ├── generators/
│       ├── translators/
│       ├── model/
│       ├── tools/
│       └── cli/
│
├── frontend/                   # React / TypeScript dashboard
├── tests/                      # Python test suite
├── pyproject.toml              # Hatchling packaging configuration
├── requirements.txt            # Azure App Service deployment dependencies
└── ...
```

- **Engine Package Name**: `awa`
- **Application Module**: `backend.app.main:app`
- **Import convention**: Code imports `awa` directly (e.g., `from awa.parser.format_handler import ...`).

---

## 2. Python Version Support

AWA has been rigorously validated on:
- **Python 3.11** (Local & CI baseline)
- **Python 3.12** (Azure default runtime — 100% test pass rate across all 204 tests)

---

## 3. Package Build & Installation

### Build System Configuration (`pyproject.toml`)

The wheel target maps `backend/awa` directly to the `awa` package in the distribution wheel:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "awa"
version = "1.0.0"
requires-python = ">= 3.11"
dependencies = [
    "lark>=1.1.0",
    "networkx>=3.0",
    "click>=8.0",
    "python-docx>=1.0.0",
    "pillow>=10.0.0",
    "pydantic>=2.0.0",
    "pandas>=2.0",
    "numpy>=1.24",
    "openpyxl>=3.0",
]

[project.optional-dependencies]
server = [
    "fastapi>=0.100.0",
    "uvicorn[standard]>=0.20.0",
    "python-multipart>=0.0.6",
]

[tool.hatch.build.targets.wheel]
packages = [
    "backend/awa",
]
```

### Installation Command for Azure

During deployment build/startup in Azure App Service:

```bash
# Upgrade pip
python -m pip install --upgrade pip

# Install AWA and its server runtime dependencies
python -m pip install ".[server]"
```

---

## 4. Production Startup Command

In production Azure deployments, **do NOT use `--reload`**. Bind explicitly to `0.0.0.0` and utilize the port provided by Azure:

```bash
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Or when configuring via `startup.sh` / Azure Startup Command:

```bash
#!/usr/bin/env bash
python -m pip install ".[server]"
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

---

## 5. Required Environment Variables

Configure these settings in Azure App Service **Application Settings**:

| Variable | Default Value | Purpose |
|---|---|---|
| `PORT` | `8000` | Port assigned dynamically by Azure App Service. |
| `AWA_CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Allowed frontend URLs (e.g., `https://your-frontend.azurewebsites.net`). |
| `AWA_MAX_UPLOAD_BYTES` | `52428800` (50 MB) | Max workflow upload size limit in bytes. |
| `AWA_STORAGE_TTL_SECONDS`| `3600` (1 hour) | Session in-memory cache TTL. |
| `AWA_LOG_LEVEL` | `INFO` | Logging verbosity (`INFO`, `WARNING`, `ERROR`, `DEBUG`). |

---

## 6. Verification Checklist

Execute these commands in a clean virtual environment to confirm package discovery and startup:

```bash
# 1. Verify core awa package discovery
python -c "import awa; print('awa:', awa.__file__)"

# 2. Verify parser import
python -c "from awa.parser.format_handler import FormatValidationError; print('FormatValidationError:', FormatValidationError)"

# 3. Verify workflow analyzer import
python -c "from awa.analysis.workflow_analyzer import analyze_canonical; print('analyze_canonical:', analyze_canonical)"

# 4. Verify FastAPI application import
python -c "from backend.app.main import app; print('FastAPI app:', app)"

# 5. Verify CLI tool
awa --help

# 6. Verify health endpoint
curl http://127.0.0.1:8000/api/health
```
