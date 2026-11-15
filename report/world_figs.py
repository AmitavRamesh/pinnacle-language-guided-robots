"""Figures + numbers for the Phase 1b-2 experiments (helipad, cross-embodiment, arm, memory)."""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, r"D:\pinnacle\sim")
import dronenav  # noqa: F401
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

OUT = Path(r"D:\pinnacle\sim\out")
FIG = Path(__file__).resolve().parent / "figs"
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 10, "figure.dpi": 200})


def wilson(k, n, z=1.96):
    if n == 0:
        return (np.nan,) * 3
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0, c - h), min(1, c + h)


def load(exp):
    f = OUT / f"world_{exp}.jsonl"
    if not f.exists():
        return pd.DataFrame()
    d = pd.DataFrame([json.loads(l) for l in open(f)])
    return d.drop_duplicates(subset=["task", "embodiment", "perception", "memory", "seed"], keep="last")


def bars(ax, groups, series, values, errs=None, colors=None, ylabel="Success (%)", ylim=105):
    w = 0.8 / len(series)
    for i, s in enumerate(series):
        x = np.arange(len(groups)) + (i - (len(series) - 1) / 2) * w
        v = [values.get((g, s), np.nan) for g in groups]
        e = None
        if errs:
            e = np.array([errs.get((g, s), (0, 0)) for g in groups]).T
        ax.bar(x, v, w, yerr=e, capsize=2, label=s, color=(colors or {}).get(s))
    ax.set_xticks(range(len(groups)), groups)
    ax.set_ylabel(ylabel)
    if ylim:
        ax.set_ylim(0, ylim)


N = {}

# ------------------------------------------------------------------- helipad
L = load("L")
if len(L):
    names = {"oracle": "Oracle", "pad_ring": "Ring detector (colour)", "pad_vlm_v1": "VLM verifier v1 (oblique)",
             "pad_vlm": "VLM verifier v3 (top-down, rot.-inv.)"}
    cols = {"Oracle": "#8c8c8c", "Ring detector (colour)": "#e69f00", "VLM verifier v1 (oblique)": "#cc79a7",
            "VLM verifier v3 (top-down, rot.-inv.)": "#d55e00"}
    vals, errs, rows = {}, {}, []
    for (t, pc), g in L.groupby(["task", "perception"]):
        n = len(g)
        k = int((g.success.astype(bool) & g.get("chose_nearest", pd.Series(False, index=g.index)).fillna(False).astype(bool)).sum())
        p, lo, hi = wilson(k, n)  # chart shows the strict measure: landed on the NEAREST helipad
        nm = names.get(pc, pc)
        vals[(t, nm)] = 100 * p
        errs[(t, nm)] = (100 * (p - lo), 100 * (hi - p))
        lo_on = g.get("landed_on")
        dec = int(g.landed_on.isin(["pad_X", "pad_plain"]).sum()) if "landed_on" in g else 0
        near = int(g.get("chose_nearest", pd.Series(dtype=bool)).fillna(False).astype(bool).sum())
        le = g.land_err.dropna() if "land_err" in g else pd.Series(dtype=float)
        strict = int((g.success.astype(bool) & g.get("chose_nearest", pd.Series(False, index=g.index)).fillna(False).astype(bool)).sum())
        rows.append(dict(task=t, perception=nm, n=n, success=round(100 * g.success.mean()), strict=round(100 * strict / n), decoy_landings=dec, chose_nearest=near,
                         land_err_med=round(float(le.median()) * 100, 1) if len(le) else None,
                         time_med=round(float(g[g.success.astype(bool)].time.median()), 1) if g.success.any() else None,
                         collisions=int(g.collisions.sum()), vlm_calls=round(float(g.vlm_calls.mean()), 1)))
    N["helipad"] = rows
    series = [s for s in names.values() if any(k[1] == s for k in vals)]
    fig, ax = plt.subplots(figsize=(8.5, 3.4))
    bars(ax, ["L1", "L2", "L3", "L4"], series, vals, errs, cols)
    ax.legend(fontsize=8, ncol=2, loc="lower left")
    ax.set_title("Landed on the NEAREST helipad (L1 one pad · L2 several · L3 + decoys · L4 + dim light)", fontsize=9.5)
    fig.tight_layout()
    fig.savefig(FIG / "res_helipad.png")
    plt.close(fig)

