"""Render the dashboard page from the template and the committed data snapshot.

Inputs
  dashboard/template.html   the page (layout, styles, script)
  dashboard/data.json       the data, written by scripts/build_dashboard.py (committed)
  dashboard/fonts/          embedded as data URIs

Outputs
  dashboard/page.html       page content for publishing as a claude.ai page
  dashboard/index.html      the same page as a full HTML document (GitHub Pages)

Standard library only, so CI can run it without the pipeline or its inputs.

Usage: python scripts/render_dashboard.py [--out DIR]
"""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path

DASH = Path(__file__).resolve().parents[1] / "dashboard"
FONTS = (("Geist", "geist.woff2"),)   # numbers use Geist with tabular figures (no slashed zeros)


def render(data: dict | None = None, out_dir: Path = DASH) -> int:
    """Write page.html and index.html; returns the page size in bytes."""
    if data is None:
        data = json.loads((DASH / "data.json").read_text())
    template = (DASH / "template.html").read_text()
    fonts = "".join(
        f'@font-face{{font-family:"{fam}";src:url(data:font/woff2;base64,'
        f'{base64.b64encode((DASH / "fonts" / fn).read_bytes()).decode()}) format("woff2");'
        f'font-weight:100 900;font-style:normal;font-display:swap;}}'
        for fam, fn in FONTS)
    page = template.replace("/*__FONTS__*/", fonts).replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":")))
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "page.html").write_text(page)
    (out_dir / "index.html").write_text(
        "<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
        "<style>html,body{margin:0}</style>\n</head>\n<body>\n" + page + "\n</body>\n</html>\n")
    return len(page)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DASH, help="output directory (default: dashboard/)")
    args = ap.parse_args()
    size = render(out_dir=args.out)
    print(f"page.html {size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
