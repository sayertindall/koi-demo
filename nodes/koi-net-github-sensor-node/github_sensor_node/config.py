import logging
import json
import os
from ruamel.yaml import YAML
from pathlib import Path
from typing import List, Dict, Any

# Configure basic logging early
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Config Loader: Supports config/local and config/docker based on KOI_CONFIG_MODE and RUN_CONTEXT ---
CONFIG_MODE = os.environ.get("KOI_CONFIG_MODE", "local")
if os.environ.get("RUN_CONTEXT") == "docker":
    CONFIG_PATH = Path("/app/config/config.yaml")
    ENV_PATH = Path("/app/config/global.env")
else:
    CONFIG_BASE = Path(__file__).parent.parent.parent.parent / "config"
    CONFIG_DIR = CONFIG_BASE / CONFIG_MODE
    CONFIG_PATH = CONFIG_DIR / "github-sensor.yaml"
    ENV_PATH = CONFIG_DIR / "global.env"

# Load env vars from the selected global.env
if ENV_PATH.is_file():
    with open(ENV_PATH) as f:
        for line in f:
            if line.strip() and not line.startswith("#") and "=" in line:
                k, v = line.strip().split("=", 1)
                os.environ.setdefault(
                    k, v
                )  # Use setdefault to avoid overriding existing env vars

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

# --- Determine Run Context & Extract Settings ---
is_docker = os.getenv("RUN_CONTEXT") == "docker" or CONFIG_MODE == "docker"

RUNTIME_CONFIG: Dict[str, Any] = CONFIG.get("runtime", {})
EDGES_CONFIG: Dict[str, Any] = CONFIG.get("edges", {})
SENSOR_CONFIG: Dict[str, Any] = CONFIG.get("sensor", {})
WEBHOOK_CONFIG: Dict[str, Any] = CONFIG.get("webhook", {})

# --- Context-Aware Configuration ---
LOCAL_DATA_BASE = Path("./.koi/github-sensor")  # Standard local path base
DOCKER_CACHE_DIR_DEFAULT = "/data/cache"
DOCKER_STATE_FILE_DEFAULT = "/data/github_state.json"

# Base configuration values
HOST: str = RUNTIME_CONFIG.get("host", "127.0.0.1" if not is_docker else "0.0.0.0")
PORT: int = RUNTIME_CONFIG.get("port", 8001)
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

# Determine State File Path (also prioritize env var if cache dir is used)
# Assume state file lives within the cache dir unless explicitly set elsewhere
env_state_file = os.getenv("GITHUB_STATE_FILE")
yaml_state_file = RUNTIME_CONFIG.get("state_file")

# Determine the state file path string first
state_file_path_str: str
if env_state_file:
    state_file_path_str = env_state_file
elif yaml_state_file and "${RID_CACHE_DIR}" in yaml_state_file and env_cache_dir:
    state_file_path_str = yaml_state_file.replace("${RID_CACHE_DIR}", env_cache_dir)
elif yaml_state_file and "${RID_CACHE_DIR}" not in yaml_state_file:
    state_file_path_str = yaml_state_file
else:
    default_filename = "github_state.json"
    # Ensure CACHE_DIR is a Path object before joining
    cache_dir_path = Path(CACHE_DIR)
    state_file_path_str = str(cache_dir_path / default_filename)
    logger.warning(
        f"GITHUB_STATE_FILE env var not set and yaml state_file missing or uses placeholder without RID_CACHE_DIR env var. Falling back to default: {state_file_path_str}"
    )

# Now convert the determined string path to a Path object
STATE_FILE = Path(state_file_path_str)

# Ensure directories exist using the Path object
Path(CACHE_DIR).mkdir(parents=True, exist_ok=True) # Ensure CACHE_DIR is also treated as Path if needed elsewhere
STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

# Sensor specific settings
SENSOR_KIND: str = SENSOR_CONFIG.get("kind", "github")
SENSOR_MODE: str = SENSOR_CONFIG.get("mode", "webhook")
MONITORED_REPOS: List[str] = SENSOR_CONFIG.get("repos", [])

