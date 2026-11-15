// --------------------------------------------------------------- Chapter 3 start: research & design process
chapter = 3;
add(H1("3. Description"));
add(P(`This chapter first documents how the project moved from a broad problem space to a narrow, testable core (Section 3.1). It then presents the analysis (3.2), design (3.3), simulation environment and its compatibility with each robot (3.4), implementation methodology (3.5), hardware and software (3.6), and the results of seven experiments with discussion (3.7).`));

add(H2("3.1 Research and Design Process"));
add(H3("3.1.1 Project Phases"));
const fPh = fig("fig_phases.png", 6.4, "Project phases: Phases 0–2 are covered in this report; Phases 3–5 are planned");
add(P(`The work was organised in phases with an explicit question and exit criterion each (${fPh.label}). **Phase 0** framed the problem: literature on VLA/VLN models, drone VLAs, memory and cross-embodiment learning; the research proposal; and the choice of tools. **Phase 1** answered the narrowest question — can a drone find and approach a named object safely using only pretrained models — with seven perception/decision configurations in two simulators. **Phase 1b** widened the *tasks* (helipad landing) and the *embodiments* (ground robot, arm) without changing the intelligence layer. **Phase 2** added persistent memory and multi-step missions in a multi-room building. Phases 3–5 (scene-graph memory with an LLM task planner, real hardware, learned adapters) are planned in Chapter 4.`));
add(fPh);
add(H3("3.1.2 Options Considered and How They Were Narrowed"));
const fFun = fig("fig_funnel.png", 6.2, "From the explored problem space to the narrow questions that were tested");
add(P(`Many alternatives were considered before implementation (${fFun.label}). They were filtered with six criteria: it must run on the available laptop (8 GB GPU, Windows), require no robot-specific training, allow hundreds of repeatable episodes, keep safety independent of the AI, and transfer to affordable real hardware. The main decisions are summarised below.`));
add(fFun);
add(table("Key design decisions, alternatives considered and reasons", ["Decision", "Alternatives considered", "Chosen", "Reason (evidence)"], [
  ["Control architecture", "End-to-end VLA (OpenVLA-7B, SmolVLA, X-VLA); VLM as pilot; modular", "Modular pipeline; VLM only for semantics", "VLAs output arm actions and need flight data {cogdrone}; VLM-as-pilot failed (C4: 0 %)"],
  ["Perception", "Colour; YOLO-World; OWLv2; Grounding DINO; CLIP; SmolVLM; hybrid", "Detector proposals + SmolVLM verification", "Best accuracy/latency trade-off (C5: 96 %, ~19 ms) and robust across simulators"],
  ["Large models in the plan (OpenVLA-7B, NavGPT)", "Run locally; cloud; replace with small models", "Small zero-shot models locally", "7 B needs ~15 GB VRAM; NavGPT assumes a discrete navigation graph"],
  ["Simulator", "Gazebo+PX4, Isaac Sim, AirSim, Webots, Habitat, PyBullet, MuJoCo", "PyBullet (primary) + MuJoCo (cross-check)", "Windows-native, fast, supports drone, wheeled robot and arm models on an 8 GB GPU"],
  ["Embodiments", "Drone only; + ground robot; + arm; + quadruped", "Drone, Husky ground robot, Franka Panda arm", "Covers flying, driving and manipulating with one intelligence layer"],
  ["Tasks", "Object approach; helipad landing; multi-object missions; pick; delivery", "First four", "Each isolates one capability (semantics, precision landing, memory, manipulation)"],
  ["Memory", "None; object map; full 3-D scene graph", "Object map + explored rooms (Phase 2)", "Smallest memory that answers RQ2; scene graph deferred to Phase 3"],
  ["Range sensing", "8-beam ToF ring; 24-beam ring; depth only", "24 beams from Phase 2", "Sensor ablation: near-misses 7/40 → 0/40"],
], [16, 30, 22, 32]));
add(H3("3.1.3 Design Iterations"));
const tIt = table("Design iterations: what was tried, what was measured, what changed", ["#", "Version tried", "Observed (measured)", "Change made"], [
  ["1", "Planner treats all depth points as obstacles", "Drone hovered 0.8 m from target; never reached stand-off", "Exclude tracked target from planner obstacles; safety filter unchanged"],
  ["2", "Camera pitched −15°, fixed altitude", "Target left the field of view at 0.5 m", "Final-approach descent to target height + 0.15 m"],
  ["3", "Colour thresholds (S > 120)", "Wooden tables detected as 'orange'", "Stricter saturation/brightness; motivates semantic detectors"],
  ["4", "Depth at object surface", "Stopped ~12 cm too far", "Surface-to-centre radius correction"],
  ["5", "YOLO-World prompt 'orange'", "Score 0.05 on rendered orange (0.21 with 'orange fruit')", "Prompt study; low-threshold proposals + VLM verification (C5)"],
  ["6", "VLM verifier: 'real orange fruit?'", "Said 'no' to most crops", "Calibrated wording + 12 px minimum crop; ablation C6 added"],
  ["7", "Cluttered scenario T4 (random pillars)", "As easy as an open room", "Pillars placed on the direct path; T4 re-run"],
  ["8", "8-beam range ring", "Near-misses down to 1.7 cm (no collisions)", "24-beam ring (multi-zone ToF) adopted for Phase 2"],
  ["9", "Pad verifier v1: VLM reads pads at an angle", `Nearest-helipad landing ${v(hpAll("v1").strict3)} % (L1–L3); real H pads seen at an angle were rejected`, "v2: verify only from directly above (gimbal −90°)"],
  ["10", "Pad verifier v2 (top-down)", "Rotated 'H' read as 'I'; partial pads voted", "v3: whole-pad check + rotation-invariant query"],
  ["11", "Pad verifier v3", `Nearest-helipad landing ${v(hpAll("v3").strict3)} % (L1–L3); 0 % in dim light`, "Kept; dim-light failure traced to the colour proposal stage (Section 3.7.11)"],
  ["12", "7 GPU processes in parallel", "Out-of-memory crashes", "Fewer parallel runs, resumable batches"],
], [5, 28, 34, 33]);
add(P(`Development was iterative: each version was measured, and changes were made only in response to a measured failure. ${tIt.label} lists the most important iterations; the full problem log is in Section 3.7.9.`));
add(tIt);
add(H3("3.1.4 Hypotheses"));
add(P(`Hypotheses were written down before the corresponding experiments were run, so that results could confirm or reject them rather than be explained after the fact:`));
add(table("Pre-registered hypotheses", ["ID", "Hypothesis", "Experiment"], [
  ["H1", "Detectors perform better with the more realistic renderer (MuJoCo) than with PyBullet's TinyRenderer", "Exp. 2"],
  ["H2", "Richer dynamics (6-DOF, un-gimballed camera) slow missions but do not reduce success", "Exp. 2"],
  ["H3", "Simulators agree on simple scenes and differ most with distractors", "Exp. 2"],
  ["H4", "Link-loss behaviour is only realistic with real firmware", "Exp. 1 (T9)"],
  ["H5", "No single simulator is closest to reality on every axis", "Phase 4 (needs real data)"],
  ["H6", "Persistent memory reduces total mission time by ≥ 20 % on repeated missions", "Exp. 7"],
  ["H7", "The same intelligence layer achieves comparable success on a ground robot with only an adapter change", "Exp. 5"],
  ["H8", "VLM verification reduces decoy landings compared with a colour-only pad detector", "Exp. 4"],
  ["H9", "Perception rankings on the arm match those on the drone (hybrid > colour under distractors)", "Exp. 6"],
], [7, 73, 20]));
