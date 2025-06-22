# MTG Sealed Deck Optimizer - TODO List



## Current Tasks

- [ ] **[Kern] Bewertungs-Interface definieren**
  - Funktion: `evaluate_deck(decklist: list[str], method: str) -> float`
  - Ermöglicht verschiedene Bewertungsmethoden abhängig von der Auswahl

- [ ] **[UI] Top-Down-Auswahlmenü vorbereiten**
  - Dropdown-Auswahl für Bewertungsmethode
  - Auswahl beeinflusst welche Bewertungsfunktion verwendet wird

- [ ] **[Option 1] Automatisierte Bewertung über 17Lands-Daten**
  - Lade `card_ratings.csv`
  - Verwende: `game_in_hand_win_rate` + `improvement_when_drawn`
  - Beschreibung im Menü: „Datenbasierte Bewertung aus 17Lands – kombiniert GIH Winrate und IWD.“

- [ ] **[Option 2] Bisherige manuelle Bewertungs- und Synergiefunktion**
  - Nutzt lokale Ratings und Synergieboni
  - Beschreibung im Menü: „Manuelle Bewertung + Synergiewerte aus lokalem Dictionary.“
  - Funktion: `evaluate_deck_manual(decklist: list[str])`



