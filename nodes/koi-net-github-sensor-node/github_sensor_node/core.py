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


identity_dir = f".koi/{name}"

# Recreate the identity directory
os.makedirs(identity_dir, exist_ok=True)

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
    first_contact=COORDINATOR_URL,
    identity_file_path=os.path.abspath(f"{identity_dir}/{name}_identity.json"),
    event_queues_file_path=os.path.abspath(f"{identity_dir}/{name}_event_queues.json"),
    cache_directory_path=CACHE_DIR,
)

logger.info(f"Initialized NodeInterface: {node.identity.rid}")
logger.info(f"Node attempting first contact with: {COORDINATOR_URL}")
