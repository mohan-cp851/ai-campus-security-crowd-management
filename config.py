"""
Configuration Module for YOLOv8 ML Detection Service (Prompts 1, 2, 5, 8)
Extended with Centroid Tracking, Frame Queue, FPS, and Resilience settings.
"""

import os

# ---------------------------------------------------------------------------
# Backend API Integration
# ---------------------------------------------------------------------------
NODE_BACKEND_URL = os.getenv("NODE_BACKEND_URL", "http://localhost:5000/api/internal/detections")
ML_SERVICE_SECRET = os.getenv("ML_SERVICE_SECRET", "campus_security_ml_secret_key_2026")

# ---------------------------------------------------------------------------
# Detection Model Settings
# ---------------------------------------------------------------------------
YOLO_MODEL_NAME = os.getenv("YOLO_MODEL_NAME", "yolov8n.pt")
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.35"))
IOU_THRESHOLD = float(os.getenv("IOU_THRESHOLD", "0.45"))
PERSON_CLASS_ID = 0  # COCO dataset class 0 = person

# ---------------------------------------------------------------------------
# Video Source & Processing Cadence
# ---------------------------------------------------------------------------
VIDEO_MODE = os.getenv("VIDEO_MODE", "webcam")
VIDEO_SOURCE = os.getenv("VIDEO_SOURCE", "0")
PROCESS_EVERY_N_FRAMES = int(os.getenv("PROCESS_EVERY_N_FRAMES", "1"))
TARGET_FPS = int(os.getenv("TARGET_FPS", "25"))
PROCESSING_INTERVAL_SEC = float(os.getenv("PROCESSING_INTERVAL_SEC", "0.5"))

# ---------------------------------------------------------------------------
# FPS Management
# ---------------------------------------------------------------------------
# Fallback FPS used when the video source does not report a valid FPS value
FALLBACK_FPS = int(os.getenv("FALLBACK_FPS", "25"))

# ---------------------------------------------------------------------------
# Frame Queue (bounded — prevents unbounded memory growth)
# ---------------------------------------------------------------------------
FRAME_QUEUE_MAXSIZE = int(os.getenv("FRAME_QUEUE_MAXSIZE", "30"))

# ---------------------------------------------------------------------------
# Centroid Tracker Parameters
# ---------------------------------------------------------------------------
# Maximum pixel distance to associate a new centroid to an existing track
MAX_DISTANCE = float(os.getenv("MAX_DISTANCE", "120"))

# Frames a track may remain unmatched before it is removed (exit detection)
MAX_DISAPPEARED_FRAMES = int(os.getenv("MAX_DISAPPEARED_FRAMES", "60"))

# Minimum frames a track must be visible before it is "confirmed" (entry counted)
MIN_TRACK_FRAMES = int(os.getenv("MIN_TRACK_FRAMES", "5"))

# ---------------------------------------------------------------------------
# Zone Mapping Strategy
# ---------------------------------------------------------------------------
ZONE_MAPPING_STRATEGY = os.getenv("ZONE_MAPPING_STRATEGY", "camera_per_zone")
PRIMARY_ZONE_ID = int(os.getenv("PRIMARY_ZONE_ID", "1"))
PRIMARY_CAMERA_ID = os.getenv("PRIMARY_CAMERA_ID", "cam_main_gate")
POLYGON_CONFIG_PATH = os.getenv("POLYGON_CONFIG_PATH", "zones_config.json")

# ---------------------------------------------------------------------------
# Resilience & Network Settings
# ---------------------------------------------------------------------------
MAX_POST_RETRIES = int(os.getenv("MAX_POST_RETRIES", "3"))
POST_TIMEOUT_SEC = float(os.getenv("POST_TIMEOUT_SEC", "2.0"))
RING_BUFFER_CAPACITY = int(os.getenv("RING_BUFFER_CAPACITY", "20"))
RETRY_SOURCE_INTERVAL_SEC = float(os.getenv("RETRY_SOURCE_INTERVAL_SEC", "3.0"))

# Seconds without a successful frame read before attempting a full reconnect
SOURCE_TIMEOUT_SEC = float(os.getenv("SOURCE_TIMEOUT_SEC", "5.0"))

# ---------------------------------------------------------------------------
# Diagnostics / Logging
# ---------------------------------------------------------------------------
# Log frame-drop statistics every N frames
STATS_LOG_INTERVAL = int(os.getenv("STATS_LOG_INTERVAL", "150"))

# Log memory usage periodically (set to 0 to disable)
MEMORY_LOG_INTERVAL = int(os.getenv("MEMORY_LOG_INTERVAL", "300"))
