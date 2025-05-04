import asyncio
import httpx
import logging
import requests
from .config import HACKMD_API_TOKEN

logger = logging.getLogger(__name__)

api_base_url = "https://api.hackmd.io/v1"


def request(path, method="GET"):
    resp = httpx.request(
        method=method,
        url=api_base_url + path,
        headers={"Authorization": "Bearer " + HACKMD_API_TOKEN},
    )

    if resp.status_code == 200:
        return resp.json()

    else:
        print(resp.status_code, resp.text)
        return


async def async_request(path, method="GET"):
    timeout = 60

    while True:
        async with httpx.AsyncClient() as client:

            resp = await client.request(
                method=method,
                url=api_base_url + path,
                headers={"Authorization": "Bearer " + HACKMD_API_TOKEN},
            )

        if resp.status_code == 200:
            return resp.json()

        elif resp.status_code == 429:
            print(resp.status_code, resp.text, f"retrying in {timeout} seconds")
            await asyncio.sleep(timeout)
            timeout *= 2
        else:
            print(resp.status_code, resp.text)
            return


def get_team_notes(team_path: str):
    """Fetch notes for a given HackMD team path."""
    # Check if token is available
    if not HACKMD_API_TOKEN:
        logger.error("HackMD API token is not configured. Cannot fetch team notes.")
        return []

    headers = {
        "Authorization": f"Bearer {HACKMD_API_TOKEN}",
    }
    try:
        # Use f-string for URL formatting
        response = requests.get(
            f"{api_base_url}/teams/{team_path}/notes", headers=headers
        )
        response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
        notes = response.json()
        logger.info(f"Successfully fetched {len(notes)} notes for team '{team_path}'")
        return notes
    except requests.exceptions.RequestException as e:
        logger.error(
            f"Error fetching HackMD notes for team '{team_path}': {e}", exc_info=True
        )
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching HackMD notes: {e}", exc_info=True)
        return []


def get_note_details(note_id: str):
    """Fetch the full details (including content) of a specific HackMD note by ID."""
    # Check if token is available
    if not HACKMD_API_TOKEN:
        logger.error("HackMD API token is not configured. Cannot fetch note details.")
        return None

    headers = {
        "Authorization": f"Bearer {HACKMD_API_TOKEN}",
    }
    try:
        # Use f-string for URL formatting
        response = requests.get(f"{api_base_url}/notes/{note_id}", headers=headers)
        response.raise_for_status()
        note_details = response.json()
        logger.debug(f"Successfully fetched details for note ID '{note_id}'")
        return note_details  # Return the full dictionary
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching HackMD note details for ID '{note_id}': {e}")
        return None
    except Exception as e:
        logger.error(
            f"Unexpected error fetching HackMD note details: {e}", exc_info=True
        )
        return None
