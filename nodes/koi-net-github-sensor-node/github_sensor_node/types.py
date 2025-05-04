from rid_lib.core import ORN


class GithubCommit(ORN):
    """
    Resource Identifier (RID) for a specific GitHub commit.

    Format: orn:github.commit:<owner>/<repo>/<sha>
    Example: orn:github.commit:microsoft/vscode/a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0
    """

    namespace = "github.commit"

    def __init__(self, owner: str, repo: str, sha: str):
        """
        Initialize a GitHub commit RID.

        Args:
            owner: The repository owner (user or organization)
            repo: The repository name
            sha: The commit SHA (full 40-character or shortened)
        """
        if not owner or not repo or not sha:
            raise ValueError("Owner, repo, and SHA cannot be empty")

        if "/" in owner or "/" in repo:
            raise ValueError("Owner and repo cannot contain '/' character")

        self.owner = owner
        self.repo = repo
        self.sha = sha

    @property
    def reference(self) -> str:
        """Returns the reference part of the RID: '<owner>/<repo>/<sha>'."""
        return f"{self.owner}/{self.repo}/{self.sha}"

    @property
    def repository_full_name(self) -> str:
        """Returns the full repository name: '<owner>/<repo>'."""
        return f"{self.owner}/{self.repo}"

    @property
    def html_url(self) -> str:
        """Returns the HTML URL to view this commit on GitHub."""
        return f"https://github.com/{self.owner}/{self.repo}/commit/{self.sha}"

    @property
    def api_url(self) -> str:
        """Returns the GitHub API URL for this commit."""
        return (
            f"https://api.github.com/repos/{self.owner}/{self.repo}/commits/{self.sha}"
        )

    @classmethod
    def from_reference(cls, reference: str) -> "GithubCommit":
        """
        Creates a GithubCommit instance from its reference string.

        Args:
            reference: String in format '<owner>/<repo>/<sha>'

        Returns:
            GithubCommit instance

        Raises:
            ValueError: If the reference format is invalid
        """
        try:
            parts = reference.split("/", maxsplit=2)
            if len(parts) != 3:
                raise ValueError("Reference must contain exactly two '/' separators")

            owner, repo, sha = parts

            if not owner or not repo or not sha:
                raise ValueError("Owner, repo, and SHA parts cannot be empty")

            # Basic SHA length check
            if len(sha) < 7:  # Minimum length for a short SHA
                raise ValueError(f"SHA part seems too short: {sha}")

            return cls(owner=owner, repo=repo, sha=sha)

        except ValueError as e:
            raise ValueError(
                f"Invalid reference format for GithubCommit. Expected '<owner>/<repo>/<sha>', got '{reference}'. Error: {e}"
            ) from e
        except Exception as e:
            raise TypeError(
                f"Unexpected error parsing GithubCommit reference '{reference}': {e}"
            ) from e
