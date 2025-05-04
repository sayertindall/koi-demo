import logging
import os
from ruamel.yaml import YAML
from pathlib import Path
from typing import Dict, Any

# Configure basic logging early
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Config Loader: Supports config/local and config/docker ---
CONFIG_MODE = os.environ.get("KOI_CONFIG_MODE", "local")
if os.environ.get("RUN_CONTEXT") == "docker":
    CONFIG_BASE = Path("/config")
    # In Docker, ensure KOI_CONFIG_MODE is set to docker if RUN_CONTEXT is docker
    if CONFIG_MODE != "docker":
        logger.warning(
            f"RUN_CONTEXT=docker but KOI_CONFIG_MODE='{CONFIG_MODE}'. Forcing KOI_CONFIG_MODE to 'docker'."
        )
        CONFIG_MODE = "docker"
else:
    # Assume local run, base path relative to this file's parent's parent
    CONFIG_BASE = Path(__file__).parent.parent.parent.parent / "config"
CONFIG_DIR = CONFIG_BASE / CONFIG_MODE

CONFIG_PATH = CONFIG_DIR / "processor-a.yaml"  # Specific config file
ENV_PATH = CONFIG_DIR / "global.env"

logger.info(f"Attempting to load config from: {CONFIG_PATH}")
logger.info(f"Attempting to load env from: {ENV_PATH}")

# Load env vars from the selected global.env first
if ENV_PATH.is_file():
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=ENV_PATH, override=True)
    logger.info(f"Loaded environment variables from {ENV_PATH}")
else:
    logger.warning(f"Global environment file not found at {ENV_PATH}")

# Load YAML config using ruamel.yaml
CONFIG = {}
if CONFIG_PATH.is_file():
    try:
        yaml_loader = YAML(typ="safe")
        with open(CONFIG_PATH) as f:
            CONFIG = yaml_loader.load(f)
        if CONFIG is None:  # Handle empty file case
            CONFIG = {}
        logger.info(f"Successfully loaded YAML config from {CONFIG_PATH}")
    except Exception as e:
        logger.error(f"Error loading YAML config from {CONFIG_PATH}: {e}")
else:
    logger.error(f"Processor A config file not found: {CONFIG_PATH}")

# --- End Config Loader ---

# --- Determine Run Context & Extract Settings ---
is_docker = os.getenv("RUN_CONTEXT") == "docker" or CONFIG_MODE == "docker"

RUNTIME_CONFIG: Dict[str, Any] = CONFIG.get("runtime", {})
EDGES_CONFIG: Dict[str, Any] = CONFIG.get("edges", {})
PROCESSOR_A_CONFIG: Dict[str, Any] = CONFIG.get(
    "processor_a", {}
)  # Processor specific settings

# --- Context-Aware Configuration ---
LOCAL_DATA_BASE = Path("./.koi/processor-a")  # Standard local path base
DOCKER_CACHE_DIR_DEFAULT = "/data/cache"  # Default for shared cache in Docker

# Base configuration values (URLs are now directly from the correct mode's YAML)
HOST: str = RUNTIME_CONFIG.get("host", "127.0.0.1" if not is_docker else "0.0.0.0")
PORT: int = RUNTIME_CONFIG.get("port", 8011)
LOG_LEVEL: str = RUNTIME_CONFIG.get("log_level", "INFO").upper()
BASE_URL = RUNTIME_CONFIG.get("base_url")  # Should be defined in yaml
COORDINATOR_URL = EDGES_CONFIG.get("coordinator_url")  # Should be defined in yaml

# Optional specific sensor RID
GITHUB_SENSOR_RID: str | None = PROCESSOR_A_CONFIG.get("github_sensor_rid")

# Determine Cache Dir
if is_docker:
    CACHE_DIR = RUNTIME_CONFIG.get("cache_dir", DOCKER_CACHE_DIR_DEFAULT)
else:
    # For local, use the config value or construct relative path
    cache_dir_config = RUNTIME_CONFIG.get("cache_dir")
    if cache_dir_config:
        CACHE_DIR = str(Path(cache_dir_config))  # Respect config if set
    else:
        LOCAL_DATA_BASE.mkdir(parents=True, exist_ok=True)
        CACHE_DIR = str(
            LOCAL_DATA_BASE / "cache"
        )  # Fallback local path relative to node state

# Ensure the resolved CACHE_DIR exists
Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)

# --- Update Logging Level Based on Config ---
try:
    logging.getLogger().setLevel(LOG_LEVEL.upper())
    # Set level for uvicorn access logs specifically if needed
    # logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logger.info(f"Logging level set to {LOG_LEVEL}")
except ValueError:
    logger.error(
        f"Invalid LOG_LEVEL '{LOG_LEVEL}' in configuration. Defaulting to INFO."
    )
    logging.getLogger().setLevel(logging.INFO)

# --- Log Loaded Config (Excluding Secrets) ---
logger.info("Processor A Configuration Loaded:")
logger.info(f"  Config Mode: {CONFIG_MODE}")
logger.info(f"  Is Docker Context: {is_docker}")
logger.info(f"  Runtime Base URL: {BASE_URL}")
logger.info(f"  Runtime Host: {HOST}")
logger.info(f"  Runtime Port: {PORT}")
logger.info(f"  Cache Dir: {CACHE_DIR}")
logger.info(f"  Coordinator URL: {COORDINATOR_URL}")
logger.info(f"  Specific GitHub Sensor RID: {GITHUB_SENSOR_RID or 'Not Set'}")

# Check required config
if not BASE_URL:
    logger.critical("Configuration error: runtime.base_url is not set.")
if not COORDINATOR_URL:
    logger.critical("Configuration error: edges.coordinator_url is not set.")
if not CACHE_DIR:
    logger.critical(
        "Configuration error: runtime.cache_dir is not set or resolved correctly."
    )
