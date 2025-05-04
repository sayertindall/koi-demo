import uvicorn

uvicorn.run(
    "coordinator_node.server:app",
    host="0.0.0.0",
    port=8080,
    log_config=None,
    reload=False,
)
