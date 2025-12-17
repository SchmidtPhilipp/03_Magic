# MTG Sealed Deck Optimizer - Project Index

## 📋 Project Overview

The **MTG Sealed Deck Optimizer** is a sophisticated web application for optimizing Magic: The Gathering sealed deck formats using advanced algorithms and machine learning techniques. The project provides both a web interface and command-line tools for deck optimization.

## 🏗️ Architecture Overview

### Core Components
- **Web Application**: Flask-based web interface with real-time optimization
- **Optimization Engine**: Multiple algorithms (Greedy, Genetic, Simulated Annealing)
- **Card Evaluation System**: Multiple evaluation methods and rating systems
- **Export System**: Multiple format support (MTG Arena, MTGO, HTML with artwork)
- **Image Caching**: Local card image storage with Scryfall integration

## 📁 Project Structure

### Root Directory Files
```
03_Magic/
├── web_app.py                 # Main Flask web application
├── main_organized.py          # Command-line interface
├── config.py                  # Centralized configuration
├── requirements.txt           # Python dependencies
├── Dockerfile                # Docker container configuration
├── docker-compose.yml        # Docker Compose setup
├── README.md                 # Project documentation
├── start_app.sh              # Application startup script
├── stop_app.sh               # Application shutdown script
└── PROJECT_INDEX.md          # This file - comprehensive project index
```

### Core Source Code (`src/magic_optimizer/`)
```
src/magic_optimizer/
├── __init__.py               # Package initialization
├── deck_builder.py           # Main deck building logic
├── card.py                   # Card data model
├── validator.py              # Card validation system
├── optimizer.py              # Optimization orchestration
├── algorithms/               # Algorithm implementations
├── evaluators/              # Card evaluation methods
├── exporters/               # Export format handlers
└── utils/                   # Utility functions
```

### Algorithm Implementations (`src/magic_optimizer/optimizers/`)
```
optimizers/
├── __init__.py              # Factory function for optimizer creation
├── base_optimizer.py        # Abstract base class for optimizers
├── greedy_optimizer.py      # Fast greedy algorithm implementation
├── genetic_optimizer.py     # Evolutionary algorithm implementation
└── simulated_annealing_optimizer.py  # Probabilistic optimization
```

### Evaluation Methods (`src/magic_optimizer/evaluators/`)
```
evaluators/
├── __init__.py              # Factory function for evaluator creation
├── base_evaluator.py        # Abstract base class for evaluators
├── manual_evaluator.py      # Manual rating system
├── seventeen_lands_evaluator.py  # 17Lands integration
├── empirical_models_evaluator.py # Empirical model evaluation
├── model_specific_evaluator.py   # Model-specific evaluation
└── game_mechanics_evaluator.py   # Game mechanics evaluation
```

### Export System (`src/magic_optimizer/exporters/`)
```
exporters/
├── __init__.py              # Export system initialization
└── deck_exporter.py         # Multiple format export handlers
```

### Web Interface (`templates/` and `static/`)
```
templates/
├── index.html               # Main web interface
└── deck_export_artwork.html # HTML export template

static/
├── css/style.css           # Custom styling
├── js/app.js              # Frontend JavaScript logic
├── card_cache/            # Cached card images
└── FinalFantasy.csv       # Default collection file
```

### Data Management (`data/`)
```
data/
├── collections/            # Card collection files
│   ├── FinalFantasy.csv   # Default collection
│   └── collection_*.csv   # User collections
└── ratings/               # Card rating systems
    ├── card_ratings.csv   # Main rating file
    ├── 17lands_ratings.csv # 17Lands ratings
    └── test_*.csv         # Test rating files
```

### Testing (`tests/`)
```
tests/
├── test_17lands_integration.py      # 17Lands API testing
├── test_artwork_export.py           # Export functionality testing
├── test_cache_performance.py        # Performance testing
├── test_color_constraints.py        # Color constraint testing
├── test_complete_system.py          # End-to-end testing
├── test_enhanced_evaluation.py      # Evaluation method testing
├── test_land_calculation.py         # Land calculation testing
├── test_performance_optimizations.py # Performance optimization testing
└── test_targeted_ratings.py         # Rating system testing
```

