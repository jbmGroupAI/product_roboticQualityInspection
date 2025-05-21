import base64
import zlib
import numpy as np
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from datetime import datetime
import uuid
from typing import List, Optional, Dict, Any
import asyncio
import yaml
from gap_detector import GapDetector, GapConfig

app = FastAPI(title="Robotic Inspection System API")

# Load configuration
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

PLC_CONFIG = config["PLC"]
PLC_REGISTERS = config["PLC_Registers"]
POSITION_ACTIONS = config["Position_Wise_Actions"]
USE_CAMERA = config["Use_Camera"]
# WELD_ROIS = config["Weld_Reference_ROIs"]  # Placeholder for future use

# New Pydantic models for profiler data
class FeatureThresholds(BaseModel):
    position_tolerance: float
    width_tolerance: float
    depth_tolerance: float
    expected_depth: float

class MasterFeature(BaseModel):
    x_min: float
    x_max: float
    width: float
    thresholds: FeatureThresholds

class GlobalThresholds(BaseModel):
    min_confidence: float
    max_position_deviation: float
    max_width_deviation: float
    max_depth_deviation: float

class ProfilerMasterData(BaseModel):
    expected_holes: int
    expected_nuts: int
    hole_positions: List[MasterFeature]
    nut_positions: List[MasterFeature]
    global_thresholds: GlobalThresholds

class FeatureValidation(BaseModel):
    is_valid: bool
    position_match: bool
    width_match: bool
    depth_match: bool
    confidence: float
    deviations: Dict[str, float]
    message: str

class DetectedFeature(BaseModel):
    type: str  # "hole" or "nut"
    x_min: float
    x_max: float
    width: float
    depth: float
    confidence: float
    center_point: List[float]
    validation: Optional[FeatureValidation] = None

class ProfilerDetectionResult(BaseModel):
    features: List[DetectedFeature]
    total_holes: int
    total_nuts: int
    is_valid: bool
    validation_message: str

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

    # Process profiler data if available
    if "Profiler" in actions and xz_data is not None:
        profiler_result = await process_profiler_data(xz_data, request.position_no)
        
        # Convert profiler results to analytics objects
        for feature in profiler_result.features:
            analytics_object = {
                "type": feature.type,
                "attributes": {
                    "start_point": [feature.x_min, 0.0],
                    "end_point": [feature.x_max, 0.0],
                    "center_point": feature.center_point
                },
                "confidence": feature.confidence,
                "metadata": {
                    "width": feature.width,
                    "is_valid": profiler_result.is_valid
                }
            }
            response_data["analytics"]["objects"].append(analytics_object)

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

# New function to process profiler data
async def process_profiler_data(xz_data: np.ndarray, event_id: int) -> ProfilerDetectionResult:
    """
    Process raw profiler data to detect holes and nuts
    Returns detection results with positions and validation
    """
    # Get master data for this event
    master_data = config.get("Profiler_Master_Data", {}).get(f"event_{event_id}")
    if not master_data:
        raise HTTPException(status_code=400, detail=f"No master data found for event {event_id}")

    # Convert master data to Pydantic model
    master = ProfilerMasterData(**master_data)

    # Initialize gap detector
    gap_config = GapConfig(
        GAP_THRESHOLD=8.0,
        MIN_DIP_DEPTH=30.0,
        MAX_GAP_WIDTH=200,
        MIN_ANOMALY_GROUP_SIZE=5,
        MAX_GROUP_JOIN_GAP=3,
        USE_GPU=True
    )
    gap_detector = GapDetector(gap_config)

    # Extract x and z data
    x_data = xz_data[:, 0]
    z_data = xz_data[:, 1]

    # Detect gaps
    detected_gaps = gap_detector.detect_gaps(x_data, z_data)

    # Convert gaps to detected features
    detected_features = []
    for x_min, x_max, width in detected_gaps:
        # Calculate depth and determine feature type
        z_values = z_data[(x_data >= x_min) & (x_data <= x_max)]
        avg_depth = np.mean(z_values)
        feature_type = "hole" if avg_depth < 0 else "nut"
        
        # Calculate confidence based on multiple factors
        width_match = any(abs(width - m.width) <= m.thresholds.width_tolerance 
                         for m in (master.hole_positions if feature_type == "hole" else master.nut_positions))
        depth_match = any(abs(avg_depth - m.thresholds.expected_depth) <= m.thresholds.depth_tolerance 
                         for m in (master.hole_positions if feature_type == "hole" else master.nut_positions))
        
        confidence = 0.95 if width_match and depth_match else 0.85

        # Create feature with validation
        feature = DetectedFeature(
            type=feature_type,
            x_min=x_min,
            x_max=x_max,
            width=width,
            depth=avg_depth,
            confidence=confidence,
            center_point=[(x_min + x_max) / 2, avg_depth]
        )

        # Validate against master data
        validation = validate_feature(feature, master)
        feature.validation = validation
        detected_features.append(feature)

    # Count features by type
    holes = [f for f in detected_features if f.type == "hole"]
    nuts = [f for f in detected_features if f.type == "nut"]

    # Overall validation
    is_valid = True
    validation_message = ""

    # Check counts
    if len(holes) != master.expected_holes:
        is_valid = False
        validation_message += f"Hole count mismatch: expected {master.expected_holes}, found {len(holes)}. "
    
    if len(nuts) != master.expected_nuts:
        is_valid = False
        validation_message += f"Nut count mismatch: expected {master.expected_nuts}, found {len(nuts)}. "

    # Check individual feature validations
    for feature in detected_features:
        if not feature.validation.is_valid:
            is_valid = False
            validation_message += f"{feature.type.capitalize()} at position {feature.center_point[0]:.2f}: {feature.validation.message} "

    return ProfilerDetectionResult(
        features=detected_features,
        total_holes=len(holes),
        total_nuts=len(nuts),
        is_valid=is_valid,
        validation_message=validation_message.strip()
    )

