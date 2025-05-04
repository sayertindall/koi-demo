import logging
import logging.handlers
from rich.logging import RichHandler
from pathlib import Path

# Import LOG_LEVEL from config (will be defined there)
# from .config import LOG_LEVEL

# Temporary log level until config is implemented
TEMP_LOG_LEVEL = "INFO"

# Get the root logger
logger = logging.getLogger()
# Set the base level
logger.setLevel(TEMP_LOG_LEVEL)

# Create Rich Handler for console
rich_handler = RichHandler(rich_tracebacks=True)
rich_handler.setLevel(TEMP_LOG_LEVEL)
rich_format = "%(name)s - %(message)s"
rich_datefmt = "%Y-%m-%d %H:%M:%S"
rich_formatter = logging.Formatter(rich_format, datefmt=rich_datefmt)
rich_handler.setFormatter(rich_formatter)

# Create File Handler
log_dir = Path(".koi/processor-b")  # Adjust node name
log_dir.mkdir(parents=True, exist_ok=True)
log_file_path = log_dir / "processor-b-node-log.txt"

file_handler = logging.handlers.RotatingFileHandler(
    log_file_path, maxBytes=10 * 1024 * 1024, backupCount=3
)
file_handler.setLevel(TEMP_LOG_LEVEL)
file_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
file_datefmt = "%Y-%m-%d %H:%M:%S"
file_formatter = logging.Formatter(file_format, datefmt=file_datefmt)
file_handler.setFormatter(file_formatter)

# Clear existing handlers
if logger.hasHandlers():
    logger.handlers.clear()

# Add the handlers
logger.addHandler(rich_handler)
logger.addHandler(file_handler)

# Optional: Set specific levels for noisy libraries later in config.py
# logging.getLogger("uvicorn.error").setLevel(logging.WARNING)

logger.info(
    f"Logging configured (Level: {TEMP_LOG_LEVEL}). Console via Rich, File: {log_file_path}"
)
