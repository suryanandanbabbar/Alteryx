# AWA Pre-Deployment Checklist

This document summarizes deployment requirements, environment configuration, and operational verification for the AWA application.

---

## 1. Runtime Requirements

- **Python**: 3.11+
- **Node.js**: 18+ (with npm 9+)
- **OS**: Linux (RHEL / Ubuntu / Debian / Alpine) or macOS

---

## 2. Installation Commands

### Backend
```bash
python -m pip install --upgrade pip
python -m pip install -e ".[server]"
```

### Frontend
```bash
cd frontend
npm ci
npm run build
```

---

## 3. Environment Configuration

Deployments should provide environment variables as specified in `.env.example`:

| Variable | Recommended Production Value | Description |
|---|---|---|
| `AWA_CORS_ORIGINS` | `https://awa.your-domain.com` | Allowed frontend origin(s), comma-separated. |
| `AWA_MAX_UPLOAD_BYTES` | `52428800` (50 MB) | Maximum upload request body in bytes. |
| `AWA_STORAGE_TTL_SECONDS` | `3600` | In-memory session lifetime in seconds. |
| `AWA_LOG_LEVEL` | `INFO` | Logging severity (`INFO`, `WARNING`, `ERROR`). |

---

## 4. Service Startup

### Backend Service
```bash
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
```

> **Note on Storage**: The default storage backend is an in-memory TTL dictionary. Single-instance deployments or single-worker processes are fully supported out-of-the-box. For multi-worker or multi-instance clustering, a shared storage backend (such as a database or key-value store) should be implemented.

### Frontend Serving
Serve the static bundle built in `frontend/dist/` using Nginx, Caddy, AWS S3 / CloudFront, or any standard reverse proxy.

Ensure API requests to `/api/*` are routed to the FastAPI backend service (`http://backend-host:8000/api/*`).

---

## 5. Operational Health Check

- **Endpoint**: `GET /api/health`
- **Expected Status**: `200 OK`
- **Expected Response**:
  ```json
  {
    "status": "ok",
    "service": "AWA Alteryx Converter API",
    "version": "1.0.0"
  }
  ```

---

## 6. Pre-Deployment Verification Steps

1. Run the test suite:
   ```bash
   pytest -v
   ```
2. Run frontend type check and build:
   ```bash
   cd frontend && npm run lint && npm run build
   ```
3. Test a sample workflow upload:
   ```bash
   curl -X POST http://localhost:8000/api/upload \
     -F "file=@fixtures/basic/simple_filter.yxmd"
   ```
4. Verify HTTP 200 response with valid `analysis_id`.
