"""Builds the results figures + a numbers.json used in the report text."""
import glob
import json
import math
import shutil
import sys
from pathlib import Path

sys.path.insert(0, r"D:\pinnacle\sim")
import dronenav  # noqa: F401
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from dronenav.parser import score_parser
from dronenav.scenarios import make_scenario

SIM = Path(r"D:\pinnacle\sim\out")
OUT = Path(__file__).resolve().parent / "figs"
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 10, "figure.dpi": 200})
NAMES = {"C0": "C0 Oracle", "C1": "C1 Colour", "C2": "C2 YOLO-World", "C3": "C3 OWLv2", "C4": "C4 VLM policy",
         "C5": "C5 Hybrid (ours)", "C6": "C6 C5 w/o VLM"}
COL = {"C0": "#8c8c8c", "C1": "#e69f00", "C2": "#56b4e9", "C3": "#009e73", "C4": "#cc79a7", "C5": "#d55e00", "C6": "#0072b2"}
SCN = ["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9", "T10"]


def wilson(k, n, z=1.96):
    if n == 0:
        return np.nan, np.nan, np.nan
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0, c - h), min(1, c + h)


d = pd.concat([pd.read_json(f, lines=True) for f in glob.glob(str(SIM / "results*.jsonl"))], ignore_index=True)
d = d.drop_duplicates(subset=["sim", "config", "scenario", "seed"], keep="last")
for c in ["wrong_target", "correct_absence", "reported_found", "success"]:
    d[c] = d[c].astype("boolean").fillna(False).astype(bool)
pb = d[(d.sim == "pybullet") & (d.seed < 10) & (d.scenario.isin(SCN)) & ~((d.config == "C4") & (d.seed >= 5))]
N = {}

# 1 heatmap ------------------------------------------------------------------
piv = pb.pivot_table(index="config", columns="scenario", values="success", aggfunc="mean")[SCN] * 100
cnt = pb.pivot_table(index="config", columns="scenario", values="success", aggfunc="count")[SCN]
fig, ax = plt.subplots(figsize=(8.5, 3.6))
im = ax.imshow(piv.values, cmap="RdYlGn", vmin=0, vmax=100, aspect="auto")
ax.set_xticks(range(len(SCN)), SCN)
ax.set_yticks(range(len(piv)), [NAMES[c] for c in piv.index])
for i in range(piv.shape[0]):
    for j in range(piv.shape[1]):
        v = piv.values[i, j]
        if not np.isnan(v):
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=8.5)
fig.colorbar(im, ax=ax, label="Success (%)", fraction=0.03)
ax.set_xlabel("Scenario")
fig.tight_layout()
fig.savefig(OUT / "res_heatmap.png")
plt.close(fig)
N["heatmap"] = piv.round(0).to_dict()
N["heatmap_n"] = cnt.to_dict()

# 2 overall table + bar -------------------------------------------------------
rows = []
for c, g in pb.groupby("config"):
    nav = g[~g.scenario.isin(["T6", "T9"])]
    t6 = g[g.scenario == "T6"]
    dis = g[g.scenario.isin(["T5", "T6", "T7"])]
    k = int(nav.success.sum())
    p, lo, hi = wilson(k, len(nav))
    pa, loa, hia = wilson(int(t6.correct_absence.sum()), len(t6))
    pw, low, hiw = wilson(int(dis.wrong_target.sum()), len(dis))
    found = nav[nav.reported_found]
    rows.append(dict(config=c, name=NAMES[c], episodes=len(g), nav_n=len(nav), nav_succ=round(100 * p, 1),
                     nav_lo=round(100 * lo, 1), nav_hi=round(100 * hi, 1),
                     spl=round(nav.spl.fillna(0).mean(), 2),
                     t_succ=round(nav.time_to_success.median(), 1) if nav.time_to_success.notna().any() else None,
                     dist_err=round(found.dist_err.median(), 3) if len(found) else None,
                     wrong=round(100 * pw, 1), wrong_lo=round(100 * low, 1), wrong_hi=round(100 * hiw, 1),
                     absence=round(100 * pa, 1), absence_n=len(t6),
                     collisions=int(g.collisions.sum()), min_clear=round(g.min_clearance.min(), 3),
                     clear_med=round(g.min_clearance.median(), 3),
                     lat_med=round(g.lat_perc_med.median(), 1), lat_p95=round(g.lat_perc_p95.median(), 1),
                     vlm_calls=round(g.vlm_calls.fillna(0).mean(), 1)))
