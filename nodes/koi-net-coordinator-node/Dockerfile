FROM python:3.12-slim

ARG SERVICE_NAME
WORKDIR /app
COPY . .
# Config files will be copied by CI/CD
# COPY ../../config/docker/global.env /config/global.env
# COPY ../../config/docker/${SERVICE_NAME}.yaml /config/config.yaml

# 1) copy UV package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# 2) copy project files and source code
COPY . /app/

# 3) install curl for healthcheck
RUN apt-get update && apt-get install -y curl

# 4) install dependencies with UV (editable mode)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system -e .

# 5) expose port and healthcheck
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl --fail http://localhost:8080/koi-net/health || exit 1

# 6) start coordinator
CMD ["uvicorn", "coordinator_node.server:app", "--host", "0.0.0.0", "--port", "8080"]