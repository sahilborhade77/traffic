#!/bin/bash
# ============================================================================
# Environment Setup Script for Traffic Intelligence System
# Bash Version for Linux/macOS
# ============================================================================
# Usage: bash setup.sh [--dev] [--gpu] [--conda]
#
# Parameters:
#   --dev        Install development dependencies
#   --gpu        Install GPU-optimized dependencies
#   --conda      Use conda instead of venv

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;36m'
NC='\033[0m'  # No Color

# Parse arguments
DEV=false
GPU=false
USE_CONDA=false
HELP=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --dev)
            DEV=true
            shift
            ;;
        --gpu)
            GPU=true
            shift
            ;;
        --conda)
            USE_CONDA=true
            shift
            ;;
        --help)
            HELP=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            HELP=true
            shift
            ;;
    esac
done

# Help function
show_help() {
    echo -e "${BLUE}============================================================================${NC}"
    echo -e "${BLUE}Traffic Intelligence System - Environment Setup${NC}"
    echo -e "${BLUE}============================================================================${NC}"
    echo ""
    echo -e "${BLUE}Usage:${NC} bash setup.sh [OPTIONS]"
    echo ""
    echo -e "${BLUE}Options:${NC}"
    echo "  --dev         Install development dependencies (testing, linting, docs)"
    echo "  --gpu         Install GPU-optimized CUDA files"
    echo "  --conda       Use conda instead of venv (requires conda/miniconda)"
    echo "  --help        Show this help message"
    echo ""
    echo -e "${BLUE}Examples:${NC}"
    echo "  bash setup.sh                 # Basic setup with venv"
    echo "  bash setup.sh --dev --gpu     # Full setup with conda and GPU support"
    echo ""
}

if [ "$HELP" = true ]; then
    show_help
    exit 0
fi

# Banner
echo -e "${BLUE}============================================================================${NC}"
echo -e "${BLUE}Traffic Intelligence System - Environment Setup${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""

# Step 1: Check Python installation
echo -e "${BLUE}[1/6] Checking Python installation...${NC}"

if [ "$USE_CONDA" = true ]; then
    # Check for conda
    if ! command -v conda &> /dev/null; then
        echo -e "${RED}ERROR: conda not found. Please install Miniconda/Anaconda first.${NC}"
        echo -e "${YELLOW}Download from: https://docs.conda.io/projects/miniconda/en/latest/${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Found conda$(conda --version)${NC}"
else
    # Check for Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}ERROR: Python 3 not found. Please install Python 3.10+ first.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Found Python $(python3 --version)${NC}"
fi

# Step 2: Create virtual environment or conda environment
echo ""
echo -e "${BLUE}[2/6] Setting up environment...${NC}"

if [ "$USE_CONDA" = true ]; then
    echo -e "${BLUE}Creating conda environment 'traffic'...${NC}"
    
    conda create -y -n traffic python=3.10
    
    # Activate conda environment
    eval "$(conda shell.bash hook)"
    conda activate traffic
    
    echo -e "${GREEN}✓ Conda environment created and activated${NC}"
else
    echo -e "${BLUE}Creating Python virtual environment 'venv'...${NC}"
    
    python3 -m venv venv
    
    # Activate venv
    source venv/bin/activate
    
    echo -e "${GREEN}✓ Virtual environment created and activated${NC}"
fi

# Step 3: Upgrade pip and tools
echo ""
echo -e "${BLUE}[3/6] Upgrading pip and setuptools...${NC}"

python -m pip install --upgrade pip setuptools wheel

echo -e "${GREEN}✓ pip upgraded${NC}"

# Step 4: Install dependencies
echo ""
echo -e "${BLUE}[4/6] Installing Python dependencies...${NC}"

if [ "$DEV" = true ]; then
    echo -e "${BLUE}Installing with development dependencies...${NC}"
    pip install -r requirements-dev.txt
else
    echo -e "${BLUE}Installing production dependencies...${NC}"
    pip install -r requirements.txt
fi

echo -e "${GREEN}✓ Dependencies installed${NC}"

# Step 5: Download models
echo ""
echo -e "${BLUE}[5/6] Downloading required models...${NC}"

# Create models directory
mkdir -p models
echo -e "${GREEN}Created models/ directory${NC}"

# Download YOLOv8 models
echo -e "${BLUE}Downloading YOLOv8 models (nano and small)...${NC}"

python -c "from ultralytics import YOLO; YOLO('yolov8n.pt'); YOLO('yolov8s.pt')" || {
    echo -e "${YELLOW}WARNING: Model download had issues, you may need to download manually${NC}"
}

echo -e "${GREEN}✓ Models downloaded to ~/.cache/yolo/${NC}"

# Step 6: Setup environment variables
echo ""
echo -e "${BLUE}[6/6] Creating .env configuration file...${NC}"

if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
# ============================================================================
# Traffic Intelligence System - Environment Configuration
# ============================================================================

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Database Configuration
DATABASE_URL=sqlite:///./traffic.db
# For PostgreSQL: DATABASE_URL=postgresql://user:password@localhost/traffic_db

# Redis Cache Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# GPU Configuration
CUDA_VISIBLE_DEVICES=0
DEVICE=cuda  # or 'cpu' for CPU-only

# Logging Configuration
LOG_LEVEL=INFO
LOG_DIR=logs

# Model Configuration
MODEL_YOLO=yolov8n.pt
CONFIDENCE_THRESHOLD=0.5
NMS_THRESHOLD=0.45

# Camera Configuration (example RTSP streams)
CAMERA_NORTH_URL=rtsp://192.168.1.100:554/stream
CAMERA_SOUTH_URL=rtsp://192.168.1.101:554/stream

# Development
DEBUG=False
RELOAD=False
EOF
    
    echo -e "${GREEN}✓ Created .env file with default configuration${NC}"
    echo -e "${YELLOW}  Edit .env to configure your settings${NC}"
else
    echo -e "${GREEN}✓ .env already exists${NC}"
fi

# Completion
echo ""
echo -e "${BLUE}============================================================================${NC}"
echo -e "${GREEN}✓ Setup Complete!${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""

echo -e "${BLUE}Next steps:${NC}"

if [ "$USE_CONDA" = true ]; then
    echo "1. Activate environment: conda activate traffic"
else
    echo "1. Activate environment: source venv/bin/activate"
fi

echo "2. Edit .env file with your configuration"
echo "3. Run the application:"
echo "   - Main pipeline: python main_pipeline.py"
echo "   - API server: python -m uvicorn src.dashboard.api:app --reload"
echo "   - Dashboard: streamlit run src/dashboard/app.py"
echo ""
echo -e "${BLUE}For more information, see README.md${NC}"
