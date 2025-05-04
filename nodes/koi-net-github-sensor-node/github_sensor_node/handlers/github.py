import logging
from ..core import node
from ..types import GithubCommit

from koi_net.processor.handler import HandlerType
from koi_net.processor.knowledge_object import KnowledgeObject, KnowledgeSource
from koi_net.processor.interface import ProcessorInterface
from koi_net.protocol.node import NodeProfile
from koi_net.protocol.event import EventType
from koi_net.protocol.edge import EdgeType
from koi_net.protocol.helpers import generate_edge_bundle
from rid_lib.types import KoiNetNode

logger = logging.getLogger(__name__)


@node.processor.register_handler(HandlerType.Network, rid_types=[KoiNetNode])
def coordinator_contact(processor: ProcessorInterface, kobj: KnowledgeObject):
    """Handles discovery of the coordinator node (or other nodes providing KoiNetNode events).

    On discovering a NEW coordinator, proposes a WEBHOOK edge for bidirectional
    communication and requests a list of other known nodes (sync).
    (Based on refactor.md example)
    """
    if kobj.normalized_event_type != EventType.NEW:
        logger.debug(f"Ignoring non-NEW event for KoiNetNode {kobj.rid}")
        return

    try:
        profile = kobj.bundle.validate_contents(NodeProfile)
        if KoiNetNode not in profile.provides.event:
            logger.debug(
                f"Node {kobj.rid} does not provide KoiNetNode events. Ignoring."
            )
            return
    except Exception as e:
        logger.warning(f"Could not validate NodeProfile for {kobj.rid}: {e}")
        return

    logger.info(
        f"Identified potential coordinator/peer: {kobj.rid}; proposing WEBHOOK edge"
    )
    try:

        edge_bundle = generate_edge_bundle(
            source=kobj.rid,
            target=node.identity.rid,
            edge_type=EdgeType.WEBHOOK,
            rid_types=[KoiNetNode],
        )
        processor.handle(bundle=edge_bundle)
    except Exception as e:
        logger.error(
            f"Failed to generate or handle WEBHOOK edge bundle for {kobj.rid}: {e}",
            exc_info=True,
        )

    logger.info(f"Syncing network nodes from {kobj.rid}")
    try:
        payload = processor.network.request_handler.fetch_rids(
            kobj.rid, rid_types=[KoiNetNode]
        )
        if not payload or not payload.rids:
            logger.warning(f"Received empty RIDs payload from {kobj.rid} during sync.")
            return

        logger.debug(f"Received {len(payload.rids)} RIDs from {kobj.rid}")
        for rid in payload.rids:

            if rid == processor.identity.rid or processor.cache.exists(rid):
                continue
            logger.debug(f"Handling discovered RID from sync: {rid}")

            processor.handle(rid=rid, source=KnowledgeSource.External)
    except Exception as e:
        logger.error(f"Failed during network sync with {kobj.rid}: {e}", exc_info=True)


@node.processor.register_handler(HandlerType.Bundle, rid_types=[GithubCommit])
def handle_github_commit(processor: ProcessorInterface, kobj: KnowledgeObject):
    """
    Basic handler for processing GithubCommit bundles.
    Currently just logs information.

    Args:
        bundle: The Bundle object containing the GithubCommit RID and contents.
    """
    try:

        bundle = kobj.bundle
        rid: GithubCommit = bundle.rid
        contents: dict = bundle.contents

        logger.info(
            f"Processing commit: {rid} (Normalized Type: {kobj.normalized_event_type}, Source: {kobj.source})"
        )

        logger.debug(
            f"  Author: {contents.get('author_name')} <{contents.get('author_email')}>"
        )
        logger.debug(
            f"  Message: {contents.get('message', '').splitlines()[0][:80]}..."
        )
        logger.debug(f"  URL: {contents.get('html_url')}")

        return None

    except Exception as e:
        logger.error(
            f"Error handling GithubCommit bundle {kobj.rid}: {e}", exc_info=True
        )

        return None


@node.processor.register_handler(HandlerType.Bundle, rid_types=[GithubCommit])
def handle_github_commit_bundle(processor: ProcessorInterface, kobj: KnowledgeObject):
    """Example handler demonstrating processing before cache write."""
    logger.debug(f"Handling GithubCommit bundle PRE-CACHE for {kobj.rid}")

    try:

        if kobj.contents and "message" in kobj.contents:
            logger.info(
                f"Processing commit {kobj.rid.sha[:7]}: {kobj.contents['message'].splitlines()[0]}"
            )

        return None

    except Exception as e:
        logger.error(
            f"Error handling GithubCommit bundle {kobj.rid}: {e}", exc_info=True
        )

        return None


logger.info("GithubCommit Bundle handler registered.")
