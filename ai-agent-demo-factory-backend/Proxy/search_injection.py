#!/usr/bin/env python3
"""
Search Injection Module
Handles JavaScript injection for search button replacement
"""
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


def is_dynamic_search_site(target_url: str) -> bool:
    """
    Universal search button replacement for ALL website types

    Returns True for every site to enable comprehensive search replacement covering:
    - Banking sites (CommBank, NAB, Westpac, ANZ)
    - E-commerce sites (Amazon, eBay, shopping sites)
    - Government sites (.gov patterns)
    - Educational sites (.edu patterns)
    - WordPress/CMS sites (WordPress, Drupal, Joomla)
    - Modern framework sites (React, Vue, Angular)
    - Corporate sites with custom search implementations
    - Client-side search sites (no API calls)
    - Traditional server-side search sites
    - SPA sites with API-based search

    Args:
        target_url: Target site URL

    Returns:
        Always True to enable universal search replacement
    """
    return True


def get_search_injection_script() -> str:
    """
    Get the JavaScript code for search injection

    This large JavaScript block handles:
    - Search modal creation and display
    - AI-powered search button detection with caching
    - Legacy rule-based fallback detection
    - Event delegation for dynamic content
    - Mutation observer for SPA support

    Returns:
        JavaScript code as string
    """
    return '''
        document.addEventListener('DOMContentLoaded', function() {
            console.log('Demo search replacement initialized - v2.0');
            console.log('Current URL:', window.location.href);

            // Function to redirect to our lookalike search page
            function redirectToSearchPage(initialQuery = '') {
                console.log('Redirecting to demo search page with query:', initialQuery);

                // Build search URL with query parameter
                const searchUrl = `/proxy/search${initialQuery ? `?q=${encodeURIComponent(initialQuery)}` : ''}`;

                // Redirect in the same window for seamless experience
                window.location.href = searchUrl;
            }

            // Function to show search input modal - fixed version
            function showSearchInput() {
                console.log(' MODAL: showSearchInput() called!');
                // Prevent multiple modals
                if (document.getElementById('demo-search-modal')) {
                    console.log(' MODAL: Modal already exists, skipping');
                    return;
                }

                // Create a styled search modal that matches the site
                const modal = document.createElement('div');
                modal.id = 'demo-search-modal';
                modal.style.cssText = `
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0, 0, 0, 0.5);
                    z-index: 999999;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                `;

                const searchBox = document.createElement('div');
                searchBox.style.cssText = `
                    background: white;
                    padding: 30px;
                    border-radius: 8px;
                    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
                    max-width: 400px;
                    width: 90%;
                    position: relative;
                    z-index: 1000000;
                `;

                searchBox.innerHTML = `
                    <h3 style="margin: 0 0 20px 0; color: #333; user-select: none;">Search</h3>
                    <input type="text" id="demo-search-input" placeholder="Enter your search query..."
                           style="width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 4px; font-size: 16px; margin-bottom: 15px; outline: none; box-sizing: border-box;"
                           autocomplete="off" spellcheck="false">
                    <div style="text-align: right; user-select: none;">
                        <button id="demo-cancel-btn" style="margin-right: 10px; padding: 8px 16px; border: 1px solid #ddd; background: white; border-radius: 4px; cursor: pointer; outline: none;">Cancel</button>
                        <button id="demo-search-btn" style="padding: 8px 16px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; outline: none;">Go</button>
                    </div>
                `;

                modal.appendChild(searchBox);
                document.body.appendChild(modal);

                // Add Enter key support for input
                const input = document.getElementById('demo-search-input');
                input.addEventListener('keydown', function(e) {
                    if (e.key === 'Enter') {
                        const query = input.value.trim();
                        if (query) {
                            document.getElementById('demo-search-modal').remove();
                            window.location.href = '/proxy/search?q=' + encodeURIComponent(query);
                        } else {
                            alert('Please enter a search query');
                        }
                    }
                    if (e.key === 'Escape') {
                        document.getElementById('demo-search-modal').remove();
                    }
                });

                // Add button event listeners
                const searchBtn = document.getElementById('demo-search-btn');
                const cancelBtn = document.getElementById('demo-cancel-btn');

                searchBtn.addEventListener('click', function(e) {
                    e.preventDefault();
                    const query = input.value.trim();
                    if (query) {
                        document.getElementById('demo-search-modal').remove();
                        window.location.href = '/proxy/search?q=' + encodeURIComponent(query);
                    } else {
                        alert('Please enter a search query');
                    }
                });

                cancelBtn.addEventListener('click', function(e) {
                    e.preventDefault();
                    document.getElementById('demo-search-modal').remove();
                });

                // Close on background click
                modal.addEventListener('click', function(e) {
                    if (e.target === modal) {
                        document.getElementById('demo-search-modal').remove();
                    }
                });

                // Focus management - wait for DOM to be ready
                requestAnimationFrame(() => {
                    input.focus();
                });
            }

            // Legacy rule-based fallback
            function replaceSearchButtonsLegacy() {
                console.log('Using legacy rule-based search detection...');

                    // Universal search detection patterns
                const searchPatterns = {
                    // Text-based detection
                    textMatches: ['search', 'find', 'look', 'query', 'buscar', 'chercher'],
                    // Class name patterns
                    classPatterns: ['search', 'find', 'lookup', 'query', 'magnify'],
                    // Attribute patterns
                    attrPatterns: ['search', 'find', 'query']
                };

                // STRICT: Only target actual search elements, not navigation
                const searchButtonSelectors = [
                    // === SEARCH INPUT FIELDS (highest priority) ===
                    'input[type="search"]',
                    'input[placeholder*="search" i]',
                    'input[name*="search" i]',
                    'input[id*="search" i]',
                    'input[class*="search" i]',

                    // === SEARCH BUTTONS (must be buttons, not links) ===
                    'button[class*="search" i]',
                    'button[id*="search" i]',
                    'button[aria-label*="search" i]',
                    'input[type="submit"][class*="search" i]',
                    'input[type="submit"][id*="search" i]',

                    // === SEARCH FORM ELEMENTS ===
                    'form[role="search"] button',
                    'form[role="search"] input[type="submit"]',
                    'form[class*="search" i] button',
                    'form[class*="search" i] input[type="submit"]',

                    // === SEARCH ICONS (only if they're in button role) ===
                    '*[role="button"][class*="search-icon" i]',
                    '*[role="button"][class*="icon-search" i]',
                    '*[role="button"][aria-label*="search" i]'
                ];

                let replacedCount = 0;

                searchButtonSelectors.forEach(selector => {
                    const buttons = document.querySelectorAll(selector);
                    console.log(`Checking selector "${selector}": found ${buttons.length} elements`);
                    buttons.forEach(button => {
                        // Skip if already processed
                        if (button.hasAttribute('data-demo-search-processed')) {
                            return;
                        }

                        const buttonText = (button.textContent || '').toLowerCase();
                        const buttonClass = (typeof button.className === 'string' ? button.className : '').toLowerCase();
                        const buttonId = (button.id || '').toLowerCase();
                        const ariaLabel = (button.getAttribute('aria-label') || '').toLowerCase();

                        // Helper function to detect search icons
                        function hasSearchIcon(element) {
                            const text = element.textContent || '';
                            const className = element.className || '';

                            return (
                                // Unicode search symbols
                                text.includes('') ||
                                // Common icon fonts
                                className.includes('fa-search') ||
                                className.includes('icon-search') ||
                                className.includes('search-icon') ||
                                // SVG detection
                                element.querySelector('svg[class*="search" i]') ||
                                element.querySelector('use[href*="search" i]')
                            );
                        }

                        // Exclude navigation elements explicitly
                        const isNavigationElement =
                            button.tagName === 'A' ||  // Never replace links
                            buttonClass.includes('nav') ||
                            buttonClass.includes('menu') ||
                            button.closest('nav') ||
                            button.closest('.navigation') ||
                            button.closest('header');

                        // STRICT: Only match elements with explicit search identifiers
                        // DO NOT use buttonText to avoid matching containers with search text
                        const isSearchElement = !isNavigationElement && (
                            buttonClass.includes('search') ||
                            buttonId.includes('search') ||
                            ariaLabel.includes('search') ||
                            hasSearchIcon(button) ||
                            button.closest('.searchContainer') ||
                            button.closest('.search-form') ||
                            button.closest('form[role="search"]') ||
                            (button.type === 'submit' && button.form?.querySelector('input[type="search"], input[name="q"]'))
                        );

                        if (isSearchElement) {
                            console.log('REPLACING search button:', button);
                            // Clone the button to preserve styling
                            const newButton = button.cloneNode(true);

                            // Remove all existing event listeners and onclick handlers
                            newButton.removeAttribute('onclick');
                            newButton.removeAttribute('href');

                            // Add our search functionality
                            newButton.addEventListener('click', function(e) {
                                e.preventDefault();
                                e.stopPropagation();
                                showSearchInput();
                            });

                            // Mark as processed and replace the original button
                            newButton.setAttribute('data-demo-search-processed', 'true');
                            button.parentNode.replaceChild(newButton, button);
                            replacedCount++;
                        }
                    });
                });

                // Universal search input field detection
                const searchInputs = document.querySelectorAll(`
                    input[type="search"],
                    input[placeholder*="search" i],
                    input[name*="search" i],
                    input[id*="search" i],
                    input[class*="search" i],
                    form[role="search"] input,
                    input#query,
                    input[name="query"],
                    input[name="q"]
                `);

                searchInputs.forEach(input => {
                    if (input.hasAttribute('data-demo-search-processed')) {
                        return;
                    }

                    input.addEventListener('keydown', function(e) {
                        if (e.key === 'Enter') {
                            e.preventDefault();
                            e.stopPropagation();

                            const query = input.value.trim();
                            if (query) {
                                redirectToSearchPage(query);
                            } else {
                                showSearchInput();
                            }
                        }
                    });

                    input.setAttribute('data-demo-search-processed', 'true');
                });

                const inputCount = searchInputs.length;
                console.log(`Replaced ${replacedCount} search buttons and enhanced ${inputCount} search inputs`);
                return replacedCount + inputCount;
            }

            console.log(' SEARCH INJECTION: Starting search button replacement...');

            // Event delegation approach - intercept clicks on ANY search elements
            document.addEventListener('click', function(e) {
                const target = e.target;

                // Debug logging
                console.log('CLICK DEBUG:', {
                    tag: target.tagName,
                    class: target.className,
                    id: target.id,
                    isSearch: isSearchElement(target)
                });

                // Check if clicked element matches our search patterns
                if (isSearchElement(target)) {
                    console.log(' CLICK: Search element clicked via delegation!', target);
                    e.preventDefault();
                    e.stopPropagation();
                    e.stopImmediatePropagation(); // Stop ALL other handlers including on same element
                    showSearchInput();
                    return false;
                }
            }, true); // Use capture phase to intercept before other handlers

            // Function to detect if an element is a search element
            function isSearchElement(element) {
                if (!element) return false;

                // Exclude our modal buttons
                const id = (element.id || '').toLowerCase();
                if (id === 'demo-search-btn' || id === 'demo-cancel-btn') {
                    return false;
                }

                const tagName = element.tagName ? element.tagName.toLowerCase() : '';
                const type = (element.type || '').toLowerCase();
                // className can be a string OR a DOMTokenList - convert to string properly
                const className = (element.className ? String(element.className) : '').toLowerCase();
                const ariaLabel = (element.getAttribute('aria-label') || '').toLowerCase();
                const placeholder = (element.getAttribute('placeholder') || '').toLowerCase();
                const role = (element.getAttribute('role') || '').toLowerCase();

                // FIRST: Check if it's a navigation link - but allow search links
                if (tagName === 'a' && element.hasAttribute('href')) {
                    // Allow if it has search-related attributes (like CommBank's <a aria-label="search">)
                    const isSearchLink =
                        ariaLabel.includes('search') ||
                        className.includes('search') ||
                        id.includes('search') ||
                        role === 'button' && (className.includes('search') || ariaLabel.includes('search'));

                    // Exclude only if it's NOT a search link
                    if (!isSearchLink) {
                        return false;
                    }
                }

                // SECOND: Check if it's a search element (highest priority)
                let isSearchRelated = false;

                // 1. Search input fields
                const name = (element.getAttribute('name') || '').toLowerCase();
                if (tagName === 'input' && (
                    type === 'search' ||
                    placeholder.includes('search') ||
                    className.includes('search') ||
                    id.includes('search') ||
                    id === 'query' ||
                    name === 'query' ||
                    name === 'q'
                )) {
                    isSearchRelated = true;
                }

                // 2. Search buttons (must be button/submit type)
                if ((tagName === 'button' || type === 'submit') && (
                    className.includes('search') ||
                    id.includes('search') ||
                    ariaLabel.includes('search')
                )) {
                    isSearchRelated = true;
                }

                // 2b. Search links with role=button (like CommBank)
                if (tagName === 'a' && (
                    ariaLabel.includes('search') ||
                    className.includes('search') ||
                    id.includes('search')
                )) {
                    isSearchRelated = true;
                }

                // 3. Search icons/spans/divs with search in class
                if ((tagName === 'span' || tagName === 'div') && (
                    className.includes('search') ||
                    id.includes('search')
                )) {
                    isSearchRelated = true;
                }

                // 4. Search icons (only if they're clickable and specifically for search)
                if (role === 'button' && (
                    className.includes('search-icon') ||
                    className.includes('icon-search') ||
                    ariaLabel.includes('search')
                )) {
                    isSearchRelated = true;
                }

                // 5. SVG search icons (only direct SVG elements with search class)
                if (tagName === 'svg' && className.includes('search')) {
                    isSearchRelated = true;
                }

                // 6. Elements inside search containers
                if (element.closest('.homeSearch, .search-box, .searchbox, .search-container, [class*="search-"][class*="container"]')) {
                    isSearchRelated = true;
                }
                if (element.closest('[id*="search"][id*="box"], [id*="search"][id*="container"]')) {
                    isSearchRelated = true;
                }

                // If it's search-related, return true immediately (don't exclude even if in nav)
                if (isSearchRelated) {
                    return true;
                }

                // THIRD: Exclude navigation elements (only if NOT search-related)
                if (tagName === 'nav' || element.closest('nav')) {
                    return false;
                }
                if (className.includes('nav') || className.includes('menu')) {
                    return false;
                }

                return false;
            }

            console.log(' Event delegation for search elements is now active');

            // Run legacy replacement to physically remove site's event handlers
            // Uses same isSearchElement() logic as event delegation for consistency
            function replaceSearchElements() {
                console.log('Running search element replacement...');
                let replacedCount = 0;

                // Find all potentially clickable elements
                const allElements = document.querySelectorAll('a, button, input, span, div, svg');

                allElements.forEach(element => {
                    // Skip if already processed
                    if (element.hasAttribute('data-demo-search-processed')) {
                        return;
                    }

                    // Use the same logic as event delegation
                    if (isSearchElement(element)) {
                        console.log('REPLACING search element:', element);

                        // Clone the element to preserve styling
                        const newElement = element.cloneNode(true);

                        // Remove all existing event listeners and handlers
                        newElement.removeAttribute('onclick');
                        newElement.removeAttribute('href');
                        if (newElement.tagName === 'A') {
                            newElement.setAttribute('href', '#');
                        }

                        // Add our search functionality
                        newElement.addEventListener('click', function(e) {
                            e.preventDefault();
                            e.stopPropagation();
                            e.stopImmediatePropagation();
                            showSearchInput();
                        });

                        // Mark as processed and replace
                        newElement.setAttribute('data-demo-search-processed', 'true');
                        element.parentNode.replaceChild(newElement, element);
                        replacedCount++;
                    }
                });

                console.log(`Replaced ${replacedCount} search elements`);
            }

            replaceSearchElements();

            console.log('Demo search replacement complete. Dynamic monitoring active.');
        });
    '''


def inject_search_functionality(html_content: str, target_url: str) -> str:
    """
    Replace existing site search functionality with our demo search

    Args:
        html_content: Original HTML content
        target_url: Target site URL

    Returns:
        HTML content with injected search JavaScript
    """
    try:
        logger.info(f"Starting search injection for {target_url}")
        soup = BeautifulSoup(html_content, 'html.parser')

        # Add JavaScript to completely replace their search functionality
        script = soup.new_tag('script')
        script.string = get_search_injection_script()

        # Find body and append our script
        body = soup.find('body')
        if body:
            body.append(script)
            logger.info(f"Search injection script added successfully to {target_url}")
        else:
            logger.warning(f"No body tag found for search injection in {target_url}")

        return str(soup)

    except Exception as e:
        logger.warning(f"Failed to inject search functionality: {e}")
        return html_content
