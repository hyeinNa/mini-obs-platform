# syntax=docker/dockerfile:1
# ---- build stage ----
FROM python:3.11-slim AS builder

WORKDIR /app
RUN pip install --no-cache-dir uv

COPY pyproject.toml ./
RUN uv pip install --system --no-cache -r pyproject.toml 2>/dev/null || \
    uv pip install --system --no-cache \
        "fastapi>=0.111.0" \
        "uvicorn[standard]>=0.30.0" \
        "httpx>=0.27.0" \
        "prometheus-client>=0.20.0" \
        "opentelemetry-api>=1.24.0" \
        "opentelemetry-sdk>=1.24.0" \
        "opentelemetry-instrumentation-fastapi>=0.45b0" \
        "opentelemetry-exporter-otlp-proto-grpc>=1.24.0" \
        "opentelemetry-propagator-b3>=1.24.0"

# ---- runtime stage ----
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY main.py otel_setup.py metrics.py ./

ENV OTEL_SERVICE_NAME=order-svc
ENV INVENTORY_SVC_URL=http://inventory-svc:8082
ENV OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317

EXPOSE 8081

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8081"]