## 🔧 Core Components

### 1. Web Application (`web_app.py`)
**Purpose**: Main Flask web server providing the user interface
**Key Features**:
- File upload handling
- Real-time optimization status
- Progress tracking
- Image caching system
- Multiple export formats
- RESTful API endpoints

**Main Routes**:
- `/` - Main interface
- `/upload` - File upload handling
- `/optimize` - Start optimization
- `/status` - Get optimization status
- `/download/<format>` - Download optimized deck
- `/cache_card_image/<card_name>` - Cache card images

### 2. Deck Builder (`src/magic_optimizer/deck_builder.py`)
**Purpose**: Core optimization orchestration
**Key Features**:
- Collection loading and validation
- Algorithm selection and execution
- Land calculation and distribution
- Deck analysis and visualization
- Export format generation

**Main Methods**:
- `load_collection()` - Load card collection from file
- `build_optimal_deck_advanced()` - Main optimization method
- `analyze_deck()` - Deck analysis and statistics
- `calculate_optimal_lands()` - Land distribution calculation

### 3. Optimization Algorithms

#### Greedy Algorithm (`greedy_optimizer.py`)
- **Complexity**: O(n × m) where n = cards, m = colors
- **Best For**: Fast optimization, large collections
- **Features**: Mean color rating, fixed color support

#### Genetic Algorithm (`genetic_optimizer.py`)
- **Complexity**: O(g × p × n) where g = generations, p = population
- **Best For**: Complex optimization, best results
- **Features**: Tournament selection, crossover, mutation, elitism

#### Simulated Annealing (`simulated_annealing_optimizer.py`)
- **Complexity**: O(iterations × temperature_steps)
- **Best For**: Global optimization, balanced results
- **Features**: Temperature-controlled random walks, cooling schedule

### 4. Evaluation Methods

#### Manual Evaluator (`manual_evaluator.py`)
- Uses predefined card ratings
- Supports custom rating files
- Fast evaluation method

#### 17Lands Evaluator (`seventeen_lands_evaluator.py`)
- Integrates with 17Lands API
- Real-time rating updates
- Limited format support

#### Empirical Models Evaluator (`empirical_models_evaluator.py`)
- Multiple empirical models
- Vanilla, MIT, Cube, Average models
- Advanced statistical evaluation

### 5. Export System (`exporters/deck_exporter.py`)
**Supported Formats**:
- **MTG Arena**: Direct import format
- **MTGO**: Magic Online format
- **HTML with Artwork**: Visual deck display
- **Cockatrice**: Cockatrice format

## 🎨 User Interface

### Frontend Components (`static/js/app.js`)
**Key Features**:
- Real-time optimization monitoring
- Dynamic card visualization
- Mobile-responsive design
- Touch-friendly interface
- Image caching and loading
- Export functionality

**Main Functions**:
- `startOptimization()` - Begin optimization process
- `updateProgressStatus()` - Real-time status updates
- `updateDeckVisualization()` - Card display management
- `cacheCardImage()` - Image caching system

### Styling (`static/css/style.css`)
**Design Features**:
- Gradient themes
- Responsive design
- Mobile optimization
- Card visualization styling
- Interactive elements

## 📊 Data Management

### Collection Format
CSV files with columns:
- `name`: Card name
- `rating`: Card rating (0-10)
- `colors`: Card colors (W, U, B, R, G)
- `cmc`: Converted mana cost
- `type`: Card type

### Rating Systems
- **Manual Ratings**: Custom rating files
- **17Lands Integration**: Real-time ratings
- **Empirical Models**: Statistical models
- **Test Ratings**: Development testing

## 🧪 Testing Framework

