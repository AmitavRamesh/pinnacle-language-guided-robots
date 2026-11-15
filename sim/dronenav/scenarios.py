"""Scenario generator. A scenario is a plain dict, so every simulator can build
the same room from it (matched layouts across simulators)."""
from __future__ import annotations

import math
import zlib

import numpy as np

ROOM = 6.0  # metres, square room centred on origin
HALF = ROOM / 2
START = np.array([-2.2, -2.2])
FLY_Z = 1.0

# object kinds: radius (m), colour (rgba), texture name, is_target
OBJECTS = {
    "orange": dict(shape="sphere", size=0.045, rgba=[1, 1, 1, 1], texture="orange_peel"),
    "orange_ball": dict(shape="sphere", size=0.09, rgba=[1.0, 0.45, 0.05, 1], texture=None),
    "orange_cube": dict(shape="box", size=0.06, rgba=[1.0, 0.5, 0.1, 1], texture=None),
    "apple": dict(shape="sphere", size=0.045, rgba=[1, 1, 1, 1], texture="apple"),
    "lemon": dict(shape="sphere", size=0.04, rgba=[1, 1, 1, 1], texture="lemon"),
}
DISTRACTORS = ["orange_ball", "orange_cube", "apple", "lemon"]

SCENARIOS = {
    "T1": "Target visible, open room",
    "T2": "Target behind drone",
    "T3": "Target hidden behind obstacle",
    "T4": "Cluttered path (6-8 pillars)",
    "T5": "Distractors present",
    "T6": "Target absent",
    "T7": "Lighting change",
    "T8": "Depth + pose noise",
    "T9": "Link loss mid-approach",
    "T10": "Command variants",
    "T4D": "T4 with dense 24-beam range ring (sensor ablation)",
}

COMMANDS = [
    "find and approach the orange",
    "go to the orange",
    "fly near the orange and stop half a metre away",
    "locate the orange fruit",
    "can you find the orange for me",
    "approach the orange, stay 50 cm away",
]


def _clear(p, others, d):
    return all(np.linalg.norm(np.asarray(p) - np.asarray(o)) > d for o in others)


def _rand_point(rng, others, d, margin=0.6):
    for _ in range(500):
        p = rng.uniform(-HALF + margin, HALF - margin, size=2)
        if _clear(p, others, d):
            return p
    raise RuntimeError("could not place object")


