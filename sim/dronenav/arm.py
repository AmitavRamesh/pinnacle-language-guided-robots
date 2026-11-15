"""Third embodiment: fixed-base arm (Franka Panda) with a fixed RGB-D camera.
Task: "pick up the <object>" from a table that may hold distractors.

The perception modules are the SAME classes used by the drone and ground robot
(they only need get_rgb / get_depth / camera / visible_pixels / gt). The embodiment
adapter maps a 3-D target point to joint angles with inverse kinematics.
Grasp simplification (stated in the report): when the open gripper reaches the object
centre within 3 cm and closes, the object is attached with a fixed constraint.
"""
from __future__ import annotations

import math
import zlib

import numpy as np
import pybullet as p
import pybullet_data

from .adapter import CameraIntrinsics, Pose
from .scenarios import OBJECTS
from .textures import ensure_textures

TABLE_H = 0.62
CAM_W, CAM_H, VFOV = 320, 240, 60.0
NEAR, FAR = 0.05, 5.0
EYE = np.array([0.12, 0.0, 1.30])
LOOK = np.array([0.55, 0.0, TABLE_H])
EE = 11
ARM_J = list(range(7))
FINGERS = [9, 10]
HOME = [0, -0.6, 0, -2.4, 0, 1.9, 0.8]


def make_arm_task(task, seed):
    rng = np.random.default_rng(zlib.crc32(f"{task}-{seed}".encode()))
    items = ["orange"]
    if task in ("A2", "A3"):
        items += list(rng.choice(["orange_ball", "orange_cube", "apple", "lemon"], 3, replace=False))
    pos = []
    for _ in items:
        for _ in range(300):
            q = np.array([rng.uniform(0.42, 0.70), rng.uniform(-0.28, 0.28)])
            if all(np.linalg.norm(q - u) > 0.13 for u in pos):
                break
        pos.append(q)
    light = dict(direction=[1, 1, 3], color=[1, 1, 1], ambient=0.6, diffuse=0.45, specular=0.1)
    if task == "A3":
        light = dict(direction=[1, -2, 3], color=[0.6, 0.6, 0.65], ambient=0.3, diffuse=0.3, specular=0.05)
    return dict(task=task, seed=seed, embodiment="arm", items=[(k, q.tolist()) for k, q in zip(items, pos)],
                target="orange", light=light, noise=dict(depth=0.0), command="pick up the orange")


