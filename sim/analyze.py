"""Turns out/results.jsonl into report tables (CSV + Markdown) and figures (PNG).

  python analyze.py                 # all results
  python analyze.py --in out/results.jsonl --tag main
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import dronenav  # noqa: E402,F401  (sets cache dirs on D: before matplotlib loads)
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from dronenav.parser import score_parser  # noqa: E402
from dronenav.scenarios import SCENARIOS, make_scenario  # noqa: E402

CFG_NAMES = {"C0": "C0 Oracle", "C1": "C1 Colour (HSV)", "C2": "C2 YOLO-World", "C3": "C3 OWLv2",
             "C4": "C4 VLM policy", "C5": "C5 Hybrid (ours)", "C6": "C6 Ablation: C5 w/o VLM"}
COLORS = {"C0": "#8c8c8c", "C1": "#e69f00", "C2": "#56b4e9", "C3": "#009e73", "C4": "#cc79a7", "C5": "#d55e00", "C6": "#0072b2"}
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 11, "figure.dpi": 150})


def wilson(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan, np.nan)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0, c - h), min(1, c + h)


def fmt_rate(k, n):
    p, lo, hi = wilson(k, n)
    return f"{100*p:.0f}% [{100*lo:.0f}-{100*hi:.0f}]"


def summarise(d):
    rows = []
    for (sim, cfg, sid), g in d.groupby(["sim", "config", "scenario"]):
        n = len(g)
        r = dict(sim=sim, config=cfg, scenario=sid, n=n,
                 success=fmt_rate(int(g.success.sum()), n), success_p=g.success.mean())
        if "spl" in g and g.spl.notna().any():
            r["SPL"] = round(g.spl.fillna(0).mean(), 2)
        if "time_to_success" in g and g.time_to_success.notna().any():
            r["t_success_med_s"] = round(g.time_to_success.median(), 1)
        if "dist_err" in g and g.dist_err.notna().any():
            r["dist_err_med_m"] = round(g[g.reported_found].dist_err.median(), 3) if g.reported_found.any() else np.nan
        r["wrong_target"] = fmt_rate(int(g.wrong_target.fillna(False).sum()), n)
        r["collision_runs"] = fmt_rate(int((g.collisions > 0).sum()), n)
        r["min_clear_m(min/med)"] = f"{g.min_clearance.min():.2f}/{g.min_clearance.median():.2f}"
        r["interventions_mean"] = round(g.interventions.mean(), 1)
        r["lat_perc_med_ms"] = round(g.lat_perc_med.median(), 1)
        r["lat_perc_p95_ms"] = round(g.lat_perc_p95.median(), 1)
        if sid == "T6":
            r["correct_absence"] = fmt_rate(int(g.correct_absence.fillna(False).sum()), n)
        if sid == "T9" and "t_to_hover" in g:
            r["hover_s_med"] = g.t_to_hover.median()
            r["land_s_med"] = g.t_to_land.median()
        rows.append(r)
    return pd.DataFrame(rows)


def overall(d):
    rows = []
    for (sim, cfg), g in d.groupby(["sim", "config"]):
        nav = g[~g.scenario.isin(["T6", "T9"])]
        r = dict(sim=sim, config=CFG_NAMES.get(cfg, cfg), episodes=len(g),
                 success_nav=fmt_rate(int(nav.success.sum()), len(nav)),
                 SPL=round(nav.spl.fillna(0).mean(), 2),
                 wrong_target=fmt_rate(int(g.wrong_target.fillna(False).sum()), len(g)),
                 collisions=int(g.collisions.sum()),
                 min_clearance=round(g.min_clearance.min(), 2),
                 lat_med_ms=round(g.lat_perc_med.median(), 1))
        t6 = g[g.scenario == "T6"]
        if len(t6):
            r["correct_absence"] = fmt_rate(int(t6.correct_absence.fillna(False).sum()), len(t6))
        rows.append(r)
    return pd.DataFrame(rows)


def fig_success(d, out):
    cfgs = sorted(d.config.unique())
    sids = [s for s in SCENARIOS if s in set(d.scenario)]
    w = 0.8 / len(cfgs)
    fig, ax = plt.subplots(figsize=(10, 4))
    for i, c in enumerate(cfgs):
        ps, los, his = [], [], []
        for s in sids:
            g = d[(d.config == c) & (d.scenario == s)]
            p, lo, hi = wilson(int(g.success.sum()), len(g))
            ps.append(p * 100), los.append((p - lo) * 100), his.append((hi - p) * 100)
        x = np.arange(len(sids)) + (i - (len(cfgs) - 1) / 2) * w
        ax.bar(x, ps, w, yerr=[los, his], capsize=2, label=CFG_NAMES.get(c, c), color=COLORS.get(c))
    ax.set_xticks(range(len(sids)), sids)
    ax.set_ylabel("Success rate (%)")
    ax.set_ylim(0, 105)
    ax.legend(ncol=3, fontsize=9, loc="lower left")
    ax.set_title("Task success by scenario (95% Wilson CI)")
    fig.tight_layout()
    fig.savefig(out / "fig_success_by_scenario.png")
    plt.close(fig)


def fig_heatmap(d, out):
    piv = d.pivot_table(index="config", columns="scenario", values="success", aggfunc="mean") * 100
    piv = piv[[s for s in SCENARIOS if s in piv.columns]]
    fig, ax = plt.subplots(figsize=(9, 0.6 * len(piv) + 1.2))
    im = ax.imshow(piv.values, cmap="RdYlGn", vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(range(piv.shape[1]), piv.columns)
    ax.set_yticks(range(piv.shape[0]), [CFG_NAMES.get(c, c) for c in piv.index])
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            v = piv.values[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=9)
    fig.colorbar(im, ax=ax, label="Success %")
    fig.tight_layout()
    fig.savefig(out / "fig_success_heatmap.png")
    plt.close(fig)


def fig_box(d, out, col, label, fname, scen=None):
    g = d if scen is None else d[d.scenario.isin(scen)]
    g = g[g[col].notna()] if col in g else g.iloc[0:0]
    if g.empty:
        return
    cfgs = sorted(g.config.unique())
    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.boxplot([g[g.config == c][col] for c in cfgs], tick_labels=[CFG_NAMES.get(c, c) for c in cfgs])
    ax.set_ylabel(label)
    plt.setp(ax.get_xticklabels(), rotation=15)
    fig.tight_layout()
    fig.savefig(out / fname)
    plt.close(fig)


def fig_latency(d, out):
    g = d.groupby("config")[["lat_perc_med", "lat_plan_med"]].median()
    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.bar([CFG_NAMES.get(c, c) for c in g.index], g.lat_perc_med, label="Perception / VLM", color="#56b4e9")
    ax.bar([CFG_NAMES.get(c, c) for c in g.index], g.lat_plan_med, bottom=g.lat_perc_med, label="Planner + safety",
           color="#e69f00")
    ax.set_ylabel("Median latency per decision (ms)")
    ax.set_yscale("log")
    ax.legend()
    plt.setp(ax.get_xticklabels(), rotation=15)
    fig.tight_layout()
    fig.savefig(out / "fig_latency.png")
    plt.close(fig)


def draw_layout(ax, sc):
    h = sc["room"] / 2
    ax.plot([-h, h, h, -h, -h], [-h, -h, h, h, -h], "k-", lw=1.5)
    for o in sc["obstacles"]:
        if o["type"] == "cyl":
            ax.add_patch(plt.Circle(o["xy"], o["size"], color="#7a8796"))
        else:
            yaw = o.get("yaw", 0) + math.pi / 2
            L, W = o["size"][1], o["size"][0]
            c, s = math.cos(yaw), math.sin(yaw)
            pts = np.array([[-W / 2, -L / 2], [W / 2, -L / 2], [W / 2, L / 2], [-W / 2, L / 2]])
            R = np.array([[c, -s], [s, c]])
            ax.add_patch(plt.Polygon(pts @ R.T + o["xy"], color="#a89f88"))
    for t in sc["tables"]:
        s = t["size"] / 2
        ax.add_patch(plt.Rectangle((t["xy"][0] - s, t["xy"][1] - s), 2 * s, 2 * s, color="#8b5a2b", alpha=0.6))
        col = {"orange": "#ff8c00", "orange_ball": "#ff6a00", "orange_cube": "#ff9933", "apple": "#c00000",
               "lemon": "#f5d800"}[t["item"]]
        ax.plot(*t["xy"], "o", color=col, mec="k", ms=8 if t["item"] == "orange" else 6)
        ax.annotate(t["item"], t["xy"], textcoords="offset points", xytext=(5, 5), fontsize=7)
    ax.plot(*sc["start"][:2], "k^", ms=8)
    ax.set_aspect("equal")
    ax.set_xlim(-h - 0.2, h + 0.2)
    ax.set_ylim(-h - 0.2, h + 0.2)


def fig_trajectories(d, out, sim="pybullet", seed=0):
    tdir = ROOT / "out" / "traj"
    sids = [s for s in SCENARIOS if s in set(d.scenario)]
    cfgs = sorted(d.config.unique())
    ncol = 5
    nrow = math.ceil(len(sids) / ncol)
    fig, axs = plt.subplots(nrow, ncol, figsize=(3.2 * ncol, 3.3 * nrow))
    for ax, sid in zip(np.ravel(axs), sids):
        draw_layout(ax, make_scenario(sid, seed))
        for c in cfgs:
            f = tdir / f"{sim}_{c}_{sid}_{seed}.csv"
            if f.exists():
                t = pd.read_csv(f)
                ax.plot(t.x, t.y, "-", lw=1.2, color=COLORS.get(c), label=CFG_NAMES.get(c, c))
        ax.set_title(f"{sid}: {SCENARIOS[sid]}", fontsize=9)
        ax.tick_params(labelsize=7)
    for ax in np.ravel(axs)[len(sids):]:
        ax.axis("off")
    h, l = np.ravel(axs)[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=len(cfgs), fontsize=9)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(out / f"fig_trajectories_seed{seed}.png")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default=str(ROOT / "out" / "results*.jsonl"), help="glob of jsonl files")
    ap.add_argument("--tag", default="main")
    a = ap.parse_args()
    out = ROOT / "out" / f"report_{a.tag}"
    out.mkdir(parents=True, exist_ok=True)
    import glob
    files = sorted(glob.glob(a.inp))
    d = pd.concat([pd.read_json(f, lines=True) for f in files], ignore_index=True)
    d = d.drop_duplicates(subset=["sim", "config", "scenario", "seed"], keep="last")
    for col in ["wrong_target", "correct_absence", "reported_found"]:
        if col in d:
            d[col] = d[col].astype("boolean")
    per = summarise(d)
    ov = overall(d)
    per.to_csv(out / "table_per_scenario.csv", index=False)
    ov.to_csv(out / "table_overall.csv", index=False)
    with open(out / "tables.md", "w", encoding="utf-8") as f:
        f.write("## Overall (T6 and T9 excluded from success_nav)\n\n" + ov.to_markdown(index=False) + "\n\n")
        f.write("## Per scenario\n\n" + per.drop(columns=["success_p"]).to_markdown(index=False) + "\n\n")
        pr = pd.DataFrame(score_parser())
        f.write(f"## Command parser (P4): {pr.correct.mean()*100:.0f}% of {len(pr)} phrasings correct\n\n")
        f.write(pr.to_markdown(index=False) + "\n")
    fig_success(d, out)
    fig_heatmap(d, out)
    fig_box(d, out, "dist_err", "|final distance - standoff| (m)", "fig_dist_error.png")
    fig_box(d, out, "min_clearance", "Min obstacle clearance (m)", "fig_clearance.png")
    fig_box(d, out, "time_to_success", "Time to success (s)", "fig_time_to_success.png")
    fig_latency(d, out)
    fig_trajectories(d, out)
    print(ov.to_string(index=False))
    print(f"\nwritten to {out}")


if __name__ == "__main__":
    main()
