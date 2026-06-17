"""
AutoFilm WebUI Backend - Corrected Version
Uses app.mount properly for static files
"""

# Read the current file
filepath = "/home/autofilm-webui/webui/backend/main.py"

with open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find where to insert (before if __name__)
insert_pos = None
for i, line in enumerate(lines):
    if "if __name__" in line:
        insert_pos = i
        break

if not insert_pos:
    print("ERROR: Cannot find if __name__")
    exit(1)

# Remove all static file serving code before if __name__
# Go backwards and find the comment
start_remove = insert_pos - 1
for i in range(insert_pos - 1, max(0, insert_pos - 50), -1):
    if "Static files" in lines[i] or "static file" in lines[i].lower():
        start_remove = i
        break

# Remove old code
del lines[start_remove:insert_pos]

# Add correct static file serving code
new_code = """# Static files and SPA fallback
# IMPORTANT: app.mount must be used for static files, not route handlers
if STATIC_DIR.exists():
    # Mount /assets for JS/CSS files
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
    
    # Root route serves index.html
    @app.get("/", include_in_schema=False)
    async def serve_index():
        return FileResponse(str(STATIC_DIR / "index.html"))
    
    # SPA fallback: any other path serves index.html
    # This must NOT match /api/* or /assets/*
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        # Skip API routes (should already be handled by API routes above)
        if full_path.startswith("api"):
            raise HTTPException(404, "API route not found")
        # Skip assets (already mounted above)
        if full_path.startswith("assets"):
            raise HTTPException(404, "Asset not found")
        # Return index.html for Vue Router
        return FileResponse(str(STATIC_DIR / "index.html"))

"""

lines.insert(start_remove, new_code)

with open(filepath, "w", encoding="utf-8") as f:
    f.writelines(lines)

print("✅ Corrected static file serving code applied")