class ArmSim:
    name = "pybullet-arm"

    def __init__(self):
        self.cid = p.connect(p.DIRECT)
        p.setAdditionalSearchPath(pybullet_data.getDataPath(), physicsClientId=self.cid)
        self.tex_paths = ensure_textures()
        self.proj = p.computeProjectionMatrixFOV(VFOV, CAM_W / CAM_H, NEAR, FAR)
        d = LOOK - EYE
        self.yaw = math.atan2(d[1], d[0])
        self.pitch = math.degrees(math.atan2(d[2], np.linalg.norm(d[:2])))

    def reset(self, sc, seed=0):
        c = self.cid
        p.resetSimulation(physicsClientId=c)
        p.setGravity(0, 0, -9.81, physicsClientId=c)
        self.sc, self.t, self._ft = sc, 0.0, -1
        self.light = sc["light"]
        self.plane = p.loadURDF("plane.urdf", physicsClientId=c)
        tex = {k: p.loadTexture(v, physicsClientId=c) for k, v in self.tex_paths.items()}
        vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.35, 0.45, TABLE_H / 2], rgbaColor=[0.55, 0.42, 0.3, 1], physicsClientId=c)
        col = p.createCollisionShape(p.GEOM_BOX, halfExtents=[0.35, 0.45, TABLE_H / 2], physicsClientId=c)
        self.table = p.createMultiBody(0, col, vis, [0.6, 0, TABLE_H / 2], physicsClientId=c)
        vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.12, 0.12, TABLE_H / 2], rgbaColor=[0.3, 0.3, 0.33, 1], physicsClientId=c)
        col = p.createCollisionShape(p.GEOM_BOX, halfExtents=[0.12, 0.12, TABLE_H / 2], physicsClientId=c)
        p.createMultiBody(0, col, vis, [0.0, 0, TABLE_H / 2], physicsClientId=c)
        self.arm = p.loadURDF("franka_panda/panda.urdf", [0, 0, TABLE_H], useFixedBase=True, physicsClientId=c)
        for j, q in zip(ARM_J, HOME):
            p.resetJointState(self.arm, j, q, physicsClientId=c)
        for f in FINGERS:
            p.resetJointState(self.arm, f, 0.04, physicsClientId=c)
        self.items = []
        for kind, xy in sc["items"]:
            spec = OBJECTS[kind]
            z = TABLE_H + spec["size"]
            if spec["shape"] == "sphere":
                v = p.createVisualShape(p.GEOM_SPHERE, radius=spec["size"], rgbaColor=spec["rgba"], physicsClientId=c)
                cl = p.createCollisionShape(p.GEOM_SPHERE, radius=spec["size"], physicsClientId=c)
            else:
                e = [spec["size"]] * 3
                v = p.createVisualShape(p.GEOM_BOX, halfExtents=e, rgbaColor=spec["rgba"], physicsClientId=c)
                cl = p.createCollisionShape(p.GEOM_BOX, halfExtents=e, physicsClientId=c)
            b = p.createMultiBody(0.1, cl, v, [*xy, z], physicsClientId=c)
            if spec["texture"]:
                p.changeVisualShape(b, -1, textureUniqueId=tex[spec["texture"]], physicsClientId=c)
            self.items.append((kind, b))
        for _ in range(60):
            p.stepSimulation(physicsClientId=c)
        self.grasp = None

    # ------------------------------------------------- sensor interface (shared perception API)
    def camera(self):
        fy = (CAM_H / 2) / math.tan(math.radians(VFOV) / 2)
        return CameraIntrinsics(CAM_W, CAM_H, fy, fy, CAM_W / 2, CAM_H / 2, self.pitch, (0.0, 0.0, 0.0))

    def get_pose(self):
        return Pose(EYE.copy(), self.yaw, np.zeros(3))

    def _render(self):
        if self._ft == self.t:
            return
        cy, sy = math.cos(self.yaw), math.sin(self.yaw)
        pt = math.radians(self.pitch)
        fwd = np.array([cy * math.cos(pt), sy * math.cos(pt), math.sin(pt)])
        right = np.array([sy, -cy, 0])
        view = p.computeViewMatrix(EYE.tolist(), (EYE + fwd).tolist(), np.cross(right, fwd).tolist())
        L = self.light
        _, _, rgba, depth, seg = p.getCameraImage(CAM_W, CAM_H, view, self.proj, lightDirection=L["direction"],
                                                  lightColor=L["color"], lightAmbientCoeff=L["ambient"],
                                                  lightDiffuseCoeff=L["diffuse"], lightSpecularCoeff=L["specular"],
                                                  shadow=1, renderer=p.ER_TINY_RENDERER, physicsClientId=self.cid)
        self._rgb = np.asarray(rgba, np.uint8).reshape(CAM_H, CAM_W, 4)[..., :3].copy()
        d = np.asarray(depth, np.float32).reshape(CAM_H, CAM_W)
        self._depth = FAR * NEAR / (FAR - (FAR - NEAR) * d)
        self._seg = np.asarray(seg, np.int32).reshape(CAM_H, CAM_W)
        self._ft = self.t

    def get_rgb(self):
        self._render()
        return self._rgb

    def get_depth(self):
        self._render()
        return self._depth

    def visible_pixels(self, bid):
        self._render()
        return int((self._seg == bid).sum())

    def gt(self):
        objs = [(k, b, np.array(p.getBasePositionAndOrientation(b, physicsClientId=self.cid)[0])) for k, b in self.items]
        return dict(pos=EYE.copy(), objects=objs)

    def scene_image(self, eye, target, w=960, h=540, fov=50):
        view = p.computeViewMatrix(list(eye), list(target), [0, 0, 1])
        proj = p.computeProjectionMatrixFOV(fov, w / h, 0.05, 20)
        L = self.light
        _, _, rgba, _, _ = p.getCameraImage(w, h, view, proj, lightDirection=L["direction"], lightColor=L["color"],
                                            lightAmbientCoeff=L["ambient"], lightDiffuseCoeff=L["diffuse"],
                                            shadow=1, renderer=p.ER_TINY_RENDERER, physicsClientId=self.cid)
        return np.asarray(rgba, np.uint8).reshape(h, w, 4)[..., :3].copy()

    # ------------------------------------------------------- embodiment adapter
    def ee_pos(self):
        return np.array(p.getLinkState(self.arm, EE, physicsClientId=self.cid)[0])

    def move_to(self, xyz, steps=240, record=None):
        """Adapter: Cartesian target -> IK joint angles -> joint position control."""
        orn = p.getQuaternionFromEuler([math.pi, 0, 0])
        q = p.calculateInverseKinematics(self.arm, EE, list(xyz), orn, maxNumIterations=200, residualThreshold=1e-4,
                                         physicsClientId=self.cid)
        p.setJointMotorControlArray(self.arm, ARM_J, p.POSITION_CONTROL, targetPositions=list(q[:7]),
                                    forces=[200] * 7, physicsClientId=self.cid)
        for i in range(steps):
            p.stepSimulation(physicsClientId=self.cid)
            self.t += 1 / 240
            if record and i % 24 == 0:
                record(self)
        return float(np.linalg.norm(self.ee_pos() - np.asarray(xyz)))

    def gripper(self, open_):
        p.setJointMotorControlArray(self.arm, FINGERS, p.POSITION_CONTROL, targetPositions=[0.04 if open_ else 0.0] * 2,
                                    forces=[40, 40], physicsClientId=self.cid)
        for _ in range(60):
            p.stepSimulation(physicsClientId=self.cid)
            self.t += 1 / 240

    def try_grasp(self):
        ee = self.ee_pos()
        best = None
        for k, b in self.items:
            pos = np.array(p.getBasePositionAndOrientation(b, physicsClientId=self.cid)[0])
            d = np.linalg.norm(pos - (ee - np.array([0, 0, 0.0])))
            if d < 0.03 and (best is None or d < best[0]):
                best = (d, k, b)
        if best:
            self.grasp = (best[1], best[2], p.createConstraint(self.arm, EE, best[2], -1, p.JOINT_FIXED, [0, 0, 0],
                                                              [0, 0, 0], [0, 0, 0], physicsClientId=self.cid))
        return best


