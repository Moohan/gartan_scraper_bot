#!/bin/bash
# Development setup script for Gartan Scraper Bot

set -e

echo "🚀 Setting up Gartan Scraper Bot development environment..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.13"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 13) else 1)" 2>/dev/null; then
    echo "❌ Python 3.13+ required. Found: $python_version"
    echo "Please install Python 3.13 or later"
    exit 1
fi

echo "✅ Python version: $(python3 --version)"

# Install dependencies
echo "📦 Installing Python dependencies..."
python3 -m pip install --upgrade pip
pip install -r requirements.txt

# Install development dependencies
echo "🛠️  Installing development dependencies..."
pip install pytest pytest-cov black isort flake8 mypy bandit safety pip-audit

# Set up git hooks
echo "🔧 Setting up git hooks..."
if [ -f ".githooks/setup-hooks.sh" ]; then
    chmod +x .githooks/setup-hooks.sh
    ./.githooks/setup-hooks.sh
else
    echo "⚠️  Git hooks setup script not found"
fi

# Create .env.example if it doesn't exist
if [ ! -f ".env.example" ]; then
    echo "📝 Creating .env.example..."
    cat > .env.example << EOF
# Gartan system credentials
GARTAN_USERNAME=your_username_here
GARTAN_PASSWORD=your_password_here

# Optional configuration
# LOG_LEVEL=INFO
# MAX_WORKERS=4
# CACHE_DURATION_MINUTES=15
# PORT=5000
# FLASK_DEBUG=false
EOF
fi

# Check if .env exists, create if not
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please update .env with your actual credentials"
fi

# Run initial tests
echo "🧪 Running initial tests..."
python -m pytest tests/ -v

# Check code quality
echo "🎨 Running code quality checks..."
echo "  - Black formatting..."
black --check . || {
    echo "💡 Run 'black .' to format code"
}

echo "  - Import sorting..."
isort --check-only . || {
    echo "💡 Run 'isort .' to sort imports"
}

echo "  - Flake8 linting..."
flake8 . || {
    echo "💡 Fix linting issues reported above"
}

echo ""
echo "✅ Development environment setup complete!"
echo ""
echo "🎯 Next steps:"
echo "  1. Update .env with your Gartan credentials"
echo "  2. Run 'python run_bot.py --max-days 1' to test data collection"
echo "  3. Run 'python api_server.py' to start the API server"
echo "  4. Visit http://localhost:5000/health to check API status"
echo ""
echo "🔧 Development commands:"
echo "  - Run tests: pytest tests/"
echo "  - Format code: black ."
echo "  - Sort imports: isort ."
echo "  - Check linting: flake8 ."
echo "  - Security scan: bandit -r ."
echo "  - Check dependencies: safety check"
