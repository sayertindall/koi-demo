# KOI-net Shared RID Types

This package provides centralized access to RID type definitions used across the KOI-net system. It re-exports RID classes from sensor nodes and other components to allow processors and other nodes to use these types without directly importing from the specific node packages.

## Available RID Types

- `GithubCommit`: Representing GitHub commit data from the GitHub sensor node
- `HackMDNote`: Representing HackMD note data from the HackMD sensor node

## Usage

```python
# Import RID types directly from this package
from rid_types import GithubCommit, HackMDNote

# Example usage
commit = GithubCommit(reference="1234abcd", repository="repo-name", owner="username")
note = HackMDNote(note_id="note-id", title="Note Title", tags=["tag1", "tag2"])
```

## Features

- Provides a consistent interface for RID types across the system
- Includes fallback implementations if the original classes cannot be imported
- Centralizes RID type definitions to avoid circular dependencies
