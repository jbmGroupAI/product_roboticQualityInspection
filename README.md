Robotic Inspection System Server
Overview
The Robotic Inspection System Server is a FastAPI-based application designed to manage data acquisition and analytics for a robotic arm equipped with a profiler and camera system. The server communicates with a Programmable Logic Controller (PLC) to retrieve position numbers, captures data from sensors (profiler and/or camera) based on a configuration-driven action mapping, processes analytics (e.g., object detection for holes and nuts), and returns a structured JSON response. The payload schema is extensible to support future sensors and analytics, making it suitable for enterprise-grade applications.
Key Features

Configuration-Driven: Loads settings from config.yaml for PLC, position-wise actions, and analytics flags.
API Endpoint: POST /acquire to trigger data acquisition and analytics.
Extensible Payload: Modular JSON schema with metadata, data, and analytics sections.
Asynchronous Processing: Concurrent data acquisition for profiler and camera.
Optimized Data Handling: Compression of large data (zlib for XZ arrays, base64-encoded JPEG images).
Position-Wise Actions: Maps position numbers to actions (Profiler, Camera, Light) from config.yaml.
Error Handling: Robust validation for position numbers and PLC mismatches.

Use Case
The server supports a robotic inspection system where:

A robotic arm halts at predefined positions to inspect a part.
The robot updates the Position_No register in the PLC.
The server captures profiler data (XZ array, image), camera data (image), or both, based on config.yaml.
For camera actions, a light may be triggered via the Light_Trigger register.
Analytics classify objects (e.g., holes, nuts) for profiler data with positions (start, end, center).
The response is sent to an external server for further processing.

Setup
Prerequisites

Python: 3.8 or higher
Dependencies: fastapi, uvicorn, pydantic, numpy, pyyaml
Hardware: Profiler and camera with acquisition code
PLC: Configured for communication (e.g., Modbus/TCP)
Configuration: config.yaml file in the working directory

Installation

Save the server code as inspection_server.py.
Create or update config.yaml (see Configuration).
Install dependencies:pip install fastapi uvicorn pydantic numpy pyyaml


Replace placeholder functions in inspection_server.py (see Customization).
Run the server:python inspection_server.py

The server will be available at http://localhost:8000.

Customization
Update the following placeholder functions in inspection_server.py:

acquire_profiler_data(): Return a NumPy array (XZ data) and image (bytes, JPEG).
acquire_camera_image(): Return an image (bytes, JPEG).
trigger_light(): Write to PLC Light_Trigger register (address 10) to activate lighting.
read_plc_position_no(): Read PLC Position_No register (address 100) to get the position number.
analyze_profiler_data(): Implement object detection for profiler data (e.g., holes, nuts).

Replace placeholder image files (placeholder_profiler_image.jpg, placeholder_camera_image.jpg) with actual paths or remove if images are generated dynamically.
Configuration
The server loads settings from config.yaml, which defines PLC communication, position-wise actions, and analytics flags.
Example config.yaml
PLC:
  IP: 0.0.0.0
  Port: 12345
PLC_Registers:
  Position_No: 100
  Light_Trigger: 10
  Robot_Home: 7
  Robot_Running_Status: 13
  Cycle_Complete: 14
  Robot_Emergency: 1
  Servo_Status: 4
Position_Wise_Actions:
  1: [Camera, Light]
  2: [Camera, Light]
  3: [Profiler]
  4: [Camera, Light]
  5: [Profiler]
  6: [Profiler]
Use_Camera: False
Use_Gabor_Filter: False
Weld_Reference_ROIs:
  "1":
    reference_image: "references/ok_pos1.jpg"
    roi: [180, 917, 220, 795]
  "2":
    reference_image: "references/ok_pos2.jpg"
    roi: [212, 900, 987, 352]

Configuration Details

PLC:
IP: PLC IP address (update to actual value).
Port: PLC port (e.g., 12345 for Modbus/TCP).


PLC_Registers:
Position_No (100): Register for position number.
Light_Trigger (10): Register to trigger lighting for camera.
Others (Robot_Home, etc.): Reserved for future use.