### Test Categories
1. **Integration Tests**: End-to-end functionality
2. **Algorithm Tests**: Optimization algorithm validation
3. **Performance Tests**: Speed and memory optimization
4. **Export Tests**: Format generation validation
5. **Color Constraint Tests**: Color logic validation

### Key Test Files
- `test_complete_system.py` - Full system validation
- `test_performance_optimizations.py` - Performance testing
- `test_color_constraints.py` - Color logic testing
- `test_land_calculation.py` - Land distribution testing

## 🐳 Deployment

### Docker Configuration
- **Dockerfile**: Python 3.10 with development tools
- **docker-compose.yml**: Multi-service setup
- **Port**: 5050 (configurable)
- **Volumes**: Live development mounting

### Environment Variables
- `FLASK_ENV`: Development/production mode
- `FLASK_DEBUG`: Debug mode toggle
- `PYTHONPATH`: Python path configuration
- `PORT`: Application port

## 🔧 Configuration (`config.py`)

### Centralized Configuration
- **Web Interface**: Text, colors, styling
- **Algorithm Settings**: Parameters and limits
- **Export Formats**: Format definitions
- **File Paths**: Directory structure
- **Validation Messages**: User feedback

### Key Configuration Sections
- `WEB_TEXTS`: Interface text and labels
- `COLORS`: Styling and theme colors
- `NUMBERS`: Limits and default values
- `ALGORITHMS`: Algorithm configurations
- `EXPORT_FORMATS`: Export format definitions

## 📈 Performance Characteristics

### Optimization Speed
- **Greedy**: 1-3 seconds for typical collections
- **Genetic**: 5-10 seconds for complex optimization
- **Simulated Annealing**: 3-8 seconds for balanced results

### Memory Usage
- **Image Caching**: 90%+ reduction in load times
- **Algorithm Efficiency**: Optimized for large collections
- **Scalability**: Handles 1000+ card collections

### Caching System
- **Card Images**: Local storage with Scryfall API
- **Ratings**: Cached rating data
- **Results**: Temporary optimization results

## 🚀 Quick Start Guide

### Development Setup
1. **Clone Repository**: `git clone <repository-url>`
2. **Install Dependencies**: `pip install -r requirements.txt`
3. **Run Web App**: `python web_app.py`
4. **Access Interface**: `http://localhost:5050`

### Docker Setup
1. **Build Container**: `docker-compose build`
2. **Start Services**: `docker-compose up`
3. **Access Interface**: `http://localhost:5050`

### Command Line Usage
1. **Run CLI**: `python main_organized.py`
2. **Follow Prompts**: Configure optimization parameters
3. **View Results**: Optimized deck output

## 🔍 Key Features Summary

### Advanced Algorithms
- ✅ Greedy optimization for speed
- ✅ Genetic algorithm for quality
- ✅ Simulated annealing for balance
- ✅ Color constraint optimization
- ✅ Land ratio management

### Professional Interface
- ✅ Modern responsive design
- ✅ Real-time progress tracking
- ✅ Interactive card visualization
- ✅ Mobile-optimized interface
- ✅ Multiple export formats

### Data Management
- ✅ CSV collection import
- ✅ Scryfall API integration
- ✅ Multiple rating systems
- ✅ Image caching system
- ✅ Comprehensive testing

## 📝 Development Notes

### Code Organization
- **Modular Design**: Clear separation of concerns
- **Factory Pattern**: Dynamic algorithm/evaluator creation
- **Configuration-Driven**: Centralized configuration management
- **Test-Driven**: Comprehensive test coverage

### Best Practices
- **Error Handling**: Comprehensive exception management
- **Logging**: Multi-level logging system
- **Documentation**: Inline code documentation
- **Performance**: Optimized algorithms and caching

### Future Enhancements
- **Machine Learning**: Advanced card evaluation
- **API Integration**: Additional rating sources
- **Mobile App**: Native mobile application
- **Cloud Deployment**: Scalable cloud hosting

---

**Version**: 1.1.0  
**Last Updated**: January 2025  
**Maintainer**: MTG Sealed Deck Optimizer Team 