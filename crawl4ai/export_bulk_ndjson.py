# export_bulk_ndjson.py
import hashlib, json, os, re, sys
from pathlib import Path
from datetime import datetime
from urllib.parse import urlsplit

OUTPUT_ROOT = Path("output/nab")

try:
    from bs4 import BeautifulSoup
    HAVE_BS4 = True
except Exception:
    HAVE_BS4 = False

def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()

def load_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

def canonical_from_html(html: str) -> str | None:
    if not html or not HAVE_BS4: return None
    soup = BeautifulSoup(html, "html.parser")
    tag = soup.find("link", rel=lambda v: v and "canonical" in v)
    if tag and tag.get("href"):
        return tag["href"].strip()
    return None

def meta_description(html: str) -> str | None:
    if not html or not HAVE_BS4: return None
    soup = BeautifulSoup(html, "html.parser")
    t = soup.find("meta", attrs={"name":"description"}) or soup.find("meta", attrs={"property":"og:description"})
    return (t.get("content") or "").strip() if t else None

def headings(html: str) -> dict:
    if not html or not HAVE_BS4: return {"h1":[], "h2":[], "h3":[]}
    soup = BeautifulSoup(html, "html.parser")
    pick = lambda sel: [h.get_text(" ", strip=True) for h in soup.select(sel)]
    return {"h1": pick("h1"), "h2": pick("h2"), "h3": pick("h3")}

def main():
    if not OUTPUT_ROOT.exists():
        print(f"Missing {OUTPUT_ROOT}; run your crawler first.", file=sys.stderr)
        sys.exit(1)

    out = []
    for folder, _, files in os.walk(OUTPUT_ROOT):
        folder = Path(folder)
        if "index.md" in files and "meta.json" in files:
            md = load_text(folder / "index.md")
            meta = json.loads(load_text(folder / "meta.json") or "{}")
            html = load_text(folder / "raw.html") if "raw.html" in files else ""

            url = meta.get("url") or ""
            parts = urlsplit(url)
            host, path = parts.netloc.lower(), parts.path

            can = canonical_from_html(html) if html else None
            heads = headings(html) if html else {"h1":[], "h2":[], "h3":[]}
            desc = meta_description(html) if html else None

            # Stable ID = sha1(canonical or url)
            stable_id = sha1((can or url).strip())

            # Simple checksum of content to support incremental updates
            checksum = sha1(md) if md else sha1(html)

            doc = {
                "url": url,
                "host": host,
                "path": path,
                "canonical": can or url,
                "title": meta.get("title") or (heads["h1"][0] if heads["h1"] else None),
                "h1": heads["h1"],
                "h2": heads["h2"],
                "h3": heads["h3"],
                "content_md": md,
                "meta_desc": desc,
                "bytes_html": int(meta.get("bytes_html") or 0),
                "fetched_at": meta.get("fetched_at"),
                "content_type": meta.get("content_type"),
                "tags": ["nab"],
                "checksum": checksum,
            }

            # Compose _bulk lines
            action = {"index": {"_index": "mirror-nab", "_id": stable_id}}
            out.append(json.dumps(action, ensure_ascii=False))
            out.append(json.dumps(doc, ensure_ascii=False))

    Path("bulk.ndjson").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f" Wrote {len(out)//2} docs to bulk.ndjson")

if __name__ == "__main__":
    main()
