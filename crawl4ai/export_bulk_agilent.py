# export_bulk_ndjson.py
import json, hashlib, re, datetime, os
from pathlib import Path
from bs4 import BeautifulSoup

# ====== CONFIG ======
OUTPUT_ROOT   = Path("output/agilent_render")   # <- your Playwright mirror folder
INDEX_NAME    = "mirror-agilent"                # OpenSearch/Elasticsearch index
OUT_FILE      = OUTPUT_ROOT / "bulk.ndjson"     # writes here
SPLIT_CHUNKS  = False                           # True = chunk text for vector search
CHUNK_TOKENS  = 280                              # ~words per chunk (naive)
CHUNK_OVERLAP = 60                               # ~overlap words between chunks
MIN_TEXT_LEN  = 200                              # skip pages with less text
MAX_TEXT_CHARS= 120_000                          # guardrail to keep lines reasonable

# ====== HELPERS ======
_ws = re.compile(r"\s+", re.UNICODE)
def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", "ignore")).hexdigest()

def norm(s: str) -> str:
    return _ws.sub(" ", (s or "").strip())

def extract(doc_html: str) -> dict:
    soup = BeautifulSoup(doc_html, "html.parser")

    # strip non-content elements
    for tag in soup(["script","style","noscript","template"]):
        tag.decompose()

    title = (soup.title.string if soup.title and soup.title.string else "").strip()
    # meta description
    meta_desc = ""
    m = soup.find("meta", attrs={"name":"description"})
    if not m:
        m = soup.find("meta", attrs={"property":"og:description"})
    if m and m.get("content"):
        meta_desc = m["content"].strip()

    # headings
    heads = {
        "h1": [norm(h.get_text(" ")) for h in soup.find_all("h1")],
        "h2": [norm(h.get_text(" ")) for h in soup.find_all("h2")],
        "h3": [norm(h.get_text(" ")) for h in soup.find_all("h3")],
    }

    # main text (very simple: whole body)
    body = soup.body or soup
    text = norm(body.get_text(" ", strip=True))
    if len(text) > MAX_TEXT_CHARS:
        text = text[:MAX_TEXT_CHARS]

    return {
        "title": title,
        "description": meta_desc,
        "headings": heads,
        "text": text,
        "text_length": len(text),
    }

def chunk_words(text: str, size: int, overlap: int):
    words = text.split()
    if not words:
        return []
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i+size])
        chunks.append(chunk)
        if i + size >= len(words): break
        i += max(1, size - overlap)
    return chunks

# ====== MAIN ======
def main():
    metas = list(OUTPUT_ROOT.rglob("meta.json"))
    if not metas:
        print(f"No meta.json files found under {OUTPUT_ROOT}. Did you run the renderer?")
        return

    n_docs = 0
    with open(OUT_FILE, "w", encoding="utf-8") as out:
        for meta_path in metas:
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8", errors="ignore"))
                url  = meta.get("url")
                if not url:
                    continue
                raw_path = meta_path.parent / "raw.html"
                if not raw_path.exists():
                    continue
                html = raw_path.read_text(encoding="utf-8", errors="ignore")
                data = extract(html)
                if data["text_length"] < MIN_TEXT_LEN:
                    continue

                # doc fields
                from urllib.parse import urlsplit
                s = urlsplit(url)
                host = s.netloc.lower()
                path = s.path or "/"
                fetched_at = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"

                if not SPLIT_CHUNKS:
                    _id = sha1(url)
                    action = {"index": {"_index": INDEX_NAME, "_id": _id}}
                    doc = {
                        "url": url,
                        "host": host,
                        "path": path,
                        "title": data["title"],
                        "description": data["description"],
                        "headings": data["headings"],
                        "text": data["text"],
                        "text_length": data["text_length"],
                        "fetched_at": fetched_at,
                        "source": "agilent-render",
                    }
                    out.write(json.dumps(action, ensure_ascii=False) + "\n")
                    out.write(json.dumps(doc, ensure_ascii=False) + "\n")
                    n_docs += 1
                else:
                    # chunking mode (useful for vector search / RAG)
                    chunks = chunk_words(data["text"], CHUNK_TOKENS, CHUNK_OVERLAP)
                    parent_id = sha1(url)
                    for idx, chunk in enumerate(chunks):
                        _id = sha1(f"{url}#chunk:{idx}")
                        action = {"index": {"_index": INDEX_NAME, "_id": _id}}
                        doc = {
                            "url": url,
                            "host": host,
                            "path": path,
                            "parent_id": parent_id,
                            "chunk_index": idx,
                            "title": data["title"],
                            "headings": data["headings"],
                            "text": chunk,
                            "text_length": len(chunk),
                            "fetched_at": fetched_at,
                            "source": "agilent-render",
                        }
                        out.write(json.dumps(action, ensure_ascii=False) + "\n")
                        out.write(json.dumps(doc, ensure_ascii=False) + "\n")
                        n_docs += 1

            except Exception as e:
                print(f"⚠️  Skip {meta_path}: {e}")

    print(f"✅ Wrote {n_docs} docs to {OUT_FILE}")

if __name__ == "__main__":
    main()