"""Phase 1b-2 agent: semantic memory + multi-step missions + embodiment-aware planning.

Layers (matching the research proposal, scaled to what can be tested here):
  Perception      -> Detection(label, pos, conf)           (oracle / colour / detector+VLM / pad detectors)
  SemanticMemory  -> persistent object map + explored rooms (layer 2-3 of the proposed world model)
  Topology        -> rooms + doors graph (layer 1; the floor plan is given, object locations are not)
  WorldMission    -> sequence of subtasks: ("approach", label) | ("land", "helipad")
  Planner         -> explore / go-to / approach / align+land, local avoidance
  SafetyFilter    -> unchanged from Phase 1 (independent, learning-free)
  Embodiment      -> WorldSim drone dynamics or ground-robot unicycle adapter
"""
from __future__ import annotations

import math
from collections import deque

import cv2
import numpy as np

from .perception import Detection, HSVPerception, Timer, blob_depth, pixel_to_world
from .planner import SafetyFilter, depth_obstacles, obstacle_rays, wrap
from .world_scenarios import DOORS, EMBODIMENT, ROOMS, room_of

V_MAX = 0.5


# ============================================================== perception
class WorldOracle:
    """Perfect detection of every labelled thing with >= 6 visible pixels."""
    name = "oracle"

    def detect(self, sim, pose, query=None):
        g = sim.gt()
        out = []
        for label, bid, pos in g["objects"]:
            if sim.visible_pixels(bid) >= 6:
                ys, xs = np.nonzero(sim._seg == bid)  # bounding box from the segmentation image (display only)
                bbox = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
                out.append(Detection(label, 1.0, pose.pos + (pos - g["pos"]), bbox, float(np.linalg.norm(pos - g["pos"]))))
        return out


class OrangeHSV(HSVPerception):
    name = "hsv"

    def detect(self, sim, pose, query=None):
        return [Detection("orange", d.conf, d.pos, d.bbox, d.dist) for d in super().detect(sim, pose, "orange")]


class PadRing:
    """Classical landing-pad detector: yellow ring blobs -> pad centres. Cannot read the marking."""
    name = "pad_ring"
    LO, HI = np.array([18, 110, 120]), np.array([38, 255, 255])

    def proposals(self, sim, pose):
        rgb, depth, cam = sim.get_rgb(), sim.get_depth(), sim.camera()
        mask = cv2.inRange(cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV), self.LO, self.HI)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
        n, lab, st, _ = cv2.connectedComponentsWithStats(mask)
        out = []
        for i in range(1, n):
            x, y, w, h, a = st[i]
            if a < 15 or w < 5 or h < 3:
                continue
            u, v = x + w / 2, y + h / 2
            m = np.zeros_like(depth, bool)
            m[int(y + h * .35):int(y + h * .65) + 1, int(x + w * .35):int(x + w * .65) + 1] = True
            z = blob_depth(depth, m)
            if z is None or z > 9:
                continue
            pw = pixel_to_world(u, v, z, pose, cam)
            out.append(Detection("helipad", min(1.0, a / 300), pw, (x, y, x + w, y + h), z))
        return out

    def detect(self, sim, pose, query=None):
        return self.proposals(sim, pose)