Position_Wise_Actions:
Maps position numbers to actions:
1, 2, 4: Camera and Light (if Use_Camera: True).
3, 5, 6: Profiler with object detection analytics.




Use_Camera:
If False, camera actions are skipped, even if specified.


Use_Gabor_Filter:
Reserved for future image processing (e.g., weld analysis).


Weld_Reference_ROIs:
Reference images and ROIs for positions 1 and 2 (placeholder for weld analysis).



API Reference
Endpoint: POST /acquire
Triggers data acquisition and analytics based on the provided position number.
Request

Method: POST
URL: /acquire
Content-Type: application/json
Body:{
  "position_no": <integer>
}


position_no: The position number from the PLC, mapped to actions in config.yaml.



Response

Status Codes:
200 OK: Successful data acquisition and processing.
400 Bad Request: Invalid position number or PLC mismatch.
500 Internal Server Error: Sensor acquisition failure.


Body: JSON object with metadata, data, and analytics sections (see Payload Schema).

Position-Wise Actions
From config.yaml:

Position 1: Camera, Light (if Use_Camera: True).
Position 2: Camera, Light (if Use_Camera: True).
Position 3: Profiler (with object detection analytics).
Position 4: Camera, Light (if Use_Camera: True).
Position 5: Profiler (with object detection analytics).
Position 6: Profiler (with object detection analytics).

Payload Schema
The response payload is extensible, supporting current sensors (profiler, camera) and future additions. It includes compressed data and metadata for traceability.
Structure
{
  "metadata": {
    "position_no": "integer",
    "timestamp": "string (ISO 8601)",
    "correlation_id": "string (UUID)",
    "schema_version": "string",
    "sources": [
      {
        "type": "string (e.g., profiler, camera)",
        "id": "string",
        "config": "object (extensible)"
      }
    ]
  },
  "data": {
    "sensors": [
      {
        "type": "string (e.g., profiler, camera)",
        "raw_data": {
          "format": "string (e.g., xz_array, image_jpeg)",
          "value": "string (base64-encoded, compressed if applicable)"
        },
        "acquisition_time": "string (ISO 8601)"
      }
    ]
  },
  "analytics": {
    "objects": [
      {
        "type": "string (e.g., hole, nut)",
        "attributes": {
          "start_point": [float, float],
          "end_point": [float, float],
          "center_point": [float, float]
        },
        "confidence": "float (0-1)",
        "metadata": "object (extensible)"
      }
    ]
  }
}

Notes

Compression: XZ data is compressed with zlib; images are base64-encoded JPEGs.
Extensibility: Add new sensors to data.sensors or analytics outputs to analytics.
Versioning: schema_version supports backward-compatible updates.
Nullability: Optional fields (e.g., analytics.objects) are empty if not applicable.

Sample API Requests and Responses
Below are sample requests and responses for all position numbers defined in config.yaml, covering both Use_Camera: True and Use_Camera: False scenarios where applicable.
Position 3: Profiler
Request:
curl -X POST http://localhost:8000/acquire -H "Content-Type: application/json" -d '{"position_no": 3}'

Response (HTTP 200):
{
  "metadata": {
    "position_no": 3,
    "timestamp": "2025-05-13T12:34:56.789Z",
    "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
    "schema_version": "1.0",
    "sources": [
      {
        "type": "profiler",
        "id": "profiler_001",
        "config": { "resolution": "high" }
      }
    ]
  },
  "data": {
    "sensors": [
      {
        "type": "profiler",
        "raw_data": {
          "format": "xz_array",
          "value": "eJxlj0sOwjAM...compressed_xz_data..."
        },
        "acquisition_time": "2025-05-13T12:34:56.790Z"
      },
      {
        "type": "profiler",
        "raw_data": {
          "format": "image_jpeg",
          "value": "iVBORw0KGgo...base64_profiler_image..."
        },
        "acquisition_time": "2025-05-13T12:34:56.790Z"
      }
    ]
  },
  "analytics": {
    "objects": [
      {
        "type": "hole",
        "attributes": {
          "start_point": [10.0, 0.5],
          "end_point": [12.0, 0.5],
          "center_point": [11.0, 0.5]
        },
        "confidence": 0.95,
        "metadata": {}
      },
      {
        "type": "nut",
        "attributes": {
          "start_point": [20.0, 1.0],
          "end_point": [22.0, 1.0],
          "center_point": [21.0, 1.0]
        },
        "confidence": 0.90,
        "metadata": {}
      }
    ]
  }
}

