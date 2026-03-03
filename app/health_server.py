"""
Health Check & Metrics Server
================================
Run alongside Streamlit as a separate process.
Exposes /health and /metrics endpoints.

Usage:
    uvicorn app.health_server:app --port 8001
"""

import os
import time
import datetime
from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse

app = FastAPI(title="HR Chatbot Health API", version="2.0.0")

START_TIME = time.time()


@app.get("/health", response_class=JSONResponse)
async def health_check():
    """Kubernetes / load-balancer liveness probe endpoint"""
    checks = {}

    # Check Pinecone connectivity
    try:
        from pinecone import Pinecone
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY", ""))
        pc.list_indexes()
        checks["pinecone"] = "ok"
    except Exception as e:
        checks["pinecone"] = f"error: {str(e)[:80]}"

    # Check OpenAI key presence
    checks["openai_key"] = "ok" if os.getenv("OPENAI_API_KEY") else "missing"
    checks["anthropic_key"] = "ok" if os.getenv("ANTHROPIC_API_KEY") else "missing"

    # Check Ollama
    try:
        import httpx
        r = httpx.get(f"{os.getenv('OLLAMA_BASE_URL','http://localhost:11434')}/api/tags", timeout=2)
        checks["ollama"] = "ok" if r.status_code == 200 else f"http_{r.status_code}"
    except Exception:
        checks["ollama"] = "unavailable"

    overall = "healthy" if checks["pinecone"] == "ok" else "degraded"

    return {
        "status": overall,
        "uptime_seconds": round(time.time() - START_TIME),
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "checks": checks,
        "version": "2.0.0"
    }


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """Prometheus metrics endpoint"""
    try:
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        return PlainTextResponse(
            content=generate_latest().decode("utf-8"),
            media_type=CONTENT_TYPE_LATEST
        )
    except ImportError:
        return PlainTextResponse("# prometheus_client not installed\n")


@app.get("/ready")
async def readiness():
    """Kubernetes readiness probe"""
    return {"status": "ready"}