class PadHybrid(PadRing):
    """Ring proposals + VLM check of the marking ('H' vs decoys).
    Iteration 2: oblique views gave wrong verdicts, so pads are only verified from a
    top-down view (gimbal <= -80 deg, directly above the pad); verdicts are majority-voted."""
    Q = "This is a landing pad seen from above. Is there a large letter H painted in the middle? Answer yes or no."
    name = "pad_vlm"

    def __init__(self):
        from .models import crop, get_vlm
        self.vlm, self.crop = get_vlm(), crop
        self.votes, self.vlm_calls, self.last = {}, 0, {}

    def reset(self):
        self.votes, self.vlm_calls, self.last = {}, 0, {}

    def detect(self, sim, pose, query=None):
        rgb = sim.get_rgb()
        out = []
        for d in self.proposals(sim, pose):
            k = tuple(np.round(d.pos[:2] / 0.4).astype(int))
            w = max(d.bbox[2] - d.bbox[0], d.bbox[3] - d.bbox[1])
            top_down = sim.cam_pitch <= -80
            x0, y0, x1, y1 = d.bbox
            H, W = rgb.shape[:2]
            whole = x0 > 2 and y0 > 2 and x1 < W - 2 and y1 < H - 2 and 0.75 < (x1 - x0) / max(1, y1 - y0) < 1.33
            if top_down and whole and w >= 40 and sim.time() - self.last.get(k, -9) > 0.6 and len(self.votes.get(k, [])) < 3:
                c = self.crop(rgb, d.bbox, pad=0.1)
                # iteration 3: rotation-invariant check (a rotated 'H' was read as 'I')
                yes = any(self.vlm.ask(img, self.Q, 3).lower().startswith("yes") for img in (c, np.rot90(c).copy()))
                self.vlm_calls += 2
                self.votes.setdefault(k, []).append(yes)
                self.last[k] = sim.time()
            v = self.votes.get(k, [])
            if not v:
                d.label, d.conf = "pad?", 0.3
            else:
                d.label = "helipad" if sum(v) * 2 >= len(v) else "pad_decoy"
            out.append(d)
        return out


class ObjectHybrid:
    """C5 from Phase 1 generalised to any object label: YOLO-World proposals for every known
    label + VLM verification of the current target class."""
    name = "hybrid"
    LABELS = {"orange": "orange fruit", "apple": "red apple", "lemon": "lemon", "orange_cube": "orange box"}

    def __init__(self):
        from .models import crop, get_vlm, get_yolo
        self.det, self.vlm, self.crop = get_yolo(), get_vlm(), crop
        self.cache, self.vlm_calls = {}, 0
        self.det.model.set_classes(list(self.LABELS.values()))
        self.det._classes = "__multi__"
        self.names = list(self.LABELS)

    def reset(self):
        self.cache, self.vlm_calls = {}, 0

    def detect(self, sim, pose, query=None):
        from .perception import boxes_to_detections
        rgb = sim.get_rgb()
        if self.det._classes != "__multi__":
            self.det.model.set_classes(list(self.LABELS.values()))
            self.det._classes = "__multi__"
        r = self.det.model.predict(rgb[..., ::-1], conf=0.01, imgsz=640, verbose=False)[0]
        labels = [self.names[int(c)] for c in r.boxes.cls.cpu().numpy()]
        dets = boxes_to_detections(r.boxes.xyxy.cpu().numpy(), r.boxes.conf.cpu().numpy(), labels, sim, pose, "x")
        out = []
        for d in dets:
            if d.label != query:
                out.append(d)  # remembered as an unverified hint
                continue
            k = (d.label, *np.round(d.pos[:2] / 0.3).astype(int))
            w = max(d.bbox[2] - d.bbox[0], d.bbox[3] - d.bbox[1])
            prev = self.cache.get(k)
            if w >= 12 and (prev is None or w >= 1.5 * prev[1]):
                ans = self.vlm.ask(self.crop(rgb, d.bbox), f"Is this a {self.LABELS[query].replace('red ', '')}? Answer yes or no.", 3).lower()
                self.vlm_calls += 1
                prev = self.cache[k] = (ans.startswith("yes"), w)
            if prev is None or prev[0]:
                d.conf = 0.3 if prev is None else 0.8
                out.append(d)
        return out


