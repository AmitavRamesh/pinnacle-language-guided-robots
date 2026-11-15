"""Scenarios for the extended study (Phase 1b-2): multiple tasks, multi-room house,
and two embodiments (drone, ground robot). Same dict-based format as scenarios.py."""
from __future__ import annotations

import math
import zlib

import numpy as np

HALF = 3.0
WALL_T = 0.12
DOOR_W = 0.95

# 2 x 2 house: four rooms, four doors (room names follow the research-proposal floor plan)
ROOMS = {
    "kitchen": dict(center=(-1.5, 1.5), lo=(-3.0, 0.0), hi=(0.0, 3.0)),
    "office": dict(center=(1.5, 1.5), lo=(0.0, 0.0), hi=(3.0, 3.0)),
    "workshop": dict(center=(-1.5, -1.5), lo=(-3.0, -3.0), hi=(0.0, 0.0)),
    "storage": dict(center=(1.5, -1.5), lo=(0.0, -3.0), hi=(3.0, 0.0)),
}
DOORS = [  # (door centre, axis the wall runs along, rooms connected)
    dict(xy=(0.0, 1.6), wall="x0", rooms=("kitchen", "office")),
    dict(xy=(0.0, -1.4), wall="x0", rooms=("workshop", "storage")),
    dict(xy=(-1.6, 0.0), wall="y0", rooms=("kitchen", "workshop")),
    dict(xy=(1.4, 0.0), wall="y0", rooms=("office", "storage")),
]
MEMORY_ITEMS = ["orange", "apple", "lemon", "orange_cube"]

EMBODIMENT = {
    # cam: height of the camera above the body centre is implicit in the body pose;
    # pitch is the gimbal/mount pitch; standoff is horizontal distance to the target
    "drone": dict(fly_z=1.0, cam_pitch=-15.0, standoff=0.45, body=(0.12, 0.12, 0.04), cam_offset=(0.13, 0, 0)),
    "ground": dict(fly_z=0.15, cam_pitch=-12.0, standoff=0.8, body=(0.30, 0.20, 0.12), cam_offset=(0.15, 0, 0.60)),
}


def room_of(xy):
    for name, r in ROOMS.items():
        if r["lo"][0] <= xy[0] <= r["hi"][0] and r["lo"][1] <= xy[1] <= r["hi"][1]:
            return name
    return None


def _interior_walls():
    """Wall segments along x=0 and y=0 with door gaps."""
    segs = []
    for axis in ("x0", "y0"):
        gaps = sorted([d["xy"][1] if axis == "x0" else d["xy"][0] for d in DOORS if d["wall"] == axis])
        edges = [-HALF]
        for g in gaps:
            edges += [g - DOOR_W / 2, g + DOOR_W / 2]
        edges.append(HALF)
        for a, b in zip(edges[0::2], edges[1::2]):
            if b - a < 0.05:
                continue
            mid, ln = (a + b) / 2, b - a
            if axis == "x0":
                segs.append(dict(type="box", xy=[0.0, mid], ext=[WALL_T / 2, ln / 2], height=2.4))
            else:
                segs.append(dict(type="box", xy=[mid, 0.0], ext=[ln / 2, WALL_T / 2], height=2.4))
    return segs


def _base(task, seed, embodiment):
    return dict(
        task=task, id=task, seed=seed, embodiment=embodiment, room=2 * HALF,
        start=[-2.2, -2.2, 0.05 if embodiment == "drone" else 0.15], start_yaw=math.radians(45),
        tables=[], obstacles=[], walls=[], pads=[],
        light=dict(direction=[2, 2, 5], color=[1, 1, 1], ambient=0.6, diffuse=0.4, specular=0.1),
        noise=dict(depth=0.0, pose=0.0, range=0.0, gust=0.0), link_loss=None,
        command="", target="orange", mission=None, house=False,
        standoff=EMBODIMENT[embodiment]["standoff"], time_budget=120.0,
        cam_pitch=EMBODIMENT[embodiment]["cam_pitch"],
        ring_rays=24,  # Phase-1 sensor ablation: dense ranging removes near-misses -> adopted for Phase 2
    )


def _pt(rng, used, d, lo=(-2.4, -2.4), hi=(2.4, 2.4)):
    for _ in range(800):
        p = rng.uniform(lo, hi)
        if all(np.linalg.norm(p - np.asarray(u)) > d for u in used):
            return p
    raise RuntimeError("placement failed")


