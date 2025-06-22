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
- ✓ **[Kern] Bewertungs-Interface definieren**
  - Funktion: `evaluate_deck(decklist: list[str], method: str) -> float`
  - Ermöglicht verschiedene Bewertungsmethoden abhängig von der Auswahl

- ✓ **[UI] Top-Down-Auswahlmenü vorbereiten**
  - Dropdown-Auswahl für Bewertungsmethode
  - Auswahl beeinflusst welche Bewertungsfunktion verwendet wird

- ✓ **[Option 1] Automatisierte Bewertung über 17Lands-Daten**
  - Lade `card_ratings.csv`
  - Verwende: `game_in_hand_win_rate` + `improvement_when_drawn`
  - Beschreibung im Menü: „Datenbasierte Bewertung aus 17Lands – kombiniert GIH Winrate und IWD."

- ✓ **[Option 2] Bisherige manuelle Bewertungs- und Synergiefunktion**
  - Nutzt lokale Ratings und Synergieboni
  - Beschreibung im Menü: „Manuelle Bewertung + Synergiewerte aus lokalem Dictionary."
  - Funktion: `evaluate_deck_manual(decklist: list[str])`

## Current Tasks

- [ ] **Performance-Optimierung der Bewertungsfunktionen**
  - Caching für Synergie-Berechnungen implementieren
  - Parallele Verarbeitung für große Decks
  - Optimierung der 17Lands-Datenintegration

- [ ] **Erweiterte Synergie-Erkennung**
  - Mehr Synergie-Patterns hinzufügen
  - Dynamische Synergie-Bewertung basierend auf Deck-Kontext
  - Tribal-Synergien implementieren

## Future Tasks

### Performance & Optimization
- Implement advanced caching strategies for card data
- Add parallel processing for large collections
- Optimize memory usage for large deck optimizations
- Add GPU acceleration for genetic algorithm
- Implement incremental optimization for real-time updates

### Algorithm Enhancements
- Add machine learning-based card evaluation
- Implement neural network for deck scoring
- Add reinforcement learning for optimization
- Create ensemble methods combining multiple algorithms
- Add support for different format-specific strategies

### Data Integration
- Real-time 17Lands data integration
- MTG Arena data import
- Scryfall API rate limiting improvements
- Add support for multiple rating sources
- Implement card price integration

### User Experience
- Add deck comparison tools
- Implement deck sharing functionality
- Add export to popular deck building sites
- Create mobile-responsive design
- Add dark mode theme

### Advanced Features
- Multi-player draft simulation
- Tournament bracket generation
- Sideboard optimization
- Meta-game analysis
- Card recommendation engine

### Testing & Quality Assurance
- Add performance benchmarks
- Implement automated testing pipeline
- Add integration tests for web interface
- Create stress tests for large collections
- Add regression testing for algorithm changes