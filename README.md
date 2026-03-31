# Smart AI Traffic Intelligence System 🚦

A full-stack, modular, AI-driven urban traffic management system. This project integrates Computer Vision, Reinforcement Learning, and Time-Series Forecasting into a unified control dashboard.

## 📁 Repository URL
[https://github.com/sahilborhade77/traffic](https://github.com/sahilborhade77/traffic)

---

## 🏗️ Architecture
1. **Module 1: Vision** (YOLOv8 + ByteTrack) - Multi-lane vehicle detection and real-time counting.
2. **Module 2: Control** (DQN / Deep Q-Learning) - Adaptive traffic signal timing based on congestion.
3. **Module 3: Prediction** (LSTM) - Time-series forecasting for upcoming traffic peaks.
4. **Module 4: Dashboard** (Streamlit + Plotly) - Interactive GUI for real-time monitoring and analytics.

---

## 🛠️ Step-by-Step Setup

### 1. Prerequisites
- Python 3.8 to 3.11
- A valid traffic video (`data/traffic_sample.mp4` - provided)

### 2. Virtual Environment Setup (MANDATORY)
```powershell
# Create environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\activate

# Activate (macOS/Linux)
# source venv/bin/activate

# Install Dependencies
pip install -r requirements.txt
```

---

## 🏃 How to Run the Modules

### Phase 1: Test Vehicle Detection & Tracking
```powershell
python demo_vision.py
```
*Wait for it to finish and check `data/traffic_analytics.csv`.*

### Phase 2: Train & Evaluate RI Signal Logic
```powershell
# Train the AI for 100 episodes
python demo_control.py --train --episodes 100

# Evaluate and compare against baseline
python demo_control.py
```
*Check `data/control_performance.csv` for results.*

### Phase 3: Traffic Forecasting
```powershell
python demo_prediction.py --epochs 30
```
*Check `data/prediction_results.csv` for forecast accuracy.*

### Phase 4: Run Integrated Pipeline
```powershell
python main_pipeline.py
```

### Final Phase: Launch the Control Dashboard
```powershell
streamlit run src/dashboard/app.py
```

---

## ⚠️ Troubleshooting & FAQ

**Q: `ModuleNotFoundError` despite installing everything?**
A: Make sure your `venv` is activated. You should see `(venv)` in your terminal prompt.

**Q: YOLOv8 is downloading every time?**
A: It only downloads once and saves to the root folder as `yolov8n.pt`. If you delete it, it will redownload.

**Q: Dashboard is blank/empty?**
A: You must run the `demo_` scripts or `main_pipeline.py` at least once to generate the data logs (`data/traffic_analytics.csv`) that the dashboard reads.

---

## 🚀 Future Roadmap
- **Next-Gen Integration**: Support for live IP Camera feeds.
- **Hardware Simulation**: Connect with Arduino/Raspberry Pi for physical signal indicators.
- **Enhanced Prediction**: Include weather and event data for more accurate forecasts.

**Built with love as part of the Smart AI Traffic Project.**