# ================================================================ memory
class SemanticMemory:
    """Persistent object map: label -> list of entries {pos, hits, last, conf}; plus explored rooms."""

    def __init__(self, gate=0.5):
        self.entries, self.explored, self.gate = {}, set(), gate

    def update(self, dets, t):
        for d in dets:
            lst = self.entries.setdefault(d.label, [])
            near = [e for e in lst if np.linalg.norm(e["pos"][:2] - d.pos[:2]) < self.gate]
            if near:
                e = near[0]
                e["pos"] = 0.7 * e["pos"] + 0.3 * d.pos
                e["hits"] += 1
                e["last"], e["conf"] = t, max(e["conf"], d.conf)
            else:
                lst.append(dict(pos=d.pos.copy(), hits=1, last=t, conf=d.conf))

    def best(self, label, near_xy=None, min_hits=2):
        lst = [e for e in self.entries.get(label, []) if e["hits"] >= min_hits]
        if not lst:
            return None
        if near_xy is None:
            return max(lst, key=lambda e: (e["hits"], e["last"]))
        return min(lst, key=lambda e: np.linalg.norm(e["pos"][:2] - near_xy))

    def forget(self, label, entry):
        self.entries[label] = [e for e in self.entries.get(label, []) if e is not entry]

    def clear(self):
        self.entries, self.explored = {}, set()

    def n_objects(self):
        return sum(len(v) for v in self.entries.values())


# ============================================================== topology
def route(a_xy, b_xy, house):
    """Waypoints from a to b. In the house: through door centres (with approach points on each side)."""
    if not house:
        return [np.asarray(b_xy, float)]
    ra, rb = room_of(a_xy), room_of(b_xy)
    if ra is None or rb is None or ra == rb:
        return [np.asarray(b_xy, float)]
    adj = {}
    for d in DOORS:
        r1, r2 = d["rooms"]
        adj.setdefault(r1, []).append((r2, d))
        adj.setdefault(r2, []).append((r1, d))
    prev, q = {ra: None}, deque([ra])
    while q:
        r = q.popleft()
        for nb, d in adj.get(r, []):
            if nb not in prev:
                prev[nb] = (r, d)
                q.append(nb)
    path, r = [], rb
    while prev[r] is not None:
        pr, d = prev[r]
        path.append((pr, r, d))
        r = pr
    wps = []
    for frm, to, d in reversed(path):
        c = np.array(d["xy"], float)
        n = np.array([1.0, 0]) if d["wall"] == "x0" else np.array([0, 1.0])
        cf = np.array(ROOMS[frm]["center"])
        side = 1 if np.dot(cf - c, n) > 0 else -1
        wps += [c + side * 0.6 * n, c - side * 0.6 * n]
    return wps + [np.asarray(b_xy, float)]