Position 5: Profiler
Request:
curl -X POST http://localhost:8000/acquire -H "Content-Type: application/json" -d '{"position_no": 5}'

Response (HTTP 200): Identical structure to Position 3, with updated timestamp and correlation ID.
{
  "metadata": {
    "position_no": 5,
    "timestamp": "2025-05-13T12:35:00.123Z",
    "correlation_id": "7b8e9f10-2a3b-4c5d-9e7f-112233445566",
    "schema_version": "1.0",
    "sources": [
      {
        "type": "profiler",
        "id": "profiler_001",
        "config": { "resolution": "high" }
      }
    ]
  },
  "data": {
    "sensors": [
      {
        "type": "profiler",
        "raw_data": {
          "format": "xz_array",
          "value": "eJxlj0sOwjAM...compressed_xz_data..."
        },
        "acquisition_time": "2025-05-13T12:35:00.124Z"
      },
      {
        "type": "profiler",
        "raw_data": {
          "format": "image_jpeg",
          "value": "iVBORw0KGgo...base64_profiler_image..."
        },
        "acquisition_time": "2025-05-13T12:35:00.124Z"
      }
    ]
  },
  "analytics": {
    "objects": [
      {
        "type": "hole",
        "attributes": {
          "start_point": [10.0, 0.5],
          "end_point": [12.0, 0.5],
          "center_point": [11.0, 0.5]
        },
        "confidence": 0.95,
        "metadata": {}
      },
      {
        "type": "nut",
        "attributes": {
          "start_point": [20.0, 1.0],
          "end_point": [22.0, 1.0],
          "center_point": [21.0, 1.0]
        },
        "confidence": 0.90,
        "metadata": {}
      }
    ]
  }
}

Position 6: Profiler
Request:
curl -X POST http://localhost:8000/acquire -H "Content-Type: application/json" -d '{"position_no": 6}'

Response (HTTP 200): Identical structure to Position 3, with updated timestamp and correlation ID.
{
  "metadata": {
    "position_no": 6,
    "timestamp": "2025-05-13T12:35:02.456Z",
    "correlation_id": "9c0d1e21-3b4c-5e6d-af8g-223344556677",
    "schema_version": "1.0",
    "sources": [
      {
        "type": "profiler",
        "id": "profiler_001",
        "config": { "resolution": "high" }
      }
    ]
  },
  "data": {
    "sensors": [
      {
        "type": "profiler",
        "raw_data": {
          "format": "xz_array",
          "value": "eJxlj0sOwjAM...compressed_xz_data..."
        },
        "acquisition_time": "2025-05-13T12:35:02.457Z"
      },
      {
        "type": "profiler",
        "raw_data": {
          "format": "image_jpeg",
          "value": "iVBORw0KGgo...base64_profiler_image..."
        },
        "acquisition_time": "2025-05-13T12:35:02.457Z"
      }
    ]
  },
  "analytics": {
    "objects": [
      {
        "type": "hole",
        "attributes": {
          "start_point": [10.0, 0.5],
          "end_point": [12.0, 0.5],
          "center_point": [11.0, 0.5]
        },
        "confidence": 0.95,
        "metadata": {}
      },
      {
        "type": "nut",
        "attributes": {
          "start_point": [20.0, 1.0],
          "end_point": [22.0, 1.0],
          "center_point": [21.0, 1.0]
        },
        "confidence": 0.90,
        "metadata": {}
      }
    ]
  }
}

