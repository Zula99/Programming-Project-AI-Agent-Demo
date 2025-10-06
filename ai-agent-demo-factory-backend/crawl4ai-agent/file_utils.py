# file_utils.py - File system operations for crawled content
import re
import time
import json
import urllib.parse
from pathlib import Path
from typing import Optional
import logging

_logger = logging.getLogger(__name__)

# Folder-style slugify
_invalid = re.compile(r"[^a-z0-9._-]+")

def path_slug(url: str, output_root: Path) -> Path:
    """
    Map a URL to a folder structure with Windows path length protection:

    https://example.com/                   -> output/example.com/index.md
    https://example.com/page               -> output/example.com/page/index.md
    https://example.com/page?x=1           -> output/example.com/page/_q_x=1/index.md
    """
    parts = urllib.parse.urlsplit(url)
    host = parts.netloc.lower()
    path = parts.path

    if not path or path == "/":
        segments = []
    else:
        segments = [s for s in path.split("/") if s]

    # sanitise each segment with shorter limits for Windows
    segments = [_invalid.sub("-", s.lower()).strip("-")[:40] for s in segments]

    # encode query if present (shorter for Windows)
    if parts.query:
        q = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
        q.sort()
        qstr = "&".join([f"{_invalid.sub('-', k.lower())}={_invalid.sub('-', v.lower())}" for k, v in q])[:60]
        segments.append(f"_q_{qstr}")

    # compose final path: output_root/<host>/<segments...>/
    final_dir = output_root / host
    for s in segments:
        final_dir = final_dir / s

    return final_dir

def save_crawl_result(result, config) -> Optional[Path]:
    """Save crawl result to filesystem in organized structure"""
    try:
        folder = path_slug(result.url, config.output_root)
        folder.mkdir(parents=True, exist_ok=True)

        md_path = folder / "index.md"
        meta_path = folder / "meta.json"
        raw_html_path = folder / "raw.html"
        rendered_html_path = folder / "index.html"

        # Write files
        with md_path.open("w", encoding="utf-8") as f:
            f.write(result.markdown)

        if result.raw_html:
            # Save to index.html for rendered content (post-JS)
            with rendered_html_path.open("w", encoding="utf-8") as f:
                f.write(result.raw_html)

            # Also save to raw.html for backwards compatibility
            with raw_html_path.open("w", encoding="utf-8") as f:
                f.write(result.raw_html)

        meta = {
            "url": result.url,
            "title": result.title,
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "content_type": result.content_type,
            "bytes_html": len(result.raw_html) if result.raw_html else 0,
            "html_type": result.html_type,
            "success": result.success,
            "error": result.error
        }

        with meta_path.open("w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        return md_path

    except Exception as e:
        _logger.error(f"  Error saving {result.url}: {e} - skipping")
        return None