# =============================================================== mission
class WorldMission:
    def __init__(self, sc, memory, use_memory=True, persist=True):
        self.sc, self.emb = sc, sc["embodiment"]
        self.E = EMBODIMENT[self.emb]
        self.house = sc.get("house", False)
        self.mem, self.use_memory, self.persist = memory, use_memory, persist
        if sc["task"].startswith("L"):
            self.missions = [[("land", "helipad")]]
        elif sc.get("mission"):
            self.missions = [[("approach", x) for x in m] for m in sc["mission"]]
        else:
            self.missions = [[("approach", sc.get("target", "orange"))]]
        self.queue = [(mi, st) for mi, m in enumerate(self.missions) for st in m]
        self.k = -1
        self.state = "TAKEOFF" if self.emb == "drone" else "IDLE"
        self.log, self.sub_log = [], []
        self.t_state = 0.0
        self.spin_acc, self.prev_yaw = 0.0, None
        self.wps, self.view_points = [], []
        self.goal_entry = None
        self.hold_t = None
        self.landing = False
        self.prog = (None, None)
        self.detour_until, self.detour_dir = -1, None
        self.explore_alt = 1.6 if sc["task"].startswith("L") else self.E["fly_z"]
        self.reexplored = 0
        self.lost_count = 0
        self.rejected = []
        self.align_t = None

    # ----------------------------------------------------------- helpers
    def _set(self, s, t):
        if s != self.state:
            self.log.append((round(t, 2), self.state, s))
            self.state, self.t_state = s, t
            if s == "SPIN":
                self.spin_acc, self.prev_yaw = 0.0, None

    def done(self):
        return self.state in ("DONE", "FAILED")

    def current(self):
        return self.queue[self.k] if 0 <= self.k < len(self.queue) else None

    DECOYS = ("pad_decoy", "pad_X", "pad_plain")

    def _pad_cand(self, xy):
        ok = lambda e: e["hits"] >= 2 and not any(np.linalg.norm(e["pos"][:2] - r) < 0.45 for r in self.rejected)  # noqa: E731
        heli = [e for e in self.mem.entries.get("helipad", []) if ok(e)]
        unk = [e for e in self.mem.entries.get("pad?", []) if ok(e)
               and not any(np.linalg.norm(e["pos"][:2] - d["pos"][:2]) < 0.45
                           for lab in self.DECOYS for d in self.mem.entries.get(lab, []))]
        lst = heli + unk
        return min(lst, key=lambda e: np.linalg.norm(e["pos"][:2] - xy)) if lst else None

    def _goal_for(self, kind, label, xy):
        return self._pad_cand(xy) if kind == "land" else self.mem.best(label, xy)

    def _verdict_near(self, pos, r=0.45):
        for lab in ("helipad",) + self.DECOYS:
            if any(np.linalg.norm(e["pos"][:2] - pos[:2]) < r for e in self.mem.entries.get(lab, [])):
                return lab
        return None

    def _viewpoints(self, xy):
        if self.house:
            rooms = [r for r in ROOMS if not (self.use_memory and r in self.mem.explored)]
            here = room_of(xy)
            rooms.sort(key=lambda r: (r != here, len(route(xy, ROOMS[r]["center"], True)),
                                      np.linalg.norm(np.array(ROOMS[r]["center"]) - xy)))
            return [(r, np.array(ROOMS[r]["center"], float)) for r in rooms]
        pts = [(-1.4, -1.4), (1.4, -1.4), (1.4, 1.4), (-1.4, 1.4), (0.0, 0.0)]
        pts = sorted(pts, key=lambda q: np.linalg.norm(np.array(q) - xy))
        return [(None, np.array(q, float)) for q in pts if np.linalg.norm(np.array(q) - xy) > 0.8]

    def _next_subtask(self, t, pose):
        if self.k >= 0:
            self.sub_log[-1]["t_end"] = t
        self.k += 1
        cur = self.current()
        if cur is None:
            self._set("DONE", t)
            return
        mi, (kind, label) = cur
        if self.k > 0 and self.queue[self.k - 1][0] != mi and not self.persist:
            self.mem.clear()  # new mission, memory not persisted
        if not self.use_memory:
            self.mem.clear()
        self.sub_log.append(dict(mission=mi, kind=kind, label=label, t_start=t, t_end=None, from_memory=False,
                                 success=False, rooms_explored=0))
        self.goal_entry = None
        e = self.mem.best(label, pose.pos[:2]) if self.use_memory else None
        if e is not None and kind == "approach":
            self.goal_entry = e
            self.sub_log[-1]["from_memory"] = True
            self.wps = route(pose.pos[:2], e["pos"][:2], self.house)
            self._set("GOTO", t)
        else:
            self.view_points = self._viewpoints(pose.pos[:2])
            self._set("SPIN" if kind == "land" or not self.house or room_of(pose.pos[:2]) not in self.mem.explored else "EXPLORE", t)

    def _vel_to(self, pose, goal, t, rays, vmax=V_MAX, kp=0.8):
        err = goal - pose.pos[:2]
        v = kp * err
        n = np.linalg.norm(v)
        if n > vmax:
            v *= vmax / n
        rep = np.zeros(2)
        for d, r in rays:
            if r < 0.7:
                w = (1.0 / max(r, 0.15) - 1.0 / 0.7) * 0.22
                rep -= w * d
                if float(v @ d) > 0 and r < 0.6:
                    tang = np.array([-d[1], d[0]])
                    if float(tang @ err) < 0:
                        tang = -tang
                    rep += 0.6 * w * tang
        v = v + rep
        dist = np.linalg.norm(err)
        rt, rd = self.prog
        if rt is None or dist < rd - 0.2:
            self.prog = (t, dist)
        elif t - rt > 5.0 and t >= self.detour_until:
            perp = np.array([-err[1], err[0]]) / (dist + 1e-6)
            self.detour_dir = perp if (int(t) % 2) else -perp
            self.detour_until, self.prog = t + 2.0, (t, dist)
        if t < self.detour_until:
            v = 0.3 * self.detour_dir + 0.4 * v
        return v

    # -------------------------------------------------------------- tick
    def tick(self, t, pose, rays):
        v, yr = np.zeros(3), 0.0
        z_des = self.explore_alt
        drone = self.emb == "drone"
        if t > self.sc["time_budget"] and not self.done():
            self._set("FAILED", t)
        s = self.state
        if s == "TAKEOFF":
            v[2] = 0.3
            if pose.pos[2] > z_des - 0.1:
                self._next_subtask(t, pose)
            return v, 0.0
        if s == "IDLE":
            self._next_subtask(t, pose)
            return v, 0.0
        if s in ("DONE", "FAILED"):
            if drone and not self.landing:
                v[2] = np.clip(1.2 * (self.E["fly_z"] - pose.pos[2]), -0.3, 0.3)
            return v, 0.0
        mi, (kind, label) = self.current()
        sub = self.sub_log[-1]

        # --- target acquisition from memory while searching
        if s in ("SPIN", "EXPLORE"):
            e = self._goal_for(kind, label, pose.pos[:2])
            if e is not None:
                if kind == "land" and s == "SPIN":
                    pass  # finish the 360 deg look first so the NEAREST pad can be chosen
                else:
                    self.goal_entry = e
                    self.wps = route(pose.pos[:2], e["pos"][:2], self.house)
                    self._set("GOTO", t)
                    s = self.state

        if s == "SPIN":
            if self.prev_yaw is not None:
                self.spin_acc += abs(wrap(pose.yaw - self.prev_yaw))
            self.prev_yaw = pose.yaw
            yr = 0.7
            if self.spin_acc > 2 * math.pi:
                r = room_of(pose.pos[:2]) if self.house else None
                if r:
                    if r in self.mem.explored:
                        self.reexplored += 1
                    self.mem.explored.add(r)
                sub["rooms_explored"] += 1
                e = self._goal_for(kind, label, pose.pos[:2])
                if e is not None:
                    self.goal_entry = e
                    self.wps = route(pose.pos[:2], e["pos"][:2], self.house)
                    self._set("GOTO", t)
                else:
                    self.view_points = [vp for vp in self.view_points if vp[0] != r] if self.house else self.view_points
                    if not self.view_points:
                        self._set("FAILED", t)
                    else:
                        self._set("EXPLORE", t)
                        self.wps = route(pose.pos[:2], self.view_points[0][1], self.house)
        elif s == "EXPLORE":
            if not self.wps:
                if not self.view_points:
                    self._set("FAILED", t)
                    return v, 0.0
                self.wps = route(pose.pos[:2], self.view_points[0][1], self.house)
            goal = self.wps[0]
            v[:2] = self._vel_to(pose, goal, t, rays)
            yr = 1.5 * wrap(math.atan2(*(goal - pose.pos[:2])[::-1]) - pose.yaw)
            if np.linalg.norm(goal - pose.pos[:2]) < (0.3 if len(self.wps) > 1 else 0.35):
                self.wps.pop(0)
                if not self.wps:
                    self.view_points.pop(0)
                    self._set("SPIN", t)
        elif s == "GOTO":
            e = self.goal_entry
            tgt = e["pos"][:2]
            if len(self.wps) <= 1:
                self.wps = [tgt]
            goal = self.wps[0]
            if kind == "approach":
                if len(self.wps) == 1:
                    self._set("APPROACH", t)
                    return v, 0.0
            dist = np.linalg.norm(goal - pose.pos[:2])
            v[:2] = self._vel_to(pose, goal, t, rays)
            yr = 1.5 * wrap(math.atan2(*(goal - pose.pos[:2])[::-1]) - pose.yaw)
            if len(self.wps) > 1 and dist < 0.3:
                self.wps.pop(0)
            if kind == "land" and len(self.wps) == 1 and dist < 0.25:
                self._set("ALIGN", t)
        elif s == "APPROACH":
            e = self.goal_entry
            tp = e["pos"]
            rel = tp[:2] - pose.pos[:2]
            dh = np.linalg.norm(rel)
            u = rel / (dh + 1e-6)
            standoff = self.sc["standoff"]
            goal = tp[:2] - u * standoff
            v[:2] = self._vel_to(pose, goal, t, rays, vmax=0.4 if dh > 1.2 else 0.2, kp=0.9)
            if not drone and dh > standoff + 0.25:
                pass
            yr = 2.0 * wrap(math.atan2(rel[1], rel[0]) - pose.yaw)
            if drone and dh < 1.5:
                z_des = max(tp[2] + 0.15, 0.6)
            seen_recent = t - e["last"] < 1.5
            if dh < 1.6 and t - e["last"] > 6.0:  # remembered object not confirmed on arrival -> stale memory
                self.mem.forget(label, e)
                self.lost_count += 1
                self.view_points = self._viewpoints(pose.pos[:2])
                self._set("SPIN", t)
            ok = abs(dh - standoff) < 0.15 and np.linalg.norm(pose.vel[:2]) < 0.12 and seen_recent
            if drone:
                ok = ok and abs(pose.pos[2] - z_des) < 0.1
            if ok:
                self.hold_t = self.hold_t or t
                if t - self.hold_t > 1.5:
                    sub["success_claim"] = True
                    sub["goal_pos"] = [float(x) for x in e["pos"][:3]]
                    sub["claim_pos"] = [float(x) for x in pose.pos[:3]]
                    self.hold_t = None
                    self._next_subtask(t, pose)
            else:
                self.hold_t = None
        elif s in ("ALIGN", "DESCEND"):
            e = self.goal_entry
            err = e["pos"][:2] - pose.pos[:2]
            v[:2] = np.clip(0.8 * err, -0.25, 0.25)
            if s == "ALIGN":
                z_des = 1.0
                self.align_t = self.align_t or t
                verdict = self._verdict_near(e["pos"])
                if verdict in self.DECOYS or (verdict is None and t - self.align_t > 8.0):
                    self.rejected.append(e["pos"][:2].copy())  # wrong marking: try the next-nearest pad
                    sub["rejected"] = sub.get("rejected", 0) + 1
                    self.align_t = None
                    nxt = self._pad_cand(pose.pos[:2])
                    if nxt is None:
                        self.view_points = self._viewpoints(pose.pos[:2])
                        self._set("EXPLORE", t)
                    else:
                        self.goal_entry, self.wps = nxt, [nxt["pos"][:2]]
                        self._set("GOTO", t)
                    return v, 0.0
                if verdict == "helipad" and np.linalg.norm(err) < 0.1 and abs(pose.pos[2] - 1.0) < 0.1                         and np.linalg.norm(pose.vel[:2]) < 0.1:
                    self.align_t = None
                    self._set("DESCEND", t)
            else:
                self.landing = True
                v[2] = -0.25 if np.linalg.norm(err) < 0.15 else 0.0
                if pose.pos[2] < 0.07:
                    sub["success_claim"] = True
                    self._next_subtask(t, pose)
                return v, 0.0
        if drone and not self.landing:
            v[2] = np.clip(1.2 * (z_des - pose.pos[2]), -0.3, 0.3)
        return v, yr


