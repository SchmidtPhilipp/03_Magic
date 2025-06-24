# MTG Sealed Deck Optimizer

A powerful web application for optimizing Magic: The Gathering sealed deck formats using advanced algorithms and machine learning techniques.

## 🎯 Features

### **Advanced Optimization Algorithms**
- **Greedy Algorithm**: Fast optimization for quick results
- **Genetic Algorithm**: Evolutionary approach for complex deck building
- **Simulated Annealing**: Probabilistic optimization for global maxima

### **Professional Web Interface**
- **Modern UI**: Beautiful, responsive design with gradient themes
- **Real-time Optimization**: Live terminal output and progress tracking
- **Interactive Deck Visualization**: Card images with adjustable sizing
- **Local Image Caching**: Fast loading with cached card images from Scryfall

### **Smart Deck Building**
- **Color Constraint Optimization**: Automatic color selection based on card ratings
- **Mana Curve Analysis**: Professional visualization with integrated color distribution
- **Land Ratio Management**: Configurable land counts (14-24 lands)
- **Multiple Export Formats**: MTG Arena, MTGO, and HTML with artwork

### **Data Management**
- **CSV Import**: Support for custom card collections and ratings
- **Scryfall Integration**: Automatic card validation and image fetching
- **Rating Systems**: Advanced scoring algorithms for card evaluation

## 🧮 Optimization Algorithms

### **1. Greedy Algorithm**
The greedy algorithm makes locally optimal choices at each step to construct the deck.

**Mathematical Formulation:**
```
For each card c in collection C:
    score(c) = rating(c) - λ × color_penalty(c, selected_colors)
    
    if score(c) > best_score and constraints_satisfied(c):
        add_card_to_deck(c)
        update_selected_colors(c)
```

**Algorithm Steps:**
1. **Color Selection**: Choose the best color combination based on card ratings
2. **Card Selection**: Iteratively add the highest-scoring card that satisfies constraints
3. **Land Distribution**: Calculate optimal land ratios based on mana curve

**Time Complexity**: O(n × m) where n = number of cards, m = number of colors
**Space Complexity**: O(n)

### **2. Genetic Algorithm**
An evolutionary approach that simulates natural selection to find optimal deck configurations.

**Mathematical Formulation:**
```
Population P = {deck₁, deck₂, ..., deckₙ}
Fitness(deck) = Σ rating(cardᵢ) - λ × color_penalty(deck)

For generation g = 1 to max_generations:
    P' = Selection(P)           # Tournament selection
    P'' = Crossover(P')         # Single-point crossover
    P''' = Mutation(P'')        # Random card swaps
    P = P''' ∪ Elitism(P)       # Keep best individuals
```

**Genetic Operators:**
- **Selection**: Tournament selection with size 3
- **Crossover**: Single-point crossover with probability 0.8
- **Mutation**: Random card replacement with probability 0.1
- **Elitism**: Preserve top 10% of population

**Fitness Function:**
```
Fitness(deck) = Σᵢ rating(cardᵢ) - λ × Σᵢⱼ color_penalty(cardᵢ, cardⱼ)
```

**Time Complexity**: O(g × p × n) where g = generations, p = population size
**Space Complexity**: O(p × n)

### **3. Simulated Annealing**
A probabilistic optimization technique inspired by metallurgy, using temperature-controlled random walks.

**Mathematical Formulation:**
```
Temperature T = T₀
Current solution S = initial_deck
Best solution S* = S

While T > T_min:
    For i = 1 to iterations_per_temp:
        S' = neighbor(S)        # Random card swap
        ΔE = fitness(S') - fitness(S)
        
        if ΔE > 0 or random() < exp(-ΔE/T):
            S = S'
            if fitness(S) > fitness(S*):
                S* = S
    
    T = α × T                   # Cooling schedule
```

**Cooling Schedule:**
```
T(t) = T₀ × α^t
where α = 0.95 (cooling rate)
```

**Acceptance Probability:**
```
P(accept) = min(1, exp(-ΔE/T))
```

**Neighborhood Function:**
- **Card Swap**: Randomly replace one card with another from collection
- **Color Adjustment**: Modify color distribution while maintaining constraints

**Time Complexity**: O(iterations × temperature_steps)
**Space Complexity**: O(n)

### **4. Color Constraint System**
A sophisticated penalty system that encourages optimal color distribution.

**Color Penalty Function:**
```
color_penalty(deck) = Σᵢⱼ penalty(cardᵢ, cardⱼ)

where penalty(card₁, card₂) = {
    0 if colors(card₁) ∩ colors(card₂) ≠ ∅
    λ × distance(colors(card₁), colors(card₂)) otherwise
}
```

