import logging
import os
from ruamel.yaml import YAML
from pathlib import Path
from typing import Dict, Any
import json

# Configure basic logging early
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Config Loader: Supports config/local and config/docker based on KOI_CONFIG_MODE and RUN_CONTEXT ---
CONFIG_MODE = os.environ.get("KOI_CONFIG_MODE", "local")
if os.environ.get("RUN_CONTEXT") == "docker":
    CONFIG_PATH = Path("/config/config.yaml")
    ENV_PATH = Path("/config/global.env")
else:
    CONFIG_BASE = Path(__file__).parent.parent.parent.parent / "config"
    CONFIG_DIR = CONFIG_BASE / CONFIG_MODE
    CONFIG_PATH = CONFIG_DIR / "hackmd-sensor.yaml"
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

# --- Determine Run Context ---
is_docker = os.getenv("RUN_CONTEXT") == "docker" or CONFIG_MODE == "docker"

# --- Extract specific configurations with defaults ---
SENSOR_CONFIG: Dict[str, Any] = CONFIG.get("sensor", {})
EDGES_CONFIG: Dict[str, Any] = CONFIG.get("edges", {})
RUNTIME_CONFIG: Dict[str, Any] = CONFIG.get("runtime", {})
API_CONFIG: Dict[str, Any] = CONFIG.get("api", {})

# --- Context-Aware Configuration ---
LOCAL_DATA_BASE = Path("./.koi/hackmd-sensor")
DOCKER_CACHE_DIR_DEFAULT = "/data/cache"

# Base configuration values
HOST: str = RUNTIME_CONFIG.get("host", "127.0.0.1" if not is_docker else "0.0.0.0")
PORT: int = RUNTIME_CONFIG.get("port", 8002)
LOG_LEVEL: str = RUNTIME_CONFIG.get("log_level", "INFO").upper()
BASE_URL = RUNTIME_CONFIG.get("base_url")
COORDINATOR_URL = EDGES_CONFIG.get("coordinator_url")

# Determine Cache Dir
# Prioritize environment variable, then YAML, then fallback
env_cache_dir = os.getenv("RID_CACHE_DIR")
yaml_cache_dir = RUNTIME_CONFIG.get("cache_dir")

if env_cache_dir:
    CACHE_DIR = env_cache_dir
elif yaml_cache_dir and "${RID_CACHE_DIR}" not in yaml_cache_dir:
    CACHE_DIR = yaml_cache_dir
else:
    if is_docker:
        CACHE_DIR = DOCKER_CACHE_DIR_DEFAULT
    else:
        LOCAL_DATA_BASE.mkdir(parents=True, exist_ok=True)
        CACHE_DIR = str(LOCAL_DATA_BASE / "cache")
    logger.warning(
        f"RID_CACHE_DIR env var not set and yaml cache_dir missing or is placeholder. Falling back to default: {CACHE_DIR}"
    )

# Ensure the resolved CACHE_DIR exists
Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)

# Sensor specific settings
SENSOR_KIND: str = SENSOR_CONFIG.get("kind", "hackmd")
TEAM_PATH: str = SENSOR_CONFIG.get("team_path", "blockscience")
POLL_INTERVAL: int = SENSOR_CONFIG.get("poll_interval", 300)
TARGET_NOTE_IDS: list[str] = SENSOR_CONFIG.get("target_note_ids", [])

# --- Load Secrets from Environment Variables ---
TOKEN_ENV_VAR: str | None = API_CONFIG.get("token_env_var")
HACKMD_API_TOKEN: str | None = None
if TOKEN_ENV_VAR:
    HACKMD_API_TOKEN = os.getenv(TOKEN_ENV_VAR)
    if not HACKMD_API_TOKEN:
        logger.warning(
            f"Environment variable '{TOKEN_ENV_VAR}' specified in config but not found in environment."
        )
else:
    logger.warning("api.token_env_var not specified in hackmd-sensor.yaml")

# --- Update Logging Level Based on Config ---
try:
    logging.getLogger().setLevel(LOG_LEVEL)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logger.info(f"Logging level set to {LOG_LEVEL}")
except ValueError:
    logger.error(
        f"Invalid LOG_LEVEL '{LOG_LEVEL}' in configuration. Defaulting to INFO."
    )
    logging.getLogger().setLevel(logging.INFO)

# --- Log Loaded Config (Excluding Secrets) ---
logger.info("HackMD Sensor Configuration Loaded:")
logger.info(f"  Config Mode: {CONFIG_MODE}")
logger.info(f"  Is Docker Context: {is_docker}")
logger.info(f"  Team Path: {SENSOR_CONFIG.get('team_path', 'blockscience')}")
logger.info(f"  Poll Interval: {SENSOR_CONFIG.get('poll_interval', 300)}s")
logger.info(f"  Coordinator URL: {COORDINATOR_URL}")
logger.info(f"  Runtime Base URL: {BASE_URL}")
logger.info(f"  Runtime Host: {HOST}")
logger.info(f"  Runtime Port: {PORT}")
logger.info(f"  Cache Dir: {CACHE_DIR}")
logger.info(f"  HackMD Token Loaded: {bool(HACKMD_API_TOKEN)}")
logger.info(
    f"  Target Note IDs: {SENSOR_CONFIG.get('target_note_ids', []) if SENSOR_CONFIG.get('target_note_ids') else 'All notes in team'}"
)

# Check for required configuration
if not COORDINATOR_URL:
    logger.critical(
        "Configuration error: edges.coordinator_url is not set or resolved correctly."
    )
if not BASE_URL:
    logger.critical(
        "Configuration error: runtime.base_url is not set or resolved correctly."
    )
if not HACKMD_API_TOKEN:
    logger.warning(
        f"Configuration warning: HackMD API token not loaded (check '{TOKEN_ENV_VAR}' in global.env and config)"
    )

# --- State Management (Moved from __main__) ---
polling_state: Dict[str, str] = {}  # Maps note_id to last_modified_timestamp


def load_polling_state():
    """Loads the polling state from the JSON file specified by STATE_FILE_PATH."""
    global polling_state
    state_path = RUNTIME_CONFIG.get("state_file")
    if state_path:
        try:
            with open(state_path, "r") as f:
                polling_state = json.load(f)
            logger.info(f"Loaded polling state from {state_path}")
        except FileNotFoundError:
            logger.warning(
                f"Polling state file not found at {state_path}. This is expected on first run. Starting fresh."
            )
            polling_state = {}
        except json.JSONDecodeError:
            logger.error(
                f"Error decoding JSON from state file {state_path}. Starting fresh."
            )
            polling_state = {}
        except Exception as e:
            logger.error(
                f"Unexpected error loading polling state file {state_path}: {e}",
                exc_info=True,
            )
            polling_state = {}
    else:
        logger.warning("state_file not specified in runtime config")
        polling_state = {}


def save_polling_state():
    """Saves the current polling state to the JSON file specified by STATE_FILE_PATH."""
    global polling_state
    state_path = RUNTIME_CONFIG.get("state_file")
    if state_path:
        try:
            state_path.parent.mkdir(parents=True, exist_ok=True)
            with open(state_path, "w") as f:
                json.dump(polling_state, f, indent=4)
            logger.debug(f"Saved polling state to {state_path}")
        except IOError as e:
            logger.error(f"Failed to write polling state file {state_path}: {e}")
        except Exception as e:
            logger.error(
                f"Unexpected error writing polling state file {state_path}: {e}",
                exc_info=True,
            )
    else:
        logger.warning("state_file not specified in runtime config")


# Load initial state when config module is imported
load_polling_state()
