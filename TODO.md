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

## Current Tasks


- Erweitere die Bewertung mittels der 17Lands Api so das die daten dort in einer cache zwischengespeichert werden und von dort wiederverwendet werden. 
- Weiters teste die Cache. 
- Überprüfe ob auch wirklich die Bewertung von 17 Lands für die Optimierung herangezogen wird wenn diese option gewählt wird. 
- Ergänze die Bewertung in der Rechten oberen Ecke falls diese von 17 Lands stammt statt der Manuellen Bewertung. 

- [ ] **Performance optimization of evaluation functions**
  - Implement caching for synergy calculations
  - Optimization of 17Lands data integration


- Optimierung
  - Bitte stell sicher das die Optimierungsalgortithmen immer auch die Kostenfunktion verwenden. 
  - Also Kostenfunktion nennst du im moment evaluation. Ich möchte aber das optimierungskriterium quasi ändern. 

- Deck Analysis
  - Seperiere die Deck Analysis von der Deck Visualization. Mach einen eigenen "Block" dafür. 

- Soppen der Optimierung
  - Mach eine option zum stoppen der optimierung. Also ein knopf der rot ist und statt dem Start Optimization Knopf auftaucht. 

- Logging
  - Bitte verwende pythons logging für die Console. 
  - Bitte seperiere in User relevante outputs und in developer relevante outputs und mach zwei modi. 
  - Im debug modus sollen alle daten auf dem optimization output ausgegeben werden Im User modus nur die User relevanten. 
  - Füg aber immer alle daten in ein logfile ein. - Das kommt dann in den jeweiligen ordner in dem wir die derzeitgen files ablegen. 