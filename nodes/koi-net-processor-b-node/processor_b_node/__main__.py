import uvicorn
import logging

# Import HOST and PORT from config (will be defined there)
from .config import HOST, PORT

# Temporary values until config is implemented
# TEMP_HOST = "0.0.0.0"
# TEMP_PORT = 8012  # Default port for Processor B

logger = logging.getLogger(__name__)

logger.info(f"Processor B node starting on {HOST}:{PORT}")
uvicorn.run(
    "processor_b_node.server:app",  # Adjust app path
    host=HOST,
    port=PORT,
    log_config=None,
    reload=False,  # Enable reload for development
)
