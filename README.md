# Language-Guided Robots on Affordable Hardware

**Persistent memory and cross-embodiment transfer — Phase 0–2 design and simulation study**
Design Project Minor (CPT 401), uGDX School of Technology, AY 2026–27.

A laptop-hosted modular agent turns natural-language instructions (*"find the orange"*, *"land on the nearest helipad"*, *"find the apple, then the lemon"*, *"pick up the orange"*) into safe action on a **drone**, a **ground robot** and a **robot arm**, using only pretrained models (zero robot-specific training), a persistent semantic memory, a classical planner and an independent safety filter.

## Key results (simulation)

| Experiment | Result |
|---|---|
| Perception on the drone (7 configs, ~1,400 episodes) | Detector + small-VLM verifier: 96 % success at ~19 ms/frame; small VLM used as the pilot: 0 % |
| Find the nearest helipad and land | 87 % in normal light after 3 verifier iterations (colour-only: 67 %); dim light unsolved (0 %) |
| Same intelligence layer on a ground robot | 100 % with perfect perception; hybrid perception 83 % → 67 % (needs per-camera calibration) |
| Robot arm pick-up | 100 % with perfect perception; hybrid 50–90 % |
| Persistent memory, repeated missions | −35 % (drone) / −27 % (ground robot) mission time, 100 % object recall |
| Safety layer | 0 collisions with perfect perception; 24-beam ranging raised min clearance 2.4 → 11.9 cm |

## Repository layout

```
sim/dronenav/      simulator adapters, perception, planner, safety filter, memory, agents
sim/*.py           experiment runners, analysis, demo/video tools, interactive flight (fly.py)
sim/out/           results (*.jsonl), analysis tables, demo videos
report/            report generator (build_report2.js + parts/), figures, final report (.docx/.pdf)
report/build_deck.py, Pinnacle_Presentation_Phase1-2.pptx   presentation
project_plan.md, problems_log.md   planning document and the problem/iteration log
```

## Reproduce

```powershell
py -3.12 -m venv .venv
.venv\Scripts\pip install pybullet mujoco numpy opencv-python matplotlib pandas pyyaml tabulate
.venv\Scripts\pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
.venv\Scripts\pip install ultralytics transformers accelerate
. .\env.ps1                                   # caches on D:\pinnacle\.cache
python run_batch.py --configs C0,C1 --seeds 20  # Phase 1
python run_world.py --exp L                     # Phase 1b-2: O | L | M | A
python fly.py --scenario T4                     # fly the drone yourself
```

See `CONTRIBUTIONS.md` for team roles.
