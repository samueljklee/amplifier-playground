#!/bin/bash
# Amplifier Playground - Development Server Script
# Usage: ./scripts/dev.sh [start|stop|restart]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKEND_PORT=8000
FRONTEND_PORT=5173

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

kill_port() {
    local port=$1
    local pids=$(lsof -ti :$port 2>/dev/null)
    if [ -n "$pids" ]; then
        echo -e "${YELLOW}Killing processes on port $port: $pids${NC}"
        echo "$pids" | xargs kill -9 2>/dev/null
        sleep 1
    fi
}

stop_servers() {
    echo -e "${YELLOW}Stopping servers...${NC}"
    kill_port $BACKEND_PORT
    kill_port $FRONTEND_PORT
    echo -e "${GREEN}Servers stopped${NC}"
}

start_backend() {
    echo -e "${GREEN}Starting backend on port $BACKEND_PORT...${NC}"
    cd "$PROJECT_DIR"
    uv run uvicorn amplifier_playground.web.app:app --reload --port $BACKEND_PORT &
}

start_frontend() {
    echo -e "${GREEN}Starting frontend on port $FRONTEND_PORT...${NC}"
    cd "$PROJECT_DIR/frontend"
    npm run dev &
}

start_servers() {
    # Clear ports first
    kill_port $BACKEND_PORT
    kill_port $FRONTEND_PORT

    start_backend
    sleep 2
    start_frontend

    echo ""
    echo -e "${GREEN}======================================${NC}"
    echo -e "${GREEN}Amplifier Playground is running!${NC}"
    echo -e "${GREEN}======================================${NC}"
    echo -e "Backend:  ${YELLOW}http://localhost:$BACKEND_PORT${NC}"
    echo -e "Frontend: ${YELLOW}http://localhost:$FRONTEND_PORT${NC}"
    echo -e "API Docs: ${YELLOW}http://localhost:$BACKEND_PORT/docs${NC}"
    echo ""
    echo -e "Press Ctrl+C to stop all servers"

    # Wait for any background job to finish (keeps script running)
    wait
}

case "${1:-start}" in
    start)
        start_servers
        ;;
    stop)
        stop_servers
        ;;
    restart)
        stop_servers
        sleep 1
        start_servers
        ;;
    *)
        echo "Usage: $0 [start|stop|restart]"
        exit 1
        ;;
esac
