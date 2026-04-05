# REST API Endpoint Specifications

Complete technical specifications for all API endpoints.

## Table of Contents

1. [Overview](#overview)
2. [Request/Response Format](#requestresponse-format)
3. [Endpoint Specifications](#endpoint-specifications)
4. [Data Model Definitions](#data-model-definitions)
5. [Error Codes Reference](#error-codes-reference)

---

## Overview

### Base URL

- Development: `http://localhost:8000`
- Production: `https://api.traffic-system.com`

### API Version

- Current: `v1.0.0`
- Format: REST with JSON

### Timeout

- Request timeout: 30 seconds
- Connection timeout: 5 seconds

---

## Request/Response Format

### Content-Type

All requests and responses use `application/json`.

### Request Headers

```
Content-Type: application/json
User-Agent: TrafficClient/1.0
X-Request-ID: <unique-request-id> [optional]
X-Admin-Token: <admin-token> [optional, for admin endpoints]
Authorization: Bearer <token> [optional, for authenticated requests]
```

### Response Headers

```
Content-Type: application/json
X-Request-ID: <echo-request-id>
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1705327200
X-Process-Time: 0.123 (seconds)
Cache-Control: no-cache, no-store, must-revalidate
```

### DateTime Format

All datetime values use ISO 8601 format:
```
2024-01-15T12:00:00Z
2024-01-15T12:00:00+00:00
```

---

## Endpoint Specifications

### 1. Health & Status


#### GET /health
System health check endpoint.

**Parameters:** None

**Response:**
```json
{
  "status": "healthy|degraded|unhealthy",
  "timestamp": "2024-01-15T12:00:00Z",
  "version": "1.0.0",
  "uptime_seconds": 3600.5
}
```

**Status Codes:**
- 200 OK: System is operational
- 503 Service Unavailable: System is unhealthy

---

#### GET /status
Comprehensive system status with metrics.

**Parameters:** None

**Response:**
```json
{
  "status": "operational|degraded|offline",
  "uptime_seconds": 3600.5,
  "cpu_usage": 45.2,
  "memory_usage": 62.3,
  "gpu_usage": 78.5,
  "active_cameras": 4,
  "database_latency_ms": 12.5,
  "detections_per_second": 240.3,
  "timestamp": "2024-01-15T12:00:00Z"
}
```

**Notes:**
- `cpu_usage`, `memory_usage`: 0-100 percentage
- `gpu_usage`: null if no GPU available
- All latencies in milliseconds
- Detection throughput in detections/second

---

#### GET /ready
Kubernetes readiness probe endpoint.

**Parameters:** None

**Response:**
```json
{
  "ready": true,
  "timestamp": "2024-01-15T12:00:00Z"
}
```

**Status Codes:**
- 200 OK: Ready to accept requests
- 503 Service Unavailable: Not ready

---

### 2. Detections

#### GET /detections
List vehicle detections with optional filtering.

**Parameters:**

| Name | Type | Location | Required | Range | Default |
|------|------|----------|----------|-------|---------|
| lane | string | query | No | North, South, East, West | - |
| start_time | string (datetime) | query | No | - | - |
| end_time | string (datetime) | query | No | - | - |
| page | integer | query | No | ≥ 1 | 1 |
| page_size | integer | query | No | 1-500 | 50 |

**Example Request:**
```
GET /detections?lane=North&page=1&page_size=50&start_time=2024-01-15T10:00:00Z
```

**Response:**
```json
{
  "items": [
    {
      "detection_id": 1,
      "timestamp": "2024-01-15T12:00:00Z",
      "lane": "North",
      "vehicle_class": "car",
      "confidence": 0.95,
      "bounding_box": {
        "x_min": 100,
        "y_min": 100,
        "x_max": 150,
        "y_max": 150
      },
      "speed": 25.5,
      "vehicle_id": "V0001"
    }
  ],
  "total": 1250,
  "page": 1,
  "page_size": 50,
  "total_pages": 25
}
```

**Status Codes:**
- 200 OK: Success
- 400 Bad Request: Invalid parameters
- 422 Unprocessable Entity: Validation error

---

#### GET /detections/{detection_id}
Get specific detection details.

**Parameters:**

| Name | Type | Location | Required | Range |
|------|------|----------|----------|-------|
| detection_id | integer | path | Yes | > 0 |

**Example Request:**
```
GET /detections/12345
```

**Response:**
```json
{
  "detection_id": 12345,
  "timestamp": "2024-01-15T12:00:00Z",
  "lane": "North",
  "vehicle_class": "car",
  "confidence": 0.95,
  "bounding_box": {
    "x_min": 100,
    "y_min": 100,
    "x_max": 150,
    "y_max": 150
  },
  "speed": 25.5,
  "vehicle_id": "V12345"
}
```

**Status Codes:**
- 200 OK: Success
- 404 Not Found: Detection not found

---

### 3. Signal Control

#### GET /signals
Get all signal states.

**Parameters:** None

**Response:**
```json
[
  {
    "lane": "North",
    "state": "green",
    "time_remaining": 35,
    "cycle_position": 40
  },
  {
    "lane": "South",
    "state": "red",
    "time_remaining": 55,
    "cycle_position": 80
  },
  ...
]
```

**Status Codes:**
- 200 OK: Success
- 500 Internal Server Error: Failed to read signals

---

#### GET /signals/{lane}
Get specific lane signal state.

**Parameters:**

| Name | Type | Location | Required |
|------|------|----------|----------|
| lane | string | path | Yes |

**Response:**
```json
{
  "lane": "North",
  "state": "green",
  "time_remaining": 35,
  "cycle_position": 40
}
```

**Status Codes:**
- 200 OK: Success
- 404 Not Found: Lane not found

---

#### POST /signals/{lane}/control
Control traffic signal (admin only).

**Parameters:**

| Name | Type | Location | Required | Valid Values |
|------|------|----------|----------|--------------|
| lane | string | path | Yes | North, South, East, West |
| state | string | query | Yes | green, yellow, red |
| duration | integer | query | Yes | 0 < duration ≤ 300 |

**Headers Required:**
```
X-Admin-Token: <admin-token>
```

**Example Request:**
```
POST /signals/North/control?state=green&duration=45
X-Admin-Token: admin-secret
```

**Response:**
```json
{
  "success": true,
  "lane": "North",
  "state": "green",
  "duration": 45,
  "timestamp": "2024-01-15T12:00:00Z"
}
```

**Status Codes:**
- 200 OK: Control successful
- 401 Unauthorized: Missing or invalid admin token
- 403 Forbidden: Admin token invalid
- 404 Not Found: Lane not found
- 422 Unprocessable Entity: Invalid parameters

---

### 4. Metrics

#### GET /metrics/{lane}
Get real-time metrics for a lane.

**Parameters:**

| Name | Type | Location | Required |
|------|------|----------|----------|
| lane | string | path | Yes |

**Response:**
```json
{
  "timestamp": "2024-01-15T12:00:00Z",
  "lane": "North",
  "vehicle_count": 12,
  "congestion_level": 0.35,
  "average_speed": 24.5,
  "throughput": 45,
  "wait_time": 32.5
}
```

**Field Constraints:**
- `congestion_level`: 0.0 to 1.0
- `average_speed`: ≥ 0 (km/h)
- `throughput`: ≥ 0 (vehicles/min)
- `wait_time`: ≥ 0 (seconds)

**Status Codes:**
- 200 OK: Success
- 404 Not Found: Lane not found

---

#### GET /metrics/system/aggregate
Get system-wide aggregated metrics.

**Parameters:**

| Name | Type | Location | Required | Default | Range |
|------|------|----------|----------|---------|-------|
| time_window | integer | query | No | 3600 | 60-86400 |

**Response:**
```json
{
  "timestamp": "2024-01-15T12:00:00Z",
  "total_vehicles": 847,
  "average_congestion": 0.32,
  "average_wait_time": 38.2,
  "overall_throughput": 1840,
  "time_window_seconds": 3600,
  "lanes": {
    "North": {
      "vehicle_count": 210,
      "congestion": 0.30,
      "wait_time": 35.5
    },
    ...
  }
}
```

**Status Codes:**
- 200 OK: Success
- 400 Bad Request: Invalid time_window

---

#### GET /analytics/hourly
Get historical hourly statistics.

**Parameters:**

| Name | Type | Location | Required | Default | Range |
|------|------|----------|----------|---------|-------|
| lane | string | query | No | All | North, South, East, West, All |
| hours | integer | query | No | 24 | 1-168 |

**Response:**
```json
{
  "data": [
    {
      "hour": "2024-01-15T11:00:00Z",
      "lane": "North",
      "vehicle_count": 150,
      "avg_speed": 20.5,
      "violations": 3,
      "congestion_level": 0.35,
      "throughput": 120
    },
    ...
  ],
  "total_hours": 24,
  "lanes_included": ["North"],
  "generated_at": "2024-01-15T12:00:00Z"
}
```

**Status Codes:**
- 200 OK: Success
- 400 Bad Request: Invalid parameters

---

### 5. Violations

#### GET /violations
List traffic violations with filtering.

**Parameters:**

| Name | Type | Location | Required | Valid Values | Default |
|------|------|----------|----------|--------------|---------|
| violation_type | string | query | No | red_light, speeding, illegal_turn, other | - |
| processed | boolean | query | No | true, false | - |
| min_severity | integer | query | No | 1-5 | 1 |
| page | integer | query | No | ≥ 1 | 1 |
| page_size | integer | query | No | 1-500 | 50 |

**Example Request:**
```
GET /violations?violation_type=red_light&processed=false&min_severity=3&page=1
```

**Response:**
```json
{
  "items": [
    {
      "violation_id": 1,
      "timestamp": "2024-01-15T12:00:00Z",
      "lane": "North",
      "vehicle_id": "V0001",
      "violation_type": "red_light",
      "severity": 3,
      "speed": 45.0,
      "processed": false,
      "image_url": "https://api.traffic-system.com/violation/1/image.jpg"
    }
  ],
  "total": 245,
  "page": 1,
  "page_size": 50,
  "total_pages": 5
}
```

**Status Codes:**
- 200 OK: Success
- 400 Bad Request: Invalid filters
- 422 Unprocessable Entity: Validation error

---

#### POST /violations/{violation_id}/process
Mark violation as processed.

**Parameters:**

| Name | Type | Location | Required |
|------|------|----------|----------|
| violation_id | integer | path | Yes |
| notes | string | query | No |

**Headers Required:**
```
X-Admin-Token: <admin-token>
```

**Example Request:**
```
POST /violations/1234/process?notes=Fine%20issued%20on%202024-01-15
X-Admin-Token: admin-secret
```

**Response:**
```json
{
  "success": true,
  "violation_id": 1234,
  "processed": true,
  "timestamp": "2024-01-15T12:00:00Z",
  "notes": "Fine issued on 2024-01-15"
}
```

**Status Codes:**
- 200 OK: Success
- 401 Unauthorized: Missing admin token
- 404 Not Found: Violation not found

---

### 6. Configuration

#### GET /config/signals
Get signal timing configuration.

**Parameters:** None

**Response:**
```json
{
  "mode": "adaptive",
  "cycle_length": 120,
  "min_green": 20,
  "max_green": 80,
  "yellow_duration": 5
}
```

**Field Constraints:**
- `mode`: fixed, adaptive, or manual
- `cycle_length`: 60-240 seconds
- `min_green`: ≥ 10 seconds
- `max_green`: ≤ 200 seconds
- `yellow_duration`: ≥ 3 seconds

**Status Codes:**
- 200 OK: Success

---

#### PUT /config/signals
Update signal timing configuration.

**Parameters:**

Request body with same fields as GET response.

**Headers Required:**
```
X-Admin-Token: <admin-token>
Content-Type: application/json
```

**Example Request:**
```
PUT /config/signals
X-Admin-Token: admin-secret
Content-Type: application/json

{
  "mode": "adaptive",
  "cycle_length": 120,
  "min_green": 25,
  "max_green": 85,
  "yellow_duration": 5
}
```

**Response:**
```json
{
  "mode": "adaptive",
  "cycle_length": 120,
  "min_green": 25,
  "max_green": 85,
  "yellow_duration": 5,
  "updated_at": "2024-01-15T12:00:00Z"
}
```

**Validation Rules:**
- `min_green + yellow_duration < cycle_length`
- `min_green ≤ max_green`
- `max_green ≥ min_green`

**Status Codes:**
- 200 OK: Configuration updated
- 400 Bad Request: Invalid configuration
- 401 Unauthorized: Missing admin token
- 422 Unprocessable Entity: Validation error

---

## Data Model Definitions

### Vehicle Detection

```json
{
  "detection_id": 1,
  "timestamp": "2024-01-15T12:00:00Z",
  "lane": "North",
  "vehicle_class": "car",
  "confidence": 0.95,
  "bounding_box": {
    "x_min": 100,
    "y_min": 100,
    "x_max": 150,
    "y_max": 150
  },
  "speed": 25.5,
  "vehicle_id": "V0001"
}
```

**Field Descriptions:**
- `detection_id` (integer): Unique detection identifier
- `timestamp` (string): ISO 8601 datetime
- `lane` (string): Lane identifier
- `vehicle_class` (string): Type of vehicle
- `confidence` (number): Detection confidence (0.0-1.0)
- `bounding_box` (object): Pixel coordinates
- `speed` (number): Estimated speed in km/h
- `vehicle_id` (string): Tracked vehicle ID

---

### Traffic Metrics

```json
{
  "timestamp": "2024-01-15T12:00:00Z",
  "lane": "North",
  "vehicle_count": 12,
  "congestion_level": 0.35,
  "average_speed": 24.5,
  "throughput": 45,
  "wait_time": 32.5
}
```

**Field Descriptions:**
- `timestamp`: Time of measurement
- `lane`: Lane identifier
- `vehicle_count`: Number of vehicles currently in lane
- `congestion_level`: 0=free, 1=saturated
- `average_speed`: Mean speed in km/h
- `throughput`: Vehicles/minute
- `wait_time`: Average wait time in seconds

---

### Violation Record

```json
{
  "violation_id": 1,
  "timestamp": "2024-01-15T12:00:00Z",
  "lane": "North",
  "vehicle_id": "V0001",
  "violation_type": "red_light",
  "severity": 3,
  "speed": 45.0,
  "processed": false
}
```

**Field Descriptions:**
- `violation_id`: Unique identifier
- `timestamp`: When violation occurred
- `lane`: Lane identifier
- `vehicle_id`: Tracked vehicle ID
- `violation_type`: Type of violation
- `severity`: 1-5 scale
- `speed`: Vehicle speed when violation occurred
- `processed`: Whether violation has been processed

---

## Error Codes Reference

### Common Error Responses

```json
{
  "error": "error_code",
  "message": "Human-readable error message",
  "timestamp": "2024-01-15T12:00:00Z",
  "details": {
    "field": "error_detail"
  },
  "request_id": "req_1234567890"
}
```

### Error Code Definitions

| Code | HTTP Status | Description |
|------|-------------|-------------|
| invalid_request | 400 | Invalid request format |
| invalid_parameter | 422 | Parameter validation failed |
| missing_parameter | 422 | Required parameter missing |
| resource_not_found | 404 | Resource doesn't exist |
| authentication_failed | 401 | Invalid credentials |
| permission_denied | 403 | Insufficient permissions |
| rate_limit_exceeded | 429 | Rate limit exceeded |
| conflict | 409 | Resource conflict |
| timeout | 504 | Request timeout |
| internal_error | 500 | Server error |

---

## Request/Response Examples

### Example 1: Successful Detection List

**Request:**
```bash
curl -X GET 'http://localhost:8000/detections?lane=North&page=1&page_size=10' \
  -H 'Content-Type: application/json'
```

**Response:**
```
HTTP/1.1 200 OK
Content-Type: application/json
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999

{
  "items": [...],
  "total": 1250,
  "page": 1,
  "page_size": 10,
  "total_pages": 125
}
```

### Example 2: Invalid Parameter Error

**Request:**
```bash
curl -X GET 'http://localhost:8000/detections?page=-1' \
  -H 'Content-Type: application/json'
```

**Response:**
```
HTTP/1.1 422 Unprocessable Entity
Content-Type: application/json

{
  "error": "invalid_parameter",
  "message": "Page must be >= 1",
  "timestamp": "2024-01-15T12:00:00Z",
  "request_id": "req_1234567890"
}
```

### Example 3: Unauthorized Admin Action

**Request:**
```bash
curl -X POST 'http://localhost:8000/signals/North/control?state=green&duration=45'
```

**Response:**
```
HTTP/1.1 401 Unauthorized
Content-Type: application/json

{
  "error": "authentication_failed",
  "message": "Admin token required",
  "timestamp": "2024-01-15T12:00:00Z"
}
```

