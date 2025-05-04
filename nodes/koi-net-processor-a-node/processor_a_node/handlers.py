import logging

from .core import node
from koi_net.processor import ProcessorInterface
from koi_net.processor.handler import HandlerType
from koi_net.processor.knowledge_object import KnowledgeObject, KnowledgeSource
from koi_net.protocol.node import NodeProfile
from koi_net.protocol.event import EventType
from koi_net.protocol.edge import EdgeType
from koi_net.protocol.helpers import generate_edge_bundle
from rid_lib.types import KoiNetNode, KoiNetEdge
from rid_types.github import GithubCommit

# Import config to potentially check for specific sensor RID
from .config import GITHUB_SENSOR_RID

logger = logging.getLogger(__name__)

# Simple in-memory index (as defined in Processor.md)
# Structure: { sha: commit_message, keyword: [sha1, sha2, ...], ... }
search_index = {}


# --- Network Handlers ---
@node.processor.register_handler(HandlerType.Network, rid_types=[KoiNetNode])
def handle_network_discovery(processor: ProcessorInterface, kobj: KnowledgeObject):
    """Handles discovery of Coordinator and potential GitHub Sensor nodes."""
    if kobj.normalized_event_type != EventType.NEW:
        logger.debug(f"Ignoring non-NEW event for KoiNetNode {kobj.rid}")
        return

    # Basic validation of the discovered node's profile
    try:
        profile = kobj.bundle.validate_contents(NodeProfile)
        if not profile or not profile.provides:
            logger.warning(
                f"Received KoiNetNode event for {kobj.rid} with invalid/missing profile."
            )
            return
    except Exception as e:
        logger.warning(f"Could not validate NodeProfile for {kobj.rid}: {e}")
        return

    # --- Coordinator Handshake ---
    # Assume any node providing KoiNetNode *could* be a coordinator/peer
    # Propose edge back for bidirectional comms if it's not ourselves
    if kobj.rid != processor.identity.rid:
        logger.info(
            f"Discovered potential peer/coordinator: {kobj.rid}. Proposing edge."
        )
        try:
            edge_bundle = generate_edge_bundle(
                source=kobj.rid,  # The discovered node is the source
                target=processor.identity.rid,  # We are the target
                edge_type=EdgeType.WEBHOOK,
                rid_types=[KoiNetNode, KoiNetEdge],  # What we expect to exchange
            )
            processor.handle(bundle=edge_bundle)
        except Exception as e:
            logger.error(f"Failed edge proposal to {kobj.rid}: {e}", exc_info=True)

    # --- GitHub Sensor Discovery & Handshake ---
    # Check if the discovered node provides the RIDs we need (GithubCommit)
    # Note: Using string comparison since we don't have the actual RID class
    provides_github_commits = False

    # Use string comparison for RID type detection
    rid_type_str = "orn:github.commit"
    provides_event = [
        str(rt) for rt in profile.provides.event if hasattr(profile.provides, "event")
    ]
    provides_state = [
        str(rt) for rt in profile.provides.state if hasattr(profile.provides, "state")
    ]

    if rid_type_str in provides_event or rid_type_str in provides_state:
        provides_github_commits = True

    if provides_github_commits:
        # Check if a specific sensor RID is configured
        if GITHUB_SENSOR_RID and str(kobj.rid) != GITHUB_SENSOR_RID:
            logger.debug(
                f"Discovered GitHub sensor {kobj.rid}, but configured to connect only to {GITHUB_SENSOR_RID}. Ignoring."
            )
            return

        logger.info(f"Discovered GitHub Sensor: {kobj.rid}. Proposing edge.")
        try:
            # Propose an edge TO the sensor to receive events
            edge_bundle = generate_edge_bundle(
                source=kobj.rid,  # Sensor is the source of events
                target=processor.identity.rid,  # We are the target
                edge_type=EdgeType.WEBHOOK,
                rid_types=[GithubCommit],  # Specify we want GithubCommit events
            )
            processor.handle(bundle=edge_bundle)
            logger.info(f"Edge proposed to GitHub Sensor {kobj.rid}")
        except Exception as e:
            logger.error(
                f"Failed edge proposal to GitHub Sensor {kobj.rid}: {e}", exc_info=True
            )


# --- Manifest Handler ---


