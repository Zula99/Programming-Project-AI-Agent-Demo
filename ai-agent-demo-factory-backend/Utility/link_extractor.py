import argparse
from http.client import responses
import sys
from typing import List, Dict, Tuple, Optional, Any

# import pandas as pd
# from usp.tree import sitemap_tree_for_homepage
from bs4 import BeautifulSoup
import requests
import urllib3
import os
from pathlib import Path
from fake_useragent import UserAgent
from urllib.parse import urljoin, urlparse
import urllib.robotparser

# Try to import AI classifier - graceful fallback if not available
try:
    # Add the crawl4ai-agent directory to path for imports
    crawl4ai_path = Path(__file__).parent.parent / "crawl4ai-agent"
    if crawl4ai_path.exists() and str(crawl4ai_path) not in sys.path:
        sys.path.insert(0, str(crawl4ai_path))
    
    from ai_content_classifier import BusinessSiteDetector, AIContentClassifier
    AI_AVAILABLE = True
except ImportError as e:
    print(f"AI classification not available: {e}")
    AI_AVAILABLE = False

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class LinkExtractor:
    def __init__(self, sitemap_url, file_name, output_file, file_path, use_ai: bool = True):
        self.sitemap_url = sitemap_url
        self.file_name = file_name
        self.file_path = file_path
        self.output_file = output_file
        self.directory_path = Path(file_path)
        self.ua = UserAgent()
        self.use_ai = use_ai and AI_AVAILABLE
        
        # Initialize AI classifier if available and requested
        if self.use_ai:
            try:
                # Initialize both the site detector and the full AI classifier
                self.site_detector = BusinessSiteDetector()
                
                # Get AI configuration and initialize classifier with API key
                from ai_config import get_ai_config
                ai_config = get_ai_config()
                
                self.ai_classifier = AIContentClassifier(
                    api_key=ai_config.openai_api_key,
                    model=ai_config.preferred_model
                )
                print("AI classification enabled for intelligent URL filtering")
            except Exception as e:
                print(f"Failed to initialize AI classifier: {e}")
                self.use_ai = False
        
        # Domain extraction for boundary enforcement
        self.base_domain = self._extract_domain(sitemap_url)
        
        # Robots.txt intelligence storage
        self.robots_intel: Dict[str, Any] = {}

        self.session = requests.Session()

        self.session.headers.update({
            'User-Agent': UserAgent().random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'cross-site',
        })



    def check_directory_exists(self, directory_path):
        try:
            print(self.file_path)
            directory_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"Error creating directory {directory_path}: {e}")
            raise



    def filter_english_urls(self):
        """
        Reads URLs from an input file, filters for English URLs (containing '/en/'),
        and writes them to a new output file.

        This function is efficient for large files as it reads and processes
        line by line.

        Args:
            input_file_path (str): The path to the source file with all URLs.
            output_file_path (str): The path for the new file to save English URLs.
        """
        english_urls_found = 0
        try:
            # Ensure the output directory exists
            # output_dir = os.path.dirname(output_file_path)
            # if output_dir:
            #     os.makedirs(output_dir, exist_ok=True)
            self.check_directory_exists(self.directory_path)

            full_input_file_path = self.directory_path / self.file_name
            full_output_file_path = self.directory_path / self.output_file
            print(f"Reading from: {full_input_file_path}")
            print(f"Writing English URLs to: {full_output_file_path}")

            # Open both files at once to read and write efficiently
            with open(full_input_file_path, 'r', encoding='utf-8') as f_in, \
                    open(full_output_file_path, 'w', encoding='utf-8') as f_out:

                for line in f_in:
                    # Check if the line contains the English language code '/en/'
                    if '/en/' in line or '/en-us/' in line or '/en-gb/' in line or '/en-ca/' in line or '/en-au/' in line or '/en-nz/' in line or '/en-in/' in line or '/en-za/' in line or '/en-ph/' in line or '/en-sg/' in line:
                        # Write the line directly to the new file
                        # The 'line' variable already includes the newline character
                        f_out.write(line)
                        english_urls_found += 1

            print(f"\nFiltering complete.")
            print(f"Found and saved {english_urls_found} English URLs.")

        except FileNotFoundError:
            print(f"Error: The input file was not found at '{full_input_file_path}'")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def process_sitemap(self):
        self.check_directory_exists(self.directory_path)
        full_file_path = self.directory_path / self.file_name
        print(f"Processing sitemap index from: {self.sitemap_url}")
        print(f"Using headers: {self.session.headers}")
        try:
            # Stage 1: Fetch the main sitemap (which might be an index)
            response = self.session.get(self.sitemap_url, verify=False)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "lxml-xml")

            # Find all sitemap locations from the index file.
            sitemap_urls = [loc.text for loc in soup.find_all("loc")]

            # If no <loc> tags are found, it might be a direct sitemap, not an index.
            if not sitemap_urls:
                print("No sitemap index found, treating as a direct sitemap.")
                sitemap_urls = [self.sitemap_url]

            print(f"Found {len(sitemap_urls)} sitemaps to process.")

            # Open the output file once to write all links.
            with open(full_file_path, "w") as file:
                # Stage 2: Process each individual sitemap URL found.
                for url in sitemap_urls:
                    print(f"  -> Processing sitemap: {url}")
                    try:
                        sitemap_response = self.session.get(url, verify=False)
                        sitemap_response.raise_for_status()

                        sitemap_soup = BeautifulSoup(sitemap_response.content, "lxml-xml")
                        page_locs = sitemap_soup.find_all("loc")

                        for loc in page_locs:
                            file.write(loc.text + "\n")
                        print(f"     ...found and wrote {len(page_locs)} links.")
                    except requests.exceptions.RequestException as e:
                        print(f"     ...failed to process sitemap {url}: {e}")

        except requests.exceptions.RequestException as e:
            print(f"Failed to fetch the main sitemap index: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def _extract_domain(self, url: str) -> str:
        """Extract base domain for boundary enforcement"""
        try:
            parsed = urlparse(url)
            return f"{parsed.scheme}://{parsed.netloc}"
        except Exception:
            return ""

    def analyze_robots_txt(self, domain: str) -> Dict[str, Any]:
        """
        Analyze robots.txt for intelligence gathering (ignoring restrictions for demos)
        
        Returns strategic information about the site rather than restrictions
        """
        if domain in self.robots_intel:
            return self.robots_intel[domain]
            
        robots_url = urljoin(domain, '/robots.txt')
        intelligence = {
            'found': False,
            'sitemaps': [],
            'suggested_delay': 0.6,  # Default respectful delay
            'hidden_sections': [],
            'complexity_estimate': 'unknown'
        }
        
        try:
            response = self.session.get(robots_url, timeout=10)
            response.raise_for_status()
            
            robots_content = response.text
            intelligence['found'] = True
            
            # Extract sitemap URLs
            for line in robots_content.split('\n'):
                line = line.strip()
                if line.lower().startswith('sitemap:'):
                    sitemap_url = line.split(':', 1)[1].strip()
                    intelligence['sitemaps'].append(sitemap_url)
                elif line.lower().startswith('crawl-delay:'):
                    try:
                        delay = float(line.split(':', 1)[1].strip())
                        intelligence['suggested_delay'] = min(delay, 2.0)  # Cap at 2 seconds
                    except ValueError:
                        pass
            
            # Look for interesting disallowed paths (for intelligence, not restriction)
            disallowed_paths = []
            for line in robots_content.split('\n'):
                line = line.strip()
                if line.lower().startswith('disallow:'):
                    path = line.split(':', 1)[1].strip()
                    if path != '/':  # Ignore blanket disallow
                        disallowed_paths.append(path)
            
            # Identify potentially valuable business content in "forbidden" areas
            business_keywords = ['product', 'service', 'about', 'contact', 'business', 'solutions', 'support']
            for path in disallowed_paths:
                if any(keyword in path.lower() for keyword in business_keywords):
                    intelligence['hidden_sections'].append(path)
            
            # Estimate site complexity based on robots.txt patterns
            if len(disallowed_paths) > 20:
                intelligence['complexity_estimate'] = 'complex'
            elif len(disallowed_paths) > 5:
                intelligence['complexity_estimate'] = 'medium'
            else:
                intelligence['complexity_estimate'] = 'simple'
                
            print(f"Robots.txt intelligence gathered: {len(intelligence['sitemaps'])} sitemaps, "
                  f"{len(intelligence['hidden_sections'])} interesting sections, "
                  f"complexity: {intelligence['complexity_estimate']}")
                  
        except Exception as e:
            print(f"Could not analyze robots.txt for {domain}: {e}")
        
        self.robots_intel[domain] = intelligence
        return intelligence

    async def intelligent_url_filtering(self, urls: List[str], sample_content: bool = False) -> List[Tuple[str, float, str]]:
        """
        Apply AI classification to prioritize URLs based on demo worthiness
        
        Args:
            urls: List of URLs to filter
            sample_content: If True, fetch small content samples for better classification
            
        Returns:
            List of tuples (url, confidence_score, reasoning)
        """
        if not self.use_ai:
            # Fallback to existing behavior - return all URLs with neutral score
            return [(url, 0.5, "AI not available - using all URLs") for url in urls]
        
        prioritized_urls = []
        print(f"\n{'='*60}")
        print(f" STARTING AI CLASSIFICATION OF SITEMAP URLS")
        print(f"{'='*60}")
        print(f"Applying AI classification to {len(urls)} URLs...")
        
        # Initialize cost tracking for this sitemap analysis
        from pathlib import Path
        import sys
        sys.path.append(str(Path(__file__).parent.parent / 'crawl4ai-agent'))
        from cost_tracker import CostTracker
        
        domain = urlparse(urls[0] if urls else 'unknown.com').netloc
        cost_tracker = CostTracker(domain.replace('www.', ''), output_dir=str(Path(self.file_path) / 'cost_logs'))
        
        for i, url in enumerate(urls):
            if i % 50 == 0 and i > 0:
                print(f"  Processed {i}/{len(urls)} URLs...")
                
            try:
                # Extract basic information from URL
                url_path = urlparse(url).path
                
                # Sample content if requested (for better classification)
                title = ""
                content_sample = ""
                
                if sample_content:  # Sample all URLs when AI classification is enabled
                    try:
                        response = self.session.get(url, timeout=5)
                        if response.status_code == 200:
                            soup = BeautifulSoup(response.content, 'html.parser')
                            title_tag = soup.find('title')
                            title = title_tag.get_text().strip() if title_tag else ""
                            
                            # Get first paragraph or content snippet
                            content_tags = soup.find_all(['p', 'div', 'article', 'main'])[:3]
                            content_sample = ' '.join([tag.get_text().strip()[:100] for tag in content_tags])
                    except Exception:
                        pass  # Use URL-only classification
                
                # Use full AI classifier to assess demo worthiness
                try:
                    # Use the comprehensive AIContentClassifier (async)
                    result = await self.ai_classifier.classify_content(url, content_sample, title)
                    confidence = result.confidence
                    reasoning = result.reasoning
                    
                    # Convert boolean to confidence score for sorting
                    if not result.is_worthy:
                        confidence = confidence * 0.5  # Reduce confidence for unworthy content
                    
                    # Track cost and show verbose output
                    content_length = len(content_sample + title)
                    cost_tracker.track_classification(url, result, content_length)
                    
                    # Verbose output for each URL with separator
                    status = "WORTHY" if result.is_worthy else "FILTERED"
                    method_indicator = "AI" if result.method_used == "ai" else result.method_used.upper()
                    
                    print(f"\n  [{i+1:4d}/{len(urls)}] {status} ({confidence:.2f}) - {url[:70]}...")
                    print(f"        {method_indicator}: {reasoning[:120]}...")
                        
                except Exception as ai_error:
                    print(f"\n  [{i+1:4d}/{len(urls)}] AI FAILED - {url[:70]}...")
                    print(f"        Error: {ai_error}")
                    # Fallback to simple URL pattern analysis
                    confidence = self._simple_url_scoring(url)
                    reasoning = "Simple URL pattern analysis (AI failed)"
                    print(f"        Fallback: Heuristic score {confidence:.2f}")
                
                prioritized_urls.append((url, confidence, reasoning))
                
            except Exception as e:
                print(f"Error classifying URL {url}: {e}")
                prioritized_urls.append((url, 0.3, f"Classification error: {str(e)[:50]}"))
        
        # Sort by confidence score (highest first)
        prioritized_urls.sort(key=lambda x: x[1], reverse=True)
        
        print(f"\n{'='*50}")
        print(f" URL CLASSIFICATION RESULTS")
        print(f"{'='*50}")
        print(f"URL classification complete. Top 10 URLs by confidence:")
        for i, (url, confidence, reasoning) in enumerate(prioritized_urls[:10]):
            print(f"  {i+1}. {confidence:.2f} - {url[:60]}... ({reasoning[:50]}...)")
        
        # Show detailed cost summary
        cost_tracker.print_session_summary(compact=False)
        cost_tracker.save_final_session()
        
        return prioritized_urls

    def _simple_url_scoring(self, url: str) -> float:
        """Simple URL pattern scoring as fallback when AI is not available"""
        url_lower = url.lower()
        
        # High-value business content patterns
        high_value = ['product', 'service', 'business', 'solution', 'about', 'contact', 'support']
        medium_value = ['news', 'blog', 'resource', 'help', 'guide']
        low_value = ['legal', 'privacy', 'terms', 'cookie', 'sitemap', 'robots']
        
        score = 0.5  # Base score
        
        for pattern in high_value:
            if pattern in url_lower:
                score += 0.3
                
        for pattern in medium_value:
            if pattern in url_lower:
                score += 0.1
                
        for pattern in low_value:
            if pattern in url_lower:
                score -= 0.2
        
        # Prefer shorter, cleaner URLs
        if len(url) < 100:
            score += 0.1
        elif len(url) > 200:
            score -= 0.1
        
        return max(0.0, min(1.0, score))

    async def process_sitemap_with_ai(self, max_urls: Optional[int] = None, sample_content: bool = False) -> Tuple[List[str], Dict[str, Any]]:
        """
        Enhanced sitemap processing with AI classification and robots.txt intelligence
        
        Args:
            max_urls: Maximum URLs to return (None for all)
            sample_content: Whether to sample page content for better classification
            
        Returns:
            Tuple of (prioritized_urls, processing_stats)
        """
        # First gather robots.txt intelligence
        robots_info = self.analyze_robots_txt(self.base_domain)
        
        # Use discovered sitemaps if available, otherwise use provided URL
        sitemap_urls_to_process = robots_info.get('sitemaps', [])
        if not sitemap_urls_to_process:
            sitemap_urls_to_process = [self.sitemap_url]
        
        all_urls = []
        processing_stats = {
            'total_sitemaps_processed': 0,
            'total_urls_discovered': 0,
            'ai_classification_enabled': self.use_ai,
            'robots_intelligence': robots_info,
            'processing_time': 0
        }
        
        import time
        start_time = time.time()
        
        print(f"Processing {len(sitemap_urls_to_process)} sitemaps with AI enhancement...")
        
        # Extract all URLs from sitemaps
        for sitemap_url in sitemap_urls_to_process:
            try:
                print(f"  -> Processing sitemap: {sitemap_url}")
                response = self.session.get(sitemap_url, verify=False)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, "lxml-xml")
                
                # Handle sitemap index vs direct sitemap
                sitemap_refs = soup.find_all("loc")
                
                if soup.find("sitemapindex"):
                    # This is a sitemap index - process each referenced sitemap
                    for loc in sitemap_refs:
                        try:
                            sub_sitemap_response = self.session.get(loc.text, verify=False)
                            sub_sitemap_response.raise_for_status()
                            sub_soup = BeautifulSoup(sub_sitemap_response.content, "lxml-xml")
                            sub_urls = [sub_loc.text for sub_loc in sub_soup.find_all("loc")]
                            all_urls.extend(sub_urls)
                            print(f"     ...extracted {len(sub_urls)} URLs from {loc.text}")
                        except Exception as e:
                            print(f"     ...failed to process sub-sitemap {loc.text}: {e}")
                else:
                    # Direct sitemap with URLs
                    urls = [loc.text for loc in sitemap_refs]
                    
                    # TEMPORARY TEST LIMIT: Only take first 10 URLs to prevent massive AI costs
                    if max_urls and len(all_urls) + len(urls) > max_urls:
                        remaining_quota = max_urls - len(all_urls)
                        urls = urls[:remaining_quota] if remaining_quota > 0 else []
                        print(f"     ...extracted {len(urls)} URLs (LIMITED by max_urls={max_urls})")
                    else:
                        print(f"     ...extracted {len(urls)} URLs")
                    
                    all_urls.extend(urls)
                
                processing_stats['total_sitemaps_processed'] += 1
                
            except Exception as e:
                print(f"  -> Failed to process sitemap {sitemap_url}: {e}")
        
        processing_stats['total_urls_discovered'] = len(all_urls)
        
        # Apply domain boundary filtering
        filtered_urls = [url for url in all_urls if self._is_same_domain(url, self.base_domain)]
        removed_external = len(all_urls) - len(filtered_urls)
        if removed_external > 0:
            print(f"Removed {removed_external} external domain URLs (domain boundary enforcement)")
        
        # Apply AI classification for prioritization
        if filtered_urls:
            prioritized_results = await self.intelligent_url_filtering(filtered_urls, sample_content)
            
            # Extract URLs and apply limit if specified
            final_urls = [url for url, confidence, reasoning in prioritized_results]
            if max_urls:
                final_urls = final_urls[:max_urls]
                print(f"Limited output to top {len(final_urls)} URLs by AI confidence")
            
            processing_stats['ai_classified_urls'] = len(prioritized_results)
            processing_stats['final_url_count'] = len(final_urls)
            processing_stats['average_confidence'] = sum(conf for _, conf, _ in prioritized_results) / len(prioritized_results)
        else:
            final_urls = []
            
        processing_stats['processing_time'] = time.time() - start_time
        
        print(f"\nSitemap processing complete:")
        print(f"  - Total URLs discovered: {processing_stats['total_urls_discovered']}")
        print(f"  - URLs after domain filtering: {len(filtered_urls)}")
        print(f"  - Final URLs returned: {len(final_urls)}")
        print(f"  - Processing time: {processing_stats['processing_time']:.2f}s")
        
        return final_urls, processing_stats

    def _is_same_domain(self, url: str, base_domain: str) -> bool:
        """Check if URL belongs to the same domain (for boundary enforcement)"""
        try:
            url_domain = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
            return url_domain == base_domain
        except Exception:
            return False


# def main():
#     print("Starting process")
#     parser = argparse.ArgumentParser(description="Process sitemaps.")
#     parser.add_argument("-u","--homepage_url", help="URL of the website homepage")
#     parser.add_argument("-f","--file_name", help="Output file name", default="site_links.txt")
#     parser.add_argument("-o","--file_path", help="Output file path", default="./" )
#     args = parser.parse_args()
#     process_sitemap(args.homepage_url, args.file_name, args.file_path)


# # Press the green button in the gutter to run the script.
# if __name__ == '__main__':
#     main()
