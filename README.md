# 🤖 YOLOv8 Real-Time Crowd Detection Service (`/ml-service`)

Standalone Python service responsible for optical frame ingestion, YOLOv8 person detection, spatial zone mapping, and streaming raw crowd telemetry to the Node.js backend.

---

## 🏗️ Architecture & Boundaries

- **Input:** Live Webcam / RTSP CCTV Stream / Loopable recorded `.mp4` video files
- **Inference:** Pretrained YOLOv8 (`yolov8n.pt` / `yolov8s.pt`) filtered to COCO Class `0` (`person`)
- **Zone Assignment:** Strategy A (1 Camera = 1 Zone) or Strategy B (Polygon Region Point-in-Polygon mapping)
- **Output:** Authenticated HTTP POST to Node.js internal endpoint: `POST http://localhost:5000/api/internal/detections` with header `x-ml-service-key`
- **Separation of Concerns:** This Python service **never** talks to MySQL directly and **never** computes business metrics (occupancy, density, status, alerts). Those are computed in Node.js.

---

## 🚀 Setup & Installation

### 1. Create & Activate Virtual Environment
```bash
cd ml-service
python -m venv venv

# On Windows:
venv\Scripts\activate

# On Linux/macOS:
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## ⚙️ Configuration (`config.py` / Environment Variables)

| Variable | Default | Description |
|---|---|---|
| `NODE_BACKEND_URL` | `http://localhost:5000/api/internal/detections` | Target Node.js internal detection ingest endpoint |
| `ML_SERVICE_SECRET` | `campus_security_ml_secret_key_2026` | Shared secret header `x-ml-service-key` |
| `VIDEO_MODE` | `webcam` | Input mode: `"webcam"`, `"file"`, or `"rtsp"` |
| `VIDEO_SOURCE` | `"0"` | Webcam device index (`0`), RTSP URL, or path to `.mp4` file |
| `YOLO_MODEL_NAME` | `yolov8n.pt` | Pretrained YOLO weights (`yolov8n.pt` or `yolov8s.pt`) |
| `CONFIDENCE_THRESHOLD` | `0.40` | Minimum confidence score for person detection |
| `PRIMARY_ZONE_ID` | `1` | Default zone mapped to the primary camera stream |
| `ZONE_MAPPING_STRATEGY`| `camera_per_zone` | `"camera_per_zone"` (1-to-1) or `"polygon"` (multi-zone) |

---

## 🖥️ Multi-Process Orchestration (Prompt 9)

Run the system across three terminals:

```
Terminal 1: Node.js Backend API
  cd backend
  node server.js
  -> Listening on http://localhost:5000

Terminal 2: React Frontend Dashboard
  cd frontend
  npm run dev
  -> Accessible on http://localhost:5173

Terminal 3: Python YOLOv8 ML Service
  cd ml-service
  python main.py
  -> Reads camera -> Inferences YOLOv8 -> Pushes detections to Port 5000
```

---

## 🧪 Testing & Verification

### Test the Node.js Ingest Endpoint with `curl`
You can verify the backend `/api/internal/detections` endpoint without opening a webcam:

```bash
curl -X POST http://localhost:5000/api/internal/detections \
  -H "Content-Type: application/json" \
  -H "x-ml-service-key: campus_security_ml_secret_key_2026" \
  -d '{
    "camera_id": "cam_main_gate",
    "zone_id": 1,
    "people_count": 340,
    "confidence_avg": 0.88,
    "detection_source": "yolov8",
    "timestamp": "2026-08-28T10:15:32Z"
  }'
```

**Expected Response (HTTP 200):**
```json
{
  "success": true,
  "processed": {
    "zone_id": 1,
    "people_count": 340,
    "occupancy": 85,
    "density": 0.97,
    "status": "WARNING",
    "alertGenerated": true
  }
}
```
The React dashboard will immediately reflect the new YOLOv8 people count and generate the corresponding warning alert over Socket.IO without requiring a browser refresh.
