import logging
import logging.handlers
from rich.logging import RichHandler
from pathlib import Path  # Import Path

# Import LOG_LEVEL from refactored config
from .config import LOG_LEVEL

# Get the root logger
logger = logging.getLogger()
# Set the base level from config
logger.setLevel(LOG_LEVEL)

# Create Rich Handler for console (use configured level)
rich_handler = RichHandler(rich_tracebacks=True)
rich_handler.setLevel(LOG_LEVEL)
rich_format = "%(name)s - %(message)s"
rich_datefmt = "%Y-%m-%d %H:%M:%S"
rich_formatter = logging.Formatter(rich_format, datefmt=rich_datefmt)
rich_handler.setFormatter(rich_formatter)

# Create File Handler (use configured level, more verbose format)
log_dir = Path(".koi/hackmd")
log_dir.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
log_file_path = log_dir / "hackmd-sensor-node-log.txt"

file_handler = logging.handlers.RotatingFileHandler(
    log_file_path, maxBytes=10 * 1024 * 1024, backupCount=3
)  # 10MB, 3 backups
file_handler.setLevel(LOG_LEVEL)
file_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
file_datefmt = "%Y-%m-%d %H:%M:%S"
file_formatter = logging.Formatter(file_format, datefmt=file_datefmt)
file_handler.setFormatter(file_formatter)

# Clear existing handlers (optional, prevents duplicate handlers on reload)
if logger.hasHandlers():
    logger.handlers.clear()

# Add the handlers
logger.addHandler(rich_handler)
logger.addHandler(file_handler)

# Optional: Set specific levels for noisy libraries
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)

logger.info(
    f"Logging configured (Level: {LOG_LEVEL}). Console via Rich, File: {log_file_path}"
)

# Logging level is now set globally based on config,
# specific logger level adjustments can happen in config.py