def make_world(task: str, seed: int, embodiment: str = "drone") -> dict:
    """Tasks:
    O1  orange visible, open room            O2  orange hidden behind wall      O3  orange + distractors
    L1  one helipad, open room               L2  helipads at different distances (choose nearest)
    L3  nearest helipad + decoy pads (X, plain)                                L4  L3 in dim light
    M1  house, 3-object sequential mission (find A, then B, then C)
    M2  house, two consecutive 3-object missions (memory may persist between them)
    """
    rng = np.random.default_rng(zlib.crc32(f"{task}-{seed}-{embodiment}".encode()))
    sc = _base(task, seed, embodiment)
    start = np.array(sc["start"][:2])
    used = [start]

    def table(xy, item, h=None):
        sc["tables"].append(dict(xy=[float(xy[0]), float(xy[1])], size=0.35,
                                 height=float(h if h is not None else rng.uniform(0.55, 0.75)), item=item))
        used.append(np.asarray(xy))

    if task.startswith("O"):
        a = sc["start_yaw"] + math.radians(rng.uniform(-15, 15))
        tgt = start + rng.uniform(3.0, 3.9) * np.array([math.cos(a), math.sin(a)])
        table(tgt, "orange")
        if task == "O2":
            mid = start + 0.6 * (tgt - start)
            yaw = math.atan2(*(tgt - start)[::-1])
            sc["obstacles"].append(dict(type="wall", xy=mid.tolist(), size=[0.15, 1.4], height=2.4, yaw=yaw))
        if task == "O3":
            for k in rng.choice(["orange_ball", "orange_cube", "apple", "lemon"], 3, replace=False):
                table(_pt(rng, used, 1.1), str(k))
        for _ in range(2):
            p = _pt(rng, used, 1.0)
            if task != "O2":
                sc["obstacles"].append(dict(type="cyl", xy=p.tolist(), size=float(rng.uniform(0.12, 0.2)), height=2.6))
                used.append(p)
        sc["command"] = "find and approach the orange"

    elif task.startswith("L"):
        sc["target"] = "helipad"
        sc["cam_pitch"] = -35.0  # gimbal tilted down for ground markers
        sc["command"] = "find the nearest helipad and land on it"
        sc["standoff"] = 0.0
        n_h = 1 if task == "L1" else int(rng.integers(2, 4))
        dists = sorted(rng.uniform(1.6, 4.2, n_h))
        for d in dists:
            for _ in range(200):
                a = rng.uniform(0, math.pi / 2)  # pads in the quadrant in front of the start corner
                p = start + d * np.array([math.cos(a), math.sin(a)])
                if np.all(np.abs(p) < 2.4) and all(np.linalg.norm(p - u) > 1.0 for u in used):
                    break
            sc["pads"].append(dict(xy=p.tolist(), kind="H", yaw=float(rng.uniform(0, math.pi))))
            used.append(p)
        if task in ("L3", "L4"):
            for kind in ["X", "plain"]:
                d = rng.uniform(1.0, max(1.2, dists[0] - 0.3))  # decoys tend to be NEARER than the real helipad
                for _ in range(300):
                    a = rng.uniform(0, math.pi / 2)
                    p = start + d * np.array([math.cos(a), math.sin(a)])
                    if np.all(np.abs(p) < 2.5) and all(np.linalg.norm(p - u) > 0.9 for u in used):
                        break
                    d = rng.uniform(1.0, 4.0)
                sc["pads"].append(dict(xy=p.tolist(), kind=kind, yaw=float(rng.uniform(0, math.pi))))
                used.append(p)
        if task == "L4":
            sc["light"] = dict(direction=[1, -2, 3], color=[0.6, 0.6, 0.65], ambient=0.3, diffuse=0.3, specular=0.05)
        sc["obstacles"].append(dict(type="cyl", xy=_pt(rng, used, 1.0).tolist(), size=0.15, height=2.6))
        sc["time_budget"] = 90.0

    elif task.startswith("M"):
        sc["house"] = True
        sc["walls"] = _interior_walls()
        door_pts = [np.array(d["xy"]) for d in DOORS]
        rooms = list(ROOMS)
        rng.shuffle(rooms)
        # one item per room (+ a distractor table in one room); start room is kept separate from the items
        start_room = room_of(start)
        item_rooms = [r for r in rooms if r != start_room] + [start_room]
        for item, rname in zip(MEMORY_ITEMS, item_rooms):
            R = ROOMS[rname]
            p = _pt(rng, used + door_pts, 0.95, lo=np.array(R["lo"]) + 0.6, hi=np.array(R["hi"]) - 0.6)
            table(p, item)
        seq = [str(x) for x in rng.permutation(["orange", "apple", "lemon"])]
        seq2 = [str(x) for x in rng.permutation(["orange", "apple", "lemon"])]
        sc["mission"] = [seq] if task == "M1" else [seq, seq2]
        sc["command"] = " ; ".join("find the " + ", then the ".join(s) for s in sc["mission"])
        sc["time_budget"] = 900.0
    else:
        raise ValueError(task)
    return sc


WORLD_TASKS = {
    "O1": "Orange visible, open room", "O2": "Orange hidden behind a wall", "O3": "Orange among distractors",
    "L1": "One helipad", "L2": "Several helipads, land on the nearest", "L3": "Nearest helipad with decoy pads",
    "L4": "L3 in dim light", "M1": "House: 3-object sequential mission", "M2": "House: two consecutive missions",
}
