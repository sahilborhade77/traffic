"""
Enhanced Traffic Management Dashboard.

Comprehensive dashboard integrating:
- Live camera feeds with congestion monitoring
- Real-time traffic heatmap
- Historical trend analysis
- Violation gallery with processing
- Traffic flow visualization with trajectories
- Signal timing comparison metrics
- Report Builder for authority use
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import sys
import time
import requests

# Add root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.dashboard.components import (
    CameraFeedGrid,
    TrafficHeatmap,
    HistoricalTrends,
    ViolationGallery
)
from src.dashboard.flow_visualization import TrafficFlowVisualization
from src.dashboard.comparison_metrics import ComparisonMetrics


# Page configuration
st.set_page_config(
    page_title="Traffic Intelligence Command Center",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Modern Color Scheme
PRIMARY_COLOR = "#0099FF"      # Bright Blue
SECONDARY_COLOR = "#00E0B6"    # Bright Teal
DANGER_COLOR = "#FF5555"       # Red
WARNING_COLOR = "#FFB84D"      # Orange
SUCCESS_COLOR = "#00DD66"      # Green
DARK_BG = "#0A1120"            # Deep Navy background
CARD_BG = "#162035"            # Lighter Navy card
TEXT_PRIMARY = "#E8EEFF"       
TEXT_SECONDARY = "#8E96AF"     

# Lane colors
NORTH_COLOR = "#FF4466"
SOUTH_COLOR = "#00E6D3"
EAST_COLOR = "#FFD93D"
WEST_COLOR = "#6FE7D7"

# Persona configuration
PERSONAS = {
    "🛡️ Traffic Authority": {
        "description": "Full access to violations, camera health, and adaptive signal control.",
        "tabs": ["Live Monitoring", "Analysis & Insights", "Comparison & Metrics", "Report Builder"],
        "icons": ["🔴", "📈", "⚡", "📋"],
        "primary": PRIMARY_COLOR
    },
    "👥 Public Citizen": {
        "description": "View traffic congestion, travel times, and public safety alerts.",
        "tabs": ["Traffic Map", "Travel Times", "Safety Alerts"],
        "icons": ["🗺️", "🕒", "📢"],
        "primary": SECONDARY_COLOR
    }
}

# --- Report State Management ---
if 'report_content' not in st.session_state:
    st.session_state.report_content = []

API_BASE_URL = "http://127.0.0.1:8000"

class ReportBuilder:
    @staticmethod
    def add_to_report(title, description, data=None):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.report_content.append({
            "title": title,
            "description": description,
            "timestamp": timestamp,
            "data": data
        })
        st.toast(f"✅ Added '{title}' to report!", icon="📝")

    @staticmethod
    def clear_report():
        st.session_state.report_content = []
        st.toast("🗑️ Report cleared", icon="🧹")

def fetch_traffic_status() -> list:
    """Fetch real lane counts from the local API."""
    try:
        response = requests.get(f"{API_BASE_URL}/api/traffic/status", timeout=2)
        response.raise_for_status()
        return response.json()
    except Exception:
        return []


# Custom CSS
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&family=Outfit:wght@300;600;800&display=swap');

    html, body, [data-testid="stAppViewContainer"] {{
        font-family: 'Inter', sans-serif;
        background-color: {DARK_BG};
    }}

    .main {{ background-color: {DARK_BG}; color: {TEXT_PRIMARY}; }}
    
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, #0F1829 0%, {DARK_BG} 100%);
        border-right: 1px solid rgba(0, 153, 255, 0.2);
    }}

    /* Card Styling - Glassmorphism */
    .info-card {{
        background: rgba(22, 32, 53, 0.6);
        backdrop-filter: blur(10px);
        padding: 24px;
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        margin-bottom: 24px;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }}
    .info-card:hover {{
        transform: translateY(-8px) scale(1.02);
        border-color: {PRIMARY_COLOR};
        box-shadow: 0 12px 40px rgba(0, 153, 255, 0.2);
    }}
    
    /* Metrics */
    [data-testid="stMetric"] {{
        background: rgba(22, 32, 53, 0.4);
        padding: 20px;
        border-radius: 14px;
        border-left: 5px solid {PRIMARY_COLOR};
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }}
    
    /* Headers */
    h1, h2, h3 {{
        font-family: 'Outfit', sans-serif;
        background: linear-gradient(135deg, #FFFFFF 0%, {PRIMARY_COLOR} 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.02em;
    }}

    .hero-text {{
        font-family: 'Outfit', sans-serif;
        font-size: 3.5rem;
        font-weight: 800;
        margin-bottom: 0;
        background: linear-gradient(90deg, #FFFFFF, {PRIMARY_COLOR}, {SECONDARY_COLOR});
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }}
    
    /* Custom Scrollbar */
    ::-webkit-scrollbar {{ width: 8px; }}
    ::-webkit-scrollbar-track {{ background: {DARK_BG}; }}
    ::-webkit-scrollbar-thumb {{ background: #333; border-radius: 10px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: {PRIMARY_COLOR}; }}

    /* Lane Glow Effects */
    .lane-north {{ border-top: 4px solid {NORTH_COLOR}; box-shadow: 0 -10px 20px rgba(255, 68, 102, 0.1); }}
    .lane-south {{ border-top: 4px solid {SOUTH_COLOR}; box-shadow: 0 -10px 20px rgba(0, 230, 211, 0.1); }}
    .lane-east {{ border-top: 4px solid {EAST_COLOR}; box-shadow: 0 -10px 20px rgba(255, 217, 61, 0.1); }}
    .lane-west {{ border-top: 4px solid {WEST_COLOR}; box-shadow: 0 -10px 20px rgba(111, 231, 215, 0.1); }}
</style>
""", unsafe_allow_html=True)

