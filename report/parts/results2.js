// --------------------------------------------------------------- 3.7 new results (Phase 1b-2)
add(H3("3.7.10 Result Sequences: Finding the Orange"));
const fOD = fig("shot_result_orange_drone.png", 4.6, "Drone, scenario O3 (distractors): search, detection of all objects with distances, approach, and final hold at the stand-off (observer camera and trajectory)");
const fOG = fig("shot_result_orange_ground.png", 4.6, "The same task on the ground robot: identical intelligence layer, unicycle adapter, mast camera");
add(P(`${fOD.label} and ${fOG.label} show complete runs frame by frame: the robot's camera with every detected object and its estimated distance, an observer camera, the final pose and the top-down trajectory with the result. These sequences correspond to individual episodes of the experiments summarised below.`));
add(fOD, fOG);

// ---------------- Experiment 4: helipad
add(H3("3.7.11 Experiment 4 — Find the Nearest Helipad and Land"));
const fLS = fig("shot_result_landing.png", 4.5, "Helipad mission with verifier v3: 360° search at 1.6 m, nearest candidate (an X decoy) checked from above and rejected, next-nearest pad confirmed as a helipad, alignment, descent and landing");
const fLC = fig("res_helipad.png", 6.3, "Landed on the nearest helipad, by detector and scenario (10 seeds each, 95 % CI)");
const pads = ["Oracle", "Ring detector (colour)", "VLM verifier v1 (oblique)", "VLM verifier v3 (top-down, rot.-inv.)"];
const tL = table("Helipad landing results (10 seeds per cell)", ["Scenario", "Detector", "Landed on a helipad", "Landed on the nearest", "Decoy landings", "Landing error (cm)", "Median time (s)", "Collisions"],
  ["L1", "L2", "L3", "L4"].flatMap((t) => pads.map((p) => { const r = HP(t, p); return r.n ? [t, p, `${r.success} %`, `${r.strict} %`, `${r.decoy_landings}`, v(r.land_err_med, 1), v(r.time_med, 1), `${r.collisions}`] : null; }).filter(Boolean)),
  [9, 31, 11, 11, 9, 10, 10, 9], { center: true });
const o = hpAll("oracle"), rg = hpAll("ring"), v1 = hpAll("v1"), v3 = hpAll("v3");
add(P(`${fLS.label} shows one complete mission with the final verifier. Two measures are reported: landing on *a* helipad (within 0.2 m, not a decoy) and the task as stated — landing on the **nearest** helipad. In normal light (L1–L3) nearest-helipad success was ${v(o.strict3)} % with the oracle, ${v(rg.strict3)} % with the colour-only ring detector, ${v(v1.strict3)} % with verifier v1 and **${v(v3.strict3)} % with verifier v3**; in dim light (L4) every real detector scored 0 % (${fLC.label}, ${tL.label}).`));
add(B([
  `**Colour alone cannot read markings.** The ring detector found every pad and succeeded without decoys (L1 ${v(HP("L1", PADNAMES.ring).strict)} %, L2 ${v(HP("L2", PADNAMES.ring).strict)} %), but landed on a decoy in ${rg.dec} of 10 runs once a decoy was nearer than the real helipad (L3). This supports H8.`,
  `**The first VLM verifier landed on the wrong helipad.** v1 judged pads from an oblique view, rejected nearby real H pads and flew on to farther ones: it landed on *a* helipad in ${v(HP("L2", PADNAMES.v1).success)} % of L2 runs but on the *nearest* one in only ${v(HP("L2", PADNAMES.v1).strict)} %.`,
  `**Active verification fixed this.** Checking each candidate from directly above with a rotation-invariant query (v3) raised nearest-helipad success to ${v(HP("L1", PADNAMES.v3).strict)} % (L1), ${v(HP("L2", PADNAMES.v3).strict)} % (L2) and ${v(HP("L3", PADNAMES.v3).strict)} % (L3), with no decoy landings and a median landing error of ${v(HP("L1", PADNAMES.v3).land_err_med, 1)}–${v(HP("L2", PADNAMES.v3).land_err_med, 1)} cm. Two L3 runs touched an obstacle while flying between candidates. The design lesson — change the viewpoint to make perception easier — transfers directly to the real drone, whose gimbal can point straight down.`,
  `**Dim light defeats the proposal stage, not the planner.** With perfect perception L4 succeeded in every run, but the colour-based ring detector found no pads in dim light, so the verifier never received a candidate. The weakest link is the first perception stage; a learned pad detector, exposure control or fiducial markers (as used in real precision landing) are needed.`,
]));
add(fLS, fLC, tL);