Position 1: Camera, Light (with Use_Camera: True)
Note: Assumes Use_Camera is set to True in config.yaml.Request:
curl -X POST http://localhost:8000/acquire -H "Content-Type: application/json" -d '{"position_no": 1}'

Response (HTTP 200):
{
  "metadata": {
    "position_no": 1,
    "timestamp": "2025-05-13T12:35:04.789Z",
    "correlation_id": "1a2b3c4d-5e6f-7a8b-9c0d-334455667788",
    "schema_version": "1.0",
    "sources": [
      {
        "type": "camera",
        "id": "camera_001",
        "config": { "resolution": "1080p" }
      }
    ]
  },
  "data": {
    "sensors": [
      {
        "type": "camera",
        "raw_data": {
          "format": "image_jpeg",
          "value": "iVBORw0KGgo...base64_camera_image..."
        },
        "acquisition_time": "2025-05-13T12:35:04.790Z"
      }
    ]
  },
  "analytics": {
    "objects": []
  }
}

Position 1: Camera, Light (with Use_Camera: False)
Request:
curl -X POST http://localhost:8000/acquire -H "Content-Type: application/json" -d '{"position_no": 1}'

Response (HTTP 200):
{
  "metadata": {
    "position_no": 1,
    "timestamp": "2025-05-13T12:35:06.123Z",
    "correlation_id": "2b3c4d5e-6f7a-8b9c-0d1e-445566778899",
    "schema_version": "1.0",
    "sources": []
  },
  "data": {
    "sensors": []
  },
  "analytics": {
    "objects": []
  }
}

Position 2: Camera, Light (with Use_Camera: True)
Request:
curl -X POST http://localhost:8000/acquire -H "Content-Type: application/json" -d '{"position_no": 2}'

Response (HTTP 200): Identical structure to Position 1 (Use_Camera: True), with updated metadata.
{
  "metadata": {
    "position_no": 2,
    "timestamp": "2025-05-13T12:35:08.456Z",
    "correlation_id": "3c4d5e6f-7a8b-9c0d-1e2f-556677889900",
    "schema_version": "1.0",
    "sources": [
      {
        "type": "camera",
        "id": "camera_001",
        "config": { "resolution": "1080p" }
      }
    ]
  },
  "data": {
    "sensors": [
      {
        "type": "camera",
        "raw_data": {
          "format": "image_jpeg",
          "value": "iVBORw0KGgo...base64_camera_image..."
        },
        "acquisition_time": "2025-05-13T12:35:08.457Z"
      }
    ]
  },
  "analytics": {
    "objects": []
  }
}

Position 4: Camera, Light (with Use_Camera: True)
Request:
curl -X POST http://localhost:8000/acquire -H "Content-Type: application/json" -d '{"position_no": 4}'

Response (HTTP 200): Identical structure to Position 1 (Use_Camera: True), with updated metadata.
{
  "metadata": {
    "position_no": 4,
    "timestamp": "2025-05-13T12:35:10.789Z",
    "correlation_id": "4d5e6f7a-8b9c-0d1e-2f3a-667788990011",
    "schema_version": "1.0",
    "sources": [
      {
        "type": "camera",
        "id": "camera_001",
        "config": { "resolution": "1080p" }
      }
    ]
  },
  "data": {
    "sensors": [
      {
        "type": "camera",
        "raw_data": {
          "format": "image_jpeg",
          "value": "iVBORw0KGgo...base64_camera_image..."
        },
        "acquisition_time": "2025-05-13T12:35:10.790Z"
      }
    ]
  },
  "analytics": {
    "objects": []
  }
}

Error Response: Invalid Position Number
Request:
curl -X POST http://localhost:8000/acquire -H "Content-Type: application/json" -d '{"position_no": 999}'

Response (HTTP 400):
{
  "detail": "Invalid position number"
}

Workflow
The server follows a configuration-driven workflow to ensure efficiency and extensibility:

Configuration Loading:

At startup, the server loads config.yaml to initialize PLC settings, position actions, and flags (Use_Camera, Use_Gabor_Filter).


Position Trigger:

