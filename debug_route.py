#!/usr/bin/env python3
"""Debug the static file serving issue"""

filepath = "/home/autofilm-webui/webui/backend/main.py"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Find the serve_static_or_spa function
import re
match = re.search(r'@app\.get\("/\{full_path:path\}".*?raise HTTPException\(404.*?\n', content, re.DOTALL)

if match:
    print("Current route code:")
    print("=" * 60)
    print(match.group(0))
    print("=" * 60)
else:
    print("Route not found!")
