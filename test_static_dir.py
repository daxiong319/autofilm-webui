#!/usr/bin/env python3
"""Test STATIC_DIR path"""
from pathlib import Path
import sys

# Test both possible paths
path1 = Path("/webui/frontend/dist")
path2 = Path("/webui/backend/../frontend/dist").resolve()

print(f"Path 1: {path1}")
print(f"  Exists: {path1.exists()}")
print(f"  Is dir: {path1.is_dir()}")

print(f"Path 2: {path2}")
print(f"  Exists: {path2.exists()}")  
print(f"  Is dir: {path2.is_dir()}")

# Check what __file__ would resolve to
import os
main_py = Path("/webui/main.py")
static_dir = main_py.parent / "frontend" / "dist"
print(f"STATIC_DIR (from /webui/main.py): {static_dir}")
print(f"  Exists: {static_dir.exists()}")
print(f"  Is dir: {static_dir.is_dir()}")

if static_dir.exists():
    assets = static_dir / "assets"
    print(f"  Assets dir: {assets}")
    print(f"    Exists: {assets.exists()}")
    if assets.exists():
        files = list(assets.glob("*.js"))
        print(f"    JS files: {len(files)}")
        if files:
            print(f"    First: {files[0].name}")
