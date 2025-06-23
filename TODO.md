# MTG Sealed Deck Optimizer - TODO List

## Completed Tasks ✓

### Core Functionality
- ✓ Web scraper for MTG Final Fantasy sealed guide pages
- ✓ Card validation using Scryfall API
- ✓ CSV export with card names and ratings
- ✓ Deck builder with color constraints
- ✓ Multiple optimization algorithms (greedy, genetic, simulated annealing)
- ✓ Scoring system for deck evaluation
- ✓ Export formats (Arena, MTGO, text)
- ✓ Flask web application with file upload
- ✓ Live optimization progress updates
- ✓ Deck visualization with card images
- ✓ Download buttons for different formats
- ✓ Backend endpoints for default CSV loading
- ✓ Color and deck size selection UI
- ✓ Conditional lambda slider for genetic algorithm
- ✓ Land ratio slider
- ✓ Total deck size handling
- ✓ Mana curve visualization
- ✓ Color distribution display
- ✓ Card image sizing and caching
- ✓ Fixed color constraint enforcement in all algorithms
- ✓ Fixed colorless card counting in color distribution
- ✓ Comprehensive unit tests for all algorithms
- ✓ Git repository initialization and version 1.0 tag

### UI/UX Improvements
- ✓ Modern, responsive web interface
- ✓ Real-time status updates
- ✓ Card image caching system
- ✓ Mana curve integration with color distribution
- ✓ Simplified export format buttons
- ✓ Numeric inputs for deck size and color selection

### Testing & Validation
- ✓ Unit tests for color constraints
- ✓ Land calculation tests
- ✓ Complete system integration tests
- ✓ Algorithm-specific test suites
- ✓ Color constraint enforcement validation

### Advanced Evaluation System ✓
- ✓ **[Core] Define evaluation interface**
  - Function: `evaluate_deck(decklist: list[str], method: str) -> float`
  - Enables different evaluation methods based on selection

- ✓ **[UI] Prepare top-down selection menu**
  - Dropdown selection for evaluation method
  - Selection influences which evaluation function is used

- ✓ **[Option 1] Automated evaluation via 17Lands data**
  - Load `card_ratings.csv`
  - Use: `game_in_hand_win_rate` + `improvement_when_drawn`
  - Description in menu: "Data-based evaluation from 17Lands – combines GIH Winrate and IWD."

- ✓ **[Option 2] Previous manual evaluation and synergy function**
  - Uses local ratings and synergy bonuses
  - Description in menu: "Manual evaluation + synergy values from local dictionary."
  - Function: `evaluate_deck_manual(decklist: list[str])`

### 17Lands API Integration ✓
- ✓ **17Lands API Cache Implementation**
  - Comprehensive caching system with JSON persistence
  - Batch processing for multiple cards
  - Memory management with configurable cache size
  - Cache hit rate monitoring and optimization

- ✓ **Cache Testing and Validation**
  - Performance tests showing 95,000x speedup with cache
  - Cache persistence verification
  - Cache clearing and optimization features
  - Comprehensive test suite for all cache operations

- ✓ **Evaluation Method Integration**
  - 17Lands evaluation properly integrated into optimization algorithms
  - Fallback to manual ratings when 17Lands data unavailable
  - UI display of evaluation method used
  - Real-time evaluation method switching

### UI Enhancements ✓
- ✓ **Stop Optimization Button**
  - Red stop button that replaces optimize button during optimization
  - Backend endpoint for stopping optimization process
  - Thread-safe stopping mechanism with timeout
  - User-friendly stop confirmation

- ✓ **Evaluation Method Display**
  - Clear indication of which evaluation method was used
  - Description of evaluation method in results panel
  - Visual distinction between manual and 17Lands evaluation

- ✓ **Deck Analysis Separation**
  - Separate "Deck Analysis" section from "Deck Visualization"
  - Comprehensive analysis including color distribution, card types, mana curve
  - Statistical overview with average CMC and ratings
  - Clean separation of concerns in UI

### Logging System ✓
- ✓ **Python Logging Implementation**
  - Comprehensive logging system with user and developer modes
  - Console output for user-relevant messages (INFO level)
  - File logging for all details (DEBUG level)
  - Rotating log files with size limits and backup retention
  - Separate loggers for different components (user, optimization, API)

## Current Tasks

- [ ] **Performance optimization of evaluation functions**
  - Implement caching for synergy calculations
  - Optimization of 17Lands data integration

- Optimierung
  - Bitte stell sicher das die Optimierungsalgortithmen immer auch die Kostenfunktion verwenden. 
  - Also Kostenfunktion nennst du im moment evaluation. Ich möchte aber das optimierungskriterium quasi ändern. 

## Future Enhancements

- [ ] **Advanced Analytics**
  - Deck win rate prediction
  - Matchup analysis
  - Sideboard recommendations

- [ ] **Performance Optimizations**
  - Parallel processing for large collections
  - Advanced caching strategies
  - Memory optimization for large datasets

- [ ] **User Experience**
  - Save/load optimization configurations
  - Deck comparison tools
  - Export to popular deck building platforms