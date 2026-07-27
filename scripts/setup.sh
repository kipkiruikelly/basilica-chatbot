#!/usr/bin/env bash
# ==============================================================================
# BASILICA — Modern Developer Bootstrap Script
# ==============================================================================
set -euo pipefail

# ANSI color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Initializing BASILICA Development Environment ===${NC}"

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 is not installed. Please install Python 3.12+ and try again.${NC}"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${GREEN}Creating Python virtual environment (venv)...${NC}"
    python3 -m venv venv
else
    echo -e "${YELLOW}Virtual environment already exists. Skipping creation.${NC}"
fi

# Activate virtual environment
echo -e "${GREEN}Activating virtual environment...${NC}"
source venv/bin/activate

# Upgrade pip
echo -e "${GREEN}Upgrading pip...${NC}"
pip install --upgrade pip

# Install dependencies
echo -e "${GREEN}Installing python requirements...${NC}"
if [ -f "backend/requirements.txt" ]; then
    pip install -r backend/requirements.txt
else
    echo -e "${RED}Error: backend/requirements.txt not found!${NC}"
    exit 1
fi

echo -e "\n${GREEN}✔ Installation completed successfully!${NC}"
echo -e "========================================================="
echo -e "${YELLOW}To start the local developer server, execute:${NC}"
echo -e "  source venv/bin/activate"
echo -e "  python -m backend.run"
echo -e "========================================================="
