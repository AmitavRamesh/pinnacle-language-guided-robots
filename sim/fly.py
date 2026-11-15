"""Fly the drone yourself (or script it).

Interactive (opens the PyBullet 3D window + a drone-camera window):
  python fly.py --scenario T5 --seed 0 --perception C1

Keys (click the 3D window first):
  Arrow Up/Down    forward / back           Arrow Left/Right  yaw left / right
  , / .            strafe left / right      PageUp / PageDown climb / descend
  a                AUTONOMOUS: run the mission ("find and approach the orange")
  m                MANUAL: take back control (safety-pilot takeover)
  x                toggle LINK LOSS (stop sending setpoints -> FC hovers, then lands)
  f                toggle safety filter ON/OFF (to show what it prevents)
  n                next scenario     r  restart     q / Esc  quit
The safety filter is ON by default in both manual and autonomous mode.

Scripted / headless (saves a contact sheet of camera frames + map):
  python fly.py --headless --script "takeoff; fwd 1.5; yaw 90; auto 40" --out out/fly_session.png
Script verbs: takeoff | fwd M | back M | left M | right M | up M | down M | yaw DEG | hover S |
              auto S | linkloss S | nofilter
"""
from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import dronenav  # noqa: E402,F401  (cache dirs on D:)
import cv2  # noqa: E402
import numpy as np  # noqa: E402
import pybullet as p  # noqa: E402

from dronenav.perception import TargetBelief  # noqa: E402
from dronenav.planner import FLY_Z, Mission, SafetyFilter, depth_obstacles, obstacle_rays  # noqa: E402
from dronenav.scenarios import SCENARIOS, make_scenario  # noqa: E402
from dronenav.sim_pybullet import PyBulletSim  # noqa: E402
from record_demo import draw_map  # noqa: E402
from run_batch import make_perception  # noqa: E402

V, VZ, YR = 0.5, 0.3, 0.8
SCEN_LIST = [s for s in SCENARIOS if s != "T4D"]


