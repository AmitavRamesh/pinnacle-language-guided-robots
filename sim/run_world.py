"""Batch runner for the Phase 1b-2 experiments (multi-task, memory, cross-embodiment).

  python run_world.py --exp O     # cross-embodiment orange task (drone vs ground robot)
  python run_world.py --exp L     # helipad: find the nearest helipad and land
  python run_world.py --exp M     # memory vs no memory in the multi-room house
  python run_world.py --exp A     # robot-arm pick task
  add --gpu-only / --cpu-only to split the work; results -> out/world_<exp>.jsonl (resumable)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import dronenav  # noqa: E402,F401

OUT = ROOT / "out"
GPU = {"hybrid", "padvlm"}
_sim, _arm, _perc = None, None, {}


def jobs_for(exp, seeds):
    J = []
    if exp == "O":
        for t in ["O1", "O2", "O3"]:
            for emb in ["drone", "ground"]:
                for pc in ["oracle", "hsv", "hybrid"]:
                    J += [dict(exp=exp, task=t, emb=emb, perc=pc, mem="persistent", seed=s) for s in seeds]
    elif exp == "L":
        for t in ["L1", "L2", "L3", "L4"]:
            for pc in ["oracle", "ring", "padvlm"]:
                J += [dict(exp=exp, task=t, emb="drone", perc=pc, mem="persistent", seed=s) for s in seeds]
    elif exp == "M":
        for emb in ["drone", "ground"]:
            for t, mems in [("M1", ["none", "persistent"]), ("M2", ["none", "per-mission", "persistent"])]:
                for m in mems:
                    J += [dict(exp=exp, task=t, emb=emb, perc="oracle", mem=m, seed=s) for s in seeds]
    elif exp == "A":
        for t in ["A1", "A2", "A3"]:
            for pc in ["oracle", "hsv", "hybrid"]:
                J += [dict(exp=exp, task=t, emb="arm", perc=pc, mem="-", seed=s) for s in seeds]
    return J


def perception(name):
    from dronenav import world_agent as W
    if name not in _perc:
        _perc[name] = {"oracle": W.WorldOracle, "hsv": W.OrangeHSV, "ring": W.PadRing,
                       "padvlm": W.PadHybrid, "hybrid": W.ObjectHybrid}[name]()
    return _perc[name]


def run(job):
    global _sim, _arm
    t0 = time.time()
    P = perception(job["perc"])
    if job["exp"] == "A":
        from dronenav.arm import ArmSim, make_arm_task, run_arm_episode
        _arm = _arm or ArmSim()
        res = run_arm_episode(_arm, make_arm_task(job["task"], job["seed"]), P)
    else:
        from dronenav.sim_world import WorldSim
        from dronenav.world_agent import run_world_episode
        from dronenav.world_scenarios import make_world
        _sim = _sim or WorldSim()
        sc = make_world(job["task"], job["seed"], job["emb"])
        res = run_world_episode(_sim, sc, P, use_memory=job["mem"] != "none", persist=job["mem"] == "persistent")
        traj = res.pop("traj")
        tdir = OUT / "traj_world"
        tdir.mkdir(parents=True, exist_ok=True)
        import pandas as pd
        pd.DataFrame(traj, columns=["t", "x", "y", "z", "yaw", "state"]).to_csv(
            tdir / f"{job['task']}_{job['emb']}_{job['perc']}_{job['mem']}_{job['seed']}.csv", index=False)
        res["state_log"] = json.dumps(res["state_log"])
    res.update(exp=job["exp"], memory=job["mem"], wall_s=round(time.time() - t0, 1))
    return res


def key(r):
    return (r["exp"], r["task"], r["embodiment"], r["perception"], r["memory"], r["seed"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", required=True)
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--gpu-only", action="store_true")
    ap.add_argument("--cpu-only", action="store_true")
    a = ap.parse_args()
    out = OUT / f"world_{a.exp}.jsonl"
    done = set()
    if out.exists():
        for line in open(out):
            r = json.loads(line)
            done.add(key(r))
    names = {"oracle": "oracle", "hsv": "hsv", "ring": "pad_ring", "padvlm": "pad_vlm", "hybrid": "hybrid"}
    J = [j for j in jobs_for(a.exp, range(a.seeds))
         if (j["exp"], j["task"], "arm" if j["exp"] == "A" else j["emb"], names[j["perc"]], j["mem"], j["seed"]) not in done]
    gpu = [j for j in J if j["perc"] in GPU]
    cpu = [j for j in J if j["perc"] not in GPU]
    if a.gpu_only:
        cpu = []
    if a.cpu_only:
        gpu = []
    print(f"{a.exp}: {len(cpu)} CPU + {len(gpu)} GPU episodes", flush=True)
    n = 0

    def write(r):
        nonlocal n
        with open(out, "a") as f:
            f.write(json.dumps(r, default=lambda o: o.item() if hasattr(o, "item") else str(o)) + "\n")
        n += 1
        print(f"[{n}] {r['task']} {r['embodiment']} {r['perception']} {r['memory']} s{r['seed']} "
              f"success={r['success']} wall={r['wall_s']}s", flush=True)

    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = [ex.submit(run, j) for j in cpu]
        for j in gpu:
            write(run(j))
        for f in as_completed(futs):
            write(f.result())


if __name__ == "__main__":
    main()
