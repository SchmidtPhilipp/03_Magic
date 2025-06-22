# Sealed Limited Optimizer

A powerful web application for optimizing Magic: The Gathering sealed deck builds using advanced algorithms and real-time analysis.

## Features

- **Multiple Optimization Algorithms**: Genetic Algorithm, Simulated Annealing, and Greedy approaches
- **Dynamic Color Constraints**: Intelligent color selection with penalty-based constraints
- **Real-time Web Interface**: Modern, responsive UI with live optimization output
- **Deck Visualization**: Visual card display with artwork from Scryfall API
- **Multiple Export Formats**: MTG Arena, MTGO, and HTML with artwork
- **Land Calculation**: Automatic optimal land distribution based on deck composition
- **Collection Management**: Upload and manage your card collections via CSV

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the Web Application**:
   ```bash
   python web_app.py
   ```

3. **Open in Browser**:
   Navigate to `http://localhost:5050`

4. **Upload Collection**:
   - Use the provided `FinalFantasy.csv` for testing
   - Or upload your own collection in CSV format

5. **Configure Settings**:
   - Set maximum colors (1-5)
   - Choose deck size and land ratio
   - Select optimization algorithm
   - Adjust color penalty strength (for Genetic/Simulated Annealing)

6. **Optimize and Export**:
   - Click "Start Optimization"
   - View results in real-time
   - Download deck in your preferred format

## Algorithm Details

### Genetic Algorithm
- Population-based optimization with crossover and mutation
- Configurable color penalty constraints
- Best for complex deck optimization scenarios

### Simulated Annealing
- Temperature-based optimization with gradual cooling
- Effective for finding global optima
- Good balance of speed and quality

### Greedy Algorithm
- Fast, deterministic approach
- Strict color compatibility enforcement
- Ideal for quick deck building

## File Structure

```
├── web_app.py                 # Flask web application
├── main_organized.py          # Command-line interface
├── requirements.txt           # Python dependencies
├── data/
│   ├── collections/           # Card collections
│   └── ratings/              # Card ratings
├── src/
│   └── magic_optimizer/      # Core optimization engine
├── templates/                # HTML templates
├── static/                   # CSS, JS, and static assets
└── tests/                    # Test suite
```

## Configuration

### CSV Format
Your collection CSV should have the following columns:
- `Card Name`: Exact card name
- `Rating`: Card rating (0-10 scale)

### Algorithm Parameters
- **Max Colors**: Maximum number of colors in the deck
- **Deck Size**: Total deck size (including lands)
- **Land Ratio**: Percentage of lands in the deck (20-50%)
- **Lambda Penalty**: Color constraint strength (0.1-5.0)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Scryfall API for card data and artwork
- Magic: The Gathering community for ratings and feedback 