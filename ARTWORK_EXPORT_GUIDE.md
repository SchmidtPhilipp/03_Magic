# 🎨 HTML Artwork Export Guide

## Übersicht

Das Magic Optimizer Projekt unterstützt jetzt **HTML-Export mit Karten-Artworks**! Diese neue Funktion erstellt wunderschöne HTML-Seiten mit echten Kartenbildern von Scryfall.

## ✨ Neue Features

### 🖼️ Karten-Artworks
- **Echte Kartenbilder**: Alle Karten werden mit echten Bildern von der Scryfall API angezeigt
- **Automatische Fehlerbehandlung**: Falls ein Bild nicht verfügbar ist, wird eine Fallback-Nachricht angezeigt
- **Responsive Design**: Die HTML-Seite funktioniert auf Desktop und Mobile

### 🎨 Moderne UI
- **Gradient-Hintergrund**: Schöner blauer Gradient-Hintergrund
- **Hover-Effekte**: Karten heben sich beim Überfahren mit der Maus an
- **Farb-Symbole**: Visuelle Darstellung der Kartenfarben mit farbigen Kreisen
- **Responsive Grid**: Automatische Anpassung an verschiedene Bildschirmgrößen

### 📊 Deck-Informationen
- **Deck-Header**: Zeigt Algorithmus, Datum und Zeitstempel
- **Statistik-Karten**: Übersicht über Farben, Score, Anzahl Karten und Durchschnittsbewertung
- **Detaillierte Karteninfo**: Rating, CMC und Farben für jede Karte

## 🚀 Verwendung

### 1. Über die Hauptanwendung
```bash
python main_organized.py
```

1. Wähle einen Algorithmus (1-3)
2. Gib die Anzahl Farben ein (1-5)
3. Gib die Deck-Größe ein (Standard: 40)
4. Bei Export-Formaten eingeben: `html_artwork`

### 2. Über Python-Code
```python
from magic_optimizer import EnhancedDeckBuilder

builder = EnhancedDeckBuilder()
result = builder.build_optimal_deck_advanced(
    collection_df, 
    num_colors=2, 
    deck_size=40, 
    algorithm='genetic',
    export_formats=['html_artwork']
)
```

### 3. Verfügbare Export-Formate
- `html_artwork` - HTML mit Karten-Artworks ⭐ **NEU**
- `copy_paste` - Einfaches Text-Format
- `arena` - MTG Arena Format
- `mtgo` - Magic Online Format
- `cockatrice` - Cockatrice XML Format
- `tappedout` - TappedOut Format
- `archidekt` - Archidekt JSON Format
- `moxfield` - Moxfield Format

## 📁 Ausgabedateien

Die HTML-Dateien werden im `runs/` Verzeichnis gespeichert:
```
runs/
└── YYYYMMDD_HHMMSS/
    ├── deck_artwork_[algorithm].html    # HTML mit Artworks
    ├── deck_copy_paste_[algorithm].txt  # Text-Format
    └── ... (andere Export-Formate)
```

## 🎯 HTML-Features im Detail

### Responsive Design
```css
.cards-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 20px;
}

@media (max-width: 768px) {
    .cards-grid {
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    }
}
```

### Karten-Container
- **Hover-Effekte**: Karten heben sich um 5px an
- **Schatten**: Moderne Box-Shadows für Tiefe
- **Rundungen**: Abgerundete Ecken für modernes Aussehen

### Farb-Symbole
- **Weiß (W)**: #f8f6d8
- **Blau (U)**: #c1d7e9
- **Schwarz (B)**: #a69f9d
- **Rot (R)**: #e49977
- **Grün (G)**: #a3c095
- **Farblos**: #d4d4d4

### Scryfall Integration
```javascript
// Automatische Fehlerbehandlung für Bilder
img.addEventListener('error', function() {
    this.style.display = 'none';
    this.nextElementSibling.style.display = 'block';
});
```

## 🧪 Testing

### Automatische Tests
```bash
# Test der HTML-Artwork-Funktionalität
python test_artwork_export.py

# Umfassender Systemtest
python test_complete_system.py

# Test der Farbbeschränkungen
python test_color_constraints.py
```

### Manuelle Tests
1. Erstelle ein Deck mit `html_artwork` Export
2. Öffne die HTML-Datei im Browser
3. Überprüfe:
   - Alle Kartenbilder werden geladen
   - Farb-Symbole sind korrekt
   - Responsive Design funktioniert
   - Hover-Effekte funktionieren

## 🔧 Anpassungen

### CSS anpassen
Die HTML-Datei enthält eingebettetes CSS. Du kannst:
- Farben ändern
- Layout anpassen
- Neue Effekte hinzufügen

### Scryfall URLs anpassen
```python
# In deck_exporter.py
image_url = f"https://api.scryfall.com/cards/named?fuzzy={card_name.replace(' ', '+')}&format=image"
```

## 📱 Browser-Kompatibilität

- ✅ Chrome/Chromium
- ✅ Firefox
- ✅ Safari
- ✅ Edge
- ✅ Mobile Browser

## 🚨 Bekannte Einschränkungen

1. **Internetverbindung erforderlich**: Kartenbilder werden von Scryfall geladen
2. **Rate Limiting**: Scryfall hat API-Limits (aber für normale Nutzung ausreichend)
3. **Bildgröße**: Kartenbilder sind auf 223px Breite begrenzt für bessere Performance

## 🎨 Beispiele

### Mono-Red Aggro Deck
- 20 Karten
- Nur rote und farblose Karten
- Durchschnittsbewertung: 0.40/10
- Score: 0.4436

### Red-Black Midrange
- 30 Karten
- Rote, schwarze und farblose Karten
- Durchschnittsbewertung: 0.50/10
- Score: 0.4700

### Three-Color Control
- 35 Karten
- Rote, schwarze, grüne und farblose Karten
- Durchschnittsbewertung: 0.43/10
- Score: 0.4490

## 🔮 Zukünftige Verbesserungen

- [ ] Mana-Basis-Visualisierung
- [ ] Deck-Statistiken als Charts
- [ ] Export als PDF
- [ ] Druckoptimierte Version
- [ ] Dark/Light Mode Toggle
- [ ] Karten-Suche und Filterung
- [ ] Deck-Vergleichsansicht

---

**Erstellt**: 2025-06-22
**Version**: 1.0
**Autor**: Magic Optimizer Team 