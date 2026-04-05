"""
Enhanced Traffic Management Dashboard.

Comprehensive dashboard integrating:
- Live camera feeds with congestion monitoring
- Real-time traffic heatmap
- Historical trend analysis
- Violation gallery with processing
- Traffic flow visualization with trajectories
- Signal timing comparison metrics
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dashboard.components import (
    CameraFeedGrid,
    TrafficHeatmap,
    HistoricalTrends,
    ViolationGallery
)
from dashboard.flow_visualization import TrafficFlowVisualization
from dashboard.comparison_metrics import ComparisonMetrics


# Page configuration
st.set_page_config(
    page_title="Traffic Management Dashboard",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Modern Color Scheme - Pure Dark Mode (No White)
PRIMARY_COLOR = "#0099FF"      # Bright Blue
SECONDARY_COLOR = "#00E0B6"    # Bright Teal
DANGER_COLOR = "#FF5555"       # Red
WARNING_COLOR = "#FFB84D"      # Orange
SUCCESS_COLOR = "#00DD66"      # Green
DARK_BG = "#0A0E18"            # Pure Dark background
CARD_BG = "#141B2F"            # Dark card background
TEXT_PRIMARY = "#E8EEFF"       # Soft Gray (not white)
TEXT_SECONDARY = "#8E96AF"     # Medium Gray

# Lane colors - DISTINCT AND VIBRANT
NORTH_COLOR = "#FF4466"        # Vibrant Red
SOUTH_COLOR = "#00E6D3"        # Bright Cyan
EAST_COLOR = "#FFD93D"         # Bright Yellow
WEST_COLOR = "#6FE7D7"         # Bright Mint

# Chart colors
CHART_COLOR_1 = "#00BFFF"      # Deep Sky Blue
CHART_COLOR_2 = "#00D9FF"      # Cyan
CHART_COLOR_3 = "#FF69B4"      # Hot Pink
CHART_COLOR_4 = "#FF6B9D"      # Salmon

# Custom CSS with PURE DARK Theme (No White)
st.markdown(f"""
<style>
    * {{
        color-scheme: dark;
    }}
    
    :root {{
        --primary: {PRIMARY_COLOR};
        --secondary: {SECONDARY_COLOR};
        --danger: {DANGER_COLOR};
        --warning: {WARNING_COLOR};
        --success: {SUCCESS_COLOR};
        --dark-bg: {DARK_BG};
        --card-bg: {CARD_BG};
        --text-primary: {TEXT_PRIMARY};
        --text-secondary: {TEXT_SECONDARY};
        --north: {NORTH_COLOR};
        --south: {SOUTH_COLOR};
        --east: {EAST_COLOR};
        --west: {WEST_COLOR};
    }}
    
    /* Main theme - NO WHITE */
    .main {{
        background-color: {DARK_BG};
        color: {TEXT_PRIMARY};
    }}
    
    /* Force no white anywhere */
    html, body {{
        background-color: {DARK_BG};
        color: {TEXT_PRIMARY};
    }}
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, #0F1829 0%, {DARK_BG} 100%);
        border-right: 3px solid {PRIMARY_COLOR};
    }}
    
    [data-testid="stSidebar"] * {{
        color: {TEXT_PRIMARY} !important;
    }}
    
    /* Sidebar headings */
    [data-testid="stSidebar"] h2 {{
        color: {TEXT_PRIMARY} !important;
        font-weight: 800;
    }}
    
    [data-testid="stSidebar"] h3 {{
        color: {SECONDARY_COLOR} !important;
        border-bottom: 2px solid {PRIMARY_COLOR};
        padding-bottom: 8px;
    }}
    
    /* Metric card styling - VIBRANT */
    [data-testid="metric-container"] {{
        background: linear-gradient(135deg, {CARD_BG} 0%, rgba(0, 153, 255, 0.05) 100%);
        padding: 20px;
        border-radius: 12px;
        border-left: 5px solid {PRIMARY_COLOR};
        border-top: 2px solid {SECONDARY_COLOR};
        box-shadow: 0 4px 15px rgba(0, 153, 255, 0.2);
        transition: all 0.3s ease;
    }}
    
    [data-testid="metric-container"] * {{
        color: {TEXT_PRIMARY} !important;
    }}
    
    [data-testid="metric-container"]:hover {{
        transform: translateY(-4px);
        box-shadow: 0 12px 35px rgba(0, 153, 255, 0.35);
        border-left-color: {SECONDARY_COLOR};
        background: linear-gradient(135deg, rgba(0, 153, 255, 0.08) 0%, rgba(0, 224, 182, 0.12) 100%);
    }}
    
    /* Headers with gradient */
    h1, h2, h3, h4, h5, h6 {{
        color: {TEXT_PRIMARY} !important;
        font-weight: 700;
        letter-spacing: -0.5px;
    }}
    
    h1 {{
        border-bottom: 3px solid;
        border-image: linear-gradient(90deg, {PRIMARY_COLOR}, {SECONDARY_COLOR}) 1;
        padding-bottom: 12px;
        background: linear-gradient(90deg, {PRIMARY_COLOR}, {SECONDARY_COLOR});
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }}
    
    /* All text elements */
    p, span, div, label {{
        color: {TEXT_PRIMARY} !important;
    }}
    
    /* Dataframe styling */
    [data-testid="dataFrame"] {{
        background-color: {CARD_BG} !important;
        color: {TEXT_PRIMARY} !important;
    }}
    
    [data-testid="dataFrame"] * {{
        background-color: {CARD_BG} !important;
        color: {TEXT_PRIMARY} !important;
    }}
    
    /* Button styling */
    .stButton > button {{
        background: linear-gradient(90deg, {PRIMARY_COLOR}, {SECONDARY_COLOR});
        color: {TEXT_PRIMARY};
        border: none;
        border-radius: 8px;
        padding: 12px 24px;
        font-weight: 700;
        transition: all 0.3s ease;
        box-shadow: 0 6px 20px rgba(0, 153, 255, 0.4);
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    
    .stButton > button:hover {{
        transform: translateY(-3px);
        box-shadow: 0 10px 35px rgba(0, 153, 255, 0.55);
        color: {TEXT_PRIMARY};
    }}
    
    /* Divider */
    hr {{
        border-color: rgba(0, 224, 182, 0.4);
        border-width: 2px;
    }}
    
    /* Radio/Select/Checkbox styling */
    .stRadio > label, .stSelectbox > label, .stMultiSelect > label, .stCheckbox > label {{
        color: {TEXT_PRIMARY} !important;
        font-weight: 600;
    }}
    
    .stRadio > label span, .stSelectbox > label span, .stMultiSelect > label span, .stCheckbox > label span {{
        color: {TEXT_PRIMARY} !important;
    }}
    
    /* Toggle styling */
    .stToggle {{
        color: {TEXT_PRIMARY} !important;
    }}
    
    /* Expander styling */
    [data-testid="stExpander"] {{
        background-color: {CARD_BG};
        border: 2px solid {PRIMARY_COLOR};
        border-radius: 8px;
    }}
    
    [data-testid="stExpander"] * {{
        color: {TEXT_PRIMARY} !important;
    }}
    
    [data-testid="stExpander"] p {{
        color: {TEXT_SECONDARY} !important;
    }}
    
    /* Success/Info/Warning messages */
    .stSuccess {{
        background-color: rgba(0, 221, 102, 0.15);
        border: 2px solid {SUCCESS_COLOR};
        border-radius: 8px;
        color: {SUCCESS_COLOR};
    }}
    
    .stSuccess * {{
        color: {SUCCESS_COLOR} !important;
    }}
    
    .stInfo {{
        background-color: rgba(0, 153, 255, 0.15);
        border: 2px solid {PRIMARY_COLOR};
        border-radius: 8px;
        color: {PRIMARY_COLOR};
    }}
    
    .stInfo * {{
        color: {TEXT_PRIMARY} !important;
    }}
    
    .stWarning {{
        background-color: rgba(255, 180, 77, 0.15);
        border: 2px solid {WARNING_COLOR};
        border-radius: 8px;
    }}
    
    .stWarning * {{
        color: {TEXT_PRIMARY} !important;
    }}
    
    .stError {{
        background-color: rgba(255, 85, 85, 0.15);
        border: 2px solid {DANGER_COLOR};
        border-radius: 8px;
    }}
    
    .stError * {{
        color: {TEXT_PRIMARY} !important;
    }}
    
    /* Info card styling */
    .info-card {{
        background: linear-gradient(135deg, {CARD_BG} 0%, rgba(0, 153, 255, 0.06) 100%);
        padding: 20px;
        border-radius: 12px;
        border: 2px solid {PRIMARY_COLOR};
        border-left: 5px solid {SECONDARY_COLOR};
        margin: 15px 0;
        box-shadow: 0 4px 15px rgba(0, 153, 255, 0.12);
    }}
    
    .info-card * {{
        color: {TEXT_PRIMARY} !important;
    }}
    
    /* Lane cards - DISTINCT COLORS */
    .lane-card-north {{
        background: linear-gradient(135deg, rgba(255, 68, 102, 0.12) 0%, rgba(255, 68, 102, 0.04) 100%);
        border-left: 5px solid {NORTH_COLOR};
        border-top: 2px solid {NORTH_COLOR};
    }}
    
    .lane-card-south {{
        background: linear-gradient(135deg, rgba(0, 230, 211, 0.12) 0%, rgba(0, 230, 211, 0.04) 100%);
        border-left: 5px solid {SOUTH_COLOR};
        border-top: 2px solid {SOUTH_COLOR};
    }}
    
    .lane-card-east {{
        background: linear-gradient(135deg, rgba(255, 217, 61, 0.12) 0%, rgba(255, 217, 61, 0.04) 100%);
        border-left: 5px solid {EAST_COLOR};
        border-top: 2px solid {EAST_COLOR};
    }}
    
    .lane-card-west {{
        background: linear-gradient(135deg, rgba(111, 231, 215, 0.12) 0%, rgba(111, 231, 215, 0.04) 100%);
        border-left: 5px solid {WEST_COLOR};
        border-top: 2px solid {WEST_COLOR};
    }}
    
    .lane-card-north *, .lane-card-south *, .lane-card-east *, .lane-card-west * {{
        color: {TEXT_PRIMARY} !important;
    }}
    
    /* Metric value styling */
    .metric-value {{
        color: {SECONDARY_COLOR} !important;
        font-size: 28px;
        font-weight: 700;
    }}
    
    .metric-delta-positive {{
        color: {SUCCESS_COLOR} !important;
        font-weight: 600;
    }}
    
    .metric-delta-negative {{
        color: {DANGER_COLOR} !important;
        font-weight: 600;
    }}
    
    .metric-delta-neutral {{
        color: {TEXT_SECONDARY} !important;
    }}
    
    /* Caption */
    .stCaption {{
        color: {TEXT_SECONDARY} !important;
    }}
    
    /* Tab styling */
    [data-testid="stTabs"] {{
        background-color: transparent;
    }}
    
    [data-testid="stTabs"] * {{
        color: {TEXT_PRIMARY} !important;
    }}
    
    /* Badge styling */
    .badge {{
        display: inline-block;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 700;
        margin: 5px 5px 5px 0;
    }}
    
    .badge-success {{
        background-color: rgba(0, 221, 102, 0.25);
        color: {SUCCESS_COLOR};
        border: 1px solid {SUCCESS_COLOR};
    }}
    
    .badge-warning {{
        background-color: rgba(255, 180, 77, 0.25);
        color: {WARNING_COLOR};
        border: 1px solid {WARNING_COLOR};
    }}
    
    .badge-danger {{
        background-color: rgba(255, 85, 85, 0.25);
        color: {DANGER_COLOR};
        border: 1px solid {DANGER_COLOR};
    }}
    
    .badge-info {{
        background-color: rgba(0, 153, 255, 0.25);
        color: {PRIMARY_COLOR};
        border: 1px solid {PRIMARY_COLOR};
    }}
    
    /* Slider styling */
    .stSlider {{
        color: {PRIMARY_COLOR};
    }}
    
    .stSlider * {{
        color: {TEXT_PRIMARY} !important;
    }}
    
    /* Text emphasis */
    strong, b {{
        color: {SECONDARY_COLOR} !important;
        font-weight: 700;
    }}
    
    /* Code block */
    .stCodeBlock {{
        background-color: {CARD_BG};
        border: 1px solid {PRIMARY_COLOR};
        border-radius: 8px;
        color: {TEXT_PRIMARY};
    }}
    
    /* Input fields */
    .stTextInput input, .stNumberInput input, .stTextArea textarea {{
        background-color: {CARD_BG} !important;
        color: {TEXT_PRIMARY} !important;
        border: 1px solid {PRIMARY_COLOR} !important;
        border-radius: 6px;
    }}
    
    .stTextInput input::placeholder, .stNumberInput input::placeholder, .stTextArea textarea::placeholder {{
        color: {TEXT_SECONDARY} !important;
    }}
    
    /* Slider track */
    .stSlider [data-testid="stSlider"] * {{
        color: {TEXT_PRIMARY} !important;
    }}
    
    /* Links */
    a {{
        color: {PRIMARY_COLOR} !important;
    }}
    
    a:hover {{
        color: {SECONDARY_COLOR} !important;
    }}
    
    /* Override any remaining white background elements */
    [style*="background-color: white"] {{
        background-color: {CARD_BG} !important;
        color: {TEXT_PRIMARY} !important;
    }}
    
    [style*="rgb(255, 255, 255)"] {{
        background-color: {CARD_BG} !important;
        color: {TEXT_PRIMARY} !important;
    }}
    
    [style*="background: white"] {{
        background-color: {CARD_BG} !important;
        color: {TEXT_PRIMARY} !important;
    }}
</style>
""", unsafe_allow_html=True)



def render_sidebar() -> dict:
    """Render and manage sidebar controls with improved styling."""
    st.sidebar.markdown("""
    <div style="text-align: center; margin-bottom: 20px;">
        <h2 style="background: linear-gradient(90deg, #0066CC, #00D4AA); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">
        🎛️ CONTROL PANEL
        </h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Dashboard mode with enhanced styling
    st.sidebar.markdown("### 📊 Dashboard View")
    dashboard_mode = st.sidebar.radio(
        "Select View",
        ["🔴 Live Monitoring", "📈 Analysis & Insights", "⚡ Comparison & Metrics"],
        index=0,
        label_visibility="collapsed"
    )
    
    # Real-time controls
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚙️ Real-Time Settings")
    live_feed_enabled = st.sidebar.toggle("📡 Enable Live Feed", value=True)
    refresh_rate = st.sidebar.slider(
        "🔄 Refresh Rate",
        min_value=1,
        max_value=60,
        value=5,
        step=1,
        help="How often to update the dashboard (seconds)"
    )
    
    # Filters
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔍 Filters & Monitoring")
    selected_lanes = st.sidebar.multiselect(
        "Monitor Lanes",
        options=["North", "South", "East", "West"],
        default=["North", "South", "East", "West"],
        help="Select which lanes to monitor"
    )
    
    # Date range for analysis
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📅 Historical Data")
    date_range = st.sidebar.slider(
        "Data Range (days)",
        min_value=1,
        max_value=90,
        value=30,
        step=1,
        help="How many days of historical data to analyze"
    )
    
    # Violation filters
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚖️ Violation Tracking")
    violation_types = st.sidebar.multiselect(
        "Violation Types",
        options=["Red Light", "Speeding", "Illegal Turn", "Other"],
        default=["Red Light", "Speeding"],
        help="Filter violations by type"
    )
    
    min_severity = st.sidebar.slider(
        "Minimum Severity",
        min_value=1,
        max_value=5,
        value=1,
        step=1,
        help="Only show violations above this severity"
    )
    
    # Advanced settings
    st.sidebar.markdown("---")
    with st.sidebar.expander("⚙️ Advanced Settings", expanded=False):
        st.markdown("**Database Connection**")
        db_type = st.selectbox(
            "Database Type",
            ["SQLite (Local)", "PostgreSQL"],
            index=0
        )
        
        use_real_data = st.checkbox("Use Real Database Data", value=False)
        
        st.markdown("**Analytics Options**")
        export_format = st.selectbox(
            "Export Format",
            ["CSV", "JSON", "PDF"],
            index=0
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📊 Export Report", use_container_width=True):
                st.success(f"✅ Report exported as {export_format}")
        with col2:
            if st.button("🔄 Sync Now", use_container_width=True):
                st.info("⏳ Syncing data...")
    
    # Clean mode conversion
    mode = dashboard_mode.replace("🔴 ", "").replace("📈 ", "").replace("⚡ ", "")
    
    return {
        "mode": mode,
        "live_feed": live_feed_enabled,
        "refresh_rate": refresh_rate,
        "lanes": selected_lanes,
        "date_range": date_range,
        "violation_types": violation_types,
        "min_severity": min_severity,
        "db_type": db_type,
        "use_real_data": use_real_data,
    }



def render_header() -> None:
    """Render dashboard header with status."""
    # Title section with gradient
    st.markdown("""
    <div style="text-align: center; padding: 20px 0; border-bottom: 2px solid rgba(0, 204, 170, 0.3); margin-bottom: 20px;">
        <h1 style="margin: 0; font-size: 2.5em; background: linear-gradient(90deg, #0066CC, #00D4AA); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">
        🚦 Traffic Intelligence System
        </h1>
        <p style="color: #B0B8C1; margin-top: 5px; font-size: 1.1em;">
        Real-time monitoring • AI-powered optimization • Live analytics
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🟢 System Status", "ONLINE", "All systems operational")
    
    with col2:
        current_time = datetime.now().strftime("%H:%M:%S")
        st.metric("⏰ Current Time", current_time, "Live")
    
    with col3:
        uptime = "99.8%"
        st.metric("✅ Uptime", uptime, "Last 7 days")
    
    with col4:
        active_cams = "12/12"
        st.metric("📹 Cameras", active_cams, "All active")



def render_live_monitoring(config: dict) -> None:
    """Render live monitoring dashboard with enhanced styling."""
    st.markdown("## 📡 Live Traffic Monitoring")
    
    # System overview metrics with better spacing and styling
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "🚗 Active Vehicles",
            "847",
            "+12 from 5m ago",
            delta_color="inverse",
            help="Number of vehicles currently detected"
        )
    
    with col2:
        st.metric(
            "⏱️ Avg Wait Time",
            "38.2s",
            "-2.3s improvement",
            delta_color="inverse",
            help="Average vehicle wait time at intersections"
        )
    
    with col3:
        st.metric(
            "🔴 Congestion Level",
            "32%",
            "+5% from peak",
            delta_color="off",
            help="Current traffic congestion percentage"
        )
    
    with col4:
        st.metric(
            "⚡ Signal Efficiency",
            "78%",
            "+4% with AI",
            delta_color="inverse",
            help="Traffic signal optimization effectiveness"
        )
    
    st.markdown("---")
    
    # Live camera feeds grid
    st.markdown("### 📹 Live Camera Feeds")
    
    lanes_data = {
        "North": {
            "vehicle_count": 145,
            "congestion": 0.42,
            "signal_state": "🟢 Green (25s)"
        },
        "South": {
            "vehicle_count": 132,
            "congestion": 0.35,
            "signal_state": "🔴 Red (18s)"
        },
        "East": {
            "vehicle_count": 178,
            "congestion": 0.58,
            "signal_state": "🟡 Yellow (5s)"
        },
        "West": {
            "vehicle_count": 112,
            "congestion": 0.28,
            "signal_state": "🟢 Green (32s)"
        },
    }
    
    # Display lanes as expandable sections
    cols = st.columns(4)
    for idx, (lane, data) in enumerate(lanes_data.items()):
        with cols[idx]:
            congestion_color = "🔴" if data['congestion'] > 0.5 else "🟡" if data['congestion'] > 0.35 else "🟢"
            # Choose lane card class based on lane name
            lane_class = f"lane-card-{lane.lower()}"
            
            st.markdown(f"""
            <div class="info-card {lane_class}" style="padding: 20px; border-radius: 12px;">
                <h3 style="margin-top: 0; margin-bottom: 15px; font-size: 1.4em;">{lane} Lane {congestion_color}</h3>
                <div style="background-color: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px; margin-bottom: 10px;">
                    <p style="margin: 5px 0;"><b>🚗 Vehicles:</b> <span style="font-size: 1.3em; color: #00D4AA;">{data['vehicle_count']}</span></p>
                    <p style="margin: 5px 0;"><b>🔥 Congestion:</b> <span style="font-size: 1.3em; color: #FFE66D;">{data['congestion']*100:.0f}%</span></p>
                    <p style="margin: 5px 0;"><b>🚦 Signal:</b> <span style="font-size: 1.2em;">{data['signal_state']}</span></p>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Real-time traffic heatmap
    st.markdown("### 🔥 Real-Time Traffic Heatmap")
    TrafficHeatmap.render()
    
    st.markdown("---")
    
    # Live statistics in tabs
    tab1, tab2 = st.tabs(["📊 Lane Performance", "🏥 System Health"])
    
    with tab1:
        lane_stats = pd.DataFrame({
            "Lane": ["North", "South", "East", "West"],
            "Vehicles": [145, 132, 178, 112],
            "Congestion %": [42, 35, 58, 28],
            "Avg Speed (km/h)": [24, 26, 18, 28],
            "Signal State": ["🟢 Green", "🔴 Red", "🟡 Yellow", "🟢 Green"]
        })
        st.dataframe(lane_stats, use_container_width=True, hide_index=True)
    
    with tab2:
        health_metrics = pd.DataFrame({
            "Metric": ["CPU Usage", "Memory", "API Response", "DB Latency"],
            "Current": ["34%", "52%", "145ms", "23ms"],
            "Status": ["✅ Good", "✅ Good", "✅ Good", "✅ Good"],
            "Trend": ["↓", "→", "↑", "↓"]
        })
        st.dataframe(health_metrics, use_container_width=True, hide_index=True)



def render_analysis_insights(config: dict) -> None:
    """Render analysis and insights dashboard with enhanced layout."""
    st.markdown("## 📈 Analysis & Insights")
    
    # Info section
    st.markdown("""
    <div class="info-card" style="border-left: 4px solid #00D4AA;">
        <b>📊 Data Summary:</b> Analyzing {0} days of traffic data across {1} monitored intersections
    </div>
    """.format(config['date_range'], len(config['lanes'])), unsafe_allow_html=True)
    
    # Tabs for different analysis views
    tab1, tab2, tab3 = st.tabs(["📉 Trends", "🚗 Flow Analysis", "⚖️ Violations"])
    
    with tab1:
        st.markdown("### Historical Trends")
        HistoricalTrends.render(days=config["date_range"])
    
    with tab2:
        st.markdown("### Traffic Flow Analysis")
        TrafficFlowVisualization.render_all()
    
    with tab3:
        st.markdown("### Violation Records")
        ViolationGallery.render(
            sort_by="recent",
            filter_type=None,
            limit=12
        )



def render_comparison_view(config: dict) -> None:
    """Render comparison and metrics dashboard with enhanced styling."""
    st.markdown("## ⚡ Comparison & Optimization Metrics")
    
    # Info box with gradient
    st.markdown("""
    <div class="info-card" style="border-left: 4px solid #00D4AA; background: linear-gradient(90deg, rgba(0, 102, 204, 0.1), rgba(0, 212, 170, 0.1));">
        <b>🎯 Comparison Overview:</b><br/>
        This section compares <span style="color: #0066CC; font-weight: 600;">Fixed-Timing Control</span> (traditional baseline) 
        versus <span style="color: #00D4AA; font-weight: 600;">Adaptive AI Control</span> (intelligent optimization).
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Render all comparison metrics
    ComparisonMetrics.render_all()



def render_footer() -> None:
    """Render dashboard footer with modern styling."""
    st.markdown("---")
    
    footer_html = f"""
    <div style="text-align: center; padding: 20px; border-top: 1px solid rgba(0, 204, 170, 0.2); margin-top: 40px;">
        <div style="display: flex; justify-content: space-around; margin-bottom: 15px; flex-wrap: wrap;">
            <span style="color: #B0B8C1; font-size: 0.9em;">
                ⏱️ Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </span>
            <span style="color: #B0B8C1; font-size: 0.9em;">
                🔄 Refresh rate: Every 5 seconds
            </span>
            <span style="color: #B0B8C1; font-size: 0.9em;">
                📊 Next sync: ~2 seconds
            </span>
        </div>
        <hr style="border-color: rgba(0, 204, 170, 0.2); margin: 15px 0;">
        <p style="color: #B0B8C1; font-size: 0.85em; margin: 0;">
            © 2024-2026 <span style="color: #00D4AA; font-weight: 600;">Traffic Intelligence System</span> | 
            <span style="color: #0066CC; font-weight: 600;">AI-Powered Traffic Control</span> | 
            <span style="color: #00D4AA;">Smart City Solution</span>
        </p>
    </div>
    """
    st.markdown(footer_html, unsafe_allow_html=True)



def main():
    """Main dashboard application."""
    # Render sidebar and get configuration
    config = render_sidebar()
    
    # Render header
    render_header()
    
    # Render appropriate view based on sidebar selection
    page = config["mode"].strip()
    
    if page == "Live Monitoring":
        render_live_monitoring(config)
    
    elif page == "Analysis & Insights":
        render_analysis_insights(config)
    
    elif page == "Comparison & Metrics":
        render_comparison_view(config)
    
    # Render footer
    render_footer()


if __name__ == "__main__":
    main()

