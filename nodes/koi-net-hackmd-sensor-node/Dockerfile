FROM python:3.12-slim

# 1) copy UV package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# 2) copy pyproject and perform editable installation
COPY pyproject.toml /app/

# 3) install curl for healthcheck
RUN apt-get update && apt-get install -y curl

# 4) install dependencies using UV and pyproject.toml
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system -e .

# 5) copy in code
COPY . /app/

# 6) expose port and set environment
EXPOSE 8002

# 7) add healthcheck using the main app's endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl --fail http://localhost:8002/koi-net/health || exit 1

# 8) start the main service using shell form for ENV var substitution
CMD ["uvicorn", "hackmd_sensor_node.server:app", "--host", "0.0.0.0", "--port", "8002"]