import logging
import hmac
import hashlib
import json
from fastapi import APIRouter, Request, Header, HTTPException, Body
from rid_lib.ext import Bundle
from .types import GithubCommit
from .core import node
from .config import (
    GITHUB_WEBHOOK_SECRET,
    MONITORED_REPOS,
    update_state_file,
    LAST_PROCESSED_SHA,
)

logger = logging.getLogger(__name__)

router = APIRouter()


async def verify_signature(request: Request, x_hub_signature_256: str = Header(None)):
    """Verify the GitHub webhook signature."""
    if not GITHUB_WEBHOOK_SECRET:
        logger.warning("Webhook verification skipped: GITHUB_WEBHOOK_SECRET not set.")
        return

    body = await request.body()
    hash_object = hmac.new(
        GITHUB_WEBHOOK_SECRET.encode("utf-8"), msg=body, digestmod=hashlib.sha256
    )
    expected_signature = "sha256=" + hash_object.hexdigest()

    if not hmac.compare_digest(expected_signature, x_hub_signature_256):
        logger.error(
            f"Webhook verification failed: Invalid signature. Expected: {expected_signature}, Got: {x_hub_signature_256}"
        )
        raise HTTPException(status_code=403, detail="Invalid signature")

    logger.debug("Webhook signature verified successfully.")


