"""
Content Deduplication System for SmartMirrorAgent

US-045: Content Deduplication System
As a demo factory operator I want the system to detect and skip duplicate content
So that demos contain only unique, valuable content

Features:
- Text similarity detection using cosine similarity
- URL pattern duplicate detection (e.g., /product/123 vs /product/456)
- Content hash comparison for exact duplicates
- Template-based page identification with different data
"""

import hashlib
import re
import logging
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass, field
from urllib.parse import urlparse, parse_qs

# Optional sklearn imports with fallback
try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("Note: sklearn not available - text similarity detection will use simple fallback method")


@dataclass
class ContentFingerprint:
    """Fingerprint for content deduplication"""
    url: str
    content_hash: str
    text_vector: Optional[np.ndarray] = None
    url_pattern: str = ""
    template_signature: str = ""
    content_length: int = 0
    title: str = ""


@dataclass
class DuplicationStats:
    """Statistics about deduplication process"""
    total_pages_processed: int = 0
    exact_duplicates: int = 0
    url_pattern_duplicates: int = 0
    text_similarity_duplicates: int = 0
    template_duplicates: int = 0
    unique_pages_kept: int = 0
    duplicate_examples: Dict[str, List[str]] = field(default_factory=dict)


class ContentDeduplicator:
    """
    Comprehensive content deduplication system for web crawling

    Implements multiple deduplication strategies:
    1. Exact content hash matching
    2. URL pattern recognition
    3. Text similarity using cosine similarity
    4. Template-based page detection
    """

    def __init__(self,
                 similarity_threshold: float = 0.85,
                 min_content_length: int = 100,
                 max_vectorizer_features: int = 5000):
        """
        Initialize the deduplicator

        Args:
            similarity_threshold: Cosine similarity threshold (0.85 = 85% similar)
            min_content_length: Minimum content length to analyze
            max_vectorizer_features: Maximum features for TF-IDF vectorizer
        """
        self.logger = logging.getLogger(__name__)
        self.similarity_threshold = similarity_threshold
        self.min_content_length = min_content_length

        # Storage for seen content
        self.content_fingerprints: List[ContentFingerprint] = []
        self.content_hashes: Set[str] = set()
        self.url_patterns: Dict[str, List[str]] = {}
        self.template_signatures: Dict[str, List[str]] = {}

        # TF-IDF vectorizer for text similarity (if sklearn available)
        self.vectorizer = None
        self.text_vectors: List[Any] = []
        self.vectorizer_fitted = False
        self.simple_text_hashes: Set[str] = set()  # Fallback for text similarity

        if SKLEARN_AVAILABLE:
            self.vectorizer = TfidfVectorizer(
                max_features=max_vectorizer_features,
                stop_words='english',
                lowercase=True,
                strip_accents='ascii'
            )

        # Statistics
        self.stats = DuplicationStats()

    def is_duplicate(self, url: str, content: str, title: str = "") -> Tuple[bool, str]:
        """
        Check if content is a duplicate using multiple strategies

        Args:
            url: Page URL
            content: Page content (markdown/text)
            title: Page title

        Returns:
            is_duplicate: Boolean indicating if content is duplicate
            reason: Reason for duplication decision
        """
        self.stats.total_pages_processed += 1

        # Skip very short content
        if len(content) < self.min_content_length:
            return False, "content_too_short"

        # 1. Exact content hash duplicate check
        content_hash = self._compute_content_hash(content)
        if content_hash in self.content_hashes:
            self.stats.exact_duplicates += 1
            self._add_duplicate_example("exact_hash", url)
            return True, "exact_content_duplicate"

        # 2. URL pattern duplicate check
        url_pattern = self._extract_url_pattern(url)
        if self._is_url_pattern_duplicate(url_pattern, url):
            self.stats.url_pattern_duplicates += 1
            self._add_duplicate_example("url_pattern", url)
            return True, "url_pattern_duplicate"

        # 3. Template-based duplicate check
        template_sig = self._extract_template_signature(content, title)
        if self._is_template_duplicate(template_sig, url):
            self.stats.template_duplicates += 1
            self._add_duplicate_example("template", url)
            return True, "template_duplicate"

        # 4. Text similarity duplicate check
        if self._is_text_similarity_duplicate(content, url):
            self.stats.text_similarity_duplicates += 1
            self._add_duplicate_example("text_similarity", url)
            return True, "text_similarity_duplicate"

        # Not a duplicate - add to fingerprints
        self._add_content_fingerprint(url, content, title, content_hash, url_pattern, template_sig)
        self.stats.unique_pages_kept += 1

        return False, "unique_content"

    def _compute_content_hash(self, content: str) -> str:
        """Compute SHA-256 hash of normalized content"""
        # Normalize content for hashing
        normalized = re.sub(r'\s+', ' ', content.strip().lower())
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    def _extract_url_pattern(self, url: str) -> str:
        """
        Extract URL pattern by replacing dynamic parts with placeholders

        Examples:
        - /product/123 -> /product/{id}
        - /article/2024/01/15/title -> /article/{year}/{month}/{day}/{slug}
        - /user/profile?id=456 -> /user/profile?id={param}
        """
        try:
            parsed = urlparse(url)
            path = parsed.path

            # Replace common dynamic patterns
            patterns = [
                (r'/\d{4}/\d{2}/\d{2}/', '/{year}/{month}/{day}/'),  # Date patterns
                (r'/\d{4}/\d{2}/', '/{year}/{month}/'),              # Year/month
                (r'/\d{4}/', '/{year}/'),                            # Year only
                (r'/\d+/', '/{id}/'),                                # Numeric IDs
                (r'/[a-f0-9]{8,}/', '/{hash}/'),                     # Hash-like strings
                (r'/[a-zA-Z0-9-]{20,}/', '/{slug}/'),                # Long slugs
            ]

            pattern_path = path
            for regex, replacement in patterns:
                pattern_path = re.sub(regex, replacement, pattern_path)

            # Handle query parameters
            if parsed.query:
                # Replace parameter values with placeholders
                query_pattern = re.sub(r'=([^&]+)', '={param}', parsed.query)
                return f"{pattern_path}?{query_pattern}"

            return pattern_path

        except Exception as e:
            self.logger.warning(f"URL pattern extraction failed for {url}: {e}")
            return url

    def _is_url_pattern_duplicate(self, pattern: str, url: str) -> bool:
        """Check if URL pattern already exists"""
        if pattern in self.url_patterns:
            # Allow some variety within the same pattern (e.g., 3 products max)
            if len(self.url_patterns[pattern]) >= 3:
                self.logger.debug(f"URL pattern duplicate: {pattern} (from {url})")
                return True
        else:
            self.url_patterns[pattern] = []

        self.url_patterns[pattern].append(url)
        return False

    def _extract_template_signature(self, content: str, title: str) -> str:
        """
        Extract template signature to identify pages with same structure but different data

        This looks at content structure patterns rather than actual content
        """
        try:
            # Extract structural elements
            structural_elements = []

            # Count different types of content elements
            heading_count = len(re.findall(r'^#+\s', content, re.MULTILINE))
            list_count = len(re.findall(r'^\s*[-*+]\s', content, re.MULTILINE))
            link_count = len(re.findall(r'\[([^\]]+)\]\([^)]+\)', content))
            image_count = len(re.findall(r'!\[([^\]]*)\]\([^)]+\)', content))

            # Extract common template phrases (navigation, footer, etc.)
            template_phrases = []
            common_patterns = [
                r'home\s*>\s*\w+',  # Breadcrumbs
                r'contact\s*us',
                r'about\s*us',
                r'privacy\s*policy',
                r'terms\s*of\s*service',
                r'copyright\s*\d{4}',
                r'all\s*rights\s*reserved'
            ]

            for pattern in common_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    template_phrases.append(pattern)

            # Create signature based on structure
            signature = f"h{heading_count}_l{list_count}_lnk{link_count}_img{image_count}"
            if template_phrases:
                signature += f"_tpl{'_'.join(template_phrases[:3])}"  # Max 3 phrases

            # Add content length category
            length_category = "short" if len(content) < 500 else "medium" if len(content) < 2000 else "long"
            signature += f"_{length_category}"

            return signature

        except Exception as e:
            self.logger.warning(f"Template signature extraction failed: {e}")
            return "unknown_template"

    def _is_template_duplicate(self, template_sig: str, url: str) -> bool:
        """Check if template signature indicates duplicate structure"""
        if template_sig in self.template_signatures:
            # Allow some variety within same template (e.g., 5 pages max)
            if len(self.template_signatures[template_sig]) >= 5:
                self.logger.debug(f"Template duplicate: {template_sig} (from {url})")
                return True
        else:
            self.template_signatures[template_sig] = []

        self.template_signatures[template_sig].append(url)
        return False

    def _is_text_similarity_duplicate(self, content: str, url: str) -> bool:
        """Check text similarity using cosine similarity or fallback method"""
        try:
            if not SKLEARN_AVAILABLE:
                # Use simple text hash fallback
                return self._is_text_similarity_duplicate_fallback(content, url)

            if not self.text_vectors:
                # First document - not a duplicate
                return False

            # Prepare text for vectorization
            clean_content = self._clean_text_for_similarity(content)

            if not self.vectorizer_fitted:
                # Fit vectorizer with existing content
                all_content = [fp.title + " " + self._clean_text_for_similarity(content)
                              for fp in self.content_fingerprints]
                if len(all_content) < 1:
                    return False

                all_content.append(clean_content)
                try:
                    self.vectorizer.fit(all_content)
                    self.vectorizer_fitted = True

                    # Re-vectorize all existing content
                    self.text_vectors = []
                    for content_text in all_content:
                        vector = self.vectorizer.transform([content_text]).toarray()[0]
                        self.text_vectors.append(vector)

                    # The last vector is for the new content - check against others
                    new_vector = self.text_vectors[-1]
                    for i, existing_vector in enumerate(self.text_vectors[:-1]):
                        similarity = cosine_similarity(new_vector.reshape(1, -1), existing_vector.reshape(1, -1))[0][0]
                        if similarity >= self.similarity_threshold:
                            self.logger.debug(f"Text similarity duplicate: {similarity:.3f} vs {self.similarity_threshold} (from {url})")
                            return True

                    return False

                except Exception as e:
                    self.logger.warning(f"Vectorizer fitting failed for {url}: {e}")
                    # Fall back to simple method
                    return self._is_text_similarity_duplicate_fallback(content, url)

            # Transform new content using fitted vectorizer
            try:
                new_vector = self.vectorizer.transform([clean_content]).toarray()[0]

                # Compare with existing vectors
                for i, existing_vector in enumerate(self.text_vectors):
                    similarity = cosine_similarity(new_vector.reshape(1, -1), existing_vector.reshape(1, -1))[0][0]
                    if similarity >= self.similarity_threshold:
                        self.logger.debug(f"Text similarity duplicate: {similarity:.3f} vs {self.similarity_threshold} (from {url})")
                        return True

                # Not a duplicate - store vector
                self.text_vectors.append(new_vector)
                return False

            except Exception as e:
                self.logger.warning(f"Vectorization failed for {url}: {e}")
                return self._is_text_similarity_duplicate_fallback(content, url)

        except Exception as e:
            self.logger.warning(f"Text similarity check failed for {url}: {e}")
            return self._is_text_similarity_duplicate_fallback(content, url)

    def _is_text_similarity_duplicate_fallback(self, content: str, url: str) -> bool:
        """Simple fallback text similarity using word overlap"""
        try:
            # Clean and normalize content
            clean_content = self._clean_text_for_similarity(content)
            words = set(clean_content.split())

            # Very short content is not useful for comparison
            if len(words) < 10:
                return False

            # Create a simple hash based on most common words
            common_words = sorted(words)[:50]  # Take up to 50 most frequent words
            text_signature = " ".join(common_words)
            text_hash = hashlib.md5(text_signature.encode()).hexdigest()

            if text_hash in self.simple_text_hashes:
                self.logger.debug(f"Simple text similarity duplicate detected for {url}")
                return True

            self.simple_text_hashes.add(text_hash)
            return False

        except Exception as e:
            self.logger.warning(f"Fallback text similarity check failed for {url}: {e}")
            return False

    def _clean_text_for_similarity(self, content: str) -> str:
        """Clean and normalize text for similarity analysis"""
        # Remove URLs, special characters, extra whitespace
        clean = re.sub(r'http[s]?://[^\s]+', '', content)
        clean = re.sub(r'[^\w\s]', ' ', clean)
        clean = re.sub(r'\s+', ' ', clean)
        return clean.strip().lower()

    def _add_content_fingerprint(self, url: str, content: str, title: str,
                                content_hash: str, url_pattern: str, template_sig: str):
        """Add content fingerprint to storage"""
        # For text similarity, prepare and store vector
        text_vector = None
        try:
            clean_content = self._clean_text_for_similarity(content)

            if not self.vectorizer_fitted and len(self.content_fingerprints) >= 1:
                # Fit vectorizer with existing content + new content
                all_content = [self._clean_text_for_similarity(fp.title + " " + content)
                              for fp in self.content_fingerprints]
                all_content.append(clean_content)

                self.vectorizer.fit(all_content)
                self.vectorizer_fitted = True

                # Re-vectorize all existing content
                self.text_vectors = []
                for content_text in all_content:
                    vector = self.vectorizer.transform([content_text]).toarray()[0]
                    self.text_vectors.append(vector)

                # The last vector is for the new content
                text_vector = self.text_vectors[-1]

            elif self.vectorizer_fitted:
                # Transform new content using fitted vectorizer
                vector = self.vectorizer.transform([clean_content]).toarray()[0]
                self.text_vectors.append(vector)
                text_vector = vector

        except Exception as e:
            self.logger.warning(f"Vector preparation failed for {url}: {e}")

        # Create and store fingerprint
        fingerprint = ContentFingerprint(
            url=url,
            content_hash=content_hash,
            text_vector=text_vector,
            url_pattern=url_pattern,
            template_signature=template_sig,
            content_length=len(content),
            title=title
        )

        self.content_fingerprints.append(fingerprint)
        self.content_hashes.add(content_hash)

    def _add_duplicate_example(self, category: str, url: str):
        """Add example URL to duplicate statistics"""
        if category not in self.stats.duplicate_examples:
            self.stats.duplicate_examples[category] = []

        # Keep only first 5 examples per category
        if len(self.stats.duplicate_examples[category]) < 5:
            self.stats.duplicate_examples[category].append(url)

    def get_deduplication_stats(self) -> DuplicationStats:
        """Get comprehensive deduplication statistics"""
        return self.stats

    def get_deduplication_summary(self) -> Dict[str, Any]:
        """Get human-readable deduplication summary"""
        total_duplicates = (self.stats.exact_duplicates +
                          self.stats.url_pattern_duplicates +
                          self.stats.text_similarity_duplicates +
                          self.stats.template_duplicates)

        duplicate_rate = total_duplicates / self.stats.total_pages_processed if self.stats.total_pages_processed > 0 else 0

        return {
            "total_processed": self.stats.total_pages_processed,
            "unique_kept": self.stats.unique_pages_kept,
            "total_duplicates": total_duplicates,
            "duplicate_rate": f"{duplicate_rate:.1%}",
            "breakdown": {
                "exact_duplicates": self.stats.exact_duplicates,
                "url_pattern_duplicates": self.stats.url_pattern_duplicates,
                "text_similarity_duplicates": self.stats.text_similarity_duplicates,
                "template_duplicates": self.stats.template_duplicates
            },
            "examples": self.stats.duplicate_examples
        }

    def reset(self):
        """Reset deduplicator state for new crawl session"""
        self.content_fingerprints.clear()
        self.content_hashes.clear()
        self.url_patterns.clear()
        self.template_signatures.clear()
        self.text_vectors.clear()
        self.simple_text_hashes.clear()
        self.vectorizer_fitted = False
        self.stats = DuplicationStats()

        # Reinitialize vectorizer if sklearn is available
        if SKLEARN_AVAILABLE:
            self.vectorizer = TfidfVectorizer(
                max_features=5000,
                stop_words='english',
                lowercase=True,
                strip_accents='ascii'
            )