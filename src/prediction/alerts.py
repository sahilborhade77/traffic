import time
import logging
import numpy as np

logger = logging.getLogger(__name__)

class CongestionDetector:
    """
    Analyzes current traffic against static thresholds and historical averages.
    Generates actionable alerts for traffic management.
    """
    def __init__(self):
        self.thresholds = {
            'low': 5,      # vehicles per lane
            'medium': 10,
            'high': 15,
            'critical': 20
        }
        self.congestion_history = []
    
    def detect_congestion_level(self, lane_densities):
        """
        Classifies congestion level for each lane based on density thresholds.
        :param lane_densities: Dict {lane_name: density_value}
        """
        levels = {}
        for lane, density in lane_densities.items():
            if density >= self.thresholds['critical']:
                levels[lane] = 'CRITICAL'
            elif density >= self.thresholds['high']:
                levels[lane] = 'HIGH'
            elif density >= self.thresholds['medium']:
                levels[lane] = 'MEDIUM'
            else:
                levels[lane] = 'LOW'
        return levels
    
    def detect_anomalies(self, current_densities, historical_stats):
        """
        Detects unusual traffic patterns using Z-score (statistical deviation).
        :param current_densities: Dict {lane_name: current_val}
        :param historical_stats: Dict {lane_name: {'mean': float, 'std': float}}
        """
        anomalies = {}
        for lane, density in current_densities.items():
            if lane in historical_stats:
                mean = historical_stats[lane]['mean']
                std = historical_stats[lane]['std']
                
                # Avoid division by zero
                if std > 0:
                    z_score = (density - mean) / std
                    if abs(z_score) > 3:  # 3 standard deviations is usually an outlier
                        anomalies[lane] = {
                            'type': 'UNUSUAL_TRAFFIC',
                            'severity': 'high' if z_score > 3 else 'low',
                            'z_score': round(float(z_score), 2),
                            'current': density,
                            'normal': round(mean, 2)
                        }
        return anomalies
    
    def generate_alert(self, lane, level, predicted_duration=10):
        """
        Generates and dispatches a JSON-ready traffic alert.
        """
        alert = {
            'id': int(time.time() * 1000),
            'timestamp': time.ctime(),
            'lane': lane,
            'congestion_level': level,
            'predicted_duration_minutes': predicted_duration,
            'recommended_actions': self.get_recommended_action(level)
        }
        
        # Log to system console
        self._dispatch_alert(alert)
        return alert

    def _dispatch_alert(self, alert):
        """Dispatches alert to the logging system/dashboard."""
        msg = f"🔔 TRAFFIC ALERT: [{alert['congestion_level']}] on {alert['lane']}. Recommended: {alert['recommended_actions'][0]}"
        logger.warning(msg)

    def get_recommended_action(self, level):
        """AI-driven action recommendations based on severity."""
        actions = {
            'CRITICAL': [
                'Extend green light duration by 50%',
                'Activate alternate route signage',
                'Deploy traffic officers',
                'Notify connected vehicles to reroute'
            ],
            'HIGH': [
                'Extend green light duration by 30%',
                'Update navigation apps with delay estimates',
                'Monitor for potential accidents in lane'
            ],
            'MEDIUM': [
                'Extend green light duration by 15%',
                'Continue monitoring sensors'
            ],
            'LOW': [
                'Maintain standard signal sequences',
                'No manual action required'
            ]
        }
        return actions.get(level, ["Continue monitoring"])