// ---------------- Experiment 5: cross-embodiment
add(H3("3.7.12 Experiment 5 — Same Intelligence Layer on a Drone and a Ground Robot"));
const fXE = fig("res_xemb.png", 6.4, "Object-approach success on the drone (solid) and the ground robot (hatched) with oracle, colour and hybrid perception");
const tXE = table("Cross-embodiment results (10 seeds per cell)", ["Task", "Robot", "Perception", "Success", "Wrong target", "Median time (s)", "Path (m)", "Collisions", "Min clearance (m)"],
  ["O1", "O2", "O3"].flatMap((t) => ["drone", "ground"].flatMap((e) => ["oracle", "hsv", "hybrid"].map((p) => { const r = XE(t, e, p); return r.n ? [t, e, p, `${r.success} %`, `${r.wrong}`, v(r.time_med, 1), v(r.path_med, 1), `${r.collisions}`, v(r.clear_min, 2)] : null; }).filter(Boolean))),
  [7, 10, 11, 10, 10, 13, 10, 12, 17], { center: true });
add(P(`The ground robot ran the identical mission, perception, memory, planner and safety code; only the adapter (Section 3.5.11), the camera mount and the stand-off distance differed (${fXE.label}, ${tXE.label}). Three findings follow.`));
add(B([
  `**The shared planning layer transfers completely.** With perfect perception both robots succeeded in every run of every task (drone ${v(xeAll("drone", "oracle"))} %, ground ${v(xeAll("ground", "oracle"))} %), with zero collisions — search, routing, approach, memory and safety needed no change beyond the adapter.`,
  `**Semantic verification pays off only when look-alikes are present.** Without distractors (O1, O2) colour thresholding was perfect and fastest on both robots, while the hybrid lost 20–30 % of runs to missed or late detections. With distractors (O3) the picture reverses on the drone: hybrid ${v(XE("O3", "drone", "hybrid").success)} % vs colour ${v(XE("O3", "drone", "hsv").success)} % (colour approached a look-alike in ${XE("O3", "drone", "hsv").wrong} of 10 runs).`,
  `**Perception does not transfer as freely as planning.** On the ground robot's low mast camera the hybrid reached only ${v(XE("O3", "ground", "hybrid").success)} % in O3 (colour ${v(XE("O3", "ground", "hsv").success)} %), with ${XE("O3", "ground", "hybrid").collisions} contact events, and ${v(xeAll("ground", "hybrid"))} % overall against ${v(xeAll("drone", "hybrid"))} % on the drone. The detector and verifier were tuned on the drone's elevated, oblique views; a flatter viewpoint changes what they see. Together with the arm result (Section 3.7.13) this shows that the intelligence layer is portable, but the perception front-end must be re-calibrated for each embodiment's camera geometry.`,
]));
add(fXE, tXE);

// ---------------- Experiment 6: arm
add(H3("3.7.13 Experiment 6 — Robot Arm: Pick Up the Orange"));
const fAS = fig("shot_result_arm.png", 6.2, "Arm episode (A2, distractors): fixed camera view, moving above the orange, descending, grasping, lifting; the orange ball, cube and lemon are ignored");
const fAC = fig("res_arm.png", 4.8, "Pick success by perception (10 seeds each)");
const tA = table("Arm results (10 seeds per cell)", ["Task", "Perception", "Success", "Picked wrong object", "Missed", "Target not found", "Reach error (cm)", "Latency (ms)"],
  ["A1", "A2", "A3"].flatMap((t) => ["oracle", "hsv", "hybrid"].map((p) => { const r = AR(t, p); return r.n ? [t, p, `${r.success} %`, `${r.picked_wrong}`, `${r.missed}`, `${r.not_found}`, v(r.reach_err_med, 1), v(r.lat_med, 0)] : null; }).filter(Boolean)),
  [8, 13, 11, 15, 10, 15, 15, 13], { center: true });
