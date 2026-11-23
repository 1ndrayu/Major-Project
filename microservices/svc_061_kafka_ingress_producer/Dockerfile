# Production Dockerfile for Kafka-Ingress-Producer (svc-061)
FROM python:3.11-slim-bullseye

WORKDIR /app

# Install security updates
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as unprivileged container user
USER 10001
EXPOSE 8061

HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
    CMD curl -f http://localhost:8061/healthz || exit 1

ENTRYPOINT ["python", "app.py"]
