#!/bin/bash

# Start the FastAPI backend server

cd "$(dirname "$0")"
source venv/bin/activate

echo "🚀 Starting Agentic RAG Backend Server..."
echo "📍 API will be available at: http://localhost:8000"
echo "📚 API Docs will be at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python main.py
