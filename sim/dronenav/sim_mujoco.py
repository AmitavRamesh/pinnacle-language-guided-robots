"""MuJoCo implementation of SimAdapter.

Differences from the PyBullet model (deliberate, for the cross-simulator study):
- full 6-DOF rigid-body quadrotor: the body tilts to accelerate, thrust acts
  along body z, attitude is held by a geometric (SO(3)) PD controller,
  thrust/torque have a first-order motor lag;
- the camera is rigidly fixed to the body (no gimbal), so it pitches/rolls
  with the drone;
- MuJoCo's OpenGL renderer (different lighting/material model, shadows).
The same velocity-loop gains and flight-controller failsafe as PyBullet are used.
"""
from __future__ import annotations

import math

import mujoco
import numpy as np

from .adapter import RANGE_MAX, ring_bearings, CameraIntrinsics, Pose, SimAdapter
from .scenarios import OBJECTS
from .textures import ensure_textures

PHYS_DT = 0.002
MASS = 0.35
G = 9.81
TAU_V = 0.35
A_MAX_XY, A_MAX_Z = 3.0, 2.5
TAU_MOTOR = 0.03
YAW_RATE_MAX = 1.5
HOVER_TIMEOUT, LAND_TIMEOUT = 0.5, 3.0
CAM_W, CAM_H, CAM_VFOV, CAM_PITCH = 320, 240, 60.0, -15.0
BODY_HALF = (0.12, 0.12, 0.04)
SENSOR_OFFSET = 0.13
I_DIAG = np.array([MASS / 12 * ((2 * BODY_HALF[1]) ** 2 + (2 * BODY_HALF[2]) ** 2),
                   MASS / 12 * ((2 * BODY_HALF[0]) ** 2 + (2 * BODY_HALF[2]) ** 2),
                   MASS / 12 * ((2 * BODY_HALF[0]) ** 2 + (2 * BODY_HALF[1]) ** 2)])
WN, ZETA = np.array([25.0, 25.0, 8.0]), 0.9
K_R = WN**2 * I_DIAG
K_W = 2 * ZETA * WN * I_DIAG


def _vee(M):
    return np.array([M[2, 1], M[0, 2], M[1, 0]])


def _quat_to_R(q):
    R = np.zeros(9)
    mujoco.mju_quat2Mat(R, q)
    return R.reshape(3, 3)


