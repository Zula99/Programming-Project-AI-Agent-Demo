import os
import json
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

def index_crawl_results_to_opensearch(run_id: str, opensearch_url: str = "http://opensearch:9200", index_name: str = "nab_search") -> Dict:
    """
    Index crawl results from Norconex XML output files to OpenSearch.
    
    Args:
        run_id: The crawl run ID
        opensearch_url: OpenSearch endpoint URL
        index_name: Target index name
    
    Returns:
        Dict with indexing results
    """
    logger.info(f"Starting indexing for crawl run {run_id}")
    
    # Look for XML output files in the norconex data directory
    data_dir = Path("/opt/norconex/data")
    if not data_dir.exists():
        data_dir = Path("./norconex_data")  # Fallback for development
        
    xml_output_dir = data_dir / "xml-output"
    
    if not xml_output_dir.exists():
        logger.warning(f"XML output directory not found: {xml_output_dir}")
        return {"indexed": 0, "failed": 0, "error": "XML output directory not found"}
    
    # Find XML files with our prefix
    xml_files = list(xml_output_dir.glob("nab-*.xml"))
    
    if not xml_files:
        logger.warning(f"No XML output files found in {xml_output_dir}")
        return {"indexed": 0, "failed": 0, "error": "No XML files found"}
    
    logger.info(f"Found {len(xml_files)} XML files to process")
    
    indexed_count = 0
    failed_count = 0
    errors = []
    
    for xml_file in xml_files:
        try:
            logger.info(f"Processing XML file: {xml_file}")
            
            # Parse the XML file
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            # Extract documents from the XML
            for doc_elem in root.findall('.//document'):
                try:
                    doc_data = extract_document_data(doc_elem)
                    if doc_data:
                        success = index_document_to_opensearch(doc_data, opensearch_url, index_name)
                        if success:
                            indexed_count += 1
                            logger.debug(f"Indexed document: {doc_data.get('url', 'unknown')}")
                        else:
                            failed_count += 1
                            logger.warning(f"Failed to index document: {doc_data.get('url', 'unknown')}")
                except Exception as e:
                    failed_count += 1
                    error_msg = f"Error processing document in {xml_file}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    
        except Exception as e:
            error_msg = f"Error processing XML file {xml_file}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
    
    result = {
        "indexed": indexed_count,
        "failed": failed_count,
        "xml_files_processed": len(xml_files)
    }
    
    if errors:
        result["errors"] = errors[:10]  # Keep only first 10 errors
    
    logger.info(f"Indexing completed: {indexed_count} indexed, {failed_count} failed")
    return result

def extract_document_data(doc_elem: ET.Element) -> Optional[Dict]:
    """
    Extract document data from a Norconex XML document element.
    
    Args:
        doc_elem: XML element containing document data
        
    Returns:
        Dictionary with document data or None if extraction fails
    """
    try:
        # Get the reference (URL)
        reference = doc_elem.get('reference')
        if not reference:
            return None
            
        # Extract content and metadata
        content = ""
        title = ""
        description = ""
        
        # Look for content in CDATA or text
        content_elem = doc_elem.find('.//content')
        if content_elem is not None:
            content = content_elem.text or ""
        
        # Extract title from metadata or content
        title_elem = doc_elem.find('.//meta[@name="title"]')
        if title_elem is not None:
            title = title_elem.get('content', '')
        else:
            # Try to extract from page_title field
            page_title_elem = doc_elem.find('.//meta[@name="page_title"]')
            if page_title_elem is not None:
                title = page_title_elem.get('content', '')
        
        # Extract description
        desc_elem = doc_elem.find('.//meta[@name="description"]')
        if desc_elem is not None:
            description = desc_elem.get('content', '')
        else:
            # Try meta_description field
            meta_desc_elem = doc_elem.find('.//meta[@name="meta_description"]')
            if meta_desc_elem is not None:
                description = meta_desc_elem.get('content', '')
        
        # Get content type
        content_type = "text/html"
        content_type_elem = doc_elem.find('.//meta[@name="document.contentType"]')
        if content_type_elem is not None:
            content_type = content_type_elem.get('content', 'text/html')
        
        # Get size
        size = 0
        size_elem = doc_elem.find('.//meta[@name="document.contentLength"]')
        if size_elem is not None:
            try:
                size = int(size_elem.get('content', '0'))
            except ValueError:
                size = 0
        
        # Create document data
        doc_data = {
            "title": title or extract_title_from_url(reference),
            "description": description or content[:200] + "..." if len(content) > 200 else content,
            "content": content,
            "url": reference,
            "contentType": content_type,
            "lastModified": "2024-01-15T00:00:00Z",  # Default timestamp
            "size": size,
            "crawlId": "auto-indexed"
        }
        
        return doc_data
        
    except Exception as e:
        logger.error(f"Error extracting document data: {e}")
        return None

def extract_title_from_url(url: str) -> str:
    """Extract a reasonable title from URL if no title is available."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        if path:
            # Use the last path segment as title
            title = path.split('/')[-1].replace('-', ' ').replace('_', ' ')
            return title.title()
        else:
            # Use domain name
            return parsed.netloc.replace('www.', '').title()
    except:
        return "Untitled Document"

def index_document_to_opensearch(doc_data: Dict, opensearch_url: str, index_name: str) -> bool:
    """
    Index a single document to OpenSearch.
    
    Args:
        doc_data: Document data dictionary
        opensearch_url: OpenSearch endpoint URL
        index_name: Target index name
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Generate document ID from URL
        doc_id = doc_data['url'].replace('/', '_').replace(':', '_').replace('?', '_').replace('=', '_')
        
        response = requests.post(
            f'{opensearch_url}/{index_name}/_doc/{doc_id}',
            headers={'Content-Type': 'application/json'},
            json=doc_data,
            timeout=30
        )
        
        return response.status_code in [200, 201]
        
    except Exception as e:
        logger.error(f"Error indexing document to OpenSearch: {e}")
        return False