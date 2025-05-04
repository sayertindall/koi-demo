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
from rid_types.hackmd import HackMDNote

# Import config to potentially check for specific sensor RID
from .config import HACKMD_SENSOR_RID


logger = logging.getLogger(__name__)

# Simple in-memory index (as defined in Processor.md)
# Structure:
# search_index = { "tag": [rid_str1, rid_str2], "title_word": [rid_str1, rid_str3], note_id: [rid_str] }
# note_metadata = { rid_str: {"title": title, "tags": tags, "lastChangedAt": ts}}
search_index = {}
note_metadata = {}


# --- Network Handlers ---
@node.processor.register_handler(HandlerType.Network, rid_types=[KoiNetNode])
def handle_network_discovery(processor: ProcessorInterface, kobj: KnowledgeObject):
    """Handles discovery of Coordinator and potential HackMD Sensor nodes."""
    if kobj.normalized_event_type != EventType.NEW:
        logger.debug(f"Ignoring non-NEW event for KoiNetNode {kobj.rid}")
        return

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

    # --- Coordinator/Peer Handshake ---
    if kobj.rid != processor.identity.rid:
        logger.info(
            f"Discovered potential peer/coordinator: {kobj.rid}. Proposing edge."
        )
        try:
            edge_bundle = generate_edge_bundle(
                source=kobj.rid,
                target=processor.identity.rid,
                edge_type=EdgeType.WEBHOOK,
                rid_types=[KoiNetNode, KoiNetEdge],
            )
            processor.handle(bundle=edge_bundle)
        except Exception as e:
            logger.error(f"Failed edge proposal to {kobj.rid}: {e}", exc_info=True)

    # --- HackMD Sensor Discovery & Handshake ---
    provides_hackmd_notes = False
    if HackMDNote != object:  # Check if HackMDNote was imported successfully
        # Check if the node provides HackMDNote events or state
        if HackMDNote in profile.provides.event or HackMDNote in profile.provides.state:
            provides_hackmd_notes = True

    if provides_hackmd_notes:
        # Check if a specific sensor RID is configured
        if HACKMD_SENSOR_RID and str(kobj.rid) != HACKMD_SENSOR_RID:
            logger.debug(
                f"Discovered HackMD sensor {kobj.rid}, but configured to connect only to {HACKMD_SENSOR_RID}. Ignoring."
            )
            return

        logger.info(f"Discovered HackMD Sensor: {kobj.rid}. Proposing edge.")
        try:
            # Propose an edge TO the sensor to receive events
            edge_bundle = generate_edge_bundle(
                source=kobj.rid,  # Sensor is the source
                target=processor.identity.rid,  # We are the target
                edge_type=EdgeType.WEBHOOK,
                rid_types=[HackMDNote],  # We want HackMDNote events
            )
            processor.handle(bundle=edge_bundle)
            logger.info(f"Edge proposed to HackMD Sensor {kobj.rid}")
        except Exception as e:
            logger.error(
                f"Failed edge proposal to HackMD Sensor {kobj.rid}: {e}", exc_info=True
            )


# --- Manifest Handler ---
@node.processor.register_handler(HandlerType.Manifest, rid_types=[HackMDNote])
def handle_note_manifest(processor: ProcessorInterface, kobj: KnowledgeObject):
    """Handles incoming note manifests, triggers bundle fetch for indexing."""
    if HackMDNote == object:
        logger.error("HackMDNote type not properly imported. Cannot process manifests.")
        return

    if not isinstance(kobj.rid, HackMDNote):
        logger.warning(f"Handler received non-HackMDNote RID: {kobj.rid}. Skipping.")
        return

    manifest = kobj.manifest
    rid: HackMDNote = kobj.rid
    logger.info(f"Received manifest for HackMD note: {rid.reference}")

    # PRD: Always dereference notes for indexing.
    logger.debug(f"Requesting bundle for {rid} for indexing.")
    try:
        processor.handle(
            rid=rid, source=KnowledgeSource.External
        )  # Trigger bundle fetch
    except Exception as e:
        logger.error(f"Error requesting bundle for {rid}: {e}", exc_info=True)


