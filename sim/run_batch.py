"""Batch experiment runner.

Example:
  python run_batch.py --configs C0,C1 --scenarios T1,T2,T3 --seeds 10 --workers 6
Results append to out/results.jsonl (one row per episode); trajectories go to out/traj/.
Already-finished (config, scenario, seed) rows are skipped, so runs can resume.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import dronenav  # noqa: E402,F401  (cache dirs on D:)
OUT = ROOT / "out"
GPU_CONFIGS = {"C2", "C3", "C4", "C5", "C6"}

_sim = None
_perc = {}


def make_perception(cfg):
    from dronenav.perception import HSVPerception, OraclePerception
    if cfg == "C0":
        return OraclePerception()
    if cfg == "C1":
        return HSVPerception()
    from dronenav import models
    return models.make(cfg)


def run_one(cfg, sid, seed, sim_name="pybullet"):
    global _sim
    from dronenav.runner import run_episode
    from dronenav.scenarios import make_scenario
    if _sim is None:
        if sim_name == "pybullet":
            from dronenav.sim_pybullet import PyBulletSim
            _sim = PyBulletSim()
        elif sim_name == "mujoco":
            from dronenav.sim_mujoco import MuJoCoSim
            _sim = MuJoCoSim()
        else:
            raise ValueError(sim_name)
    if hasattr(_sim, "max_tilt"):
        _sim.max_tilt = 0.0
    if cfg not in _perc:
        _perc[cfg] = make_perception(cfg)
    sc = make_scenario(sid, seed)
    t0 = time.time()
    res = run_episode(_sim, sc, _perc[cfg])
    traj = res.pop("traj")
    log = res.pop("state_log")
    res.update(config=cfg, sim=sim_name, max_tilt_deg=round(getattr(_sim, "max_tilt", 0.0), 1), wall_s=round(time.time() - t0, 1), state_log=json.dumps(log))
    tdir = OUT / "traj"
    tdir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(traj, columns=["t", "x", "y", "z", "yaw", "state"]).to_csv(
        tdir / f"{sim_name}_{cfg}_{sid}_{seed}.csv", index=False)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs", default="C0,C1")
    ap.add_argument("--scenarios", default="T1,T2,T3,T4,T5,T6,T7,T8,T9,T10")
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--seed0", type=int, default=0)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument("--sim", default="pybullet")
    ap.add_argument("--out", default=str(OUT / "results.jsonl"))
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    done = set()
    if Path(a.out).exists():
        prev = pd.read_json(a.out, lines=True)
        if len(prev):
            done = set(zip(prev.config, prev.scenario, prev.seed, prev["sim"]))
    jobs = [(c, s, k) for c in a.configs.split(",") for s in a.scenarios.split(",")
            for k in range(a.seed0, a.seed0 + a.seeds) if (c, s, k, a.sim) not in done]
    # GPU models share one GPU: run them in a single worker; CPU configs in parallel
    cpu_jobs = [j for j in jobs if j[0] not in GPU_CONFIGS]
    gpu_jobs = [j for j in jobs if j[0] in GPU_CONFIGS]
    print(f"{len(jobs)} episodes ({len(cpu_jobs)} CPU, {len(gpu_jobs)} GPU)")
    n = 0

    def write(res):
        nonlocal n
        with open(a.out, "a") as f:
            f.write(json.dumps(res, default=lambda o: o.item() if hasattr(o, "item") else str(o)) + "\n")
        n += 1
        print(f"[{n}/{len(jobs)}] {res['config']} {res['scenario']} s{res['seed']} "
              f"success={res['success']} state={res['final_state']} coll={res['collisions']} "
              f"t={res['time']} wall={res['wall_s']}s", flush=True)

    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = [ex.submit(run_one, *j, a.sim) for j in cpu_jobs]
        for j in gpu_jobs:  # GPU jobs run in this process, sequentially
            write(run_one(*j, a.sim))
        for f in as_completed(futs):
            write(f.result())


if __name__ == "__main__":
    main()
