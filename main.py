"""
Main Execution Pipeline & Streaming Server for YOLOv8 Crowd Detection

Pipeline:
  Video Source → OpenCV Frame Capture → Bounded Frame Queue
    → YOLO Detection → Centroid Tracking → Zone Mapping
    → MJPEG Encoding → HTTP Stream → React Browser
    → Backend HTTP POST (with ring-buffer retry)

Key improvements over previous version:
  - Persistent person tracking via CentroidTracker (centroid-distance matching)
  - Bounded frame queue (FRAME_QUEUE_MAXSIZE) — drops stale frames, not new ones
  - FPS read from source; falls back to FALLBACK_FPS
  - Full error handling: each stage is isolated — one failure never kills the loop
  - Memory cleanup: frames released after encoding; cap.release() in finally block
  - Source reconnect after SOURCE_TIMEOUT_SEC of continuous failures
  - Periodic frame-drop statistics + optional memory monitoring
  - MJPEG stream at /video_feed remains on port 8000 (unchanged)
  - Backend API contract preserved; optional active_count/total_entries appended
"""

import time
import datetime
import logging
import threading
import queue
import json
import os
from collections import deque
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    import urllib.request
    import urllib.error

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

import config
from video_source import VideoSource
from detector import PersonDetector
from zone_mapper import ZoneMapper
from tracker import CentroidTracker

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("YOLOv8-Service")

# ---------------------------------------------------------------------------
# Shared state for MJPEG stream
# ---------------------------------------------------------------------------
latest_annotated_frame_bytes: bytes | None = None
frame_lock = threading.Lock()


