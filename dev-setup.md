# Docker Development Setup

## Quick Start

### 1. Start Development Environment
```bash
docker-compose up -d mtg-dev
```

### 2. Enter Development Container
```bash
docker-compose exec mtg-dev bash
```

### 3. Run the Application
Inside the container:
```bash
python web_app.py
```

### 4. Run Tests
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/test_17lands_integration.py -v

# Run with coverage
python -m pytest tests/ --cov=src -v
```

## Development Workflow

### Start Development Session
```bash
# Build and start the development container
docker-compose up -d mtg-dev

# Enter the container
docker-compose exec mtg-dev bash
```

### Inside the Container
- All your code changes are immediately reflected (volume mounting)
- You can run any Python commands, tests, etc.
- The container has all development tools installed (vim, git, etc.)

### Run the Web App
```bash
# Start Flask app
python web_app.py

# Or with debug mode
FLASK_DEBUG=1 python web_app.py
```

### Code Quality Tools
```bash
# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

### Stop Development
```bash
# Exit container
exit

# Stop container
docker-compose down
```

## Useful Commands

### Rebuild Container (after requirements.txt changes)
```bash
docker-compose build mtg-dev
docker-compose up -d mtg-dev
```

### View Logs
```bash
docker-compose logs mtg-dev
```

### Run Tests Only
```bash
docker-compose --profile test up mtg-test
```

### Clean Up
```bash
# Remove containers and volumes
docker-compose down -v

# Remove images
docker rmi mtg-optimizer_mtg-dev
```

## Benefits

1. **Isolated Environment**: No conflicts with your system Python
2. **Reproducible**: Same environment for all developers
3. **Live Development**: Code changes are immediately reflected
4. **All Tools Included**: Git, editors, testing tools, etc.
5. **Easy Cleanup**: Just remove the container to start fresh 