The robotic arm halts at a specific position during part inspection.
The robot updates the Position_No register (address 100) in the PLC.


API Request:

An external server sends a POST /acquire request with the position number (e.g., {"position_no": 3}).
The server validates the position number against Position_Wise_Actions in config.yaml.


PLC Verification:

The server reads the Position_No register using read_plc_position_no.
If the PLC position number mismatches the request, a 400 error is returned.


Data Acquisition:

The server retrieves actions from Position_Wise_Actions (e.g., ["Profiler"] for position 3).
Actions are processed:
Profiler: Calls acquire_profiler_data to get XZ data (NumPy array) and image (bytes).
Camera (if Use_Camera: True): Calls acquire_camera_image to get image (bytes).
Light (if Use_Camera: True): Calls trigger_light to write to Light_Trigger register.


Sensor tasks are executed concurrently using asyncio.gather.
XZ data is compressed with zlib; images are base64-encoded.


Analytics Processing:

For profiler actions (positions 3, 5, 6), the server calls analyze_profiler_data asynchronously.
Analytics classify objects (e.g., holes, nuts) with positions and confidence scores.
Placeholders for future analytics:
Gabor filter (if Use_Gabor_Filter: True).
Weld analysis using Weld_Reference_ROIs for camera images (positions 1, 2).


Results are added to analytics.objects.


Response Generation:

The server constructs the response with:
Metadata: Position number, timestamp, correlation ID, schema version, source details.
Data: Sensor data (type, format, compressed value, acquisition time).
Analytics: Detected objects with attributes and metadata.


The response is returned as JSON (HTTP 200).


Error Handling:

Invalid position numbers return a 400 error.
Sensor acquisition failures return a 500 error.
The response structure remains consistent even in partial failures.



Extensibility

New Sensors:
Add new actions to Position_Wise_Actions in config.yaml (e.g., ["Thermal_Camera"]).
Implement a new acquisition function (e.g., acquire_thermal_data).
Update the acquire_data endpoint to handle the new sensor type.


New Analytics:
Implement Gabor filter processing by checking Use_Gabor_Filter in analyze_profiler_data.
Add weld analysis using Weld_Reference_ROIs to compare camera images against references.
Extend analytics with new keys (e.g., "weld_defects").


Schema Evolution:
Update schema_version for new payload versions.
Use config and metadata fields for sensor- or analytics-specific settings.


PLC Enhancements:
Use additional registers (e.g., Robot_Emergency, Cycle_Complete) for status checks or triggers.



Performance Optimizations

Asynchronous Processing: Sensor tasks run concurrently with asyncio.gather.
Compression: XZ data is compressed with zlib; images are base64-encoded JPEGs.
Configuration Caching: config.yaml is loaded once at startup.
Error Handling: Early validation minimizes unnecessary processing.


## Add Master Profile API (New Format)

### Endpoint
`POST /add_master_profile`

### Description
Add master profile data for a specific event. This allows you to store the master raw profile and detected holes/nuts for an event. During actual runs, you can pass the event name/id to compare against this master data.

### Request Body
```
{
  "event_name": "event_4",
  "raw_profile": {
    "X": [1722, 1710, ...],
    "Z": [4807, 4826, ...]
  },
  "holes": [
    {
      "x_min": 10.0,
      "x_max": 12.0,
      "width": 2.0,
      "thresholds": {
        "position_tolerance": 0.5,
        "width_tolerance": 0.3,
        "depth_tolerance": 0.2,
        "expected_depth": -1.0
      }
    }
    // ... more holes ...
  ],
  "nuts": [
    // ... same structure as holes ...
  ],
  "global_thresholds": {
    "min_confidence": 0.85,
    "max_position_deviation": 1.0,
    "max_width_deviation": 0.5,
    "max_depth_deviation": 0.3
  }
}
```

