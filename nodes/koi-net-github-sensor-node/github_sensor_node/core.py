import os
import shutil
import logging

from koi_net import NodeInterface
from koi_net.protocol.node import NodeProfile, NodeType, NodeProvides

# Import necessary config values from the refactored config module
from .config import (
    BASE_URL,
    COORDINATOR_URL,
    CACHE_DIR,
    LOG_LEVEL,
)  # Import necessary vars
from .types import GithubCommit

logger = logging.getLogger(__name__)

name = "github"

# Identity and cache directory paths remain relative for setup,
# but NodeInterface gets absolute paths derived from config
identity_dir = f".koi/{name}"
# Cache dir is now defined in config, use that path for NodeInterface
# cache_dir_setup = f".koi/{name}/rid_cache_{name}"

# Clear existing state directories logic remains the same
# Consider making this behavior optional or configurable
logger.info(f"Attempting to clear existing identity directory: {identity_dir}")
shutil.rmtree(identity_dir, ignore_errors=True)
# Cache dir managed by Docker volume, no need to clear here
# shutil.rmtree(cache_dir, ignore_errors=True)

# Recreate the identity directory
os.makedirs(identity_dir, exist_ok=True)
# Ensure cache directory exists within the container is handled by Docker volume mount implicitly
# os.makedirs(cache_dir, exist_ok=True)
logger.info(f"Ensured identity directory exists: {identity_dir}")

# Ensure required config values are present
if not BASE_URL:
    raise ValueError("Runtime base_url is not configured in github-sensor.yaml")
if not COORDINATOR_URL:
    raise ValueError("Edges coordinator_url is not configured in github-sensor.yaml")

# Initialize the KOI-net Node Interface for the GitHub Sensor
node = NodeInterface(
    name=name,
    profile=NodeProfile(
        # Use BASE_URL from config
        base_url=BASE_URL,
        node_type=NodeType.FULL,
        provides=NodeProvides(
            event=[GithubCommit],
            state=[GithubCommit],
        ),
    ),
    use_kobj_processor_thread=True,
    # Use COORDINATOR_URL from config for first_contact
    first_contact=COORDINATOR_URL,
    # State file paths are now relative to the application root in the container
    identity_file_path=os.path.abspath(f"{identity_dir}/{name}_identity.json"),
    event_queues_file_path=os.path.abspath(f"{identity_dir}/{name}_event_queues.json"),
    # Use CACHE_DIR from config (should be /data/cache)
    cache_directory_path=CACHE_DIR,
)

logger.info(f"Initialized NodeInterface: {node.identity.rid}")
logger.info(f"Node attempting first contact with: {COORDINATOR_URL}")