# ================================================================ runner
CAM_PERIOD = 0.2


def run_world_episode(sim, sc, perception, use_memory=True, persist=True, record=None, gimbal_land=-90.0):
    sim.reset(sc, sc["seed"])
    if hasattr(perception, "reset"):
        perception.reset()
    mem = SemanticMemory()
    ms = WorldMission(sc, mem, use_memory, persist)
    safety = SafetyFilter()
    drone = sc["embodiment"] == "drone"
    lat, depth_obs, depth_raw = [], [], []
    pending, next_t = None, 0.0
    path_len, prev, min_clear, traj = 0.0, None, 99.0, []
    tick = 0
    while sim.time() < sc["time_budget"] + 5 and not ms.done():
        t = sim.time()
        pose, ranges = sim.get_pose(), sim.get_ranges()
        # gimbal: look straight down while aligning/landing on a pad
        if drone and ms.state in ("ALIGN", "DESCEND"):
            sim.set_gimbal(gimbal_land)
        else:
            sim.set_gimbal(sc["cam_pitch"])
        if pending and t >= pending[0]:
            dets = pending[1]
            pending = None
            mem.update(dets, t)
            if ms.state in ("ALIGN", "DESCEND") and ms.goal_entry is not None:
                for d in dets:
                    if (d.label.startswith("pad") or d.label == "helipad") and np.linalg.norm(d.pos[:2] - ms.goal_entry["pos"][:2]) < 0.6:
                        ms.goal_entry["pos"] = 0.6 * ms.goal_entry["pos"] + 0.4 * d.pos
        if t >= next_t and ms.state not in ("TAKEOFF",):
            sim.get_rgb()
            with Timer() as tm:
                dets = perception.detect(sim, pose, (ms.current() or (0, (0, None)))[1][1])
            lat.append(tm.ms)
            excl = ms.goal_entry["pos"] if ms.goal_entry else None
            zab = None if drone else (0.05, 0.55)
            depth_raw = depth_obstacles(sim.get_depth(), pose, sim.camera(), z_abs=zab)
            depth_obs = depth_obstacles(sim.get_depth(), pose, sim.camera(), exclude=excl, exclude_r=0.3, z_abs=zab)
            pending = (t + max(CAM_PERIOD, tm.ms / 1000), dets)
            next_t = pending[0]
        rays_p = obstacle_rays(ranges, depth_obs, pose.yaw)
        rays_s = obstacle_rays(ranges, depth_raw, pose.yaw)
        v, yr = ms.tick(t, pose, rays_p)
        if drone:
            if ms.landing:  # landing mode: floor-clearance rule disabled, everything else active
                v2, yr = safety(np.array([v[0], v[1], 0.0]), yr, pose, rays_s, {**ranges, "down": 9.0})
                v = np.array([v2[0], v2[1], v[2]])
            else:
                v, yr = safety(np.asarray(v, float), yr, pose, rays_s, ranges)
        else:
            v2, yr = safety(np.array([v[0], v[1], 0.0]), yr, pose, rays_s, {**ranges, "down": 9.0})
            v = np.array([v2[0], v2[1], 0.0])
            if pose.pos[2] < 0.5:  # ground robot: altitude rules do not apply
                v[2] = 0.0
        sim.send_velocity(*v, yr)
        sim.step()
        g = sim.gt()
        if prev is not None:
            path_len += float(np.linalg.norm(g["pos"][:2] - prev))
        prev = g["pos"][:2].copy()
        if tick % 4 == 0:
            min_clear = min(min_clear, g["clearance"])
        traj.append((t, *g["pos"], g["yaw"], ms.state))
        if record is not None and tick % 4 == 0:
            record(sim, pose, ms, mem, g)
        tick += 1
    return evaluate(sim, sc, ms, mem, dict(path_len=path_len, min_clear=min_clear, lat=lat, traj=traj,
                                           interventions=safety.interventions, perception=perception))


