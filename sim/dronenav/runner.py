"""Runs one episode and computes all metrics.

Inference latency is modelled in *simulated* time: a perception result computed
on the frame at time t only becomes available at t + (measured wall-clock
latency), and the next frame is only processed after that. Slow models
therefore get stale information, as they would on the real drone."""
from __future__ import annotations

import heapq
import math
import time

import numpy as np

from .parser import parse
from .perception import TargetBelief, Timer
from .planner import Mission, SafetyFilter, depth_obstacles, obstacle_rays

STANDOFF_TOL = 0.15
CAM_PERIOD = 0.2  # 5 Hz camera pipeline (minimum period)


def astar_length(sc, start_xy, goal_xy, res=0.1, inflate=0.3):
    """Shortest collision-free 2D path length (for SPL)."""
    half = sc["room"] / 2
    n = int(sc["room"] / res)
    occ = np.zeros((n, n), bool)
    xs = (np.arange(n) + 0.5) * res - half
    X, Y = np.meshgrid(xs, xs, indexing="ij")
    occ |= (np.abs(X) > half - 0.4) | (np.abs(Y) > half - 0.4)
    for o in sc["obstacles"]:
        if o["type"] == "cyl":
            occ |= np.hypot(X - o["xy"][0], Y - o["xy"][1]) < o["size"] + inflate
        else:
            yaw = o.get("yaw", 0) + math.pi / 2
            dx, dy = X - o["xy"][0], Y - o["xy"][1]
            lx = dx * math.cos(yaw) + dy * math.sin(yaw)
            ly = -dx * math.sin(yaw) + dy * math.cos(yaw)
            occ |= (np.abs(lx) < o["size"][0] / 2 + inflate) & (np.abs(ly) < o["size"][1] / 2 + inflate)
    idx = lambda p: tuple(np.clip(((np.asarray(p) + half) / res).astype(int), 0, n - 1))
    s, g = idx(start_xy), idx(goal_xy)
    # unobstructed straight line -> exact Euclidean length (grid A* overestimates)
    line = np.linspace(np.asarray(start_xy), np.asarray(goal_xy), 200)
    if not any(occ[idx(q)] for q in line[5:-5]):
        return float(np.linalg.norm(np.asarray(goal_xy) - np.asarray(start_xy)))
    occ[s] = occ[g] = False
    dist = {s: 0.0}
    pq = [(0.0, s)]
    nbrs = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]
    while pq:
        _, c = heapq.heappop(pq)
        if c == g:
            return dist[c] * res
        for dx, dy in nbrs:
            nb = (c[0] + dx, c[1] + dy)
            if not (0 <= nb[0] < n and 0 <= nb[1] < n) or occ[nb]:
                continue
            nd = dist[c] + math.hypot(dx, dy)
            if nd < dist.get(nb, 1e9):
                dist[nb] = nd
                heapq.heappush(pq, (nd + math.hypot(g[0] - nb[0], g[1] - nb[1]), nb))
    return float(np.linalg.norm(np.asarray(goal_xy) - np.asarray(start_xy)))


