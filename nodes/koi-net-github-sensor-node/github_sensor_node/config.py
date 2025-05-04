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
    CONFIG_BASE = Path("/config")
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

# --- Determine Run Context ---
is_docker = os.getenv("RUN_CONTEXT") == "docker" or CONFIG_MODE == "docker"

# --- Extract specific configurations with defaults ---
SENSOR_CONFIG: Dict[str, Any] = CONFIG.get("sensor", {})
EDGES_CONFIG: Dict[str, Any] = CONFIG.get("edges", {})
RUNTIME_CONFIG: Dict[str, Any] = CONFIG.get("runtime", {})
WEBHOOK_CONFIG: Dict[str, Any] = CONFIG.get("webhook", {})

# --- Context-Aware Configuration ---
LOCAL_DATA_BASE = Path("./.koi/github")  # Relative to workspace root for local runs

# Base configuration values (URLs are now directly from the correct mode's YAML)
MONITORED_REPOS: List[str] = SENSOR_CONFIG.get("repos", [])
POLL_INTERVAL: int = SENSOR_CONFIG.get("poll_interval", 60)
SENSOR_MODE: str = SENSOR_CONFIG.get("mode", "webhook")
HOST: str = RUNTIME_CONFIG.get("host", "0.0.0.0" if not is_docker else "0.0.0.0")
PORT: int = RUNTIME_CONFIG.get("port", 8001)
LOG_LEVEL: str = RUNTIME_CONFIG.get("log_level", "INFO").upper()
COORDINATOR_URL = EDGES_CONFIG.get("coordinator_url")
BASE_URL = RUNTIME_CONFIG.get("base_url")

# Adjust Cache and State Paths based on run context
DOCKER_CACHE_DIR = RUNTIME_CONFIG.get("cache_dir", "/data/cache")  # Default Docker path
DOCKER_STATE_FILE = RUNTIME_CONFIG.get(
    "state_file", os.path.join(DOCKER_CACHE_DIR, "github_state.json")
)

if is_docker:
    CACHE_DIR = DOCKER_CACHE_DIR
    STATE_FILE_PATH = (
        Path(DOCKER_STATE_FILE)
        if Path(DOCKER_STATE_FILE).is_absolute()
        else Path("/app") / DOCKER_STATE_FILE  # Assume /app if relative in Docker
    )
else:
    LOCAL_DATA_BASE.mkdir(parents=True, exist_ok=True)
    CACHE_DIR = str(LOCAL_DATA_BASE / "cache")
    STATE_FILE_PATH = LOCAL_DATA_BASE / "github_state.json"
    logger.debug(f"Using local CACHE_DIR: {CACHE_DIR}")
    logger.debug(f"Using local STATE_FILE_PATH: {STATE_FILE_PATH}")

# Ensure resolved CACHE_DIR exists
Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)

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
logger.info(f"  Monitored Repos: {MONITORED_REPOS}")
logger.info(f"  Coordinator URL: {COORDINATOR_URL}")
logger.info(f"  Runtime Base URL: {BASE_URL}")
logger.info(f"  Runtime Host: {HOST}")
logger.info(f"  Runtime Port: {PORT}")
logger.info(f"  Cache Dir: {CACHE_DIR}")
logger.info(f"  State File Path: {STATE_FILE_PATH}")
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
    """Loads the last processed SHA state from the JSON file specified by STATE_FILE_PATH."""
    global LAST_PROCESSED_SHA
    state_path = STATE_FILE_PATH
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

    state_path = STATE_FILE_PATH
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