# --- Bundle Handler ---
@node.processor.register_handler(HandlerType.Bundle, rid_types=[HackMDNote])
def handle_note_bundle(processor: ProcessorInterface, kobj: KnowledgeObject):
    """Processes note bundle contents and updates the search index."""
    if HackMDNote == object:
        logger.error("HackMDNote type not properly imported. Cannot process bundles.")
        return

    if not isinstance(kobj.rid, HackMDNote):
        logger.warning(f"Handler received non-HackMDNote RID: {kobj.rid}. Skipping.")
        return

    if not kobj.contents or not isinstance(kobj.contents, dict):
        logger.warning(f"Bundle for {kobj.rid} has no contents or invalid format.")
        return

    rid: HackMDNote = kobj.rid
    contents = kobj.contents
    rid_str = str(rid)  # Use string representation for dict keys
    note_id = rid.note_id
    title = contents.get("title", f"Note {note_id}")  # Use ID if title missing

    logger.info(f"Processing bundle for note: {note_id} - '{title}'")

    # --- Check Timestamp to Avoid Re-indexing ---
    last_changed = contents.get("lastChangedAt")
    if rid_str in note_metadata and last_changed == note_metadata[rid_str].get(
        "lastChangedAt"
    ):
        logger.debug(
            f"Note {note_id} has not changed ({last_changed}) since last index. Skipping."
        )
        return

    # --- Update Metadata Cache ---
    current_tags = contents.get("tags", [])
    note_metadata[rid_str] = {
        "title": title,
        "tags": current_tags,
        "lastChangedAt": last_changed,
    }

    # --- Update Search Index (Example: Tags, Title words, Note ID) ---
    # Clear old index entries for this note first
    for key, rid_list in list(search_index.items()):
        if isinstance(rid_list, list) and rid_str in rid_list:
            search_index[key].remove(rid_str)
            # Remove key if list becomes empty after removing the RID
            if not search_index[key]:
                del search_index[key]

    # Index by tags
    for tag in current_tags:
        tag_key = tag.lower()  # Case-insensitive tag indexing
        if tag_key not in search_index:
            search_index[tag_key] = []
        # Avoid adding duplicates if somehow the clear logic failed
        if rid_str not in search_index[tag_key]:
            search_index[tag_key].append(rid_str)

    # Index by title words
    for word in title.lower().split():
        if len(word) > 2:  # Basic filtering
            if word not in search_index:
                search_index[word] = []
            if rid_str not in search_index[word]:
                search_index[word].append(rid_str)

    # Index by note ID itself for direct lookup
    note_id_key = note_id  # Use the actual note ID as the key
    if note_id_key not in search_index:
        search_index[note_id_key] = []
    if rid_str not in search_index[note_id_key]:
        search_index[note_id_key].append(rid_str)

    # Note: Markdown content parsing is omitted as per simplified scope.
    # md_content = contents.get("content", "")
    # If implemented, parse md_content and add relevant keywords/entities to search_index.

    logger.debug(
        f"Updated search index for note {note_id}. Index size (keys): {len(search_index)}"
    )


# --- Helper for Search Endpoint ---
def query_note_index(query: str) -> list:
    """Queries the in-memory note search index."""
    results_rids = set()  # Use a set to automatically handle duplicates
    query_lower = query.lower()

    # 1. Check if query is a direct Note ID match
    if query in search_index and isinstance(search_index[query], list):
        results_rids.update(search_index[query])

    # 2. Check if query matches a tag (case-insensitive)
    if query_lower in search_index and isinstance(search_index[query_lower], list):
        results_rids.update(search_index[query_lower])

    # 3. Check if query matches a title word (case-insensitive)
    if query_lower in search_index and isinstance(search_index[query_lower], list):
        results_rids.update(search_index[query_lower])

    # Format results using metadata cache
    results = []
    for rid_str in results_rids:
        meta = note_metadata.get(rid_str, {})  # Get cached metadata
        results.append(
            {
                "rid": rid_str,
                "title": meta.get("title", "N/A"),
                "tags": meta.get("tags", []),
            }
        )

    # Optional: Sort results, e.g., alphabetically by title
    results.sort(key=lambda x: x.get("title", "").lower())

    return results


logger.info("Processor B handlers registered.")