def render_sidebar() -> dict:
    st.sidebar.markdown(f"<h2 style='text-align: center;'>🚦 COMMAND</h2>", unsafe_allow_html=True)
    
    persona_name = st.sidebar.selectbox("User Role", list(PERSONAS.keys()))
    persona = PERSONAS[persona_name]
    st.sidebar.caption(persona["description"])
    
    st.sidebar.divider()
    
    dashboard_mode = st.sidebar.radio("Navigation", 
                                     [f"{icon} {tab}" for icon, tab in zip(persona["icons"], persona["tabs"])])
    
    st.sidebar.divider()
    
    with st.sidebar.expander("⚙️ System Settings"):
        live_feed = st.toggle("Live Analysis", value=True)
        use_real_counts = st.toggle("Use Real Counts", value=False)
        refresh = st.slider("Refresh (s)", 1, 60, 5)
        auto_lane = st.checkbox("AI Auto-Lane Discovery", value=True)
        if auto_lane:
            st.caption("✨ AI learning trajectories...")

    # Extract the base tab name (everything after the icon and space)
    mode = " ".join(dashboard_mode.split(" ")[1:])
    
    return {
        "mode": mode,
        "persona": persona_name,
        "live_feed": live_feed,
        "use_real_counts": use_real_counts,
        "refresh_rate": refresh,
        "auto_lane": auto_lane
    }

def render_header(is_hero=True):
    if is_hero:
        st.markdown(f"""
        <div style="text-align: center; padding: 40px 0 20px 0;">
            <h1 class="hero-text">Traffic Intelligence Command</h1>
            <p style="color: #8E96AF; font-size: 1.2rem; font-weight: 300;">AI-Driven Urban Mobility & Safety Management</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; padding: 10px; background: rgba(255,255,255,0.03); border-radius: 12px;">
            <h3 style="margin: 0; background: none; -webkit-text-fill-color: {TEXT_PRIMARY};">🚦 Intelligence Command</h3>
            <span style="color: {PRIMARY_COLOR}; font-weight: 600; font-size: 0.9em;">System Status: Optimal</span>
        </div>
        """, unsafe_allow_html=True)