def run_arm_episode(sim, sc, perception, record=None, frames=6):
    """Perceive (fuse a few frames) -> choose target -> pre-grasp -> descend -> close -> lift."""
    from .perception import Timer
    sim.reset(sc, sc["seed"])
    if hasattr(perception, "reset"):
        perception.reset()
    pose = sim.get_pose()
    target = sc["target"]
    cands, lat = [], []
    for _ in range(frames):
        sim.t += 0.05
        sim.get_rgb()  # camera capture is not inference latency
        with Timer() as tm:
            dets = perception.detect(sim, pose, target)
        lat.append(tm.ms)
        cands += [d for d in dets if d.label == target]
    res = dict(task=sc["task"], seed=sc["seed"], embodiment="arm", perception=perception.name,
               lat_med=float(np.median(lat)), vlm_calls=getattr(perception, "vlm_calls", 0))
    g = sim.gt()
    true_t = [q for k, _, q in g["objects"] if k == target][0]
    if not cands:
        res.update(success=False, picked=None, reach_err=None, est_err=None, outcome="not_found")
        return res
    # cluster candidates, take the most supported one
    best = max(cands, key=lambda d: (sum(np.linalg.norm(c.pos - d.pos) < 0.05 for c in cands), d.conf))
    group = [c.pos for c in cands if np.linalg.norm(c.pos - best.pos) < 0.05]
    est = np.mean(group, axis=0)
    res["est_err"] = round(float(np.linalg.norm(est - true_t)), 4)
    res["aimed_at"] = min(g["objects"], key=lambda o: np.linalg.norm(o[2] - est))[0]
    sim.gripper(True)
    sim.move_to(est + np.array([0, 0, 0.15]), record=record)
    err = sim.move_to(est + np.array([0, 0, 0.0]), steps=200, record=record)
    res["reach_err"] = round(float(np.linalg.norm(sim.ee_pos() - true_t)), 4)
    grabbed = sim.try_grasp()
    sim.gripper(False)
    sim.move_to(est + np.array([0, 0, 0.2]), record=record)
    if grabbed is None:
        res.update(success=False, picked=None, outcome="missed")
    else:
        k, b = grabbed[1], grabbed[2]
        z = p.getBasePositionAndOrientation(b, physicsClientId=sim.cid)[0][2]
        res.update(picked=k, lifted=bool(z > TABLE_H + 0.1), success=bool(k == target and z > TABLE_H + 0.1),
                   outcome="picked_target" if k == target else "picked_wrong")
    return res
