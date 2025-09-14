"""
Robust Content Deduplication System for SmartMirrorAgent
Handles exact duplicates, near-duplicates, and redirect stubs
"""

import re, hashlib, html
from bs4 import BeautifulSoup
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass

# Global regex patterns
WS_RE = re.compile(r'\s+')
DATE_WORD_RE = re.compile(r'\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\b', re.I)
DATE_NUMERIC_RE = re.compile(r'\b(?:\d{1,2}[\/\-.]){1,2}\d{2,4}\b')
DATE_ISO_RE = re.compile(r'\b\d{4}-\d{2}-\d{2}\b')
TIME_RE = re.compile(r'\b(?:[01]?\d|2[0-3]):[0-5]\d(?::[0-5]\d)?(?:\s?[AP]M)?\b', re.I)
NUMERIC_RE = re.compile(r'\b(?:\$|€|£)?\d[\d,]*(?:\.\d+)?%?\b')

# Common redirect stub phrases
REDIRECT_PHRASES = [
    r'\bthis page has moved\b',
    r'\bpage moved to\b',
    r'\bredirect(?:ing)? to\b',
    r'\bclick here to continue\b',
    r'\bhas been relocated\b',
]

@dataclass
class DeduplicationResult:
    """Result of deduplication decision"""
    status: str  # "canon", "dup", "alias"
    canonical_url: str  # The canonical URL for this content
    reason: str  # Why this decision was made

