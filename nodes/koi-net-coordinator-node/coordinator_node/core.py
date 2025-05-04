import shutil
import os
import logging  # Import logging
from rid_lib.types import KoiNetNode, KoiNetEdge
from koi_net import NodeInterface
from koi_net.protocol.node import NodeProfile, NodeType, NodeProvides

# Import from the new config loader
from .config_loader import BASE_URL, PORT, CACHE_DIR  # Import BASE_URL, PORT, and CACHE_DIR

logger = logging.getLogger(__name__)  # Get logger instance

name = "coordinator"

# Keep identity/cache dir logic as it's node-specific state, not static config
identity_dir = f".koi/{name}"
# cache_dir = f".koi/{name}/rid_cache_{name}" # REMOVED - Using shared CACHE_DIR now

# Remove existing directories if they exist - REMOVED THESE LINES
# logger.info(
#     f"Attempting to clear existing state directories: {identity_dir}, {cache_dir}"
# )
# shutil.rmtree(identity_dir, ignore_errors=True)
# shutil.rmtree(cache_dir, ignore_errors=True)

# Recreate the directories - Ensure only identity_dir is created if needed
os.makedirs(identity_dir, exist_ok=True)
# os.makedirs(cache_dir, exist_ok=True) # REMOVED - Shared cache managed elsewhere
logger.info(f"Ensured identity directory exists: {identity_dir}")


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
    # Corrected to use shared CACHE_DIR from config
    cache_directory_path=CACHE_DIR,
)

# Import handlers after node is initialized
from . import handlers
