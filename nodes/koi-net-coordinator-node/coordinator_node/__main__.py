import uvicorn

# Remove import from old config
# from .config import PORT

# Port is now handled by Docker CMD and config_loader if needed elsewhere
uvicorn.run(
    "coordinator_node.server:app",
    host="0.0.0.0",
    port=8080,
    log_config=None,
    reload=True,
)