@node.processor.register_handler(HandlerType.Manifest, rid_types=[GithubCommit])
def handle_commit_manifest(processor: ProcessorInterface, kobj: KnowledgeObject):
    """Handles incoming commit manifests, triggers bundle fetch for indexing."""
    # Check if we can work with the RID
    try:
        rid = kobj.rid
        if not hasattr(rid, "reference"):
            logger.warning(
                f"Handler received RID without reference attribute: {rid}. Skipping."
            )
            return
    except Exception as e:
        logger.warning(f"Error checking RID {kobj.rid}: {e}")
        return

    manifest = kobj.manifest
    logger.info(f"Received manifest for commit: {rid.reference}")

    # PRD: Optionally dereference bundles. For indexing, we need the content.
    # Decision: Always dereference for this implementation.
    logger.debug(f"Requesting bundle for {rid} for indexing.")
    try:
        processor.handle(
            rid=rid, source=KnowledgeSource.External
        )  # Trigger bundle fetch
    except Exception as e:
        logger.error(f"Error requesting bundle for {rid}: {e}", exc_info=True)


# --- Bundle Handler ---


@node.processor.register_handler(HandlerType.Bundle, rid_types=[GithubCommit])
def handle_commit_bundle(processor: ProcessorInterface, kobj: KnowledgeObject):
    """Processes commit bundle contents and updates the search index."""
    # Check if we can work with the RID
    try:
        rid = kobj.rid
        if not hasattr(rid, "reference"):
            logger.warning(
                f"Handler received RID without reference attribute: {rid}. Skipping."
            )
            return
    except Exception as e:
        logger.warning(f"Error checking RID {kobj.rid}: {e}")
        return

    if not kobj.contents or not isinstance(kobj.contents, dict):
        logger.warning(f"Bundle for {kobj.rid} has no contents or invalid format.")
        return

    contents = kobj.contents
    sha = contents.get("sha")
    if not sha:
        logger.warning(
            f"Commit bundle {kobj.rid} missing SHA in contents. Skipping index update."
        )
        return

    logger.info(f"Processing bundle for commit: {sha[:7]}")

    # --- Update Search Index (Example Implementation) ---
    message = contents.get("message", "")

    # Clear old keyword associations for this SHA first if re-indexing
    for keyword, sha_list in list(search_index.items()):
        if isinstance(sha_list, list) and sha in sha_list:
            search_index[keyword].remove(sha)
            if not search_index[keyword]:  # Remove keyword if list becomes empty
                del search_index[keyword]

    # Index by full SHA
    search_index[sha] = message

    # Index by keywords (simple example)
    # Consider stemming, stop words, etc. for a real implementation
    keywords_processed = set()
    for keyword in message.lower().split():
        # Basic filtering: length > 3, alphanumeric, avoid duplicates per message
        if len(keyword) > 3 and keyword.isalnum() and keyword not in keywords_processed:
            if keyword not in search_index:
                search_index[keyword] = []
            # Add SHA to keyword list if not already present
            if sha not in search_index[keyword]:
                search_index[keyword].append(sha)
            keywords_processed.add(keyword)

    logger.debug(
        f"Updated search index for SHA: {sha[:7]}. Index size (keys): {len(search_index)}"
    )


# --- Helper for Search Endpoint ---
def query_search_index(query: str) -> list:
    """Queries the in-memory search index."""
    results = []
    query_lower = query.lower()

    # 1. Check if query is a SHA (full or partial >= 7 chars)
    if len(query) >= 7:
        # Check full SHA match
        if query in search_index and isinstance(search_index[query], str):
            # Need owner/repo to construct full RID - requires better index storage
            # For now, return SHA and message
            results.append(
                {
                    "sha": query,
                    "match_context": search_index[query][:100]
                    + "...",  # Truncate message
                }
            )
            return results  # Exact SHA match takes precedence

        # Check partial SHA match (less efficient)
        for sha_key, msg in search_index.items():
            # Ensure it's a SHA key (check length or type if index structure is mixed)
            if isinstance(msg, str) and sha_key.startswith(query):
                results.append({"sha": sha_key, "match_context": msg[:100] + "..."})
                # Optionally break after first partial match or collect all

    # 2. Check if query is a keyword
    if query_lower in search_index and isinstance(search_index[query_lower], list):
        for sha in search_index[query_lower]:
            # Avoid adding duplicates if already found via partial SHA match
            if not any(r["sha"] == sha for r in results):
                message = search_index.get(sha, "")  # Get message associated with SHA
                results.append({"sha": sha, "match_context": message[:100] + "..."})

    # 3. (Optional) Search within commit messages (less efficient)
    # for sha, message in search_index.items():
    #     if isinstance(message, str) and query_lower in message.lower():
    #         # Add logic to avoid duplicates
    #         results.append(...)

    return results


logger.info("Processor A handlers registered.")
