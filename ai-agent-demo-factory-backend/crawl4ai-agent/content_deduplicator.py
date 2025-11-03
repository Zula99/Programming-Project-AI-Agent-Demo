"""
Exact Content Deduplication System for SmartMirrorAgent
Handles exact duplicates and redirect stubs only
"""

import re, hashlib, html
from bs4 import BeautifulSoup
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass

# Global regex patterns
WS_RE = re.compile(r'\s+')

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
    Exact content deduplication system - only detects identical content
    """

    def __init__(self, min_content_length: int = 100, **kwargs):
        """
        Initialize deduplicator for exact duplicate detection only

        Args:
            min_content_length: Minimum content length to analyze
            **kwargs: Ignored parameters for backward compatibility
        """
        self.min_content_length = min_content_length

        # Storage for exact duplicate detection
        self.exact_map: Dict[str, str] = {}  # exact_hash -> canonical_url

        # Statistics
        self.stats = {
            "total_processed": 0,
            "exact_duplicates": 0,
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

    def sha256_hex(self, s: str) -> str:
        """Compute SHA-256 hash"""
        return hashlib.sha256(s.encode("utf-8")).hexdigest()

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

    def compute_hash_bundle(self, html_content: str) -> Dict[str, Any]:
        """Compute exact hash and metadata for a page"""
        text, meta = self.extract_meaningful_text(html_content)
        exact_norm = self.normalize_exact(text)

        return {
            "meta": meta,
            "exact_hash": self.sha256_hex(exact_norm),
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

        # 1) Exact duplicate only
        if bundle["exact_hash"] in self.exact_map:
            self.stats["exact_duplicates"] += 1
            return DeduplicationResult("dup", self.exact_map[bundle["exact_hash"]], "exact_duplicate")

        # 2) New canonical - store exact hash only
        self.exact_map[bundle["exact_hash"]] = url
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
                          self.stats["redirect_stubs"])

        duplicate_rate = total_duplicates / self.stats["total_processed"] if self.stats["total_processed"] > 0 else 0

        return {
            "total_processed": self.stats["total_processed"],
            "unique_kept": self.stats["unique_pages"],
            "total_duplicates": total_duplicates,
            "duplicate_rate": f"{duplicate_rate:.1%}",
            "breakdown": {
                "exact_duplicates": self.stats["exact_duplicates"],
                "redirect_stubs": self.stats["redirect_stubs"]
            }
        }

    def reset(self):
        """Reset deduplicator state for new crawl session"""
        self.exact_map.clear()
        self.stats = {
            "total_processed": 0,
            "exact_duplicates": 0,
            "redirect_stubs": 0,
            "unique_pages": 0
        }

# Backward compatibility alias
ContentDeduplicator = RobustContentDeduplicator