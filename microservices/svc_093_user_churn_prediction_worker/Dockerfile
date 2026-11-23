# Production Dockerfile for User-Churn-Prediction-Worker (svc-093)
FROM python:3.11-slim-bullseye

WORKDIR /app

# Install security updates
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as unprivileged container user
USER 10001
EXPOSE 8093

HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
    CMD curl -f http://localhost:8093/healthz || exit 1

ENTRYPOINT ["python", "app.py"]
