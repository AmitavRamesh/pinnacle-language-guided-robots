"""Mission state machine, classical planner (search + approach + local avoidance)
and the safety filter. The safety filter uses raw range/depth data only and
never trusts the AI modules."""
from __future__ import annotations

import math

import numpy as np

from .adapter import RANGE_BEARINGS
from .perception import cam_frame

FLY_Z = 1.0
V_MAX = 0.5
VZ_MAX = 0.3
YAW_RATE = 0.7
ROOM_HALF = 3.0


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


# ---------------------------------------------------------------- obstacle sensing
def depth_obstacles(depth, pose, cam, n_sectors=7, band=0.15, exclude=None, exclude_r=0.15, z_abs=None):
    """Forward obstacle distances per sector from the depth image (horizontal
    distance of points within +-band m of flight altitude)."""
    if depth is None:
        return []
    H, W = depth.shape
    step = 3
    vs, us = np.mgrid[0:H:step, 0:W:step]
    z = depth[::step, ::step]
    eye, fwd, right, up = cam_frame(pose, cam)
    xc = (us - cam.cx) / cam.fx * z
    yc = (vs - cam.cy) / cam.fy * z
    rel = fwd[None, None] * z[..., None] + right[None, None] * xc[..., None] - up[None, None] * yc[..., None]
    zw = rel[..., 2] + eye[2]
    if z_abs is not None:  # absolute height band (ground robots: anything it could drive into)
        keep = (zw > z_abs[0]) & (zw < z_abs[1]) & (z < 3.0)
    else:
        keep = (np.abs(zw - pose.pos[2]) < band) & (z < 3.0)
    if exclude is not None:
        keep &= np.linalg.norm(rel + eye - exclude, axis=-1) > exclude_r
    if not keep.any():
        return []
    pts = rel[keep]
    ang = np.arctan2(pts[:, 1], pts[:, 0]) - pose.yaw
    ang = (ang + math.pi) % (2 * math.pi) - math.pi
    dist = np.hypot(pts[:, 0], pts[:, 1])
    hfov = math.atan(cam.cx / cam.fx)
    edges = np.linspace(-hfov, hfov, n_sectors + 1)
    out = []
    for i in range(n_sectors):
        m = (ang >= edges[i]) & (ang < edges[i + 1])
        if m.any():
            out.append(((edges[i] + edges[i + 1]) / 2, float(np.percentile(dist[m], 2))))
    return out  # list of (bearing rel. body, distance)


def obstacle_rays(ranges, depth_obs, yaw):
    """All obstacle observations as (world unit vector, distance)."""
    rays = []
    for b, r in zip(ranges.get("bearings", RANGE_BEARINGS), ranges["ring"]):
        a = yaw + b
        rays.append((np.array([math.cos(a), math.sin(a)]), float(r) + 0.13))
    for b, r in depth_obs:
        a = yaw + b
        rays.append((np.array([math.cos(a), math.sin(a)]), r))
    return rays


# ------------------------------------------------------------------ safety filter
class SafetyFilter:
    D_STOP, D_SLOW, D_PUSH = 0.25, 0.60, 0.18

    def __init__(self):
        self.interventions = 0

    def __call__(self, v, yaw_rate, pose, rays, ranges):
        v_in = v.copy()
        v = v.copy()
        sp = np.linalg.norm(v[:2])
        if sp > V_MAX:
            v[:2] *= V_MAX / sp
        v[2] = np.clip(v[2], -VZ_MAX, VZ_MAX)
        yaw_rate = float(np.clip(yaw_rate, -1.0, 1.0))
        for d, r in rays:
            toward = float(v[:2] @ d)
            if r < self.D_STOP and toward > 0:
                v[:2] -= toward * d
            elif r < self.D_SLOW and toward > 0:
                allowed = V_MAX * (r - self.D_STOP) / (self.D_SLOW - self.D_STOP)
                if toward > allowed:
                    v[:2] -= (toward - allowed) * d
            if r < self.D_PUSH:
                v[:2] -= 0.15 * d
        # geofence (room interior shrunk by 0.4 m)
        lim = ROOM_HALF - 0.4
        for i in range(2):
            if pose.pos[i] > lim and v[i] > 0:
                v[i] = -0.1
            if pose.pos[i] < -lim and v[i] < 0:
                v[i] = 0.1
        # altitude band and floor/table clearance
        if pose.pos[2] > 1.8 and v[2] > 0:
            v[2] = 0
        if (ranges["down"] < 0.35 or pose.pos[2] < 0.5) and v[2] < 0.1:
            v[2] = 0.15
        if np.linalg.norm(v - v_in) > 0.05:
            self.interventions += 1
        return v, yaw_rate


