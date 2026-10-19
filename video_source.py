"""
Video Source Abstraction (Prompts 1, 7, 8)
Handles laptop webcams (DirectShow for Windows), RTSP streams, and recorded demo files.
"""

import time
import os
import logging

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

logger = logging.getLogger("VideoSource")

class VideoSource:
    def __init__(self, source_path="0", mode="webcam", is_file=False):
        self.source_path = source_path
        self.mode = mode
        self.is_file = is_file or mode == "file"
        self.cap = None
        self.is_connected = False
        self._black_frame_count = 0
        self._init_capture()

    def _init_capture(self):
        if not HAS_CV2:
            logger.warning("OpenCV (cv2) is not installed. Run: pip install opencv-python")
            self.is_connected = True
            return

        try:
            # Handle integer webcam indices
            if isinstance(self.source_path, str) and self.source_path.isdigit():
                src = int(self.source_path)
            elif isinstance(self.source_path, str) and not self.source_path.startswith(('rtsp://', 'http://', 'https://')):
                # Resolve relative local file path
                if not os.path.isabs(self.source_path):
                    resolved = os.path.join(os.path.dirname(__file__), self.source_path)
                    src = resolved if os.path.exists(resolved) else self.source_path
                else:
                    src = self.source_path
            else:
                src = self.source_path

            logger.info(f"Opening video stream from: '{src}' (Mode: {self.mode})")

            # On Windows, cv2.CAP_DSHOW provides instant access to laptop webcam without hangs
            if self.mode == "webcam" and isinstance(src, int):
                self.cap = cv2.VideoCapture(src, cv2.CAP_DSHOW)
                if not self.cap.isOpened():
                    self.cap = cv2.VideoCapture(src) # fallback standard backend
            else:
                self.cap = cv2.VideoCapture(src)

            if self.cap.isOpened():
                self.is_connected = True
                # Set optimal resolution for webcam performance and warm up sensor
                if self.mode == "webcam":
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    self.cap.set(cv2.CAP_PROP_FPS, 30)
                    for _ in range(5):
                        self.cap.read()
                logger.info(f"Video capture successfully connected to {self.mode} source: {src}")
            else:
                # If webcam failed, fallback to sample crowd_video.mp4
                if self.mode == "webcam":
                    fallback_file = os.path.join(os.path.dirname(__file__), "crowd_video.mp4")
                    if os.path.exists(fallback_file):
                        logger.warning(f"Webcam index {src} not found. Falling back to '{fallback_file}'.")
                        self.cap = cv2.VideoCapture(fallback_file)
                        self.mode = "file"
                        self.is_file = True
                        if self.cap.isOpened():
                            self.is_connected = True
                            return

                self.is_connected = False
                logger.warning(f"Unable to open video source: '{src}'.")
        except Exception as e:
            self.is_connected = False
            logger.error(f"Error initializing capture source: {e}")

    def read_frame(self):
        """Reads a frame with automatic loop recovery for video files."""
        if not HAS_CV2:
            return True, None

        if not self.is_connected or self.cap is None:
            self._init_capture()
            if not self.is_connected:
                return False, None

        ret, frame = self.cap.read()

        # Handle End-of-File for video files -> loop from start (Prompt 8)
        if not ret and self.is_file:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()

        if not ret or frame is None:
            self.is_connected = False
            logger.warning("Frame read failed. Retrying...")
            return False, None

        # Detect persistent hardware blackout on webcam (DirectShow cutoff: all pixels literally 0)
        if self.mode == "webcam":
            if frame.max() == 0:
                self._black_frame_count += 1
                if self._black_frame_count >= 45:
                    logger.warning("[VIDEO] 45 consecutive hardware black frames detected — resetting camera")
                    self.release()
                    self._black_frame_count = 0
                    return False, None
            else:
                self._black_frame_count = 0

        return True, frame

    def release(self):
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
            self.is_connected = False