class RobustContentDeduplicator:
    """
    Production-ready content deduplication system
    """

    def __init__(self, simhash_threshold: int = 4, min_content_length: int = 100):
        """
        Initialize deduplicator

        Args:
            simhash_threshold: Hamming distance threshold for near-duplicates (4 = ~94% similarity)
            min_content_length: Minimum content length to analyze
        """
        self.simhash_threshold = simhash_threshold
        self.min_content_length = min_content_length

        # Storage for deduplication data
        self.exact_map: Dict[str, str] = {}  # exact_hash -> canonical_url
        self.fuzzy_buckets: Dict[str, List[str]] = {}  # fuzzy_hash -> [urls]
        self.sim_map: Dict[str, str] = {}  # url -> simhash_hex
        self.canon_map: Dict[str, str] = {}  # url -> canonical_url (for aliases)

        # Statistics
        self.stats = {
            "total_processed": 0,
            "exact_duplicates": 0,
            "near_duplicates": 0,
            "redirect_stubs": 0,
            "unique_pages": 0
        }

    def extract_meaningful_text(self, html_content: str) -> Tuple[str, Dict[str, Any]]:
        """
        Extract meaningful text from HTML and gather metadata

        Returns:
            (text, meta) where text is boilerplate-reduced, meta contains hints
        """
        soup = BeautifulSoup(html_content, "lxml")

        # Remove scripts, styles, and other non-content tags
        for tag in soup(["script", "style", "template", "noscript"]):
            tag.decompose()

        meta = {
            "title": (soup.title.get_text(" ", strip=True) if soup.title else "").strip(),
            "canonical": None,
            "meta_refresh": False,
            "js_redirect_hint": False,
            "body_len": 0,
        }

        # Check for canonical URL
        link_canon = soup.find("link", rel=lambda v: v and "canonical" in v)
        if link_canon and link_canon.has_attr("href"):
            meta["canonical"] = link_canon["href"].strip()

        # Meta refresh detection
        for m in soup.find_all("meta", attrs={"http-equiv": True, "content": True}):
            if m["http-equiv"].lower() == "refresh":
                meta["meta_refresh"] = True
                break

        # JS redirect hint (lightweight detection)
        if (soup.find(string=re.compile(r'location\.(href|replace)\s*=')) or
            soup.find(string=re.compile(r'window\.location'))):
            meta["js_redirect_hint"] = True

        # Extract meaningful content
        root = soup.find(["main", "article"]) or soup.body or soup
        chunks = []

        if meta["title"]:
            chunks.append(meta["title"])

        for tag in root.find_all(["h1", "h2", "h3", "p", "li", "th", "td", "figcaption"]):
            txt = tag.get_text(" ", strip=True)
            if txt:
                chunks.append(txt)

        text = html.unescape(" ".join(chunks))
        text = WS_RE.sub(" ", text).strip()
        meta["body_len"] = len(text)

        return text, meta

    def normalize_exact(self, text: str) -> str:
        """Normalize text for exact matching"""
        return WS_RE.sub(" ", text.strip().lower())

    def normalize_fuzzy(self, text: str, neutralize_numbers=True, neutralize_dates=True) -> str:
        """Normalize text for fuzzy matching"""
        t = text.lower()

        if neutralize_dates:
            # Replace various date formats with <date>
            t = DATE_ISO_RE.sub(" <date> ", t)
            t = DATE_NUMERIC_RE.sub(" <date> ", t)
            t = re.sub(rf'(\b\d{{1,2}}\b[ ,.-/]*)?{DATE_WORD_RE.pattern}([ ,.-/]*\b\d{{2,4}}\b)?',
                      " <date> ", t, flags=re.I)
            t = TIME_RE.sub(" <time> ", t)
            t = re.sub(r'\b(last|updated|as of|published)\b.*?(<date>|<time>)',
                      " <upd> ", t, flags=re.I)

        if neutralize_numbers:
            t = NUMERIC_RE.sub(" <num> ", t)

        # Remove common stopwords lightly
        STOP = {"a","an","the","of","in","on","at","for","to","from","by","and","or","if","this","that","with","as","is","are","be","was","were","it"}
        toks = [tok for tok in WS_RE.sub(" ", t).split(" ") if tok and tok not in STOP]
        return " ".join(toks)

    def sha256_hex(self, s: str) -> str:
        """Compute SHA-256 hash"""
        return hashlib.sha256(s.encode("utf-8")).hexdigest()

    def _ngrams(self, tokens, n=3):
        """Generate n-grams from tokens"""
        return [" ".join(tokens[i:i+n]) for i in range(len(tokens)-n+1)] if len(tokens) >= n else tokens

    def _hash64(self, s: str) -> int:
        """Convert string to 64-bit integer hash"""
        h = hashlib.md5(s.encode("utf-8")).digest()
        return int.from_bytes(h[:8], "big", signed=False)

    def simhash64(self, text: str, n=3) -> int:
        """Compute 64-bit SimHash for near-duplicate detection"""
        toks = [t for t in WS_RE.sub(" ", text).split(" ") if t]
        grams = self._ngrams(toks, n)

        # Simple TF weighting
        freq = {}
        for g in grams:
            freq[g] = freq.get(g, 0) + 1

        vec = [0] * 64
        for g, w in freq.items():
            h = self._hash64(g)
            for i in range(64):
                vec[i] += w if ((h >> i) & 1) else -w

        fp = 0
        for i in range(64):
            if vec[i] >= 0:
                fp |= (1 << i)
        return fp

    def hamming64(self, a: int, b: int) -> int:
        """Compute Hamming distance between two 64-bit integers"""
        return (a ^ b).bit_count()

    def is_redirect_stub(self, html_content: str, text: str, meta: Dict[str, Any]) -> bool:
        """Detect redirect stub pages"""
        if meta["meta_refresh"]:
            return True

        if meta["js_redirect_hint"] and meta["body_len"] < 240:
            return True

        # Tiny pages that announce a move
        if meta["body_len"] < 180:
            for pattern in REDIRECT_PHRASES:
                if re.search(pattern, text, re.I):
                    return True
        return False

    def compute_hash_bundle(self, html_content: str, neutralize_numbers=True, neutralize_dates=True) -> Dict[str, Any]:
        """Compute all hashes and metadata for a page"""
        text, meta = self.extract_meaningful_text(html_content)
        exact_norm = self.normalize_exact(text)
        fuzzy_norm = self.normalize_fuzzy(text, neutralize_numbers, neutralize_dates)

        return {
            "meta": meta,
            "exact_hash": self.sha256_hex(exact_norm),
            "fuzzy_hash": self.sha256_hex(fuzzy_norm),
            "simhash_hex": f"{self.simhash64(fuzzy_norm, n=3):016x}",
            "len_norm": len(exact_norm),
            "title": meta.get("title", "")
        }

    def decide_dedup(self, url: str, html_content: str) -> DeduplicationResult:
        """
        Main deduplication decision logic

        Returns:
            DeduplicationResult with status, canonical_url, and reason
        """
        self.stats["total_processed"] += 1

        bundle = self.compute_hash_bundle(html_content)

        # Skip very short content
        if bundle["len_norm"] < self.min_content_length:
            return DeduplicationResult("canon", url, "content_too_short")

        # 0) Redirect / canonical short-circuits
        if self.is_redirect_stub(html_content, bundle["title"], bundle["meta"]):
            self.stats["redirect_stubs"] += 1
            target = bundle["meta"]["canonical"] or "unknown"
            return DeduplicationResult("alias", target, "redirect_stub")

        # 1) Exact duplicate
        if bundle["exact_hash"] in self.exact_map:
            self.stats["exact_duplicates"] += 1
            return DeduplicationResult("dup", self.exact_map[bundle["exact_hash"]], "exact_hash")

        # 2) Near-duplicate (fuzzy pre-bucket → SimHash compare)
        candidates = self.fuzzy_buckets.get(bundle["fuzzy_hash"], [])
        for c_url in candidates:
            if c_url in self.sim_map:
                current_simhash = int(bundle["simhash_hex"], 16)
                candidate_simhash = int(self.sim_map[c_url], 16)
                if self.hamming64(current_simhash, candidate_simhash) <= self.simhash_threshold:
                    self.stats["near_duplicates"] += 1
                    return DeduplicationResult("dup", c_url, f"near_dup_simhash<={self.simhash_threshold}")

        # 3) New canonical - store all hashes
        self.exact_map[bundle["exact_hash"]] = url
        self.fuzzy_buckets.setdefault(bundle["fuzzy_hash"], []).append(url)
        self.sim_map[url] = bundle["simhash_hex"]
        self.stats["unique_pages"] += 1

        return DeduplicationResult("canon", url, "unique")

    def is_duplicate(self, url: str, content: str, title: str = "") -> Tuple[bool, str]:
        """
        Compatibility method for existing crawler integration

        Args:
            url: Page URL
            content: Page content (HTML or markdown)
            title: Page title (unused in new implementation)

        Returns:
            (is_duplicate, reason)
        """
        result = self.decide_dedup(url, content)

        # Map new statuses to old boolean logic
        is_duplicate = result.status in ["dup", "alias"]
        return is_duplicate, result.reason

    def get_deduplication_summary(self) -> Dict[str, Any]:
        """Get human-readable deduplication summary"""
        total_duplicates = (self.stats["exact_duplicates"] +
                          self.stats["near_duplicates"] +
                          self.stats["redirect_stubs"])

        duplicate_rate = total_duplicates / self.stats["total_processed"] if self.stats["total_processed"] > 0 else 0

        return {
            "total_processed": self.stats["total_processed"],
            "unique_kept": self.stats["unique_pages"],
            "total_duplicates": total_duplicates,
            "duplicate_rate": f"{duplicate_rate:.1%}",
            "breakdown": {
                "exact_duplicates": self.stats["exact_duplicates"],
                "near_duplicates": self.stats["near_duplicates"],
                "redirect_stubs": self.stats["redirect_stubs"]
            }
        }

    def reset(self):
        """Reset deduplicator state for new crawl session"""
        self.exact_map.clear()
        self.fuzzy_buckets.clear()
        self.sim_map.clear()
        self.canon_map.clear()
        self.stats = {
            "total_processed": 0,
            "exact_duplicates": 0,
            "near_duplicates": 0,
            "redirect_stubs": 0,
            "unique_pages": 0
        }

# Backward compatibility alias
ContentDeduplicator = RobustContentDeduplicator