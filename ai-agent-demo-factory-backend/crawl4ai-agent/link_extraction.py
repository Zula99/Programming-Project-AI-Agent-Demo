# link_extraction.py - Extract links from HTML content
import re
from typing import Set

try:
    from bs4 import BeautifulSoup
    HAVE_BS4 = True
except Exception:
    HAVE_BS4 = False

from url_utils import to_abs

def extract_links(html: str, base_url: str) -> Set[str]:
    """Extract all links from HTML content"""
    links: Set[str] = set()
    if not html:
        return links

    if HAVE_BS4:
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            u = to_abs(base_url, a["href"])
            if u:
                links.add(u)
        return links

    # fallback regex
    for m in re.finditer(r'href=["\']([^"\']+)["\']', html, flags=re.I):
        u = to_abs(base_url, m.group(1))
        if u:
            links.add(u)
    return links