def evaluate(sim, sc, ms, mem, info):
    g = sim.gt()
    objs = g["objects"]
    start = np.array(sc["start"][:2])
    res = dict(task=sc["task"], seed=sc["seed"], embodiment=sc["embodiment"], perception=info["perception"].name,
               memory=("persistent" if ms.persist else "per-mission") if ms.use_memory else "none",
               final_state=ms.state, time=round(sim.time(), 2), collisions=g["collisions"],
               min_clearance=round(info["min_clear"], 3), path_len=round(info["path_len"], 2),
               interventions=info["interventions"], reexplored_rooms=ms.reexplored, lost=ms.lost_count,
               lat_med=float(np.median(info["lat"])) if info["lat"] else 0.0,
               vlm_calls=getattr(info["perception"], "vlm_calls", 0), mem_objects=mem.n_objects())
    subs = []
    for sl in ms.sub_log:
        ok = False
        if sl.get("success_claim"):
            if sl["kind"] == "land":
                pads = [(lab, p) for lab, _, p in objs if lab.startswith("pad") or lab == "helipad"]
                landed_xy = None
                for row in reversed(info["traj"]):
                    if row[3] < 0.1:
                        landed_xy = np.array(row[1:3])
                        break
                landed_xy = landed_xy if landed_xy is not None else g["pos"][:2]
                near = min(pads, key=lambda q: np.linalg.norm(q[1][:2] - landed_xy))
                err = float(np.linalg.norm(near[1][:2] - landed_xy))
                helis = [p for lab, p in pads if lab == "helipad"]
                nearest = min(helis, key=lambda q: np.linalg.norm(q[:2] - start))
                sl["land_err"] = round(err, 3)
                sl["landed_on"] = near[0]
                sl["chose_nearest"] = bool(near[0] == "helipad" and np.linalg.norm(near[1][:2] - nearest[:2]) < 0.05)
                ok = near[0] == "helipad" and err < 0.20
                res["land_err"], res["landed_on"], res["chose_nearest"] = sl["land_err"], sl["landed_on"], sl["chose_nearest"]
            else:
                end_row = min(info["traj"], key=lambda r: abs(r[0] - sl["t_end"]))
                pos = np.array(end_row[1:4])
                # which real object was the robot approaching? -> nearest object to its goal estimate
                goal = np.array(sl.get("goal_pos", pos))
                lab, p = min([(lb, q) for lb, _, q in objs], key=lambda o: np.linalg.norm(o[1][:2] - goal[:2]))
                dh = float(np.linalg.norm(p[:2] - pos[:2]))
                sl["final_dh"] = round(dh, 3)
                sl["at"] = lab
                ok = lab == sl["label"] and float(np.linalg.norm(p[:2] - goal[:2])) < 0.35 and abs(dh - sc["standoff"]) < 0.2
        sl["success"] = bool(ok)
        sl["duration"] = round((sl["t_end"] or sim.time()) - sl["t_start"], 2)
        subs.append(sl)
    res["subtasks"] = subs
    res["n_sub"] = len(ms.queue)
    res["n_sub_ok"] = sum(s["success"] for s in subs)
    res["success"] = bool(res["n_sub_ok"] == len(ms.queue))
    res["wrong_target"] = any(s.get("success_claim") and not s["success"] and (s.get("at") not in (None, s["label"]) or s.get("landed_on", "helipad") != "helipad") for s in subs)
    # memory recall: fraction of real objects whose remembered position is within 0.4 m
    real = [(lab, p) for lab, _, p in objs]
    hit = 0
    for lab, p in real:
        if any(np.linalg.norm(e["pos"][:2] - p[:2]) < 0.4 for e in mem.entries.get(lab, [])):
            hit += 1
    res["mem_recall"] = round(hit / max(1, len(real)), 3)
    res["traj"] = info["traj"]
    res["state_log"] = ms.log
    return res
