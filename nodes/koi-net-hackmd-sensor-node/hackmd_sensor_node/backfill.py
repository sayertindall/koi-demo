import logging
from datetime import datetime, timedelta
from .hackmd_api import get_team_notes, get_note_details
from rid_types import HackMDNote
from rid_lib.ext import Bundle
from .core import node

# Import TEAM_PATH and the new TARGET_NOTE_IDS from config
from .config import TEAM_PATH, TARGET_NOTE_IDS

logger = logging.getLogger(__name__)


# Define the type for the state dictionary for clarity
StateType = dict[str, str]  # Maps note_id to last_modified_timestamp


def perform_backfill(state: StateType):
    """Fetches all notes for the configured team, compares with state, and bundles new/updated notes."""
    logger.info(f"Starting HackMD backfill for team path: '{TEAM_PATH}'")
    if not TEAM_PATH:
        logger.error("HackMD team path is not configured. Backfill skipped.")
        return

    try:
        processed_count = 0
        bundled_count = 0

        # Decide whether to process specific notes or all team notes
        if TARGET_NOTE_IDS:
            logger.info(
                f"Targeting specific HackMD notes for backfill: {TARGET_NOTE_IDS}"
            )
            # Process only specified notes
            for note_id in TARGET_NOTE_IDS:
                processed_count += 1
                logger.debug(f"Fetching targeted note ID: {note_id}")
                # Fetch the full note details, including content and metadata
                note_details = get_note_details(note_id)
                if not note_details:
                    logger.warning(
                        f"Could not fetch details for targeted note ID {note_id}. Skipping."
                    )
                    continue

                last_modified_str = note_details.get("lastChangedAt")
                title = note_details.get(
                    "title", f"Note {note_id}"
                )  # Use ID if title missing

                if not last_modified_str:
                    logger.warning(
                        f"Skipping targeted note {note_id} due to missing lastChangedAt."
                    )
                    continue

                # Check state for this specific note
                if note_id not in state or last_modified_str > state[note_id]:
                    logger.info(
                        f"Processing targeted note '{title}' (ID: {note_id}) - New or updated."
                    )
                    # Content is already part of note_details if get_note_details fetches everything
                    note_content = note_details.get("content")
                    if note_content is None:
                        logger.error(
                            f"Content missing for note ID {note_id} even after fetch. Skipping."
                        )
                        continue

                    # Bundle the note (logic similar to below, adapted for note_details)
                    try:
                        rid = HackMDNote(note_id=note_id)
                        contents = {
                            "id": note_id,
                            "title": title,
                            "content": note_content,
                            "createdAt": note_details.get("createdAt"),
                            "lastChangedAt": last_modified_str,
                            "publishLink": note_details.get("publishLink"),
                            "tags": note_details.get("tags", []),
                        }
                        bundle = Bundle.generate(rid=rid, contents=contents)
                        logger.debug(
                            f"Making backfill targeted note bundle {rid} available locally."
                        )
                        node.processor.handle(bundle=bundle)
                        bundled_count += 1
                        state[note_id] = last_modified_str  # Update state
                    except Exception as e:
                        logger.error(
                            f"Error bundling targeted note {note_id}: {e}",
                            exc_info=True,
                        )
                else:
                    logger.debug(
                        f"Skipping targeted note '{title}' (ID: {note_id}) - Already up-to-date."
                    )

        else:
            # Original logic: process all notes in the team
            logger.info(f"Processing all notes in team path: '{TEAM_PATH}'")
            team_notes = get_team_notes(TEAM_PATH)
            if not team_notes:
                logger.warning(
                    f"No notes found or error fetching notes for team '{TEAM_PATH}'. Backfill ending."
                )
                return

            for note_summary in team_notes:
                processed_count += 1
                note_id = note_summary.get("id")
                last_modified_str = note_summary.get("lastChangedAt")
                title = note_summary.get("title")

                if not note_id or not last_modified_str:
                    logger.warning(
                        f"Skipping note from team list due to missing ID or lastChangedAt: {note_summary}"
                    )
                    continue

                # Check if note needs processing based on state
                if note_id not in state or last_modified_str > state[note_id]:
                    logger.info(
                        f"Processing note '{title}' (ID: {note_id}) from team list - New or updated."
                    )
                    # Fetch full content only when needed
                    note_details = get_note_details(
                        note_id
                    )  # Use get_note_details to get full details
                    if note_details is None or note_details.get("content") is None:
                        logger.error(
                            f"Failed to fetch content/details for note ID {note_id} from team list. Skipping."
                        )
                        continue
                    note_content = note_details.get("content")

                    try:
                        rid = HackMDNote(note_id=note_id)
                        contents = {
                            "id": note_id,
                            "title": title,
                            "content": note_content,
                            "createdAt": note_summary.get(
                                "createdAt"
                            ),  # Use summary data where possible
                            "lastChangedAt": last_modified_str,
                            "publishLink": note_summary.get("publishLink"),
                            "tags": note_summary.get("tags", []),
                        }
                        bundle = Bundle.generate(rid=rid, contents=contents)
                        logger.debug(
                            f"Making backfill note bundle {rid} from team list available locally."
                        )
                        node.processor.handle(bundle=bundle)
                        bundled_count += 1
                        state[note_id] = last_modified_str  # Update state

                    except Exception as e:
                        logger.error(
                            f"Error creating/handling bundle for note {note_id} from team list: {e}",
                            exc_info=True,
                        )
                else:
                    logger.debug(
                        f"Skipping note '{title}' (ID: {note_id}) from team list - Already up-to-date."
                    )

        logger.info(
            f"HackMD backfill complete. Processed {processed_count} notes, bundled {bundled_count} new/updated notes."
        )

    except Exception as e:
        logger.error(f"Unexpected error during HackMD backfill: {e}", exc_info=True)


# Note: The state persistence (load/save) should be handled by the caller
# (e.g., the polling mechanism in server.py or __main__.py)

if __name__ == "__main__":
    # Example usage (requires node setup and async context)
    # import asyncio
    # node.start()
    # asyncio.run(perform_backfill({}))
    # node.stop()
    pass  # Keep placeholder for potential direct execution