add(P(`The arm uses the same perception classes with a fixed camera and an inverse-kinematics adapter (${fAS.label}). With the oracle every pick succeeded (${v(AR("A2", "oracle").success)} % in A2), showing that the adapter and grasp sequence are sound. Colour perception succeeded when the orange was alone (A1: ${v(AR("A1", "hsv").success)} %) but not with orange distractors or dim light (A2: ${v(AR("A2", "hsv").success)} %, A3: ${v(AR("A3", "hsv").success)} %). The hybrid succeeded in ${v(AR("A2", "hybrid").success)} % (A2) and ${v(AR("A3", "hybrid").success)} % (A3) of runs, but only ${v(AR("A1", "hybrid").success)} % in A1, where most failures were "target not found" — the detector-plus-verifier rejected or missed a large, close, top-down view of a single orange that differs from the oblique views it was calibrated on (${fAC.label}, ${tA.label}). This is a useful negative result: verifier calibration is viewpoint-specific and must be repeated for each embodiment's camera geometry.`));
add(fAS, fAC, tA);

// ---------------- Experiment 7: memory
add(H3("3.7.14 Experiment 7 — Persistent Memory in Multi-Step Missions"));
const fMD = fig("shot_result_memory_drone.png", 6.3, "Drone, mission M2 (find three objects, twice): without memory (left) and with persistent memory (right); crosses are remembered objects, * marks subtasks served from memory");
const fMG = fig("shot_result_memory_ground.png", 6.3, "The same comparison on the ground robot");
const fMC = fig("res_memory.png", 6.4, "Mean mission time (± s.d.) and distance travelled by memory mode, task and robot (10 seeds each)");
const fMS = fig("res_memory_subtasks.png", 6.4, "Mean duration of each subtask in M2: with persistent memory, the second mission's subtasks are served from memory");
const mem = (t, e, m) => ME(t, e, m);
const red = (t, e) => { const a = mem(t, e, "none").time_mean, b = mem(t, e, "persistent").time_mean; return a && b ? (100 * (a - b)) / a : null; };
const tM = table("Memory results (10 seeds per cell; perception = oracle to isolate the effect of memory)", ["Task", "Robot", "Memory", "Subtasks done", "Mission time (s)", "Path (m)", "From memory", "Object recall", "Collisions"],
  ["M1", "M2"].flatMap((t) => ["drone", "ground"].flatMap((e) => ["none", "per-mission", "persistent"].map((m) => { const r = mem(t, e, m); return r.n ? [t, e, m, `${r.sub_ok} %`, `${v(r.time_mean, 1)} ± ${v(r.time_sd, 1)}`, v(r.path_mean, 1), `${r.from_memory} %`, `${r.recall} %`, `${r.collisions}`] : null; }).filter(Boolean))),
  [7, 9, 13, 11, 17, 9, 12, 12, 10], { center: true });
add(P(`Both robots completed every subtask in every memory mode, so memory did not change *whether* missions succeed but *how efficiently* (${fMC.label}, ${tM.label}). With persistent memory, total mission time fell by ${v(red("M1", "drone"))} % (drone) and ${v(red("M1", "ground"))} % (ground) on single missions (M1) and by **${v(red("M2", "drone"))} % (drone) and ${v(red("M2", "ground"))} % (ground) on repeated missions (M2)**; ${v(mem("M2", "drone", "persistent").from_memory)} % of M2 subtasks were served directly from memory and object recall reached ${v(mem("M2", "drone", "persistent").recall)} %. Per-mission memory gives an intermediate result, showing that the benefit grows with how long knowledge is kept. ${fMS.label} shows where the time is saved: with persistent memory the second mission's subtasks take only the travel time to the remembered object. Hypothesis H6 (≥ 20 % reduction on repeated missions) is therefore supported for both robots, while the single-mission gain is smaller because each object must still be found once.`));
add(fMD, fMG, fMC, fMS, tM);

