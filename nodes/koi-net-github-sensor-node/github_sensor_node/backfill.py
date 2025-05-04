import logging
from github import Github, GithubException, RateLimitExceededException
from github.Commit import Commit
from rid_lib.ext import Bundle

# Assuming GithubCommit RID type is accessible
from .types import GithubCommit
from .core import node

# Import necessary config values
from .config import GITHUB_TOKEN, MONITORED_REPOS, LAST_PROCESSED_SHA, update_state_file

logger = logging.getLogger(__name__)

# Initialize GitHub client (authenticated if token provided)
# Use the GITHUB_TOKEN loaded from config
github_client = Github(GITHUB_TOKEN) if GITHUB_TOKEN else Github()
logger.info(f"GitHub client initialized. Authenticated: {bool(GITHUB_TOKEN)}")


def perform_backfill():
    """
    One-time startup backfill: fetch all commits since LAST_PROCESSED_SHA
    for each monitored repo, bundle them as NEW, and persist the latest SHA processed.
    Processes commits oldest-to-newest after fetching.
    """
    logger.info("Starting GitHub backfill process...")

    # Load the state dictionary once before the loop
    current_state = (
        LAST_PROCESSED_SHA.copy()
    )  # Use a copy to avoid modifying during iteration if needed
    newest_sha_processed_overall_map = (
        {}
    )  # Track newest SHA per repo processed in this run

    if not MONITORED_REPOS:
        logger.warning(
            "No repositories configured in MONITORED_REPOS. Backfill skipped."
        )
        return

    for repo_full_name in MONITORED_REPOS:
        try:
            owner, repo_name_only = repo_full_name.split("/")
            # Get the last processed SHA for *this specific repository*
            last_sha_for_repo = current_state.get(repo_full_name)
            logger.info(
                f"Backfilling repository: {repo_full_name} since SHA: {last_sha_for_repo or 'beginning'}"
            )

            gh_repo = github_client.get_repo(repo_full_name)
            commits_to_process_buffer: list[Commit] = []

            # Iterate commits newest-first until we find the last processed one
            paginated_commits = gh_repo.get_commits()
            logger.debug(f"Fetching commits for {repo_full_name}...")
            commit_count = 0
            for commit in paginated_commits:
                commit_count += 1
                # Check against the specific SHA for this repo
                if last_sha_for_repo and commit.sha == last_sha_for_repo:
                    logger.info(
                        f"Found last processed SHA {last_sha_for_repo} in {repo_full_name}. Stopping fetch for this repo."
                    )
                    break
                commits_to_process_buffer.append(commit)
                # Safety break for potentially huge repos without a known SHA
                # Adjust limit as needed
                if commit_count % 100 == 0:
                    logger.debug(
                        f"Fetched {commit_count} commits for {repo_full_name} so far..."
                    )
                # if commit_count > 1000:
                #    logger.warning(f"Reached fetch limit (1000) for {repo_full_name}. Consider adjusting.")
                #    break

            logger.info(
                f"Found {len(commits_to_process_buffer)} new commits in {repo_full_name} to backfill."
            )

            # Process commits oldest → newest
            newest_sha_processed_in_repo = None
            for commit in reversed(commits_to_process_buffer):
                try:
                    rid = GithubCommit(owner=owner, repo=repo_name_only, sha=commit.sha)
                    # Extract commit details carefully, handling potential missing attributes
                    author = commit.commit.author
                    committer = commit.commit.committer

                    contents = {
                        "sha": commit.sha,
                        "message": commit.commit.message,
                        "author_name": author.name if author else None,
                        "author_email": author.email if author else None,
                        "author_date": (
                            author.date.isoformat() if author and author.date else None
                        ),
                        "committer_name": committer.name if committer else None,
                        "committer_email": committer.email if committer else None,
                        "committer_date": (
                            committer.date.isoformat()
                            if committer and committer.date
                            else None
                        ),
                        "html_url": commit.html_url,
                        "parents": [
                            p.sha for p in commit.parents
                        ],  # List of parent SHAs
                    }
                    bundle = Bundle.generate(rid=rid, contents=contents)
                    # CORRECT USAGE: 'handle' makes the bundle available locally
                    # in the sensor's cache/event queue for consumers to poll/fetch.
                    # It does NOT push the application-specific GithubCommit bundle directly.
                    logger.debug(
                        f"Making backfill commit bundle {rid} available locally via sensor API."
                    )
                    node.processor.handle(bundle=bundle)

                    # Track the newest SHA processed in this run for this repo
                    newest_sha_processed_in_repo = commit.sha

                except Exception as e:
                    logger.error(
                        f"Error processing commit {commit.sha} in {repo_full_name}: {e}",
                        exc_info=True,
                    )

            # Store the newest SHA processed for this repo during this run
            if newest_sha_processed_in_repo:
                newest_sha_processed_overall_map[repo_full_name] = (
                    newest_sha_processed_in_repo
                )
                logger.debug(
                    f"Newest SHA processed for {repo_full_name} in this run: {newest_sha_processed_in_repo}"
                )

        except RateLimitExceededException:
            logger.error(
                f"GitHub API rate limit exceeded while backfilling {repo_full_name}. Aborting backfill. Try again later or use a GITHUB_TOKEN."
            )
            # Depending on requirements, could wait and retry, but for now, we stop.
            return  # Stop the entire backfill process
        except GithubException as e:
            logger.error(
                f"GitHub API error for repository {repo_full_name}: {e}. Skipping this repo."
            )
            continue  # Skip to the next repository
        except Exception as e:
            logger.error(
                f"Unexpected error backfilling repository {repo_full_name}: {e}",
                exc_info=True,
            )
            continue  # Skip to the next repository

    # After processing all repos, persist the newest SHAs found (if changed)
    updated_count = 0
    for repo_full_name, newest_sha in newest_sha_processed_overall_map.items():
        if newest_sha != current_state.get(repo_full_name):
            update_state_file(
                repo_full_name, newest_sha
            )  # Call function from config.py
            updated_count += 1
        else:
            logger.debug(
                f"No state update needed for {repo_full_name}, newest SHA {newest_sha} is same as stored."
            )

    if updated_count > 0:
        logger.info(
            f"Backfill complete. Updated state for {updated_count} repositories."
        )
    else:
        logger.info(
            f"Backfill complete. No new commits found or state changes required across monitored repositories."
        )


if __name__ == "__main__":
    # Example of how to run backfill directly for testing
    # Requires node to be started if handle() depends on active components
    # In practice, this is called by server.py during startup
    logging.basicConfig(level=logging.INFO)
    logger.info("Running backfill directly for testing...")
    # node.start() # Might be needed depending on node.processor.handle implementation
    perform_backfill()
    # node.stop()
