#python - <<'PY'
from pathlib import Path
import re

root = Path("documents/Websites/madinps")

for path in sorted(root.glob("*.md")):
    content = path.read_text(encoding="utf-8", errors="ignore")

    url = re.search(r"source_url:\s*(.+)", content)
    title = re.search(r"^#\s+(.+)", content, re.MULTILINE)

    print("-" * 90)
    print(f"File: {path.name}")
    print(f"URL: {url.group(1).strip() if url else 'Not found'}")
    print(f"Title: {title.group(1).strip() if title else 'Not found'}")
    print(f"Characters: {len(content)}")
#PY