# ---------------------------------------------------------- cross-embodiment
O = load("O")
if len(O):
    vals, errs, rows = {}, {}, []
    for (t, emb, pc), g in O.groupby(["task", "embodiment", "perception"]):
        n, k = len(g), int(g.success.sum())
        p, lo, hi = wilson(k, n)
        key = f"{emb} / {pc}"
        vals[(t, key)] = 100 * p
        errs[(t, key)] = (100 * (p - lo), 100 * (hi - p))
        dh = [s.get("final_dh") for sl in g.subtasks for s in sl if s.get("final_dh") is not None]
        rows.append(dict(task=t, embodiment=emb, perception=pc, n=n, success=round(100 * p),
                         wrong=int(g.wrong_target.sum()), time_med=round(float(g[g.success].time.median()), 1) if k else None,
                         path_med=round(float(g.path_len.median()), 2), collisions=int(g.collisions.sum()),
                         clear_min=round(float(g.min_clearance.min()), 3), final_dh_med=round(float(np.median(dh)), 3) if dh else None,
                         lat_med=round(float(g.lat_med.median()), 1)))
    N["xemb"] = rows
    fig, axs = plt.subplots(1, 3, figsize=(10.5, 3.2), sharey=True)
    pcs = ["oracle", "hsv", "hybrid"]
    pcol = {"oracle": "#8c8c8c", "hsv": "#e69f00", "hybrid": "#d55e00"}
    for ax, t, ttl in zip(axs, ["O1", "O2", "O3"], ["O1 visible", "O2 hidden behind wall", "O3 with distractors"]):
        for i, pc in enumerate(pcs):
            for j, emb in enumerate(["drone", "ground"]):
                v = vals.get((t, f"{emb} / {pc}"), np.nan)
                ax.bar(j + (i - 1) * 0.27, v, 0.27, color=pcol[pc], label=pc if (t == "O1" and j == 0) else None,
                       hatch="//" if emb == "ground" else None, edgecolor="white")
        ax.set_xticks([0, 1], ["Drone", "Ground robot"])
        ax.set_title(ttl, fontsize=9.5)
        ax.set_ylim(0, 105)
    axs[0].set_ylabel("Success (%)")
    axs[0].legend(fontsize=8, loc="lower left")
    fig.tight_layout()
    fig.savefig(FIG / "res_xemb.png")
    plt.close(fig)

# ----------------------------------------------------------------------- arm
A = load("A")
if len(A):
    rows, vals = [], {}
    for (t, pc), g in A.groupby(["task", "perception"]):
        n, k = len(g), int(g.success.sum())
        vals[(t, pc)] = 100 * k / n
        oc = g.outcome.value_counts().to_dict()
        rows.append(dict(task=t, perception=pc, n=n, success=round(100 * k / n), picked_wrong=oc.get("picked_wrong", 0),
                         missed=oc.get("missed", 0), not_found=oc.get("not_found", 0),
                         reach_err_med=round(float(g.reach_err.dropna().median()) * 100, 1) if g.reach_err.notna().any() else None,
                         lat_med=round(float(g.lat_med.median()), 1)))
    N["arm"] = rows
    fig, ax = plt.subplots(figsize=(6, 3))
    bars(ax, ["A1", "A2", "A3"], ["oracle", "hsv", "hybrid"], vals, colors={"oracle": "#8c8c8c", "hsv": "#e69f00", "hybrid": "#d55e00"})
    ax.legend(fontsize=8)
    ax.set_title("Arm: pick up the orange (A1 alone · A2 + distractors · A3 + dim light)", fontsize=9.5)
    fig.tight_layout()
    fig.savefig(FIG / "res_arm.png")
    plt.close(fig)

