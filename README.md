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