@router.post("/github/webhook", status_code=202)  # Use 202 Accepted as we process async
async def github_webhook(
    request: Request,
    x_github_event: str = Header(...),  # Required header
    x_hub_signature_256: str = Header(...),  # Required for verification
):
    """Handle incoming GitHub webhook events (specifically 'push')."""
    logger.info(f"Received GitHub webhook event: {x_github_event}")

    try:
        # --- Signature Verification (Optional) ---
        # await verify_signature(request, x_hub_signature_256)

        # --- Parse JSON Payload ---
        raw_body = await request.body()
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            logger.error("Invalid JSON in GitHub webhook payload")
            raise HTTPException(status_code=400, detail="Invalid JSON")

        # --- Event Handling ---
        if x_github_event == "ping":
            logger.info("Received 'ping' event from GitHub. Responding OK.")
            return {"message": "Pong!"}

        if x_github_event != "push":
            logger.debug(f"Ignoring non-'push' event: {x_github_event}")
            return {"message": f"Ignoring event type: {x_github_event}"}

        logger.info(f"Processing 'push' event: {payload}")

        # --- Process 'push' Event ---
        repo_info = payload.get("repository", {})
        repo_full_name = repo_info.get("full_name")
        repo_owner = repo_info.get("owner", {}).get("login") or repo_info.get(
            "owner", {}
        ).get("name")
        repo_name = repo_info.get("name")
        commits = payload.get("commits", [])
        head_commit = payload.get("head_commit", {})

        if not repo_full_name or not repo_owner or not repo_name:
            logger.error(f"Webhook payload missing repository details: {repo_info}")
            raise HTTPException(
                status_code=400, detail="Missing repository information in payload"
            )

        # Check if the repository is monitored
        if repo_full_name not in MONITORED_REPOS:
            logger.debug(
                f"Ignoring push event for non-monitored repository: {repo_full_name}"
            )
            return {"message": f"Repository {repo_full_name} not monitored"}

        if not commits and not head_commit:
            logger.warning(
                f"'push' event for {repo_full_name} received without 'commits' or 'head_commit' data. Possibly a branch deletion or tag push? Payload head: {payload.get('ref', '')}"
            )
            return {"message": "No commit data found in push event"}

        # Determine the commit(s) to process and the SHA to potentially update state with
        commits_to_process = []
        sha_to_update_state = None

        head_commit_id = head_commit.get("id")
        if head_commit_id:
            commits_to_process = [head_commit]  # Use head_commit as the primary source
            sha_to_update_state = (
                head_commit_id  # This is the SHA representing the push tip
            )
            logger.debug(f"Processing head_commit: {head_commit_id}")
        elif commits:
            commits_to_process = commits  # Fallback to commits list
            # If using commits list, the last commit's SHA is the best candidate for state update
            if commits:
                sha_to_update_state = commits[-1].get("id")
            logger.debug(
                f"Processing commits list (count: {len(commits)}). Potential state update SHA: {sha_to_update_state}"
            )
        else:
            # This case should ideally not be reached due to the check above, but included for completeness
            logger.warning(
                f"No processable commit data found in push event for {repo_full_name}. Skipping."
            )
            return {"message": "No processable commit data"}

        processed_new_commit = False
        for commit in commits_to_process:
            commit_sha = commit.get("id")
            if not commit_sha:
                logger.warning("Skipping commit in payload with missing 'id'.")
                continue

            # Avoid reprocessing the last known SHA for this repo
            last_known_sha_for_repo = LAST_PROCESSED_SHA.get(repo_full_name)
            if last_known_sha_for_repo and commit_sha == last_known_sha_for_repo:
                logger.debug(
                    f"Skipping commit {commit_sha} for {repo_full_name} as it matches last known SHA {last_known_sha_for_repo}."
                )
                continue

            # Inner try-except for processing individual commits within the push
            try:
                # Construct RID
                rid = GithubCommit(owner=repo_owner, repo=repo_name, sha=commit_sha)

                # Extract details - ensure keys exist
                author = commit.get("author", {})
                committer = commit.get("committer", {})

                contents = {
                    "sha": commit_sha,
                    "message": commit.get("message"),
                    "author_name": author.get("name"),
                    "author_email": author.get("email"),
                    "author_date": commit.get(
                        "timestamp"
                    ),  # GitHub often uses 'timestamp'
                    "committer_name": committer.get("name"),
                    "committer_email": committer.get("email"),
                    "committer_date": committer.get("timestamp"),
                    "html_url": commit.get("url"),  # Use 'url' from webhook payload
                    "parents": commit.get(
                        "parents", []
                    ),  # Typically a list of SHAs in webhook
                }

                bundle = Bundle.generate(rid=rid, contents=contents)
                # CORRECT USAGE: 'handle' makes the bundle available locally
                # in the sensor's cache/event queue for consumers to poll/fetch.
                # It does NOT push the application-specific GithubCommit bundle directly.
                logger.debug(
                    f"Making webhook commit bundle {rid} available locally via sensor API."
                )
                node.processor.handle(bundle=bundle)

                processed_new_commit = (
                    True  # Mark that we processed at least one new commit
                )

            except Exception as e:
                logger.error(
                    f"Error processing webhook commit {commit_sha} for {repo_full_name}: {e}",
                    exc_info=True,
                )
                # Decide whether to continue processing other commits in the push or stop
                continue  # Continue with next commit in the webhook push

        # Update state file only if we processed a new commit and have a valid SHA representing the push tip
        if processed_new_commit and sha_to_update_state:
            # Check again if the sha_to_update is different from the stored one before writing
            last_known_sha_for_repo = LAST_PROCESSED_SHA.get(repo_full_name)
            if sha_to_update_state != last_known_sha_for_repo:
                logger.info(
                    f"Webhook processing complete for {repo_full_name}. Updating state to SHA: {sha_to_update_state}"
                )
                update_state_file(repo_full_name, sha_to_update_state)
            else:
                logger.info(
                    f"Webhook processing complete for {repo_full_name}. State SHA {sha_to_update_state} already stored."
                )
        elif processed_new_commit:
            logger.warning(
                f"Webhook processing complete for {repo_full_name}. Processed new commit(s) but could not determine SHA for state update."
            )
        else:
            logger.info(
                f"Webhook processing complete for {repo_full_name}. No new commits processed or state updated."
            )

        return {"message": "Webhook processed successfully"}

    # Exception handlers are now correctly indented relative to the main 'try' block
    except HTTPException as he:
        # Re-raise HTTP exceptions to return proper status codes
        logger.warning(f"HTTP Exception during webhook processing: {he.detail}")
        raise he
    except Exception as e:
        logger.error(
            f"Unexpected error handling webhook event {x_github_event}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Internal server error handling webhook"
        )
