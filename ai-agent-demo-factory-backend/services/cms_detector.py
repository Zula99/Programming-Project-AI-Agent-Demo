"""
CMS/Platform Detection Service
Utilizes tools from wus_utilites_lib.py for website CMS and platform detection
"""

import requests
import re
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Optional, Tuple
from services.search365.wus_utilites_lib import WusUtilities, Search365Lib
import json


class CMSDetector:
    """CMS and platform detector"""
    
    def __init__(self):
        self.wus_utils = WusUtilities()
        # Search365Lib requires env_name_path parameter, but we'll make it optional for CMS detection
        try:
            self.search365_lib = Search365Lib('.env')
        except:
            # If Search365Lib fails to initialize, we'll use a mock version for basic functionality
            self.search365_lib = None
        
        # CMS feature detection rules
        self.cms_patterns = {
            'WordPress': {
                'html_patterns': [
                    r'wp-content/themes/',
                    r'wp-includes/',
                    r'wp-json/',
                    r'wordpress',
                    r'wp-admin/',
                    r'wp-content/plugins/'
                ],
                'meta_patterns': [
                    r'<meta name="generator" content="WordPress',
                    r'<link[^>]*wp-content/',
                    r'<script[^>]*wp-content/'
                ],
                'response_headers': ['x-powered-by: wordpress'],
                'url_patterns': ['/wp-admin/', '/wp-content/', '/wp-includes/']
            },
            'Drupal': {
                'html_patterns': [
                    r'/sites/default/files/',
                    r'/modules/',
                    r'/themes/',
                    r'drupal',
                    r'/misc/',
                    r'/profiles/'
                ],
                'meta_patterns': [
                    r'<meta name="generator" content="Drupal',
                    r'<link[^>]*sites/default/',
                    r'<script[^>]*misc/'
                ],
                'response_headers': ['x-drupal-cache', 'x-generator: drupal'],
                'url_patterns': ['/node/', '/user/', '/admin/']
            },
            'Joomla': {
                'html_patterns': [
                    r'/media/',
                    r'/templates/',
                    r'/administrator/',
                    r'joomla',
                    r'/components/',
                    r'/modules/'
                ],
                'meta_patterns': [
                    r'<meta name="generator" content="Joomla',
                    r'<link[^>]*templates/',
                    r'<script[^>]*media/'
                ],
                'response_headers': ['x-powered-by: joomla'],
                'url_patterns': ['/administrator/', '/component/', '/modules/']
            },
            'Shopify': {
                'html_patterns': [
                    r'shopify',
                    r'shopifycdn',
                    r'cdn\.shopify\.com',
                    r'shopify\.com',
                    r'cdn\.shopifycdn\.com'
                ],
                'meta_patterns': [
                    r'<meta name="generator" content="Shopify',
                    r'<link[^>]*cdn\.shopify',
                    r'<script[^>]*cdn\.shopify'
                ],
                'response_headers': ['x-shopify-stage', 'x-shopify-shop-domain'],
                'url_patterns': ['/collections/', '/products/', '/cart/', '/checkout/']
            },
            'Magento': {
                'html_patterns': [
                    r'magento',
                    r'/media/',
                    r'/skin/',
                    r'/js/',
                    r'/app/',
                    r'/var/'
                ],
                'meta_patterns': [
                    r'<meta name="generator" content="Magento',
                    r'<link[^>]*skin/',
                    r'<script[^>]*js/'
                ],
                'response_headers': ['x-magento-version'],
                'url_patterns': ['/catalog/', '/customer/', '/checkout/']
            },
            'Wix': {
                'html_patterns': [
                    r'wix\.com',
                    r'wixstatic\.com',
                    r'wixpress\.com',
                    r'wix\.com/_partials/'
                ],
                'meta_patterns': [
                    r'<meta name="generator" content="Wix',
                    r'<link[^>]*wixstatic',
                    r'<script[^>]*wix\.com'
                ],
                'response_headers': ['x-wix-version'],
                'url_patterns': ['/_partials/', '/_api/']
            },
            'Squarespace': {
                'html_patterns': [
                    r'squarespace',
                    r'squarespace-cdn\.com',
                    r'squarespace\.com'
                ],
                'meta_patterns': [
                    r'<meta name="generator" content="Squarespace',
                    r'<link[^>]*squarespace-cdn',
                    r'<script[^>]*squarespace'
                ],
                'response_headers': ['x-squarespace-version'],
                'url_patterns': ['/s/', '/config/']
            },
            'Ghost': {
                'html_patterns': [
                    r'ghost',
                    r'/ghost/',
                    r'/assets/',
                    r'ghost\.org'
                ],
                'meta_patterns': [
                    r'<meta name="generator" content="Ghost',
                    r'<link[^>]*/assets/',
                    r'<script[^>]*ghost'
                ],
                'response_headers': ['x-powered-by: ghost'],
                'url_patterns': ['/ghost/', '/tag/', '/author/']
            },
            'Webflow': {
                'html_patterns': [
                    r'webflow',
                    r'webflow\.com',
                    r'webflow\.io',
                    r'webflow\.com/design/'
                ],
                'meta_patterns': [
                    r'<meta name="generator" content="Webflow',
                    r'<link[^>]*webflow',
                    r'<script[^>]*webflow'
                ],
                'response_headers': ['x-webflow-version'],
                'url_patterns': ['/design/', '/cms/']
            },
            'Moodle': {
                'html_patterns': [
                    r'moodle',
                    r'/theme/',
                    r'/mod/',
                    r'/blocks/',
                    r'/lib/'
                ],
                'meta_patterns': [
                    r'<meta name="generator" content="Moodle',
                    r'<link[^>]*theme/',
                    r'<script[^>]*mod/'
                ],
                'response_headers': ['x-moodle-version'],
                'url_patterns': ['/course/', '/mod/', '/user/']
            }
        }
    
    def detect_cms(self, url: str) -> Dict[str, any]:
        """
        Detect website's CMS/platform
        
        Args:
            url: Website URL to detect
            
        Returns:
            Dict containing detection results and recommended template
        """
        try:
            # Use URL validation from wus_utilites_lib
            if self.search365_lib:
                status_code = self.search365_lib.check_url_code(url)
            else:
                # If Search365Lib is not available, use requests directly
                response = requests.get(url, timeout=10)
                status_code = response.status_code
            if status_code != 200:
                return {
                    'success': False,
                    'error': f'URL returned status code: {status_code}',
                    'detected_cms': None,
                    'confidence': 0,
                    'recommended_template': None
                }
            
            # Get website content
            response = requests.get(url, timeout=10)
            html_content = response.text
            headers = dict(response.headers)
            
            # Detect CMS
            detection_results = self._analyze_content(html_content, headers, url)
            
            # Select best match
            best_match = self._select_best_match(detection_results)
            
            # Get recommended template
            recommended_template = self._get_recommended_template(best_match['cms'])
            
            return {
                'success': True,
                'detected_cms': best_match['cms'],
                'confidence': best_match['confidence'],
                'evidence': best_match['evidence'],
                'recommended_template': recommended_template,
                'domain': self.search365_lib.data_source_extractor(url) if self.search365_lib else urlparse(url).netloc.replace('www.', '')
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'detected_cms': None,
                'confidence': 0,
                'recommended_template': None
            }
    
    def _analyze_content(self, html_content: str, headers: Dict, url: str) -> List[Dict]:
        """Analyze website content and detect CMS features"""
        results = []
        
        for cms_name, patterns in self.cms_patterns.items():
            confidence = 0
            evidence = []
            
            # Check HTML patterns
            for pattern in patterns.get('html_patterns', []):
                if re.search(pattern, html_content, re.IGNORECASE):
                    confidence += 20
                    evidence.append(f"Found HTML pattern: {pattern}")
            
            # Check Meta tags
            for pattern in patterns.get('meta_patterns', []):
                if re.search(pattern, html_content, re.IGNORECASE):
                    confidence += 25
                    evidence.append(f"Found Meta tag: {pattern}")
            
            # Check response headers
            for header_pattern in patterns.get('response_headers', []):
                for header_name, header_value in headers.items():
                    if re.search(header_pattern, f"{header_name}: {header_value}", re.IGNORECASE):
                        confidence += 30
                        evidence.append(f"Found response header: {header_name}: {header_value}")
            
            # Check URL patterns
            for url_pattern in patterns.get('url_patterns', []):
                if url_pattern in url:
                    confidence += 15
                    evidence.append(f"Found URL pattern: {url_pattern}")
            
            if confidence > 0:
                results.append({
                    'cms': cms_name,
                    'confidence': min(confidence, 100),
                    'evidence': evidence
                })
        
        return results
    
    def _select_best_match(self, results: List[Dict]) -> Dict:
        """Select the best matching CMS"""
        if not results:
            return {
                'cms': 'Unknown',
                'confidence': 0,
                'evidence': ['No known CMS features detected']
            }
        
        # Sort by confidence
        best_match = max(results, key=lambda x: x['confidence'])
        
        # If confidence is too low, return Unknown
        if best_match['confidence'] < 30:
            return {
                'cms': 'Unknown',
                'confidence': best_match['confidence'],
                'evidence': best_match['evidence'] + ['Confidence too low']
            }
        
        return best_match
    
    def _get_recommended_template(self, cms: str) -> Optional[Dict]:
        """Get recommended template based on detected CMS"""
        template_mapping = {
            'WordPress': {
                'id': 'wordpress',
                'name': 'WordPress',
                'description': 'Crawler configuration optimized for WordPress websites',
                'platform': 'WordPress',
                'maxDepth': 3,
                'maxDocuments': 500,
                'numThreads': 4,
                'delay': 2000,
                'stayOnDomain': True,
                'includeSubdomains': True,
                'fileExclusions': ['*.pdf', '*.doc', '*.docx', '*.zip', '*.rar'],
                'urlPatterns': ['/wp-content/', '/wp-includes/', '/wp-admin/']
            },
            'Drupal': {
                'id': 'drupal',
                'name': 'Drupal',
                'description': 'Crawler configuration optimized for Drupal websites',
                'platform': 'Drupal',
                'maxDepth': 3,
                'maxDocuments': 500,
                'numThreads': 4,
                'delay': 2500,
                'stayOnDomain': True,
                'includeSubdomains': True,
                'fileExclusions': ['*.pdf', '*.doc', '*.docx', '*.zip', '*.rar'],
                'urlPatterns': ['/sites/default/', '/modules/', '/themes/']
            },
            'Joomla': {
                'id': 'joomla',
                'name': 'Joomla',
                'description': 'Crawler configuration optimized for Joomla websites',
                'platform': 'Joomla',
                'maxDepth': 3,
                'maxDocuments': 500,
                'numThreads': 4,
                'delay': 2000,
                'stayOnDomain': True,
                'includeSubdomains': True,
                'fileExclusions': ['*.pdf', '*.doc', '*.docx', '*.zip', '*.rar'],
                'urlPatterns': ['/media/', '/templates/', '/administrator/']
            },
            'Shopify': {
                'id': 'shopify',
                'name': 'Shopify',
                'description': 'Crawler configuration optimized for Shopify e-commerce websites',
                'platform': 'Shopify',
                'maxDepth': 3,
                'maxDocuments': 500,
                'numThreads': 4,
                'delay': 3000,
                'stayOnDomain': True,
                'includeSubdomains': True,
                'fileExclusions': ['*.pdf', '*.doc', '*.docx', '*.zip', '*.rar'],
                'urlPatterns': ['/collections/', '/products/', '/cart/']
            },
            'Magento': {
                'id': 'magento',
                'name': 'Magento',
                'description': 'Crawler configuration optimized for Magento e-commerce websites',
                'platform': 'Magento',
                'maxDepth': 3,
                'maxDocuments': 500,
                'numThreads': 4,
                'delay': 2500,
                'stayOnDomain': True,
                'includeSubdomains': True,
                'fileExclusions': ['*.pdf', '*.doc', '*.docx', '*.zip', '*.rar'],
                'urlPatterns': ['/catalog/', '/customer/', '/checkout/']
            },
            'Wix': {
                'id': 'wix',
                'name': 'Wix',
                'description': 'Crawler configuration optimized for Wix websites',
                'platform': 'Wix',
                'maxDepth': 3,
                'maxDocuments': 500,
                'numThreads': 4,
                'delay': 2000,
                'stayOnDomain': True,
                'includeSubdomains': True,
                'fileExclusions': ['*.pdf', '*.doc', '*.docx', '*.zip', '*.rar'],
                'urlPatterns': ['/_partials/', '/_api/']
            },
            'Squarespace': {
                'id': 'squarespace',
                'name': 'Squarespace',
                'description': 'Crawler configuration optimized for Squarespace websites',
                'platform': 'Squarespace',
                'maxDepth': 3,
                'maxDocuments': 500,
                'numThreads': 4,
                'delay': 2000,
                'stayOnDomain': True,
                'includeSubdomains': True,
                'fileExclusions': ['*.pdf', '*.doc', '*.docx', '*.zip', '*.rar'],
                'urlPatterns': ['/s/', '/config/']
            },
            'Ghost': {
                'id': 'ghost',
                'name': 'Ghost',
                'description': 'Crawler configuration optimized for Ghost blog platform',
                'platform': 'Ghost',
                'maxDepth': 3,
                'maxDocuments': 500,
                'numThreads': 4,
                'delay': 2000,
                'stayOnDomain': True,
                'includeSubdomains': True,
                'fileExclusions': ['*.pdf', '*.doc', '*.docx', '*.zip', '*.rar'],
                'urlPatterns': ['/ghost/', '/tag/', '/author/']
            },
            'Webflow': {
                'id': 'webflow',
                'name': 'Webflow',
                'description': 'Crawler configuration optimized for Webflow websites',
                'platform': 'Webflow',
                'maxDepth': 3,
                'maxDocuments': 500,
                'numThreads': 4,
                'delay': 2000,
                'stayOnDomain': True,
                'includeSubdomains': True,
                'fileExclusions': ['*.pdf', '*.doc', '*.docx', '*.zip', '*.rar'],
                'urlPatterns': ['/design/', '/cms/']
            },
            'Moodle': {
                'id': 'moodle',
                'name': 'Moodle',
                'description': 'Crawler configuration optimized for Moodle learning management system',
                'platform': 'Moodle',
                'maxDepth': 3,
                'maxDocuments': 500,
                'numThreads': 4,
                'delay': 2500,
                'stayOnDomain': True,
                'includeSubdomains': True,
                'fileExclusions': ['*.pdf', '*.doc', '*.docx', '*.zip', '*.rar'],
                'urlPatterns': ['/course/', '/mod/', '/user/']
            }
        }
        
        return template_mapping.get(cms)
    
    def get_tech_stack_analysis(self, url: str) -> Dict[str, any]:
        """
        Get website tech stack analysis (utilizing Search365Lib's entity extraction functionality)
        
        Args:
            url: Website URL to analyze
            
        Returns:
            Tech stack analysis results
        """
        try:
            # Get website content
            response = requests.get(url, timeout=10)
            html_content = response.text
            
            # Use Search365Lib's entity extraction functionality (if available)
            entity_info = []
            if self.search365_lib:
                try:
                    # Here we simulate a document object to use extract_entity_info
                    mock_doc = {
                        'content': html_content,
                        'title': f'Analysis of {url}',
                        'url': url
                    }
                    
                    # Extract entity information
                    entity_info = self.search365_lib.extract_entity_info(mock_doc)
                except:
                    entity_info = []
            
            # Analyze tech stack
            tech_analysis = {
                'javascript_frameworks': self._detect_js_frameworks(html_content),
                'css_frameworks': self._detect_css_frameworks(html_content),
                'analytics_tools': self._detect_analytics(html_content),
                'cms_indicators': self._detect_cms_indicators(html_content),
                'server_technologies': self._detect_server_tech(response.headers),
                'entities': entity_info
            }
            
            return {
                'success': True,
                'tech_stack': tech_analysis,
                'domain': self.search365_lib.data_source_extractor(url) if self.search365_lib else urlparse(url).netloc.replace('www.', '')
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'tech_stack': None
            }
    
    def _detect_js_frameworks(self, html_content: str) -> List[str]:
        """Detect JavaScript frameworks"""
        frameworks = []
        js_patterns = {
            'React': [r'react', r'react-dom', r'jsx'],
            'Vue': [r'vue\.js', r'vuejs', r'v-if'],
            'Angular': [r'angular', r'ng-', r'@angular'],
            'jQuery': [r'jquery', r'\$\(', r'jQuery'],
            'Bootstrap': [r'bootstrap', r'bs-', r'data-bs-']
        }
        
        for framework, patterns in js_patterns.items():
            for pattern in patterns:
                if re.search(pattern, html_content, re.IGNORECASE):
                    frameworks.append(framework)
                    break
        
        return list(set(frameworks))
    
    def _detect_css_frameworks(self, html_content: str) -> List[str]:
        """Detect CSS frameworks"""
        frameworks = []
        css_patterns = {
            'Bootstrap': [r'bootstrap', r'bs-', r'col-', r'container'],
            'Tailwind': [r'tailwind', r'tw-', r'space-', r'flex'],
            'Foundation': [r'foundation', r'row', r'column'],
            'Bulma': [r'bulma', r'is-', r'has-']
        }
        
        for framework, patterns in css_patterns.items():
            for pattern in patterns:
                if re.search(pattern, html_content, re.IGNORECASE):
                    frameworks.append(framework)
                    break
        
        return list(set(frameworks))
    
    def _detect_analytics(self, html_content: str) -> List[str]:
        """Detect analytics tools"""
        analytics = []
        analytics_patterns = {
            'Google Analytics': [r'google-analytics', r'gtag', r'ga\(', r'googletagmanager'],
            'Google Tag Manager': [r'googletagmanager', r'gtm', r'dataLayer'],
            'Facebook Pixel': [r'facebook', r'fbq', r'pixel'],
            'Hotjar': [r'hotjar', r'hj\('],
            'Mixpanel': [r'mixpanel', r'mixpanel\.track']
        }
        
        for tool, patterns in analytics_patterns.items():
            for pattern in patterns:
                if re.search(pattern, html_content, re.IGNORECASE):
                    analytics.append(tool)
                    break
        
        return list(set(analytics))
    
    def _detect_cms_indicators(self, html_content: str) -> List[str]:
        """Detect CMS indicators"""
        indicators = []
        cms_patterns = {
            'WordPress': [r'wp-content', r'wp-includes', r'wordpress'],
            'Drupal': [r'drupal', r'sites/default', r'/modules/'],
            'Joomla': [r'joomla', r'/media/', r'/templates/'],
            'Shopify': [r'shopify', r'shopifycdn', r'cdn\.shopify'],
            'Magento': [r'magento', r'/media/', r'/skin/']
        }
        
        for cms, patterns in cms_patterns.items():
            for pattern in patterns:
                if re.search(pattern, html_content, re.IGNORECASE):
                    indicators.append(cms)
                    break
        
        return list(set(indicators))
    
    def _detect_server_tech(self, headers: Dict) -> List[str]:
        """Detect server technologies"""
        technologies = []
        
        server_headers = {
            'Apache': ['apache', 'httpd'],
            'Nginx': ['nginx'],
            'IIS': ['iis', 'microsoft-iis'],
            'Cloudflare': ['cloudflare'],
            'AWS': ['amazon', 'aws'],
            'Google Cloud': ['google', 'gcp']
        }
        
        for tech, patterns in server_headers.items():
            for header_name, header_value in headers.items():
                for pattern in patterns:
                    if re.search(pattern, f"{header_name}: {header_value}", re.IGNORECASE):
                        technologies.append(tech)
                        break
        
        return list(set(technologies))