ov = pd.DataFrame(rows)
N["overall"] = ov.to_dict(orient="records")
fig, axs = plt.subplots(1, 3, figsize=(10, 3.2))
for ax, (col, lo, hi, title) in zip(axs, [("nav_succ", "nav_lo", "nav_hi", "Navigation success (T1–T5, T7, T8, T10)"),
                                          ("wrong", "wrong_lo", "wrong_hi", "Wrong-target rate (T5–T7)"),
                                          ("absence", None, None, "Correct 'not found' (T6)")]):
    y = ov[col].values
    err = None if lo is None else [y - ov[lo].values, ov[hi].values - y]
    ax.bar(range(len(ov)), y, yerr=err, capsize=2, color=[COL[c] for c in ov.config])
    ax.set_xticks(range(len(ov)), ov.config)
    ax.set_title(title, fontsize=9.5)
    ax.set_ylim(0, 105)
    ax.set_ylabel("%")
fig.tight_layout()
fig.savefig(OUT / "res_overall.png")
plt.close(fig)

# 3 cross-simulator -----------------------------------------------------------
xs = d[(d.config.isin(["C0", "C1", "C2", "C5"])) & (d.scenario.isin(["T1", "T3", "T5", "T6", "T9"])) & (d.seed < 10)]
xt = xs.pivot_table(index=["config", "scenario"], columns="sim", values="success", aggfunc="mean").mul(100).round(0)
N["cross_sim"] = {f"{a}|{b}": r.to_dict() for (a, b), r in xt.iterrows()}
fig, axs = plt.subplots(1, 4, figsize=(10.5, 2.9), sharey=True)
for ax, c in zip(axs, ["C0", "C1", "C2", "C5"]):
    sub = xt.loc[c]
    x = np.arange(len(sub))
    ax.bar(x - 0.2, sub.get("pybullet", np.nan), 0.4, label="PyBullet", color="#4c72b0")
    ax.bar(x + 0.2, sub.get("mujoco", np.nan), 0.4, label="MuJoCo", color="#dd8452")
    ax.set_xticks(x, sub.index)
    ax.set_title(NAMES[c], fontsize=9.5)
    ax.set_ylim(0, 105)
axs[0].set_ylabel("Success (%)")
axs[0].legend(fontsize=8, loc="lower left")
fig.tight_layout()
fig.savefig(OUT / "res_cross_sim.png")
plt.close(fig)
mj = d[d.sim == "mujoco"]
N["mujoco_tilt_max"] = float(mj.max_tilt_deg.max())
N["mujoco_tilt_med"] = float(mj.max_tilt_deg.median())
t3 = d[(d.scenario == "T3") & (d.config == "C0") & (d.seed < 10)].groupby("sim").time.median()
N["t3_time"] = t3.round(1).to_dict()
t9 = d[d.scenario == "T9"].groupby("sim")[["t_to_hover", "t_to_land"]].agg(["min", "max"])
N["t9"] = {f"{s}": {"hover": [float(t9.loc[s, ("t_to_hover", "min")]), float(t9.loc[s, ("t_to_hover", "max")])],
                    "land": [float(t9.loc[s, ("t_to_land", "min")]), float(t9.loc[s, ("t_to_land", "max")])]}
           for s in t9.index}

# 4 sensor ablation -----------------------------------------------------------
sa = d[(d.config == "C0") & (d.scenario.isin(["T4", "T4D"]))]
fig, ax = plt.subplots(figsize=(6, 3.2))
groups = [("pybullet", "T4"), ("pybullet", "T4D"), ("mujoco", "T4"), ("mujoco", "T4D")]
ax.boxplot([sa[(sa.sim == s) & (sa.scenario == t)].min_clearance for s, t in groups],
           tick_labels=[f"{'PyBullet' if s == 'pybullet' else 'MuJoCo'}\n{'8 beams' if t == 'T4' else '24 beams'}"
                        for s, t in groups])
