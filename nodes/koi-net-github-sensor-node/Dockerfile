FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy all project files first
COPY . .
# Config files will be copied by CI/CD
# COPY ../../config/docker/global.env /config/global.env
# COPY ../../config/docker/${SERVICE_NAME}.yaml /config/config.yaml

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl

# Install dependencies using UV
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system -e .

EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl --fail http://localhost:8001/koi-net/health || exit 1

CMD ["uvicorn", "github_sensor_node.server:app", "--host", "0.0.0.0", "--port", "8001"]