class Pilot:
    def __init__(self, gui, scenario, seed, perc_cfg):
        self.sim = PyBulletSim(gui=gui)
        self.gui = gui
        self.perc = make_perception(perc_cfg)
        self.perc_cfg = perc_cfg
        self.load(scenario, seed)

    def load(self, scenario, seed):
        self.sid, self.seed = scenario, seed
        self.sc = make_scenario(scenario, seed)
        self.sc["link_loss"] = None
        self.sim.reset(self.sc, seed)
        if self.gui:
            c = self.sim.cid
            p.configureDebugVisualizer(p.COV_ENABLE_KEYBOARD_SHORTCUTS, 0, physicsClientId=c)
            p.configureDebugVisualizer(p.COV_ENABLE_GUI, 0, physicsClientId=c)
        self.belief = TargetBelief()
        self.mission = Mission(standoff=self.sc["standoff"], time_budget=1e9, start_xy=self.sc["start"][:2])
        self.safety = SafetyFilter()
        self.mode = "MANUAL"
        self.link = True
        self.filter_on = True
        self.depth_obs = self.depth_raw = []
        self.dets = []
        self.next_cam = 0.0
        self.traj = []
        self.events = []
        self.t_mode = 0.0

    def set_mode(self, m):
        if m != self.mode:
            self.events.append((round(self.sim.time(), 1), f"{self.mode}->{m}"))
            self.mode = m
            if m == "AUTO":
                self.mission = Mission(standoff=self.sc["standoff"], time_budget=1e9, start_xy=self.pose().pos[:2])
                if self.pose().pos[2] > FLY_Z - 0.15:
                    self.mission._set("SEARCH_SPIN", self.sim.time())

    def pose(self):
        return self.sim.get_pose()

    def tick(self, manual_body=(0, 0, 0, 0)):
        """manual_body: (forward, left, up, yaw_rate) in body frame (m/s, rad/s)."""
        sim = self.sim
        t = sim.time()
        pose, ranges = sim.get_pose(), sim.get_ranges()
        if t >= self.next_cam and pose.pos[2] > 0.3:
            self.dets = self.perc.detect(sim, pose, "orange")
            self.belief.update(self.dets, t)
            self.depth_raw = depth_obstacles(sim.get_depth(), pose, sim.camera())
            self.depth_obs = depth_obstacles(sim.get_depth(), pose, sim.camera(), exclude=self.belief.pos)
            self.next_cam = t + 0.2
        rays_plan = obstacle_rays(ranges, self.depth_obs, pose.yaw)
        rays_safe = obstacle_rays(ranges, self.depth_raw, pose.yaw)
        if self.mode == "AUTO":
            v, yr = self.mission.tick(t, pose, self.belief, rays_plan)
        else:
            f, l, u, yr = manual_body
            c, s = math.cos(pose.yaw), math.sin(pose.yaw)
            v = np.array([f * c - l * s, f * s + l * c, u])
        before = self.safety.interventions
        if self.filter_on:
            v, yr = self.safety(np.asarray(v, float), yr, pose, rays_safe, ranges)
        self.blocked = self.safety.interventions > before
        if self.link:
            sim.send_velocity(*v, yr)
        sim.step()
        g = sim.gt()
        self.traj.append(g["pos"][:2].copy())
        if self.gui:
            p.resetDebugVisualizerCamera(2.2, math.degrees(pose.yaw) - 90, -30, g["pos"].tolist(), physicsClientId=sim.cid)
        return g

    def camera_view(self, scale=2):
        rgb = cv2.cvtColor(self.sim.get_rgb(), cv2.COLOR_RGB2BGR)
        img = cv2.resize(rgb, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
        for d in self.dets:
            x0, y0, x1, y1 = [int(v * scale) for v in d.bbox]
            if x1 > x0:
                cv2.rectangle(img, (x0, y0), (x1, y1), (0, 255, 0), 2)
                cv2.putText(img, f"{d.conf:.2f} {d.dist:.2f}m", (x0, max(12, y0 - 4)), 0, 0.45, (0, 255, 0), 1)
        g = self.sim.gt()
        dist = np.linalg.norm(g["target"] - g["pos"]) if g["target"] is not None else float("nan")
        st = self.mission.state if self.mode == "AUTO" else "-"
        lines = [f"{self.mode}  mission:{st}  FC:{self.sim.fc_mode()}  link:{'UP' if self.link else 'LOST'}",
                 f"safety filter:{'ON' if self.filter_on else 'OFF'}{'  [BLOCKING]' if getattr(self, 'blocked', False) else ''}"
                 f"  collisions:{g['collisions']}",
                 f"t={self.sim.time():5.1f}s  alt={g['pos'][2]:.2f}m  dist to orange={dist:.2f}m  "
                 f"{self.sid} s{self.seed} {self.perc_cfg}"]
        cv2.rectangle(img, (0, 0), (img.shape[1], 66), (0, 0, 0), -1)
        for i, s in enumerate(lines):
            cv2.putText(img, s, (6, 18 + 20 * i), 0, 0.45, (0, 255, 255) if i == 0 else (255, 255, 255), 1)
        return img


# ------------------------------------------------------------------ interactive
def interactive(a):
    pl = Pilot(True, a.scenario, a.seed, a.perception)
    print(__doc__.split("Scripted")[0])
    keys_held = {}
    si = SCEN_LIST.index(a.scenario) if a.scenario in SCEN_LIST else 0
    while True:
        t0 = time.time()
        ev = p.getKeyboardEvents(physicsClientId=pl.sim.cid)
        for k, st in ev.items():
            if st & p.KEY_WAS_TRIGGERED:
                keys_held[k] = True
            if st & p.KEY_WAS_RELEASED:
                keys_held.pop(k, None)
            if not st & p.KEY_WAS_TRIGGERED:
                continue
            if k in (ord("q"), 27):
                return
            if k == ord("a"):
                pl.set_mode("AUTO")
            if k == ord("m"):
                pl.set_mode("MANUAL")
            if k == ord("x"):
                pl.link = not pl.link
            if k == ord("f"):
                pl.filter_on = not pl.filter_on
            if k == ord("r"):
                pl.load(pl.sid, pl.seed)
            if k == ord("n"):
                si = (si + 1) % len(SCEN_LIST)
                pl.load(SCEN_LIST[si], pl.seed)
        h = lambda k: k in keys_held  # noqa: E731
        f = V * (h(p.B3G_UP_ARROW) - h(p.B3G_DOWN_ARROW))
        yr = YR * (h(p.B3G_LEFT_ARROW) - h(p.B3G_RIGHT_ARROW))
        l = V * (h(ord(",")) - h(ord(".")))  # noqa: E741
        u = VZ * (h(p.B3G_PAGE_UP) - h(p.B3G_PAGE_DOWN))
        if pl.mode == "MANUAL" and pl.pose().pos[2] < 0.3 and u == 0 and (f or l or yr):
            u = VZ  # auto-takeoff when you start flying from the ground
        pl.tick((f, l, u, yr))
        cv2.imshow("Drone camera", pl.camera_view())
        cv2.imshow("Map", draw_map(pl.sc, pl.traj, pl.sim.gt(), pl.belief))
        cv2.waitKey(1)
        time.sleep(max(0, pl.sim.dt_control - (time.time() - t0)))


# --------------------------------------------------------------------- scripted
def scripted(a):
    pl = Pilot(False, a.scenario, a.seed, a.perception)
    shots = []
    dt = pl.sim.dt_control

    def run_for(seconds, cmd=(0, 0, 0, 0), label=None):
        n = max(1, int(round(seconds / dt)))
        for i in range(n):
            pl.tick(cmd)
        shots.append((label or "", pl.camera_view(scale=1).copy(), draw_map(pl.sc, pl.traj, pl.sim.gt(), pl.belief)))

    for step in [s.strip() for s in a.script.split(";") if s.strip()]:
        verb, *arg = step.split()
        x = float(arg[0]) if arg else 0.0
        if verb == "takeoff":
            while pl.pose().pos[2] < FLY_Z - 0.05:
                pl.tick((0, 0, VZ, 0))
            run_for(0.5, label="takeoff")
        elif verb in ("fwd", "back", "left", "right", "up", "down"):
            sp = VZ if verb in ("up", "down") else V
            vec = {"fwd": (sp, 0, 0, 0), "back": (-sp, 0, 0, 0), "left": (0, sp, 0, 0), "right": (0, -sp, 0, 0),
                   "up": (0, 0, sp, 0), "down": (0, 0, -sp, 0)}[verb]
            run_for(x / sp, vec, label=step)
        elif verb == "yaw":
            run_for(abs(math.radians(x)) / YR, (0, 0, 0, YR * np.sign(x)), label=step)
        elif verb == "hover":
            run_for(x, label=step)
        elif verb == "nofilter":
            pl.filter_on = False
        elif verb == "linkloss":
            pl.link = False
            run_for(x, label=f"link lost {x:.0f}s")
        elif verb == "auto":
            pl.set_mode("AUTO")
            t_end = pl.sim.time() + x
            k = 0
            while pl.sim.time() < t_end and not pl.mission.done():
                pl.tick()
                k += 1
                if k % int(round(8 / dt)) == 0:
                    shots.append((f"auto {pl.mission.state}", pl.camera_view(scale=1).copy(),
                                  draw_map(pl.sc, pl.traj, pl.sim.gt(), pl.belief)))
            run_for(0.5, label=f"auto -> {pl.mission.state}")
            pl.set_mode("MANUAL")
        g = pl.sim.gt()
        print(f"[{pl.sim.time():6.1f}s] {step:22s} pos={np.round(g['pos'], 2)} FC={pl.sim.fc_mode():15s} "
              f"collisions={g['collisions']} filter_blocks={pl.safety.interventions} "
              f"mission={pl.mission.state if pl.mode == 'AUTO' or pl.mission.done() else '-'}")
    # contact sheet
    tiles = []
    for label, cam, mp in shots:
        mp = cv2.resize(mp, (cam.shape[0], cam.shape[0]))
        tile = np.hstack([cam, mp])
        cv2.rectangle(tile, (0, tile.shape[0] - 20), (tile.shape[1], tile.shape[0]), (40, 40, 40), -1)
        cv2.putText(tile, label, (6, tile.shape[0] - 6), 0, 0.45, (255, 255, 255), 1)
        tiles.append(tile)
    cols = 2
    while len(tiles) % cols:
        tiles.append(np.zeros_like(tiles[0]))
    sheet = np.vstack([np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)])
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(a.out, sheet)
    print("saved", a.out, "| events:", pl.events)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="T5")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--perception", default="C1", help="C0 oracle, C1 colour, C2 YOLO-World, C3 OWLv2, C5 hybrid")
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--script", default="takeoff; fwd 1.5; yaw 90; auto 60")
    ap.add_argument("--out", default=str(ROOT / "out" / "fly_session.png"))
    a = ap.parse_args()
    scripted(a) if a.headless else interactive(a)
