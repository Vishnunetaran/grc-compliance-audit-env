FROM ghcr.io/meta-pytorch/openenv-base:latest

WORKDIR /app

# Install Python dependencies first (layer-cached unless requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy full project
COPY . .

# Install the package in editable mode so imports resolve correctly
RUN pip install --no-cache-dir -e .

# Health check — Hugging Face / platform polls /health
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

EXPOSE 7860

CMD ["uvicorn", "grc_compliance_audit_env.server.app:app", \
     "--host", "0.0.0.0", "--port", "7860", \
     "--workers", "1", \
     "--log-level", "info"]