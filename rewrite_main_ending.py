#!/usr/bin/env python3
"""Completely rewrite the end of main.py to fix static file serving"""

filepath = "/home/autofilm-webui/webui/backend/main.py"

with open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find the last API endpoint (system_status)
# Everything after that should be replaced
cutoff = None
for i in range(len(lines) - 1, 0, -1):
    if 'async def system_status' in lines[i]:
        # Find the end of this function (next line that's not indented or is a comment)
        for j in range(i + 1, len(lines)):
            if lines[j].strip() and not lines[j].startswith(' ') and not lines[j].startswith('#'):
                cutoff = j
                break
            if lines[j].strip() == '':
                continue
            if 'if __name__' in lines[j] or '#' in lines[j] and 'Static' in lines[j]:
                cutoff = j
                break
        break

if not cutoff:
    # Fallback: find last '}'
    for i in range(len(lines) - 1, 0, -1):
        if lines[i].strip() == '}':
            cutoff = i + 1
            break

print(f"Cutoff at line {cutoff}")

# Keep only up to cutoff
new_lines = lines[:cutoff]

# Add the correct static file serving code
new_code = """
# ──────────────────────────────────────────────
# Static files and SPA fallback
# ──────────────────────────────────────────────
if STATIC_DIR.exists():
    # Mount /assets directory for JS/CSS files (MUST be before catch-all routes)
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # Root path serves index.html
    @app.get("/", include_in_schema=False)
    async def serve_root_index():
        return FileResponse(str(STATIC_DIR / "index.html"))

    # SPA fallback for Vue Router history mode
    # This catches all non-API, non-asset paths
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa_fallback(full_path: str):
        # Don't intercept API routes (they're defined above)
        # Don't intercept asset routes (they're mounted above)
        # Just return index.html for client-side routing
        return FileResponse(str(STATIC_DIR / "index.html"))


if __name__ == "__main__":
    port = int(os.environ.get("WEBUI_PORT", "8096"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
"""

new_lines.append(new_code)

with open(filepath, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("✅ main.py rewritten successfully")