class MuJoCoSim(SimAdapter):
    name = "mujoco"

    def __init__(self):
        self.tex_paths = ensure_textures()
        fy = (CAM_H / 2) / math.tan(math.radians(CAM_VFOV) / 2)
        self._cam = CameraIntrinsics(CAM_W, CAM_H, fy, fy, CAM_W / 2, CAM_H / 2, CAM_PITCH, (SENSOR_OFFSET, 0, 0))
        self.renderer = None

    # ------------------------------------------------------------------ build
    def _xml(self, sc):
        L = sc["light"]
        dvec = -np.asarray(L["direction"], float)
        dvec /= np.linalg.norm(dvec)
        col = np.asarray(L["color"])
        half = sc["room"] / 2
        a = []
        a.append(f'''<mujoco model="room"><option timestep="{PHYS_DT}" gravity="0 0 -{G}"/>
<visual><headlight ambient="{L['ambient']*0.6:.2f} {L['ambient']*0.6:.2f} {L['ambient']*0.6:.2f}" diffuse="0.15 0.15 0.15" specular="0 0 0"/>
<quality shadowsize="2048"/><global offwidth="{CAM_W}" offheight="{CAM_H}"/></visual>
<asset>
<texture name="floor" type="2d" builtin="checker" rgb1="1 1 1" rgb2="0.68 0.78 0.95" width="256" height="256"/>
<material name="floor" texture="floor" texrepeat="6 6"/>''')
        for k, pth in self.tex_paths.items():
            a.append(f'<texture name="{k}" type="cube" file="{pth}"/><material name="{k}" texture="{k}"/>')
        a.append('</asset><worldbody>')
        a.append(f'<light directional="true" dir="{dvec[0]:.3f} {dvec[1]:.3f} {dvec[2]:.3f}" pos="0 0 4" '
                 f'diffuse="{col[0]*L["diffuse"]*1.6:.2f} {col[1]*L["diffuse"]*1.6:.2f} {col[2]*L["diffuse"]*1.6:.2f}" '
                 f'specular="{L["specular"]:.2f} {L["specular"]:.2f} {L["specular"]:.2f}" castshadow="true"/>')
        a.append(f'<light directional="false" pos="0 0 2.5" dir="0 0 -1" diffuse="{col[0]*L["ambient"]*0.5:.2f} '
                 f'{col[1]*L["ambient"]*0.5:.2f} {col[2]*L["ambient"]*0.5:.2f}" castshadow="false"/>')
        a.append(f'<geom name="floor" type="plane" size="{half+1} {half+1} 0.1" material="floor"/>')
        for i, (xy, ext) in enumerate([((half, 0), (0.05, half, 1.3)), ((-half, 0), (0.05, half, 1.3)),
                                       ((0, half), (half, 0.05, 1.3)), ((0, -half), (half, 0.05, 1.3))]):
            a.append(f'<geom name="wall{i}" type="box" size="{ext[0]} {ext[1]} {ext[2]}" pos="{xy[0]} {xy[1]} 1.3" rgba="0.82 0.82 0.8 1"/>')
        for i, t in enumerate(sc["tables"]):
            h, s = t["height"], t["size"] / 2
            a.append(f'<geom name="table{i}" type="box" size="{s} {s} {h/2}" pos="{t["xy"][0]} {t["xy"][1]} {h/2}" rgba="0.45 0.3 0.18 1"/>')
            spec = OBJECTS[t["item"]]
            z = h + spec["size"]
            mat = f'material="{spec["texture"]}"' if spec["texture"] else f'rgba="{" ".join(map(str, spec["rgba"]))}"'
            if spec["shape"] == "sphere":
                a.append(f'<geom name="item{i}" type="sphere" size="{spec["size"]}" pos="{t["xy"][0]} {t["xy"][1]} {z}" {mat}/>')
            else:
                e = spec["size"]
                a.append(f'<geom name="item{i}" type="box" size="{e} {e} {e}" pos="{t["xy"][0]} {t["xy"][1]} {z}" {mat}/>')
        for i, o in enumerate(sc["obstacles"]):
            if o["type"] == "cyl":
                a.append(f'<geom name="obs{i}" type="cylinder" size="{o["size"]} {o["height"]/2}" '
                         f'pos="{o["xy"][0]} {o["xy"][1]} {o["height"]/2}" rgba="0.55 0.6 0.7 1"/>')
            else:
                yaw = o.get("yaw", 0) + math.pi / 2
                a.append(f'<geom name="obs{i}" type="box" size="{o["size"][0]/2} {o["size"][1]/2} {o["height"]/2}" '
                         f'pos="{o["xy"][0]} {o["xy"][1]} {o["height"]/2}" euler="0 0 {yaw}" rgba="0.7 0.68 0.6 1"/>')
        sx, sy, sz = sc["start"]
        sz = max(sz, BODY_HALF[2] + 0.005)
        p = math.radians(CAM_PITCH)
        a.append(f'''<body name="drone" pos="{sx} {sy} {sz}" euler="0 0 {sc["start_yaw"]}"><freejoint/>
<geom name="dbody" type="box" size="{BODY_HALF[0]} {BODY_HALF[1]} {BODY_HALF[2]}" mass="{MASS}" rgba="0.15 0.15 0.18 1"/>
<camera name="fpv" pos="{SENSOR_OFFSET} 0 0" xyaxes="0 -1 0 {-math.sin(p):.4f} 0 {math.cos(p):.4f}" fovy="{CAM_VFOV}"/>
</body></worldbody></mujoco>''')
        return "\n".join(a)

    def reset(self, scenario, seed):
        self.sc = scenario
        self.m = mujoco.MjModel.from_xml_string(self._xml(scenario))
        self.d = mujoco.MjData(self.m)
        mujoco.mj_forward(self.m, self.d)
        if self.renderer is not None:
            self.renderer.close()
        self.renderer = mujoco.Renderer(self.m, CAM_H, CAM_W)
        gid = lambda n: mujoco.mj_name2id(self.m, mujoco.mjtObj.mjOBJ_GEOM, n)
        self.bid = mujoco.mj_name2id(self.m, mujoco.mjtObj.mjOBJ_BODY, "drone")
        self.dgeom = gid("dbody")
        self.floor = gid("floor")
        self.items = []
        self.target_table = None
        for i, t in enumerate(scenario["tables"]):
            g = gid(f"item{i}")
            self.items.append((t["item"], g, self.d.geom_xpos[g].copy()))
            if t["item"] == "orange":
                self.target_table = gid(f"table{i}")
        self.obstacle_geoms = [g for g in range(self.m.ngeom) if g not in (self.dgeom, self.floor)]
        self.rng = np.random.default_rng(seed + 1000)
        self.noise, self.light = scenario["noise"], scenario["light"]
        self.bearings = ring_bearings(scenario.get("ring_rays", 8))
        self.cmd = np.zeros(4)
        self.t = self.last_cmd_t = 0.0
        self.mode = "OFFBOARD"
        self.yaw_sp = scenario["start_yaw"]
        self.thrust = 0.0
        self.torque = np.zeros(3)
        self.drift = np.zeros(3)
        self.gust = np.zeros(3)
        self.collisions, self._in_contact = 0, False
        self._frame_t = -1.0
        self.max_tilt = 0.0

    # ------------------------------------------------------------- dynamics
    def send_velocity(self, vx, vy, vz, yaw_rate):
        self.cmd = np.array([vx, vy, vz, yaw_rate], float)
        self.last_cmd_t = self.t

    def _R(self):
        return _quat_to_R(self.d.qpos[3:7])

    def step(self):
        m, d = self.m, self.d
        n = round(self.dt_control / PHYS_DT)
        for _ in range(n):
            age = self.t - self.last_cmd_t
            pos = d.qpos[:3]
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
            if self.mode == "LANDING" and pos[2] < BODY_HALF[2] + 0.02:
                self.mode = "LANDED"
            R = self._R()
            v = d.qvel[:3].copy()
            w = d.qvel[3:6].copy()  # body-frame angular velocity
            if self.mode == "LANDED":
                d.xfrc_applied[self.bid] = 0
                mujoco.mj_step(m, d)
                self.t += PHYS_DT
                continue
            a_des = (cmd[:3] - v) / TAU_V
            nxy = np.linalg.norm(a_des[:2])
            if nxy > A_MAX_XY:
                a_des[:2] *= A_MAX_XY / nxy
            a_des[2] = np.clip(a_des[2], -A_MAX_Z, A_MAX_Z)
            if self.noise["gust"] > 0:
                self.gust += -self.gust * PHYS_DT / 1.5 + self.rng.normal(0, self.noise["gust"] * 0.08, 3) * math.sqrt(PHYS_DT)
                self.gust[2] *= 0.3
            F = MASS * (a_des + np.array([0, 0, G]))
            # attitude setpoint from desired force direction + yaw setpoint
            self.yaw_sp += np.clip(cmd[3], -YAW_RATE_MAX, YAW_RATE_MAX) * PHYS_DT
            zb = F / np.linalg.norm(F)
            xc = np.array([math.cos(self.yaw_sp), math.sin(self.yaw_sp), 0])
            yb = np.cross(zb, xc)
            yb /= np.linalg.norm(yb)
            xb = np.cross(yb, zb)
            Rd = np.column_stack([xb, yb, zb])
            eR = 0.5 * _vee(Rd.T @ R - R.T @ Rd)
            tau_cmd = -K_R * eR - K_W * w + np.cross(w, I_DIAG * w)
            T_cmd = float(F @ R[:, 2])
            # motor lag
            self.thrust += (T_cmd - self.thrust) * PHYS_DT / TAU_MOTOR
            self.torque += (tau_cmd - self.torque) * PHYS_DT / TAU_MOTOR
            force_w = self.thrust * R[:, 2] - 0.05 * v + MASS * self.gust
            d.xfrc_applied[self.bid, :3] = force_w
            d.xfrc_applied[self.bid, 3:] = R @ self.torque
            mujoco.mj_step(m, d)
            self.t += PHYS_DT
            self.max_tilt = max(self.max_tilt, math.degrees(math.acos(np.clip(R[2, 2], -1, 1))))
        # collisions (events)
        hit = False
        for i in range(d.ncon):
            c = d.contact[i]
            if self.dgeom in (c.geom1, c.geom2) and self.floor not in (c.geom1, c.geom2):
                hit = True
        if hit and not self._in_contact:
            self.collisions += 1
        self._in_contact = hit
        if self.noise["pose"] > 0:
            v = d.qvel[:3]
            self.drift += self.rng.normal(0, 1, 3) * self.noise["pose"] * np.abs(v) * self.dt_control
            self.drift[2] *= 0.5

    def time(self):
        return self.t

    def fc_mode(self):
        return self.mode

    # ---------------------------------------------------------------- sensors
    def _yaw(self, R):
        return math.atan2(R[1, 0], R[0, 0])

    def get_pose(self):
        R = self._R()
        return Pose(self.d.qpos[:3].copy() + self.drift, self._yaw(R), self.d.qvel[:3].copy(), rot=R)

    def camera(self):
        return self._cam

    def _render(self):
        if self._frame_t == self.t:
            return
        r = self.renderer
        r.disable_depth_rendering()
        r.disable_segmentation_rendering()
        r.update_scene(self.d, "fpv")
        self._rgb = r.render().copy()
        r.enable_depth_rendering()
        r.update_scene(self.d, "fpv")
        z = r.render().copy().astype(np.float32)
        r.disable_depth_rendering()
        if self.noise["depth"] > 0:
            z = z * (1 + self.rng.normal(0, self.noise["depth"], z.shape).astype(np.float32))
        self._depth = z
        r.enable_segmentation_rendering()
        r.update_scene(self.d, "fpv")
        seg = r.render()
        r.disable_segmentation_rendering()
        self._seg = np.where(seg[..., 1] == int(mujoco.mjtObj.mjOBJ_GEOM), seg[..., 0], -1)
        self._frame_t = self.t

    def get_rgb(self):
        self._render()
        return self._rgb

    def get_depth(self):
        self._render()
        return self._depth

    def get_ranges(self):
        n_ring = len(self.bearings)
        R = self._R()
        pos = self.d.qpos[:3]
        yaw = self._yaw(R)
        dirs = [np.array([math.cos(yaw + b), math.sin(yaw + b), 0]) for b in self.bearings]
        dirs += [-R[:, 2], R[:, 2]]  # down/up sensors are body-fixed
        out = []
        gid = np.zeros(1, np.int32)
        for i, dv in enumerate(dirs):
            off = SENSOR_OFFSET if i < n_ring else BODY_HALF[2] + 0.01
            s = pos + dv * off
            dist = mujoco.mj_ray(self.m, self.d, s, dv / np.linalg.norm(dv), None, 1, self.bid, gid)
            out.append(RANGE_MAX if dist < 0 or dist > RANGE_MAX else dist)
        r = np.array(out)
        if self.noise["range"] > 0:
            r = np.clip(r + self.rng.normal(0, self.noise["range"], r.shape), 0, RANGE_MAX)
        return {"ring": r[:n_ring], "down": float(r[n_ring]), "up": float(r[n_ring + 1]), "bearings": self.bearings}

    def gt(self):
        R = self._R()
        tgt = [it for it in self.items if it[0] == "orange"]
        tgt_ids = {self.target_table} | {it[1] for it in tgt}
        clear, clear_tgt = RANGE_MAX, RANGE_MAX
        ft = np.zeros(6)
        for g in self.obstacle_geoms:
            dist = mujoco.mj_geomDistance(self.m, self.d, self.dgeom, g, 2.0, ft)
            if g in tgt_ids:
                clear_tgt = min(clear_tgt, dist)
            else:
                clear = min(clear, dist)
        return dict(pos=self.d.qpos[:3].copy(), vel=self.d.qvel[:3].copy(), yaw=self._yaw(R),
                    target=tgt[0][2] if tgt else None, target_id=tgt[0][1] if tgt else None,
                    distractors=[(k, p) for k, _, p in self.items if k != "orange"],
                    clearance=clear, clearance_target=clear_tgt, collisions=self.collisions, mode=self.mode)

    def visible_pixels(self, geom_id):
        self._render()
        return int((self._seg == geom_id).sum())

    def close(self):
        if self.renderer is not None:
            self.renderer.close()
