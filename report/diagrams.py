"""Draws the design diagrams for the report (block diagram, mission flowchart,
use-case diagram, DFD level 0/1, staged roadmap) as PNGs in report/figs/."""
import sys
from pathlib import Path

sys.path.insert(0, r"D:\pinnacle\sim")
import dronenav  # noqa: F401  (cache dirs on D:)
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).resolve().parent / "figs"
OUT.mkdir(exist_ok=True)
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 10})
C = dict(lap="#e8f1fb", ai="#fde9d9", safe="#fce4e4", drone="#e6f4ea", io="#f3f3f3", edge="#333333")


def box(ax, x, y, w, h, text, fc, fs=9.5, bold=False, ec=None, lw=1.2, round_=0.04):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0.01,rounding_size={round_}",
                                fc=fc, ec=ec or C["edge"], lw=lw))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal", wrap=True)


def arrow(ax, p, q, text=None, style="-|>", color="#333", ls="-", off=(0, 0), fs=8.5, rad=0.0):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=12, color=color, lw=1.2, ls=ls,
                                 connectionstyle=f"arc3,rad={rad}"))
    if text:
        ax.text((p[0] + q[0]) / 2 + off[0], (p[1] + q[1]) / 2 + off[1], text, fontsize=fs, ha="center",
                va="center", color=color, bbox=dict(fc="white", ec="none", pad=0.5))


def canvas(w, h):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis("off")
    return fig, ax


