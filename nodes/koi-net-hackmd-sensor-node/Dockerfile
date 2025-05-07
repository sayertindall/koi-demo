FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY . .
# Config files will be copied by CI/CD
# COPY ../../config/docker/global.env /config/global.env
# COPY ../../config/docker/${SERVICE_NAME}.yaml /config/config.yaml

RUN apt-get update && apt-get install -y curl

RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system -e .

EXPOSE 8002
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl --fail http://localhost:8002/koi-net/health || exit 1

CMD ["uvicorn", "hackmd_sensor_node.server:app", "--host", "0.0.0.0", "--port", "8002"]