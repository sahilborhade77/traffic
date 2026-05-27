"""
Advanced Streamlit Dashboard Components.

Provides reusable components for:
- Camera feed display
- Traffic heatmap rendering
- Historical trend charts
- Violation gallery with evidence
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from src.prediction.forecaster import TrafficForecaster

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class CameraFeedGrid:
    """Live camera feed grid display."""
    
    @staticmethod
    def render_feed(lane_name: str, camera_id: str, vehicle_count: int, congestion: float, signal_state: str):
        """Render a single camera feed card."""
        # Color code based on congestion
        if congestion < 0.3:
            color = "#00ff00"  # Green - Low
        elif congestion < 0.6:
            color = "#ffff00"  # Yellow - Medium
        elif congestion < 0.85:
            color = "#ff8800"  # Orange - High
        else:
            color = "#ff0000"  # Red - Critical

        # Create placeholder image (in production, would use actual camera feed)
        fig = go.Figure()
        fig.add_shape(
            type="rect",
            x0=0, y0=0, x1=100, y1=100,
            fillcolor=color,
            opacity=0.3,
            line=dict(color=color, width=3)
        )
        
        fig.add_annotation(
            text=f"{lane_name} ({camera_id})<br>Vehicles: {vehicle_count}<br>Congestion: {congestion:.0%}<br>Signal: {signal_state}",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=12, color="white"),
            bgcolor="rgba(0,0,0,0.5)",
            bordercolor=color,
            borderwidth=2
        )
        
        fig.update_layout(
            title=f"📹 {lane_name}",
            showlegend=False,
            height=250,
            margin=dict(l=0, r=0, t=30, b=0),
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            plot_bgcolor="rgba(0,0,0,0.1)",
        )
        
        return fig
    
    @staticmethod
    def render_grid(lanes_data: List[Dict]) -> None:
        """Render camera feed grid."""
        st.subheader("📹 Live Camera Feed Grid")
        
        cols = st.columns(min(4, len(lanes_data)))
        for idx, lane_data in enumerate(lanes_data):
            with cols[idx % 4]:
                fig = CameraFeedGrid.render_feed(
                    lane_name=lane_data["name"],
                    camera_id=lane_data.get("id", "CAM-XXX"),
                    vehicle_count=lane_data["vehicles"],
                    congestion=lane_data["congestion"],
                    signal_state=lane_data["signal"]
                )
                st.plotly_chart(fig, use_container_width=True)

class MultiCameraStatus:
    """Component to show status/health of all registered cameras."""
    
    @staticmethod
    def render(camera_stats: Dict) -> None:
        st.subheader("🖥️ Network Camera Health")
        
        cols = st.columns(len(camera_stats))
        for i, (cam_id, stat) in enumerate(camera_stats.items()):
            with cols[i]:
                status_color = "green" if stat["is_active"] else "red"
                st.markdown(f"""
                <div style="border-left: 5px solid {status_color}; padding-left: 10px; background: #111; padding: 10px; border-radius: 5px;">
                    <b style="color: {status_color};">{cam_id}</b><br>
                    <small>{stat['name']}</small><br>
                    <span>FPS: {stat.get('fps', 30)}</span><br>
                    <span style="font-size: 0.8em; color: #888;">Processed: {stat['frames_processed']}</span>
                </div>
                """, unsafe_allow_html=True)


class TrafficHeatmap:
    """Real-time traffic heatmap visualization."""
    
    @staticmethod
    def generate_heatmap_data(num_lanes: int = 4, num_timepoints: int = 24) -> pd.DataFrame:
        """Generate realistic heatmap data."""
        hours = np.arange(num_timepoints)
        lanes = [f"Lane {i+1}" for i in range(num_lanes)]
        
        data = []
        for hour in hours:
            # Peak traffic during rush hours
            base_traffic = 30 + 50 * np.sin(hour * np.pi / 12)
            
            for lane in lanes:
                traffic = base_traffic + np.random.normal(0, 10)
                traffic = max(0, min(100, traffic))
                data.append({
                    "Hour": hour,
                    "Lane": lane,
                    "Traffic Density": traffic
                })
        
        return pd.DataFrame(data)
    
    @staticmethod
    def render(timeframe: str = "24h") -> None:
        """Render traffic heatmap."""
        st.subheader("🔥 Real-Time Traffic Heatmap")
        
        # Generate data
        df = TrafficHeatmap.generate_heatmap_data()
        heatmap_data = df.pivot_table(
            values="Traffic Density",
            index="Lane",
            columns="Hour",
            aggfunc="mean"
        )
        
        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=heatmap_data.values,
            x=heatmap_data.columns,
            y=heatmap_data.index,
            colorscale="RdYlGn_r",
            colorbar=dict(title="Density %")
        ))
        
        fig.update_layout(
            title=f"Traffic Density by Lane ({timeframe})",
            xaxis_title="Hour of Day",
            yaxis_title="Lane",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)

    @staticmethod
    def render_forecast() -> None:
        """Render LSTM traffic forecast."""
        st.subheader("🔮 AI Traffic Forecast (Next 15 Minutes)")
        
        try:
            forecaster = TrafficForecaster()
            # Try to load model, fallback to synthetic if fails
            try:
                forecaster.load_model('models/traffic_density_lstm.pth')
            except:
                pass
                
            # Generate 60 mins of "recent" data
            recent_data = np.random.rand(60, 4) * 50
            results = forecaster.predict_next_15_minutes(recent_data)
            
            # Convert to DataFrame for plotting
            preds = np.array(results['predictions'])
            df_forecast = pd.DataFrame(preds, columns=results['lanes'])
            df_forecast['Time'] = results['timestamps']
            
            fig = px.line(
                df_forecast,
                x='Time',
                y=results['lanes'],
                title="Predicted Traffic Density (Next 15 Minutes)",
                labels={"value": "Predicted Density", "Time": "Future Time"}
            )
            fig.update_layout(hovermode="x unified", height=350)
            st.plotly_chart(fig, use_container_width=True)
            
            # Summary
            summary = forecaster.get_prediction_summary(results)
            cols = st.columns(4)
            for i, lane in enumerate(results['lanes']):
                with cols[i]:
                    st.metric(f"{lane} Peak", f"{summary['max_density'][lane]:.1f}", "Predicted")
                    
        except Exception as e:
            st.warning(f"Forecasting engine initializing... {e}")


class HistoricalTrends:
    """Historical trend charts."""
    
    @staticmethod
    def generate_trend_data(days: int = 30) -> Dict[str, pd.DataFrame]:
        """Generate historical trend data."""
        dates = pd.date_range(end=datetime.now(), periods=days)
        
        # Vehicle trends
        vehicle_data = []
        for date in dates:
            hour_data = []
            for hour in range(24):
                # Realistic traffic pattern
                traffic = 50 + 40 * np.sin((hour - 8) * np.pi / 12)
                traffic = max(0, traffic)
                traffic += np.random.normal(0, 5)
                hour_data.append(traffic)
            
            vehicle_data.append({
                "Date": date.date(),
                "Daily Average": np.mean(hour_data),
                "Peak": np.max(hour_data),
                "Min": np.min(hour_data)
            })
        
        df_vehicles = pd.DataFrame(vehicle_data)
        
        # Violation trends
        violation_data = []
        for date in dates:
            violation_data.append({
                "Date": date.date(),
                "Red Light": np.random.poisson(5),
                "Speeding": np.random.poisson(8),
                "Illegal Turn": np.random.poisson(3),
                "Other": np.random.poisson(2)
            })
        
        df_violations = pd.DataFrame(violation_data)
        
        return {
            "vehicles": df_vehicles,
            "violations": df_violations
        }
    
    @staticmethod
    def render(days: int = 30) -> None:
        """Render historical trends."""
        st.subheader("📊 Historical Traffic Trends")
        
        trends = HistoricalTrends.generate_trend_data(days)
        
        # Vehicle trends
        col1, col2 = st.columns(2)
        
        with col1:
            fig_vehicles = px.line(
                trends["vehicles"],
                x="Date",
                y=["Daily Average", "Peak", "Min"],
                title="Vehicle Count Trends",
                labels={"value": "Vehicle Count", "Date": "Date"}
            )
            fig_vehicles.update_layout(hovermode="x unified")
            st.plotly_chart(fig_vehicles, use_container_width=True)
        
        with col2:
            fig_violations = px.bar(
                trends["violations"],
                x="Date",
                y=["Red Light", "Speeding", "Illegal Turn", "Other"],
                title="Violation Trends",
                barmode="stack",
                labels={"value": "Count"}
            )
            st.plotly_chart(fig_violations, use_container_width=True)
        
        # Add Forecast
        TrafficHeatmap.render_forecast()
        
        # Statistics
        st.metric("Avg Daily Vehicles", f"{trends['vehicles']['Daily Average'].mean():.0f}")
        st.metric("Total Violations (30d)", f"{trends['violations'][['Red Light', 'Speeding', 'Illegal Turn', 'Other']].sum().sum():.0f}")


class ViolationGallery:
    """Traffic violation gallery with evidence."""
    
    @staticmethod
    def generate_violations(count: int = 12) -> List[Dict]:
        """Generate sample violation records."""
        violation_types = ["red_light", "speeding", "illegal_turn", "illegal_stop"]
        severity_levels = ["low", "medium", "high", "critical"]
        lanes = ["North", "South", "East", "West"]
        
        violations = []
        for i in range(count):
            violations.append({
                "id": f"VIO-{1001+i}",
                "timestamp": (datetime.now() - timedelta(hours=np.random.randint(0, 72))).strftime("%Y-%m-%d %H:%M"),
                "type": np.random.choice(violation_types),
                "severity": np.random.choice(severity_levels),
                "lane": np.random.choice(lanes),
                "vehicle_id": np.random.randint(1000, 9999),
                "speed": f"{np.random.randint(30, 80)} km/h",
                "processed": np.random.choice([True, False], p=[0.7, 0.3])
            })
        
        return violations
    
    @staticmethod
    def render_violation_card(violation: Dict) -> None:
        """Render a single violation card."""
        severity_colors = {
            "low": "🟢",
            "medium": "🟡",
            "high": "🔴",
            "critical": "🔥"
        }
        
        status_icon = "✅" if violation["processed"] else "⏳"
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.write(f"### {violation['id']}")
            st.write(f"**Type:** {violation['type'].replace('_', ' ').title()}")
            st.write(f"**Lane:** {violation['lane']} | **Vehicle:** {violation['vehicle_id']}")
            st.write(f"**Time:** {violation['timestamp']}")
        
        with col2:
            st.write(f"{severity_colors.get(violation['severity'], '❓')} **{violation['severity'].upper()}**")
            st.write(f"**Speed:** {violation['speed']}")
        
        with col3:
            st.write(f"{status_icon}")
            if not violation["processed"]:
                if st.button("Process", key=f"btn_{violation['id']}"):
                    st.success("Violation processed!")
            
            # Show PDF link if processed
            if violation["processed"]:
                challan_path = PROJECT_ROOT / "output" / "challans" / f"echallan_{violation['id']}.pdf"
                st.markdown(f"[📄 View Challan]({challan_path.as_uri()})")
    
    @staticmethod
    def render(sort_by: str = "recent", filter_type: str = "all", limit: int = 12) -> None:
        """Render violation gallery."""
        st.subheader("⚠️ Traffic Violation Gallery")
        
        # Controls
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            sort_option = st.selectbox("Sort By", ["Recent", "Severity", "Type"])
        with col2:
            type_filter = st.selectbox("Violation Type", ["All"] + ["Red Light", "Speeding", "Illegal Turn", "Illegal Stop"])
        with col3:
            processed_filter = st.selectbox("Status", ["All", "Processed", "Pending"])
        
        # Generate violations
        violations = ViolationGallery.generate_violations(limit)
        
        # Filter
        if type_filter != "All":
            violations = [v for v in violations if v["type"] == type_filter.lower().replace(" ", "_")]
        
        if processed_filter == "Processed":
            violations = [v for v in violations if v["processed"]]
        elif processed_filter == "Pending":
            violations = [v for v in violations if not v["processed"]]
        
        # Sort
        if sort_option == "Severity":
            severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
            violations.sort(key=lambda x: severity_order.get(x["severity"], 0), reverse=True)
        elif sort_option == "Type":
            violations.sort(key=lambda x: x["type"])
        
        # Display
        st.write(f"**Showing {len(violations)} violations**")
        
        for violation in violations[:limit]:
            ViolationGallery.render_violation_card(violation)
            st.divider()
