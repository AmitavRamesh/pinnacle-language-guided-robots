"""Perception modules. Each returns a list of Detection in the drone's
*estimated* world frame (so pose drift propagates into target estimates)."""
from __future__ import annotations

import math
import time
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class Detection:
    label: str
    conf: float
    pos: np.ndarray  # estimated world position (m)
    bbox: tuple  # x0, y0, x1, y1 (px)
    dist: float  # metres from camera


def cam_axes(yaw: float, pitch_deg: float):
    cy, sy = math.cos(yaw), math.sin(yaw)
    pitch = math.radians(pitch_deg)
    fwd = np.array([cy * math.cos(pitch), sy * math.cos(pitch), math.sin(pitch)])
    right = np.array([sy, -cy, 0.0])
    up = np.cross(right, fwd)
    return fwd, right, up


def cam_frame(pose, cam):
    """Camera eye position and axes in the world, using full attitude when available."""
    if pose.rot is None:
        fwd, right, up = cam_axes(pose.yaw, cam.pitch_deg)
        c, s_ = math.cos(pose.yaw), math.sin(pose.yaw)
        o = cam.offset
        eye = pose.pos + np.array([c * o[0] - s_ * o[1], s_ * o[0] + c * o[1], o[2] if len(o) > 2 else 0.0])
        return eye, fwd, right, up
    p = math.radians(cam.pitch_deg)
    fb = np.array([math.cos(p), 0, math.sin(p)])
    rb = np.array([0.0, -1.0, 0.0])
    ub = np.cross(rb, fb)
    R = pose.rot
    return pose.pos + R @ np.asarray(cam.offset), R @ fb, R @ rb, R @ ub


def pixel_to_world(u, v, z, pose, cam):
    eye, fwd, right, up = cam_frame(pose, cam)
    xc = (u - cam.cx) / cam.fx * z
    yc = (v - cam.cy) / cam.fy * z
    return eye + fwd * z + right * xc - up * yc


def centre_depth(z_surface, bbox_w_px, fx):
    """Depth image sees the near surface; add the estimated object radius."""
    r = 0.5 * bbox_w_px * z_surface / fx
    return z_surface + min(r, 0.3)


def blob_depth(depth, mask):
    vals = depth[mask]
    vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        return None
    return float(np.percentile(vals, 30))  # nearer part of blob = object surface, not background


class Perception:
    name = "base"
    needs_gpu = False

    def detect(self, sim, pose, query: str) -> list[Detection]:
        raise NotImplementedError


class OraclePerception(Perception):
    """C0: perfect detection whenever >= 4 target pixels are visible."""
    name = "oracle"

    def detect(self, sim, pose, query):
        g = sim.gt()
        if g["target_id"] is None or sim.visible_pixels(g["target_id"]) < 4:
            return []
        rel = g["target"] - g["pos"]
        est = pose.pos + rel
        return [Detection(query, 1.0, est, (0, 0, 0, 0), float(np.linalg.norm(rel)))]


class HSVPerception(Perception):
    """C1: colour threshold. Knows nothing about 'orange the fruit', only the colour."""
    name = "hsv"
    LO, HI = np.array([5, 150, 150]), np.array([22, 255, 255])

    def detect(self, sim, pose, query):
        rgb, depth, cam = sim.get_rgb(), sim.get_depth(), sim.camera()
        hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
        mask = cv2.inRange(hsv, self.LO, self.HI)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))  # merge peel-texture fragments
        n, lab, stats, cents = cv2.connectedComponentsWithStats(mask)
        out = []
        for i in range(1, n):
            area = stats[i, cv2.CC_STAT_AREA]
            if area < 4:
                continue
            z = blob_depth(depth, lab == i)
            if z is None or z > 8:
                continue
            u, v = cents[i]
            x, y, w, h = stats[i, :4]
            z = centre_depth(z, w, cam.fx)
            out.append(Detection(query, min(1.0, area / 40), pixel_to_world(u, v, z, pose, cam), (x, y, x + w, y + h), z))
        return out


def boxes_to_detections(boxes, scores, labels, sim, pose, query, min_px=2):
    depth, cam = sim.get_depth(), sim.camera()
    H, W = depth.shape
    out = []
    for (x0, y0, x1, y1), s, lab in zip(boxes, scores, labels):
        x0, y0 = max(0, int(x0)), max(0, int(y0))
        x1, y1 = min(W, int(math.ceil(x1))), min(H, int(math.ceil(y1)))
        if x1 - x0 < min_px or y1 - y0 < min_px:
            continue
        # central 50% of the box to avoid background pixels
        cx0, cx1 = x0 + (x1 - x0) // 4, x1 - (x1 - x0) // 4
        cy0, cy1 = y0 + (y1 - y0) // 4, y1 - (y1 - y0) // 4
        m = np.zeros_like(depth, bool)
        m[cy0:max(cy1, cy0 + 1), cx0:max(cx1, cx0 + 1)] = True
        z = blob_depth(depth, m)
        if z is None or z > 8:
            continue
        u, v = (x0 + x1) / 2, (y0 + y1) / 2
        z = centre_depth(z, x1 - x0, cam.fx)
        out.append(Detection(lab, float(s), pixel_to_world(u, v, z, pose, cam), (x0, y0, x1, y1), z))
    return out


class TargetBelief:
    """Fuses detections over time into one target estimate."""

    def __init__(self, gate=0.6, alpha=0.4, confirm_hits=3):
        self.pos = None
        self.hits = 0
        self.last_seen = -1e9
        self.conf = 0.0
        self.gate, self.alpha, self.confirm_hits = gate, alpha, confirm_hits

    def update(self, dets, t, min_conf=0.0):
        dets = [d for d in dets if d.conf >= min_conf]
        if not dets:
            return None
        if self.pos is not None:
            near = [d for d in dets if np.linalg.norm(d.pos - self.pos) < self.gate]
            if near:
                d = max(near, key=lambda d: d.conf)
                self.pos = (1 - self.alpha) * self.pos + self.alpha * d.pos
                self.hits += 1
                self.last_seen, self.conf = t, max(self.conf * 0.8, d.conf)
                return d
            if t - self.last_seen < 2.0:
                return None  # stay locked on current track briefly
        d = max(dets, key=lambda d: d.conf)
        self.pos, self.hits, self.last_seen, self.conf = d.pos.copy(), 1, t, d.conf
        return d

    @property
    def confirmed(self):
        return self.pos is not None and self.hits >= self.confirm_hits

    def reset(self):
        self.__init__(self.gate, self.alpha, self.confirm_hits)


class Timer:
    def __enter__(self):
        self.t0 = time.perf_counter()
        return self

    def __exit__(self, *a):
        self.ms = (time.perf_counter() - self.t0) * 1000
