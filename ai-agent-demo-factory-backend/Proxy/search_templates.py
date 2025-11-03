#!/usr/bin/env python3
"""
Search Templates - Separate file for search result templates
Makes it easy to edit template designs without touching main proxy code
"""

def create_native_search_template(styling_dna: dict) -> str:
    """Create modern card-based search results template using site styling DNA"""

    # Extract styling variables
    brand_name = styling_dna.get("brand_name", "Search")
    primary_font = styling_dna.get("primary_font", "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif")
    text_color = styling_dna.get("text_color", "#2c3e50")
    background_color = styling_dna.get("background_color", "#ffffff")
    brand_color = styling_dna.get("brand_color", "#3498db")
    link_color = styling_dna.get("link_color", "#3498db")
    header_bg = styling_dna.get("header_bg", "#ffffff")
    header_border = styling_dna.get("header_border", "1px solid #e1e5e9")
    container_width = styling_dna.get("container_width", "1200px")
    content_padding = styling_dna.get("content_padding", "24px")
    header_padding = styling_dna.get("header_padding", "16px 24px")

    # Logo handling
    logo_url = styling_dna.get("logo_url", "")
    if logo_url:
        logo_html = f'<img src="{logo_url}" alt="{brand_name}" class="brand-logo">'
    else:
        logo_html = f'<div class="brand-logo-text">{brand_name[0]}</div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Search Results - {brand_name}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: {primary_font};
            color: {text_color};
            background-color: #f8fafc;
            line-height: 1.6;
            min-height: 100vh;
        }}

        /* Header Styles */
        .site-header {{
            background: {header_bg};
            border-bottom: {header_border};
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }}

        .header-content {{
            max-width: {container_width};
            margin: 0 auto;
            padding: {header_padding};
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}

        .brand-section {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .brand-logo {{
            height: 32px;
            width: auto;
        }}

        .brand-logo-text {{
            width: 40px;
            height: 40px;
            background: {brand_color};
            color: white;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            font-size: 18px;
        }}

        .brand-name {{
            font-size: 24px;
            font-weight: 700;
            color: {brand_color};
            text-decoration: none;
            transition: opacity 0.2s ease;
        }}

        .brand-name:hover {{
            opacity: 0.8;
        }}

        /* Main Container */
        .container {{
            max-width: {container_width};
            margin: 0 auto;
            padding: {content_padding};
        }}

        /* Search Header */
        .search-header {{
            background: {background_color};
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 32px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
            display: flex;
            align-items: center;
            gap: 20px;
            flex-wrap: wrap;
        }}

        .back-button {{
            background: {brand_color};
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .back-button:hover {{
            background: {brand_color}dd;
            transform: translateY(-1px);
        }}

        .search-info {{
            flex: 1;
            font-size: 18px;
            color: {text_color};
        }}

        .search-query {{
            font-weight: 600;
            color: {brand_color};
            background: {brand_color}15;
            padding: 4px 12px;
            border-radius: 6px;
            margin: 0 8px;
        }}

        .results-count {{
            color: #6b7280;
            font-size: 16px;
            margin-left: 8px;
        }}

        /* Results Grid */
        .results-grid {{
            display: grid;
            gap: 24px;
            grid-template-columns: 1fr;
        }}

        .result-item {{
            background: {background_color};
            border: 1px solid #e1e5e9;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
            transition: all 0.2s ease;
            position: relative;
            overflow: hidden;
        }}

        .result-item:hover {{
            box-shadow: 0 8px 24px rgba(0,0,0,0.1);
            transform: translateY(-2px);
            border-color: {brand_color}40;
        }}

        .result-header {{
            display: flex;
            align-items: flex-start;
            gap: 16px;
            margin-bottom: 16px;
        }}

        .result-icon {{
            width: 48px;
            height: 48px;
            background: {brand_color}15;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            font-size: 20px;
            color: {brand_color};
        }}

        .result-title-section {{
            flex: 1;
            min-width: 0;
        }}

        .result-title {{
            font-size: 20px;
            font-weight: 600;
            color: {link_color};
            text-decoration: none;
            line-height: 1.3;
            display: block;
            margin-bottom: 4px;
            transition: color 0.2s ease;
        }}

        .result-title:hover {{
            color: {brand_color};
            text-decoration: underline;
        }}

        .result-url {{
            font-size: 14px;
            color: #22c55e;
            word-break: break-all;
        }}

        .result-content {{
            margin-bottom: 16px;
        }}

        .result-snippet {{
            font-size: 16px;
            line-height: 1.6;
            color: {text_color}cc;
            margin-bottom: 12px;
        }}

        .result-meta {{
            display: flex;
            align-items: center;
            gap: 16px;
            flex-wrap: wrap;
            padding-top: 16px;
            border-top: 1px solid #f1f5f9;
        }}

        .meta-item {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 14px;
            color: #6b7280;
        }}

        .meta-badge {{
            background: {brand_color}15;
            color: {brand_color};
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 500;
        }}

        /* No Results */
        .no-results {{
            text-align: center;
            padding: 80px 20px;
            background: {background_color};
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }}

        .no-results h3 {{
            color: {brand_color};
            font-size: 24px;
            margin-bottom: 12px;
            font-weight: 600;
        }}

        .no-results p {{
            color: #6b7280;
            font-size: 16px;
            max-width: 400px;
            margin: 0 auto;
            line-height: 1.6;
        }}

        /* Responsive Design */
        @media (max-width: 768px) {{
            .header-content {{
                flex-direction: column;
                gap: 15px;
                text-align: center;
            }}

            .container {{
                padding: 16px;
            }}

            .search-header {{
                flex-direction: column;
                align-items: stretch;
                gap: 16px;
                padding: 20px;
            }}

            .search-info {{
                text-align: center;
                font-size: 16px;
            }}

            .results-grid {{
                gap: 16px;
            }}

            .result-item {{
                padding: 20px;
            }}

            .result-header {{
                gap: 12px;
            }}

            .result-icon {{
                width: 40px;
                height: 40px;
                font-size: 18px;
            }}

            .result-title {{
                font-size: 18px;
            }}

            .result-meta {{
                flex-direction: column;
                align-items: stretch;
                gap: 8px;
            }}

            .meta-item {{
                justify-content: center;
            }}
        }}

        @media (max-width: 480px) {{
            .search-query {{
                display: block;
                margin: 8px 0;
            }}

            .results-count {{
                display: block;
                margin-left: 0;
                margin-top: 4px;
            }}
        }}
    </style>
</head>
<body>
    <header class="site-header">
        <div class="header-content">
            <div class="brand-section">
                {logo_html}
                <a href="/proxy/" class="brand-name">{brand_name}</a>
            </div>
        </div>
    </header>

    <main class="container">
        <div class="search-header">
            <button class="back-button" onclick="goBack()">← Back</button>
            <div class="search-info">
                Search results for: <span class="search-query">{{{{SEARCH_QUERY}}}}</span>
                <span class="results-count">({{{{TOTAL_RESULTS}}}} found)</span>
            </div>
        </div>

        <div class="results-grid">
            {{{{SEARCH_RESULTS}}}}
        </div>
    </main>

    <script>
        function goBack() {{
            if (window.history.length > 1) {{
                window.history.back();
            }} else {{
                // Fallback to homepage if no history
                window.location.href = '/proxy/';
            }}
        }}
    </script>
</body>
</html>"""


def create_result_item_html(title: str, url: str, snippet: str, domain: str = "", page_type: str = "", brand_color: str = "#3498db") -> str:
    """Create modern HTML for a single search result item"""

    # Determine icon based on page type or content
    if "product" in page_type.lower() or "product" in title.lower():
        icon = "🛍️"
    elif "service" in page_type.lower() or "service" in title.lower():
        icon = "⚙️"
    elif "about" in page_type.lower() or "about" in title.lower():
        icon = "🏢"
    elif "contact" in page_type.lower() or "contact" in title.lower():
        icon = "📞"
    elif "news" in page_type.lower() or "blog" in page_type.lower():
        icon = "📰"
    else:
        icon = "📄"

    # Clean URL for display
    display_url = url.replace('http://', '').replace('https://', '').replace('/proxy/', '')
    if display_url.startswith('www.'):
        display_url = display_url[4:]

    return f"""
    <div class="result-item">
        <div class="result-header">
            <div class="result-icon">{icon}</div>
            <div class="result-title-section">
                <a href="{url}" class="result-title">{title}</a>
                <div class="result-url">{display_url}</div>
            </div>
        </div>
        <div class="result-content">
            <div class="result-snippet">{snippet}</div>
        </div>
        <div class="result-meta">
            <div class="meta-item">
                <span>{domain}</span>
            </div>
            {f'<div class="meta-badge">{page_type}</div>' if page_type else ''}
        </div>
    </div>
    """


def create_no_results_html(query: str) -> str:
    """Create modern HTML for no results found"""
    return f"""
    <div class="no-results">
        <h3>No results found</h3>
        <p>We couldn't find any results for "<strong>{query}</strong>". Try using different keywords or check your spelling.</p>
    </div>
    """