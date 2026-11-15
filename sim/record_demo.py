"""Records a demo video of one episode: drone camera view with detections and
status on the left, top-down map with trajectory on the right.

  python record_demo.py --config C1 --scenario T5 --seed 0 [--sim pybullet|mujoco]
Output: out/demo_<sim>_<config>_<scenario>_<seed>.mp4
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from dronenav.runner import run_episode  # noqa: E402
from dronenav.scenarios import SCENARIOS, make_scenario  # noqa: E402
from run_batch import make_perception  # noqa: E402

MAP = 480
S = MAP / 6.4


def w2m(xy):
    return int(MAP / 2 + xy[0] * S), int(MAP / 2 - xy[1] * S)


def draw_map(sc, traj, pose_true, belief):
    img = np.full((MAP, MAP, 3), 250, np.uint8)
    h = sc["room"] / 2
    cv2.rectangle(img, w2m((-h, h)), w2m((h, -h)), (0, 0, 0), 2)
    for o in sc["obstacles"]:
        if o["type"] == "cyl":
            cv2.circle(img, w2m(o["xy"]), int(o["size"] * S), (150, 135, 122), -1)
        else:
            yaw = o.get("yaw", 0) + math.pi / 2
            c, s = math.cos(yaw), math.sin(yaw)
            W, L = o["size"]
            pts = np.array([[-W / 2, -L / 2], [W / 2, -L / 2], [W / 2, L / 2], [-W / 2, L / 2]]) @ np.array([[c, s], [-s, c]])
            cv2.fillPoly(img, [np.array([w2m(p + o["xy"]) for p in pts])], (136, 159, 168))
    col = {"orange": (0, 140, 255), "orange_ball": (0, 106, 255), "orange_cube": (51, 153, 255),
           "apple": (0, 0, 192), "lemon": (0, 216, 245)}
    for t in sc["tables"]:
        s = t["size"] / 2
        cv2.rectangle(img, w2m((t["xy"][0] - s, t["xy"][1] + s)), w2m((t["xy"][0] + s, t["xy"][1] - s)), (43, 90, 139), -1)
        cv2.circle(img, w2m(t["xy"]), 6, col[t["item"]], -1)
        cv2.putText(img, t["item"], (w2m(t["xy"])[0] + 8, w2m(t["xy"])[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
    if len(traj) > 1:
        cv2.polylines(img, [np.array([w2m(p) for p in traj])], False, (200, 80, 0), 2)
    p = pose_true["pos"]
    y = pose_true["yaw"]
    cv2.circle(img, w2m(p[:2]), 7, (40, 40, 40), -1)
    cv2.line(img, w2m(p[:2]), w2m(p[:2] + 0.4 * np.array([math.cos(y), math.sin(y)])), (40, 40, 40), 2)
    if belief.pos is not None:
        cv2.drawMarker(img, w2m(belief.pos[:2]), (0, 0, 255), cv2.MARKER_CROSS, 18, 2)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="C1")
    ap.add_argument("--scenario", default="T5")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--sim", default="pybullet")
    a = ap.parse_args()
    if a.sim == "pybullet":
        from dronenav.sim_pybullet import PyBulletSim
        sim = PyBulletSim()
    else:
        from dronenav.sim_mujoco import MuJoCoSim
        sim = MuJoCoSim()
    sc = make_scenario(a.scenario, a.seed)
    perc = make_perception(a.config)
    out = ROOT / "out" / f"demo_{a.sim}_{a.config}_{a.scenario}_{a.seed}.mp4"
    vw = cv2.VideoWriter(str(out), cv2.VideoWriter_fourcc(*"mp4v"), 5, (640 + MAP, MAP))
    traj = []
    query = "orange"

    def record(sim, pose, belief, mission, g):
        traj.append(g["pos"][:2].copy())
        rgb = cv2.cvtColor(sim.get_rgb(), cv2.COLOR_RGB2BGR)
        cam = cv2.resize(rgb, (640, 480), interpolation=cv2.INTER_NEAREST)
        if not getattr(perc, "is_policy", False):
            for d in perc.detect(sim, pose, query):
                x0, y0, x1, y1 = [int(v * 2) for v in d.bbox]
                if x1 > x0:
                    cv2.rectangle(cam, (x0, y0), (x1, y1), (0, 255, 0), 2)
                    cv2.putText(cam, f"{d.label} {d.conf:.2f} {d.dist:.2f}m", (x0, max(12, y0 - 4)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
        dist = np.linalg.norm(g["target"] - g["pos"]) if g["target"] is not None else float("nan")
        lines = [f"cmd: \"{sc['command']}\"", f"state: {mission.state}   fc: {sim.fc_mode()}",
                 f"t={sim.time():5.1f}s  true dist to orange={dist:.2f} m", f"config {a.config} | {a.sim} | {a.scenario}"]
        cv2.rectangle(cam, (0, 0), (640, 86), (0, 0, 0), -1)
        for i, s in enumerate(lines):
            cv2.putText(cam, s, (8, 18 + 20 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        vw.write(np.hstack([cam, draw_map(sc, traj, g, belief)]))

    res = run_episode(sim, sc, perc, record=record)
    vw.release()
    print({k: res.get(k) for k in ("success", "final_state", "time", "final_dist", "collisions", "wrong_target")})
    print("saved", out)


if __name__ == "__main__":
    main()
