import uvicorn
import asyncio
import logging
from .backfill import perform_backfill
from .config import HOST, PORT, POLL_INTERVAL, polling_state, save_polling_state
from .core import node
import threading
import time

logger = logging.getLogger(__name__)

stop_event = threading.Event()


def poll_hackmd():
    """Periodically polls HackMD using the backfill logic."""
    while not stop_event.is_set():
        logger.info("Polling HackMD...")
        try:
            perform_backfill(polling_state)
            save_polling_state()
        except Exception as e:
            logger.error(f"Error during HackMD polling loop: {e}", exc_info=True)

        # Wait for the configured interval or until stop event is set
        stop_event.wait(POLL_INTERVAL)


if __name__ == "__main__":
    logger.info(f"HackMD sensor node starting on {HOST}:{PORT}")
    logger.info(f"Polling HackMD every {POLL_INTERVAL} seconds.")

    # Start the KOI node processing thread
    node.start()

    # Start the polling thread
    polling_thread = threading.Thread(target=poll_hackmd, daemon=True)
    polling_thread.start()

    try:
        # Run the FastAPI server
        uvicorn.run(
            "hackmd_sensor_node.server:app",
            # Use HOST and PORT from config
            host=HOST,
            port=PORT,
            log_config=None,
            reload=True,
        )
    finally:
        # Signal threads to stop and wait for them
        logger.info("Shutting down HackMD sensor...")
        stop_event.set()
        polling_thread.join()
        node.stop()
        logger.info("HackMD sensor shut down gracefully.")
