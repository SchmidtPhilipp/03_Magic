# Configuration Guide

This guide explains how to customize the MTG Sealed Deck Optimizer using the `config.py` file.

## Overview

The `config.py` file centralizes all configurable elements of the application, making it easy to customize:
- Application metadata (name, version, year)
- Web interface text and labels
- Colors and styling
- Numbers and limits
- External links and resources
- File paths and folders
- Algorithm settings
- Export formats
- Validation messages

## Quick Customization Examples

### Change Application Name

```python
# In config.py
APP_NAME = "My Custom Deck Optimizer"
WEB_TEXTS = {
    "page_title": "My Custom Deck Optimizer",
    "header_title": "My Custom Deck Optimizer",
    "footer_text": "My Custom Deck Optimizer",
    # ... other text updates
}
```

### Change Colors

```python
# In config.py
COLORS = {
    "primary_gradient_start": "#2c3e50",  # Dark blue
    "primary_gradient_end": "#3498db",    # Light blue
    "deck_settings_header": "bg-info",    # Change to info blue
    "results_header": "bg-warning",       # Change to warning yellow
    # ... other color changes
}
```

### Change Default Values

```python
# In config.py
NUMBERS = {
    "default_num_colors": 3,        # Default to 3 colors
    "default_deck_size": 60,        # Default to 60-card deck
    "default_land_ratio": 24,       # Default to 24 lands
    "min_deck_size": 40,            # Minimum deck size
    "max_deck_size": 100,           # Maximum deck size
    # ... other number changes
}
```

### Add New Algorithm

```python
# In config.py
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
    "my_custom_algorithm": {        # Add new algorithm
        "name": "My Custom Algorithm",
        "description": "My custom optimization algorithm",
        "show_lambda": True,
    },
}
```

### Add New Export Format

```python
# In config.py
EXPORT_FORMATS = {
    "arena": {
        "name": "MTG Arena Format",
        "description": "Format compatible with MTG Arena import",
        "icon": "fas fa-download",
        "button_class": "btn-outline-primary",
    },
    "my_custom_format": {           # Add new format
        "name": "My Custom Format",
        "description": "My custom export format",
        "icon": "fas fa-file-export",
        "button_class": "btn-outline-secondary",
    },
}
```

## Configuration Sections

### Application Metadata

```python
APP_NAME = "MTG Sealed Deck Optimizer"
APP_VERSION = "1.0.0"
APP_YEAR = "2025"
APP_DESCRIPTION = "Advanced Magic: The Gathering sealed deck optimization tool"
```

### Web Interface Text

All text displayed in the web interface can be customized:

```python
WEB_TEXTS = {
    "page_title": "Sealed Limited Optimizer",
    "header_title": "MTG Sealed Deck Optimizer",
    "welcome_title": "Welcome to Sealed Limited Optimizer!",
    "deck_settings_title": "Deck Settings",
    "optimize_button_text": "Start Optimization",
    # ... many more text options
}
```

### Colors and Styling

Customize the visual appearance:

```python
COLORS = {
    "primary_gradient_start": "#1a2980",  # Header/footer gradient start
    "primary_gradient_end": "#26d0ce",    # Header/footer gradient end
    "deck_settings_header": "bg-primary", # Panel header colors
    "optimize_button": "btn-gradient",    # Button styling
    # ... other color options
}
```

### Numbers and Limits

Configure all numerical settings:

```python
NUMBERS = {
    "default_num_colors": 2,        # Default number of colors
    "min_colors": 1,                # Minimum colors allowed
    "max_colors": 5,                # Maximum colors allowed
    "default_deck_size": 40,        # Default deck size
    "min_deck_size": 20,            # Minimum deck size
    "max_deck_size": 60,            # Maximum deck size
    "default_lambda": 0.5,          # Default lambda penalty
    "max_file_size_mb": 16,         # Maximum file upload size
    # ... other numerical settings
}
```

