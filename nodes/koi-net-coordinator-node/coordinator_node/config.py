import logging
from ruamel.yaml import YAML
from pathlib import Path
import os
from typing import Dict, Any

# Configure basic logging early
logging.basicConfig(level=logging.INFO, format="%(name)s - %(message)s")
logger = logging.getLogger(__name__)

# --- Config Loader: Supports config/local and config/docker based on KOI_CONFIG_MODE and RUN_CONTEXT ---
CONFIG_MODE = os.environ.get("KOI_CONFIG_MODE", "local")
if os.environ.get("RUN_CONTEXT") == "docker":
    CONFIG_BASE = Path("/config")
else:
    CONFIG_BASE = Path(__file__).parent.parent.parent.parent / "config"
CONFIG_DIR = CONFIG_BASE / CONFIG_MODE

print(f"CONFIG_DIR: {CONFIG_DIR}")
print(f"CONFIG_MODE: {CONFIG_MODE}")

CONFIG_PATH = CONFIG_DIR / "coordinator.yaml"
ENV_PATH = CONFIG_DIR / "global.env"

# Load env vars from the selected global.env
if ENV_PATH.is_file():
    with open(ENV_PATH) as f:
        for line in f:
            if line.strip() and not line.startswith("#") and "=" in line:
                k, v = line.strip().split("=", 1)
                os.environ.setdefault(k, v)

# Load YAML config using ruamel.yaml
CONFIG = {}
if CONFIG_PATH.is_file():
    try:
        yaml_loader = YAML(typ="safe")
        with open(CONFIG_PATH) as f:
            CONFIG = yaml_loader.load(f)
        if CONFIG is None:  # Handle empty file case
            CONFIG = {}
    except Exception as e:
        logging.error(f"Error loading YAML config from {CONFIG_PATH}: {e}")
else:
    logging.error(f"Config file not found: {CONFIG_PATH}")

# --- End Config Loader ---

# --- Default Values --- #
DEFAULT_RUNTIME = {
    "port": 8080,
    "host": "0.0.0.0",
    "log_level": "INFO",
    "base_url": None,
    "cache_dir": None,
}

# --- Determine Run Context & Set Defaults ---
is_docker = os.getenv("RUN_CONTEXT") == "docker" or CONFIG_MODE == "docker"
RUNTIME_CONFIG: Dict[str, Any] = {**DEFAULT_RUNTIME, **CONFIG.get("runtime", {})}

# Adjust paths based on context
LOCAL_DATA_BASE = Path(".koi/shared_cache")  # Define a local base if needed
DOCKER_CACHE_DIR_DEFAULT = "/data/cache"  # Default for Docker

# Determine Cache Dir
# Prioritize environment variable, then YAML, then fallback
env_cache_dir = os.getenv("RID_CACHE_DIR")
yaml_cache_dir = RUNTIME_CONFIG.get("cache_dir")

if env_cache_dir:
    CACHE_DIR = env_cache_dir
elif yaml_cache_dir and "${RID_CACHE_DIR}" not in yaml_cache_dir:
    CACHE_DIR = yaml_cache_dir
else:
    # Fallback logic (adjust default as needed)
    CACHE_DIR = ".koi/shared_cache"
    logger.warning(
        f"RID_CACHE_DIR env var not set and yaml cache_dir missing or is placeholder. Falling back to default: {CACHE_DIR}"
    )

# Ensure the resolved CACHE_DIR exists
Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)

# Export specific values for easier access
PORT = RUNTIME_CONFIG.get("port")
HOST = RUNTIME_CONFIG.get("host")
LOG_LEVEL = RUNTIME_CONFIG.get("log_level", "INFO").upper()
BASE_URL = RUNTIME_CONFIG.get("base_url")

logger.info(
    f"Coordinator configured with MODE={CONFIG_MODE}, PORT={PORT}, BASE_URL={BASE_URL}, LOG_LEVEL={LOG_LEVEL}, CACHE_DIR={CACHE_DIR}"
)

# Check for required config
if not BASE_URL:
    logger.critical(
        "Configuration error: runtime.base_url is not set or resolved correctly."
    )
if not CACHE_DIR:
    logger.critical(
        "Configuration error: runtime.cache_dir is not set or resolved correctly."
    )