# -------------------------------------------------------------------- memory
M = load("M")
if len(M):
    rows = []
    for (t, emb, mem), g in M.groupby(["task", "embodiment", "memory"]):
        subs = [s for sl in g.subtasks for s in sl]
        fm = np.mean([s["from_memory"] for s in subs]) if subs else 0
        rows.append(dict(task=t, embodiment=emb, memory=mem, n=len(g), success=round(100 * g.success.mean()),
                         sub_ok=round(100 * g.n_sub_ok.sum() / g.n_sub.sum()),
                         time_mean=round(float(g.time.mean()), 1), time_sd=round(float(g.time.std()), 1),
                         path_mean=round(float(g.path_len.mean()), 1), from_memory=round(100 * fm),
                         recall=round(100 * float(g.mem_recall.mean())), collisions=int(g.collisions.sum()),
                         clear_min=round(float(g.min_clearance.min()), 3)))
    N["memory"] = rows
    R = pd.DataFrame(rows)
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.4))
    mcol = {"none": "#999999", "per-mission": "#56b4e9", "persistent": "#009e73"}
    for ax, met, yl in zip(axs, ["time_mean", "path_mean"], ["Mission time (s)", "Path length (m)"]):
        grp = [(t, e) for t in ["M1", "M2"] for e in ["drone", "ground"]]
        for i, m in enumerate(["none", "per-mission", "persistent"]):
            v, sd = [], []
            for t, e in grp:
                r = R[(R.task == t) & (R.embodiment == e) & (R.memory == m)]
                v.append(float(r[met].iloc[0]) if len(r) else np.nan)
                sd.append(float(r["time_sd"].iloc[0]) if (len(r) and met == "time_mean") else 0)
            ax.bar(np.arange(len(grp)) + (i - 1) * 0.27, v, 0.27, yerr=sd if met == "time_mean" else None, capsize=2,
                   color=mcol[m], label=m)
        ax.set_xticks(range(len(grp)), [f"{t}\n{e}" for t, e in grp])
        ax.set_ylabel(yl)
    axs[0].legend(fontsize=8, title="memory", title_fontsize=8)
    axs[0].set_title("Mission time (M1: 3 objects, M2: 2 × 3 objects)", fontsize=9.5)
    axs[1].set_title("Distance travelled", fontsize=9.5)
    fig.tight_layout()
    fig.savefig(FIG / "res_memory.png")
    plt.close(fig)
    # subtask durations: first vs repeated visits
    dd = []
    for _, r in M[M.task == "M2"].iterrows():
        for i, s in enumerate(r.subtasks):
            dd.append(dict(emb=r.embodiment, mem=r.memory, idx=i + 1, dur=s["duration"]))
    D = pd.DataFrame(dd)
    fig, axs = plt.subplots(1, 2, figsize=(10, 3), sharey=True)
    for ax, emb in zip(axs, ["drone", "ground"]):
        for m in ["none", "per-mission", "persistent"]:
            s = D[(D.emb == emb) & (D.mem == m)].groupby("idx").dur.mean()
            ax.plot(s.index, s.values, "o-", color=mcol[m], label=m)
        ax.axvline(3.5, color="#aaa", ls=":")
        ax.text(3.6, ax.get_ylim()[1] * 0.9 if ax.get_ylim()[1] > 1 else 40, "mission 2 starts", fontsize=8, color="#666")
        ax.set_xlabel("Subtask number (M2)")
        ax.set_title(emb, fontsize=9.5)
    axs[0].set_ylabel("Mean subtask duration (s)")
    axs[0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "res_memory_subtasks.png")
    plt.close(fig)

json.dump(N, open(Path(__file__).resolve().parent / "numbers_world.json", "w"), indent=1, default=str)
for k, v in N.items():
    print("==", k)
    print(pd.DataFrame(v).to_string(index=False))