ax.axhline(0.10, color="#a33", ls="--", lw=1)
ax.text(4.45, 0.105, "10 cm", color="#a33", fontsize=8, ha="right")
ax.set_ylabel("Minimum obstacle clearance per run (m)")
fig.tight_layout()
fig.savefig(OUT / "res_sensor_ablation.png")
plt.close(fig)
N["sensor"] = {f"{s}|{t}": dict(n=int(len(g)), success=float(g.success.mean() * 100), min=float(g.min_clearance.min()),
                                med=float(g.min_clearance.median()), below10=int((g.min_clearance < 0.10).sum()),
                                time=float(g.time.median()), interv=float(g.interventions.mean()))
               for (s, t), g in sa.groupby(["sim", "scenario"])}

# 5 latency -------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(6.5, 3))
ax.bar(range(len(ov)), ov.lat_med, color=[COL[c] for c in ov.config])
ax.errorbar(range(len(ov)), ov.lat_med, yerr=[np.zeros(len(ov)), ov.lat_p95 - ov.lat_med], fmt="none", ecolor="k",
            capsize=3)
ax.set_xticks(range(len(ov)), ov.config)
ax.set_yscale("log")
ax.set_ylabel("Perception / decision latency (ms)\nmedian, whisker = p95")
ax.axhline(200, color="#777", ls=":", lw=1)
ax.text(len(ov) - 0.5, 215, "5 Hz camera period", fontsize=8, ha="right", color="#555")
fig.tight_layout()
fig.savefig(OUT / "res_latency.png")
plt.close(fig)

# 6 distractor analysis (which distractor fooled which config) ----------------
rows = []
for c in ["C1", "C3", "C5", "C6"]:
    g = pb[(pb.config == c) & (pb.scenario.isin(["T5", "T6", "T7"]))]
    for has_ball in [True, False]:
        sel = [("orange_ball" in [t["item"] for t in make_scenario(r.scenario, int(r.seed))["tables"]]) == has_ball
               for r in g.itertuples()]
        gg = g[sel]
        rows.append(dict(config=c, ball_present=has_ball, episodes=len(gg), wrong=int(gg.wrong_target.sum())))
N["distractor"] = rows

# 7 parser + collisions + episodes ------------------------------------------
pr = pd.DataFrame(score_parser())
N["parser"] = dict(correct=int(pr.correct.sum()), n=len(pr), failed=pr[~pr.correct].command.tolist())
N["episodes_total"] = int(len(d))
N["episodes_by_sim"] = d.groupby("sim").size().to_dict()
N["collision_eps"] = d[d.collisions > 0][["sim", "config", "scenario", "seed"]].to_dict(orient="records")
N["dist_err_c0"] = float(pb[(pb.config == "C0") & pb.reported_found].dist_err.median())

# copy screenshots
for src, dst in [(SIM / "view_T5.png", "shot_pybullet.png"), (SIM / "view_mj_T5.png", "shot_mujoco.png"),
                 (SIM / "demo_frame.png", "shot_demo.png"), (SIM / "fly_A_safety_on.png", "shot_fly_on.png"),
                 (SIM / "fly_B_safety_off.png", "shot_fly_off.png"), (SIM / "fly_C_linkloss.png", "shot_linkloss.png"),
                 (SIM / "report_all" / "fig_trajectories_seed0.png", "res_trajectories.png")]:
    if src.exists():
        shutil.copy(src, OUT / dst)
json.dump(N, open(OUT.parent / "numbers.json", "w"), indent=1, default=str)
print(ov[["config", "episodes", "nav_succ", "nav_lo", "nav_hi", "spl", "t_succ", "dist_err", "wrong", "absence",
          "collisions", "min_clear", "lat_med", "lat_p95", "vlm_calls"]].to_string(index=False))
print(json.dumps({k: N[k] for k in ["sensor", "distractor", "parser", "episodes_total", "episodes_by_sim", "t3_time",
                                     "mujoco_tilt_max", "t9", "dist_err_c0"]}, indent=0, default=str)[:3500])