def validate_feature(feature: DetectedFeature, master: ProfilerMasterData) -> FeatureValidation:
    """
    Validate a detected feature against master data
    """
    master_features = master.hole_positions if feature.type == "hole" else master.nut_positions
    global_thresholds = master.global_thresholds

    # Find best matching master feature
    best_match = None
    min_position_deviation = float('inf')
    
    for master_feature in master_features:
        # Calculate position deviation (center point)
        master_center = (master_feature.x_min + master_feature.x_max) / 2
        feature_center = (feature.x_min + feature.x_max) / 2
        position_deviation = abs(master_center - feature_center)
        
        if position_deviation < min_position_deviation:
            min_position_deviation = position_deviation
            best_match = master_feature

    if best_match is None:
        return FeatureValidation(
            is_valid=False,
            position_match=False,
            width_match=False,
            depth_match=False,
            confidence=0.0,
            deviations={},
            message="No matching master feature found"
        )

    # Calculate all deviations
    width_deviation = abs(feature.width - best_match.width)
    depth_deviation = abs(feature.depth - best_match.thresholds.expected_depth)

    # Check against thresholds
    position_match = min_position_deviation <= best_match.thresholds.position_tolerance
    width_match = width_deviation <= best_match.thresholds.width_tolerance
    depth_match = depth_deviation <= best_match.thresholds.depth_tolerance

    # Overall validation
    is_valid = (position_match and width_match and depth_match and 
                feature.confidence >= global_thresholds.min_confidence)

    # Generate validation message
    message_parts = []
    if not position_match:
        message_parts.append(f"Position deviation {min_position_deviation:.2f}mm exceeds tolerance {best_match.thresholds.position_tolerance}mm")
    if not width_match:
        message_parts.append(f"Width deviation {width_deviation:.2f}mm exceeds tolerance {best_match.thresholds.width_tolerance}mm")
    if not depth_match:
        message_parts.append(f"Depth deviation {depth_deviation:.2f}mm exceeds tolerance {best_match.thresholds.depth_tolerance}mm")
    if feature.confidence < global_thresholds.min_confidence:
        message_parts.append(f"Confidence {feature.confidence:.2f} below minimum {global_thresholds.min_confidence}")

    return FeatureValidation(
        is_valid=is_valid,
        position_match=position_match,
        width_match=width_match,
        depth_match=depth_match,
        confidence=feature.confidence,
        deviations={
            "position": min_position_deviation,
            "width": width_deviation,
            "depth": depth_deviation
        },
        message="; ".join(message_parts) if message_parts else "All parameters within tolerance"
    )

# Updated models for new format
class Profile1D(BaseModel):
    X: list
    Z: list

class Thresholds(BaseModel):
    position_tolerance: float
    width_tolerance: float
    depth_tolerance: float
    expected_depth: float

class FeatureWithThresholds(BaseModel):
    x_min: float
    x_max: float
    width: float
    thresholds: Thresholds

class GlobalThresholdsModel(BaseModel):
    min_confidence: float
    max_position_deviation: float
    max_width_deviation: float
    max_depth_deviation: float

class MasterProfileDataV2(BaseModel):
    event_name: str
    raw_profile: Profile1D
    holes: list[FeatureWithThresholds]
    nuts: list[FeatureWithThresholds]
    global_thresholds: GlobalThresholdsModel

