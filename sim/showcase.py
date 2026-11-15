"""Generates the screenshot figures for the report: robots in the world, multi-sensor
panels, and step-by-step result sequences for each task. Output: ../report/figs/shot_*.png"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import dronenav  # noqa: E402,F401
import cv2  # noqa: E402
import numpy as np  # noqa: E402

from dronenav.arm import ArmSim, make_arm_task, run_arm_episode  # noqa: E402
from dronenav.sim_world import WorldSim  # noqa: E402
from dronenav.world_agent import PadRing, WorldOracle, run_world_episode  # noqa: E402
from dronenav.world_scenarios import DOORS, ROOMS, make_world  # noqa: E402

FIG = ROOT.parent / "report" / "figs"
FIG.mkdir(parents=True, exist_ok=True)
FONT = cv2.FONT_HERSHEY_SIMPLEX
COL = {"orange": (255, 140, 0), "apple": (200, 0, 0), "lemon": (235, 215, 0), "orange_cube": (255, 160, 60),
       "orange_ball": (255, 100, 0), "helipad": (0, 200, 0), "pad_X": (220, 0, 0), "pad_plain": (150, 150, 150),
       "pad_decoy": (220, 0, 0), "pad?": (255, 200, 0)}


def label(img, text, pos=(8, 22), scale=0.6, bg=(0, 0, 0), fg=(255, 255, 255)):
    (w, h), _ = cv2.getTextSize(text, FONT, scale, 1)
    cv2.rectangle(img, (pos[0] - 4, pos[1] - h - 6), (pos[0] + w + 4, pos[1] + 6), bg, -1)
    cv2.putText(img, text, pos, FONT, scale, fg, 1, cv2.LINE_AA)
    return img


def save(name, rgb):
    cv2.imwrite(str(FIG / name), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    print("saved", name)


def grid(tiles, cols):
    h, w = tiles[0].shape[:2]
    tiles = [cv2.resize(t, (w, h)) for t in tiles]
    while len(tiles) % cols:
        tiles.append(np.full_like(tiles[0], 255))
    return np.vstack([np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)])


def topdown(sim, sc, traj=None, mem=None, size=420, title=None, rays=None):
    img = np.full((size, size, 3), 250, np.uint8)
    s = size / 6.6
    w2 = lambda xy: (int(size / 2 + xy[0] * s), int(size / 2 - xy[1] * s))  # noqa: E731
    cv2.rectangle(img, w2((-3, 3)), w2((3, -3)), (0, 0, 0), 2)
    if sc.get("house"):
        for nm, R in ROOMS.items():
            cv2.putText(img, nm, (w2((R["lo"][0] + 0.15, R["hi"][1] - 0.35))), FONT, 0.42, (120, 120, 120), 1, cv2.LINE_AA)
        for wl in sc["walls"]:
            x, y = wl["xy"]
            ex, ey = wl["ext"]
            cv2.rectangle(img, w2((x - ex, y + ey)), w2((x + ex, y - ey)), (110, 120, 140), -1)
        for d in DOORS:
            cv2.circle(img, w2(d["xy"]), 4, (0, 150, 0), -1)
    for o in sc["obstacles"]:
        if o["type"] == "cyl":
            cv2.circle(img, w2(o["xy"]), int(o["size"] * s), (150, 140, 125), -1)
        else:
            yaw = o.get("yaw", 0) + math.pi / 2
            c_, s_ = math.cos(yaw), math.sin(yaw)
            W, L = o["size"]
            pts = np.array([[-W / 2, -L / 2], [W / 2, -L / 2], [W / 2, L / 2], [-W / 2, L / 2]]) @ np.array([[c_, s_], [-s_, c_]])
            cv2.fillPoly(img, [np.array([w2(q + o["xy"]) for q in pts])], (168, 159, 136))
    for t in sc["tables"]:
        h = t["size"] / 2
        cv2.rectangle(img, w2((t["xy"][0] - h, t["xy"][1] + h)), w2((t["xy"][0] + h, t["xy"][1] - h)), (139, 90, 43), -1)
        cv2.circle(img, w2(t["xy"]), 5, COL.get(t["item"], (0, 0, 0)), -1)
    for pd in sc.get("pads", []):
        cv2.circle(img, w2(pd["xy"]), int(0.32 * s), (240, 200, 40), 2)
        cv2.putText(img, pd["kind"][0].upper(), (w2(pd["xy"])[0] - 5, w2(pd["xy"])[1] + 5), FONT, 0.45, (0, 0, 0), 1)
    if traj is not None and len(traj) > 1:
        cv2.polylines(img, [np.array([w2(q) for q in traj])], False, (0, 90, 220), 2)
    if mem is not None:
        for lab, lst in mem.entries.items():
            for e in lst:
                cv2.drawMarker(img, w2(e["pos"][:2]), COL.get(lab, (255, 0, 255)), cv2.MARKER_TILTED_CROSS, 14, 2)
    g = sim.gt()
    cv2.circle(img, w2(g["pos"][:2]), 7, (30, 30, 30), -1)
    cv2.line(img, w2(g["pos"][:2]), w2(g["pos"][:2] + 0.45 * np.array([math.cos(g["yaw"]), math.sin(g["yaw"])])), (30, 30, 30), 2)
    if rays is not None:
        for d, r in rays:
            p0 = g["pos"][:2]
            cv2.line(img, w2(p0), w2(p0 + d * min(r, 4.0)), (220, 60, 60) if r < 0.6 else (90, 180, 90), 1)
    if title:
        label(img, title, (8, size - 12), 0.5)
    return img


def depth_vis(d):
    d = np.clip(d, 0, 6) / 6
    return cv2.cvtColor(cv2.applyColorMap((255 - d * 255).astype(np.uint8), cv2.COLORMAP_TURBO), cv2.COLOR_BGR2RGB)


def seg_vis(seg):
    rng = np.random.default_rng(3)
    lut = rng.integers(40, 255, (512, 3)).astype(np.uint8)
    return lut[np.clip(seg, 0, 511)]


def fpv_with_dets(sim, dets, scale=2):
    img = cv2.resize(sim.get_rgb(), None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
    for d in dets:
        if d.bbox[2] > d.bbox[0]:
            x0, y0, x1, y1 = [int(v * scale) for v in d.bbox]
            c = COL.get(d.label, (0, 255, 0))
            cv2.rectangle(img, (x0, y0), (x1, y1), c, 2)
            cv2.putText(img, f"{d.label} {d.dist:.2f}m", (x0, max(14, y0 - 4)), FONT, 0.45, c, 1, cv2.LINE_AA)
    return img


def fly_to_alt(sim, z=1.0):
    while sim.get_pose().pos[2] < z - 0.05:
        sim.send_velocity(0, 0, 0.3, 0)
        sim.step()


# =================================================================== 1. robots in the world
def robots_in_world():
    s = WorldSim()
    tiles = []
    sc = make_world("O3", 0, "drone")
    s.reset(sc, 0)
    fly_to_alt(s, 1.0)
    pos = s.get_pose().pos
    tiles.append(label(s.scene_image(pos + np.array([0.42, -0.3, 0.22]), pos, 960, 540, fov=40), "Quadrotor model (3.5-inch ducted), physics body + camera"))
    tiles.append(label(s.scene_image((2.6, -2.6, 2.4), (-0.8, 0.2, 0.4), 960, 540, fov=60), "Drone imported into the test room (T5-style scene)"))
    sc = make_world("M1", 1, "ground")
    s.reset(sc, 1)
    for _ in range(30):
        s.send_velocity(0.3, 0.3, 0, 0)
        s.step()
    pos = s.get_pose().pos
    tiles.append(label(s.scene_image(pos + np.array([0.9, -0.7, 0.6]), pos, 960, 540, fov=45), "Ground robot (Husky) with mast camera"))
    tiles.append(label(s.scene_image((0, -2.2, 8.5), (0, 0.3, 0), 960, 540, fov=50), "Multi-room house: kitchen, office, workshop, storage"))
    sc = make_world("L3", 2, "drone")
    s.reset(sc, 2)
    fly_to_alt(s, 1.6)
    tiles.append(label(s.scene_image((1.5, -3.4, 4.2), (-0.5, 0.2, 0), 960, 540, fov=60), "Helipad scene: H pads and decoys (X, plain)"))
    a = ArmSim()
    a.reset(make_arm_task("A2", 0))
    tiles.append(label(a.scene_image((1.35, -0.85, 1.25), (0.45, 0, 0.72)), "Franka Panda arm with distractors on the table"))
    save("shot_robots_world.png", grid(tiles, 2))
    s.close()


# =================================================================== 2. sensor panels
def sensor_panel(emb):
    from dronenav.planner import depth_obstacles, obstacle_rays
    s = WorldSim()
    sc = make_world("O3", 3, emb)
    s.reset(sc, 3)
    if emb == "drone":
        fly_to_alt(s, 1.0)
    for _ in range(25):
        s.send_velocity(0, 0, 0, 0.7)
        s.step()
    pose = s.get_pose()
    dets = WorldOracle().detect(s, pose)
    rays = obstacle_rays(s.get_ranges(), depth_obstacles(s.get_depth(), pose, s.camera(), z_abs=None if emb == "drone" else (0.05, 0.55)), pose.yaw)
    t = [label(fpv_with_dets(s, dets, 2), "RGB camera + detections"),
         label(cv2.resize(depth_vis(s.get_depth()), (640, 480), interpolation=cv2.INTER_NEAREST), "Depth image (near = red, far = blue)"),
         label(cv2.resize(seg_vis(s.get_seg()), (640, 480), interpolation=cv2.INTER_NEAREST), "Segmentation (ground truth, evaluation only)"),
         label(cv2.resize(topdown(s, sc, rays=rays), (480, 480)), "24-beam ToF ring + depth sectors (red < 0.6 m)")]
    t[3] = cv2.copyMakeBorder(t[3], 0, 0, 80, 80, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    save(f"shot_sensors_{emb}.png", grid(t, 4))
    s.close()


# =================================================================== 3. result sequences
def orange_sequence(emb="drone", seed=0, task="O3"):
    s = WorldSim()
    sc = make_world(task, seed, emb)
    frames, traj = [], []
    P = WorldOracle()
    want = {"SPIN": 1, "GOTO": 1, "APPROACH": 2, "DONE": 1}
    got = {}

    def rec(sim, pose, ms, mem, g):
        traj.append(g["pos"][:2].copy())
        st = ms.state
        if st in want and got.get(st, 0) < want[st] and (st != "APPROACH" or got.get(st, 0) == 0 or len(traj) % 40 == 0):
            got[st] = got.get(st, 0) + 1
            dets = P.detect(sim, sim.get_pose())
            dist = np.linalg.norm(g["target"][:2] - g["pos"][:2]) if g["target"] is not None else float("nan")
            frames.append((label(fpv_with_dets(sim, dets, 2), f"{emb} camera | state {st} | t={sim.time():.1f}s | {dist:.2f} m to orange"),
                           label(sim.chase_image(w=640, h=480), "observer camera")))

    r = run_world_episode(s, sc, P, record=rec)
    sub = r["subtasks"][0]
    tiles = []
    for a, b in frames[:4]:
        tiles += [cv2.resize(a, (640, 480)), b]
    td = label(cv2.resize(topdown(s, sc, traj, title=f"RESULT: success={r['success']} final distance {sub.get('final_dh')} m, {r['time']} s"), (480, 480)), "trajectory")
    td = cv2.copyMakeBorder(td, 0, 0, 80, 80, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    save(f"shot_result_orange_{emb}.png", grid(tiles + [td, label(s.chase_image(w=640, h=480), "final pose: target found, holding stand-off")], 2))
    s.close()
    return r


def landing_sequence(seed=0):
    from dronenav.world_agent import PadHybrid
    s = WorldSim()
    sc = make_world("L3", seed, "drone")
    P = PadHybrid()
    frames, traj = [], []
    want = {"SPIN": 2, "GOTO": 1, "ALIGN": 1, "DESCEND": 1}
    got = {}

    def rec(sim, pose, ms, mem, g):
        traj.append(g["pos"][:2].copy())
        st = ms.state
        if st in want and got.get(st, 0) < want[st] and (len(traj) % 25 == 0 or st in ("ALIGN", "DESCEND")):
            got[st] = got.get(st, 0) + 1
            dets = PadRing().detect(sim, sim.get_pose())
            for d in dets:  # show the verifier's verdicts from memory
                near = [(lab, e) for lab, lst in mem.entries.items() for e in lst if np.linalg.norm(e["pos"][:2] - d.pos[:2]) < 0.4]
                d.label = near[0][0] if near else "pad?"
            frames.append((label(fpv_with_dets(sim, dets, 2), f"gimbal {sim.cam_pitch:.0f} deg | {st} | alt {g['pos'][2]:.2f} m"),
                           label(sim.chase_image(w=640, h=480, dist=1.8, height=1.2), f"observer | t={sim.time():.1f}s")))

    r = run_world_episode(s, sc, P, record=rec)
    tiles = []
    for a, b in frames[:5]:
        tiles += [cv2.resize(a, (640, 480)), b]
    pos = s.get_pose().pos
    tiles.append(cv2.resize(label(topdown(s, sc, traj, title=f"RESULT: landed on {r.get('landed_on')}, error {r.get('land_err')} m, nearest={r.get('chose_nearest')}"), "trajectory"), (640, 480)))
    tiles.append(label(s.scene_image(pos + np.array([0.8, -0.8, 0.7]), pos, 640, 480, fov=50), "landed on the helipad"))
    save("shot_result_landing.png", grid(tiles, 2))
    s.close()
    return r


def memory_sequence(emb="drone", seed=1):
    out = []
    s = WorldSim()
    for mem_mode in ["none", "persistent"]:
        sc = make_world("M2", seed, emb)
        traj = []
        snaps = {}

        def rec(sim, pose, ms, mem, g):
            traj.append(g["pos"][:2].copy())
            snaps["last"] = mem

        r = run_world_episode(s, sc, WorldOracle(), use_memory=mem_mode != "none", persist=mem_mode == "persistent", record=rec)
        subs = " | ".join(f"{x['label']}:{x['duration']:.0f}s{'*' if x['from_memory'] else ''}" for x in r["subtasks"])
        img = topdown(s, sc, traj, mem=snaps.get("last"), size=560)
        label(img, f"{emb}, memory={mem_mode}: total {r['time']:.0f} s, path {r['path_len']:.1f} m", (8, 22), 0.55)
        label(img, subs, (8, 46), 0.42)
        out.append(img)
    s.close()
    save(f"shot_result_memory_{emb}.png", grid(out, 2))


def arm_sequence(seed=0):
    a = ArmSim()
    sc = make_arm_task("A2", seed)
    frames = []

    def rec(sim):
        if len(frames) < 12:
            frames.append(sim.scene_image((1.25, -0.75, 1.15), (0.5, 0, 0.7), 640, 480))

    r = run_arm_episode(a, sc, WorldOracle(), record=rec)
    pick = [frames[i] for i in [0, 4, 9, len(frames) - 1] if i < len(frames)]
    tiles = [label(cv2.resize(a.get_rgb(), (640, 480)), "fixed camera view")] + \
            [label(f, n) for f, n in zip(pick, ["move above target", "descend", "grasp", "lift"])]
    tiles.append(label(a.scene_image((1.25, -0.75, 1.15), (0.5, 0, 0.7), 640, 480), f"RESULT: picked {r.get('picked')}, success={r['success']}"))
    save("shot_result_arm.png", grid(tiles, 3))


if __name__ == "__main__":
    what = sys.argv[1:] or ["robots", "sensors", "orange", "landing", "memory", "arm"]
    if "robots" in what:
        robots_in_world()
    if "sensors" in what:
        sensor_panel("drone")
        sensor_panel("ground")
    if "orange" in what:
        orange_sequence("drone")
        orange_sequence("ground")
    if "landing" in what:
        landing_sequence()
    if "memory" in what:
        memory_sequence("drone")
        memory_sequence("ground")
    if "arm" in what:
        arm_sequence()
