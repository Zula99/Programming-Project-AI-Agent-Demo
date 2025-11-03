"""
Crawl Storage Utility - Filesystem scanning for completed crawls

Provides functions to discover and list completed crawl sessions from the
output directory structure. Supports Phase 2 of PLAN.md for manual indexing UI.
"""

from pathlib import Path
from typing import List, Dict, Optional
import json
import logging

logger = logging.getLogger(__name__)


def scan_crawl_output_directory(base_path: str = "./output/agent_crawls") -> List[Dict]:
    """
    Scan filesystem for all crawl directories with run_metadata.json

    Args:
        base_path: Base output directory path

    Returns:
        List of crawl metadata dictionaries
    """
    crawls = []
    base = Path(base_path)

    if not base.exists():
        logger.warning(f"Output directory not found: {base_path}")
        return crawls

    # Scan for run_metadata.json files
    # Structure: ./output/agent_crawls/{domain}/{run_id}/run_metadata.json
    for metadata_file in base.rglob("run_metadata.json"):
        try:
            metadata = get_crawl_metadata(metadata_file.parent)
            if metadata:
                crawls.append(metadata)
        except Exception as e:
            logger.error(f"Error reading metadata from {metadata_file}: {e}")

    logger.info(f"Found {len(crawls)} completed crawls in {base_path}")
    return crawls


def get_crawl_metadata(output_path: Path) -> Optional[Dict]:
    """
    Read run_metadata.json from crawl directory

    Args:
        output_path: Path to crawl output directory

    Returns:
        Metadata dictionary or None if not found/invalid
    """
    metadata_file = Path(output_path) / "run_metadata.json"

    if not metadata_file.exists():
        return None

    try:
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)

        # Validate required fields
        required_fields = ["run_id", "target_url", "domain", "status"]
        if not all(field in metadata for field in required_fields):
            logger.warning(f"Invalid metadata file (missing fields): {metadata_file}")
            return None

        return metadata

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse metadata JSON from {metadata_file}: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to read metadata from {metadata_file}: {e}")
        return None


def list_all_crawls(active_sessions: Dict = None, base_path: str = "./output/agent_crawls") -> List[Dict]:
    """
    Combines filesystem scan + in-memory sessions for complete crawl list

    Args:
        active_sessions: Optional dict of active crawl sessions (from main.py)
        base_path: Base output directory path

    Returns:
        List of crawl metadata dictionaries, deduplicated and sorted by date
    """
    # Get all crawls from filesystem
    all_crawls = scan_crawl_output_directory(base_path)

    # Add active sessions if provided
    if active_sessions:
        for run_id, session in active_sessions.items():
            # Only add running/pending sessions (completed ones are already in filesystem)
            if session.get("status") in ["running", "pending"]:
                all_crawls.append({
                    "run_id": run_id,
                    "target_url": session["target_url"],
                    "domain": session.get("domain", ""),
                    "status": session["status"],
                    "started_at": session.get("started_at", ""),
                    "completed_at": None,
                    "pages_crawled": session.get("progress", {}).get("pages_crawled", 0),
                    "quality_score": session.get("quality_score"),
                    "output_path": session.get("output_path", "")
                })

    # Deduplicate by run_id (prefer filesystem version for completed crawls)
    crawls_by_id = {}
    for crawl in all_crawls:
        run_id = crawl.get("run_id")
        if not run_id:
            continue

        # Prefer completed status over running (filesystem is source of truth)
        if run_id not in crawls_by_id or crawl.get("status") == "completed":
            crawls_by_id[run_id] = crawl

    # Sort by completed_at or started_at descending (most recent first)
    sorted_crawls = sorted(
        crawls_by_id.values(),
        key=lambda x: x.get("completed_at") or x.get("started_at", ""),
        reverse=True
    )

    logger.info(f"Returning {len(sorted_crawls)} total crawls (filesystem + sessions)")
    return sorted_crawls


def get_crawl_by_run_id(run_id: str, base_path: str = "./output/agent_crawls") -> Optional[Dict]:
    """
    Get metadata for a specific crawl by run_id

    Args:
        run_id: Unique run identifier
        base_path: Base output directory path

    Returns:
        Metadata dictionary or None if not found
    """
    base = Path(base_path)

    if not base.exists():
        return None

    # Search for run_metadata.json with matching run_id
    for metadata_file in base.rglob("run_metadata.json"):
        try:
            metadata = get_crawl_metadata(metadata_file.parent)
            if metadata and metadata.get("run_id") == run_id:
                return metadata
        except Exception as e:
            logger.error(f"Error checking metadata file {metadata_file}: {e}")

    return None


if __name__ == "__main__":
    # Quick test
    import sys

    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    # Scan for crawls
    crawls = scan_crawl_output_directory()

    print(f"\nFound {len(crawls)} completed crawls:\n")
    for crawl in crawls:
        print(f"  - {crawl['domain']} ({crawl['run_id'][:8]}...): {crawl['status']}")
        print(f"    Pages: {crawl.get('pages_crawled', 0)}, Quality: {crawl.get('quality_score', 'N/A')}")
        print(f"    Started: {crawl.get('started_at', 'N/A')}")
        print()
