# Multi-stage build to reduce final image size

# Build stage - install dependencies and compile wheels
FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy requirements
COPY requirements.txt .

# Create wheels directory and install dependencies
RUN pip install --upgrade pip wheel
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# Runtime stage - minimal final image
FROM python:3.11-slim AS runtime

# Install only runtime system dependencies (if any needed)
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security with home directory
RUN groupadd -r retainr && useradd -r -g retainr -m -d /home/retainr retainr

# Set working directory
WORKDIR /app

# Copy wheels and requirements from builder stage
COPY --from=builder /wheels /wheels
COPY --from=builder /build/requirements.txt /tmp/

# Install Python packages from wheels (much faster and smaller)
RUN pip install --upgrade pip \
    && pip install --no-index --find-links /wheels -r /tmp/requirements.txt \
    && rm -rf /wheels /tmp/requirements.txt \
    && pip cache purge

# Pre-download the embedding model to avoid runtime downloads
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy application code
COPY --chown=retainr:retainr mcp_server/ ./mcp_server/
COPY --chown=retainr:retainr cli/ ./cli/
COPY --chown=retainr:retainr pyproject.toml ./

# Create directories for data persistence and model cache
RUN mkdir -p /app/memory /app/chroma /home/retainr/.cache \
    && chown -R retainr:retainr /app /home/retainr

# Switch to non-root user
USER retainr

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the server
CMD ["python", "-m", "uvicorn", "mcp_server.main:app", "--host", "0.0.0.0", "--port", "8000"]
