#!/usr/bin/env python3
"""
Test script to verify that the rid_types package correctly imports and
re-exports the RID types from the sensor nodes.
"""

import os
import sys

print("Testing rid_types package...")

# Ensure the project root is in the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    print(f"Added {project_root} to Python path")

# Import directly from the shared package
from rid_types import GithubCommit, HackMDNote

print("✅ Successfully imported GithubCommit and HackMDNote from rid_types package")

# Print type information
print(f"GithubCommit type: {type(GithubCommit)}")
print(f"HackMDNote type: {type(HackMDNote)}")
print(f"GithubCommit module: {GithubCommit.__module__}")
print(f"HackMDNote module: {HackMDNote.__module__}")

print("\nDone testing.")
