# Plan: Scaffold and Implement Processor Nodes

This plan outlines the steps to create and implement Processor A (Repo Indexer) and Processor B (Note Indexer) within the existing `nodes/` directory structure, integrating them into the overall system defined by the PRD and `Processor.md`.

## Phase 0: Creating a Shared RID Types Package

**Goal:** Create a centralized package that re-exports existing RID type definitions to be used across all nodes.

1. **Task: Create Shared RID Types Directory Structure**

   - **Action:** Create the directory `rid_types/` at the project root.
   - **Verification:** The directory structure exists.

2. **Task: Create Basic RID Types Package Files**

   - **Action:** Inside `rid_types/`, create the following files:
     - `__init__.py` (exports all RID types)
     - `github.py` (re-exports GitHub-related RID types)
     - `hackmd.py` (re-exports HackMD-related RID types)
   - **Verification:** All specified files exist in the correct locations.

3. **Task: Implement GitHub RID Types Re-export**

   - **Action:** In `rid_types/github.py`, import and re-export the existing `GithubCommit` RID class:

     ```python
     # Re-export the existing GithubCommit class
     from nodes.koi_net_github_sensor_node.github_sensor_node.types import GithubCommit

     __all__ = ["GithubCommit"]
     ```

   - **Verification:** The `GithubCommit` class is successfully imported and re-exported.

4. **Task: Implement HackMD RID Types Re-export**

   - **Action:** In `rid_types/hackmd.py`, import and re-export the existing `HackMDNote` RID class:

     ```python
     # Re-export the existing HackMDNote class
     from nodes.koi_net_hackmd_sensor_node.rid_types import HackMDNote

     __all__ = ["HackMDNote"]
     ```

   - **Verification:** The `HackMDNote` class is successfully imported and re-exported.

5. **Task: Implement Package Exports**

   - **Action:** In `rid_types/__init__.py`, export all RID classes:

     ```python
     from .github import GithubCommit
     from .hackmd import HackMDNote

     __all__ = ["GithubCommit", "HackMDNote"]
     ```

   - **Verification:** The package properly exports all RID classes.
