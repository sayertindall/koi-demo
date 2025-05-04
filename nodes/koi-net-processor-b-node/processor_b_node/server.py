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

# Import the query helper from handlers
from .handlers import query_note_index

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage node startup and shutdown."""
    logger.info("Starting Processor B lifespan...")
    try:
        node.start()
        logger.info("Processor B KOI-net node started successfully.")
    except Exception as e:
        logger.error(f"Failed to start KOI-net node: {e}", exc_info=True)
        raise RuntimeError("Failed to initialize KOI-net node") from e

    yield  # Application runs here

    logger.info("Shutting down Processor B...")
    try:
        node.stop()
        logger.info("Processor B KOI-net node stopped successfully.")
    except Exception as e:
        logger.error(f"Error stopping KOI-net node: {e}", exc_info=True)
    logger.info("Processor B shutdown complete.")


app = FastAPI(
    title="KOI-net Processor B Node (Note Indexer)",
    description="Processes HackMD notes and provides a search API.",
    version="0.1.0",
    lifespan=lifespan,
)

# --- KOI Protocol Router ---
koi_net_router = APIRouter(prefix="/koi-net")


@koi_net_router.post(BROADCAST_EVENTS_PATH)
async def broadcast_events_endpoint(req: EventsPayload):
    if not req.events:
        logger.debug("Received empty broadcast event list.")
        return {}
    logger.info(
        f"Request to {BROADCAST_EVENTS_PATH}, received {len(req.events)} event(s)"
    )
    for event in req.events:
        try:
            node.processor.handle(event=event, source=KnowledgeSource.External)
        except Exception as e:
            logger.error(
                f"Error handling broadcast event {event.rid}: {e}", exc_info=True
            )
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
        return EventsPayload(events=[])


@koi_net_router.post(FETCH_RIDS_PATH)
async def fetch_rids_endpoint(req: FetchRids) -> RidsPayload:
    logger.info(f"Request to {FETCH_RIDS_PATH} for types {req.rid_types}")
    try:
        return node.network.response_handler.fetch_rids(req)
    except Exception as e:
        logger.error(f"Error fetching RIDs: {e}", exc_info=True)
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
    if node and node.is_running():
        return {"status": "healthy", "node_status": "running"}
    else:
        return {"status": "unhealthy", "node_status": "stopped_or_not_initialized"}


app.include_router(koi_net_router)

# --- Custom Search API Router ---
search_router = APIRouter()


@search_router.get("/search")
async def search_notes_endpoint(q: str):
    """Endpoint to search the indexed note data."""
    if not q:
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required.")

    logger.info(f"Search request received: q='{q}'")
    try:
        # Use the helper function from handlers
        results = query_note_index(q)
        logger.info(f"Search for '{q}' yielded {len(results)} results.")
        return {"query": q, "results": results}
    except Exception as e:
        logger.error(f"Error during search for query '{q}': {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Internal server error during search."
        )


app.include_router(search_router)

logger.info("Processor B FastAPI application configured with KOI and Search routers.")
