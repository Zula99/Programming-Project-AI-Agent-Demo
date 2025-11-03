# quality_monitoring.py - Site-specific quality thresholds for plateau detection

def _get_site_specific_thresholds(site_type):
    """
    Map BusinessSiteType to quality plateau thresholds
    All 13 site types from ai_content_classifier.py with appropriate settings
    """
    from ai_content_classifier import BusinessSiteType

    # VERY PERMISSIVE - Product/content rich sites that want comprehensive coverage
    if site_type == BusinessSiteType.ECOMMERCE:
        return {
            'quality_window_size': 25,      # Larger window for product variety
            'worthy_threshold': 0.15,       # Only 15% worthy needed (very low)
            'diversity_threshold': 0.95,    # 95% similarity to stop (very high)
            'diversity_window_size': 20     # Check more pages for diversity
        }
    elif site_type == BusinessSiteType.RESTAURANT:
        return {
            'quality_window_size': 20,
            'worthy_threshold': 0.2,        # Most restaurant content is valuable
            'diversity_threshold': 0.9,     # Menu items can be similar
            'diversity_window_size': 15
        }
    elif site_type == BusinessSiteType.REAL_ESTATE:
        return {
            'quality_window_size': 25,
            'worthy_threshold': 0.2,        # Property listings are valuable
            'diversity_threshold': 0.9,     # Properties can be similar
            'diversity_window_size': 18
        }

    # MODERATELY PERMISSIVE - Professional content sites
    elif site_type == BusinessSiteType.HEALTHCARE:
        return {
            'quality_window_size': 20,
            'worthy_threshold': 0.25,       # Medical content should be quality
            'diversity_threshold': 0.85,    # Allow some similar health topics
            'diversity_window_size': 15
        }
    elif site_type == BusinessSiteType.EDUCATIONAL:
        return {
            'quality_window_size': 22,
            'worthy_threshold': 0.25,       # Academic content variety important
            'diversity_threshold': 0.85,    # Courses/programs can be similar
            'diversity_window_size': 16
        }
    elif site_type == BusinessSiteType.LEGAL:
        return {
            'quality_window_size': 18,
            'worthy_threshold': 0.3,        # Legal content should be substantial
            'diversity_threshold': 0.85,    # Practice areas can overlap
            'diversity_window_size': 14
        }
    elif site_type == BusinessSiteType.TECHNOLOGY:
        return {
            'quality_window_size': 22,
            'worthy_threshold': 0.2,        # Tech content often valuable (bias toward inclusion)
            'diversity_threshold': 0.85,    # Products/solutions can be similar
            'diversity_window_size': 16
        }
    elif site_type == BusinessSiteType.NON_PROFIT:
        return {
            'quality_window_size': 20,
            'worthy_threshold': 0.25,       # Mission-driven content important
            'diversity_threshold': 0.8,     # Programs/initiatives should be diverse
            'diversity_window_size': 15
        }

    # BALANCED - Standard business content
    elif site_type == BusinessSiteType.BANKING:
        return {
            'quality_window_size': 20,
            'worthy_threshold': 0.3,        # Financial content needs quality
            'diversity_threshold': 0.8,     # Standard similarity threshold
            'diversity_window_size': 15
        }
    elif site_type == BusinessSiteType.CORPORATE:
        return {
            'quality_window_size': 18,
            'worthy_threshold': 0.3,        # Professional corporate content
            'diversity_threshold': 0.8,     # Business content should vary
            'diversity_window_size': 14
        }
    elif site_type == BusinessSiteType.GOVERNMENT:
        return {
            'quality_window_size': 20,
            'worthy_threshold': 0.3,        # Government services should be quality
            'diversity_threshold': 0.8,     # Services should be diverse
            'diversity_window_size': 15
        }

    # HIGHER STANDARDS - Content/editorial sites
    elif site_type == BusinessSiteType.NEWS:
        return {
            'quality_window_size': 18,
            'worthy_threshold': 0.4,        # News should be engaging
            'diversity_threshold': 0.7,     # Articles can be topically similar
            'diversity_window_size': 12
        }
    elif site_type == BusinessSiteType.ENTERTAINMENT:
        return {
            'quality_window_size': 20,
            'worthy_threshold': 0.35,       # Entertainment should be engaging
            'diversity_threshold': 0.75,    # Content can have similar themes
            'diversity_window_size': 14
        }

    # DEFAULT - Unknown or unmatched site types
    else:  # BusinessSiteType.UNKNOWN or any new types
        return {
            'quality_window_size': 20,
            'worthy_threshold': 0.3,        # Balanced default
            'diversity_threshold': 0.8,     # Standard similarity threshold
            'diversity_window_size': 15
        }
