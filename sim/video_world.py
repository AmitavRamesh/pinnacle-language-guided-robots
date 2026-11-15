"""Demo videos for the Phase 1b-2 tasks: robot camera | observer camera | live map.
  python video_world.py landing | memory_drone | memory_ground | orange_ground
Output: out/video_<name>.mp4"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import dronenav  # noqa: E402,F401
import cv2  # noqa: E402
import numpy as np  # noqa: E402

from dronenav.sim_world import WorldSim  # noqa: E402
from dronenav.world_agent import PadRing, WorldOracle, run_world_episode  # noqa: E402
from dronenav.world_scenarios import make_world  # noqa: E402
from showcase import fpv_with_dets, label, topdown  # noqa: E402

JOBS = {
    "landing": dict(task="L3", seed=0, emb="drone", perc="padvlm", mem="persistent"),
    "memory_drone": dict(task="M2", seed=1, emb="drone", perc="oracle", mem="persistent"),
    "memory_ground": dict(task="M2", seed=1, emb="ground", perc="oracle", mem="persistent"),
    "orange_ground": dict(task="O3", seed=0, emb="ground", perc="oracle", mem="persistent"),
}


def main(name):
    j = JOBS[name]
    s = WorldSim()
    sc = make_world(j["task"], j["seed"], j["emb"])
    if j["perc"] == "padvlm":
        from dronenav.world_agent import PadHybrid
        P = PadHybrid()
    else:
        P = WorldOracle()
    show = PadRing() if j["task"].startswith("L") else WorldOracle()
    out = ROOT / "out" / f"video_{name}.mp4"
    vw = cv2.VideoWriter(str(out), cv2.VideoWriter_fourcc(*"mp4v"), 5, (640 + 640 + 480, 480))
    traj = []

    def rec(sim, pose, ms, mem, g):
        traj.append(g["pos"][:2].copy())
        dets = show.detect(sim, sim.get_pose())
        if j["task"].startswith("L"):
            for d in dets:
                near = [(lab, e) for lab, lst in mem.entries.items() for e in lst if np.linalg.norm(e["pos"][:2] - d.pos[:2]) < 0.4]
                d.label = near[0][0] if near else "pad?"
        cur = ms.current()
        task = f"{cur[1][0]} {cur[1][1]}" if cur else ""
        cam = label(cv2.resize(fpv_with_dets(sim, dets, 2), (640, 480)), f"{j['emb']} camera | {ms.state} | {task}")
        obs = label(sim.chase_image(w=640, h=480, dist=1.8, height=1.0), f"observer | t={sim.time():.1f}s")
        mp = cv2.resize(topdown(sim, sc, traj, mem=mem, size=480), (480, 480))
        label(mp, f"memory: {mem.n_objects()} objects, {len(mem.explored)} rooms", (8, 22), 0.5)
        vw.write(cv2.cvtColor(np.hstack([cam, obs, mp]), cv2.COLOR_RGB2BGR))

    r = run_world_episode(s, sc, P, use_memory=j["mem"] != "none", persist=j["mem"] == "persistent", record=rec)
    vw.release()
    print(name, "success", r["success"], f"{r['n_sub_ok']}/{r['n_sub']}", "time", r["time"], "->", out)


if __name__ == "__main__":
    for n in sys.argv[1:] or list(JOBS):
        main(n)
