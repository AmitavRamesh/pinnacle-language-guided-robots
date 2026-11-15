"""PyBullet implementation of SimAdapter.

Dynamics model (stated as a limitation in the report): translational rigid body
with a velocity-tracking controller, first-order acceleration lag (attitude
response) and acceleration saturation; roll/pitch are not simulated, so the
camera behaves as if gimballed. Collisions use the full PyBullet contact solver.
A minimal flight-controller emulation implements the offboard setpoint timeout:
no setpoint for 0.5 s -> hover, for 3 s -> land.
"""
from __future__ import annotations

import math

import numpy as np
import pybullet as p
import pybullet_data

from .adapter import RANGE_MAX, ring_bearings, CameraIntrinsics, Pose, SimAdapter
from .scenarios import OBJECTS
from .textures import ensure_textures

PHYS_DT = 1 / 240
MASS = 0.35
G = 9.81
TAU_V = 0.35  # velocity-loop time constant (s)
TAU_ATT = 0.08  # attitude / thrust response lag (s)
A_MAX_XY, A_MAX_Z = 3.0, 2.5
YAW_RATE_MAX = 1.5
HOVER_TIMEOUT, LAND_TIMEOUT = 0.5, 3.0
CAM_W, CAM_H, CAM_VFOV, CAM_PITCH = 320, 240, 60.0, -15.0
NEAR, FAR = 0.05, 12.0
BODY_HALF = (0.12, 0.12, 0.04)
SENSOR_OFFSET = 0.13


def _yaw_quat(yaw):
    return p.getQuaternionFromEuler([0, 0, yaw])


