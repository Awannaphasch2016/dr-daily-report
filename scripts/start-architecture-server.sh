#!/bin/bash

# Start Architecture Server - Structurizr Lite with Hot Reload
# This script sets up the complete "vibe programming" environment

set -e

# Configuration
STRUCTURIZR_PORT=8081
ARCHITECTURE_DIR="./docs/architecture"
DSL_FILE="$ARCHITECTURE_DIR/workspace.dsl"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🏗️  Starting Daily Report Architecture Server${NC}"
echo "==========================================================="

# Validate prerequisites
echo -e "${YELLOW}📋 Checking prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed${NC}"
    exit 1
fi

# Use the appropriate Docker Compose command
DOCKER_COMPOSE="docker-compose"
if ! command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
fi

# Check if architecture directory exists
if [ ! -d "$ARCHITECTURE_DIR" ]; then
    echo -e "${RED}❌ Architecture directory not found: $ARCHITECTURE_DIR${NC}"
    exit 1
fi

# Check if DSL file exists
if [ ! -f "$DSL_FILE" ]; then
    echo -e "${RED}❌ DSL workspace file not found: $DSL_FILE${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All prerequisites satisfied${NC}"

# Check if port is already in use
if lsof -Pi :$STRUCTURIZR_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Port $STRUCTURIZR_PORT is already in use${NC}"
    echo -e "   Attempting to stop any existing containers..."
    $DOCKER_COMPOSE down 2>/dev/null || true
fi

# Start the services
echo -e "${BLUE}🚀 Starting Structurizr Lite...${NC}"
$DOCKER_COMPOSE up -d structurizr

# Wait for Structurizr to be ready
echo -e "${YELLOW}⏳ Waiting for Structurizr to start...${NC}"
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if curl -s -f http://localhost:$STRUCTURIZR_PORT > /dev/null 2>&1; then
        break
    fi
    sleep 1
    attempt=$((attempt + 1))
    echo -n "."
done

echo "" # New line after dots

if [ $attempt -eq $max_attempts ]; then
    echo -e "${RED}❌ Structurizr failed to start after 30 seconds${NC}"
    echo -e "   Check logs with: docker-compose logs structurizr"
    exit 1
fi

echo -e "${GREEN}✅ Structurizr Lite is running${NC}"

# Start file watcher in development mode
if [ "${1:-}" == "--dev" ] || [ "${ENVIRONMENT:-}" == "dev" ]; then
    echo -e "${BLUE}🔥 Starting hot reload file watcher...${NC}"
    $DOCKER_COMPOSE --profile dev up -d file-watcher
    echo -e "${GREEN}✅ File watcher started${NC}"
fi

# Display status and URLs
echo ""
echo -e "${GREEN}🎉 Architecture Server Ready!${NC}"
echo "==========================================================="
echo -e "${BLUE}📊 Structurizr Lite:${NC}     http://localhost:$STRUCTURIZR_PORT"
echo -e "${BLUE}📁 Architecture Files:${NC}   $ARCHITECTURE_DIR"
echo -e "${BLUE}🔧 Main DSL File:${NC}        $DSL_FILE"
echo ""
echo -e "${YELLOW}💡 Next Steps:${NC}"
echo "   1. Open http://localhost:$STRUCTURIZR_PORT in your browser"
echo "   2. Edit $DSL_FILE to modify diagrams"
echo "   3. Refresh browser to see changes"
echo ""
echo -e "${BLUE}🛠️  Management Commands:${NC}"
echo "   Stop server:     $DOCKER_COMPOSE down"
echo "   View logs:       $DOCKER_COMPOSE logs -f structurizr"
echo "   Restart:         $DOCKER_COMPOSE restart structurizr"
echo "   Full rebuild:    $DOCKER_COMPOSE down && $DOCKER_COMPOSE up -d"
echo ""
echo -e "${GREEN}🎯 Ready for 'vibe programming' - iterative architecture development!${NC}"

# Optional: Open browser automatically (macOS/Linux)
if command -v open &> /dev/null; then
    # macOS
    open "http://localhost:$STRUCTURIZR_PORT" 2>/dev/null || true
elif command -v xdg-open &> /dev/null; then
    # Linux
    xdg-open "http://localhost:$STRUCTURIZR_PORT" 2>/dev/null || true
fi