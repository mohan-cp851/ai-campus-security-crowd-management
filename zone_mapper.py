"""
Zone Mapper Module (Prompt 3)
Converts pixel-level bounding boxes into zone-assigned crowd counts.
Supports Strategy A (1 Cam = 1 Zone) and Strategy B (Polygon-based regions).

Extended (backward-compatible):
  assign_tracked_to_zones() — maps tracked detections (with person_id) to zones.
  assign_to_zones()         — original method, preserved unchanged.
"""

import json
import os
import logging
import config

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

logger = logging.getLogger("ZoneMapper")


class ZoneMapper:
    def __init__(
        self,
        strategy: str = config.ZONE_MAPPING_STRATEGY,
        config_path: str = config.POLYGON_CONFIG_PATH,
    ):
        self.strategy = strategy
        self.config_path = config_path
        self.polygon_map = {}
        self._load_polygon_config()

    def _load_polygon_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    self.polygon_map = json.load(f)
                logger.info(f"Loaded polygon mapping for cameras: {list(self.polygon_map.keys())}")
            except Exception as e:
                logger.error(f"Failed to read polygon config {self.config_path}: {e}")

    # ------------------------------------------------------------------
    # Original method — preserved exactly as before (backward-compatible)
    # ------------------------------------------------------------------

    def assign_to_zones(
        self,
        detections: list,
        camera_id: str = config.PRIMARY_CAMERA_ID,
        default_zone_id: int = config.PRIMARY_ZONE_ID,
    ) -> dict:
        """
        Assigns detected persons to zones.
        Returns:
            dict: { zone_id (int): count (int) }
        """
        # Strategy A: One camera = one zone (Recommended for MVP)
        if self.strategy == "camera_per_zone" or not HAS_CV2:
            cam_info = self.polygon_map.get(camera_id, {})
            target_zone = cam_info.get("default_zone_id", default_zone_id)
            return {target_zone: len(detections)}

        # Strategy B: Polygon-based spatial assignment
        counts = {}
        cam_info = self.polygon_map.get(camera_id)

        if not cam_info or "polygons" not in cam_info:
            return {default_zone_id: len(detections)}

        for poly in cam_info["polygons"]:
            counts[poly["zone_id"]] = 0

        for det in detections:
            bottom_center_x = (det["x1"] + det["x2"]) // 2
            bottom_center_y = det["y2"]
            point = (float(bottom_center_x), float(bottom_center_y))

            matched = False
            for poly in cam_info["polygons"]:
                pts = np.array(poly["points"], dtype=np.int32)
                dist = cv2.pointPolygonTest(pts, point, False)
                if dist >= 0:
                    counts[poly["zone_id"]] += 1
                    matched = True
                    break

            if not matched:
                counts[default_zone_id] = counts.get(default_zone_id, 0) + 1

        return counts

    # ------------------------------------------------------------------
    # Extended method — maps tracked detections (with person_id) to zones
    # ------------------------------------------------------------------

    def assign_tracked_to_zones(
        self,
        tracked_detections: list,
        camera_id: str = config.PRIMARY_CAMERA_ID,
        default_zone_id: int = config.PRIMARY_ZONE_ID,
    ) -> dict:
        """
        Maps tracked detections (each with person_id) to zones.

        Returns:
            dict: { zone_id (int): [person_id, ...] }
        """
        zone_persons: dict = {}

        if not tracked_detections:
            return zone_persons

        # Strategy A: all persons go to the same zone
        if self.strategy == "camera_per_zone" or not HAS_CV2:
            cam_info = self.polygon_map.get(camera_id, {})
            target_zone = int(cam_info.get("default_zone_id", default_zone_id))
            zone_persons[target_zone] = [d["person_id"] for d in tracked_detections if "person_id" in d]
            return zone_persons

        # Strategy B: Polygon-based spatial assignment
        cam_info = self.polygon_map.get(camera_id)
        if not cam_info or "polygons" not in cam_info:
            zone_persons[default_zone_id] = [d["person_id"] for d in tracked_detections if "person_id" in d]
            return zone_persons

        for poly in cam_info["polygons"]:
            zone_persons[poly["zone_id"]] = []

        for det in tracked_detections:
            if "person_id" not in det:
                continue
            # Use bottom-center of bounding box for zone assignment
            bottom_center_x = float((det["x1"] + det["x2"]) // 2)
            bottom_center_y = float(det["y2"])
            point = (bottom_center_x, bottom_center_y)

            matched = False
            for poly in cam_info["polygons"]:
                pts = np.array(poly["points"], dtype=np.int32)
                if cv2.pointPolygonTest(pts, point, False) >= 0:
                    zone_persons[poly["zone_id"]].append(det["person_id"])
                    matched = True
                    break

            if not matched:
                zone_persons.setdefault(default_zone_id, []).append(det["person_id"])

        return zone_persons
