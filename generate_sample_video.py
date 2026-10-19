"""
Utility to generate a sample crowd video (crowd_video.mp4) for testing without webcam
"""
import os
import cv2
import numpy as np
import random

def create_sample_crowd_video(filename=None, duration_sec=15, fps=20):
    if filename is None:
        filename = os.path.join(os.path.dirname(__file__), "crowd_video.mp4")

    width, height = 1280, 720
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(filename, fourcc, fps, (width, height))

    num_people = 24
    people = []
    
    # Preset color palette for pedestrian clothing
    colors = [
        (220, 150, 50),   # Blue/Cyan
        (50, 180, 230),   # Amber/Orange
        (130, 80, 220),   # Crimson/Pink
        (60, 200, 120),   # Emerald Green
        (180, 100, 180),  # Purple
        (200, 200, 200),  # White
        (70, 70, 80),     # Dark Grey
        (40, 120, 220),   # Warm Orange
    ]

    for i in range(num_people):
        people.append({
            'x': float(random.randint(120, width - 120)),
            'y': float(random.randint(160, height - 120)),
            'dx': random.uniform(-2.5, 2.5),
            'dy': random.uniform(-1.2, 1.2),
            'h': random.randint(85, 120),
            'w': random.randint(32, 44),
            'color': random.choice(colors),
            'step_phase': random.uniform(0, 6.28)
        })

    total_frames = duration_sec * fps
    print(f"Generating realistic CCTV crowd video: {filename} ({total_frames} frames)...")

    for f in range(total_frames):
        # Background: Campus walkway with perspective grid
        frame = np.full((height, width, 3), (24, 28, 40), dtype=np.uint8)

        # Floor grid lines
        for gx in range(0, width, 80):
            cv2.line(frame, (gx, 100), (gx, height), (32, 38, 54), 1)
        for gy in range(100, height, 60):
            cv2.line(frame, (0, gy), (width, gy), (32, 38, 54), 1)

        # Campus walkways
        cv2.rectangle(frame, (80, 120), (width - 80, height - 40), (28, 34, 48), -1)
        cv2.rectangle(frame, (80, 120), (width - 80, height - 40), (45, 55, 75), 1)

        # Draw walking pedestrians sorted by Y (depth ordering)
        people.sort(key=lambda p: p['y'])

        for p in people:
            p['x'] += p['dx']
            p['y'] += p['dy']
            p['step_phase'] += 0.2

            # Bounce off borders
            if p['x'] < 100 or p['x'] > width - 100:
                p['dx'] *= -1
            if p['y'] < 150 or p['y'] > height - 60:
                p['dy'] *= -1

            x, y, w, h = int(p['x']), int(p['y']), int(p['w']), int(p['h'])
            color = p['color']

            # Shadow on floor
            cv2.ellipse(frame, (x, y + h // 2 + 2), (w // 2 + 4, 6), 0, 0, 360, (15, 18, 26), -1)

            # Walking leg offset
            leg_swing = int(np.sin(p['step_phase']) * 6)
            cv2.line(frame, (x - 6, y + h // 6), (x - 8 + leg_swing, y + h // 2), (35, 40, 50), 4)
            cv2.line(frame, (x + 6, y + h // 6), (x + 8 - leg_swing, y + h // 2), (35, 40, 50), 4)

            # Torso / Upper Body (Jacket)
            cv2.rectangle(frame, (x - w // 2, y - h // 2 + 20), (x + w // 2, y + h // 6), color, -1)
            cv2.rectangle(frame, (x - w // 2, y - h // 2 + 20), (x + w // 2, y + h // 6), (255, 255, 255), 1)

            # Head with skin tone
            cv2.circle(frame, (x, y - h // 2 + 10), 11, (210, 195, 185), -1)
            cv2.circle(frame, (x, y - h // 2 + 10), 11, (100, 100, 100), 1)

        # Top CCTV HUD bar
        cv2.rectangle(frame, (0, 0), (width, 50), (12, 16, 24), -1)
        cv2.putText(frame, "CAM-01 [MAIN GATE PLAZA] - OPTICAL SURVEILLANCE FEED", (20, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (220, 230, 240), 2)
        cv2.putText(frame, f"LIVE HD 1080p | 20 FPS | FRAME #{f:04d}", (width - 340, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 230, 120), 1)

        out.write(frame)

    out.release()
    print(f"Sample video created successfully: {filename}")

if __name__ == "__main__":
    create_sample_crowd_video()

