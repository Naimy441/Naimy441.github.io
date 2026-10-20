#!/usr/bin/env python3
"""
scripts/generate_campus_map_data.py

Convenience wrapper for src/duke_maps_client.py to refresh campus building
footprints and dining venue catalog.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from src.duke_maps_client import main

if __name__ == "__main__":
    main()
