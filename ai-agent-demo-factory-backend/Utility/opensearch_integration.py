"""
OpenSearch Integration Utility for Crawl4AI Demo Factory

This utility provides OpenSearch indexing capabilities for crawled content from Crawl4AI,
enabling semantic search across all demo sites as specified in US-047.

Features:
- Bulk indexing of crawl4ai output data
- Index management (create, delete, configure)
- Search functionality with ranking and filtering
- Integration with existing crawl4ai data structures
- Configurable connection settings
"""

import hashlib
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from urllib.parse import urlsplit
from typing import Dict, List, Optional, Any, Union
import logging
from dataclasses import dataclass

try:
    from opensearchpy import OpenSearch, helpers
    from opensearchpy.exceptions import OpenSearchException, NotFoundError
    OPENSEARCH_AVAILABLE = True
except ImportError:
    OPENSEARCH_AVAILABLE = False
    logger.warning("opensearch-py not installed. Install with: pip install opensearch-py")

try:
    from bs4 import BeautifulSoup
    HAVE_BS4 = True
except ImportError:
    HAVE_BS4 = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class OpenSearchConfig:
    """Configuration for OpenSearch connection"""
    host: str = os.getenv("OPENSEARCH_HOST", "opensearch-demo")
    port: int = int(os.getenv("OPENSEARCH_PORT", "9200"))
    scheme: str = "http"
    username: Optional[str] = None
    password: Optional[str] = None
    verify_certs: bool = False
    ca_certs_path: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3

@dataclass
class IndexConfig:
    """Configuration for OpenSearch index"""
    name: str
    number_of_shards: int = 1
    number_of_replicas: int = 0
    max_result_window: int = 10000

