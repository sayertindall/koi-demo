FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy code and shared dependencies
COPY . .
# Config files will be copied by CI/CD
# COPY ../../config/docker/global.env /config/global.env
# COPY ../../config/docker/${SERVICE_NAME}.yaml /config/config.yaml

# Install curl
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*


# Install processor A itself
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system -e .

EXPOSE 8011
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl --fail http://localhost:8011/koi-net/health || exit 1

CMD ["uvicorn", "processor_a_node.server:app", "--host", "0.0.0.0", "--port", "8011"]