class CompareProfileDataV2(BaseModel):
    event_name: str
    raw_profile: Profile1D
    holes: list[FeatureWithThresholds]
    nuts: list[FeatureWithThresholds]

# In-memory storage for master data (new format)
MASTER_DATA_STORE_V2 = {}

@app.post("/add_master_profile")
def add_master_profile_v2(data: MasterProfileDataV2 = Body(...)):
    """
    Add master profile data for a specific event (new format).
    - event_name: Name of the event (string)
    - raw_profile: {X: [...], Z: [...]}
    - holes: List of features with thresholds
    - nuts: List of features with thresholds
    - global_thresholds: Thresholds for validation
    """
    MASTER_DATA_STORE_V2[data.event_name] = data.dict()
    return {"message": f"Master data for event '{data.event_name}' added successfully."}

@app.post("/compare_to_master")
def compare_to_master_v2(data: CompareProfileDataV2 = Body(...)):
    """
    Compare actual run data to master data for a specific event (new format).
    - event_name: Name of the event (string)
    - raw_profile: {X: [...], Z: [...]}
    - holes: List of features (with thresholds for comparison)
    - nuts: List of features (with thresholds for comparison)
    Returns per-feature pass/fail and deviation details.
    """
    master = MASTER_DATA_STORE_V2.get(data.event_name)
    if not master:
        return {"error": f"No master data found for event '{data.event_name}'"}

    def match_features(master_list, actual_list, feature_type):
        results = []
        max_len = max(len(master_list), len(actual_list))
        for i in range(max_len):
            if i >= len(master_list):
                # Extra actual feature, no master to compare
                results.append({
                    "index": i,
                    "master": None,
                    "actual": actual_list[i].dict(),
                    "is_match": False,
                    "message": f"Extra {feature_type} detected (no master to compare)",
                })
                continue
            if i >= len(actual_list):
                # Missing actual feature
                results.append({
                    "index": i,
                    "master": master_list[i],
                    "actual": None,
                    "is_match": False,
                    "message": f"Missing {feature_type} in actual data",
                })
                continue
            mg = master_list[i]
            ag = actual_list[i].dict()
            # Calculate deviations
            x_min_dev = abs(mg["x_min"] - ag["x_min"])
            x_max_dev = abs(mg["x_max"] - ag["x_max"])
            width_dev = abs(mg["width"] - ag["width"])
            # Depth comparison (optional, if present)
            depth_dev = None
            if "expected_depth" in mg["thresholds"] and "thresholds" in ag and "expected_depth" in ag["thresholds"]:
                depth_dev = abs(mg["thresholds"]["expected_depth"] - ag["thresholds"]["expected_depth"])
            # Thresholds
            pos_tol = mg["thresholds"]["position_tolerance"]
            width_tol = mg["thresholds"]["width_tolerance"]
            depth_tol = mg["thresholds"].get("depth_tolerance", None)
            # Pass/fail
            is_match = (
                x_min_dev <= pos_tol and
                x_max_dev <= pos_tol and
                width_dev <= width_tol and
                (depth_dev is None or depth_dev <= depth_tol)
            )
            # Message
            msg_parts = []
            if x_min_dev > pos_tol or x_max_dev > pos_tol:
                msg_parts.append(f"Position deviation exceeds tolerance ({x_min_dev:.2f}, {x_max_dev:.2f} > {pos_tol})")
            if width_dev > width_tol:
                msg_parts.append(f"Width deviation exceeds tolerance ({width_dev:.2f} > {width_tol})")
            if depth_dev is not None and depth_tol is not None and depth_dev > depth_tol:
                msg_parts.append(f"Depth deviation exceeds tolerance ({depth_dev:.2f} > {depth_tol})")
            if not msg_parts:
                msg_parts.append("All parameters within tolerance")
            results.append({
                "index": i,
                "master": mg,
                "actual": ag,
                "x_min_deviation": x_min_dev,
                "x_max_deviation": x_max_dev,
                "width_deviation": width_dev,
                "depth_deviation": depth_dev,
                "is_match": is_match,
                "message": "; ".join(msg_parts)
            })
        return results

    holes_comparison = match_features(master["holes"], data.holes, "hole")
    nuts_comparison = match_features(master["nuts"], data.nuts, "nut")

    comparison = {
        "event_name": data.event_name,
        "master_hole_count": len(master["holes"]),
        "actual_hole_count": len(data.holes),
        "hole_count_match": len(master["holes"]) == len(data.holes),
        "hole_comparisons": holes_comparison,
        "master_nut_count": len(master["nuts"]),
        "actual_nut_count": len(data.nuts),
        "nut_count_match": len(master["nuts"]) == len(data.nuts),
        "nut_comparisons": nuts_comparison
    }
    return comparison

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
