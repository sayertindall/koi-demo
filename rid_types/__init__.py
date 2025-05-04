"""
Shared RID Types Package

This package re-exports RID type definitions from various sensor nodes,
providing a centralized location for accessing these types without
needing to import directly from the sensor node packages.
"""

# Import and re-export RID types
from .github import GithubCommit
from .hackmd import HackMDNote

__all__ = [
    "GithubCommit",
    "HackMDNote",
]
