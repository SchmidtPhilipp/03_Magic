#!/usr/bin/env python3
"""
Configuration file for MTG Sealed Deck Optimizer
Centralizes all configurable elements for easy customization
"""

# =============================================================================
# APPLICATION METADATA
# =============================================================================
APP_NAME = "MTG Sealed Deck Optimizer"
APP_VERSION = "1.0.0"
APP_YEAR = "2025"
APP_DESCRIPTION = "Advanced Magic: The Gathering sealed deck optimization tool"

# =============================================================================
# WEB INTERFACE TEXT
# =============================================================================
WEB_TEXTS = {
    # Page title
    "page_title": "Sealed Limited Optimizer",
    # Header and navigation
    "header_title": "MTG Sealed Deck Optimizer",
    "header_icon": "fas fa-hat-wizard",
    # Footer
    "footer_text": "MTG Sealed Deck Optimizer",
    "footer_icon": "fas fa-hat-wizard",
    "github_link": "https://github.com/",
    "github_text": "GitHub",
    "github_icon": "fab fa-github",
    # Welcome messages
    "welcome_title": "Welcome to Sealed Limited Optimizer!",
    "welcome_message": "Upload a CSV file and configure settings to start.",
    # Panel headers
    "deck_settings_title": "Deck Settings",
    "deck_settings_icon": "fas fa-cog",
    "optimization_output_title": "Optimization Output",
    "optimization_output_icon": "fas fa-terminal",
    "results_title": "Results",
    "results_icon": "fas fa-chart-bar",
    "deck_visualization_title": "Deck Visualization",
    "deck_visualization_icon": "fas fa-cards-blank",
    "download_deck_title": "Download Deck",
    "download_deck_icon": "fas fa-download",
    "current_file_title": "Current File",
    "current_file_icon": "fas fa-file-csv",
    # Form labels
    "upload_csv_label": "Upload Collection CSV",
    "target_colors_label": "Target Colors",
    "deck_size_label": "Deck Size (total)",
    "land_ratio_label": "Number of Lands:",
    "algorithm_label": "Algorithm",
    "color_penalty_label": "Color Penalty Strength",
    "optimize_button_text": "Start Optimization",
    "optimize_button_icon": "fas fa-play",
    "progress_label": "Optimization Progress",
    "card_size_label": "Size:",
    # Algorithm options
    "algorithm_greedy": "Greedy",
    "algorithm_genetic": "Genetic Algorithm",
    "algorithm_simulated_annealing": "Simulated Annealing",
    # Lambda penalty labels
    "lambda_soft": "0.1 (Soft)",
    "lambda_hard": "5.0 (Hard)",
    # Card size labels
    "card_size_small": "Small",
    "card_size_normal": "Normal",
    "card_size_large": "Large",
    # Download format labels
    "download_arena": "MTG Arena Format",
    "download_html": "HTML with Artwork",
    "download_mtgo": "MTGO Format",
    # Status messages
    "starting_status": "Starting...",
    "results_placeholder": "Optimization results will appear here...",
    "deck_placeholder": "Deck cards will be displayed here after optimization...",
    "file_info_label": "File:",
    "cards_label": "Cards:",
    # Button tooltips
    "copy_output_tooltip": "Copy Output",
    "clear_output_tooltip": "Clear Output",
}

# =============================================================================
# COLORS AND STYLING
# =============================================================================
COLORS = {
    # Primary gradient colors
    "primary_gradient_start": "#1a2980",
    "primary_gradient_end": "#26d0ce",
    # Bootstrap color classes
    "header_bg": "bg-gradient-primary",
    "footer_bg": "bg-gradient-primary",
    "deck_settings_header": "bg-primary",
    "optimization_header": "bg-dark",
    "results_header": "bg-success",
    "download_header": "bg-warning",
    "current_file_header": "bg-info",
    "deck_visualization_header": "bg-secondary",
    # Text colors
    "header_text": "text-white",
    "footer_text": "text-white",
    "card_header_text": "text-white",
    "download_header_text": "text-dark",
    # Button colors
    "optimize_button": "btn-gradient",
    "copy_button": "btn-outline-light",
    "clear_button": "btn-outline-light",
    "download_arena_button": "btn-outline-primary",
    "download_html_button": "btn-outline-success",
    "download_mtgo_button": "btn-outline-info",
}

