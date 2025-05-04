import shutil
import os
import logging  # Import logging
from rid_lib.types import KoiNetNode, KoiNetEdge
from koi_net import NodeInterface
from koi_net.protocol.node import NodeProfile, NodeType, NodeProvides

# Import from the new config loader
from .config_loader import BASE_URL, PORT  # Import BASE_URL as well

logger = logging.getLogger(__name__)  # Get logger instance

name = "coordinator"

# Keep identity/cache dir logic as it's node-specific state, not static config
identity_dir = f".koi/{name}"
cache_dir = f".koi/{name}/rid_cache_{name}"
# Remove existing directories if they exist
# Consider making this behavior optional or configurable
logger.info(
    f"Attempting to clear existing state directories: {identity_dir}, {cache_dir}"
)
shutil.rmtree(identity_dir, ignore_errors=True)
shutil.rmtree(cache_dir, ignore_errors=True)

# Recreate the directories
os.makedirs(identity_dir, exist_ok=True)
os.makedirs(cache_dir, exist_ok=True)
logger.info(f"Ensured state directories exist: {identity_dir}, {cache_dir}")


node = NodeInterface(
    name="coordinator",
    profile=NodeProfile(
        # Use the base_url loaded from the YAML config
        base_url=BASE_URL,
        node_type=NodeType.FULL,
        provides=NodeProvides(
            event=[KoiNetNode, KoiNetEdge], state=[KoiNetNode, KoiNetEdge]
        ),
    ),
    use_kobj_processor_thread=True,
    # Use resolved absolute paths for state files/dirs
    identity_file_path=os.path.abspath(f"{identity_dir}/{name}_identity.json"),
    event_queues_file_path=os.path.abspath(f"{identity_dir}/{name}_event_queues.json"),
    cache_directory_path=os.path.abspath(cache_dir),
)

# Import handlers after node is initialized
from . import handlers
