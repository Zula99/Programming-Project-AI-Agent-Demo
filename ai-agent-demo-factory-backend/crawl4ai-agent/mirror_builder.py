# mirror_builder.py - Generic static mirror builder for SmartMirrorAgent
import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import urllib.parse

# Import the existing static mirror builder
sys.path.append(str(Path(__file__).parent.parent.parent / "crawl4ai"))

class MirrorBuilder:
    """
    Generic wrapper for the static mirror builder that can be configured
    for any domain by the SmartMirrorAgent
    """
    
    def __init__(self):
        self.last_mirror_path: Optional[str] = None
        self.last_mirror_stats: Dict[str, Any] = {}
    
    async def build_static_mirror(self, 
                                crawl_data: Dict[str, Any],
                                concurrency: int = 8,
                                request_gap: float = 0.15,
                                mirror_external_assets: bool = True,
                                strip_scripts: bool = False,
                                rewrite_css_urls: bool = True) -> str:
        """
        Build a static mirror from crawled data
        
        Args:
            crawl_data: Data from the crawler containing output path and domain info
            concurrency: Number of parallel asset downloads
            request_gap: Delay between asset requests
            mirror_external_assets: Whether to mirror external assets
            strip_scripts: Whether to remove script tags
            rewrite_css_urls: Whether to rewrite CSS urls
            
        Returns:
            mirror_path: Path to the generated mirror root
        """
        try:
            # Extract info from crawl data
            output_path = crawl_data.get("output_path")
            domain = crawl_data.get("domain") 
            url = crawl_data.get("url", "")
            
            if not output_path or not domain:
                raise ValueError("Missing output_path or domain in crawl_data")
            
            output_root = Path(output_path)
            
            # Parse domain to get clean version
            parsed = urllib.parse.urlsplit(url)
            clean_domain = parsed.netloc.lower()
            if clean_domain.startswith("www."):
                clean_domain = clean_domain[4:]
            
            print(f"Building static mirror for {domain}")
            print(f"Source: {output_root}")
            
            # Import and use the new dynamic API
            from build_static_mirror import build_mirror_for_domain
            
            # Build the mirror using the clean API
            mirror_root = await build_mirror_for_domain(
                domain=clean_domain,
                output_root=output_root
            )
            
            # Store results
            self.last_mirror_path = str(mirror_root.resolve())
            self.last_mirror_stats = {
                "mirror_path": self.last_mirror_path,
                "domain": domain,
                "concurrency": concurrency,
                "request_gap": request_gap,
                "mirror_external_assets": mirror_external_assets,
                "strip_scripts": strip_scripts,
                "rewrite_css_urls": rewrite_css_urls,
                "success": True
            }
            
            print(f"✅ Static mirror built successfully at: {self.last_mirror_path}")
            return self.last_mirror_path
            
        except Exception as e:
            error_msg = f"Mirror building failed: {e}"
            print(f"⚠️ {error_msg}")
            
            self.last_mirror_stats = {
                "success": False,
                "error": str(e)
            }
            
            raise Exception(error_msg)
    
    def get_mirror_stats(self) -> Dict[str, Any]:
        """Get statistics from the last mirror build"""
        return self.last_mirror_stats.copy()
    
    def get_entry_point_suggestions(self, crawl_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Get suggested entry points for the mirror based on crawl data
        
        Returns:
            Dictionary of entry point names to file paths
        """
        if not self.last_mirror_path:
            return {}
        
        mirror_root = Path(self.last_mirror_path)
        domain = crawl_data.get("domain", "")
        
        suggestions = {}
        
        # Main entry point - root domain
        if domain:
            clean_domain = domain
            if clean_domain.startswith("www."):
                clean_domain = clean_domain[4:]
            
            # Try different possible entry points
            possible_entries = [
                mirror_root / f"www.{clean_domain}" / "index.html",
                mirror_root / clean_domain / "index.html",
                mirror_root / domain / "index.html"
            ]
            
            for entry in possible_entries:
                if entry.exists():
                    suggestions["homepage"] = str(entry)
                    break
        
        # Find other common entry points
        if mirror_root.exists():
            # Look for common pages
            common_pages = ["about", "contact", "products", "services", "help"]
            for page in common_pages:
                page_paths = list(mirror_root.rglob(f"*/{page}/index.html"))
                if page_paths:
                    suggestions[page] = str(page_paths[0])
        
        return suggestions

async def test_mirror_builder():
    """Test the mirror builder with sample crawl data"""
    # This would normally come from a real crawl
    test_crawl_data = {
        "url": "https://www.example.com/",
        "domain": "example.com",
        "output_path": "output/test_mirror",
        "successful": True
    }
    
    builder = MirrorBuilder()
    
    try:
        mirror_path = await builder.build_static_mirror(test_crawl_data)
        print(f"Test mirror built at: {mirror_path}")
        
        stats = builder.get_mirror_stats()
        print(f"Mirror stats: {stats}")
        
        entries = builder.get_entry_point_suggestions(test_crawl_data)
        print(f"Entry points: {entries}")
        
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_mirror_builder())