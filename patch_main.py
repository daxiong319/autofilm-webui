#!/usr/bin/env python3
"""Patch main.py to fix static file serving"""
import sys

filepath = "/home/autofilm-webui/webui/backend/main.py"

with open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find the last section (if __name__)
insert_pos = None
for i, line in enumerate(lines):
    if "if __name__" in line:
        insert_pos = i
        break

if not insert_pos:
    print("ERROR: Cannot find insertion point")
    sys.exit(1)

# Remove old static file serving code (last 30 lines before if __name__)
# Find where the old code starts
old_code_start = insert_pos - 1
for i in range(insert_pos - 1, max(0, insert_pos - 40), -1):
    if "# 静态文件服务" in lines[i] or "# Static files" in lines[i]:
        old_code_start = i
        break

# Delete old code
del lines[old_code_start:insert_pos]

# Insert new code
new_code = """# Static files + SPA fallback (must be after all API routes)
if STATIC_DIR.exists():
    @app.get("/", include_in_schema=False)
    async def serve_index():
        return FileResponse(str(STATIC_DIR / "index.html"))
    
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_static_or_spa(full_path: str):
        # Try to serve static files first (JS/CSS/images)
        file_path = STATIC_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        # Fallback to index.html for SPA routing
        index_file = STATIC_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        raise HTTPException(404, "File not found")

"""

lines.insert(old_code_start, new_code)

with open(filepath, "w", encoding="utf-8") as f:
    f.writelines(lines)

print("✅ Patch applied successfully")
