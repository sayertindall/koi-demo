import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, Request, Body, Header, HTTPException
from koi_net.processor.knowledge_object import KnowledgeSource
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
from .core import node
from .webhook import router as github_router
from .backfill import perform_backfill
from .loader import register_handlers

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage node startup, backfill, and shutdown."""
    logger.info("Starting FastAPI application lifespan...")
    # Start the KOI-net node
    try:
        register_handlers()
        node.start()
        logger.info("KOI-net node started successfully.")
    except Exception as e:
        logger.error(f"Failed to start KOI-net node: {e}", exc_info=True)
        raise RuntimeError("Failed to initialize KOI-net node") from e

    logger.info("Scheduling initial GitHub backfill...")
    backfill_task = asyncio.to_thread(perform_backfill)

    try:
        yield  # Application runs here
    finally:
        logger.info("Shutting down FastAPI application...")
        # Attempt to gracefully cancel the backfill if it's still running
        # This might require more sophisticated task management if backfill is long-running
        # if backfill_task and not backfill_task.done():
        #     try:
        #         backfill_task.cancel()
        #         await backfill_task
        #     except asyncio.CancelledError:
        #         logger.info("Backfill task cancelled.")
        #     except Exception as e:
        #         logger.error(f"Error cancelling backfill task: {e}", exc_info=True)

        try:
            node.stop()
            logger.info("KOI-net node stopped successfully.")
        except Exception as e:
            logger.error(f"Error stopping KOI-net node: {e}", exc_info=True)
        logger.info("FastAPI application shutdown complete.")


app = FastAPI(
    title="KOI-net GitHub Sensor Node",
    description="Listens for GitHub webhooks and performs backfill to ingest commit data.",
    version="0.1.0",
    lifespan=lifespan,
)

koi_net_router = APIRouter(prefix="/koi-net")


@koi_net_router.post(BROADCAST_EVENTS_PATH)
async def broadcast_events_endpoint(req: EventsPayload):
    logger.info(
        f"Request to {BROADCAST_EVENTS_PATH}, received {len(req.events)} event(s)"
    )
    for event in req.events:
        node.processor.handle(event=event, source=KnowledgeSource.External)
    return {}


@koi_net_router.post(POLL_EVENTS_PATH)
async def poll_events_endpoint(req: PollEvents) -> EventsPayload:
    logger.info(f"Request to {POLL_EVENTS_PATH}")
    events = node.network.flush_poll_queue(req.rid)
    return EventsPayload(events=events)


@koi_net_router.post(FETCH_RIDS_PATH)
async def fetch_rids_endpoint(req: FetchRids) -> RidsPayload:
    logger.info(f"Request to {FETCH_RIDS_PATH} for types {req.rid_types}")
    return node.network.response_handler.fetch_rids(req)


@koi_net_router.post(FETCH_MANIFESTS_PATH)
async def fetch_manifests_endpoint(req: FetchManifests) -> ManifestsPayload:
    logger.info(
        f"Request to {FETCH_MANIFESTS_PATH} for types {req.rid_types}, rids {req.rids}"
    )
    manifests_payload = node.network.response_handler.fetch_manifests(req)
    return manifests_payload  # The default handler already includes not_found


@koi_net_router.post(FETCH_BUNDLES_PATH)
async def fetch_bundles_endpoint(req: FetchBundles) -> BundlesPayload:
    logger.info(f"Request to {FETCH_BUNDLES_PATH} for rids {req.rids}")
    bundles_payload = node.network.response_handler.fetch_bundles(req)
    return bundles_payload


@koi_net_router.get("/health")
async def health():
    """Basic health check endpoint for Docker."""
    # Add more sophisticated checks if needed, e.g., node.is_running()
    return {"status": "healthy"}


app.include_router(koi_net_router)  # KOI-net API endpoints
app.include_router(github_router)  # GitHub webhook endpoint

logger.info("FastAPI application configured with webhook and KOI-net routers.")
