FROM python:3.12-slim

# 1) copy UV package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# 2) copy shared rid_types package into correct path
COPY ./rid_types /app/rid_types

# 3) install rid_types in editable mode
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system -e /app/rid_types

# 4) ensure Python can locate rid_types
ENV PYTHONPATH="/app/rid_types:${PYTHONPATH}"

# 5) copy processor‑b pyproject.toml
COPY ./nodes/koi-net-processor-b-node/pyproject.toml /app/

# 6) install curl for healthcheck (and clean up)
RUN apt-get update \
 && apt-get install -y curl \
 && rm -rf /var/lib/apt/lists/*

# 7) install processor‑b (and its deps) in editable mode
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system -e .

# 8) copy in the rest of the processor‑b code
COPY ./nodes/koi-net-processor-b-node/. /app/

# 9) expose port and add healthcheck
EXPOSE 8012
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl --fail http://localhost:8012/koi-net/health || exit 1

# 10) start the service
CMD ["uvicorn", "processor_b_node.server:app", "--host", "0.0.0.0", "--port", "8012"]