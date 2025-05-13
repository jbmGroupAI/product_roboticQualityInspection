import base64
import zlib
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
import uuid
from typing import List, Optional, Dict, Any
import asyncio
import yaml

app = FastAPI(title="Robotic Inspection System API")

# Load configuration
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

PLC_CONFIG = config["PLC"]
PLC_REGISTERS = config["PLC_Registers"]
POSITION_ACTIONS = config["Position_Wise_Actions"]
USE_CAMERA = config["Use_Camera"]
# WELD_ROIS = config["Weld_Reference_ROIs"]  # Placeholder for future use

# Pydantic models for request and response
class AcquireRequest(BaseModel):
    position_no: int  # Changed from event_id to match config

class Source(BaseModel):
    type: str
    id: str
    config: Optional[Dict[str, Any]] = {}

class SensorData(BaseModel):
    type: str
    raw_data: Dict[str, str]
    acquisition_time: str

class ObjectAttributes(BaseModel):
    start_point: List[float]
    end_point: List[float]
    center_point: List[float]

class AnalyticsObject(BaseModel):
    type: str
    attributes: ObjectAttributes
    confidence: float
    metadata: Optional[Dict[str, Any]] = {}

class Metadata(BaseModel):
    position_no: int
    timestamp: str
    correlation_id: str
    schema_version: str
    sources: List[Source]

class InspectionResponse(BaseModel):
    metadata: Metadata
    data: Dict[str, List[SensorData]]
    analytics: Dict[str, List[AnalyticsObject]]

# Placeholder for profiler data acquisition
async def acquire_profiler_data() -> tuple[np.ndarray, bytes]:
    # Replace with your actual profiler code
    xz_data = np.array([[i, np.sin(i / 10.0)] for i in range(100)], dtype=np.float32)
    with open("placeholder_profiler_image.jpg", "rb") as f:
        image_data = f.read()
    return xz_data, image_data

# Placeholder for camera image acquisition
async def acquire_camera_image() -> bytes:
    # Replace with your actual camera code
    with open("placeholder_camera_image.jpg", "rb") as f:
        image_data = f.read()
    return image_data

# Placeholder for triggering light via PLC
async def trigger_light() -> None:
    # Replace with PLC write to Light_Trigger register (address 10)
    pass

# Placeholder for reading PLC position number
async def read_plc_position_no() -> int:
    # Replace with PLC read from Position_No register (address 100)
    return 1  # Dummy value

@app.post("/acquire", response_model=InspectionResponse)
async def acquire_data(request: AcquireRequest):
    # Validate position number
    position_str = str(request.position_no)
    if position_str not in POSITION_ACTIONS:
        raise HTTPException(status_code=400, detail="Invalid position number")

    # Read PLC position number
    plc_position_no = await read_plc_position_no()
    if plc_position_no != request.position_no:
        raise HTTPException(status_code=400, detail="PLC position number mismatch")

    # Initialize response
    correlation_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat() + "Z"
    response_data = {
        "metadata": {
            "position_no": request.position_no,
            "timestamp": timestamp,
            "correlation_id": correlation_id,
            "schema_version": "1.0",
            "sources": []
        },
        "data": {"sensors": []},
        "analytics": {"objects": []}
    }

    # Get actions for the position
    actions = POSITION_ACTIONS[position_str]
    sensor_tasks = []
    sensor_data = []
    xz_data = None  # Store for analytics

    # Process actions
    for action in actions:
        if action == "Profiler":
            sensor_tasks.append(acquire_profiler_data())
            response_data["metadata"]["sources"].append({
                "type": "profiler",
                "id": "profiler_001",
                "config": {"resolution": "high"}
            })
        elif action == "Camera" and USE_CAMERA:
            sensor_tasks.append(acquire_camera_image())
            response_data["metadata"]["sources"].append({
                "type": "camera",
                "id": "camera_001",
                "config": {"resolution": "1080p"}
            })
        elif action == "Light" and USE_CAMERA:
            await trigger_light()

    # Execute sensor tasks concurrently
    results = await asyncio.gather(*sensor_tasks, return_exceptions=True)

    # Process sensor results
    for idx, action in enumerate([a for a in actions if a in ["Profiler", "Camera"] and (a != "Camera" or USE_CAMERA)]):
        if isinstance(results[idx], Exception):
            raise HTTPException(status_code=500, detail=f"Failed to acquire {action} data")
        
        acquisition_time = datetime.utcnow().isoformat() + "Z"
        if action == "Profiler":
            xz_data, image_data = results[idx]
            compressed_xz = zlib.compress(xz_data.tobytes())
            sensor_data.append({
                "type": "profiler",
                "raw_data": {
                    "format": "xz_array",
                    "value": base64.b64encode(compressed_xz).decode("utf-8")
                },
                "acquisition_time": acquisition_time
            })
            sensor_data.append({
                "type": "profiler",
                "raw_data": {
                    "format": "image_jpeg",
                    "value": base64.b64encode(image_data).decode("utf-8")
                },
                "acquisition_time": acquisition_time
            })
        elif action == "Camera":
            image_data = results[idx]
            sensor_data.append({
                "type": "camera",
                "raw_data": {
                    "format": "image_jpeg",
                    "value": base64.b64encode(image_data).decode("utf-8")
                },
                "acquisition_time": acquisition_time
            })

    response_data["data"]["sensors"] = sensor_data

    # Perform analytics for profiler data
    if "Profiler" in actions:
        # Placeholder for Gabor filter and weld ROI analytics
        # if config["Use_Gabor_Filter"]:
        #     # Apply Gabor filter to profiler image or XZ data
        # if position_str in config["Weld_Reference_ROIs"]:
        #     # Compare camera image with reference_image using roi
        analytics_result = await analyze_profiler_data(xz_data)
        response_data["analytics"]["objects"] = analytics_result

    return response_data

# Simplified analytics (replace with your logic)
async def analyze_profiler_data(xz_data: np.ndarray) -> List[Dict[str, Any]]:
    # Simulate detecting a hole and a nut
    return [
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
