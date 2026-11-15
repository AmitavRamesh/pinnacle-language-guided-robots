"""Extended PyBullet world (Phase 1b-2): drone or ground robot, multi-room house,
landing pads, tiltable camera gimbal, visual robot models and third-person scene cameras.

Embodiment layer (the 'lightweight adapter'): both robots accept the SAME world-frame
velocity setpoint (vx, vy, vz, yaw_rate) from the shared planner.
- drone: translational dynamics as in sim_pybullet (velocity loop + attitude lag) + FC fail-safe
- ground: differential-drive (unicycle) adapter -> forward speed v and turn rate w,
          no lateral motion, vz ignored. Same fail-safe (stop instead of land).
"""
from __future__ import annotations

import math

import numpy as np
import pybullet as p
import pybullet_data

from .adapter import RANGE_MAX, CameraIntrinsics, Pose, SimAdapter, ring_bearings
from .scenarios import OBJECTS
from .textures import ensure_pad_textures, ensure_textures
from .world_scenarios import EMBODIMENT

PHYS_DT = 1 / 240
G = 9.81
TAU_V, TAU_ATT = 0.35, 0.08
A_MAX_XY, A_MAX_Z = 3.0, 2.5
HOVER_TIMEOUT, LAND_TIMEOUT = 0.5, 3.0
CAM_W, CAM_H, CAM_VFOV = 320, 240, 60.0
NEAR, FAR = 0.05, 14.0
GROUND_V_MAX, GROUND_W_MAX, GROUND_TAU = 0.6, 1.2, 0.3
HIDE = [0, 0, -50]
PAD_R = 0.32
PAD_OBJ = str(__import__("pathlib").Path(__file__).resolve().parent.parent / "assets" / "pad.obj")


def _q(yaw, roll=0.0, pitch=0.0):
    return p.getQuaternionFromEuler([roll, pitch, yaw])


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


