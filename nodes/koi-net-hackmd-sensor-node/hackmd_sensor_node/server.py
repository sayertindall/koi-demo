import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
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
from .backfill import perform_backfill


logger = logging.getLogger(__name__)


async def backfill_loop():
    while True:
        await asyncio.sleep(600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    node.start()

    yield
    node.stop()


app = FastAPI(lifespan=lifespan, title="KOI-net Protocol API", version="1.0.0")


koi_net_router = APIRouter(prefix="/koi-net")


@koi_net_router.post(BROADCAST_EVENTS_PATH)
def broadcast_events(req: EventsPayload):
    logger.info(
        f"Request to {BROADCAST_EVENTS_PATH}, received {len(req.events)} event(s)"
    )
    for event in req.events:
        logger.info(f"{event!r}")
        node.processor.handle(event=event, source=KnowledgeSource.External)


@koi_net_router.post(POLL_EVENTS_PATH)
def poll_events(req: PollEvents) -> EventsPayload:
    logger.info(f"Request to {POLL_EVENTS_PATH}")
    events = node.network.flush_poll_queue(req.rid)
    return EventsPayload(events=events)


@koi_net_router.post(FETCH_RIDS_PATH)
def fetch_rids(req: FetchRids) -> RidsPayload:
    return node.network.response_handler.fetch_rids(req)


@koi_net_router.post(FETCH_MANIFESTS_PATH)
def fetch_manifests(req: FetchManifests) -> ManifestsPayload:
    return node.network.response_handler.fetch_manifests(req)


@koi_net_router.post(FETCH_BUNDLES_PATH)
def fetch_bundles(req: FetchBundles) -> BundlesPayload:
    return node.network.response_handler.fetch_bundles(req)


# Add health endpoint
@koi_net_router.get("/health")
async def health():
    """Basic health check endpoint for Docker."""
    # Add more sophisticated checks if needed
    return {"status": "healthy"}


app.include_router(koi_net_router)
