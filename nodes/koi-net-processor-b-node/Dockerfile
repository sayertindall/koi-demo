FROM python:3.12-slim

# 1) copy UV package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# 2) copy pyproject and perform editable installation
COPY pyproject.toml /app/

# 3) install curl for healthcheck
RUN apt-get update && apt-get install -y curl --no-install-recommends && rm -rf /var/lib/apt/lists/*

# 4) install dependencies using UV and pyproject.toml
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system -e .

# 5) copy in code
COPY processor_b_node /app/processor_b_node 

# 6) expose port
EXPOSE 8012 

# 7) add healthcheck using the main app's endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl --fail http://localhost:8012/koi-net/health || exit 1

# 8) start the main service using shell form for ENV var substitution
CMD ["uvicorn", "processor_b_node.server:app", "--host", "0.0.0.0", "--port", "8012"] 