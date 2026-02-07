"""
Create a ZIP package containing project files for submission.
Run: python package_submission.py
"""
import zipfile
from pathlib import Path

root = Path(__file__).parent
out = root / "submission.zip"
exclude = {".venv", "submission.zip"}

with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for p in root.rglob("*"):
        if any(part in exclude for part in p.parts):
            continue
        if p.is_file():
            arc = p.relative_to(root)
            z.write(p, arc)

print(f"Wrote {out}")
