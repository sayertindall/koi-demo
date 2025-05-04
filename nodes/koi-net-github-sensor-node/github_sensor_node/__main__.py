import uvicorn
import logging
from .config import HOST, PORT

logger = logging.getLogger(__name__)

logger.info(f"GitHub sensor node starting on {HOST}:{PORT}")
uvicorn.run(
    "github_sensor_node.server:app",
    host=HOST,
    port=PORT,
    log_config=None,
    reload=True,
)
