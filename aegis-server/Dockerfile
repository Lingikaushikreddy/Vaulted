# Build Stage
FROM python:3.10-slim AS builder

WORKDIR /app
COPY requirements.txt .

# Install dependencies into a temporary directory
RUN pip install --user --no-cache-dir -r requirements.txt

# Runtime Stage
FROM python:3.10-slim

WORKDIR /app

# create non-root user
RUN useradd -m aegis
USER aegis

# Copy installed packages from builder
COPY --from=builder /root/.local /home/aegis/.local
ENV PATH=/home/aegis/.local/bin:$PATH

# Copy application code
COPY --chown=aegis:aegis aegis-server /app/aegis-server
COPY --chown=aegis:aegis certs /app/certs

# Create directories for persistence
RUN mkdir -p logs checkpoints

# Expose ports
# 8080: Flower gRPC
# 9090: Prometheus Metrics
EXPOSE 8080 9090

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:9090/metrics').getcode() == 200" || exit 1

# Launch Server
CMD ["python3", "-m", "aegis_server.server"]
