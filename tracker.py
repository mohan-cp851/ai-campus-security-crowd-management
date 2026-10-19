"""
CentroidTracker — Robust persistent person tracking with re-identification for Campus Security.

Features:
    - Bounded spatial association (IoU + centroid distance).
    - Requires MIN_TRACK_FRAMES (default: 5) of consecutive detection before confirming an entry.
    - Prevents runaway counter inflation: unconfirmed flickers never count as entries.
    - Recent-exits re-identification: if a person is momentarily occluded or steps out for a few
      seconds, their track ID is re-activated upon return without double-counting total_entries.
    - active_count accurately reflects confirmed persons currently in frame.
"""

import math
import time
import logging
import config

logger = logging.getLogger("CentroidTracker")


class CentroidTracker:
    def __init__(
        self,
        max_distance: float = config.MAX_DISTANCE,
        max_disappeared_frames: int = config.MAX_DISAPPEARED_FRAMES,
        min_track_frames: int = config.MIN_TRACK_FRAMES,
    ):
        self.max_distance = max_distance
        self.max_disappeared_frames = max_disappeared_frames
        self.min_track_frames = max(2, min_track_frames)

        self._next_id: int = 1
        self.active_people: dict = {}
        self.recent_exits: list = []  # [{id, centroid, bbox, exit_time}]
        self.total_entries: int = 0
        self.active_count: int = 0

    def update(self, detections: list, zone_id: int = config.PRIMARY_ZONE_ID) -> list:
        """
        Update tracker with detections from the current frame.
        """
        # Age all active tracks
        for track in self.active_people.values():
            track["disappeared_frames"] += 1

        # Clean expired recent exits (>8 seconds)
        now_ts = time.time()
        self.recent_exits = [e for e in self.recent_exits if (now_ts - e["exit_time"]) < 8.0]

        if not detections:
            self._prune_exited()
            self._update_active_count()
            return []

        new_centroids = [(d["cx"], d["cy"]) for d in detections]

        if self.active_people:
            track_ids = list(self.active_people.keys())
            used_track_ids = set()
            used_det_indices = set()

            candidates = []
            for di, det in enumerate(detections):
                nc = (det["cx"], det["cy"])
                det_bbox = (det["x1"], det["y1"], det["x2"], det["y2"])
                det_w = max(1, det["x2"] - det["x1"])
                det_h = max(1, det["y2"] - det["y1"])

                for ti, tid in enumerate(track_ids):
                    track = self.active_people[tid]
                    tc = track["centroid"]
                    tb = track.get("bbox", (tc[0] - 25, tc[1] - 50, tc[0] + 25, tc[1] + 50))
                    tw = max(1, tb[2] - tb[0])
                    th = max(1, tb[3] - tb[1])

                    d = math.hypot(nc[0] - tc[0], nc[1] - tc[1])

                    # IoU
                    xA = max(det_bbox[0], tb[0])
                    yA = max(det_bbox[1], tb[1])
                    xB = min(det_bbox[2], tb[2])
                    yB = min(det_bbox[3], tb[3])
                    inter = max(0, xB - xA) * max(0, yB - yA)
                    union = (det_w * det_h) + (tw * th) - inter
                    iou = (inter / float(union)) if union > 0 else 0.0

                    in_track_box = (tb[0] <= nc[0] <= tb[2]) and (tb[1] <= nc[1] <= tb[3])
                    in_det_box = (det_bbox[0] <= tc[0] <= det_bbox[2]) and (det_bbox[1] <= tc[1] <= det_bbox[3])

                    max_dim = max(det_w, det_h, tw, th)
                    adaptive_dist = max(self.max_distance, max_dim * 1.2, 180.0)

                    if len(detections) == 1 and len(track_ids) == 1:
                        adaptive_dist = max(adaptive_dist, 350.0)

                    is_valid = (iou > 0.05) or in_track_box or in_det_box or (d <= adaptive_dist)
                    if is_valid:
                        score = d - (iou * 250.0) - (50.0 if (in_track_box or in_det_box) else 0.0)
                        candidates.append((score, d, di, ti))

            candidates.sort(key=lambda x: x[0])

            for score, dist, det_idx, track_idx in candidates:
                tid = track_ids[track_idx]
                if tid in used_track_ids or det_idx in used_det_indices:
                    continue

                track = self.active_people[tid]
                det = detections[det_idx]
                nc = new_centroids[det_idx]

                # Exponential moving average
                tc = track["centroid"]
                track["centroid"] = (
                    int(0.7 * nc[0] + 0.3 * tc[0]),
                    int(0.7 * nc[1] + 0.3 * tc[1])
                )
                track["bbox"] = (det["x1"], det["y1"], det["x2"], det["y2"])
                track["disappeared_frames"] = 0
                track["track_frames"] += 1
                track["zone_id"] = zone_id

                # Confirm entry only once minimum persistence threshold is met
                if not track["confirmed"] and track["track_frames"] >= self.min_track_frames:
                    track["confirmed"] = True
                    self.total_entries += 1
                    logger.info(
                        f"[TRACKING] Person #{tid} CONFIRMED after {track['track_frames']} frames "
                        f"→ total_entries={self.total_entries}"
                    )

                detections[det_idx]["person_id"] = tid
                detections[det_idx]["confirmed"] = track["confirmed"]
                detections[det_idx]["zone_id"] = zone_id

                used_track_ids.add(tid)
                used_det_indices.add(det_idx)

            # Check unmatched detections against recent exits before assigning a brand new ID
            for det_idx, det in enumerate(detections):
                if det_idx not in used_det_indices:
                    re_id = self._match_recent_exits(det)
                    if re_id is not None:
                        # Re-activated track — DO NOT increment total_entries!
                        self.active_people[re_id] = {
                            "centroid": (det["cx"], det["cy"]),
                            "bbox": (det["x1"], det["y1"], det["x2"], det["y2"]),
                            "track_frames": self.min_track_frames,
                            "disappeared_frames": 0,
                            "confirmed": True,
                            "zone_id": zone_id,
                        }
                        det["person_id"] = re_id
                        det["confirmed"] = True
                        det["zone_id"] = zone_id
                        logger.info(f"[TRACKING] Person #{re_id} re-acquired — total_entries preserved at {self.total_entries}")
                    else:
                        new_id = self._register(det, zone_id)
                        det["person_id"] = new_id
                        det["confirmed"] = False
                        det["zone_id"] = zone_id
        else:
            # No current tracks — check recent exits or register
            for det in detections:
                re_id = self._match_recent_exits(det)
                if re_id is not None:
                    self.active_people[re_id] = {
                        "centroid": (det["cx"], det["cy"]),
                        "bbox": (det["x1"], det["y1"], det["x2"], det["y2"]),
                        "track_frames": self.min_track_frames,
                        "disappeared_frames": 0,
                        "confirmed": True,
                        "zone_id": zone_id,
                    }
                    det["person_id"] = re_id
                    det["confirmed"] = True
                    det["zone_id"] = zone_id
                    logger.info(f"[TRACKING] Person #{re_id} re-acquired — total_entries preserved at {self.total_entries}")
                else:
                    new_id = self._register(det, zone_id)
                    det["person_id"] = new_id
                    det["confirmed"] = False
                    det["zone_id"] = zone_id

        self._prune_exited()
        self._update_active_count()

        return [d for d in detections if "person_id" in d]

    def _match_recent_exits(self, det: dict) -> int | None:
        """Find if detection matches a person who exited within the last few seconds."""
        nc = (det["cx"], det["cy"])
        best_id = None
        best_dist = 220.0  # Search radius

        for exit_item in self.recent_exits:
            ec = exit_item["centroid"]
            d = math.hypot(nc[0] - ec[0], nc[1] - ec[1])
            if d < best_dist:
                best_dist = d
                best_id = exit_item["id"]

        if best_id is not None:
            self.recent_exits = [e for e in self.recent_exits if e["id"] != best_id]
            return best_id
        return None

    def _register(self, det: dict, zone_id: int) -> int:
        """Create a new unconfirmed track. Entries counter will ONLY increment once verified."""
        tid = self._next_id
        self._next_id += 1
        self.active_people[tid] = {
            "centroid": (det["cx"], det["cy"]),
            "bbox": (det.get("x1", det["cx"] - 25), det.get("y1", det["cy"] - 50),
                     det.get("x2", det["cx"] + 25), det.get("y2", det["cy"] + 50)),
            "track_frames": 1,
            "disappeared_frames": 0,
            "confirmed": False,
            "zone_id": zone_id,
        }
        logger.debug(f"[TRACKING] New tentative ID {tid} registered at ({det['cx']}, {det['cy']})")
        return tid

    def _prune_exited(self):
        """Remove tracks missing for too long; save confirmed tracks to recent_exits."""
        now_ts = time.time()
        to_delete = []
        for tid, track in self.active_people.items():
            if track["disappeared_frames"] > self.max_disappeared_frames:
                to_delete.append(tid)

        for tid in to_delete:
            track = self.active_people.pop(tid)
            if track["confirmed"]:
                self.recent_exits.append({
                    "id": tid,
                    "centroid": track["centroid"],
                    "bbox": track["bbox"],
                    "exit_time": now_ts,
                })
                logger.info(f"[TRACKING] Person #{tid} EXITED after {track['disappeared_frames']} missing frames")

    def _update_active_count(self):
        """Active count is the number of confirmed persons currently visible (disappeared <= 3 frames)."""
        self.active_count = sum(
            1 for t in self.active_people.values()
            if t.get("confirmed", False) and t.get("disappeared_frames", 0) <= 3
        )

    def get_stats(self) -> dict:
        return {
            "active_count": self.active_count,
            "total_entries": self.total_entries,
            "tracking_ids": list(self.active_people.keys()),
            "confirmed_ids": [
                tid for tid, t in self.active_people.items() if t["confirmed"]
            ],
        }