# ---------------------------------------------------------------------------
# MJPEG HTTP Stream Server (port 8000)
# ---------------------------------------------------------------------------
class MJPEGStreamHandler(BaseHTTPRequestHandler):
    """HTTP handler that streams JPEG frames as multipart/x-mixed-replace."""

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_GET(self):
        global latest_annotated_frame_bytes

        if self.path.startswith("/video_feed"):
            self.send_response(200)
            self.send_header("Content-type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.end_headers()

            logger.debug("[STREAM] New browser client connected to /video_feed")

            while True:
                try:
                    with frame_lock:
                        frame_data = latest_annotated_frame_bytes

                    if frame_data is not None:
                        chunk = (
                            b"--frame\r\n"
                            b"Content-Type: image/jpeg\r\n"
                            b"Content-Length: " + str(len(frame_data)).encode() + b"\r\n\r\n"
                            + frame_data +
                            b"\r\n"
                        )
                        self.wfile.write(chunk)
                    time.sleep(0.04)  # ~25 fps output ceiling
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    logger.debug("[STREAM] Browser client disconnected from /video_feed")
                    break
                except OSError as e:
                    if getattr(e, "winerror", None) in (10053, 10054):
                        logger.debug(f"[STREAM] Browser client closed connection ({e})")
                    else:
                        logger.warning(f"[STREAM] Stream write error: {e}")
                    break
                except Exception as e:
                    logger.warning(f"[STREAM] Stream write error: {e}")
                    break

        elif self.path.startswith("/status"):
            body = b'{"status": "online", "model": "YOLOv8", "streaming": true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "*")
            self.send_header("Connection", "close")
            self.end_headers()
            try:
                self.wfile.write(body)
            except Exception:
                pass
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress default access log spam
        return


def start_stream_server(port: int = 8000):
    try:
        server = ThreadingHTTPServer(("0.0.0.0", port), MJPEGStreamHandler)
        logger.info(f"[STREAM] MJPEG stream server running at: http://localhost:{port}/video_feed")
        server.serve_forever()
    except Exception as e:
        logger.warning(f"[STREAM] Stream server error on port {port}: {e}")


# ---------------------------------------------------------------------------
# Frame Annotation
# ---------------------------------------------------------------------------
def annotate_frame(frame, tracked_detections: list, active_count: int, total_entries: int):
    """
    Draw high-visibility bounding boxes, centroid dots, and Person badges on frame.
    """
    if not HAS_CV2 or frame is None:
        return frame

    try:
        h, w = frame.shape[:2]

        for det in tracked_detections:
            x1, y1, x2, y2 = det["x1"], det["y1"], det["x2"], det["y2"]
            cx, cy = det.get("cx", (x1 + x2) // 2), det.get("cy", (y1 + y2) // 2)
            person_id = det.get("person_id", None)
            conf = det.get("confidence", 0.0)

            # High-visibility Emerald bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 230, 115), 2)

            # Centroid point
            cv2.circle(frame, (cx, cy), 5, (0, 200, 255), -1)

            # Label badge
            conf_pct = int(conf * 100) if conf else 0
            if person_id is not None and str(person_id) != "?":
                label = f"Person #{person_id} ({conf_pct}%)"
            else:
                label = f"Person ({conf_pct}%)" if conf_pct > 0 else "Person"

            (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
            label_y = max(y1 - 6, lh + 6)
            cv2.rectangle(frame, (x1, label_y - lh - 4), (x1 + lw + 6, label_y + 4), (15, 23, 42), -1)
            cv2.putText(frame, label, (x1 + 3, label_y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 230, 115), 2)

        # HUD overlay — top-left
        display_people = max(len(tracked_detections), active_count)
        cv2.rectangle(frame, (10, 10), (420, 85), (15, 23, 42), -1)
        cv2.rectangle(frame, (10, 10), (420, 85), (99, 102, 241), 1)
        cv2.putText(
            frame,
            f"YOLOv8 Real-Time | Detected: {display_people} person(s)",
            (20, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 230, 115) if display_people > 0 else (255, 255, 255), 2,
        )
        cv2.putText(
            frame,
            f"Sensor: {config.PRIMARY_CAMERA_ID} | Zone #{config.PRIMARY_ZONE_ID} | Entries: {total_entries}",
            (20, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (148, 163, 184), 1,
        )
        cv2.putText(
            frame,
            f"Live Tracking Mode: CentroidTracker + Re-ID (Active: {active_count})",
            (20, 76), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (56, 189, 248), 1,
        )

    except Exception as e:
        logger.warning(f"[VIDEO] Frame annotation error: {e}")

    return frame


# ---------------------------------------------------------------------------
# Main ML Detection Service
# ---------------------------------------------------------------------------
class MLDetectionService:

    def __init__(self):
        logger.info("==================================================")
        logger.info(" Starting Campus Security YOLOv8 ML Detection Service")
        logger.info(f" Target Backend: {config.NODE_BACKEND_URL}")
        logger.info(f" Video Source: {config.VIDEO_SOURCE} (Mode: {config.VIDEO_MODE})")
        logger.info(f" Tracking: MAX_DIST={config.MAX_DISTANCE} MAX_DISAP={config.MAX_DISAPPEARED_FRAMES} MIN_FRAMES={config.MIN_TRACK_FRAMES}")
        logger.info("==================================================")

        # Start MJPEG stream server in daemon thread immediately
        stream_thread = threading.Thread(
            target=start_stream_server, kwargs={"port": 8000}, daemon=True
        )
        stream_thread.start()

        # Initialise components
        self.video_source = VideoSource(
            source_path=config.VIDEO_SOURCE,
            mode=config.VIDEO_MODE,
        )
        self.detector = PersonDetector(
            model_name=config.YOLO_MODEL_NAME,
            conf_thresh=config.CONFIDENCE_THRESHOLD,
            iou_thresh=config.IOU_THRESHOLD,
        )
        self.zone_mapper = ZoneMapper(
            strategy=config.ZONE_MAPPING_STRATEGY,
            config_path=config.POLYGON_CONFIG_PATH,
        )
        self.tracker = CentroidTracker(
            max_distance=config.MAX_DISTANCE,
            max_disappeared_frames=config.MAX_DISAPPEARED_FRAMES,
            min_track_frames=config.MIN_TRACK_FRAMES,
        )

        # Bounded frame queue (drops stale frames — low latency over completeness)
        self._frame_queue: queue.Queue = queue.Queue(maxsize=config.FRAME_QUEUE_MAXSIZE)

        # Ring buffer for network-offline resilience
        self.ring_buffer: deque = deque(maxlen=config.RING_BUFFER_CAPACITY)

        # State
        self.is_running = True

        # Frame statistics counters
        self._frames_received: int = 0
        self._frames_processed: int = 0
        self._frames_dropped: int = 0
        self._frames_failed: int = 0

        # FPS tracking
        self._source_fps: float = self._read_source_fps()
        self._frame_sleep: float = 1.0 / max(self._source_fps, 1.0)

        # Source health tracking for reconnect logic
        self._last_good_frame_time: float = time.time()
        self._last_post_time: float = 0.0
        self._last_posted_count: int = -1

    # ------------------------------------------------------------------
    # FPS helpers
    # ------------------------------------------------------------------

    def _read_source_fps(self) -> float:
        """Read FPS from video capture; fall back to FALLBACK_FPS if unavailable."""
        if not HAS_CV2 or self.video_source.cap is None:
            return float(config.FALLBACK_FPS)
        try:
            raw_fps = self.video_source.cap.get(cv2.CAP_PROP_FPS)
            if raw_fps and raw_fps > 0 and raw_fps < 200:
                logger.info(f"[VIDEO] Source FPS detected: {raw_fps:.1f}")
                return float(raw_fps)
        except Exception:
            pass
        logger.info(f"[VIDEO] Source FPS unavailable — using fallback: {config.FALLBACK_FPS}")
        return float(config.FALLBACK_FPS)

    # ------------------------------------------------------------------
    # Network helpers (preserve existing ring-buffer / retry logic)
    # ------------------------------------------------------------------

    def _http_post(self, payload: dict):
        headers = {
            "Content-Type": "application/json",
            "x-ml-service-key": config.ML_SERVICE_SECRET,
        }
        if HAS_REQUESTS:
            res = requests.post(
                config.NODE_BACKEND_URL,
                json=payload,
                headers=headers,
                timeout=config.POST_TIMEOUT_SEC,
            )
            return res.status_code == 200, res.status_code, res.text
        else:
            req = urllib.request.Request(
                config.NODE_BACKEND_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=config.POST_TIMEOUT_SEC) as response:
                return response.status == 200, response.status, response.read().decode("utf-8")

    def post_payload_with_retry(self, payload: dict):
        """Flush ring buffer first, then send payload with exponential-backoff retry."""
        # Flush any buffered payloads
        while self.ring_buffer:
            buffered = self.ring_buffer.popleft()
            try:
                self._http_post(buffered)
                logger.info(f"[BACKEND] Ring-buffer flushed payload for zone {buffered.get('zone_id')}")
            except Exception:
                self.ring_buffer.appendleft(buffered)
                break

        for attempt in range(1, config.MAX_POST_RETRIES + 1):
            try:
                ok, status_code, body = self._http_post(payload)
                if ok:
                    logger.debug(f"[BACKEND] Detection sent OK (zone={payload.get('zone_id')} count={payload.get('people_count')})")
                    return True, status_code
                else:
                    logger.warning(f"[BACKEND] Backend rejected payload (HTTP {status_code}): {body}")
            except Exception as e:
                logger.warning(f"[BACKEND] POST attempt {attempt}/{config.MAX_POST_RETRIES} failed: {e}")
                if attempt < config.MAX_POST_RETRIES:
                    time.sleep(0.3 * (2 ** (attempt - 1)))

        self.ring_buffer.append(payload)
        logger.warning(f"[BACKEND] Backend unavailable — payload buffered (buffer size={len(self.ring_buffer)})")
        return False, None

    # ------------------------------------------------------------------
    # Memory diagnostic
    # ------------------------------------------------------------------

    @staticmethod
    def _log_memory():
        try:
            import os as _os
            pid = _os.getpid()
            # Attempt to read from /proc (Linux) — on Windows falls through
            proc_path = f"/proc/{pid}/status"
            if _os.path.exists(proc_path):
                with open(proc_path) as f:
                    for line in f:
                        if line.startswith("VmRSS:"):
                            kb = int(line.split()[1])
                            logger.info(f"[MEMORY] Usage: {kb // 1024} MB")
                            return
            # Windows fallback via psutil (optional)
            try:
                import psutil
                mem_mb = psutil.Process(_os.getpid()).memory_info().rss // (1024 * 1024)
                logger.info(f"[MEMORY] Usage: {mem_mb} MB")
            except ImportError:
                pass  # psutil not installed — skip silently
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Frame reader thread — fills bounded queue
    # ------------------------------------------------------------------

    def _frame_reader_thread(self):
        """
        Continuously reads frames from the video source and puts them into
        the bounded queue.  If the queue is full, the oldest frame is dropped
        to make room for the newest (low-latency preference).
        """
        logger.info("[VIDEO] Frame reader thread started")
        while self.is_running:
            try:
                # Source reconnect after prolonged failure
                elapsed_since_good = time.time() - self._last_good_frame_time
                if elapsed_since_good > config.SOURCE_TIMEOUT_SEC:
                    logger.warning(f"[VIDEO] No good frame for {elapsed_since_good:.1f}s — attempting source reconnect")
                    self.video_source.release()
                    time.sleep(0.5)
                    self.video_source = VideoSource(
                        source_path=config.VIDEO_SOURCE, mode=config.VIDEO_MODE
                    )
                    self._source_fps = self._read_source_fps()
                    self._frame_sleep = 1.0 / max(self._source_fps, 1.0)
                    self._last_good_frame_time = time.time()

                success, frame = self.video_source.read_frame()
                if not success or frame is None:
                    time.sleep(0.1)
                    continue

                self._last_good_frame_time = time.time()
                self._frames_received += 1

                # Non-blocking put — if queue is full, evict oldest frame
                if self._frame_queue.full():
                    try:
                        self._frame_queue.get_nowait()
                        self._frames_dropped += 1
                    except queue.Empty:
                        pass

                self._frame_queue.put_nowait(frame)

            except Exception as e:
                logger.error(f"[VIDEO] Frame reader error: {e}")
                time.sleep(1.0)

        logger.info("[VIDEO] Frame reader thread stopped")

    # ------------------------------------------------------------------
    # Main processing loop
    # ------------------------------------------------------------------

    def run(self):
        global latest_annotated_frame_bytes

        # Start reader thread
        reader_thread = threading.Thread(target=self._frame_reader_thread, daemon=True)
        reader_thread.start()

        frame_idx = 0
        last_stats_frame = 0
        last_memory_frame = 0

        logger.info("[VIDEO] Processing loop started — waiting for frames...")

        try:
            while self.is_running:
                # ----- Drain frame from queue ----------------------------------------
                try:
                    frame = self._frame_queue.get(timeout=5.0)
                except queue.Empty:
                    logger.warning("[VIDEO] No frames received for 5s — waiting for source...")
                    continue

                frame_idx += 1

                # ----- Periodic statistics log ---------------------------------------
                if config.STATS_LOG_INTERVAL > 0 and (frame_idx - last_stats_frame) >= config.STATS_LOG_INTERVAL:
                    last_stats_frame = frame_idx
                    tracker_stats = self.tracker.get_stats()
                    logger.info(
                        f"[STATS] Received={self._frames_received} "
                        f"Processed={self._frames_processed} "
                        f"Dropped={self._frames_dropped} "
                        f"Failed={self._frames_failed} "
                        f"QueueDepth={self._frame_queue.qsize()} "
                        f"ActivePeople={tracker_stats['active_count']} "
                        f"TotalEntries={tracker_stats['total_entries']}"
                    )

                # ----- Optional memory log -------------------------------------------
                if (
                    config.MEMORY_LOG_INTERVAL > 0
                    and (frame_idx - last_memory_frame) >= config.MEMORY_LOG_INTERVAL
                ):
                    last_memory_frame = frame_idx
                    self._log_memory()

                # ==========================================================
                # INFERENCE + TRACKING PIPELINE
                # ==========================================================

                # ----- 1. YOLO Detection -----------------------------------------
                try:
                    total_raw, detections, conf_avg = self.detector.detect(frame)
                except Exception as e:
                    logger.error(f"[VIDEO] Detection failed on frame {frame_idx}: {e}")
                    self._frames_failed += 1
                    del frame
                    continue

                # ----- 2. Centroid Tracking --------------------------------------
                try:
                    tracked_dets = self.tracker.update(
                        detections, zone_id=config.PRIMARY_ZONE_ID
                    )
                    tracker_stats = self.tracker.get_stats()
                    active_count = tracker_stats["active_count"]
                    total_entries = tracker_stats["total_entries"]
                except Exception as e:
                    logger.error(f"[TRACKING] Tracker update failed: {e}")
                    tracked_dets = detections
                    active_count = total_raw
                    total_entries = 0

                # If tracking is starting up, ensure active detections are visible
                if not tracked_dets and detections:
                    tracked_dets = detections

                # ----- 3. Zone mapping (count-based, backward-compatible) ---------
                try:
                    zone_counts = self.zone_mapper.assign_to_zones(
                        tracked_dets if tracked_dets else detections,
                        camera_id=config.PRIMARY_CAMERA_ID,
                        default_zone_id=config.PRIMARY_ZONE_ID,
                    )
                except Exception as e:
                    logger.error(f"[TRACKING] Zone mapping failed: {e}")
                    zone_counts = {config.PRIMARY_ZONE_ID: max(len(detections), active_count)}

                # ----- 4. Backend POST (Asynchronous & Throttled) ----------------
                timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
                now_ts = time.time()
                for zone_id, count in zone_counts.items():
                    count_changed = (count != self._last_posted_count)
                    time_elapsed = (now_ts - self._last_post_time) >= config.PROCESSING_INTERVAL_SEC
                    if count_changed or time_elapsed:
                        self._last_post_time = now_ts
                        self._last_posted_count = count
                        payload = {
                            "camera_id": config.PRIMARY_CAMERA_ID,
                            "zone_id": zone_id,
                            "people_count": count,
                            "confidence_avg": conf_avg,
                            "detection_source": "yolov8",
                            "timestamp": timestamp,
                            "active_count": max(count, active_count),
                            "total_entries": total_entries,
                        }
                        threading.Thread(target=self.post_payload_with_retry, args=(payload,), daemon=True).start()

                self._frames_processed += 1

                # ----- 5. Frame annotation + MJPEG encode ------------------------
                if HAS_CV2:
                    try:
                        annotated = annotate_frame(
                            frame.copy(), tracked_dets, active_count, total_entries
                        )
                        ret, jpeg = cv2.imencode(
                            ".jpg", annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 75]
                        )
                        if ret:
                            with frame_lock:
                                latest_annotated_frame_bytes = jpeg.tobytes()
                        else:
                            logger.warning(f"[STREAM] JPEG encoding failed on frame {frame_idx}")
                        del annotated, jpeg
                    except Exception as e:
                        logger.error(f"[STREAM] Frame encode/stream error: {e}")

                # ----- 6. Memory cleanup -----------------------------------------
                del frame

                # Minimal yield so UI & threads remain silky smooth
                time.sleep(0.005)

        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt — shutting down ML service...")
            self.is_running = False
        except Exception as e:
            logger.error(f"Fatal error in processing loop: {e}", exc_info=True)
            self.is_running = False
        finally:
            self.is_running = False
            try:
                self.video_source.release()
                logger.info("[VIDEO] Video source released")
            except Exception:
                pass
            logger.info(
                f"[STATS] Final — Received={self._frames_received} "
                f"Processed={self._frames_processed} "
                f"Dropped={self._frames_dropped} "
                f"Failed={self._frames_failed}"
            )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    service = MLDetectionService()
    service.run()