class PyBulletSim(SimAdapter):
    name = "pybullet"

    def __init__(self, gui: bool = False):
        self.cid = p.connect(p.GUI if gui else p.DIRECT)
        p.setAdditionalSearchPath(pybullet_data.getDataPath(), physicsClientId=self.cid)
        self.tex_paths = ensure_textures()
        fy = (CAM_H / 2) / math.tan(math.radians(CAM_VFOV) / 2)
        self._cam = CameraIntrinsics(CAM_W, CAM_H, fy, fy, CAM_W / 2, CAM_H / 2, CAM_PITCH, (SENSOR_OFFSET, 0, 0))
        self._proj = p.computeProjectionMatrixFOV(CAM_VFOV, CAM_W / CAM_H, NEAR, FAR)

    # ------------------------------------------------------------------ build
    def reset(self, scenario: dict, seed: int) -> None:
        c = self.cid
        p.resetSimulation(physicsClientId=c)
        p.setGravity(0, 0, -G, physicsClientId=c)
        p.setTimeStep(PHYS_DT, physicsClientId=c)
        self.sc = scenario
        self.rng = np.random.default_rng(seed + 1000)
        self.textures = {k: p.loadTexture(v, physicsClientId=c) for k, v in self.tex_paths.items()}
        self.plane = p.loadURDF("plane.urdf", physicsClientId=c)
        self.static_ids = []  # walls, tables, obstacles (things you can crash into)
        self.items = []  # (kind, body_id, pos)
        self.target_table = None
        half = scenario["room"] / 2
        for xy, ext in [((half, 0), (0.05, half, 1.3)), ((-half, 0), (0.05, half, 1.3)),
                        ((0, half), (half, 0.05, 1.3)), ((0, -half), (half, 0.05, 1.3))]:
            self.static_ids.append(self._box(ext, (xy[0], xy[1], 1.3), [0.82, 0.82, 0.8, 1]))
        for t in scenario["tables"]:
            h, s = t["height"], t["size"] / 2
            self.static_ids.append(self._box((s, s, h / 2), (*t["xy"], h / 2), [0.45, 0.3, 0.18, 1]))
            if t["item"] == "orange":
                self.target_table = self.static_ids[-1]
            spec = OBJECTS[t["item"]]
            z = h + spec["size"]
            if spec["shape"] == "sphere":
                vis = p.createVisualShape(p.GEOM_SPHERE, radius=spec["size"], rgbaColor=spec["rgba"], physicsClientId=c)
                col = p.createCollisionShape(p.GEOM_SPHERE, radius=spec["size"], physicsClientId=c)
            else:
                e = [spec["size"]] * 3
                vis = p.createVisualShape(p.GEOM_BOX, halfExtents=e, rgbaColor=spec["rgba"], physicsClientId=c)
                col = p.createCollisionShape(p.GEOM_BOX, halfExtents=e, physicsClientId=c)
            bid = p.createMultiBody(0, col, vis, [*t["xy"], z], physicsClientId=c)
            if spec["texture"]:
                p.changeVisualShape(bid, -1, textureUniqueId=self.textures[spec["texture"]], physicsClientId=c)
            self.items.append((t["item"], bid, np.array([*t["xy"], z])))
        for o in scenario["obstacles"]:
            if o["type"] == "cyl":
                vis = p.createVisualShape(p.GEOM_CYLINDER, radius=o["size"], length=o["height"],
                                          rgbaColor=[0.55, 0.6, 0.7, 1], physicsClientId=c)
                col = p.createCollisionShape(p.GEOM_CYLINDER, radius=o["size"], height=o["height"], physicsClientId=c)
                self.static_ids.append(p.createMultiBody(0, col, vis, [*o["xy"], o["height"] / 2], physicsClientId=c))
            else:  # wall segment
                ext = (o["size"][0] / 2, o["size"][1] / 2, o["height"] / 2)
                self.static_ids.append(self._box(ext, (*o["xy"], o["height"] / 2), [0.7, 0.68, 0.6, 1],
                                                 yaw=o.get("yaw", 0) + math.pi / 2))
        col = p.createCollisionShape(p.GEOM_BOX, halfExtents=BODY_HALF, physicsClientId=c)
        vis = p.createVisualShape(p.GEOM_BOX, halfExtents=BODY_HALF, rgbaColor=[0.15, 0.15, 0.18, 1], physicsClientId=c)
        self.drone = p.createMultiBody(MASS, col, vis, scenario["start"], _yaw_quat(scenario["start_yaw"]), physicsClientId=c)
        p.changeDynamics(self.drone, -1, linearDamping=0, angularDamping=0, physicsClientId=c)
        self.yaw = scenario["start_yaw"]
        self.yaw_rate = 0.0
        self.a_act = np.zeros(3)
        self.cmd = np.zeros(4)
        self.t = 0.0
        self.last_cmd_t = 0.0
        self.mode = "OFFBOARD"
        self.drift = np.zeros(3)
        self.gust = np.zeros(3)
        self.collisions = 0
        self._in_contact = False
        self._frame_t = -1.0
        self.bearings = ring_bearings(scenario.get("ring_rays", 8))
        self.noise = scenario["noise"]
        self.light = scenario["light"]

    def _box(self, ext, pos, rgba, yaw=0.0):
        c = self.cid
        vis = p.createVisualShape(p.GEOM_BOX, halfExtents=ext, rgbaColor=rgba, physicsClientId=c)
        col = p.createCollisionShape(p.GEOM_BOX, halfExtents=ext, physicsClientId=c)
        return p.createMultiBody(0, col, vis, pos, _yaw_quat(yaw), physicsClientId=c)

    # ------------------------------------------------------------- dynamics
    def send_velocity(self, vx, vy, vz, yaw_rate):
        self.cmd = np.array([vx, vy, vz, yaw_rate], float)
        self.last_cmd_t = self.t

    def step(self):
        c = self.cid
        n = round(self.dt_control / PHYS_DT)
        for _ in range(n):
            age = self.t - self.last_cmd_t
            pos, _ = p.getBasePositionAndOrientation(self.drone, physicsClientId=c)
            if self.mode == "LANDED":
                pass
            elif age > LAND_TIMEOUT or self.mode == "LANDING":
                self.mode = "LANDING"
                cmd = np.array([0, 0, -0.35, 0])
            elif age > HOVER_TIMEOUT:
                self.mode = "HOVER_FAILSAFE"
                cmd = np.zeros(4)
            else:
                self.mode = "OFFBOARD"
                cmd = self.cmd
            if self.mode == "LANDING" and pos[2] < 0.06:
                self.mode = "LANDED"
            v = np.array(p.getBaseVelocity(self.drone, physicsClientId=c)[0])
            if self.mode == "LANDED":
                force = np.zeros(3)
                self.yaw_rate = 0.0
            else:
                a_des = (cmd[:3] - v) / TAU_V
                nxy = np.linalg.norm(a_des[:2])
                if nxy > A_MAX_XY:
                    a_des[:2] *= A_MAX_XY / nxy
                a_des[2] = np.clip(a_des[2], -A_MAX_Z, A_MAX_Z)
                self.a_act += (a_des - self.a_act) * (PHYS_DT / TAU_ATT)
                if self.noise["gust"] > 0:
                    self.gust += -self.gust * PHYS_DT / 1.5 + self.rng.normal(0, self.noise["gust"] * 0.08, 3) * math.sqrt(PHYS_DT)
                    self.gust[2] *= 0.3
                force = MASS * (self.a_act + np.array([0, 0, G]) + self.gust) - 0.05 * v
                yr = np.clip(cmd[3], -YAW_RATE_MAX, YAW_RATE_MAX)
                self.yaw_rate += (yr - self.yaw_rate) * (PHYS_DT / 0.1)
            self.yaw = (self.yaw + self.yaw_rate * PHYS_DT + math.pi) % (2 * math.pi) - math.pi
            p.applyExternalForce(self.drone, -1, force.tolist(), pos, p.WORLD_FRAME, physicsClientId=c)
            p.stepSimulation(physicsClientId=c)
            pos2, _ = p.getBasePositionAndOrientation(self.drone, physicsClientId=c)
            v2 = p.getBaseVelocity(self.drone, physicsClientId=c)[0]
            p.resetBasePositionAndOrientation(self.drone, pos2, _yaw_quat(self.yaw), physicsClientId=c)
            p.resetBaseVelocity(self.drone, v2, [0, 0, self.yaw_rate], physicsClientId=c)
            self.t += PHYS_DT
        # contact bookkeeping (count collision events, not frames)
        cps = [cp for cp in p.getContactPoints(bodyA=self.drone, physicsClientId=c) if cp[2] != self.plane]
        if cps and not self._in_contact:
            self.collisions += 1
        self._in_contact = bool(cps)
        # pose drift proportional to distance travelled (optical-flow / VIO style)
        if self.noise["pose"] > 0:
            v = np.array(p.getBaseVelocity(self.drone, physicsClientId=c)[0])
            self.drift += self.rng.normal(0, 1, 3) * self.noise["pose"] * np.abs(v) * self.dt_control
            self.drift[2] *= 0.5

    def time(self):
        return self.t

    def fc_mode(self):
        return self.mode

    # ---------------------------------------------------------------- sensors
    def _true_pose(self):
        pos, _ = p.getBasePositionAndOrientation(self.drone, physicsClientId=self.cid)
        v = p.getBaseVelocity(self.drone, physicsClientId=self.cid)[0]
        return np.array(pos), np.array(v)

    def get_pose(self):
        pos, v = self._true_pose()
        return Pose(pos + self.drift, self.yaw, v)

    def camera(self):
        return self._cam

    def _render(self):
        if self._frame_t == self.t:
            return
        pos, _ = self._true_pose()
        cy, sy = math.cos(self.yaw), math.sin(self.yaw)
        pitch = math.radians(CAM_PITCH)
        eye = pos + np.array([cy, sy, 0]) * SENSOR_OFFSET
        fwd = np.array([cy * math.cos(pitch), sy * math.cos(pitch), math.sin(pitch)])
        right = np.array([sy, -cy, 0])
        up = np.cross(right, fwd)
        view = p.computeViewMatrix(eye.tolist(), (eye + fwd).tolist(), up.tolist())
        L = self.light
        _, _, rgba, depth, seg = p.getCameraImage(
            CAM_W, CAM_H, view, self._proj, lightDirection=L["direction"], lightColor=L["color"],
            lightAmbientCoeff=L["ambient"], lightDiffuseCoeff=L["diffuse"], lightSpecularCoeff=L["specular"],
            shadow=1, renderer=p.ER_TINY_RENDERER, physicsClientId=self.cid)
        self._rgb = np.asarray(rgba, np.uint8).reshape(CAM_H, CAM_W, 4)[..., :3].copy()
        d = np.asarray(depth, np.float32).reshape(CAM_H, CAM_W)
        z = FAR * NEAR / (FAR - (FAR - NEAR) * d)
        if self.noise["depth"] > 0:
            z = z * (1 + self.rng.normal(0, self.noise["depth"], z.shape).astype(np.float32))
        self._depth = z
        self._seg = np.asarray(seg, np.int32).reshape(CAM_H, CAM_W)
        self._frame_t = self.t

    def get_rgb(self):
        self._render()
        return self._rgb

    def get_depth(self):
        self._render()
        return self._depth

    def get_ranges(self):
        n_ring = len(self.bearings)
        pos, _ = self._true_pose()
        starts, ends = [], []
        dirs = [np.array([math.cos(self.yaw + b), math.sin(self.yaw + b), 0]) for b in self.bearings]
        dirs += [np.array([0, 0, -1.0]), np.array([0, 0, 1.0])]
        for i, dvec in enumerate(dirs):
            off = SENSOR_OFFSET if i < n_ring else BODY_HALF[2] + 0.01
            s = pos + dvec * off
            starts.append(s.tolist())
            ends.append((s + dvec * RANGE_MAX).tolist())
        res = p.rayTestBatch(starts, ends, physicsClientId=self.cid)
        r = np.array([h[2] * RANGE_MAX if h[0] >= 0 else RANGE_MAX for h in res])
        if self.noise["range"] > 0:
            r = np.clip(r + self.rng.normal(0, self.noise["range"], r.shape), 0, RANGE_MAX)
        return {"ring": r[:n_ring], "down": float(r[n_ring]), "up": float(r[n_ring + 1]), "bearings": self.bearings}

    # ----------------------------------------------------------- ground truth
    def gt(self):
        pos, v = self._true_pose()
        tgt = [it for it in self.items if it[0] == "orange"]
        clear, clear_tgt = RANGE_MAX, RANGE_MAX
        tgt_ids = {self.target_table} | {it[1] for it in self.items if it[0] == "orange"}
        for bid in self.static_ids + [it[1] for it in self.items]:
            for cp in p.getClosestPoints(self.drone, bid, 2.0, physicsClientId=self.cid):
                if bid in tgt_ids:
                    clear_tgt = min(clear_tgt, cp[8])
                else:
                    clear = min(clear, cp[8])
        return dict(
            pos=pos, vel=v, yaw=self.yaw,
            target=tgt[0][2] if tgt else None,
            target_id=tgt[0][1] if tgt else None,
            distractors=[(k, pp) for k, _, pp in self.items if k != "orange"],
            clearance=clear, clearance_target=clear_tgt, collisions=self.collisions, mode=self.mode,
        )

    def visible_pixels(self, body_id):
        self._render()
        return int((self._seg == body_id).sum())

    def close(self):
        p.disconnect(self.cid)
