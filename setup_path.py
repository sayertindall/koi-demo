"""
Path setup module for the KOI-net project.

This module adds the project root to the Python path, enabling imports from
the project's top-level packages like 'nodes'.

Usage:
    import setup_path  # At the beginning of your script

    # Now you can import from project packages
    from nodes.koi_net_github_sensor_node.github_sensor_node.types import GithubCommit
"""

import os
import sys

# Get the absolute path to the project root directory
project_root = os.path.dirname(os.path.abspath(__file__))

# Add the project root to the Python path if it's not already there
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    print(f"Added {project_root} to Python path")
