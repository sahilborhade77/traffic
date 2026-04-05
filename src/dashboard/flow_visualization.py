"""
Traffic Flow Visualization with Animated Scatter Plots.

Visualizes:
- Vehicle trajectories and movement patterns
- Color-coded speed indicators
- Real-time traffic flow animation
- Intersection view with lane tracking
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple


class TrafficFlowVisualization:
    """Traffic flow visualization with animated trajectories."""
    
    @staticmethod
    def generate_trajectory_data(num_vehicles: int = 50, timesteps: int = 30) -> pd.DataFrame:
        """
        Generate realistic vehicle trajectory data.
        
        Returns DataFrame with columns:
        - time: timestep (0-timesteps)
        - vehicle_id: unique vehicle ID
        - x, y: position on road
        - speed: vehicle speed
        - lane: lane name
        """
        lanes = {
            "North": {"x_range": (40, 60), "y_range": (60, 100)},
            "South": {"x_range": (40, 60), "y_range": (0, 40)},
            "East": {"x_range": (60, 100), "y_range": (40, 60)},
            "West": {"x_range": (0, 40), "y_range": (40, 60)},
        }
        
        trajectories = []
        
        for vehicle_id in range(num_vehicles):
            lane = np.random.choice(list(lanes.keys()))
            lane_config = lanes[lane]
            
            # Random starting position in lane
            start_x = np.random.uniform(*lane_config["x_range"])
            start_y = np.random.uniform(*lane_config["y_range"])
            
            # Direction based on lane
            if lane == "North":
                direction = np.array([0, 1])
            elif lane == "South":
                direction = np.array([0, -1])
            elif lane == "East":
                direction = np.array([1, 0])
            else:  # West
                direction = np.array([-1, 0])
            
            # Generate trajectory
            position = np.array([start_x, start_y], dtype=float)
            base_speed = np.random.uniform(5, 20)
            
            for t in range(timesteps):
                # Speed varies with conditions
                congestion_factor = 1 - (0.3 + 0.7 * np.sin(t * np.pi / timesteps))
                speed = base_speed * congestion_factor
                
                # Stop occasionally (traffic light)
                if t > timesteps * 0.5 and np.random.random() < 0.3:
                    speed = 0
                
                # Movement
                position = position + direction * speed * 0.5
                
                # Boundary wrapping
                position = np.clip(position, 0, 100)
                
                trajectories.append({
                    "time": t,
                    "vehicle_id": f"V{vehicle_id:04d}",
                    "x": position[0],
                    "y": position[1],
                    "speed": speed,
                    "lane": lane,
                    "color_group": int(speed // 5),  # For color mapping
                })
        
        return pd.DataFrame(trajectories)
    
    @staticmethod
    def render_animated_trajectories() -> None:
        """Render animated vehicle trajectories."""
        st.subheader("🚗 Animated Vehicle Trajectories")
        
        # Generate data
        df = TrafficFlowVisualization.generate_trajectory_data(num_vehicles=50, timesteps=30)
        
        # Create animated scatter plot
        fig = px.scatter(
            df,
            x="x",
            y="y",
            animation_frame="time",
            animation_group="vehicle_id",
            size="speed",
            color="speed",
            hover_name="vehicle_id",
            hover_data={"lane": True, "speed": ":.1f", "x": ":.1f", "y": ":.1f"},
            title="Real-Time Vehicle Movement in Intersection",
            labels={"x": "X Position", "y": "Y Position", "speed": "Speed (m/s)"},
            color_continuous_scale="RdYlGn_r",
            range_x=[0, 100],
            range_y=[0, 100],
            size_max=20,
        )
        
        # Add lane divisions
        fig.add_shape(
            type="line", x0=50, y0=0, x1=50, y1=100,
            line=dict(color="white", width=2, dash="dash")
        )
        fig.add_shape(
            type="line", x0=0, y0=50, x1=100, y1=50,
            line=dict(color="white", width=2, dash="dash")
        )
        
        # Add lane labels
        fig.add_annotation(text="North", x=75, y=95, showarrow=False, font=dict(size=12, color="white"))
        fig.add_annotation(text="South", x=25, y=5, showarrow=False, font=dict(size=12, color="white"))
        fig.add_annotation(text="East", x=95, y=75, showarrow=False, font=dict(size=12, color="white"))
        fig.add_annotation(text="West", x=5, y=25, showarrow=False, font=dict(size=12, color="white"))
        
        fig.update_layout(
            height=600,
            plot_bgcolor="rgba(0, 0, 0, 0.3)",
            paper_bgcolor="rgba(0, 0, 0, 0.1)",
            hovermode="closest",
            coloraxis_colorbar=dict(title="Speed<br>(m/s)")
        )
        
        fig.update_xaxes(range=[0, 100])
        fig.update_yaxes(range=[0, 100])
        
        st.plotly_chart(fig, use_container_width=True)
    
    @staticmethod
    def render_speed_distribution() -> None:
        """Render speed distribution by lane."""
        st.subheader("📊 Speed Distribution by Lane")
        
        df = TrafficFlowVisualization.generate_trajectory_data(num_vehicles=100, timesteps=20)
        
        # Speed statistics
        col1, col2, col3, col4 = st.columns(4)
        
        lanes = df["lane"].unique()
        for col, lane in zip([col1, col2, col3, col4], lanes):
            lane_data = df[df["lane"] == lane]
            avg_speed = lane_data["speed"].mean()
            max_speed = lane_data["speed"].max()
            
            with col:
                st.metric(f"{lane} Lane", f"{avg_speed:.1f} m/s", f"Max: {max_speed:.1f}")
        
        # Distribution plot
        fig = px.box(
            df,
            x="lane",
            y="speed",
            color="lane",
            title="Speed Distribution by Lane",
            labels={"speed": "Speed (m/s)", "lane": "Lane"},
            points="all"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    @staticmethod
    def render_heatmap_density() -> None:
        """Render 2D density heatmap of vehicle positions."""
        st.subheader("🔥 Traffic Density Heatmap")
        
        df = TrafficFlowVisualization.generate_trajectory_data(num_vehicles=200, timesteps=10)
        
        # Create 2D histogram
        fig = go.Figure(data=go.Histogram2d(
            x=df["x"],
            y=df["y"],
            nbinsx=10,
            nbinsy=10,
            colorscale="Hot",
            showscale=True,
            colorbar=dict(title="Vehicle<br>Count")
        ))
        
        # Add lane divisions
        fig.add_shape(type="line", x0=50, y0=0, x1=50, y1=100, line=dict(color="white", width=2))
        fig.add_shape(type="line", x0=0, y0=50, x1=100, y1=50, line=dict(color="white", width=2))
        
        fig.update_layout(
            title="Vehicle Density Distribution",
            xaxis_title="X Position",
            yaxis_title="Y Position",
            height=500,
            plot_bgcolor="rgba(0, 0, 0, 0.2)",
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    @staticmethod
    def render_flow_metrics() -> None:
        """Render traffic flow metrics."""
        st.subheader("📈 Traffic Flow Metrics")
        
        df = TrafficFlowVisualization.generate_trajectory_data(num_vehicles=80, timesteps=25)
        
        col1, col2, col3 = st.columns(3)
        
        # Calculate metrics
        total_vehicles = df["vehicle_id"].nunique()
        avg_speed = df["speed"].mean()
        stopped_vehicles = (df["speed"] < 0.5).sum() / len(df) * 100
        
        with col1:
            st.metric("Total Vehicles", total_vehicles)
        
        with col2:
            st.metric("Avg Speed", f"{avg_speed:.1f} m/s")
        
        with col3:
            st.metric("Stopped %", f"{stopped_vehicles:.1f}%")
        
        # Time series of metrics
        metrics_by_time = df.groupby("time").agg({
            "speed": "mean",
            "vehicle_id": "nunique"
        }).reset_index()
        metrics_by_time.columns = ["Time", "Avg Speed", "Active Vehicles"]
        
        fig_metrics = px.line(
            metrics_by_time,
            x="Time",
            y=["Avg Speed", "Active Vehicles"],
            title="Traffic Flow Metrics Over Time",
            markers=True
        )
        
        fig_metrics.update_layout(hovermode="x unified")
        st.plotly_chart(fig_metrics, use_container_width=True)
    
    @staticmethod
    def render_all() -> None:
        """Render all traffic flow visualizations."""
        TabTrafficFlow = st.tabs([
            "Animated Trajectories",
            "Speed Distribution",
            "Density Heatmap",
            "Flow Metrics"
        ])
        
        with TabTrafficFlow[0]:
            TrafficFlowVisualization.render_animated_trajectories()
        
        with TabTrafficFlow[1]:
            TrafficFlowVisualization.render_speed_distribution()
        
        with TabTrafficFlow[2]:
            TrafficFlowVisualization.render_heatmap_density()
        
        with TabTrafficFlow[3]:
            TrafficFlowVisualization.render_flow_metrics()