class Crawl4AIOpenSearchIntegration:
    """
    OpenSearch integration for Crawl4AI crawled content and system logs

    Provides functionality to:
    - Index crawled content from Crawl4AI output directories
    - Index system logs for real-time monitoring and debugging
    - Search across indexed content with semantic capabilities
    - Manage indices for different demo sites and log streams
    """

    def __init__(self, config: OpenSearchConfig = None):
        """
        Initialize OpenSearch integration

        Args:
            config: OpenSearch configuration (uses defaults if None)
        """
        if not OPENSEARCH_AVAILABLE:
            raise ImportError("opensearch-py is required. Install with: pip install opensearch-py")

        self.config = config or OpenSearchConfig()
        self.client = self._create_client()
        self._verify_connection()
        # Cache known indices to avoid repeated existence checks
        self._known_indices = set()

    def _create_client(self) -> OpenSearch:
        """Create OpenSearch client with configuration"""
        client_config = {
            'hosts': [{'host': self.config.host, 'port': self.config.port}],
            'http_compress': True,
            'timeout': self.config.timeout,
            'max_retries': self.config.max_retries,
            'retry_on_timeout': True,
            'use_ssl': self.config.scheme == 'https',
            'verify_certs': self.config.verify_certs,
            'ssl_show_warn': False
        }

        # Add authentication if provided
        if self.config.username and self.config.password:
            client_config['http_auth'] = (self.config.username, self.config.password)

        # Add CA certs if provided
        if self.config.ca_certs_path:
            client_config['ca_certs'] = self.config.ca_certs_path

        return OpenSearch(**client_config)

    def _verify_connection(self):
        """Verify OpenSearch connection"""
        try:
            info = self.client.info()
            logger.info(f"Connected to OpenSearch cluster: {info['cluster_name']} (version: {info['version']['number']})")
        except Exception as e:
            logger.error(f"Failed to connect to OpenSearch: {e}")
            raise

    def create_index(self, index_config: IndexConfig, recreate: bool = False) -> bool:
        """
        Create OpenSearch index with optimized settings for demo content

        Args:
            index_config: Index configuration
            recreate: If True, delete existing index first

        Returns:
            True if index created successfully
        """
        if recreate and self.client.indices.exists(index=index_config.name):
            logger.info(f"Deleting existing index: {index_config.name}")
            self.client.indices.delete(index=index_config.name)

        if self.client.indices.exists(index=index_config.name):
            logger.info(f"Index {index_config.name} already exists")
            return True

        # Index mapping optimized for demo content search
        mapping = {
            "settings": {
                "number_of_shards": index_config.number_of_shards,
                "number_of_replicas": index_config.number_of_replicas,
                "max_result_window": index_config.max_result_window,
                "analysis": {
                    "analyzer": {
                        "content_analyzer": {
                            "type": "standard",
                            "stopwords": "_english_"
                        },
                        "url_analyzer": {
                            "type": "keyword"
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "url": {"type": "keyword", "index": True},
                    "host": {"type": "keyword", "index": True},
                    "path": {"type": "text", "analyzer": "url_analyzer"},
                    "canonical": {"type": "keyword", "index": True},
                    "title": {
                        "type": "text",
                        "analyzer": "content_analyzer",
                        "fields": {"raw": {"type": "keyword"}}
                    },
                    "content_md": {
                        "type": "text",
                        "analyzer": "content_analyzer"
                    },
                    "meta_desc": {
                        "type": "text",
                        "analyzer": "content_analyzer"
                    },
                    "h1": {"type": "text", "analyzer": "content_analyzer"},
                    "h2": {"type": "text", "analyzer": "content_analyzer"},
                    "h3": {"type": "text", "analyzer": "content_analyzer"},
                    "tags": {"type": "keyword", "index": True},
                    "content_type": {"type": "keyword", "index": True},
                    "bytes_html": {"type": "integer"},
                    "fetched_at": {"type": "date"},
                    "checksum": {"type": "keyword", "index": True},
                    "indexed_at": {"type": "date"}
                }
            }
        }

        try:
            self.client.indices.create(index=index_config.name, body=mapping)
            logger.info(f"Successfully created index: {index_config.name}")
            return True
        except OpenSearchException as e:
            logger.error(f"Failed to create index {index_config.name}: {e}")
            return False

    def index_crawl4ai_data(self, crawl_output_dir: Union[str, Path], index_name: str,
                           batch_size: int = 100, domain_tag: str = None) -> Dict[str, Any]:
        """
        Index crawled content from Crawl4AI output directory

        Args:
            crawl_output_dir: Path to crawl4ai output directory (e.g., "output/nab")
            index_name: Target OpenSearch index name
            batch_size: Number of documents per batch
            domain_tag: Tag to add to all documents (defaults to domain from first URL)

        Returns:
            Dictionary with indexing statistics
        """
        crawl_dir = Path(crawl_output_dir)
        if not crawl_dir.exists():
            raise ValueError(f"Crawl output directory not found: {crawl_dir}")

        # Ensure index exists
        index_config = IndexConfig(name=index_name)
        self.create_index(index_config)

        documents = []
        stats = {
            "total_folders_found": 0,
            "documents_processed": 0,
            "documents_indexed": 0,
            "errors": 0,
            "batch_count": 0,
            "start_time": datetime.now()
        }

        logger.info(f"Starting indexing of {crawl_dir} into {index_name}")

        # Walk through crawl output directory
        for folder, _, files in os.walk(crawl_dir):
            folder_path = Path(folder)

            # Look for crawl4ai output structure (index.md + meta.json)
            if "index.md" in files and "meta.json" in files:
                stats["total_folders_found"] += 1

                try:
                    doc = self._process_crawl_folder(folder_path, files, domain_tag)
                    if doc:
                        documents.append(doc)
                        stats["documents_processed"] += 1

                        # Batch indexing
                        if len(documents) >= batch_size:
                            indexed_count = self._bulk_index_documents(documents, index_name)
                            stats["documents_indexed"] += indexed_count
                            stats["batch_count"] += 1
                            logger.info(f"Indexed batch {stats['batch_count']}: {indexed_count} documents")
                            documents = []

                except Exception as e:
                    logger.error(f"Error processing folder {folder_path}: {e}")
                    stats["errors"] += 1

        # Index remaining documents
        if documents:
            indexed_count = self._bulk_index_documents(documents, index_name)
            stats["documents_indexed"] += indexed_count
            stats["batch_count"] += 1
            logger.info(f"Indexed final batch: {indexed_count} documents")

        stats["end_time"] = datetime.now()
        stats["duration"] = (stats["end_time"] - stats["start_time"]).total_seconds()

        logger.info(f"Indexing complete: {stats['documents_indexed']}/{stats['documents_processed']} documents indexed in {stats['duration']:.2f}s")
        return stats

    def _process_crawl_folder(self, folder_path: Path, files: List[str], domain_tag: str = None) -> Optional[Dict[str, Any]]:
        """Process a single crawl folder into an OpenSearch document"""
        try:
            # Load core files
            md_content = self._load_text(folder_path / "index.md")
            meta_content = self._load_text(folder_path / "meta.json")
            html_content = self._load_text(folder_path / "raw.html") if "raw.html" in files else ""

            if not meta_content:
                logger.warning(f"No meta.json found in {folder_path}")
                return None

            meta = json.loads(meta_content)
            url = meta.get("url", "")
            if not url:
                logger.warning(f"No URL found in meta.json for {folder_path}")
                return None

            # Parse URL components
            parts = urlsplit(url)
            host = parts.netloc.lower()
            path = parts.path

            # Extract HTML metadata
            canonical = self._canonical_from_html(html_content) if html_content else None
            headings = self._headings_from_html(html_content) if html_content else {"h1": [], "h2": [], "h3": []}
            meta_desc = self._meta_description_from_html(html_content) if html_content else None

            # Generate stable document ID
            stable_id = self._sha1((canonical or url).strip())

            # Content checksum for incremental updates
            checksum = self._sha1(md_content) if md_content else self._sha1(html_content)

            # Determine domain tag
            if not domain_tag:
                domain_tag = host.replace("www.", "").split(".")[0]

            # Build document
            doc = {
                "url": url,
                "host": host,
                "path": path,
                "canonical": canonical or url,
                "title": meta.get("title") or (headings["h1"][0] if headings["h1"] else None),
                "h1": headings["h1"],
                "h2": headings["h2"],
                "h3": headings["h3"],
                "content_md": md_content,
                "meta_desc": meta_desc,
                "bytes_html": int(meta.get("bytes_html", 0)),
                "fetched_at": meta.get("fetched_at"),
                "content_type": meta.get("content_type"),
                "tags": [domain_tag] if domain_tag else [],
                "checksum": checksum,
                "indexed_at": datetime.now().isoformat(),
                "_id": stable_id
            }

            return doc

        except Exception as e:
            logger.error(f"Error processing folder {folder_path}: {e}")
            return None

    def _bulk_index_documents(self, documents: List[Dict[str, Any]], index_name: str) -> int:
        """Bulk index documents to OpenSearch"""
        if not documents:
            return 0

        # Format for bulk API
        actions = []
        for doc in documents:
            doc_id = doc.pop('_id', None)
            action = {
                "_index": index_name,
                "_source": doc
            }
            if doc_id:
                action["_id"] = doc_id
            actions.append(action)

        try:
            # Use helpers.bulk for efficient indexing
            success, failed = helpers.bulk(
                self.client,
                actions,
                index=index_name,
                chunk_size=100,
                request_timeout=60,
                max_retries=3
            )
            return success
        except Exception as e:
            logger.error(f"Bulk indexing failed: {e}")
            return 0

    def search(self, query: str, index_name: str, size: int = 10,
               filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Search indexed content with OpenSearch

        Args:
            query: Search query
            index_name: Index to search
            size: Number of results to return
            filters: Additional filters (e.g., {"host": "example.com"})

        Returns:
            Search results with hits and metadata
        """
        search_body = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": [
                                    "title^3",
                                    "h1^2",
                                    "h2^1.5",
                                    "h3^1.2",
                                    "content_md^1",
                                    "meta_desc^2"
                                ],
                                "type": "best_fields",
                                "fuzziness": "AUTO"
                            }
                        }
                    ]
                }
            },
            "size": size,
            "sort": [
                "_score",
                {"fetched_at": {"order": "desc"}}
            ],
            "highlight": {
                "fields": {
                    "content_md": {"fragment_size": 150, "number_of_fragments": 3},
                    "title": {},
                    "meta_desc": {}
                }
            }
        }

        # Add filters if provided
        if filters:
            for field, value in filters.items():
                search_body["query"]["bool"]["must"].append({
                    "term": {field: value}
                })

        try:
            results = self.client.search(index=index_name, body=search_body)
            return {
                "total_hits": results["hits"]["total"]["value"],
                "max_score": results["hits"]["max_score"],
                "hits": [
                    {
                        "score": hit["_score"],
                        "url": hit["_source"]["url"],
                        "title": hit["_source"]["title"],
                        "meta_desc": hit["_source"].get("meta_desc"),
                        "highlight": hit.get("highlight", {}),
                        "source": hit["_source"]
                    }
                    for hit in results["hits"]["hits"]
                ],
                "took": results["took"]
            }
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {"total_hits": 0, "hits": [], "error": str(e)}

    def delete_index(self, index_name: str) -> bool:
        """Delete an index"""
        try:
            self.client.indices.delete(index=index_name)
            logger.info(f"Successfully deleted index: {index_name}")
            return True
        except NotFoundError:
            logger.warning(f"Index {index_name} not found")
            return False
        except Exception as e:
            logger.error(f"Failed to delete index {index_name}: {e}")
            return False

    def get_index_stats(self, index_name: str) -> Dict[str, Any]:
        """Get statistics for an index"""
        try:
            stats = self.client.indices.stats(index=index_name)
            count_result = self.client.count(index=index_name)

            return {
                "document_count": count_result["count"],
                "store_size": stats["indices"][index_name]["total"]["store"]["size_in_bytes"],
                "index_name": index_name
            }
        except Exception as e:
            logger.error(f"Failed to get stats for {index_name}: {e}")
            return {"error": str(e)}

    def list_all_indexes(self, pattern: str = "demo-*") -> List[Dict]:
        """
        List all indexes matching pattern with metadata

        Args:
            pattern: Index pattern to match (default: demo-*)

        Returns:
            List of index metadata dictionaries
        """
        try:
            # Get all indexes matching pattern
            indices = self.client.cat.indices(index=pattern, format="json")

            results = []
            for idx in indices:
                results.append({
                    "name": idx["index"],
                    "doc_count": int(idx.get("docs.count", 0)),
                    "size_bytes": idx.get("store.size", "0b"),
                    "status": idx.get("health", "unknown")
                })

            return results
        except Exception as e:
            logger.error(f"Failed to list indexes: {e}")
            return []

    def get_all_demo_indexes(self) -> List[Dict]:
        """
        Get all demo-* indexes with parsed metadata

        Returns:
            List of index dictionaries with parsed domain and run_id
        """
        indexes = self.list_all_indexes("demo-*")

        # Parse index names to extract domain and run_id
        # Format: demo-domain_com-run_id
        for idx in indexes:
            name = idx["name"]
            if name.startswith("demo-"):
                parts = name[5:].split("-")
                if len(parts) >= 2:
                    idx["domain"] = parts[0].replace("_", ".")
                    idx["run_id"] = "-".join(parts[1:])

        return indexes

    def index_exists(self, index_name: str) -> bool:
        """
        Check if index exists

        Args:
            index_name: Name of the index to check

        Returns:
            True if index exists, False otherwise
        """
        try:
            return self.client.indices.exists(index=index_name)
        except Exception as e:
            logger.error(f"Failed to check index existence: {e}")
            return False

    def create_log_index(self, index_name: str, recreate: bool = False) -> bool:
        """
        Create OpenSearch index optimized for system logs

        Args:
            index_name: Name for the log index (e.g., "ai-agent-logs-2024.01")
            recreate: If True, delete existing index first

        Returns:
            True if index created successfully
        """
        # Check cache first to avoid repeated API calls
        if index_name in self._known_indices and not recreate:
            return True

        if recreate and self.client.indices.exists(index=index_name):
            logger.info(f"Deleting existing log index: {index_name}")
            self.client.indices.delete(index=index_name)
            self._known_indices.discard(index_name)

        if self.client.indices.exists(index=index_name):
            # Only log once per index
            if index_name not in self._known_indices:
                logger.info(f"Log index {index_name} already exists")
            self._known_indices.add(index_name)
            return True

        # Log mapping optimized for real-time monitoring
        log_mapping = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "max_result_window": 10000,
                "index.refresh_interval": "1s",  # Fast refresh for real-time logs
                "analysis": {
                    "analyzer": {
                        "log_analyzer": {
                            "type": "standard",
                            "stopwords": "_none_"  # Keep all words in logs
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "@timestamp": {"type": "date"},
                    "level": {"type": "keyword", "index": True},
                    "service": {"type": "keyword", "index": True},
                    "component": {"type": "keyword", "index": True},
                    "domain": {"type": "keyword", "index": True},
                    "message": {
                        "type": "text",
                        "analyzer": "log_analyzer",
                        "fields": {"raw": {"type": "keyword"}}
                    },
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "keyword"},
                            "ai_confidence": {"type": "float"},
                            "cost_usd": {"type": "float"},
                            "execution_time_ms": {"type": "integer"},
                            "error_code": {"type": "keyword"},
                            "user_agent": {"type": "keyword"}
                        }
                    },
                    "thread_id": {"type": "keyword"},
                    "process_id": {"type": "keyword"},
                    "hostname": {"type": "keyword"}
                }
            }
        }

        try:
            self.client.indices.create(index=index_name, body=log_mapping)
            logger.info(f"Successfully created log index: {index_name}")
            self._known_indices.add(index_name)
            return True
        except OpenSearchException as e:
            logger.error(f"Failed to create log index {index_name}: {e}")
            return False

    def index_log_entry(self, log_entry: Dict[str, Any], index_name: str) -> bool:
        """
        Index a single log entry to OpenSearch

        Args:
            log_entry: Log entry dictionary with timestamp, level, message, etc.
            index_name: Target log index name

        Returns:
            True if indexed successfully
        """
        # Ensure log index exists
        self.create_log_index(index_name)

        # Add indexed timestamp if not present
        if "@timestamp" not in log_entry:
            log_entry["@timestamp"] = datetime.now().isoformat()

        try:
            result = self.client.index(
                index=index_name,
                body=log_entry,
                refresh=True  # Make immediately searchable
            )
            return result["result"] in ["created", "updated"]
        except Exception as e:
            logger.error(f"Failed to index log entry: {e}")
            return False

    def bulk_index_logs(self, log_entries: List[Dict[str, Any]], index_name: str) -> int:
        """
        Bulk index multiple log entries to OpenSearch

        Args:
            log_entries: List of log entry dictionaries
            index_name: Target log index name

        Returns:
            Number of successfully indexed entries
        """
        if not log_entries:
            return 0

        # Ensure log index exists
        self.create_log_index(index_name)

        # Format for bulk API
        actions = []
        for entry in log_entries:
            if "@timestamp" not in entry:
                entry["@timestamp"] = datetime.now().isoformat()

            actions.append({
                "_index": index_name,
                "_source": entry
            })

        try:
            success, failed = helpers.bulk(
                self.client,
                actions,
                index=index_name,
                chunk_size=100,
                request_timeout=30,
                max_retries=3
            )
            return success
        except Exception as e:
            logger.error(f"Bulk log indexing failed: {e}")
            return 0

    def search_logs(self, query: str = "*", index_name: str = None,
                   level: str = None, service: str = None, component: str = None,
                   time_from: str = None, time_to: str = None, size: int = 100) -> Dict[str, Any]:
        """
        Search system logs with filtering

        Args:
            query: Search query for log messages
            index_name: Log index to search (searches all log indices if None)
            level: Filter by log level (INFO, WARN, ERROR, DEBUG)
            service: Filter by service name
            component: Filter by component name
            time_from: Start time filter (ISO format)
            time_to: End time filter (ISO format)
            size: Number of results to return

        Returns:
            Search results with log entries
        """
        # Use pattern to search all log indices if none specified
        search_index = index_name or "ai-agent-logs-*"

        search_body = {
            "query": {
                "bool": {
                    "must": [],
                    "filter": []
                }
            },
            "size": size,
            "sort": [{"@timestamp": {"order": "desc"}}]
        }

        # Add text query
        if query and query != "*":
            search_body["query"]["bool"]["must"].append({
                "multi_match": {
                    "query": query,
                    "fields": ["message^2", "component", "service"],
                    "type": "best_fields"
                }
            })
        else:
            search_body["query"]["bool"]["must"].append({"match_all": {}})

        # Add filters
        if level:
            search_body["query"]["bool"]["filter"].append({"term": {"level": level}})
        if service:
            search_body["query"]["bool"]["filter"].append({"term": {"service": service}})
        if component:
            search_body["query"]["bool"]["filter"].append({"term": {"component": component}})

        # Add time range filter
        if time_from or time_to:
            time_filter = {"range": {"@timestamp": {}}}
            if time_from:
                time_filter["range"]["@timestamp"]["gte"] = time_from
            if time_to:
                time_filter["range"]["@timestamp"]["lte"] = time_to
            search_body["query"]["bool"]["filter"].append(time_filter)

        try:
            results = self.client.search(index=search_index, body=search_body)
            return {
                "total_hits": results["hits"]["total"]["value"],
                "logs": [
                    {
                        "timestamp": hit["_source"]["@timestamp"],
                        "level": hit["_source"]["level"],
                        "service": hit["_source"].get("service"),
                        "component": hit["_source"].get("component"),
                        "message": hit["_source"]["message"],
                        "metadata": hit["_source"].get("metadata", {}),
                        "source": hit["_source"]
                    }
                    for hit in results["hits"]["hits"]
                ],
                "took": results["took"]
            }
        except Exception as e:
            logger.error(f"Log search failed: {e}")
            return {"total_hits": 0, "logs": [], "error": str(e)}

    # Utility methods (similar to export_bulk_ndjson.py)
    def _sha1(self, s: str) -> str:
        """Generate SHA1 hash of string"""
        return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()

    def _load_text(self, path: Path) -> str:
        """Load text file with UTF-8 encoding"""
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""

    def _canonical_from_html(self, html: str) -> Optional[str]:
        """Extract canonical URL from HTML"""
        if not html or not HAVE_BS4:
            return None
        soup = BeautifulSoup(html, "html.parser")
        tag = soup.find("link", rel=lambda v: v and "canonical" in v)
        if tag and tag.get("href"):
            return tag["href"].strip()
        return None

    def _meta_description_from_html(self, html: str) -> Optional[str]:
        """Extract meta description from HTML"""
        if not html or not HAVE_BS4:
            return None
        soup = BeautifulSoup(html, "html.parser")
        tag = soup.find("meta", attrs={"name": "description"}) or \
              soup.find("meta", attrs={"property": "og:description"})
        return (tag.get("content") or "").strip() if tag else None

    def _headings_from_html(self, html: str) -> Dict[str, List[str]]:
        """Extract headings from HTML"""
        if not html or not HAVE_BS4:
            return {"h1": [], "h2": [], "h3": []}
        soup = BeautifulSoup(html, "html.parser")
        pick = lambda sel: [h.get_text(" ", strip=True) for h in soup.select(sel)]
        return {
            "h1": pick("h1"),
            "h2": pick("h2"),
            "h3": pick("h3")
        }


def main():
    """Example usage and CLI interface"""
    import argparse

    parser = argparse.ArgumentParser(description="OpenSearch integration for Crawl4AI")
    parser.add_argument("--crawl-dir", required=True, help="Path to crawl4ai output directory")
    parser.add_argument("--index-name", required=True, help="OpenSearch index name")
    parser.add_argument("--host", default="localhost", help="OpenSearch host")
    parser.add_argument("--port", type=int, default=9200, help="OpenSearch port")
    parser.add_argument("--recreate", action="store_true", help="Recreate index if exists")
    parser.add_argument("--search", help="Search query to test")

    args = parser.parse_args()

    # Configure OpenSearch
    config = OpenSearchConfig(host=args.host, port=args.port)
    integration = Crawl4AIOpenSearchIntegration(config)

    # Index data
    if args.recreate:
        integration.delete_index(args.index_name)

    logger.info(f"Indexing {args.crawl_dir} to {args.index_name}")
    stats = integration.index_crawl4ai_data(args.crawl_dir, args.index_name)

    logger.info(f"Indexing Results:")
    logger.info(f"  Documents indexed: {stats['documents_indexed']}")
    logger.info(f"  Processing time: {stats['duration']:.2f}s")
    logger.info(f"  Errors: {stats['errors']}")

    # Test search if query provided
    if args.search:
        logger.info(f"Testing search: '{args.search}'")
        results = integration.search(args.search, args.index_name)
        logger.info(f"  Found {results['total_hits']} results")
        for i, hit in enumerate(results['hits'][:3]):
            logger.info(f"  {i+1}. {hit['title']} - {hit['url']} (score: {hit['score']:.2f})")


if __name__ == "__main__":
    main()