def save(fig, name):
    fig.savefig(OUT / name, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ------------------------------------------------------------------ block diagram
def block_diagram():
    fig, ax = canvas(10, 7.4)
    ax.add_patch(FancyBboxPatch((0.15, 1.75), 9.7, 5.5, boxstyle="round,pad=0.02", fc="#fbfdff", ec="#6b8bb5",
                                lw=1.5, ls="--"))
    ax.text(0.35, 7.05, "LAPTOP  (ground station: Python / ROS 2-ready)", fontsize=10, fontweight="bold",
            color="#2c4f7c")
    box(ax, 0.4, 5.9, 2.6, 0.8, "Operator command\n\"find and approach the orange\"", C["io"])
    box(ax, 3.5, 5.9, 2.7, 0.8, "[1] Command parser\nNL → mission JSON\n(target, stand-off, speed)", C["lap"])
    box(ax, 6.7, 5.9, 2.9, 0.8, "[2] Mission state machine\nTAKEOFF→SEARCH→APPROACH\n→HOLD→FOUND / NOT_FOUND", C["lap"])
    box(ax, 0.4, 4.1, 2.9, 1.2, "[3] Perception\nopen-vocab detector\n(YOLO-World / OWLv2)\n+ VLM verifier + depth", C["ai"])
    box(ax, 3.6, 4.1, 2.6, 1.2, "[4] Target belief &\nlocal world model\n(tracker, obstacle\nsectors from depth+ToF)", C["lap"])
    box(ax, 6.7, 4.1, 2.9, 1.2, "[5] Planner\nsearch (spin + waypoints)\napproach to stand-off\nlocal avoidance", C["lap"])
    box(ax, 3.0, 2.15, 6.6, 1.15,
        "[6] SAFETY FILTER  (no ML, always on, final authority)\nspeed / accel clamps · geofence · altitude band\n"
        "min clearance from RAW range & depth data", C["safe"], fs=9)
    arrow(ax, (3.0, 6.3), (3.5, 6.3))
    arrow(ax, (6.2, 6.3), (6.7, 6.3))
    arrow(ax, (3.3, 4.7), (3.6, 4.7), "detections", off=(0, 0.25))
    arrow(ax, (6.2, 4.7), (6.7, 4.7), "belief", off=(0, 0.25))
    arrow(ax, (8.15, 5.9), (8.15, 5.3))
    arrow(ax, (8.15, 4.1), (8.15, 3.3), "v_cmd, yaw_rate", off=(0.75, 0))
    # drone
    ax.add_patch(FancyBboxPatch((0.15, 0.05), 9.7, 1.35, boxstyle="round,pad=0.02", fc="#f7fcf8", ec="#3d8b55",
                                lw=1.5, ls="--"))
    ax.text(0.35, 1.2, "DRONE", fontsize=10, fontweight="bold", color="#2f6b41")
    box(ax, 0.4, 0.2, 2.3, 0.85, "Sensors\nRGB camera · depth\nToF ring · flow+height", C["drone"], fs=8.5)
    box(ax, 3.3, 0.2, 3.5, 0.85, "Flight controller (PX4 / emulated)\nattitude & velocity loops, state estimate\n"
                                 "FAILSAFE: no setpoint 0.5 s→hover, 3 s→land", C["drone"], fs=8.5)
    box(ax, 7.4, 0.2, 2.3, 0.85, "Independent RC link\n(safety pilot / kill)", C["drone"], fs=8.5)
    arrow(ax, (6.3, 2.15), (5.05, 1.05), "setpoints @ 20 Hz (wireless)", off=(1.0, 0.0))
    arrow(ax, (1.55, 1.05), (1.55, 4.1), "images, depth,\nranges, pose", ls="--", color="#2f6b41", off=(0.0, 0.0))
    arrow(ax, (7.4, 0.62), (6.8, 0.62), color="#a33")
    save(fig, "fig_block_diagram.png")


# ------------------------------------------------------------------ flowchart
def flowchart():
    fig, ax = canvas(9, 8.2)
    W, H = 2.6, 0.62
    nodes = {
        "start": (3.2, 7.4, "Receive command\nparse → mission JSON"),
        "clar": (6.4, 7.4, "Ask operator\nto clarify"),
        "take": (3.2, 6.4, "TAKEOFF to 1.0 m"),
        "spin": (3.2, 5.3, "SEARCH_SPIN\nyaw 360° at 0.7 rad/s"),
        "move": (6.4, 5.3, "SEARCH_MOVE\nnext waypoint + avoidance"),
        "appr": (3.2, 3.9, "APPROACH\ngoal = target − stand-off\nfinal descent, face target"),
        "hold": (3.2, 2.7, "HOLD 1.5 s\n|d − 0.5 m| < 0.1 m, speed < 0.12"),
        "found": (3.2, 1.45, "FOUND → report, hover"),
        "nf": (6.4, 2.7, "NOT_FOUND → report,\nhover/land"),
        "abort": (0.1, 2.7, "FAILSAFE (FC)\nlink lost 0.5 s → hover\n3 s → land"),
    }
    fcs = {"start": C["io"], "clar": C["io"], "found": C["drone"], "nf": "#fff4cc", "abort": C["safe"]}
    for k, (x, y, t) in nodes.items():
        box(ax, x, y, W, H if k not in ("appr", "abort") else 0.8, t, fcs.get(k, C["lap"]), fs=8.5)
    a = lambda p, q, t=None, off=(0, 0), rad=0: arrow(ax, p, q, t, off=off, rad=rad, fs=8)  # noqa: E731
    a((5.8, 7.71), (6.4, 7.71), "ambiguous", off=(0, 0.2))
    a((4.5, 7.4), (4.5, 7.02), "ok", off=(0.25, 0))
    a((4.5, 6.4), (4.5, 5.92))
    a((5.8, 5.61), (6.4, 5.61), "360° done,\nnot seen", off=(0, 0.35))
    a((6.4, 5.45), (5.8, 5.45), "waypoint\nreached", off=(0, -0.33))
    a((4.5, 5.3), (4.5, 4.7), "target confirmed\n(≥3 hits)", off=(0.85, 0))
    a((4.5, 3.9), (4.5, 3.32))
    a((4.5, 2.7), (4.5, 2.07), "held", off=(0.3, 0))
    a((7.7, 5.3), (7.7, 3.32), "no waypoints left\nor time budget", off=(0.85, 0))
    a((3.2, 4.3), (3.2, 5.5), "target lost > 4 s", off=(-0.95, 0), rad=-0.6)
    ax.text(0.1, 3.75, "Any state:", fontsize=8.5, fontweight="bold", color="#a33")
    ax.text(0.0, 0.6, "Safety filter wraps every velocity command in every state (block diagram, block 6).",
            fontsize=8.5, style="italic")
    save(fig, "fig_flowchart.png")


# ------------------------------------------------------------------ use case
def usecase():
    fig, ax = canvas(9, 5.6)

    def actor(x, y, name):
        ax.add_patch(plt.Circle((x, y + 0.75), 0.15, fill=False, lw=1.2))
        ax.plot([x, x], [y + 0.6, y + 0.15], "k", lw=1.2)
        ax.plot([x - 0.25, x + 0.25], [y + 0.45, y + 0.45], "k", lw=1.2)
        ax.plot([x, x - 0.2], [y + 0.15, y - 0.2], "k", lw=1.2)
        ax.plot([x, x + 0.2], [y + 0.15, y - 0.2], "k", lw=1.2)
        ax.text(x, y - 0.5, name, ha="center", fontsize=9)

    ax.add_patch(FancyBboxPatch((2.0, 0.2), 5.0, 5.2, boxstyle="round,pad=0.02", fc="#fbfdff", ec="#555"))
    ax.text(4.5, 5.15, "Language-commanded drone system", ha="center", fontweight="bold")
    ucs = [("Issue NL command", 4.5), ("Clarify ambiguous command", 3.85), ("Monitor camera / status", 3.2),
           ("Search for target", 2.55), ("Approach & hold stand-off", 1.9), ("Report found / not found", 1.25),
           ("Abort / take over (RC)", 0.6)]
    pos = {}
    for t, y in ucs:
        ax.add_patch(Ellipse((4.5, y), 3.4, 0.5, fc="#eef4fb", ec="#333"))
        ax.text(4.5, y, t, ha="center", va="center", fontsize=9)
        pos[t] = y
    actor(0.8, 3.3, "Operator")
    actor(0.8, 0.9, "Safety pilot")
    actor(8.2, 2.3, "Drone\n(FC + sensors)")
    for t in ["Issue NL command", "Clarify ambiguous command", "Monitor camera / status", "Report found / not found"]:
        ax.plot([1.1, 2.8], [3.75, pos[t]], "k", lw=0.8)
    ax.plot([1.1, 2.8], [1.2, pos["Abort / take over (RC)"]], "k", lw=0.8)
    for t in ["Search for target", "Approach & hold stand-off", "Abort / take over (RC)"]:
        ax.plot([7.9, 6.2], [2.7, pos[t]], "k", lw=0.8)
    save(fig, "fig_usecase.png")


# ------------------------------------------------------------------ DFD
def dfd():
    fig, ax = canvas(10, 5.2)
    ax.text(0.1, 4.95, "Level 0", fontweight="bold")
    box(ax, 0.2, 3.7, 1.8, 0.8, "Operator", C["io"])
    ax.add_patch(plt.Circle((5.0, 4.1), 0.75, fc=C["lap"], ec="#333"))
    ax.text(5.0, 4.1, "0\nNavigation\nsystem", ha="center", va="center", fontsize=9)
    box(ax, 8.0, 3.7, 1.8, 0.8, "Drone", C["drone"])
    arrow(ax, (2.0, 4.25), (4.25, 4.25), "command", off=(0, 0.18))
    arrow(ax, (4.25, 3.95), (2.0, 3.95), "status, video, report", off=(0, -0.18))
    arrow(ax, (5.75, 4.25), (8.0, 4.25), "velocity setpoints", off=(0, 0.18))
    arrow(ax, (8.0, 3.95), (5.75, 3.95), "images, depth, ranges, pose", off=(0, -0.18))
    ax.plot([0.1, 9.9], [3.3, 3.3], color="#999", lw=0.8, ls="--")
    ax.text(0.1, 3.05, "Level 1", fontweight="bold")
    procs = [(1.0, "1.0\nParse"), (2.9, "2.0\nPerceive"), (4.8, "3.0\nTrack &\nmap"), (6.7, "4.0\nPlan"),
             (8.6, "5.0\nSafety\nfilter")]
    for x, t in procs:
        ax.add_patch(plt.Circle((x, 1.9), 0.62, fc=C["lap"] if "Safety" not in t else C["safe"], ec="#333"))
        ax.text(x, 1.9, t, ha="center", va="center", fontsize=8.5)
    for (x1, _), (x2, _), lab in zip(procs[:-1], procs[1:], ["mission JSON", "detections", "target belief,\nobstacle sectors", "v_cmd"]):
        arrow(ax, (x1 + 0.62, 1.9), (x2 - 0.62, 1.9), lab, off=(0, 0.42), fs=7.5)
    ax.plot([3.6, 6.0], [0.55, 0.55], "k", lw=1)
    ax.plot([3.6, 6.0], [0.2, 0.2], "k", lw=1)
    ax.text(4.8, 0.37, "D1  episode log (trajectory, states, metrics)", ha="center", va="center", fontsize=8)
    arrow(ax, (4.8, 1.28), (4.8, 0.55), fs=7)
    arrow(ax, (8.6, 1.28), (6.0, 0.4), fs=7)
    save(fig, "fig_dfd.png")


# ------------------------------------------------------------------ roadmap
def roadmap():
    fig, ax = canvas(10, 2.6)
    st = [("Stage 1\nSimulation\n(PyBullet + MuJoCo)", "#cfe8d5", "DONE"),
          ("Stage 2\nDJI Neo 2\nshadow mode", "#fff1c2", "READY\n(needs footage)"),
          ("Stage 3\nPX4 SITL + Gazebo\nreal firmware", "#e8eef8", "PLANNED"),
          ("Stage 4\nCustom drone:\nbench, tether", "#e8eef8", "PLANNED"),
          ("Stage 5\nSupervised flights\n+ VLA adaptation", "#e8eef8", "PLANNED")]
    for i, (t, fc, s) in enumerate(st):
        x = 0.1 + i * 2.0
        box(ax, x, 0.9, 1.75, 1.3, t, fc, fs=8.5)
        ax.text(x + 0.875, 0.55, s, ha="center", va="center", fontsize=8, fontweight="bold")
        if i < len(st) - 1:
            arrow(ax, (x + 1.75, 1.55), (x + 2.0, 1.55))
    save(fig, "fig_roadmap.png")


if __name__ == "__main__":
    block_diagram()
    flowchart()
    usecase()
    dfd()
    roadmap()
    print("ok", sorted(p.name for p in OUT.glob("*.png")))


# ------------------------------------------------------------------ design funnel
def funnel():
    fig, ax = canvas(11, 7.2)
    layers = [
        ("PROBLEM SPACE (explored)", "#eef3fb", 0.15, 10.7,
         "Robots: drone · wheeled robot · arm · quadruped     Control: end-to-end VLA · mid-level VLA · modular pipeline\n"
         "Perception: colour · YOLO-World · OWLv2 · Grounding DINO · CLIP · small VLM · hybrid     Memory: none · object map · scene graph\n"
         "Simulators: Gazebo+PX4 · Isaac Sim · AirSim · Webots · Habitat · PyBullet · MuJoCo     Tasks: object search · landing · multi-step missions · pick"),
        ("SELECTION CRITERIA", "#fff4d6", 0.9, 9.2,
         "runs on an 8 GB laptop GPU · Windows-native · no robot-specific training · measurable in < 2 min per episode ·\n"
         "safety kept independent of AI · transferable to real affordable hardware (Neo 2 / custom drone / small UGV)"),
        ("CHOSEN CORE (built + tested)", "#e3f2e6", 1.8, 7.4,
         "Modular pipeline + independent safety filter · zero-shot detectors + small-VLM verifier ·\n"
         "PyBullet (primary) + MuJoCo (cross-check) · drone first, then ground robot + arm via thin adapters ·\n"
         "tasks: find/approach object, find nearest helipad and land, multi-object missions with memory, pick"),
        ("TESTED NARROW QUESTIONS", "#fde7e7", 2.9, 5.2,
         "Which perception works? (7 configs) · Does memory shorten missions?\n"
         "Does the same brain run on 3 robots? · Which simulator is closer to reality?"),
    ]
    y = 6.9
    for title, fc, x, w, txt in layers:
        h = 1.25 if title.startswith("PROBLEM") else 1.05
        box(ax, x, y - h, w, h, "", fc)
        ax.text(x + w / 2, y - 0.17, title, ha="center", va="center", fontsize=9.5, fontweight="bold")
        ax.text(x + w / 2, y - h / 2 - 0.1, txt, ha="center", va="center", fontsize=8.2)
        if not title.startswith("TESTED"):
            arrow(ax, (5.5, y - h - 0.02), (5.5, y - h - 0.33))
        y -= h + 0.38
    box(ax, 3.4, 0.15, 4.2, 0.75, "ANALYSIS → hypotheses for the next phase\n(memory scene graph, LLM task planner, real hardware)", "#ede7f6", fs=8.5)
    arrow(ax, (5.5, y + 0.36), (5.5, 0.92))
    save(fig, "fig_funnel.png")


# ------------------------------------------------------------------ layered architecture
def layered():
    fig, ax = canvas(11, 6.4)
    box(ax, 0.2, 5.5, 10.6, 0.7, "Natural-language mission  —  \"find the apple, then the lemon\"  ·  \"find the nearest helipad and land\"  ·  \"pick up the orange\"", C["io"], fs=9)
    ax.add_patch(FancyBboxPatch((0.2, 1.75), 10.6, 3.5, boxstyle="round,pad=0.02", fc="#fbfdff", ec="#6b8bb5", lw=1.5, ls="--"))
    ax.text(0.4, 5.05, "SHARED INTELLIGENCE LAYER (identical code for every robot, laptop-hosted)", fontsize=9.5, fontweight="bold", color="#2c4f7c")
    box(ax, 0.45, 3.35, 2.35, 1.4, "Mission parser\n& subtask queue\n(approach X | land)", C["lap"], fs=8.5)
    box(ax, 3.0, 3.35, 2.45, 1.4, "Perception\ndetector proposals +\nVLM verification + depth", C["ai"], fs=8.5)
    box(ax, 5.65, 3.35, 2.45, 1.4, "Persistent semantic\nmemory\nobjects · rooms explored", "#e8f5e9", fs=8.5)
    box(ax, 8.3, 3.35, 2.3, 1.4, "Planner\nexplore · go-to via doors\napproach · align · land", C["lap"], fs=8.5)
    box(ax, 0.45, 1.95, 10.15, 1.1, "Independent safety filter (no ML): speed limits · geofence · clearance from raw range + depth · altitude rules", C["safe"], fs=8.8)
    for x in (2.8, 5.45, 8.1):
        arrow(ax, (x, 4.05), (x + 0.2, 4.05))
    arrow(ax, (1.62, 5.5), (1.62, 4.77))
    ax.text(5.5, 1.5, "common interface:  world-frame velocity setpoint (vx, vy, vz, yaw-rate)  ·  3-D target point", ha="center", fontsize=8.8, style="italic")
    for x, name, adapt, col in [(0.4, "DRONE", "adapter: velocity loop + gimbal\nFC fail-safe (hover → land)", C["drone"]),
                                (3.95, "GROUND ROBOT", "adapter: (vx,vy,ψ̇) → (v, ω) unicycle\n~10 lines, no training data", C["drone"]),
                                (7.5, "ROBOT ARM", "adapter: 3-D point → inverse\nkinematics → joint targets", C["drone"])]:
        box(ax, x, 0.1, 3.15, 1.05, f"{name}\n{adapt}", col, fs=8.4)
        arrow(ax, (x + 1.57, 1.95), (x + 1.57, 1.17))
    save(fig, "fig_layered.png")


# ------------------------------------------------------------------ phases
def phases():
    fig, ax = canvas(11, 3.6)
    st = [("Phase 0", "Problem framing\nliterature, options,\nproposal", "#cfe8d5", "DONE"),
          ("Phase 1", "Single goal on a drone\n7 perception configs,\n2 simulators", "#cfe8d5", "DONE"),
          ("Phase 1b", "Task + embodiment\ndiversity: helipad,\nground robot, arm", "#cfe8d5", "DONE (sim)"),
          ("Phase 2", "Persistent memory,\nmulti-step missions\nin a house", "#e3f0d0", "INITIAL STUDY"),
          ("Phase 3", "Scene graph + LLM\ntask planner,\nreplanning", "#e8eef8", "PLANNED"),
          ("Phase 4", "Real hardware: Neo 2\nshadow mode, custom\ndrone, small UGV", "#fff1c2", "NEXT"),
          ("Phase 5", "Learned adapters /\nVLA fine-tuning,\ndata efficiency", "#e8eef8", "PLANNED")]
    for i, (t, d, fc, s) in enumerate(st):
        x = 0.1 + i * 1.56
        box(ax, x, 1.0, 1.4, 2.2, "", fc)
        ax.text(x + 0.7, 2.95, t, ha="center", fontweight="bold", fontsize=9.5)
        ax.text(x + 0.7, 1.95, d, ha="center", va="center", fontsize=7.8)
        ax.text(x + 0.7, 0.65, s, ha="center", fontsize=8, fontweight="bold", color="#2f6b41" if "DONE" in s else "#555")
        if i < len(st) - 1:
            arrow(ax, (x + 1.4, 2.1), (x + 1.56, 2.1))
    ax.text(5.5, 0.15, "this report: Phases 0–2 (simulation)          next semester: Phases 3–5", ha="center", fontsize=9, style="italic")
    save(fig, "fig_phases.png")


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "new":
    funnel()
    layered()
    phases()
    print("new diagrams ok")