def make_scenario(sid: str, seed: int) -> dict:
    if sid == "T4D":  # identical layout to T4, denser obstacle sensing
        sc = make_scenario("T4", seed)
        sc.update(id="T4D", ring_rays=24)
        return sc
    rng = np.random.default_rng(zlib.crc32(f"{sid}-{seed}".encode()))
    sc = dict(
        id=sid,
        seed=seed,
        room=ROOM,
        start=START.tolist() + [0.05],
        start_yaw=math.radians(45),  # facing room centre
        tables=[],  # each: dict(xy, size, height, item)
        obstacles=[],  # each: dict(type box|cyl, xy, size, height)
        light=dict(direction=[2, 2, 5], color=[1, 1, 1], ambient=0.6, diffuse=0.4, specular=0.1),
        noise=dict(depth=0.0, pose=0.0, range=0.0, gust=0.0),
        link_loss=None,
        command=COMMANDS[0],
        target_present=True,
        standoff=0.5,
        time_budget=120.0,
    )
    used = [START]
    start_yaw = sc["start_yaw"]

    def add_table(xy, item):
        sc["tables"].append(dict(xy=list(map(float, xy)), size=0.35, height=float(rng.uniform(0.55, 0.8)), item=item))
        used.append(np.asarray(xy))

    def target_in_view(dist_lo=2.8, dist_hi=4.0, half_angle=20):
        a = start_yaw + math.radians(rng.uniform(-half_angle, half_angle))
        d = rng.uniform(dist_lo, dist_hi)
        return START + d * np.array([math.cos(a), math.sin(a)])

    def add_pillars(n, avoid_line=None):
        for _ in range(n):
            for _ in range(200):
                p = _rand_point(rng, used, 0.9)
                if avoid_line is not None:
                    a, b = avoid_line
                    t = np.clip(np.dot(p - a, b - a) / np.dot(b - a, b - a), 0, 1)
                    if np.linalg.norm(p - (a + t * (b - a))) < avoid_line_clear:
                        continue
                break
            r = float(rng.uniform(0.12, 0.25))
            sc["obstacles"].append(dict(type="cyl", xy=p.tolist(), size=r, height=2.6))
            used.append(p)

    avoid_line_clear = 0.6

    if sid in ("T1", "T7", "T8", "T9", "T10"):
        tgt = target_in_view()
        add_table(tgt, "orange")
        add_pillars(2, avoid_line=(START, tgt))
    elif sid == "T2":
        # start mid-room facing +x; target is behind (bearing 140-220 deg)
        st = np.array([0.8, float(rng.uniform(-0.5, 0.5))])
        sc["start"] = st.tolist() + [0.05]
        sc["start_yaw"] = 0.0
        used[0] = st
        a = math.radians(rng.uniform(140, 220))
        tgt = np.clip(st + rng.uniform(2.2, 3.0) * np.array([math.cos(a), math.sin(a)]), -HALF + 0.6, HALF - 0.6)
        add_table(tgt, "orange")
        add_pillars(2, avoid_line=(st, tgt))
    elif sid == "T3":
        tgt = target_in_view(3.2, 4.2, 10)
        add_table(tgt, "orange")
        mid = START + 0.6 * (tgt - START)
        yaw = math.atan2(*(tgt - START)[::-1])
        sc["obstacles"].append(dict(type="wall", xy=mid.tolist(), size=[0.15, 1.4], height=2.4, yaw=yaw))
        used.append(mid)
    elif sid == "T4":
        tgt = target_in_view(3.2, 4.2, 15)
        add_table(tgt, "orange")
        # 2-3 pillars ON the direct path (forces avoidance), the rest random
        d = tgt - START
        nrm = np.array([-d[1], d[0]]) / np.linalg.norm(d)
        for f in np.sort(rng.uniform(0.3, 0.75, size=int(rng.integers(2, 4)))):
            p = START + f * d + nrm * rng.uniform(-0.25, 0.25)
            if _clear(p, [o["xy"] for o in sc["obstacles"]], 0.7):
                sc["obstacles"].append(dict(type="cyl", xy=p.tolist(), size=float(rng.uniform(0.15, 0.25)), height=2.6))
                used.append(p)
        avoid_line_clear = 0.0
        add_pillars(int(rng.integers(4, 6)))
    elif sid == "T5":
        tgt = target_in_view()
        add_table(tgt, "orange")
        for kind in rng.choice(DISTRACTORS, size=int(rng.integers(2, 4)), replace=False):
            add_table(_rand_point(rng, used, 1.0), str(kind))
        add_pillars(1, avoid_line=(START, tgt))
    elif sid == "T6":
        sc["target_present"] = False
        for kind in rng.choice(DISTRACTORS, size=2, replace=False):
            add_table(_rand_point(rng, used, 1.0), str(kind))
        add_pillars(2)
    else:
        raise ValueError(sid)

    if sid == "T7":
        mode = ["dim", "bright", "warm"][seed % 3]
        sc["light"] = {
            "dim": dict(direction=[1, -2, 3], color=[0.6, 0.6, 0.65], ambient=0.25, diffuse=0.3, specular=0.05),
            "bright": dict(direction=[0, 0, 5], color=[1, 1, 1], ambient=0.9, diffuse=0.6, specular=0.4),
            "warm": dict(direction=[-2, 1, 4], color=[1.0, 0.75, 0.5], ambient=0.5, diffuse=0.5, specular=0.1),
        }[mode]
        sc["light_mode"] = mode
        add_table(_rand_point(rng, used, 1.0), str(rng.choice(["apple", "orange_ball"])))
    if sid == "T8":
        sc["noise"] = dict(depth=0.05, pose=0.05, range=0.03, gust=0.4)
    if sid == "T9":
        sc["link_loss"] = dict(trigger_dist=1.8, duration=1e9)  # permanent loss once within 1.8 m
    if sid == "T10":
        sc["command"] = COMMANDS[seed % len(COMMANDS)]
    return sc