### Links and External Resources

Configure external dependencies:

```python
LINKS = {
    "bootstrap_css": "https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css",
    "bootstrap_js": "https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js",
    "fontawesome_css": "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css",
    "scryfall_api": "https://api.scryfall.com/cards/named",
    "github_repo": "https://github.com/your-repo",
}
```

### File Paths and Folders

Configure file system paths:

```python
PATHS = {
    "upload_folder": "uploads",
    "cache_folder": "static/card_cache",
    "static_folder": "static",
    "templates_folder": "templates",
    "default_csv": "data/collections/FinalFantasy.csv",
}
```

### Application Settings

Configure Flask application settings:

```python
APP_CONFIG = {
    "secret_key": "magic_optimizer_secret_key",
    "debug": True,
    "host": "0.0.0.0",
    "port": 5050,
    "threaded": True,
}
```

### Validation Messages

Customize error and validation messages:

```python
VALIDATION_MESSAGES = {
    "no_file": "No file provided",
    "no_file_selected": "No file selected",
    "invalid_file_type": "Invalid file type. Please upload a CSV file.",
    "optimization_running": "Optimization already running",
    # ... other validation messages
}
```

## Advanced Customization

### Custom Gradient Styles

You can create custom gradient functions:

```python
def get_custom_gradient_style():
    """Get a custom CSS gradient style string"""
    return f"linear-gradient(45deg, {COLORS['primary_gradient_start']} 0%, {COLORS['primary_gradient_end']} 50%, #e74c3c 100%)"
```

### Dynamic Configuration

You can make configuration dynamic based on environment:

```python
import os

# Use environment variables for sensitive settings
APP_CONFIG = {
    "secret_key": os.environ.get("SECRET_KEY", "default_secret_key"),
    "debug": os.environ.get("DEBUG", "True").lower() == "true",
    "host": os.environ.get("HOST", "0.0.0.0"),
    "port": int(os.environ.get("PORT", "5050")),
    "threaded": True,
}
```

### Theme Support

You can create multiple themes:

```python
THEMES = {
    "default": {
        "primary_gradient_start": "#1a2980",
        "primary_gradient_end": "#26d0ce",
        "deck_settings_header": "bg-primary",
    },
    "dark": {
        "primary_gradient_start": "#2c3e50",
        "primary_gradient_end": "#34495e",
        "deck_settings_header": "bg-dark",
    },
    "light": {
        "primary_gradient_start": "#ecf0f1",
        "primary_gradient_end": "#bdc3c7",
        "deck_settings_header": "bg-light",
    },
}
```

## Best Practices

1. **Backup your config**: Before making changes, backup your `config.py` file
2. **Test changes**: After making changes, test the application thoroughly
3. **Use version control**: Commit configuration changes to track modifications
4. **Document customizations**: Add comments to explain why changes were made
5. **Environment-specific configs**: Use environment variables for deployment-specific settings

## Troubleshooting

### Common Issues

1. **Template errors**: Make sure all referenced config values exist
2. **Color issues**: Verify Bootstrap color classes are valid
3. **Path errors**: Ensure file paths exist and are accessible
4. **Import errors**: Check that all required modules are installed

### Validation

After making changes, validate your configuration:

```python
# Add this to config.py for validation
def validate_config():
    """Validate configuration settings"""
    required_sections = ['WEB_TEXTS', 'COLORS', 'NUMBERS', 'LINKS', 'PATHS']
    for section in required_sections:
        if not hasattr(config, section):
            raise ValueError(f"Missing required config section: {section}")
    
    # Validate specific values
    if config.NUMBERS['min_colors'] > config.NUMBERS['max_colors']:
        raise ValueError("min_colors cannot be greater than max_colors")
    
    print("Configuration validation passed!")

if __name__ == "__main__":
    validate_config()
```

This configuration system makes the MTG Sealed Deck Optimizer highly customizable while maintaining a clean, organized codebase. 