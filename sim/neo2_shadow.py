"""DJI Neo 2 'shadow mode': runs the perception + decision pipeline on real
footage (recorded clip or screen-mirrored feed) and overlays what the planner
WOULD command. The Neo 2 is flown by the pilot; nothing is sent to the drone.

  python neo2_shadow.py --video clip.mp4 --detector yolo   [--hfov 80] [--standoff 0.5]
  python neo2_shadow.py --camera 0 --detector hsv          (live webcam / capture card)

Distance is monocular: Z = f_px * D_real / w_px, using the known orange diameter
(default 7.5 cm). Verify --hfov against the Neo 2 spec for the video mode used.
Outputs: annotated MP4 + per-frame CSV (for the sim-to-real perception table).
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def hsv_boxes(bgr):
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, np.array([5, 150, 150]), np.array([22, 255, 255]))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    boxes, scores = [], []
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if a > 30:
            boxes.append((x, y, x + w, y + h))
            scores.append(min(1.0, a / 400))
    return np.array(boxes, float).reshape(-1, 4), np.array(scores)


def suggest(box, W, H, f_px, diam, standoff):
    """Same decision rule as the sim planner, in image space."""
    if box is None:
        return "SEARCH: yaw +45 deg", None, None
    x0, y0, x1, y1 = box
    w = max(x1 - x0, y1 - y0)
    z = f_px * diam / max(w, 1)
    bearing = math.degrees(math.atan(((x0 + x1) / 2 - W / 2) / f_px))
    if abs(bearing) > 10:
        return f"YAW {'LEFT' if bearing < 0 else 'RIGHT'} {abs(bearing):.0f} deg", z, bearing
    if z > standoff + 0.1:
        return f"FORWARD {min(z - standoff, 0.5):.2f} m", z, bearing
    if z < standoff - 0.1:
        return f"BACK {standoff - z:.2f} m", z, bearing
    return "STOP: target reached, report FOUND", z, bearing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video")
    ap.add_argument("--camera", type=int)
    ap.add_argument("--detector", default="yolo", choices=["yolo", "hsv", "owlv2", "hybrid"])
    ap.add_argument("--query", default="orange")
    ap.add_argument("--hfov", type=float, default=80.0, help="horizontal FOV of the footage (deg) - verify")
    ap.add_argument("--diam", type=float, default=0.075, help="real object diameter (m)")
    ap.add_argument("--standoff", type=float, default=0.5)
    ap.add_argument("--every", type=int, default=3, help="process every Nth frame")
    ap.add_argument("--width", type=int, default=960, help="resize width for processing")
    a = ap.parse_args()
    cap = cv2.VideoCapture(a.video if a.video else a.camera)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    name = Path(a.video).stem if a.video else f"cam{a.camera}"
    out_dir = ROOT / "out" / "neo2"
    out_dir.mkdir(parents=True, exist_ok=True)
    det = vlm = None
    if a.detector in ("yolo", "hybrid"):
        from dronenav.models import get_yolo
        det = get_yolo()
    if a.detector == "owlv2":
        from dronenav.models import OwlV2Perception
        det = OwlV2Perception()
    if a.detector == "hybrid":
        from dronenav.models import crop, get_vlm
        vlm = get_vlm()
    vw, rows, k = None, [], 0
    import time
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        k += 1
        if k % a.every:
            continue
        H0, W0 = frame.shape[:2]
        scale = a.width / W0
        frame = cv2.resize(frame, (a.width, int(H0 * scale)))
        H, W = frame.shape[:2]
        f_px = (W / 2) / math.tan(math.radians(a.hfov) / 2)
        t0 = time.perf_counter()
        if a.detector == "hsv":
            boxes, scores = hsv_boxes(frame)
        else:
            boxes, scores = det.raw(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), a.query)
        keep = scores >= 0.15 if a.detector != "hsv" else scores > 0
        boxes, scores = boxes[keep], scores[keep]
        verified = []
        if vlm is not None:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            for b in boxes:
                ans = vlm.ask(crop(rgb, b), f"Is the object in the centre of this image a real {a.query} fruit? Answer yes or no.", 3)
                verified.append(ans.lower().startswith("yes"))
            boxes, scores = boxes[np.array(verified, bool)] if len(boxes) else boxes, \
                scores[np.array(verified, bool)] if len(scores) else scores
        ms = (time.perf_counter() - t0) * 1000
        best = boxes[int(np.argmax(scores))] if len(scores) else None
        action, z, bearing = suggest(best, W, H, f_px, a.diam, a.standoff)
        for b, s in zip(boxes, scores):
            x0, y0, x1, y1 = map(int, b)
            cv2.rectangle(frame, (x0, y0), (x1, y1), (0, 255, 0), 2)
            cv2.putText(frame, f"{a.query} {s:.2f}", (x0, max(15, y0 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.rectangle(frame, (0, 0), (W, 70), (0, 0, 0), -1)
        cv2.putText(frame, f"SHADOW MODE (pilot flying)  detector={a.detector}  {ms:.0f} ms", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
        dtxt = f"est. dist {z:.2f} m" if z else "target not visible"
        cv2.putText(frame, f"would command: {action}   ({dtxt})", (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.65,
                    (0, 220, 255), 2)
        if vw is None:
            vw = cv2.VideoWriter(str(out_dir / f"{name}_{a.detector}.mp4"), cv2.VideoWriter_fourcc(*"mp4v"),
                                 fps / a.every, (W, H))
        vw.write(frame)
        rows.append(dict(frame=k, t=k / fps, n_dets=len(scores), best_conf=float(scores.max()) if len(scores) else 0,
                         est_dist=z, bearing_deg=bearing, action=action, latency_ms=ms))
        if a.camera is not None:
            cv2.imshow("shadow", frame)
            if cv2.waitKey(1) == 27:
                break
    if vw:
        vw.release()
    pd.DataFrame(rows).to_csv(out_dir / f"{name}_{a.detector}.csv", index=False)
    print(f"{len(rows)} frames -> {out_dir}")


if __name__ == "__main__":
    main()