### Example Request
```
curl -X POST http://localhost:8000/add_master_profile \
  -H "Content-Type: application/json" \
  -d '{
    "event_name": "event_4",
    "raw_profile": {
      "X": [1722, 1710, 1700],
      "Z": [4807, 4826, 4834]
    },
    "holes": [
      {
        "x_min": 10.0,
        "x_max": 12.0,
        "width": 2.0,
        "thresholds": {
          "position_tolerance": 0.5,
          "width_tolerance": 0.3,
          "depth_tolerance": 0.2,
          "expected_depth": -1.0
        }
      }
    ],
    "nuts": [],
    "global_thresholds": {
      "min_confidence": 0.85,
      "max_position_deviation": 1.0,
      "max_width_deviation": 0.5,
      "max_depth_deviation": 0.3
    }
  }'
```

### Response
```
{
  "message": "Master data for event 'event_4' added successfully."
}
```

---

## Compare to Master API (New Format)

### Endpoint
`POST /compare_to_master`

### Description
Compare actual run data (raw profile and detected holes/nuts) to the master data for a specific event. Returns a detailed comparison including count match and per-feature deviations.

### Request Body
```
{
  "event_name": "event_4",
  "raw_profile": {
    "X": [1722, 1710, ...],
    "Z": [4807, 4826, ...]
  },
  "holes": [
    {
      "x_min": 10.1,
      "x_max": 12.1,
      "width": 2.1,
      "thresholds": {
        "position_tolerance": 0.5,
        "width_tolerance": 0.3,
        "depth_tolerance": 0.2,
        "expected_depth": -1.0
      }
    }
    // ... more holes ...
  ],
  "nuts": [
    // ...
  ]
}
```

### Example Request
```
curl -X POST http://localhost:8000/compare_to_master \
  -H "Content-Type: application/json" \
  -d '{
    "event_name": "event_4",
    "raw_profile": {
      "X": [1722, 1710, 1700],
      "Z": [4807, 4826, 4834]
    },
    "holes": [
      {
        "x_min": 10.1,
        "x_max": 12.1,
        "width": 2.1,
        "thresholds": {
          "position_tolerance": 0.5,
          "width_tolerance": 0.3,
          "depth_tolerance": 0.2,
          "expected_depth": -1.0
        }
      }
    ],
    "nuts": []
  }'
```

### Example Response
```
{
  "event_name": "event_4",
  "master_hole_count": 1,
  "actual_hole_count": 1,
  "hole_count_match": true,
  "hole_comparisons": [
    {
      "index": 0,
      "master": {"x_min": 10.0, "x_max": 12.0, "width": 2.0, ...},
      "actual": {"x_min": 10.1, "x_max": 12.1, "width": 2.1, ...},
      "x_min_deviation": 0.1,
      "x_max_deviation": 0.1,
      "width_deviation": 0.1
    }
  ],
  "master_nut_count": 0,
  "actual_nut_count": 0,
  "nut_count_match": true,
  "nut_comparisons": []
}
```

### Notes
- If no master data is found for the event, the response will include an error message.
- You can extend the comparison logic to include more fields or tolerances as needed.


## Master Profile CRUD API

### List All Master Profiles
`GET /list_master_profiles`

**Description:**
Returns a list of all event names for which master profiles exist.

**Example Request:**
```
curl http://localhost:8000/list_master_profiles
```
**Example Response:**
```
{
  "event_names": ["event_4", "event_5"]
}
```

---

### Get a Master Profile
`GET /get_master_profile/{event_name}`

**Description:**
Returns the full master profile for the given event name.

**Example Request:**
```
curl http://localhost:8000/get_master_profile/event_4
```
**Example Response:**
```
{
  "event_name": "event_4",
  "raw_profile": {"X": [...], "Z": [...]},
  "holes": [...],
  "nuts": [...],
  "global_thresholds": {...}
}
```

---

### Delete a Master Profile
`DELETE /delete_master_profile/{event_name}`

**Description:**
Deletes the master profile for the given event name.

**Example Request:**
```
curl -X DELETE http://localhost:8000/delete_master_profile/event_4
```
**Example Response:**
```
{
  "message": "Master data for event 'event_4' deleted successfully."
}
```

---

### Edit a Master Profile
Use `POST /add_master_profile` with the same event name to update/replace the profile.

