#!/bin/bash

# Complete Startup Script for Agentic RAG System

echo "🚀 Starting Agentic RAG Knowledge Assistant..."
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Kill existing processes
echo -e "${YELLOW}Cleaning up existing processes...${NC}"
pkill -f "uvicorn.*main:app" 2>/dev/null
pkill -f "vite" 2>/dev/null
sleep 2

# Check if .env exists
if [ ! -f "backend/.env" ]; then
    echo -e "${RED}❌ Error: backend/.env file not found!${NC}"
    echo "Please create it from backend/.env.example and add your API keys."
    exit 1
fi

# Start Backend
echo -e "${GREEN}📦 Starting Backend Server...${NC}"
cd backend
source venv/bin/activate
PYTHONPATH=. uvicorn main:app --host 0.0.0.0 --port 8000 --reload > ../backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
echo "Waiting for backend to start..."
sleep 5

# Check if backend is running
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend is running on http://localhost:8000${NC}"
else
    echo -e "${RED}❌ Backend failed to start. Check backend.log${NC}"
    exit 1
fi

# Start Frontend
echo -e "${GREEN}🎨 Starting Frontend...${NC}"
cd frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Wait for frontend to start
echo "Waiting for frontend to start..."
sleep 5

echo ""
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ System Started Successfully!${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo ""
echo "📍 Access Points:"
echo "   Backend API:  http://localhost:8000"
echo "   API Docs:     http://localhost:8000/docs"
echo "   Frontend:     http://localhost:5173"
echo ""
echo "📊 Logs:"
echo "   Backend:  tail -f backend.log"
echo "   Frontend: tail -f frontend.log"
echo ""
echo "🛑 To stop:"
echo "   pkill -f 'uvicorn.*main:app'"
echo "   pkill -f 'vite'"
echo ""
echo -e "${YELLOW}Opening frontend in browser...${NC}"
sleep 2
open http://localhost:5173 2>/dev/null || xdg-open http://localhost:5173 2>/dev/null || echo "Please open http://localhost:5173 in your browser"
