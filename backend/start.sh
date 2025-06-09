#!/bin/bash

# Crogia Backend Startup Script
echo "🚀 Starting Crogia FastAPI Backend..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚙️  Creating .env file from template..."
    cp env.example .env
    echo "📝 Please edit .env file with your configuration before running the server"
    echo "   Especially set your OPENAI_API_KEY"
fi

# Start the server
echo "🌟 Starting FastAPI server..."
echo "   API Documentation: http://localhost:8000/docs"
echo "   Health Check: http://localhost:8000/api/health"
echo ""

python run.py 