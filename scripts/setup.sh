#!/bin/bash

# Setup script for Agentic RAG Knowledge Assistant
# This script sets up the development environment

set -e

echo "=========================================="
echo "Agentic RAG Knowledge Assistant Setup"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "   Python version: $python_version"

# Check Node.js version
echo "📋 Checking Node.js version..."
if command -v node &> /dev/null; then
    node_version=$(node --version)
    echo "   Node.js version: $node_version"
else
    echo "   ⚠️  Node.js not found. Please install Node.js 18+"
    exit 1
fi

# Backend setup
echo ""
echo "🔧 Setting up backend..."
cd backend

if [ ! -d "venv" ]; then
    echo "   Creating Python virtual environment..."
    python3 -m venv venv
fi

echo "   Activating virtual environment..."
source venv/bin/activate  # On Windows: venv\Scripts\activate

echo "   Installing Python dependencies..."
pip install --upgrade pip
pip install -r ../requirements.txt

echo "   ✅ Backend setup complete!"

# Check for .env file
if [ ! -f ".env" ]; then
    echo ""
    echo "   ⚠️  .env file not found!"
    echo "   Please create .env file with your API keys:"
    echo "   - OPENAI_API_KEY"
    echo "   - PINECONE_API_KEY"
    echo ""
    echo "   You can copy .env.example as a template."
fi

cd ..

# Frontend setup
echo ""
echo "🔧 Setting up frontend..."
cd frontend

if [ ! -d "node_modules" ]; then
    echo "   Installing Node.js dependencies..."
    npm install
fi

echo "   ✅ Frontend setup complete!"
cd ..

# Create data directories if they don't exist
echo ""
echo "📁 Creating data directories..."
mkdir -p data/raw
mkdir -p data/processed

echo ""
echo "=========================================="
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Add your documents (PDF, TXT, MD) to data/raw/"
echo "2. Create backend/.env with your API keys"
echo "3. Run data ingestion:"
echo "   cd backend && python scripts/ingest.py"
echo "4. Start the backend:"
echo "   cd backend && python main.py"
echo "5. Start the frontend (in new terminal):"
echo "   cd frontend && npm run dev"
echo ""
echo "Or use Docker:"
echo "   docker-compose up --build"
echo ""
