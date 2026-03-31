# Smart AI Traffic Intelligence System 🚦

A full-stack, modular, AI-driven urban traffic management system. This project integrates Computer Vision, Reinforcement Learning, and Time-Series Forecasting into a unified control dashboard.


---

## 🏗️ 5.2 System Architecture

Your Smart AI Traffic System is built on a 5-layer industrial framework:

```text
┌─────────────────────────────────────────────────────────────┐
│                    SMART AI TRAFFIC SYSTEM                  │
└─────────────────────────────────────────────────────────────┘

┌───────────────────┐         ┌──────────────────────────────┐
│  1. CAMERA LAYER  │────────▶│   2. DETECTION & TRACKING    │
│                   │         │                              │
│ • 4K IP Cameras   │         │ • YOLOv8 Object Detection    │
│ • Thermal Sensors │         │ • DeepSORT Tracking          │
│ • LiDAR (Support) │         │ • Vehicle Classification     │
│ • PTZ Controls    │         │ • Speed & Queue Estimation   │
└───────────────────┘         └──────────────────────────────┘
         │                                  │
         │                                  ▼
         │                    ┌──────────────────────────────┐
         │                    │   3. ANALYTICS & PREDICTION  │
         │                    │                              │
         │                    │ • LSTM Flow Prediction       │
         │                    │ • Congestion Level Detection │
         │                    │ • Incident/Accident Detection│
         │                    │ • Weather/Env Adaptation     │
         └───────────────────┘└──────────────────────────────┘
         │                                  │
         ▼                                  ▼
┌───────────────────────────────────────────────────────────┐
│                  4. DECISION & CONTROL LAYER               │
│                                                            │
│  ┌──────────────────┐       ┌──────────────────────────┐ │
│  │  RL SIGNAL       │       │  EMERGENCY RESPONSE      │ │
│  │  CONTROLLER      │       │  SYSTEM                  │ │
│  │                  │       │                          │ │
│  │ • PPO RL Agent   │       │ • Siren/Light Detection  │ │
│  │ • Phase Optimizer│       │ • Green Wave 'Corridor'  │ │
│  └──────────────────┘       └──────────────────────────┘ │
└───────────────────────────────────────────────────────────┘
                              │
                              ▼
         ┌────────────────────────────────────────┐
         │      5. TRAFFIC LIGHT CONTROLLERS      │
         │                                        │
         │  • NEMA / NTCIP Protcol Integration    │
         │  • Physical Hardware Interface (GPIO)  │
         │  • Safe Yellow/All-Red Clearance       │
         └────────────────────────────────────────┘
                              │
                              ▼
         ┌────────────────────────────────────────┐
         │         USER INTERFACE LAYER           │
         │                                        │
         │  • Real-time WebSocket Dashboard       │
         │  • Mobile Alert Apps                   │
         │  • Navigation Service Integration      │
         └────────────────────────────────────────┘
```

---

## 🚀 Getting Started (Professional Guide)

### 1. Prerequisites
- **Python 3.10+**: (Recommend using `conda` or `pyenv`)
- **NVIDIA GPU (Optional but Recommended)**: For real-time inference (>30 FPS)
- **Docker & Docker-Compose**: (For containerized deployment)

### 2. Local Installation
Follow these exact steps to prepare your environment:

```powershell
# 1. Clone & Enter Repository
# git clone https://github.com/sahilborhade77/traffic.git
# cd traffic

# 2. Setup Virtual Environment
python -m venv venv
.\venv\Scripts\activate

# 3. Install Pinned Dependencies
pip install -r requirements.txt
```

### 3. Quick Start (Three Modes)

#### **A. Developer Mode (Local Execution)**
Run the full AI pipeline with the integrated dashboard:
```powershell
python main_pipeline.py
```

#### **B. Production Mode (Docker Deployment)**
Launch the entire ecosystem (Hub + Vision Worker) in isolated containers:
```bash
docker-compose up --build
```
*Access the Live Dashboard at: `http://localhost:8000`*

#### **C. Testing Mode (Quality Check)**
Run the automated test suite to verify module integrity:
```bash
pytest tests/
```

### 4. System Configuration
All settings are centralized in **`config.yaml`**. You can safely modify the following without touching the code:
- **Video Sources**: Change input path to your local IP camera.
- **AI Thresholds**: Adjust detection confidence and LSTM history windows.
- **Signal Timings**: Modify the default green/red durations for each lane.

---

## 🚦 Quick Tips

*   **Virtual Environment**: Always ensure `(venv)` is visible in your terminal before running any script.
*   **Missing Data**: If the Dashboard is empty, run `python main_pipeline.py` or `python demo_vision.py` first to generate the necessary `traffic_analytics.json` logs.
*   **GPU Acceleration**: If you have an NVIDIA GPU, the system will automatically use **CUDA** for a 5x speed boost.
*   **Final Release**: This project is now fully complete (Phase 1-5).

---

**Built with love as part of the Smart AI Traffic Architecture Project.** 🚀