def run_episode(sim, sc, perception, policy=None, record=None, max_extra=5.0):
    """policy: optional high-level decision module (VLM) with .decide(...)."""
    cmd = parse(sc["command"])
    sim.reset(sc, sc["seed"])
    query = cmd["target"] or "orange"
    is_policy = getattr(perception, "is_policy", False)
    if is_policy:
        from .policy import PolicyMission
        mission = PolicyMission(time_budget=sc["time_budget"])
    else:
        mission = Mission(standoff=cmd["standoff_m"], time_budget=sc["time_budget"], start_xy=sc["start"][:2])
    if hasattr(perception, "reset"):
        perception.reset()
    belief = TargetBelief()
    safety = SafetyFilter()
    lat_perc, lat_plan = [], []
    pending = None  # (ready_time, detections)
    next_frame_t = next_depth_t = 0.0
    path_len, prev_pos = 0.0, None
    min_clear, min_clear_tgt = 99.0, 99.0
    link_up, t_loss, t_hover, t_land = True, None, None, None
    depth_obs, depth_obs_raw = [], []
    first_found_det = None
    traj = []
    t_end = sc["time_budget"] + max_extra
    while sim.time() < t_end:
        t = sim.time()
        pose = sim.get_pose()
        ranges = sim.get_ranges()
        g = sim.gt()
        # ---- perception pipeline with latency in sim time
        if pending and t >= pending[0]:
            out = pending[1]
            pending = None
            if is_policy:
                mission.set_action(out, t, pose)
            else:
                d = belief.update(out, t)
                if d is not None and first_found_det is None and belief.confirmed:
                    first_found_det = d
        if t >= next_depth_t and mission.state != "TAKEOFF":
            depth_obs_raw = depth_obstacles(sim.get_depth(), pose, sim.camera())
            depth_obs = depth_obstacles(sim.get_depth(), pose, sim.camera(), exclude=belief.pos)
            next_depth_t = t + CAM_PERIOD
        ready = mission.want_decision(t) if is_policy else mission.state != "TAKEOFF"
        if pending is None and t >= next_frame_t and ready:
            rgb = sim.get_rgb()  # camera capture (sim cost, not counted as inference latency)
            with Timer() as tm:
                out = perception.decide(rgb, query) if is_policy else perception.detect(sim, pose, query)
            lat_perc.append(tm.ms)
            delay = max(CAM_PERIOD, tm.ms / 1000)
            pending = (t + delay, out)
            next_frame_t = t + delay
        # ---- planning
        with Timer() as tp:
            rays = obstacle_rays(ranges, depth_obs, pose.yaw)
            v, yr = mission.tick(t, pose, belief, rays)
            v, yr = safety(v, yr, pose, obstacle_rays(ranges, depth_obs_raw, pose.yaw), ranges)
        lat_plan.append(tp.ms)
        # ---- link + flight controller
        if sc["link_loss"] and link_up and g["target"] is not None:
            if np.linalg.norm(g["target"][:2] - g["pos"][:2]) < sc["link_loss"]["trigger_dist"] and mission.state != "TAKEOFF":
                link_up, t_loss = False, t
        if link_up:
            sim.send_velocity(*v, yr)
        sim.step()
        mode = sim.fc_mode()
        if t_loss is not None and t_hover is None and mode == "HOVER_FAILSAFE":
            t_hover = sim.time()
        if t_loss is not None and t_land is None and mode == "LANDED":
            t_land = sim.time()
        # ---- bookkeeping
        if prev_pos is not None:
            path_len += float(np.linalg.norm(g["pos"][:2] - prev_pos))
        prev_pos = g["pos"][:2].copy()
        if g["pos"][2] > 0.3:
            min_clear = min(min_clear, g["clearance"])
            min_clear_tgt = min(min_clear_tgt, g["clearance_target"])
        traj.append((t, *g["pos"], g["yaw"], mission.state))
        if record is not None and int(round(t / sim.dt_control)) % 4 == 0:
            record(sim, pose, belief, mission, g)
        if mission.done() and t > mission.log[-1][0] + 1.0:
            break
        if mode == "LANDED" and t_loss is not None:
            break

    g = sim.gt()
    final_pos = g["pos"]
    found = any(r[1] == "found" for r in mission.reports)
    res = dict(
        scenario=sc["id"], seed=sc["seed"], perception=perception.name,
        policy=getattr(policy, "name", "classical"), command=sc["command"],
        final_state=mission.state, reported_found=found, time=round(sim.time(), 2),
        collisions=g["collisions"], min_clearance=round(min_clear, 3), min_clearance_target=round(min_clear_tgt, 3),
        interventions=safety.interventions, path_len=round(path_len, 2), lost_count=mission.lost_count,
        lat_perc_med=float(np.median(lat_perc)) if lat_perc else 0.0,
        lat_perc_p95=float(np.percentile(lat_perc, 95)) if lat_perc else 0.0,
        lat_plan_med=float(np.median(lat_plan)),
        vlm_calls=getattr(perception, "vlm_calls", 0) if not is_policy else len(mission.decisions),
        light=sc.get("light_mode", ""),
    )
    tgt = g["target"]
    if tgt is not None:
        d_final = float(np.linalg.norm(tgt - final_pos))
        res["final_dist"] = round(d_final, 3)
        res["dist_err"] = round(abs(d_final - cmd["standoff_m"]), 3)
        # target in camera view at the end?
        res["target_in_view"] = sim.visible_pixels(g["target_id"]) >= 4
        # wrong target: ended closer to a distractor than to the target
        dd = [np.linalg.norm(p - final_pos) for _, p in g["distractors"]]
        res["wrong_target"] = bool(found and dd and min(dd) < d_final and min(dd) < 1.0)
        res["success"] = bool(found and abs(d_final - cmd["standoff_m"]) <= STANDOFF_TOL and res["target_in_view"]
                              and not res["wrong_target"])
        if res["success"]:
            u = (tgt[:2] - np.array(sc["start"][:2]))
            u /= np.linalg.norm(u)
            dz = 0.15  # final approach altitude offset used by the planner
            dh = math.sqrt(max(cmd["standoff_m"] ** 2 - dz ** 2, 0.09))
            goal_xy = tgt[:2] - u * dh
            sp = astar_length(sc, sc["start"][:2], goal_xy)
            res["spl"] = round(sp / max(sp, path_len), 3)
            res["time_to_success"] = next(r[0] for r in mission.reports if r[1] == "found")
        else:
            res["spl"] = 0.0
    else:
        dd = [np.linalg.norm(p - final_pos) for _, p in g["distractors"]]
        res["wrong_target"] = bool(found and dd and min(dd) < 1.0)
        res["correct_absence"] = bool(not found and mission.state == "NOT_FOUND")
        res["success"] = res["correct_absence"]
    if sc["link_loss"]:
        res["link_lost"] = t_loss is not None
        res["t_to_hover"] = round(t_hover - t_loss, 3) if t_hover and t_loss else None
        res["t_to_land"] = round(t_land - t_loss, 3) if t_land and t_loss else None
        res["success"] = bool(t_loss is not None and t_land is not None and g["collisions"] == 0)
    res["traj"] = traj
    res["state_log"] = mission.log
    return res