class WorldSim(SimAdapter):
    name = "pybullet-world"

    def __init__(self, gui=False):
        self.cid = p.connect(p.GUI if gui else p.DIRECT)
        p.setAdditionalSearchPath(pybullet_data.getDataPath(), physicsClientId=self.cid)
        self.tex_paths = ensure_textures()
        self.pad_paths = ensure_pad_textures()
        self._proj = p.computeProjectionMatrixFOV(CAM_VFOV, CAM_W / CAM_H, NEAR, FAR)

    # ------------------------------------------------------------------ build
    def _box(self, ext, pos, rgba, yaw=0.0, tex=None):
        c = self.cid
        vis = p.createVisualShape(p.GEOM_BOX, halfExtents=ext, rgbaColor=rgba, physicsClientId=c)
        col = p.createCollisionShape(p.GEOM_BOX, halfExtents=ext, physicsClientId=c)
        b = p.createMultiBody(0, col, vis, pos, _q(yaw), physicsClientId=c)
        if tex is not None:
            p.changeVisualShape(b, -1, textureUniqueId=tex, physicsClientId=c)
        return b

    def _drone_visual(self):
        """Procedural 3.5-inch ducted quadrotor (visual only, no collision)."""
        c = self.cid
        # central body + battery + camera
        vs = [p.createVisualShape(p.GEOM_BOX, halfExtents=[0.06, 0.035, 0.018], rgbaColor=[0.12, 0.12, 0.14, 1], physicsClientId=c)]
        fr = [[0, 0, 0]]
        fo = [[0, 0, 0, 1]]
        def a(kind, rgba, pos, orn=(0, 0, 0), **kw):
            vs.append(p.createVisualShape(kind, rgbaColor=rgba, physicsClientId=c, **kw))
            fr.append(list(pos))
            fo.append(list(p.getQuaternionFromEuler(orn)))
        a(p.GEOM_BOX, [0.85, 0.35, 0.1, 1], (-0.01, 0, 0.028), halfExtents=[0.04, 0.025, 0.012])  # battery
        a(p.GEOM_BOX, [0.05, 0.05, 0.05, 1], (0.07, 0, 0.0), halfExtents=[0.012, 0.016, 0.014])  # camera
        a(p.GEOM_SPHERE, [0.2, 0.5, 0.9, 1], (0.083, 0, 0.0), radius=0.008)  # lens
        for i, ang in enumerate([45, 135, 225, 315]):
            r = math.radians(ang)
            mx, my = 0.11 * math.cos(r), 0.11 * math.sin(r)
            a(p.GEOM_BOX, [0.15, 0.15, 0.17, 1], (mx / 2, my / 2, 0), (0, 0, r), halfExtents=[0.055, 0.009, 0.006])  # arm
            a(p.GEOM_CYLINDER, [0.25, 0.25, 0.28, 1], (mx, my, 0.012), radius=0.014, length=0.022)  # motor
            a(p.GEOM_CYLINDER, [0.9, 0.9, 0.95, 0.55] if i < 2 else [0.95, 0.4, 0.2, 0.55], (mx, my, 0.026),
              radius=0.045, length=0.003)  # prop disc (front props white, rear orange)
            a(p.GEOM_CYLINDER, [0.1, 0.1, 0.12, 1], (mx, my, 0.02), radius=0.05, length=0.03)  # duct (drawn as ring-ish)
        links_vis = vs[1:]
        body = p.createMultiBody(baseMass=0, baseCollisionShapeIndex=-1, baseVisualShapeIndex=vs[0],
                                 basePosition=HIDE,
                                 linkMasses=[0] * len(links_vis), linkCollisionShapeIndices=[-1] * len(links_vis),
                                 linkVisualShapeIndices=links_vis, linkPositions=fr[1:], linkOrientations=fo[1:],
                                 linkInertialFramePositions=[[0, 0, 0]] * len(links_vis),
                                 linkInertialFrameOrientations=[[0, 0, 0, 1]] * len(links_vis),
                                 linkParentIndices=[0] * len(links_vis), linkJointTypes=[p.JOINT_FIXED] * len(links_vis),
                                 linkJointAxis=[[0, 0, 1]] * len(links_vis), physicsClientId=c)
        return body

    def reset(self, sc, seed):
        c = self.cid
        p.resetSimulation(physicsClientId=c)
        p.setGravity(0, 0, -G, physicsClientId=c)
        p.setTimeStep(PHYS_DT, physicsClientId=c)
        self.sc, self.emb = sc, sc["embodiment"]
        E = EMBODIMENT[self.emb]
        self.body_half = E["body"]
        self.rng = np.random.default_rng(seed + 1000)
        self.textures = {k: p.loadTexture(v, physicsClientId=c) for k, v in self.tex_paths.items()}
        self.pad_tex = {k: p.loadTexture(v, physicsClientId=c) for k, v in self.pad_paths.items()}
        self.plane = p.loadURDF("plane.urdf", physicsClientId=c)
        self.static_ids, self.items, self.pads = [], [], []
        self.table_of = {}
        half = sc["room"] / 2
        for xy, ext in [((half, 0), (0.05, half, 1.3)), ((-half, 0), (0.05, half, 1.3)),
                        ((0, half), (half, 0.05, 1.3)), ((0, -half), (half, 0.05, 1.3))]:
            self.static_ids.append(self._box(ext, (xy[0], xy[1], 1.3), [0.82, 0.82, 0.8, 1]))
        for w in sc.get("walls", []):
            self.static_ids.append(self._box((w["ext"][0], w["ext"][1], w["height"] / 2), (*w["xy"], w["height"] / 2),
                                             [0.78, 0.74, 0.66, 1]))
        for t in sc["tables"]:
            h, s = t["height"], t["size"] / 2
            tb = self._box((s, s, h / 2), (*t["xy"], h / 2), [0.45, 0.3, 0.18, 1])
            self.static_ids.append(tb)
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
            self.table_of[bid] = tb
        for pd in sc.get("pads", []):
            vis = p.createVisualShape(p.GEOM_MESH, fileName=PAD_OBJ, meshScale=[2 * PAD_R, 2 * PAD_R, 1],
                                      rgbaColor=[1, 1, 1, 1], physicsClientId=c)
            bid = p.createMultiBody(0, -1, vis, [*pd["xy"], 0.004], _q(pd["yaw"]), physicsClientId=c)
            p.changeVisualShape(bid, -1, textureUniqueId=self.pad_tex[pd["kind"]], physicsClientId=c)
            self.pads.append((pd["kind"], bid, np.array([*pd["xy"], 0.004])))
        for o in sc["obstacles"]:
            if o["type"] == "cyl":
                vis = p.createVisualShape(p.GEOM_CYLINDER, radius=o["size"], length=o["height"], rgbaColor=[0.55, 0.6, 0.7, 1], physicsClientId=c)
                col = p.createCollisionShape(p.GEOM_CYLINDER, radius=o["size"], height=o["height"], physicsClientId=c)
                self.static_ids.append(p.createMultiBody(0, col, vis, [*o["xy"], o["height"] / 2], physicsClientId=c))
            else:
                ext = (o["size"][0] / 2, o["size"][1] / 2, o["height"] / 2)
                self.static_ids.append(self._box(ext, (*o["xy"], o["height"] / 2), [0.7, 0.68, 0.6, 1], yaw=o.get("yaw", 0) + math.pi / 2))
        # physics body (invisible) + visual model that follows it
        col = p.createCollisionShape(p.GEOM_BOX, halfExtents=self.body_half, physicsClientId=c)
        start = list(sc["start"])
        if self.emb == "ground":
            start[2] = self.body_half[2] + 0.02
            self.body = p.createMultiBody(5.0, col, -1, start, _q(sc["start_yaw"]), physicsClientId=c)
            self.model = p.loadURDF("husky/husky.urdf", HIDE, globalScaling=0.6, useFixedBase=True, physicsClientId=c)
            self.model_z = -0.12
        else:
            self.body = p.createMultiBody(0.35, col, -1, start, _q(sc["start_yaw"]), physicsClientId=c)
            self.model = self._drone_visual()
            self.model_z = 0.0
        for j in range(-1, p.getNumJoints(self.model, physicsClientId=c)):
            p.setCollisionFilterGroupMask(self.model, j, 0, 0, physicsClientId=c)
            if self.emb == "ground":
                nm = p.getJointInfo(self.model, j, physicsClientId=c)[12].decode() if j >= 0 else "base"
                col_ = [0.12, 0.12, 0.12, 1] if "wheel" in nm else [0.95, 0.72, 0.08, 1]
                p.changeVisualShape(self.model, j, rgbaColor=col_, physicsClientId=c)
        p.changeVisualShape(self.body, -1, rgbaColor=[1, 1, 1, 0], physicsClientId=c)
        p.changeDynamics(self.body, -1, linearDamping=0, angularDamping=0, lateralFriction=0.0, physicsClientId=c)
        self.yaw, self.yaw_rate, self.a_act = sc["start_yaw"], 0.0, np.zeros(3)
        self.v_fwd, self.w = 0.0, 0.0
        self.cmd, self.t, self.last_cmd_t, self.mode = np.zeros(4), 0.0, 0.0, "OFFBOARD"
        self.drift, self.gust = np.zeros(3), np.zeros(3)
        self.collisions, self._in_contact, self._frame_t = 0, False, -1.0
        self.bearings = ring_bearings(sc.get("ring_rays", 8))
        hx, hy = self.body_half[0], self.body_half[1]
        self.ray_off = np.array([min(hx / max(abs(math.cos(b)), 1e-6), hy / max(abs(math.sin(b)), 1e-6)) + 0.01
                                 for b in self.bearings])
        self.noise, self.light = sc["noise"], sc["light"]
        self.cam_pitch = sc.get("cam_pitch", EMBODIMENT[self.emb]["cam_pitch"])
        self.cam_offset = EMBODIMENT[self.emb]["cam_offset"]
        self._place_model()

    def _place_model(self):
        pos, _ = p.getBasePositionAndOrientation(self.body, physicsClientId=self.cid)
        p.resetBasePositionAndOrientation(self.model, [pos[0], pos[1], pos[2] + self.model_z], _q(self.yaw), physicsClientId=self.cid)

    # ----------------------------------------------------------- embodiment
    def set_gimbal(self, pitch_deg):
        self.cam_pitch = float(np.clip(pitch_deg, -90, 20))
        self._frame_t = -1

    def send_velocity(self, vx, vy, vz, yaw_rate):
        self.cmd = np.array([vx, vy, vz, yaw_rate], float)
        self.last_cmd_t = self.t

    def ground_adapter(self, cmd):
        """World-frame (vx, vy, vz, yaw_rate) -> differential drive (v, w). The whole
        embodiment-specific translation for the ground robot is these few lines."""
        v = np.asarray(cmd[:2])
        sp = float(np.linalg.norm(v))
        if sp < 0.05:
            return 0.0, float(np.clip(cmd[3], -GROUND_W_MAX, GROUND_W_MAX))
        err = wrap(math.atan2(v[1], v[0]) - self.yaw)
        w = float(np.clip(2.5 * err, -GROUND_W_MAX, GROUND_W_MAX))
        fwd = min(sp, GROUND_V_MAX) * max(0.0, math.cos(err)) ** 2
        return fwd, w

    def step(self):
        c = self.cid
        for _ in range(round(self.dt_control / PHYS_DT)):
            age = self.t - self.last_cmd_t
            pos, _ = p.getBasePositionAndOrientation(self.body, physicsClientId=c)
            if self.mode == "LANDED":
                cmd = np.zeros(4)
            elif age > LAND_TIMEOUT or self.mode == "LANDING":
                self.mode = "LANDING"
                cmd = np.array([0, 0, -0.35, 0])
            elif age > HOVER_TIMEOUT:
                self.mode = "HOVER_FAILSAFE"
                cmd = np.zeros(4)
            else:
                self.mode = "OFFBOARD"
                cmd = self.cmd
            v = np.array(p.getBaseVelocity(self.body, physicsClientId=c)[0])
            if self.emb == "ground":
                if self.mode in ("LANDING", "LANDED"):
                    self.mode = "LANDED" if self.mode == "LANDING" else self.mode
                    cmd = np.zeros(4)
                fwd, w = self.ground_adapter(cmd)
                self.v_fwd += (fwd - self.v_fwd) * PHYS_DT / GROUND_TAU
                self.w += (w - self.w) * PHYS_DT / 0.15
                self.yaw = wrap(self.yaw + self.w * PHYS_DT)
                vel = [self.v_fwd * math.cos(self.yaw), self.v_fwd * math.sin(self.yaw), min(v[2], 0.0)]
                p.resetBaseVelocity(self.body, vel, [0, 0, self.w], physicsClientId=c)
                p.stepSimulation(physicsClientId=c)
                pos2, _ = p.getBasePositionAndOrientation(self.body, physicsClientId=c)
                p.resetBasePositionAndOrientation(self.body, [pos2[0], pos2[1], max(pos2[2], self.body_half[2] + 0.005)],
                                                  _q(self.yaw), physicsClientId=c)
            else:
                if self.mode == "LANDING" and pos[2] < 0.06:
                    self.mode = "LANDED"
                if self.mode == "LANDED":
                    force = np.zeros(3)
                    self.yaw_rate = 0.0
                else:
                    a_des = (cmd[:3] - v) / TAU_V
                    n = np.linalg.norm(a_des[:2])
                    if n > A_MAX_XY:
                        a_des[:2] *= A_MAX_XY / n
                    a_des[2] = np.clip(a_des[2], -A_MAX_Z, A_MAX_Z)
                    self.a_act += (a_des - self.a_act) * (PHYS_DT / TAU_ATT)
                    force = 0.35 * (self.a_act + np.array([0, 0, G])) - 0.05 * v
                    self.yaw_rate += (np.clip(cmd[3], -1.5, 1.5) - self.yaw_rate) * (PHYS_DT / 0.1)
                self.yaw = wrap(self.yaw + self.yaw_rate * PHYS_DT)
                p.applyExternalForce(self.body, -1, force.tolist(), pos, p.WORLD_FRAME, physicsClientId=c)
                p.stepSimulation(physicsClientId=c)
                pos2, _ = p.getBasePositionAndOrientation(self.body, physicsClientId=c)
                v2 = p.getBaseVelocity(self.body, physicsClientId=c)[0]
                p.resetBasePositionAndOrientation(self.body, pos2, _q(self.yaw), physicsClientId=c)
                p.resetBaseVelocity(self.body, v2, [0, 0, self.yaw_rate], physicsClientId=c)
            self.t += PHYS_DT
        cps = [cp for cp in p.getContactPoints(bodyA=self.body, physicsClientId=c) if cp[2] != self.plane]
        if cps and not self._in_contact:
            self.collisions += 1
        self._in_contact = bool(cps)
        self._place_model()

    def time(self):
        return self.t

    def fc_mode(self):
        return self.mode

    # ---------------------------------------------------------------- sensors
    def _true_pose(self):
        pos, _ = p.getBasePositionAndOrientation(self.body, physicsClientId=self.cid)
        v = p.getBaseVelocity(self.body, physicsClientId=self.cid)[0]
        return np.array(pos), np.array(v)

    def get_pose(self):
        pos, v = self._true_pose()
        return Pose(pos + self.drift, self.yaw, v)

    def camera(self):
        fy = (CAM_H / 2) / math.tan(math.radians(CAM_VFOV) / 2)
        off = self.cam_offset
        return CameraIntrinsics(CAM_W, CAM_H, fy, fy, CAM_W / 2, CAM_H / 2, self.cam_pitch, off)

    def cam_eye(self):
        pos, _ = self._true_pose()
        cy, sy = math.cos(self.yaw), math.sin(self.yaw)
        o = self.cam_offset
        return pos + np.array([cy * o[0] - sy * o[1], sy * o[0] + cy * o[1], o[2]])

    def _view(self, eye, pitch_deg, yaw):
        cy, sy = math.cos(yaw), math.sin(yaw)
        pt = math.radians(pitch_deg)
        fwd = np.array([cy * math.cos(pt), sy * math.cos(pt), math.sin(pt)])
        right = np.array([sy, -cy, 0])
        up = np.cross(right, fwd)
        return p.computeViewMatrix(eye.tolist(), (eye + fwd).tolist(), up.tolist())

    def _render(self):
        if self._frame_t == self.t:
            return
        c = self.cid
        p.resetBasePositionAndOrientation(self.model, HIDE, _q(0), physicsClientId=c)  # don't see own body
        view = self._view(self.cam_eye(), self.cam_pitch, self.yaw)
        L = self.light
        _, _, rgba, depth, seg = p.getCameraImage(CAM_W, CAM_H, view, self._proj, lightDirection=L["direction"],
                                                  lightColor=L["color"], lightAmbientCoeff=L["ambient"],
                                                  lightDiffuseCoeff=L["diffuse"], lightSpecularCoeff=L["specular"],
                                                  shadow=1, renderer=p.ER_TINY_RENDERER, physicsClientId=c)
        self._place_model()
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

    def get_seg(self):
        self._render()
        return self._seg

    def get_ranges(self):
        pos, _ = self._true_pose()
        n = len(self.bearings)
        dirs = [np.array([math.cos(self.yaw + b), math.sin(self.yaw + b), 0]) for b in self.bearings]
        offs = list(self.ray_off)
        dirs += [np.array([0, 0, -1.0]), np.array([0, 0, 1.0])]
        offs += [self.body_half[2] + 0.01] * 2
        starts = [(pos + d * o) for d, o in zip(dirs, offs)]
        res = p.rayTestBatch([s.tolist() for s in starts], [(s + d * RANGE_MAX).tolist() for s, d in zip(starts, dirs)],
                             collisionFilterMask=-1, physicsClientId=self.cid)
        r = np.array([h[2] * RANGE_MAX if h[0] >= 0 and h[0] != self.model else RANGE_MAX for h in res])
        return {"ring": r[:n], "down": float(r[n]), "up": float(r[n + 1]), "bearings": self.bearings}

    # ------------------------------------------------------------ scene cameras
    def scene_image(self, eye, target, w=960, h=540, fov=60, up=(0, 0, 1)):
        view = p.computeViewMatrix(list(eye), list(target), list(up))
        proj = p.computeProjectionMatrixFOV(fov, w / h, 0.05, 30)
        L = self.light
        _, _, rgba, _, _ = p.getCameraImage(w, h, view, proj, lightDirection=L["direction"], lightColor=L["color"],
                                            lightAmbientCoeff=L["ambient"], lightDiffuseCoeff=L["diffuse"],
                                            lightSpecularCoeff=L["specular"], shadow=1, renderer=p.ER_TINY_RENDERER,
                                            physicsClientId=self.cid)
        return np.asarray(rgba, np.uint8).reshape(h, w, 4)[..., :3].copy()

    def chase_image(self, dist=1.5, height=0.7, w=960, h=540, side=0.6):
        """Observer camera placed between the robot and the room centre, looking back at the robot."""
        pos, _ = self._true_pose()
        to_c = -pos[:2] / (np.linalg.norm(pos[:2]) + 1e-6)
        perp = np.array([-to_c[1], to_c[0]])
        xy = pos[:2] + to_c * dist + perp * side
        eye = np.array([xy[0], xy[1], pos[2] + height])
        return self.scene_image(eye, pos + np.array([0, 0, 0.05]), w, h, fov=50)

    # ----------------------------------------------------------- ground truth
    def objects(self):
        """All semantic things in the world: (label, body_id, position)."""
        out = [(k, b, pp) for k, b, pp in self.items]
        out += [("helipad" if k == "H" else f"pad_{k}", b, pp) for k, b, pp in self.pads]
        return out

    def gt(self):
        pos, v = self._true_pose()
        tl = self.sc.get("target", "orange")
        tg = [o for o in self.objects() if o[0] == tl]
        clear = RANGE_MAX
        for bid in self.static_ids:
            for cp in p.getClosestPoints(self.body, bid, 1.0, physicsClientId=self.cid):
                clear = min(clear, cp[8])
        return dict(pos=pos, vel=v, yaw=self.yaw, target=tg[0][2] if tg else None, target_id=tg[0][1] if tg else None,
                    targets=tg, objects=self.objects(), clearance=clear, collisions=self.collisions, mode=self.mode)

    def visible_pixels(self, body_id):
        self._render()
        return int((self._seg == body_id).sum())

    def close(self):
        p.disconnect(self.cid)