**Color Distance Metric:**
```
distance(color₁, color₂) = |color₁ - color₂| mod 5
```

**Lambda Parameter (λ):**
- **Low λ (0.1-0.5)**: Soft color constraints, allows more flexibility
- **High λ (1.0-2.0)**: Strict color constraints, enforces color coherence

### **5. Land Optimization**
Intelligent land distribution based on mana curve analysis.

**Land Calculation:**
```
total_lands = deck_size - spell_count
color_lands = Σᵢ (color_ratioᵢ × total_lands)

where color_ratioᵢ = Σᵢ mana_symbols(card) / Σ total_mana_symbols
```

**Mana Curve Analysis:**
```
curve_score = Σᵢ (curve_weightᵢ × cards_at_cmcᵢ)
where curve_weight = [0.1, 0.2, 0.3, 0.2, 0.1, 0.05, 0.05] for CMC 1-7+
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip package manager

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd mtg-sealed-deck-optimizer
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python web_app.py
   ```

4. **Open your browser**
   Navigate to `http://localhost:5050`

## 📊 Usage

### **1. Upload Your Collection**
- Prepare a CSV file with columns: `name`, `rating`, `colors`, `cmc`, `type`
- Upload via the web interface or use the default FinalFantasy.csv

### **2. Configure Settings**
- **Target Colors**: Number of colors for the optimizer to use (1-5)
- **Deck Size**: Total deck size (20-60 cards)
- **Number of Lands**: Land count (14-24)
- **Algorithm**: Choose optimization method
- **Lambda Penalty**: Color constraint strength (for advanced algorithms)

### **3. Run Optimization**
- Click "Start Optimization" to begin
- Monitor progress in real-time
- View results in the deck visualization

### **4. Export Your Deck**
- Download in MTG Arena format
- Export as HTML with artwork
- Get MTGO-compatible list

## 🏗️ Architecture

### **Backend Components**
- **Deck Builder**: Core optimization engine
- **Card Validator**: Scryfall API integration
- **Export System**: Multiple format support
- **Image Cache**: Local card image storage

### **Frontend Features**
- **Flask Web Server**: RESTful API endpoints
- **Real-time Updates**: WebSocket-like polling
- **Responsive Design**: Bootstrap-based UI
- **Interactive Elements**: Dynamic card sizing and visualization

### **Optimization Engine**
- **Multi-algorithm Support**: Greedy, Genetic, Simulated Annealing
- **Color Constraint Handling**: Dynamic color filtering
- **Land Calculation**: Optimal land distribution
- **Scoring System**: Advanced card evaluation metrics

## 📁 Project Structure

```
mtg-sealed-deck-optimizer/
├── src/magic_optimizer/          # Core optimization engine
│   ├── deck_builder.py          # Main deck building logic
│   ├── optimizer.py             # Algorithm implementations
│   ├── validator.py             # Card validation
│   └── exporters/               # Export format handlers
├── static/                      # Web assets
│   ├── css/style.css           # Styling
│   ├── js/app.js               # Frontend logic
│   └── card_cache/             # Cached card images
├── templates/                   # HTML templates
├── data/                       # Sample data
├── tests/                      # Test suite
├── web_app.py                  # Flask application
└── requirements.txt            # Python dependencies
```

## 🧪 Testing

Run the test suite to verify functionality:

```bash
python -m pytest tests/
```

## 🔧 Configuration

### **Environment Variables**
- `FLASK_ENV`: Set to 'development' for debug mode
- `PORT`: Custom port (default: 5050)

### **Customization**
- Modify `static/css/style.css` for UI changes
- Update `src/magic_optimizer/` for algorithm tuning
- Add new export formats in `exporters/`

## 📈 Performance

- **Optimization Speed**: 5-10 seconds for typical collections
- **Image Caching**: 90%+ reduction in load times after initial cache
- **Memory Usage**: Efficient algorithms for large collections
- **Scalability**: Handles collections up to 1000+ cards

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Scryfall API**: Card data and images
- **Bootstrap**: UI framework
- **Flask**: Web framework
- **Magic: The Gathering**: Game mechanics and concepts

## 📞 Support

For issues, questions, or contributions:
- Create an issue on GitHub
- Check the documentation
- Review the test suite for examples

---

**Version**: 1.0  
**Last Updated**: June 2025  
**Author**: MTG Sealed Deck Optimizer Team 