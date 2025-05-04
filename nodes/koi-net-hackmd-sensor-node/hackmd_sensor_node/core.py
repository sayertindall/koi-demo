import logging
import shutil
import os
from rid_types import HackMDNote
from koi_net import NodeInterface
from koi_net.protocol.node import NodeProfile, NodeType, NodeProvides
from koi_net.processor.default_handlers import (
    basic_rid_handler,
    edge_negotiation_handler,
    basic_network_output_filter,
)

# Import from refactored config
from .config import BASE_URL, COORDINATOR_URL, CACHE_DIR

logger = logging.getLogger(__name__)

name = "hackmd"

# Keep identity dir logic, cache dir comes from config
identity_dir = f".koi/{name}"
# cache_dir = f".koi/{name}/rid_cache_{name}" # Removed

# Clear existing identity directory - REMOVED
# logger.info(f"Attempting to clear existing identity directory: {identity_dir}")
# shutil.rmtree(identity_dir, ignore_errors=True)

# Recreate the identity directory - Ensure it exists
os.makedirs(identity_dir, exist_ok=True)
# os.makedirs(cache_dir, exist_ok=True) # Cache dir managed by Docker volume
logger.info(f"Ensured identity directory exists: {identity_dir}")

# Ensure required config values are present (already logged in config.py)
if not BASE_URL or not COORDINATOR_URL:
    # Optional: Raise error here if critical config is missing
    logger.critical(
        "Required configuration (BASE_URL or COORDINATOR_URL) missing. Node might not function correctly."
    )

node = NodeInterface(
    name="hackmd-sensor",
    profile=NodeProfile(
        # Use BASE_URL from config
        base_url=BASE_URL,
        node_type=NodeType.FULL,
        provides=NodeProvides(event=[HackMDNote], state=[HackMDNote]),
    ),
    use_kobj_processor_thread=True,
    # Use COORDINATOR_URL from config for first_contact
    first_contact=COORDINATOR_URL,
    handlers=[basic_rid_handler, edge_negotiation_handler, basic_network_output_filter],
    # Use absolute paths for state files/dirs
    identity_file_path=os.path.abspath(f"{identity_dir}/{name}_identity.json"),
    event_queues_file_path=os.path.abspath(f"{identity_dir}/{name}_event_queues.json"),
    # Use CACHE_DIR from config
    cache_directory_path=CACHE_DIR,
)

# Import handlers after node is initialized
from . import handlers