# =============================================================================
# NUMBERS AND LIMITS
# =============================================================================
NUMBERS = {
    # Deck configuration
    "default_num_colors": 2,
    "min_colors": 1,
    "max_colors": 5,
    "default_deck_size": 40,
    "min_deck_size": 20,
    "max_deck_size": 60,
    "default_land_ratio": 17,
    "min_land_ratio": 14,
    "max_land_ratio": 24,
    # Lambda penalty
    "default_lambda": 0.5,
    "min_lambda": 0.1,
    "max_lambda": 5.0,
    "lambda_step": 0.1,
    # Card size slider
    "default_card_size": 1.0,
    "min_card_size": 0.5,
    "max_card_size": 2.0,
    "card_size_step": 0.1,
    # File upload
    "max_file_size_mb": 16,
    "max_output_lines": 1000,
    "output_buffer_size": 50,
}

# =============================================================================
# LINKS AND EXTERNAL RESOURCES
# =============================================================================
LINKS = {
    # CDN resources
    "bootstrap_css": "https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css",
    "bootstrap_js": "https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js",
    "fontawesome_css": "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css",
    # External services
    "scryfall_api": "https://api.scryfall.com/cards/named",
    "github_repo": "https://github.com/",
}

# =============================================================================
# FILE PATHS AND FOLDERS
# =============================================================================
PATHS = {
    "upload_folder": "uploads",
    "cache_folder": "static/card_cache",
    "static_folder": "static",
    "templates_folder": "templates",
    "default_csv": "data/collections/FinalFantasy.csv",
}

# =============================================================================
# ALGORITHM CONFIGURATION
# =============================================================================
ALGORITHMS = {
    "greedy": {
        "name": "Greedy",
        "description": "Fast greedy algorithm for quick optimization",
        "show_lambda": False,
    },
    "genetic": {
        "name": "Genetic Algorithm",
        "description": "Evolutionary algorithm for complex optimization",
        "show_lambda": True,
    },
    "simulated_annealing": {
        "name": "Simulated Annealing",
        "description": "Probabilistic optimization algorithm",
        "show_lambda": True,
    },
}

# =============================================================================
# EXPORT FORMATS
# =============================================================================
EXPORT_FORMATS = {
    "arena": {
        "name": "MTG Arena Format",
        "description": "Format compatible with MTG Arena import",
        "icon": "fas fa-download",
        "button_class": "btn-outline-primary",
    },
    "html": {
        "name": "HTML with Artwork",
        "description": "HTML file with card images",
        "icon": "fas fa-download",
        "button_class": "btn-outline-success",
    },
    "mtgo": {
        "name": "MTGO Format",
        "description": "Format compatible with Magic Online",
        "icon": "fas fa-download",
        "button_class": "btn-outline-info",
    },
}

# =============================================================================
# APPLICATION SETTINGS
# =============================================================================
APP_CONFIG = {
    "secret_key": "magic_optimizer_secret_key",
    "debug": True,
    "host": "0.0.0.0",
    "port": 5050,
    "threaded": True,
}

# =============================================================================
# VALIDATION MESSAGES
# =============================================================================
VALIDATION_MESSAGES = {
    "no_file": "No file provided",
    "no_file_selected": "No file selected",
    "invalid_file_type": "Invalid file type. Please upload a CSV file.",
    "invalid_csv": "Invalid CSV file: {error}",
    "optimization_running": "Optimization already running",
    "file_upload_success": "File uploaded successfully",
    "optimization_started": "Optimization started",
    "optimization_completed": "Optimization completed",
    "optimization_error": "Error during optimization: {error}",
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def get_gradient_style():
    """Get the CSS gradient style string"""
    return f"linear-gradient(90deg, {COLORS['primary_gradient_start']} 0%, {COLORS['primary_gradient_end']} 100%)"


def get_algorithm_options():
    """Get algorithm options for HTML select"""
    return [(key, value["name"]) for key, value in ALGORITHMS.items()]


def get_export_format_options():
    """Get export format options for HTML"""
    return [
        (key, value["name"], value["button_class"], value["icon"])
        for key, value in EXPORT_FORMATS.items()
    ]
