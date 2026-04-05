"""
System Architecture Diagram Generator.

Generates visual architecture diagrams showing:
- System components and layers
- Data flow between components
- External integrations
- Deployment topology
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.container import Docker
from diagrams.onprem.database import PostgreSQL, Redis
from diagrams.onprem.queue import Kafka
from diagrams.onprem.monitoring import Prometheus, Grafana
from diagrams.onprem.vcs import Github
from diagrams.onprem.ci import GithubActions
from diagrams.onprem.compute import Server
from diagrams.onprem.network import Internet
from diagrams.custom import Custom
from diagrams.c4 import Person, Container, Database, System, SystemBoundary
import os


def generate_high_level_architecture():
    """Generate high-level system architecture diagram."""
    with Diagram("Traffic Management System - High Level Architecture", show=False, direction="TB"):
        
        with Cluster("External Systems"):
            cameras = Custom("Traffic Cameras", "docs/assets/camera.png")
            signals = Custom("Traffic Signals", "docs/assets/signal.png")
        
        with Cluster("Traffic Management Platform"):
            with Cluster("Data Ingestion"):
                vision = Custom("Vision Processing", "docs/assets/vision.png")
                detector = Custom("Vehicle Detector", "docs/assets/detector.png")
            
            with Cluster("Core Services"):
                api = Docker("FastAPI Server")
                dashboard = Docker("Streamlit Dashboard")
                controller = Custom("Signal Controller", "docs/assets/control.png")
            
            with Cluster("Data Layer"):
                db = PostgreSQL("PostgreSQL")
                cache = Redis("Redis Cache")
            
            with Cluster("Analytics & Monitoring"):
                metrics = Prometheus("Prometheus")
                viz = Grafana("Grafana")
        
        with Cluster("Infrastructure"):
            registry = Github("Container Registry")
            ci_cd = GithubActions("CI/CD Pipeline")
        
        # Data flow
        cameras >> detector >> vision
        signals >> controller
        
        vision >> api
        vision >> cache
        
        api >> db
        api >> cache
        api >> dashboard
        
        controller >> api
        
        api >> metrics
        metrics >> viz
        
        registry >> ci_cd


def generate_detailed_data_flow():
    """Generate detailed data flow diagram."""
    with Diagram("Traffic Management - Detailed Data Flow", show=False, direction="LR"):
        
        with Cluster("Input Layer"):
            rtsp = Custom("RTSP Streams", "docs/assets/stream.png")
            sensors = Custom("Traffic Sensors", "docs/assets/sensor.png")
        
        with Cluster("Processing Layer"):
            with Cluster("Real-time Processing"):
                yolo = Custom("YOLOv8 Detector", "docs/assets/yolo.png")
                tracker = Custom("Vehicle Tracker", "docs/assets/tracker.png")
                analyzer = Custom("Analytics Engine", "docs/assets/analyzer.png")
            
            with Cluster("Decision Making"):
                controller = Custom("Signal Controller", "docs/assets/control.png")
                optimizer = Custom("Traffic Optimizer", "docs/assets/optimizer.png")
        
        with Cluster("Storage Layer"):
            postgres = PostgreSQL("PostgreSQL\n(Time-series)")
            redis = Redis("Redis\n(Cache)")
            s3 = Custom("S3 Storage\n(Models/Videos)", "docs/assets/storage.png")
        
        with Cluster("Presentation Layer"):
            api = Docker("REST API")
            dashboard = Docker("Web Dashboard")
            alerts = Custom("Alert System", "docs/assets/alert.png")
        
        # Data flow
        rtsp >> yolo >> tracker >> analyzer
        sensors >> analyzer
        
        analyzer >> optimize: "queue_lengths"
        analyzer >> controller: "detections"
        optimize >> controller: "timings"
        
        analyzer >> postgres
        analyzer >> redis
        analyzer >> s3
        
        postgres >> api
        redis >> api
        
        api >> dashboard
        analyzer >> alerts
        controller >> alerts


def generate_deployment_architecture():
    """Generate deployment architecture diagram."""
    with Diagram("Traffic Management - Deployment Architecture", show=False, direction="TB"):
        
        users = Person("Users/Operators")
        
        with Cluster("Load Balancer"):
            lb = Custom("NGINX/ALB", "docs/assets/loadbalancer.png")
        
        with Cluster("Kubernetes Cluster"):
            with Cluster("API Services"):
                api_pods = [
                    Docker("API Pod 1"),
                    Docker("API Pod 2"),
                    Docker("API Pod 3"),
                ]
            
            with Cluster("Dashboard Services"):
                dash_pods = [
                    Docker("Dashboard Pod 1"),
                    Docker("Dashboard Pod 2"),
                ]
            
            with Cluster("Vision Services (GPU)"):
                vision_pods = [
                    Docker("Vision Pod 1\n(GPU: 1x A100)"),
                    Docker("Vision Pod 2\n(GPU: 1x A100)"),
                ]
            
            with Cluster("Message Queue"):
                queue = Kafka("Kafka Cluster")
            
            with Cluster("Databases"):
                postgres = PostgreSQL("PostgreSQL\nReplicated")
                redis = Redis("Redis\nCluster")
        
        with Cluster("Monitoring Stack"):
            prometheus = Prometheus("Prometheus")
            grafana = Grafana("Grafana")
        
        # Connections
        users >> lb
        
        lb >> api_pods
        lb >> dash_pods
        
        api_pods >> queue
        vision_pods >> queue
        queue >> postgres
        queue >> redis
        
        api_pods >> postgres
        api_pods >> redis
        
        vision_pods >> postgres
        
        api_pods >> prometheus
        vision_pods >> prometheus
        prometheus >> grafana


def generate_system_components():
    """Generate detailed system components diagram."""
    with Diagram("Traffic Management - System Components", show=False, direction="TB"):
        
        with Cluster("Vision & Detection"):
            cameras = Custom("Camera Feeds (×4)", "docs/assets/camera.png")
            reader = Docker("Video Reader")
            preprocessor = Docker("Image Preprocessor")
            yolo = Docker("YOLOv8 Detector")
            tracker = Docker("Centroid Tracker")
            analyzer = Docker("Vision Analyzer")
            
            cameras >> reader >> preprocessor >> yolo >> tracker >> analyzer
        
        with Cluster("Signal Control"):
            controller = Docker("Signal Controller")
            fixed = Docker("Fixed Timing (Baseline)")
            adaptive = Docker("Adaptive Timing (AI)")
            optimizer = Docker("RL Optimizer")
            
            controller >> [fixed, adaptive, optimizer]
        
        with Cluster("Data Management"):
            aggregator = Docker("Data Aggregator")
            db_manager = Docker("Database Manager")
            cache_manager = Docker("Cache Manager")
            
            aggregator >> [db_manager, cache_manager]
        
        with Cluster("API & Dashboard"):
            api = Docker("FastAPI Server")
            dashboard = Docker("Streamlit UI")
            ws_server = Docker("WebSocket Server")
            
            api >> dashboard
            api >> ws_server
        
        with Cluster("Infrastructure"):
            postgres = PostgreSQL("PostgreSQL")
            redis = Redis("Redis")
            s3 = Custom("S3/MinIO", "docs/assets/storage.png")
            
            [db_manager, cache_manager] >> postgres
            cache_manager >> redis
            [analyzer, yolo] >> s3
        
        # Main flow
        analyzer >> aggregator
        aggregator >> api
        aggregator >> controller
        api >> dashboard


def generate_ci_cd_pipeline():
    """Generate CI/CD pipeline diagram."""
    with Diagram("Traffic Management - CI/CD Pipeline", show=False, direction="LR"):
        
        with Cluster("Source Control"):
            github = Github("GitHub\nRepository")
        
        with Cluster("CI/CD Stage"):
            with Cluster("Testing"):
                lint = Custom("Lint", "docs/assets/test.png")
                unit = Custom("Unit Tests", "docs/assets/test.png")
                integration = Custom("Integration Tests", "docs/assets/test.png")
                security = Custom("Security Scan", "docs/assets/security.png")
            
            with Cluster("Build"):
                build = Docker("Build Docker\nImage")
                scan = Custom("Image Scan", "docs/assets/security.png")
        
        with Cluster("Deployment"):
            with Cluster("Staging"):
                staging = Docker("Deploy to\nStaging")
                test_staging = Custom("Smoke Tests", "docs/assets/test.png")
            
            with Cluster("Production"):
                prod = Docker("Deploy to\nProduction")
                rollout = Custom("Gradual Rollout", "docs/assets/deploy.png")
        
        with Cluster("Monitoring"):
            prometheus = Prometheus("Prometheus")
            alerts = Custom("Alerts", "docs/assets/alert.png")
        
        github >> [lint, unit, integration, security]
        [lint, unit, integration, security] >> build
        build >> scan >> staging
        staging >> test_staging >> prod >> rollout
        rollout >> [prometheus, alerts]


def generate_database_schema():
    """Generate database schema diagram."""
    with Diagram("Traffic Management - Database Schema", show=False, direction="TB"):
        
        with Cluster("Dimension Tables"):
            lanes = Database("lanes\n(lane_id, name)")
            signals = Database("signals\n(signal_id, type)")
            cameras = Database("cameras\n(camera_id, url)")
        
        with Cluster("Fact Tables"):
            detections = Database("vehicle_detections\n(detection_id, timestamp, confidence)")
            violations = Database("violation_records\n(violation_id, type, severity)")
            wait_times = Database("wait_time_observations\n(observation_id, queue_length)")
        
        with Cluster("Aggregate Tables"):
            hourly = Database("hourly_statistics\n(hour_start, vehicle_count, avg_speed)")
            daily = Database("daily_statistics\n(date, peak_hour, total_violations)")
        
        with Cluster("Operational"):
            states = Database("signal_states\n(timestamp, state)")
            snapshots = Database("traffic_snapshots\n(timestamp, total_vehicles)")
        
        # Relationships
        lanes >> [detections, violations, wait_times, states]
        cameras >> detections
        detections >> [violations, hourly, daily]
        wait_times >> [hourly, daily]
        states >> snapshots


def generate_data_pipeline():
    """Generate data pipeline diagram."""
    with Diagram("Traffic Management - Data Pipeline", show=False, direction="TB"):
        
        with Cluster("Ingestion"):
            sources = [
                Custom("RTSP Streams", "docs/assets/stream.png"),
                Custom("CSV Uploads", "docs/assets/data.png"),
                Custom("API Webhooks", "docs/assets/api.png"),
            ]
        
        with Cluster("Processing"):
            validation = Docker("Data\nValidation")
            transformation = Docker("Data\nTransformation")
            enrichment = Docker("Data\nEnrichment")
            aggregation = Docker("Data\nAggregation")
        
        with Cluster("Storage"):
            raw = PostgreSQL("Raw Layer\n(Bronze)")
            processed = PostgreSQL("Processed Layer\n(Silver)")
            analytics = PostgreSQL("Analytics Layer\n(Gold)")
        
        with Cluster("Consumption"):
            api = Docker("REST API")
            dashboard = Docker("Dashboard")
            reports = Docker("Reports")
        
        sources >> validation >> raw
        raw >> transformation >> processed
        processed >> enrichment >> analytics
        analytics >> [api, dashboard, reports]


def main():
    """Generate all architecture diagrams."""
    print("Generating Traffic Management System Architecture Diagrams...\n")
    
    diagrams_dir = "docs/architecture"
    os.makedirs(diagrams_dir, exist_ok=True)
    
    # Change to diagrams directory for output
    original_cwd = os.getcwd()
    os.chdir(diagrams_dir)
    
    try:
        print("✓ Generating high-level architecture...")
        generate_high_level_architecture()
        
        print("✓ Generating detailed data flow...")
        generate_detailed_data_flow()
        
        print("✓ Generating deployment architecture...")
        generate_deployment_architecture()
        
        print("✓ Generating system components...")
        generate_system_components()
        
        print("✓ Generating CI/CD pipeline...")
        generate_ci_cd_pipeline()
        
        print("✓ Generating database schema...")
        generate_database_schema()
        
        print("✓ Generating data pipeline...")
        generate_data_pipeline()
        
        print("\n✅ All architecture diagrams generated successfully!")
        print(f"📁 Diagrams saved to: {diagrams_dir}/")
        
    finally:
        os.chdir(original_cwd)


if __name__ == "__main__":
    main()