// ---------------- Hypotheses & research questions
add(H3("3.7.15 Hypotheses and Research Questions — Outcomes"));
add(table("Outcome of the pre-registered hypotheses", ["ID", "Hypothesis (short)", "Outcome"], [
  ["H1", "Better renderer → better detection", "Supported for YOLO-World (MuJoCo > PyBullet)"],
  ["H2", "Richer dynamics slow missions, same success", "Partly supported (MuJoCo slower, same success; PX4 not yet run)"],
  ["H3", "Simulators agree on simple scenes, differ with distractors", "Supported"],
  ["H4", "Link loss only realistic with real firmware", "Confirmed by construction (identical 0.5 s / 6.15 s)"],
  ["H5", "No simulator closest on every axis", "Not yet testable (needs Phase-4 real data)"],
  ["H6", "Persistent memory cuts repeated-mission time ≥ 20 %", `Supported (M2: −${v(red("M2", "drone"))} % drone, −${v(red("M2", "ground"))} % ground)`],
  ["H7", "Same layer works on the ground robot", `Supported for planning, memory and safety (oracle ${v(xeAll("ground", "oracle"))} % on both robots); perception only partly (hybrid ${v(xeAll("ground", "hybrid"))} % ground vs ${v(xeAll("drone", "hybrid"))} % drone)`],
  ["H8", "VLM verification reduces decoy landings", `Supported (decoy landings: ring ${rg.dec}, verifier v3 ${v3.dec}); dim light unsolved`],
  ["H9", "Arm perception ranking matches the drone", "Partly supported (hybrid > colour with distractors and dim light; hybrid weak on single close views)"],
], [7, 45, 48]));
add(table("Answers to the research questions (Phases 0–2)", ["RQ", "Answer from this report"], [
  ["RQ1 Perception", `Detector proposals + small-VLM verification (C5): ${v(OV.C5.nav_succ)} % navigation success at ~${v(OV.C5.lat_med)} ms; a VLM used as the pilot failed (C4: ${v(OV.C4.nav_succ)} %)`],
  ["RQ2 Memory", `Yes: −${v(red("M2", "drone"))} % / −${v(red("M2", "ground"))} % mission time on repeated missions, fewer re-explorations, ${v(mem("M2", "drone", "persistent").recall)} % object recall`],
  ["RQ3 Cross-embodiment", "Yes for planning, memory and safety (100 % with perfect perception on drone and ground robot; arm 100 %); the perception front-end needs per-robot calibration"],
  ["RQ4 Data needed", "Zero robot-specific data for hand-written adapters; learned-adapter data requirements remain open (Phase 5)"],
  ["RQ5 Unseen environments", "All results are on randomised unseen layouts; real unseen buildings remain to be tested"],
  ["RQ6 Closest simulator", "MuJoCo closer on dynamics and rendering; measurement against real data pending"],
], [22, 78]));

// ---------------- Problems, limitations, conclusion
add(H3("3.7.16 Problems Encountered"));
add(P(`The main problems and how they were resolved are listed in the design-iteration table of Section 3.1.3. Additional problems: two parallel GPU batches crashed with out-of-memory errors (resolved with fewer processes and resumable runs); a library update renamed the OWLv2 post-processing function; the DJI Neo 2 has no developer SDK support we could find, so it is used in shadow mode only; and two contact events in about 1,400 Phase-1 episodes could not be reproduced on replay because live-measured latency makes runs slightly non-deterministic.`));
add(H3("3.7.17 Limitations"));
add(B([
  "All quantitative results are from simulation with simplified rendering; perception on real images is untested (Phase 4).",
  "The room connectivity of the house was given (object locations were not); online discovery of rooms is Phase 3.",
  "Memory experiments used oracle perception to isolate the effect of memory; memory with imperfect perception (false entries) still needs study.",
  "Adapters were hand-written; the arm grasp uses a simplified attachment rather than friction grasping.",
  "Ten seeds per cell (five for C4) give wide confidence intervals for individual cells.",
  "The verifier cannot separate an orange from a plain orange ball and is sensitive to viewpoint (A1 result).",
  "No VLA was fine-tuned; the 'VLA-style' result (C4) used a zero-shot VLM.",
]));
add(H3("3.7.18 Conclusion"));
add(P(`Phases 0–2 turned a broad research problem — language-guided action on affordable robots with memory and cross-embodiment transfer — into a modular architecture and seven controlled experiments in simulation. A shared, laptop-hosted intelligence layer (zero-shot detector proposals verified by a small VLM, a persistent semantic memory, a classical planner and an independent safety filter) found objects with ${v(OV.C5.nav_succ)} % success on the drone, landed on the nearest correct helipad among decoys in ${v(v3.strict3)} % of normal-light runs after three design iterations (dim light remains unsolved), ran unchanged on a ground robot and an arm through thin adapters (100 % success with perfect perception, while the perception front-end needed per-robot calibration), and reduced repeated-mission time by about a third with persistent memory. The experiments also showed clearly what does not work — a small VLM used directly as the pilot, colour-only perception with look-alike objects, and verification from oblique or unfamiliar viewpoints — which defines the next phases: a richer scene-graph memory with an LLM task planner, real hardware, and learned adapters whose data requirements can now be measured against these baselines.`));