# ------------------------------------------------------------------- mission
class Mission:
    """TAKEOFF -> SEARCH_SPIN <-> SEARCH_MOVE -> APPROACH -> HOLD -> FOUND
    any search exhausted / time budget -> NOT_FOUND."""

    def __init__(self, standoff=0.5, time_budget=120.0, start_xy=(0, 0)):
        self.state = "TAKEOFF"
        self.standoff = standoff
        self.budget = time_budget
        self.spin_acc = 0.0
        self.prev_yaw = None
        self.hold_t = None
        self.reports = []
        self.lost_count = 0
        pts = [np.array(p) for p in [(-1.6, -1.6), (1.6, -1.6), (1.6, 1.6), (-1.6, 1.6), (0.0, 0.0)]]
        order, cur = [], np.array(start_xy, float)
        while pts:
            i = int(np.argmin([np.linalg.norm(p - cur) for p in pts]))
            cur = pts.pop(i)
            if np.linalg.norm(cur - np.array(start_xy)) > 0.8:
                order.append(cur)
        self.waypoints = order
        self.wp_progress = (None, None)
        self.detour_until, self.detour_dir = -1, None
        self.log = []

    def _set(self, s, t):
        if s != self.state:
            self.log.append((round(t, 2), self.state, s))
            self.state = s
            if s == "SEARCH_SPIN":
                self.spin_acc, self.prev_yaw = 0.0, None

    def done(self):
        return self.state in ("FOUND", "NOT_FOUND")

    # ---------------------------------------------------------------- helpers
    def _goal_velocity(self, pose, goal_xy, t, rays, v_max=V_MAX, kp=0.8):
        err = goal_xy - pose.pos[:2]
        v = kp * err
        n = np.linalg.norm(v)
        if n > v_max:
            v *= v_max / n
        # repulsion + tangential slide around obstacles
        rep = np.zeros(2)
        for d, r in rays:
            if r < 0.8:
                w = (1.0 / max(r, 0.15) - 1.0 / 0.8) * 0.25
                rep -= w * d
                if float(v @ d) > 0 and r < 0.8:
                    tang = np.array([-d[1], d[0]])
                    if float(tang @ err) < 0:
                        tang = -tang
                    rep += 0.6 * w * tang
        v = v + rep
        # stuck handling: no progress -> commit to a sideways detour
        if t < self.detour_until and self.detour_dir is not None:
            v = 0.35 * self.detour_dir + 0.3 * v
        return v

    def _check_stuck(self, pose, goal_xy, t):
        d = np.linalg.norm(goal_xy - pose.pos[:2])
        ref_t, ref_d = self.wp_progress
        if ref_t is None or d < ref_d - 0.25:
            self.wp_progress = (t, d)
            return False
        if t - ref_t > 6.0:
            self.wp_progress = (t, d)
            return True
        return False

    def _start_detour(self, pose, goal_xy, t):
        err = goal_xy - pose.pos[:2]
        perp = np.array([-err[1], err[0]]) / (np.linalg.norm(err) + 1e-6)
        if np.random.default_rng(int(t * 10)).random() < 0.5:
            perp = -perp
        self.detour_dir, self.detour_until = perp, t + 2.5

    # -------------------------------------------------------------------- tick
    def tick(self, t, pose, belief, rays, verdict=None):
        """Returns world-frame velocity (3,) and yaw rate. `verdict` lets a
        high-level policy (VLM) override search decisions."""
        z_des = FLY_Z
        if self.state in ("APPROACH", "HOLD") and belief.pos is not None:
            if np.linalg.norm(belief.pos[:2] - pose.pos[:2]) < 1.5:
                z_des = max(belief.pos[2] + 0.15, 0.6)  # final approach: drop so target stays in view
        vz = np.clip(1.2 * (z_des - pose.pos[2]), -VZ_MAX, VZ_MAX)
        v = np.zeros(3)
        yaw_rate = 0.0
        if t > self.budget and not self.done():
            self._set("NOT_FOUND", t)
            self.reports.append((t, "not_found"))
        s = self.state
        if s == "TAKEOFF":
            v[2] = VZ_MAX
            if pose.pos[2] > FLY_Z - 0.1:
                self._set("SEARCH_SPIN", t)
            return v, 0.0
        if s in ("FOUND", "NOT_FOUND"):
            v[2] = vz
            return v, 0.0

        # target acquisition from any search state
        if s.startswith("SEARCH") and belief.confirmed and t - belief.last_seen < 1.0:
            self._set("APPROACH", t)
            s = self.state

        if s == "SEARCH_SPIN":
            if self.prev_yaw is not None:
                self.spin_acc += abs(wrap(pose.yaw - self.prev_yaw))
            self.prev_yaw = pose.yaw
            yaw_rate = YAW_RATE
            if self.spin_acc > 2 * math.pi:
                if self.waypoints:
                    self._set("SEARCH_MOVE", t)
                    self.wp_progress = (None, None)
                else:
                    self._set("NOT_FOUND", t)
                    self.reports.append((t, "not_found"))
        elif s == "SEARCH_MOVE":
            goal = self.waypoints[0]
            vxy = self._goal_velocity(pose, goal, t, rays)
            v[:2] = vxy
            heading = math.atan2(*(goal - pose.pos[:2])[::-1])
            yaw_rate = 1.5 * wrap(heading - pose.yaw)
            if np.linalg.norm(goal - pose.pos[:2]) < 0.35:
                self.waypoints.pop(0)
                self._set("SEARCH_SPIN", t)
            elif self._check_stuck(pose, goal, t):
                if t >= self.detour_until:
                    self._start_detour(pose, goal, t)
                if getattr(self, "_stuck_n", 0) >= 3:
                    self.waypoints.pop(0)
                    self._stuck_n = 0
                    self._set("SEARCH_SPIN", t)
                else:
                    self._stuck_n = getattr(self, "_stuck_n", 0) + 1
        elif s in ("APPROACH", "HOLD"):
            if t - belief.last_seen > 4.0:
                self.lost_count += 1
                belief.reset()
                self._set("SEARCH_SPIN", t)
                v[2] = vz
                return v, YAW_RATE
            tp = belief.pos
            dz = pose.pos[2] - tp[2]
            dh_des = math.sqrt(max(self.standoff**2 - dz**2, 0.3**2))
            rel = tp[:2] - pose.pos[:2]
            dh = np.linalg.norm(rel)
            u = rel / (dh + 1e-6)
            goal = tp[:2] - u * dh_des
            vmax = 0.4 if dh > 1.2 else 0.2
            v[:2] = self._goal_velocity(pose, goal, t, rays, v_max=vmax, kp=0.9)
            yaw_rate = 2.0 * wrap(math.atan2(rel[1], rel[0]) - pose.yaw)
            if self._check_stuck(pose, goal, t) and t >= self.detour_until:
                self._start_detour(pose, goal, t)
            dist3 = float(np.linalg.norm(tp - pose.pos))
            ok = abs(dist3 - self.standoff) < 0.1 and abs(pose.pos[2] - z_des) < 0.08 and np.linalg.norm(pose.vel[:2]) < 0.12 and t - belief.last_seen < 1.5
            if ok:
                if self.hold_t is None:
                    self.hold_t = t
                    self._set("HOLD", t)
                elif t - self.hold_t > 1.5:
                    self._set("FOUND", t)
                    self.reports.append((t, "found"))
            else:
                self.hold_t = None
                if self.state == "HOLD":
                    self._set("APPROACH", t)
        v[2] = vz if s != "TAKEOFF" else v[2]
        return v, yaw_rate
