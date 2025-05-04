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
    # This path assumes nodes/ are sibling directories in the project root
    from nodes.koi_net_github_sensor_node.github_sensor_node.types import GithubCommit
except ImportError as e:
    logger.error(f"Failed to import GithubCommit: {e}. Ensure sensor node is accessible or use shared RID definitions. Using placeholder.")
    # Define a placeholder if import fails during scaffolding
    class GithubCommit:
        pass 

name = "processor-a"

# Identity directory setup - relative to where the node is run
identity_dir = f".koi/{name}"
os.makedirs(identity_dir, exist_ok=True)
logger.info(f"Ensured identity directory exists: {identity_dir}")

# Check required config values (basic check)
if not BASE_URL or not COORDINATOR_URL or not CACHE_DIR:
    # Config loader already logs critical errors, this is an extra safeguard
    raise ValueError("Essential configuration (BASE_URL, COORDINATOR_URL, CACHE_DIR) is missing or failed to load!")

# Initialize the KOI-net Node Interface for Processor A
node = NodeInterface(
    name=name,
    profile=NodeProfile(
        base_url=BASE_URL,
        node_type=NodeType.FULL,
        provides=NodeProvides( # Processor A provides no new RIDs per PRD
            event=[], 
            state=[]
        ),
        # Consumes GithubCommit implicitly via handlers
    ),
    use_kobj_processor_thread=True, # Run processing in a separate thread
    first_contact=COORDINATOR_URL,
    # Use absolute paths for state files to avoid ambiguity
    identity_file_path=os.path.abspath(f"{identity_dir}/{name}_identity.json"),
    event_queues_file_path=os.path.abspath(f"{identity_dir}/{name}_event_queues.json"),
    cache_directory_path=CACHE_DIR, # Use the resolved cache directory path
)

logger.info(f"Initialized NodeInterface for Processor A: {node.identity.rid}")
logger.info(f"Node attempting first contact with: {COORDINATOR_URL}")

# Import handlers after node is initialized to allow decorator registration
from . import handlers 