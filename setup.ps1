# ============================================================================
# Environment Setup Script for Traffic Intelligence System
# PowerShell Version for Windows
# ============================================================================
# Usage: .\setup.ps1 [--dev] [--gpu] [--miniconda]
# 
# Parameters:
#   --dev        : Install development dependencies
#   --gpu        : Install GPU-optimized dependencies
#   --miniconda  : Use Miniconda instead of venv

param(
    [switch]$dev = $false,
    [switch]$gpu = $false,
    [switch]$miniconda = $false,
    [switch]$help = $false
)

# Colors for output
$SuccessColor = "Green"
$ErrorColor = "Red"
$WarningColor = "Yellow"
$InfoColor = "Cyan"

# Banner
Write-Host "============================================================================" -ForegroundColor $InfoColor
Write-Host "Traffic Intelligence System - Environment Setup" -ForegroundColor $InfoColor
Write-Host "============================================================================" -ForegroundColor $InfoColor
Write-Host ""

# Help information
if ($help) {
    Write-Host "Usage: .\setup.ps1 [OPTIONS]" -ForegroundColor $InfoColor
    Write-Host ""
    Write-Host "Options:" -ForegroundColor $InfoColor
    Write-Host "  --dev          Install development dependencies (testing, linting, docs)" -ForegroundColor $InfoColor
    Write-Host "  --gpu          Install GPU-optimized CUDA files" -ForegroundColor $InfoColor
    Write-Host "  --miniconda    Use Miniconda instead of venv" -ForegroundColor $InfoColor
    Write-Host "  --help         Show this help message" -ForegroundColor $InfoColor
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor $InfoColor
    Write-Host "  .\setup.ps1                    # Basic setup with venv" -ForegroundColor $InfoColor
    Write-Host "  .\setup.ps1 --dev --gpu        # Full setup with conda and GPU support" -ForegroundColor $InfoColor
    exit 0
}

# Step 1: Check Python installation
Write-Host "[1/6] Checking Python installation..." -ForegroundColor $InfoColor

if ($miniconda) {
    # Check for conda
    $conda = cmd /c where conda 2>$null
    if (-not $conda) {
        Write-Host "ERROR: Miniconda not found. Please install Miniconda first." -ForegroundColor $ErrorColor
        Write-Host "Download from: https://docs.conda.io/projects/miniconda/en/latest/" -ForegroundColor $WarningColor
        exit 1
    }
    Write-Host "✓ Found Miniconda: $conda" -ForegroundColor $SuccessColor
} else {
    # Check for Python
    $python = cmd /c where python 2>$null
    if (-not $python) {
        Write-Host "ERROR: Python not found. Please install Python 3.10+ first." -ForegroundColor $ErrorColor
        exit 1
    }
    Write-Host "✓ Found Python: $python" -ForegroundColor $SuccessColor
    
    # Check Python version
    $version = python --version 2>&1
    Write-Host "  Version: $version" -ForegroundColor $SuccessColor
}

# Step 2: Create virtual environment or conda environment
Write-Host ""
Write-Host "[2/6] Setting up environment..." -ForegroundColor $InfoColor

if ($miniconda) {
    Write-Host "Creating conda environment 'traffic'..." -ForegroundColor $InfoColor
    
    # Create conda environment
    conda create -y -n traffic python=3.10
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to create conda environment" -ForegroundColor $ErrorColor
        exit 1
    }
    
    # Activate conda environment
    conda activate traffic
    Write-Host "✓ Conda environment created and activated" -ForegroundColor $SuccessColor
} else {
    Write-Host "Creating Python virtual environment 'venv'..." -ForegroundColor $InfoColor
    
    # Create venv
    python -m venv venv
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to create virtual environment" -ForegroundColor $ErrorColor
        exit 1
    }
    
    # Activate venv
    & .\venv\Scripts\Activate.ps1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to activate virtual environment" -ForegroundColor $ErrorColor
        exit 1
    }
    
    Write-Host "✓ Virtual environment created and activated" -ForegroundColor $SuccessColor
}

# Step 3: Upgrade pip
Write-Host ""
Write-Host "[3/6] Upgrading pip and setuptools..." -ForegroundColor $InfoColor

python -m pip install --upgrade pip setuptools wheel
if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: pip upgrade had issues, continuing anyway..." -ForegroundColor $WarningColor
}

Write-Host "✓ pip upgraded" -ForegroundColor $SuccessColor

# Step 4: Install dependencies
Write-Host ""
Write-Host "[4/6] Installing Python dependencies..." -ForegroundColor $InfoColor

$requirements_file = "requirements.txt"
if ($dev) {
    $requirements_file = "requirements-dev.txt"
    Write-Host "Installing with development dependencies..." -ForegroundColor $InfoColor
} else {
    Write-Host "Installing production dependencies..." -ForegroundColor $InfoColor
}

pip install -r $requirements_file

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to install dependencies" -ForegroundColor $ErrorColor
    exit 1
}

Write-Host "✓ Dependencies installed" -ForegroundColor $SuccessColor

# Step 5: Download models
Write-Host ""
Write-Host "[5/6] Downloading required models..." -ForegroundColor $InfoColor

# Create models directory
if (-not (Test-Path "models")) {
    New-Item -ItemType Directory -Path "models" | Out-Null
    Write-Host "Created models/ directory" -ForegroundColor $SuccessColor
}

# Download YOLOv8 models
Write-Host "Downloading YOLOv8 models (nano and small)..." -ForegroundColor $InfoColor

python -c "from ultralytics import YOLO; YOLO('yolov8n.pt'); YOLO('yolov8s.pt')"

if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: Model download had issues, you may need to download manually" -ForegroundColor $WarningColor
} else {
    Write-Host "✓ Models downloaded to ~/.cache/yolo/" -ForegroundColor $SuccessColor
}

# Step 6: Setup environment variables
Write-Host ""
Write-Host "[6/6] Creating .env configuration file..." -ForegroundColor $InfoColor

if (-not (Test-Path ".env")) {
    @"
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
"@ | Out-File -FilePath ".env" -Encoding UTF8
    
    Write-Host "✓ Created .env file with default configuration" -ForegroundColor $SuccessColor
    Write-Host "  Edit .env to configure your settings" -ForegroundColor $WarningColor
} else {
    Write-Host "✓ .env already exists" -ForegroundColor $SuccessColor
}

# Completion
Write-Host ""
Write-Host "============================================================================" -ForegroundColor $SuccessColor
Write-Host "✓ Setup Complete!" -ForegroundColor $SuccessColor
Write-Host "============================================================================" -ForegroundColor $SuccessColor
Write-Host ""

Write-Host "Next steps:" -ForegroundColor $InfoColor
if ($miniconda) {
    Write-Host "1. Activate environment: conda activate traffic" -ForegroundColor $InfoColor
} else {
    Write-Host "1. Activate environment: .\venv\Scripts\Activate.ps1" -ForegroundColor $InfoColor
}
Write-Host "2. Edit .env file with your configuration" -ForegroundColor $InfoColor
Write-Host "3. Run the application:" -ForegroundColor $InfoColor
Write-Host "   - Main pipeline: python main_pipeline.py" -ForegroundColor $InfoColor
Write-Host "   - API server: python -m uvicorn src.dashboard.api:app --reload" -ForegroundColor $InfoColor
Write-Host "   - Dashboard: streamlit run src/dashboard/app.py" -ForegroundColor $InfoColor
Write-Host ""
Write-Host "For more information, see README.md" -ForegroundColor $InfoColor
