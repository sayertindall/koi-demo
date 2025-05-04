import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, HTTPException

from koi_net.protocol.api_models import (
    PollEvents,
    FetchRids,
    FetchManifests,
    FetchBundles,
    EventsPayload,
    RidsPayload,
    ManifestsPayload,
    BundlesPayload,
)
from koi_net.protocol.consts import (
    BROADCAST_EVENTS_PATH,
    POLL_EVENTS_PATH,
    FETCH_RIDS_PATH,
    FETCH_MANIFESTS_PATH,
    FETCH_BUNDLES_PATH,
)
from koi_net.processor.knowledge_object import KnowledgeSource

from .core import node  # Import the initialized node instance

# Import the query helper and index from handlers
from .handlers import query_search_index, search_index

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage node startup and shutdown."""
    logger.info("Starting Processor A lifespan...")
    try:
        node.start()
        logger.info("Processor A KOI-net node started successfully.")
    except Exception as e:
        logger.error(f"Failed to start KOI-net node: {e}", exc_info=True)
        # Potentially exit or raise to prevent FastAPI from starting improperly
        raise RuntimeError("Failed to initialize KOI-net node") from e

    yield  # Application runs here

    logger.info("Shutting down Processor A...")
    try:
        node.stop()
        logger.info("Processor A KOI-net node stopped successfully.")
    except Exception as e:
        logger.error(f"Error stopping KOI-net node: {e}", exc_info=True)
    logger.info("Processor A shutdown complete.")


app = FastAPI(
    title="KOI-net Processor A Node (Repo Indexer)",
    description="Processes GitHub commits and provides a search API.",
    version="0.1.0",
    lifespan=lifespan,
)

# --- KOI Protocol Router ---
koi_net_router = APIRouter(prefix="/koi-net")


@koi_net_router.post(BROADCAST_EVENTS_PATH)
async def broadcast_events_endpoint(req: EventsPayload):
    # Basic validation
    if not req.events:
        logger.debug("Received empty broadcast event list.")
        return {}

    logger.info(
        f"Request to {BROADCAST_EVENTS_PATH}, received {len(req.events)} event(s)"
    )
    # Asynchronously handle each event to avoid blocking the endpoint
    for event in req.events:
        try:
            # Assuming node.processor.handle is thread-safe or handles async appropriately
            node.processor.handle(event=event, source=KnowledgeSource.External)
        except Exception as e:
            logger.error(
                f"Error handling broadcast event {event.rid}: {e}", exc_info=True
            )
            # Decide if one error should stop processing others
    return {}


@koi_net_router.post(POLL_EVENTS_PATH)
async def poll_events_endpoint(req: PollEvents) -> EventsPayload:
    logger.info(f"Request to {POLL_EVENTS_PATH} for {req.rid}")
    try:
        events = node.network.flush_poll_queue(req.rid)
        logger.debug(f"Returning {len(events)} events for {req.rid}")
        return EventsPayload(events=events)
    except Exception as e:
        logger.error(f"Error polling events for {req.rid}: {e}", exc_info=True)
        return EventsPayload(events=[])  # Return empty list on error


@koi_net_router.post(FETCH_RIDS_PATH)
async def fetch_rids_endpoint(req: FetchRids) -> RidsPayload:
    logger.info(f"Request to {FETCH_RIDS_PATH} for types {req.rid_types}")
    try:
        return node.network.response_handler.fetch_rids(req)
    except Exception as e:
        logger.error(f"Error fetching RIDs: {e}", exc_info=True)
        # Return empty payload or raise HTTP exception?
        return RidsPayload(rids=[])


@koi_net_router.post(FETCH_MANIFESTS_PATH)
async def fetch_manifests_endpoint(req: FetchManifests) -> ManifestsPayload:
    logger.info(
        f"Request to {FETCH_MANIFESTS_PATH} for types {req.rid_types}, rids {req.rids}"
    )
    try:
        return node.network.response_handler.fetch_manifests(req)
    except Exception as e:
        logger.error(f"Error fetching Manifests: {e}", exc_info=True)
        return ManifestsPayload(manifests=[], not_found=req.rids or [])


@koi_net_router.post(FETCH_BUNDLES_PATH)
async def fetch_bundles_endpoint(req: FetchBundles) -> BundlesPayload:
    logger.info(f"Request to {FETCH_BUNDLES_PATH} for rids {req.rids}")
    try:
        return node.network.response_handler.fetch_bundles(req)
    except Exception as e:
        logger.error(f"Error fetching Bundles: {e}", exc_info=True)
        return BundlesPayload(bundles=[], not_found=req.rids or [])


@koi_net_router.get("/health")
async def health():
    """Basic health check endpoint."""
    # Could add checks like node.is_running() if available
    if node and node.is_running():  # Basic check assuming is_running method exists
        return {"status": "healthy", "node_status": "running"}
    else:
        return {"status": "unhealthy", "node_status": "stopped_or_not_initialized"}


app.include_router(koi_net_router)

# --- Custom Search API Router ---
search_router = APIRouter()


@search_router.get("/search")
async def search_commits_endpoint(q: str):
    """Endpoint to search the indexed commit data."""
    if not q:
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required.")

    logger.info(f"Search request received: q='{q}'")
    try:
        # Use the helper function from handlers
        results = query_search_index(q)
        logger.info(f"Search for '{q}' yielded {len(results)} results.")
        # Note: The current index only returns SHA and context.
        # A real implementation would likely reconstruct the full RID.
        return {"query": q, "results": results}
    except Exception as e:
        logger.error(f"Error during search for query '{q}': {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Internal server error during search."
        )


# Include the custom search router *without* the /koi-net prefix
app.include_router(search_router)

logger.info("Processor A FastAPI application configured with KOI and Search routers.")
