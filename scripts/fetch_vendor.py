"""Download fixed frontend distributions and their upstream licenses."""
from pathlib import Path
import re
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent / "static" / "vendor"
FILES = {
    "bootstrap.min.css": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css",
    "bootstrap.bundle.min.js": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js",
    "bootstrap-LICENSE.txt": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/LICENSE",
    "chart.umd.min.js": "https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js",
    "chartjs-LICENSE.txt": "https://cdn.jsdelivr.net/npm/chart.js@4.5.1/LICENSE.md",
}
if __name__ == "__main__":
    ROOT.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        with urlopen(url, timeout=30) as response:
            content = response.read()
        if name.endswith((".css", ".js")):
            # Source maps are optional development assets, not part of this bundle.
            content = re.sub(rb"/\*# sourceMappingURL=.*?\*/|//# sourceMappingURL=[^\r\n]*", b"", content)
        (ROOT / name).write_bytes(content)
        print(f"Saved {name}: {len(content):,} bytes")
