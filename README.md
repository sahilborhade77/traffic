# Smart AI Traffic Intelligence System

A modular, AI-driven traffic management system for real-time monitoring, signal control, and prediction.

## 📁 Project Structure
```text
f:/traffic_project/
├── data/               # Datasets and sample videos
├── models/             # Pre-trained weights (YOLO, RL models)
├── src/                # Core Python Source Code
│   ├── vision/         # Vehicle detection and counting (Computer Vision)
│   ├── control/        # Traffic signal optimization (RL-based)
│   ├── prediction/     # Historical congestion forecasting (Time-series)
│   ├── dashboard/      # Web interface for visualization (Streamlit)
│   └── utils/          # Common helper and shared functions
├── tests/              # Unit and integration tests
├── venv/               # Virtual Environment (Generated)
├── requirements.txt    # list of free/open-source dependencies
└── README.md           # This file
```

## 🛠️ Setup Guide

To ensure a clean development environment, follow these steps:

### 1. Create a Virtual Environment
**Windows:**
```powershell
python -m venv venv
```

**macOS/Linux:**
```bash
python3 -m venv venv
```

### 2. Activate the Virtual Environment
**Windows (PowerShell):**
```powershell
.\venv\Scripts\activate
```

**macOS/Linux:**
```bash
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

## 🏃 How to Run
Currently, the system is in its scaffolding phase. You can launch the placeholder dashboard to verify setup:
```bash
streamlit run src/dashboard/app.py
```

## 📋 Module Descriptions
- **`vision`**: Responsible for processing camera feeds to detect vehicle types (cars, buses, bikes, etc.) and calculate real-time density.
- **`control`**: Implements reinforcement learning agents to intelligently adjust signal durations.
- **`prediction`**: Uses time-series models to predict upcoming traffic spikes based on historical patterns.
- **`dashboard`**: A user interface that integrates live data, predictions, and signal controls into a single view.

## 📝 Roadmap
1. [x] Project Initialization & Structure
2. [ ] Phase 1: Real-time Vehicle Detection (YOLO Integration)
3. [ ] Phase 2: Traffic Signal Logic
4. [ ] Phase 3: Dashboard Integration
5. [ ] Phase 4: Full System Simulation
