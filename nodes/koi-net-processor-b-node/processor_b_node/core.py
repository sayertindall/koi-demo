import os
import logging

from koi_net import NodeInterface
from koi_net.protocol.node import NodeProfile, NodeType, NodeProvides

# Import necessary config values from the final config loader
from .config import (
    BASE_URL,
    COORDINATOR_URL,
    CACHE_DIR,
) 

# Import the RID type this processor consumes
logger = logging.getLogger(__name__) 
try:
    # Attempt import - adjust path if project structure changes
    from nodes.koi_net_hackmd_sensor_node.rid_types import HackMDNote
except ImportError as e:
    logger.error(f"Failed to import HackMDNote: {e}. Ensure sensor node is accessible or use shared RID definitions. Using placeholder.")
    # Define a placeholder if import fails
    class HackMDNote:
        pass 

name = "processor-b"

# Identity directory setup
identity_dir = f".koi/{name}"
os.makedirs(identity_dir, exist_ok=True)
logger.info(f"Ensured identity directory exists: {identity_dir}")

# Check required config values
if not BASE_URL or not COORDINATOR_URL or not CACHE_DIR:
    raise ValueError("Essential configuration (BASE_URL, COORDINATOR_URL, CACHE_DIR) is missing or failed to load!")

# Initialize the KOI-net Node Interface for Processor B
node = NodeInterface(
    name=name,
    profile=NodeProfile(
        base_url=BASE_URL,
        node_type=NodeType.FULL,
        provides=NodeProvides( # Processor B provides no new RIDs per PRD
            event=[], 
            state=[]
        ),
        # Consumes HackMDNote implicitly via handlers
    ),
    use_kobj_processor_thread=True,
    first_contact=COORDINATOR_URL,
    identity_file_path=os.path.abspath(f"{identity_dir}/{name}_identity.json"),
    event_queues_file_path=os.path.abspath(f"{identity_dir}/{name}_event_queues.json"),
    cache_directory_path=CACHE_DIR,
)

logger.info(f"Initialized NodeInterface for Processor B: {node.identity.rid}")
logger.info(f"Node attempting first contact with: {COORDINATOR_URL}")

# Import handlers after node is initialized
from . import handlers 