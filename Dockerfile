# ─────────────────────────────────────────────────────
# HR Chatbot Pro — Production Dockerfile
# Multi-stage build for minimal image size
# ─────────────────────────────────────────────────────

# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc git \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python deps
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --user -r requirements.txt

# ─────────────────────────────────────────────────────
# Stage 2: Runtime
FROM python:3.11-slim AS runtime

WORKDIR /app

# Runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application files
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 chatbot && \
    chown -R chatbot:chatbot /app && \
    mkdir -p /app/logs && chown chatbot:chatbot /app/logs

USER chatbot

# Expose ports
EXPOSE 8501   # Streamlit
EXPOSE 8001   # Health/metrics server

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Start script: run health server in background, then Streamlit
CMD ["sh", "-c", \
    "uvicorn app.health_server:app --host 0.0.0.0 --port 8001 & \
     streamlit run app/frontend.py \
       --server.port=8501 \
       --server.address=0.0.0.0 \
       --server.headless=true \
       --server.enableXsrfProtection=true \
       --browser.gatherUsageStats=false"]