# --- Load Secrets from Environment Variables ---
GITHUB_TOKEN: str | None = os.getenv("GITHUB_TOKEN")
WEBHOOK_SECRET_ENV_VAR: str | None = WEBHOOK_CONFIG.get("secret_env_var")
GITHUB_WEBHOOK_SECRET: str | None = None
if WEBHOOK_SECRET_ENV_VAR:
    GITHUB_WEBHOOK_SECRET = os.getenv(WEBHOOK_SECRET_ENV_VAR)
    if not GITHUB_WEBHOOK_SECRET:
        logger.warning(
            f"Environment variable '{WEBHOOK_SECRET_ENV_VAR}' specified in config but not found in environment."
        )
else:
    logger.warning("webhook.secret_env_var not specified in github-sensor.yaml")

# --- Update Logging Level Based on Config ---
try:
    logging.getLogger().setLevel(LOG_LEVEL)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("github").setLevel(logging.WARNING)
    logger.info(f"Logging level set to {LOG_LEVEL}")
except ValueError:
    logger.error(
        f"Invalid LOG_LEVEL '{LOG_LEVEL}' in configuration. Defaulting to INFO."
    )
    logging.getLogger().setLevel(logging.INFO)

# --- Log Loaded Config (Excluding Secrets) ---
logger.info("GitHub Sensor Configuration Loaded:")
logger.info(f"  Config Mode: {CONFIG_MODE}")
logger.info(f"  Is Docker Context: {is_docker}")
logger.info(f"  Sensor Mode: {SENSOR_MODE}")
logger.info(f"  Coordinator URL: {COORDINATOR_URL}")
logger.info(f"  Runtime Base URL: {BASE_URL}")
logger.info(f"  Runtime Host: {HOST}")
logger.info(f"  Runtime Port: {PORT}")
logger.info(f"  Cache Dir: {CACHE_DIR}")
logger.info(f"  State File Path: {STATE_FILE}")
logger.info(f"  GitHub Token Loaded: {bool(GITHUB_TOKEN)}")
logger.info(f"  Webhook Secret Loaded: {bool(GITHUB_WEBHOOK_SECRET)}")

# Check required config
if not COORDINATOR_URL:
    logger.critical(
        "Configuration error: edges.coordinator_url is not set or resolved correctly."
    )
if not BASE_URL:
    logger.critical(
        "Configuration error: runtime.base_url is not set or resolved correctly."
    )
if not GITHUB_WEBHOOK_SECRET:
    logger.warning("Configuration warning: GitHub Webhook Secret not loaded.")

# --- State Management (Loading initial state & update function) ---
LAST_PROCESSED_SHA: Dict[str, str] = {}  # Dictionary mapping repo_name -> last_sha


def load_state():
    """Loads the last processed SHA state from the JSON file specified by STATE_FILE."""
    global LAST_PROCESSED_SHA
    state_path = STATE_FILE
    try:
        with open(state_path, "r") as f:
            LAST_PROCESSED_SHA = json.load(f)
        logger.info(
            f"Loaded state from '{state_path}': Repos {list(LAST_PROCESSED_SHA.keys())}"
        )
    except FileNotFoundError:
        logger.warning(
            f"State file '{state_path}' not found. This is expected on first run. Starting with empty state (will perform full backfill)."
        )
        LAST_PROCESSED_SHA = {}
    except json.JSONDecodeError:
        logger.error(
            f"Error decoding JSON from state file '{state_path}'. Starting with empty state."
        )
        LAST_PROCESSED_SHA = {}
    except Exception as e:
        logger.error(
            f"Unexpected error loading state file '{state_path}': {e}",
            exc_info=True,
        )
        LAST_PROCESSED_SHA = {}


def update_state_file(repo_name: str, last_sha: str):
    """Updates the state file with the latest processed SHA for a repo."""
    global LAST_PROCESSED_SHA
    LAST_PROCESSED_SHA[repo_name] = last_sha
    
    state_path = STATE_FILE
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(state_path, "w") as f:
            json.dump(LAST_PROCESSED_SHA, f, indent=4)
        logger.debug(
            f"Updated state file '{state_path}' for {repo_name} with SHA: {last_sha}"
        )
    except IOError as e:
        logger.error(f"Failed to write state file '{state_path}': {e}")
    except Exception as e:
        logger.error(
            f"Unexpected error writing state file '{state_path}': {e}",
            exc_info=True,
        )


# Load initial state when config module is imported
load_state()
