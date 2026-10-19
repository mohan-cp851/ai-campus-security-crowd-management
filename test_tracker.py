"""Quick unit test for CentroidTracker."""
import sys
sys.path.insert(0, '.')
from tracker import CentroidTracker
import config

def run():
    t = CentroidTracker()
    print(f"[OK] CentroidTracker created MAX_DIST={t.max_distance} MAX_DISAP={t.max_disappeared_frames} MIN_FRAMES={t.min_track_frames}")

    # --- Test 2: person confirmed after MIN_TRACK_FRAMES ---
    dets = [{"x1":100,"y1":100,"x2":150,"y2":200,"confidence":0.9,"cx":125,"cy":150}]
    for _ in range(config.MIN_TRACK_FRAMES):
        t.update(dets, zone_id=1)
    s = t.get_stats()
    assert s["active_count"] == 1, f"Expected active=1 got {s['active_count']}"
    assert s["total_entries"] == 1, f"Expected entries=1 got {s['total_entries']}"
    print(f"[OK] Confirmed after {config.MIN_TRACK_FRAMES} frames -> active={s['active_count']} entries={s['total_entries']}")

    # --- Test 3: same person 10 more frames -> count stays at 1 ---
    for _ in range(10):
        t.update(dets, zone_id=1)
    s = t.get_stats()
    assert s["total_entries"] == 1, f"Expected entries still 1, got {s['total_entries']}"
    print(f"[OK] 10 more frames -> entries still {s['total_entries']}")

    # --- Test 4: exit ---
    for _ in range(config.MAX_DISAPPEARED_FRAMES + 2):
        t.update([], zone_id=1)
    s = t.get_stats()
    assert s["active_count"] == 0, f"Expected active=0 after exit, got {s['active_count']}"
    assert s["total_entries"] == 1, f"entries should not drop on exit, got {s['total_entries']}"
    print(f"[OK] Exit -> active={s['active_count']} entries={s['total_entries']}")

    # --- Test 5: re-entry -> new count ---
    dets2 = [{"x1":200,"y1":200,"x2":250,"y2":300,"confidence":0.88,"cx":225,"cy":250}]
    for _ in range(config.MIN_TRACK_FRAMES):
        t.update(dets2, zone_id=1)
    s = t.get_stats()
    assert s["total_entries"] == 2, f"Re-entry should give entries=2, got {s['total_entries']}"
    print(f"[OK] Re-entry -> entries={s['total_entries']}")

    # --- Test 6: 3 simultaneous distinct people ---
    t2 = CentroidTracker()
    multi = [
        {"x1":10,"y1":10,"x2":50,"y2":100,"confidence":0.9,"cx":30,"cy":55},
        {"x1":200,"y1":10,"x2":240,"y2":100,"confidence":0.9,"cx":220,"cy":55},
        {"x1":400,"y1":10,"x2":440,"y2":100,"confidence":0.9,"cx":420,"cy":55},
    ]
    for _ in range(config.MIN_TRACK_FRAMES):
        t2.update(multi, zone_id=1)
    s2 = t2.get_stats()
    assert s2["active_count"] == 3, f"Expected active=3, got {s2['active_count']}"
    assert s2["total_entries"] == 3, f"Expected entries=3, got {s2['total_entries']}"
    assert len(set(s2["confirmed_ids"])) == 3, "All 3 IDs must be unique"
    print(f"[OK] 3 simultaneous people -> active={s2['active_count']} entries={s2['total_entries']} ids={s2['confirmed_ids']}")

    # --- Test 7: import detector centroid ---
    from detector import PersonDetector
    pd = PersonDetector()
    print(f"[OK] PersonDetector loaded, model={'loaded' if pd.model else 'fallback'}")

    # --- Test 8: import zone_mapper ---
    from zone_mapper import ZoneMapper
    zm = ZoneMapper()
    result = zm.assign_tracked_to_zones(
        [{"x1":10,"y1":10,"x2":50,"y2":100,"cx":30,"cy":55,"person_id":1,"confirmed":True}],
        default_zone_id=1
    )
    print(f"[OK] ZoneMapper tracked -> {result}")

    print("")
    print("ALL TESTS PASSED")

if __name__ == "__main__":
    run()
