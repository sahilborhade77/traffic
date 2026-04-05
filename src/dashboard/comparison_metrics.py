"""
Signal Timing Comparison Metrics Widget.

Compares performance metrics between:
- Fixed timing signal control (baseline)
- Adaptive AI-based signal control (optimization)

Shows efficiency improvements and detailed comparisons.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple


class ComparisonMetrics:
    """Signal timing comparison and efficiency analysis."""
    
    @staticmethod
    def generate_control_comparison() -> Dict:
        """
        Generate performance comparison data between fixed and adaptive control.
        
        Returns dict with baseline and optimized metrics.
        """
        # Fixed timing baseline (typical city signals)
        fixed = {
            "name": "Fixed Timing",
            "avg_wait_time": 45.3,
            "peak_queue_length": 28,
            "total_vehicles": 450,
            "total_delay": 2840,
            "throughput": 180,
            "red_light_violations": 12,
            "average_speed": 18.5,
            "fuel_consumption": 1240,  # liters
            "co2_emissions": 3100,  # grams
        }
        
        # Adaptive AI control (with optimization)
        adaptive = {
            "name": "Adaptive AI Control",
            "avg_wait_time": 32.1,
            "peak_queue_length": 18,
            "total_vehicles": 450,
            "total_delay": 1890,
            "throughput": 225,
            "red_light_violations": 3,
            "average_speed": 24.2,
            "fuel_consumption": 980,  # liters
            "co2_emissions": 2450,  # grams
        }
        
        return {"fixed": fixed, "adaptive": adaptive}
    
    @staticmethod
    def calculate_improvements(fixed: Dict, adaptive: Dict) -> Dict:
        """Calculate percentage improvements from fixed to adaptive."""
        improvements = {
            "avg_wait_time": ((fixed["avg_wait_time"] - adaptive["avg_wait_time"]) / fixed["avg_wait_time"]) * 100,
            "peak_queue_length": ((fixed["peak_queue_length"] - adaptive["peak_queue_length"]) / fixed["peak_queue_length"]) * 100,
            "total_delay": ((fixed["total_delay"] - adaptive["total_delay"]) / fixed["total_delay"]) * 100,
            "throughput": ((adaptive["throughput"] - fixed["throughput"]) / fixed["throughput"]) * 100,
            "red_light_violations": ((fixed["red_light_violations"] - adaptive["red_light_violations"]) / fixed["red_light_violations"]) * 100,
            "average_speed": ((adaptive["average_speed"] - fixed["average_speed"]) / fixed["average_speed"]) * 100,
            "fuel_consumption": ((fixed["fuel_consumption"] - adaptive["fuel_consumption"]) / fixed["fuel_consumption"]) * 100,
            "co2_emissions": ((fixed["co2_emissions"] - adaptive["co2_emissions"]) / fixed["co2_emissions"]) * 100,
        }
        return improvements
    
    @staticmethod
    def render_kpi_comparison() -> None:
        """Render key performance indicator comparison cards."""
        st.subheader("📊 Key Performance Indicators")
        
        data = ComparisonMetrics.generate_control_comparison()
        fixed = data["fixed"]
        adaptive = data["adaptive"]
        improvements = ComparisonMetrics.calculate_improvements(fixed, adaptive)
        
        # Main metrics
        col1, col2, col3 = st.columns(3)
        
        # Average Wait Time
        with col1:
            st.metric(
                "Average Wait Time (seconds)",
                f"{adaptive['avg_wait_time']:.1f}s",
                f"-{improvements['avg_wait_time']:.1f}% vs Fixed",
                delta_color="inverse"
            )
        
        # Peak Queue Length
        with col2:
            st.metric(
                "Peak Queue Length (vehicles)",
                f"{adaptive['peak_queue_length']}",
                f"-{improvements['peak_queue_length']:.1f}% vs Fixed",
                delta_color="inverse"
            )
        
        # Throughput
        with col3:
            st.metric(
                "Throughput (vehicles/hour)",
                f"{adaptive['throughput']}",
                f"+{improvements['throughput']:.1f}% vs Fixed",
            )
        
        st.divider()
        
        # Additional metrics
        col4, col5, col6 = st.columns(3)
        
        with col4:
            st.metric(
                "Total Delay (seconds)",
                f"{adaptive['total_delay']}",
                f"-{improvements['total_delay']:.1f}% vs Fixed",
                delta_color="inverse"
            )
        
        with col5:
            st.metric(
                "Violations (red light)",
                f"{adaptive['red_light_violations']}",
                f"-{improvements['red_light_violations']:.1f}% vs Fixed",
                delta_color="inverse"
            )
        
        with col6:
            st.metric(
                "Avg Speed (km/h)",
                f"{adaptive['average_speed']:.1f}",
                f"+{improvements['average_speed']:.1f}% vs Fixed"
            )
    
    @staticmethod
    def render_detailed_metrics_table() -> None:
        """Render detailed metrics comparison table."""
        st.subheader("📋 Detailed Metrics Comparison")
        
        data = ComparisonMetrics.generate_control_comparison()
        fixed = data["fixed"]
        adaptive = data["adaptive"]
        improvements = ComparisonMetrics.calculate_improvements(fixed, adaptive)
        
        # Create comparison DataFrame
        metrics_names = [
            "Average Wait Time (s)",
            "Peak Queue Length (vehicles)",
            "Total Delay (seconds)",
            "Throughput (veh/hour)",
            "Red Light Violations",
            "Average Speed (km/h)",
            "Fuel Consumption (liters)",
            "CO₂ Emissions (grams)"
        ]
        
        metrics_keys = [
            "avg_wait_time",
            "peak_queue_length",
            "total_delay",
            "throughput",
            "red_light_violations",
            "average_speed",
            "fuel_consumption",
            "co2_emissions"
        ]
        
        comparison_data = []
        for name, key in zip(metrics_names, metrics_keys):
            improvement = improvements[key]
            comparison_data.append({
                "Metric": name,
                "Fixed Timing": f"{fixed[key]:.1f}" if isinstance(fixed[key], float) else fixed[key],
                "Adaptive AI": f"{adaptive[key]:.1f}" if isinstance(adaptive[key], float) else adaptive[key],
                "Improvement": f"{improvement:+.1f}%",
                "Better": "✅ Adaptive" if improvement > 0 else "❌ Fixed"
            })
        
        df_comparison = pd.DataFrame(comparison_data)
        st.dataframe(df_comparison, use_container_width=True, hide_index=True)
    
    @staticmethod
    def render_bar_chart_comparison() -> None:
        """Render side-by-side bar chart comparison."""
        st.subheader("📈 Performance Comparison Chart")
        
        data = ComparisonMetrics.generate_control_comparison()
        fixed = data["fixed"]
        adaptive = data["adaptive"]
        
        # Key metrics for visualization
        metrics = [
            ("Avg Wait Time", "avg_wait_time", "seconds"),
            ("Peak Queue", "peak_queue_length", "vehicles"),
            ("Total Delay", "total_delay", "seconds"),
            ("Throughput", "throughput", "veh/hour"),
        ]
        
        comparison_data = []
        for metric_name, key, unit in metrics:
            comparison_data.append({
                "Metric": metric_name,
                "Fixed": fixed[key],
                "Adaptive": adaptive[key]
            })
        
        df_metrics = pd.DataFrame(comparison_data)
        
        # Create grouped bar chart
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=df_metrics["Metric"],
            y=df_metrics["Fixed"],
            name="Fixed Timing",
            marker_color="rgb(255, 100, 100)",
        ))
        
        fig.add_trace(go.Bar(
            x=df_metrics["Metric"],
            y=df_metrics["Adaptive"],
            name="Adaptive AI",
            marker_color="rgb(100, 200, 100)",
        ))
        
        fig.update_layout(
            barmode="group",
            title="Control Method Comparison",
            xaxis_title="Metrics",
            yaxis_title="Value",
            height=400,
            hovermode="x unified"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    @staticmethod
    def render_efficiency_gauge() -> None:
        """Render efficiency improvement gauge."""
        st.subheader("⚡ Overall Efficiency Improvement")
        
        data = ComparisonMetrics.generate_control_comparison()
        fixed = data["fixed"]
        adaptive = data["adaptive"]
        improvements = ComparisonMetrics.calculate_improvements(fixed, adaptive)
        
        # Calculate overall improvement score
        improvement_scores = [
            improvements["throughput"],  # Higher is better
            improvements["avg_wait_time"],  # Higher (negative) means better
            improvements["total_delay"],  # Higher (negative) means better
            improvements["fuel_consumption"],  # Higher (negative) means better
            improvements["co2_emissions"],  # Higher (negative) means better
        ]
        
        overall_improvement = np.mean(improvement_scores)
        
        # Create gauge chart
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=overall_improvement,
            title={"text": "Efficiency Improvement Score"},
            delta={"reference": 0, "suffix": "%"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "darkblue"},
                "steps": [
                    {"range": [0, 25], "color": "lightcoral"},
                    {"range": [25, 50], "color": "lightyellow"},
                    {"range": [50, 75], "color": "lightgreen"},
                    {"range": [75, 100], "color": "darkgreen"}
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": 50
                }
            }
        ))
        
        fig.update_layout(height=400)
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Interpretation
        if overall_improvement >= 75:
            st.success(f"🎉 Excellent improvement: {overall_improvement:.1f}%")
        elif overall_improvement >= 50:
            st.info(f"✅ Good improvement: {overall_improvement:.1f}%")
        elif overall_improvement >= 25:
            st.warning(f"⚠️ Moderate improvement: {overall_improvement:.1f}%")
        else:
            st.error(f"❌ Minimal improvement: {overall_improvement:.1f}%")
    
    @staticmethod
    def render_environmental_impact() -> None:
        """Render environmental impact comparison."""
        st.subheader("🌱 Environmental Impact")
        
        data = ComparisonMetrics.generate_control_comparison()
        fixed = data["fixed"]
        adaptive = data["adaptive"]
        improvements = ComparisonMetrics.calculate_improvements(fixed, adaptive)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "Fuel Consumption",
                f"{adaptive['fuel_consumption']} L",
                f"-{improvements['fuel_consumption']:.1f}% reduction",
                delta_color="inverse"
            )
        
        with col2:
            st.metric(
                "CO₂ Emissions",
                f"{adaptive['co2_emissions']} g",
                f"-{improvements['co2_emissions']:.1f}% reduction",
                delta_color="inverse"
            )
        
        # Environmental benefits visualization
        env_data = {
            "Control": ["Fixed", "Adaptive"],
            "Fuel (L)": [fixed["fuel_consumption"], adaptive["fuel_consumption"]],
            "CO₂ (g)": [fixed["co2_emissions"], adaptive["co2_emissions"]]
        }
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=env_data["Control"],
            y=env_data["Fuel (L)"],
            name="Fuel Consumption (L)",
            marker_color="rgb(200, 100, 50)",
        ))
        
        fig.add_trace(go.Bar(
            x=env_data["Control"],
            y=env_data["CO₂ (g)"],
            name="CO₂ Emissions (g)",
            marker_color="rgb(100, 150, 200)",
        ))
        
        fig.update_layout(
            barmode="group",
            title="Environmental Impact Comparison",
            xaxis_title="Control Method",
            yaxis_title="Amount",
            height=400,
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    @staticmethod
    def render_time_series_comparison() -> None:
        """Render time-series performance comparison over a day."""
        st.subheader("📉 Performance Over Time (24-hour cycle)")
        
        hours = np.arange(0, 24)
        
        # Simulate wait time variations throughout the day
        fixed_wait_times = 45 + 15 * np.sin(hours * np.pi / 12) + np.random.normal(0, 3, 24)
        adaptive_wait_times = 32 + 8 * np.sin(hours * np.pi / 12) + np.random.normal(0, 2, 24)
        
        # Ensure non-negative
        fixed_wait_times = np.maximum(fixed_wait_times, 20)
        adaptive_wait_times = np.maximum(adaptive_wait_times, 15)
        
        df_timeseries = pd.DataFrame({
            "Hour": hours,
            "Fixed Timing": fixed_wait_times,
            "Adaptive AI": adaptive_wait_times
        })
        
        fig = px.line(
            df_timeseries,
            x="Hour",
            y=["Fixed Timing", "Adaptive AI"],
            title="Average Wait Time Throughout the Day",
            markers=True,
            labels={"Hour": "Hour of Day", "value": "Wait Time (seconds)"}
        )
        
        fig.update_layout(hovermode="x unified", height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    @staticmethod
    def render_all() -> None:
        """Render all comparison metrics sections."""
        ComparisonMetrics.render_kpi_comparison()
        
        st.divider()
        
        ComparisonMetrics.render_bar_chart_comparison()
        
        st.divider()
        
        comparison_tabs = st.tabs([
            "Detailed Table",
            "Efficiency Score",
            "Environmental Impact",
            "24-Hour Trend"
        ])
        
        with comparison_tabs[0]:
            ComparisonMetrics.render_detailed_metrics_table()
        
        with comparison_tabs[1]:
            ComparisonMetrics.render_efficiency_gauge()
        
        with comparison_tabs[2]:
            ComparisonMetrics.render_environmental_impact()
        
        with comparison_tabs[3]:
            ComparisonMetrics.render_time_series_comparison()
