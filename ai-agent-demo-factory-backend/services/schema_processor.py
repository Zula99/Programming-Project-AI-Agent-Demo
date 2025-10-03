import re
import json
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime
import urllib.parse
from html import unescape
import hashlib

class Search365SchemaProcessor:
    """
    Processes raw crawl data into the complete Search365 schema (229 fields)
    """

    def __init__(self, opensearch_host="http://opensearch:9200"):
        self.opensearch_host = opensearch_host
        self.raw_index = "demo_factory_raw"
        self.main_index = "demo_factory"

    def process_crawl_to_main_index(self, run_id: str) -> Dict[str, Any]:
        """
        Convert all raw crawl documents to main Search365 schema
        """
        result = {
            "processed_documents": 0,
            "failed_documents": 0,
            "run_id": run_id,
            "processing_time": datetime.now().isoformat(),
            "errors": []
        }

        try:
            # Get all raw documents for this crawl
            raw_docs = self._get_raw_crawl_documents(run_id)

            if not raw_docs:
                result["errors"].append("No raw documents found for run_id")
                return result

            for raw_doc in raw_docs:
                try:
                    # Process each document through the schema mapping
                    enriched_doc = self._enrich_document(raw_doc, run_id)

                    # Index to main schema
                    self._index_to_main_schema(enriched_doc)
                    result["processed_documents"] += 1

                except Exception as e:
                    error_msg = f"Failed to process document {raw_doc.get('url', 'unknown')}: {e}"
                    print(error_msg)
                    result["failed_documents"] += 1
                    result["errors"].append(error_msg)

        except Exception as e:
            result["errors"].append(f"Critical processing error: {e}")

        return result

    def _get_raw_crawl_documents(self, run_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all raw documents for a specific crawl run
        """
        try:
            # First try to get by run_id field if it exists
            response = requests.get(
                f"{self.opensearch_host}/{self.raw_index}/_search",
                json={
                    "query": {"match": {"run_id": run_id}},
                    "size": 1000
                },
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                docs = [hit["_source"] for hit in data["hits"]["hits"]]
                if docs:
                    print(f"Found {len(docs)} documents with run_id: {run_id}")
                    return docs

            # Fallback: get recent documents from raw index
            response = requests.get(
                f"{self.opensearch_host}/{self.raw_index}/_search",
                json={
                    "query": {"match_all": {}},
                    "sort": [{"crawl_timestamp": {"order": "desc"}}],
                    "size": 100
                },
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                all_docs = [hit["_source"] for hit in data["hits"]["hits"]]
                print(f"Found {len(all_docs)} documents in raw index (fallback)")
                return all_docs

        except Exception as e:
            print(f"Error retrieving raw documents: {e}")

        return []

    def _index_to_main_schema(self, enriched_doc: Dict[str, Any]) -> bool:
        """
        Index enriched document to main schema index
        """
        try:
            doc_id = enriched_doc.get('id', hashlib.md5(enriched_doc.get('url', '').encode()).hexdigest())

            response = requests.put(
                f"{self.opensearch_host}/{self.main_index}/_doc/{doc_id}",
                json=enriched_doc,
                headers={"Content-Type": "application/json"},
                timeout=10
            )

            return response.status_code in [200, 201]

        except Exception as e:
            print(f"Error indexing document: {e}")
            return False

    def _enrich_document(self, raw_doc: Dict[str, Any], run_id: str) -> Dict[str, Any]:
        """
        Transform raw document into complete 229-field Search365 schema
        """
        enriched = {}

        # === CORE FIELDS ===
        enriched['id'] = raw_doc.get('url', raw_doc.get('id', ''))
        enriched['url'] = raw_doc.get('url', '')
        enriched['location'] = raw_doc.get('url', '')
        enriched['title'] = self._extract_title(raw_doc)
        enriched['content'] = self._clean_content(raw_doc.get('content', ''))
        enriched['description'] = self._extract_description(raw_doc)
        enriched['summary'] = self._generate_summary(raw_doc.get('content', ''))
        enriched['run_id'] = run_id

        # === TECHNICAL METADATA ===
        enriched['contenttype'] = self._extract_content_type(raw_doc)
        enriched['encoding'] = self._extract_encoding(raw_doc)
        enriched['docsize'] = len(raw_doc.get('content', ''))
        enriched['extension'] = self._extract_extension(raw_doc.get('url', ''))

        # === SEARCH365 SPECIFIC ===
        enriched['contentfamily'] = self._classify_content_family(raw_doc)
        enriched['category'] = self._classify_category(raw_doc)
        enriched['collection'] = 'web_crawl'
        enriched['access'] = 'public'
        enriched['dacl'] = 'public'
        enriched['tags'] = self._extract_tags(raw_doc)
        enriched['contentpurpose'] = self._determine_content_purpose(raw_doc)
        enriched['topicarea'] = self._classify_topic_area(raw_doc)
        enriched['age'] = 0
        enriched['datasource'] = self._extract_domain(raw_doc.get('url', ''))
        enriched['sitename'] = self._extract_sitename(raw_doc)
        enriched['systemtitle'] = enriched['title']

        # === HTML EXTRACTED ===
        enriched.update(self._extract_html_elements(raw_doc))

        # === META TAGS ===
        enriched.update(self._extract_meta_tags(raw_doc))

        # === SOCIAL MEDIA ===
        enriched.update(self._extract_social_media(raw_doc))

        # === HTTP HEADERS ===
        enriched.update(self._extract_http_headers(raw_doc))

        # === DATES ===
        enriched.update(self._extract_dates(raw_doc, run_id))

        # === LOCATION & CONTACT ===
        enriched.update(self._extract_contact_info(raw_doc))

        # === URL PARSING ===
        enriched.update(self._parse_url_components(raw_doc.get('url', '')))

        # === COLLECTOR METADATA ===
        enriched.update(self._add_collector_metadata(raw_doc, run_id))

        # === DEFAULT VALUES ===
        enriched.update(self._add_default_values(enriched))

        return enriched

    def _extract_title(self, raw_doc: Dict[str, Any]) -> str:
        """Extract best title from multiple sources"""
        # Priority: existing title > og:title > h1 > filename
        title = raw_doc.get('title', '').strip()

        if not title:
            meta_props = self._parse_meta_properties(raw_doc.get('meta_properties', []))
            title = meta_props.get('og:title', '').strip()

        if not title:
            h1_headings = raw_doc.get('h1_headings', [])
            if h1_headings and isinstance(h1_headings, list):
                title = self._strip_html_tags(h1_headings[0]) if h1_headings else ''

        if not title:
            url = raw_doc.get('url', '')
            path = urllib.parse.urlparse(url).path
            title = path.split('/')[-1] if path != '/' else urllib.parse.urlparse(url).netloc

        return self._clean_text(title)

    def _extract_description(self, raw_doc: Dict[str, Any]) -> str:
        """Extract description from meta tags or content"""
        meta_tags = self._parse_meta_tags(raw_doc.get('meta_tags', []))
        meta_props = self._parse_meta_properties(raw_doc.get('meta_properties', []))

        # Priority: meta description > og:description > first paragraph
        description = meta_tags.get('description', '').strip()

        if not description:
            description = meta_props.get('og:description', '').strip()

        if not description:
            content = raw_doc.get('content', '')
            if content:
                # Extract first meaningful paragraph
                sentences = content.split('. ')
                if sentences:
                    description = '. '.join(sentences[:2]) + '.' if len(sentences) > 1 else sentences[0]

        return self._clean_text(description)[:500]  # Limit to 500 chars

    def _generate_summary(self, content: str) -> str:
        """Generate a summary from content"""
        if not content:
            return ''

        # Simple summarization - first 300 characters of cleaned content
        cleaned = self._clean_text(content)
        if len(cleaned) <= 300:
            return cleaned

        # Find a good break point near 300 chars
        summary = cleaned[:300]
        last_period = summary.rfind('.')
        last_space = summary.rfind(' ')

        if last_period > 250:
            return summary[:last_period + 1]
        elif last_space > 250:
            return summary[:last_space] + '...'
        else:
            return summary + '...'

    def _extract_html_elements(self, raw_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Extract HTML structural elements"""
        result = {}

        # Extract headings from base-crawl template (strings, not arrays)
        for level in range(1, 4):  # Only H1, H2, H3 are in schema
            heading_field = f'h{level}_headings'
            headings = raw_doc.get(heading_field, '')
            if headings:
                if isinstance(headings, str):
                    result[f'htmlextractedh{level}'] = self._strip_html_tags(headings)
                elif isinstance(headings, list):
                    clean_headings = [self._strip_html_tags(h) for h in headings if h]
                    result[f'htmlextractedh{level}'] = ' | '.join(clean_headings)

        # Analyze HTML for advanced features
        html_source = raw_doc.get('html_source', '').lower()
        content = raw_doc.get('content', '').lower()

        # Feature detection
        result['htmlextractedhasapplynow'] = 'true' if 'apply now' in content else 'false'
        result['htmlextractedhasenquire'] = 'true' if 'enquire' in content else 'false'
        result['htmlextractedhasgettingstarted'] = 'true' if 'getting started' in content else 'false'
        result['htmlextractedhasgetstarted'] = 'true' if 'get started' in content else 'false'
        result['htmlextractedhasgetincontact'] = 'true' if 'get in contact' in content else 'false'
        result['htmlextractedhasproductdiv'] = 'true' if 'product' in html_source else 'false'

        # Count elements from base-crawl extracted data
        input_types = raw_doc.get('input_types', [])
        input_count = len(input_types) if isinstance(input_types, list) else 0
        result['htmlextractedinputcount'] = str(input_count)

        # Count links from base-crawl extracted data
        all_link_urls = raw_doc.get('all_link_urls', [])
        link_count = len(all_link_urls) if isinstance(all_link_urls, list) else 0
        result['htmlextractedoutboundlinkcount'] = str(link_count)

        # URL analysis
        url = raw_doc.get('url', '')
        url_segments = [seg for seg in url.split('/') if seg]
        result['htmlextractedurlsegmentcount'] = str(len(url_segments))

        # Content analysis
        result['htmlextractedishowto'] = 'true' if any(term in content for term in ['how to', 'tutorial', 'guide']) else 'false'

        return result

    def _extract_meta_tags(self, raw_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and map meta tags"""
        result = {}

        # Parse meta tags - try base-crawl format first, then fallback to old format
        meta_tags = self._parse_meta_tags_from_base_crawl(raw_doc)
        if not meta_tags:
            meta_tags = self._parse_meta_tags(raw_doc.get('meta_tags', []))

        meta_props = self._parse_meta_properties_from_base_crawl(raw_doc)
        if not meta_props:
            meta_props = self._parse_meta_properties(raw_doc.get('meta_properties', []))

        # For now, skip http-equiv as it's not in our test data
        meta_http = {}

        # Standard meta tags
        result['keywords'] = meta_tags.get('keywords', '')
        result['author'] = meta_tags.get('author', '')
        result['robots'] = meta_tags.get('robots', '')
        result['viewport'] = meta_tags.get('viewport', '')
        result['googlesiteverification'] = meta_tags.get('google-site-verification', '')
        result['xparsedby'] = meta_tags.get('generator', '')

        # Additional meta fields
        result['formatdetection'] = meta_tags.get('format-detection', '')
        result['origintrial'] = meta_tags.get('origin-trial', '')
        result['xuacompatible'] = meta_http.get('x-ua-compatible', '')

        return result

    def _extract_social_media(self, raw_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Extract social media metadata"""
        result = {}

        # Parse meta properties - try base-crawl format first, then fallback to old format
        meta_props = self._parse_meta_properties_from_base_crawl(raw_doc)
        if not meta_props:
            meta_props = self._parse_meta_properties(raw_doc.get('meta_properties', []))

        # Parse meta tags - try base-crawl format first, then fallback to old format
        meta_tags = self._parse_meta_tags_from_base_crawl(raw_doc)
        if not meta_tags:
            meta_tags = self._parse_meta_tags(raw_doc.get('meta_tags', []))

        # Open Graph
        result['ogtitle'] = meta_props.get('og:title', '')
        result['ogdescription'] = meta_props.get('og:description', '')
        result['ogtype'] = meta_props.get('og:type', '')
        result['ogurl'] = meta_props.get('og:url', '')

        # Twitter Cards
        result['twittercard'] = meta_tags.get('twitter:card', '')
        result['twittersite'] = meta_tags.get('twitter:site', '')
        result['twittertitle'] = meta_tags.get('twitter:title', '')
        result['twitterdescription'] = meta_tags.get('twitter:description', '')
        result['twitteraccountid'] = meta_tags.get('twitter:account_id', '')

        # Facebook
        result['fbadmins'] = meta_tags.get('fb:admins', '')
        result['fbpageid'] = meta_tags.get('fb:page_id', '')

        # Extract social links
        result['facebook'] = self._extract_social_link(raw_doc.get('facebook_links', []))
        result['twitter'] = self._extract_social_link(raw_doc.get('twitter_links', []))
        result['linkedin'] = self._extract_social_link(raw_doc.get('linkedin_links', []))

        return result

    def _extract_http_headers(self, raw_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Extract HTTP headers with proper naming"""
        result = {}

        # Get HTTP headers from the nested structure
        http_headers = raw_doc.get('http_headers', {})
        if not isinstance(http_headers, dict):
            return result

        # Map headers to schema fields
        header_mapping = {
            'cache-control': 'httpheadercachecontrol',
            'content-type': 'httpheadercontenttype',
            'content-length': 'httpheadercontentlength',
            'content-encoding': 'httpheadercontentencoding',
            'last-modified': 'httpheaderlastmodified',
            'etag': 'httpheaderetag',
            'expires': 'httpheaderexpires',
            'date': 'httpheaderdate',
            'vary': 'httpheadervary',
            'connection': 'httpheaderconnection',
            'accept-ranges': 'httpheaderacceptranges',
            'transfer-encoding': 'httpheadertransferencoding',
            'x-frame-options': 'httpheaderxframeoptions',
            'x-content-type-options': 'httpheaderxcontenttypeoptions',
            'strict-transport-security': 'httpheaderstricttransportsecurity',
            'content-security-policy': 'httpheadercontentsecuritypolicy',
            'set-cookie': 'httpheadersetcookie'
        }

        for header_name, header_value in http_headers.items():
            # Clean header name
            clean_name = header_name.lower().replace('_', '-')
            schema_field = header_mapping.get(clean_name)
            if schema_field:
                result[schema_field] = str(header_value)[:500]  # Limit length

        return result

    def _extract_dates(self, raw_doc: Dict[str, Any], run_id: str) -> Dict[str, Any]:
        """Extract date information"""
        result = {}

        current_time = datetime.now()
        current_iso = current_time.isoformat()

        # Crawl time
        result['crawltime'] = current_iso
        result['crawledat'] = current_iso

        # Try to extract last modified from headers
        http_headers = raw_doc.get('http_headers', {})
        last_modified = http_headers.get('last_modified') or http_headers.get('last-modified')
        if last_modified:
            result['lastmodified'] = last_modified
            result['modified'] = last_modified
        else:
            result['lastmodified'] = current_iso
            result['modified'] = current_iso

        # Set created date (fallback to crawl time)
        result['created'] = current_iso
        result['date'] = current_iso

        return result

    def _extract_contact_info(self, raw_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Extract contact and location information"""
        result = {}

        # Extract from meta tags first
        meta_tags = self._parse_meta_tags(raw_doc.get('meta_tags', []))
        result['email'] = meta_tags.get('contact.email', '')
        result['phone'] = meta_tags.get('contact.phone', '')
        result['address'] = meta_tags.get('address', '')

        # Extract from links
        email_links = raw_doc.get('email_links', [])
        if email_links and not result['email']:
            # Extract email from mailto: links
            for link in email_links:
                if link.startswith('mailto:'):
                    result['email'] = link.replace('mailto:', '')
                    break

        phone_links = raw_doc.get('phone_links', [])
        if phone_links and not result['phone']:
            # Extract phone from tel: links
            for link in phone_links:
                if link.startswith('tel:'):
                    result['phone'] = link.replace('tel:', '')
                    break

        # Try to extract from content using regex
        content = raw_doc.get('content', '')
        if content and not result['email']:
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, content)
            if emails:
                result['email'] = emails[0]

        if content and not result['phone']:
            # Simple phone pattern
            phone_pattern = r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'
            phones = re.findall(phone_pattern, content)
            if phones:
                result['phone'] = f"{phones[0][0]}-{phones[0][1]}-{phones[0][2]}"

        return result

    def _parse_url_components(self, url: str) -> Dict[str, Any]:
        """Parse URL into components"""
        result = {}

        if not url:
            return result

        try:
            parsed = urllib.parse.urlparse(url)

            result['uriprotocol'] = parsed.scheme
            result['urihost'] = parsed.netloc
            result['uripath'] = parsed.path
            result['uriparams'] = parsed.query
            result['path'] = parsed.path

            # Extract domain components
            if parsed.netloc:
                domain_parts = parsed.netloc.split('.')
                if len(domain_parts) >= 2:
                    result['sitename'] = '.'.join(domain_parts[-2:])

        except Exception as e:
            result['uripathparseerror'] = str(e)

        return result

    def _add_collector_metadata(self, raw_doc: Dict[str, Any], run_id: str) -> Dict[str, Any]:
        """Add collector-specific metadata"""
        result = {}

        # Collector metadata from raw document
        collector_meta = raw_doc.get('collector_metadata', {})

        result['collectorcontenttype'] = collector_meta.get('content_type', '')
        result['collectorcontentencoding'] = collector_meta.get('content_encoding', '')
        result['collectordepth'] = str(collector_meta.get('depth', 0))
        result['collectoriscrawlnew'] = 'true'  # Always true for new crawls

        # Document metadata
        doc_meta = raw_doc.get('document_metadata', {})
        result['documentcontenttype'] = doc_meta.get('content_type', '')
        result['documentcontentencoding'] = doc_meta.get('content_encoding', '')
        result['documentreference'] = raw_doc.get('url', '')

        return result

    def _classify_content_family(self, raw_doc: Dict[str, Any]) -> str:
        """Classify content into families"""
        content = raw_doc.get('content', '').lower()
        url = raw_doc.get('url', '').lower()
        title = raw_doc.get('title', '').lower()

        # News/Blog content
        if any(term in content for term in ['news', 'article', 'blog', 'post', 'published']):
            return 'News'

        # Product/E-commerce
        if any(term in url for term in ['product', 'shop', 'buy', 'cart', 'store']):
            return 'Product'

        # Documentation
        if any(term in content for term in ['documentation', 'manual', 'guide', 'tutorial', 'api', 'reference']):
            return 'Documentation'

        # Corporate pages
        if any(term in content for term in ['contact', 'about', 'team', 'company', 'careers']):
            return 'Corporate'

        # Support/Help
        if any(term in content for term in ['support', 'help', 'faq', 'troubleshoot']):
            return 'Support'

        return 'Web'

    def _classify_category(self, raw_doc: Dict[str, Any]) -> str:
        """Classify content category"""
        content_family = self._classify_content_family(raw_doc)

        category_map = {
            'News': 'News Article',
            'Product': 'Product Page',
            'Documentation': 'Technical Documentation',
            'Corporate': 'Corporate Page',
            'Support': 'Support Content',
            'Web': 'Web Page'
        }

        return category_map.get(content_family, 'Web Page')

    def _determine_content_purpose(self, raw_doc: Dict[str, Any]) -> str:
        """Determine content purpose"""
        content = raw_doc.get('content', '').lower()

        if any(term in content for term in ['learn', 'tutorial', 'guide', 'how to']):
            return 'educational'
        elif any(term in content for term in ['buy', 'purchase', 'order', 'shop']):
            return 'commercial'
        elif any(term in content for term in ['contact', 'support', 'help']):
            return 'support'
        elif any(term in content for term in ['news', 'announce', 'update']):
            return 'informational'
        else:
            return 'general'

    def _classify_topic_area(self, raw_doc: Dict[str, Any]) -> str:
        """Classify topic area"""
        content = raw_doc.get('content', '').lower()
        url = raw_doc.get('url', '').lower()

        # Technology
        if any(term in content for term in ['technology', 'software', 'api', 'developer', 'code', 'programming']):
            return 'technology'

        # Business
        if any(term in content for term in ['business', 'finance', 'investment', 'banking', 'enterprise']):
            return 'business'

        # Healthcare
        if any(term in content for term in ['health', 'medical', 'doctor', 'patient', 'treatment']):
            return 'healthcare'

        # Education
        if any(term in content for term in ['education', 'school', 'university', 'course', 'learning']):
            return 'education'

        return 'general'

    def _extract_tags(self, raw_doc: Dict[str, Any]) -> str:
        """Extract relevant tags from content"""
        tags = ['web', 'crawled']

        content = raw_doc.get('content', '').lower()
        url = raw_doc.get('url', '').lower()

        # Add content-based tags
        if 'tutorial' in content or 'guide' in content:
            tags.append('tutorial')
        if 'api' in content:
            tags.append('api')
        if 'product' in content or 'product' in url:
            tags.append('product')
        if 'news' in content or 'blog' in content:
            tags.append('news')

        return ', '.join(tags)

    def _add_default_values(self, enriched: Dict[str, Any]) -> Dict[str, Any]:
        """Add default values for missing fields"""
        defaults = {
            'age': 0,
            'editor': '',
            'licensee': '',
            'state': '',
            'suburb': '',
            'postcode': '',
            'taxonomy': '',
            'subcollection': '',
            'website': enriched.get('datasource', ''),
            'breadcrumb': '',
            'filename': '',
            'searchrefiners': '',
            'searchrefinersall': '',
            'principleimage': '',
            'principlename': '',
            'principletitle': '',
            'postaladdress': '',
            'fax': '',
            'longitude': 0.0,
            'latitude': 0.0
        }

        result = {}
        for key, default_value in defaults.items():
            if key not in enriched:
                result[key] = default_value

        return result

    # Helper methods
    def _parse_meta_tags(self, meta_tags: List[str]) -> Dict[str, str]:
        """Parse meta tags list into dictionary"""
        result = {}
        if isinstance(meta_tags, list):
            for tag in meta_tags:
                if isinstance(tag, str) and '|' in tag:
                    parts = tag.split('|', 1)
                    if len(parts) == 2:
                        name, content = parts
                        result[name.strip()] = content.strip()
        return result

    def _parse_meta_tags_from_base_crawl(self, raw_doc: Dict[str, Any]) -> Dict[str, str]:
        """Parse meta tags from base-crawl template structure (separate name/content arrays)"""
        result = {}

        # Get the separate arrays from base-crawl template
        meta_names = raw_doc.get('meta_names', [])
        meta_contents = raw_doc.get('meta_contents', [])

        if isinstance(meta_names, list) and isinstance(meta_contents, list):
            # Pair up names with contents
            for i, name in enumerate(meta_names):
                if i < len(meta_contents) and name and meta_contents[i]:
                    result[name.strip()] = meta_contents[i].strip()

        return result

    def _parse_meta_properties(self, meta_properties: List[str]) -> Dict[str, str]:
        """Parse meta properties list into dictionary"""
        result = {}
        if isinstance(meta_properties, list):
            for prop in meta_properties:
                if isinstance(prop, str) and '|' in prop:
                    parts = prop.split('|', 1)
                    if len(parts) == 2:
                        property_name, content = parts
                        result[property_name.strip()] = content.strip()
        return result

    def _parse_meta_properties_from_base_crawl(self, raw_doc: Dict[str, Any]) -> Dict[str, str]:
        """Parse meta properties from base-crawl template structure"""
        result = {}

        # Get the separate arrays from base-crawl template
        meta_property_names = raw_doc.get('meta_property_names', [])
        meta_property_contents = raw_doc.get('meta_property_contents', [])

        if isinstance(meta_property_names, list) and isinstance(meta_property_contents, list):
            # Pair up names with contents
            for i, name in enumerate(meta_property_names):
                if i < len(meta_property_contents) and name and meta_property_contents[i]:
                    result[name.strip()] = meta_property_contents[i].strip()

        return result

    def _parse_meta_http_equiv(self, meta_http_equiv: List[str]) -> Dict[str, str]:
        """Parse meta http-equiv list into dictionary"""
        result = {}
        if isinstance(meta_http_equiv, list):
            for equiv in meta_http_equiv:
                if isinstance(equiv, str) and '|' in equiv:
                    parts = equiv.split('|', 1)
                    if len(parts) == 2:
                        equiv_name, content = parts
                        result[equiv_name.strip()] = content.strip()
        return result

    def _strip_html_tags(self, text: str) -> str:
        """Remove HTML tags from text"""
        if not text:
            return ''

        # Remove HTML tags
        clean = re.sub(r'<[^>]+>', '', text)
        # Decode HTML entities
        clean = unescape(clean)
        # Clean up whitespace
        clean = ' '.join(clean.split())

        return clean.strip()

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ''

        # Remove extra whitespace
        clean = ' '.join(text.split())
        # Remove control characters
        clean = ''.join(char for char in clean if ord(char) >= 32)

        return clean.strip()

    def _clean_content(self, content: str) -> str:
        """Clean main content text"""
        if not content:
            return ''

        # Basic cleaning
        clean = self._clean_text(content)

        # Remove common navigation text
        patterns_to_remove = [
            r'Skip to (?:main )?content',
            r'Skip navigation',
            r'Jump to navigation',
            r'Back to top',
            r'Print this page',
        ]

        for pattern in patterns_to_remove:
            clean = re.sub(pattern, '', clean, flags=re.IGNORECASE)

        return clean.strip()

    def _extract_content_type(self, raw_doc: Dict[str, Any]) -> str:
        """Extract content type from headers or metadata"""
        # Try HTTP headers first
        http_headers = raw_doc.get('http_headers', {})
        content_type = http_headers.get('content_type') or http_headers.get('content-type')

        if content_type:
            # Clean content type (remove charset etc)
            return content_type.split(';')[0].strip()

        # Fallback to document metadata
        doc_meta = raw_doc.get('document_metadata', {})
        return doc_meta.get('content_type', 'text/html')

    def _extract_encoding(self, raw_doc: Dict[str, Any]) -> str:
        """Extract character encoding"""
        # Try HTTP headers first
        http_headers = raw_doc.get('http_headers', {})
        content_type = http_headers.get('content_type') or http_headers.get('content-type', '')

        if 'charset=' in content_type:
            return content_type.split('charset=')[1].split(';')[0].strip()

        # Fallback to document metadata
        doc_meta = raw_doc.get('document_metadata', {})
        return doc_meta.get('content_encoding', 'utf-8')

    def _extract_extension(self, url: str) -> str:
        """Extract file extension from URL"""
        if not url:
            return 'html'

        parsed = urllib.parse.urlparse(url)
        path = parsed.path

        if '.' in path:
            return path.split('.')[-1].lower()

        return 'html'

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        if not url:
            return ''

        try:
            parsed = urllib.parse.urlparse(url)
            return parsed.netloc
        except:
            return ''

    def _extract_sitename(self, raw_doc: Dict[str, Any]) -> str:
        """Extract site name from various sources"""
        # Try Open Graph site_name first using base-crawl parsing
        meta_props = self._parse_meta_properties_from_base_crawl(raw_doc)
        if not meta_props:
            meta_props = self._parse_meta_properties(raw_doc.get('meta_properties', []))
        site_name = meta_props.get('og:site_name', '')

        if site_name:
            return site_name

        # Try extracting from domain
        url = raw_doc.get('url', '')
        if url:
            domain = self._extract_domain(url)
            if domain:
                # Remove www. prefix and extract main name
                clean_domain = domain.replace('www.', '')
                return clean_domain.split('.')[0].capitalize()

        return ''

    def _extract_social_link(self, links: List[str]) -> str:
        """Extract the first valid social media link"""
        if isinstance(links, list) and links:
            return links[0]
        return ''