def render_live_monitoring(config):
    lane_order = ["North", "South", "East", "West"]
    lane_counts = {
        "North": 145,
        "South": 132,
        "East": 178,
        "West": 112,
    }
    lane_loads = {"North": "45%", "South": "38%", "East": "62%", "West": "30%"}
    real_mode = config.get("use_real_counts", False)
    traffic_status = fetch_traffic_status() if real_mode else []

    if traffic_status:
        lane_counts = {
            item.get("lane"): int(item.get("vehicle_count", 0))
            for item in traffic_status
        }
        lane_loads = {
            lane: f"{min(100, lane_counts.get(lane, 0) * 5)}%"
            for lane in lane_order
        }
        avg_wait = (
            sum(float(item.get("wait_time", 0.0)) for item in traffic_status) / len(traffic_status)
        )
        critical_lanes = sum(
            1 for item in traffic_status
            if item.get("congestion_level") in {"high", "critical"}
        )
    else:
        avg_wait = 38.2
        critical_lanes = 0

    col_t, col_b = st.columns([3, 1])
    with col_t:
        st.markdown("## 📡 Real-Time Operations")
    with col_b:
        if st.button("📸 Add to Report", use_container_width=True):
            ReportBuilder.add_to_report("Live Operations Snapshot", "System-wide traffic metrics and lane status.")

    m1, m2, m3, m4 = st.columns(4)
    if real_mode and traffic_status:
        m1.metric("Active Vehicles", sum(lane_counts.get(lane, 0) for lane in lane_order))
        m2.metric("Avg Wait Time", f"{avg_wait:.1f}s", delta_color="inverse")
        m3.metric("Congested Lanes", f"{critical_lanes}/{len(lane_order)}", delta_color="inverse")
        m4.metric("Count Source", "Real")
    elif real_mode:
        m1.metric("Active Vehicles", "0")
        m2.metric("Avg Wait Time", "0.0s", delta_color="inverse")
        m3.metric("Congested Lanes", "0/4", delta_color="inverse")
        m4.metric("Count Source", "Waiting")
    else:
        m1.metric("Active Vehicles", "847", "+12")
        m2.metric("Avg Wait Time", "38.2s", "-2.3s", delta_color="inverse")
        m3.metric("Congestion", "32%", "+5%", delta_color="inverse")
        m4.metric("AI Optimization", "78%", "+4%")
    
    st.divider()
    
    t1, t2 = st.tabs(["📊 Analytics", "📹 Intelligence"])
    
    with t1:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 🔥 Traffic Heatmap")
            TrafficHeatmap.render()
        with c2:
            st.markdown("### 🏗️ Lane Occupancy")
            df = pd.DataFrame({
                "Lane": lane_order,
                "Vehicles": [lane_counts.get(lane, 0) for lane in lane_order],
                "Load": [lane_loads.get(lane, "0%") for lane in lane_order]
            })
            st.dataframe(df, use_container_width=True, hide_index=True)
            
        st.markdown("### 📹 Virtual Lane Monitoring")
        if config["auto_lane"]:
            st.info("💡 **AI Lane Discovery**: The system is analyzing trajectories to map lanes. If only one lane is visible, ensure traffic flow is present across all segments.")
        
        lc = st.columns(4)
        for i, l in enumerate(lane_order):
            with lc[i]:
                st.markdown(f"""
                <div class="info-card lane-{l.lower()}">
                    <small>{l} Lane</small>
                    <h3>{lane_counts.get(l, 0)}</h3>
                    <div style='color: #00D4AA; font-size: 0.8em;'>{'Real count' if real_mode else 'Flowing'}</div>
                </div>
                """, unsafe_allow_html=True)

    with t2:
        st.markdown("### 🧠 Computer Vision Engine")
        st.markdown("""
        <div style="background: #000; height: 350px; border-radius: 12px; display: flex; align-items: center; justify-content: center; border: 2px dashed #0099FF;">
            <div style="text-align: center; color: #8E96AF;">
                <p style="font-size: 1.5em;">📹 Live Stream Processing</p>
                <p>YOLOv8s Model • 30 FPS • CUDA Enabled</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        sc1, sc2 = st.columns(2)
        sc1.selectbox("Camera Source", ["Main Intersection", "Highway Exit", "City Square", "Custom Upload..."])
        sc2.multiselect("Active Detectors", ["Car", "Truck", "Bus", "Motorcycle"], default=["Car", "Truck"])

def render_report_builder():
    st.markdown("## 📋 Intelligence Report Builder")
    
    c1, c2 = st.columns([2, 1])
    
    with c2:
        st.markdown("### 📥 Export")
        name = st.text_input("Report Name", f"Traffic_Summary_{datetime.now().strftime('%H%M')}")
        fmt = st.selectbox("Format", ["PDF", "HTML", "Excel"])
        if st.button("🚀 Generate Report", use_container_width=True):
            if st.session_state.report_content:
                with st.spinner("Compiling..."):
                    time.sleep(1.5)
                    st.success(f"Report '{name}.{fmt.lower()}' ready!")
                    st.balloons()
            else:
                st.error("No data added to report.")
        if st.button("🗑️ Clear All", use_container_width=True):
            ReportBuilder.clear_report()
            st.rerun()

    with c1:
        st.markdown("### 📝 Preview")
        if not st.session_state.report_content:
            st.info("Add snapshots from other tabs to build your report.")
        else:
            for i, item in enumerate(st.session_state.report_content):
                with st.expander(f"{i+1}. {item['title']} - {item['timestamp']}"):
                    st.write(item['description'])
                    if st.button("Remove", key=f"rm_{i}"):
                        st.session_state.report_content.pop(i)
                        st.rerun()

def render_public_view(config):
    m = config["mode"]
    if m == "Traffic Map":
        st.markdown("## 🗺️ Live Traffic Map")
        TrafficHeatmap.render()
    elif m == "Travel Times":
        st.markdown("## 🕒 Est. Travel Times")
        st.table(pd.DataFrame({
            "Route": ["Home to Work", "Work to Gym", "City Center"],
            "Time": ["15 min", "8 min", "22 min"],
            "Delay": ["+2 min", "None", "+5 min"]
        }))
    elif m == "Safety Alerts":
        st.markdown("## 📢 Safety Alerts")
        st.warning("🚧 Construction on Park Ave until 6 PM.")
    else:
        st.error(f"Unknown Mode: {m}")

def main():
    config = render_sidebar()
    
    # Header logic: only show hero on live monitoring or first load
    is_hero = config["mode"] in ["Live Monitoring", "Traffic Map"]
    render_header(is_hero=is_hero)
    
    if "Public" in config["persona"]:
        render_public_view(config)
    else:
        m = config["mode"]
        if m == "Live Monitoring": render_live_monitoring(config)
        elif m == "Analysis & Insights": 
            st.markdown("## 📈 Trends & Analysis")
            HistoricalTrends.render()
        elif m == "Comparison & Metrics": 
            st.markdown("## ⚡ Performance Comparison")
            ComparisonMetrics.render_all()
        elif m == "Report Builder": 
            render_report_builder()
        else:
            st.error(f"Unknown Mode: {m}")
            st.info("Please select a valid module from the sidebar.")
    
    st.divider()
    st.caption(f"© 2024-2026 Traffic Intelligence System | Status: Connected | Last Update: {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    main()
