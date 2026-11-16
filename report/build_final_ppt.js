// Final presentation (college format): white background, black text, Times New Roman.
// Content follows the report (Project_Report_v2); numbers come from numbers*.json.
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const DIR = __dirname;
const FIG = (f) => path.join(DIR, "figs", f);
const AS = (f) => path.join(DIR, "deck_assets", f);
const J = (f) => JSON.parse(fs.readFileSync(path.join(DIR, f), "utf8").replace(/\bNaN\b/g, "null"));
const N1 = J("numbers.json"), NW = J("numbers_world.json");
const OV = Object.fromEntries(N1.overall.map((r) => [r.config, r]));
const HP = (t, p) => NW.helipad.find((r) => r.task === t && r.perception === p) || {};
const XE = (t, e, p) => NW.xemb.find((r) => r.task === t && r.embodiment === e && r.perception === p) || {};
const AR = (t, p) => NW.arm.find((r) => r.task === t && r.perception === p) || {};
const ME = (t, e, m) => NW.memory.find((r) => r.task === t && r.embodiment === e && r.memory === m) || {};
const V3 = "VLM verifier v3 (top-down, rot.-inv.)", V1 = "VLM verifier v1 (oblique)", RING = "Ring detector (colour)", OR = "Oracle";
const strict3 = (p) => ["L1", "L2", "L3"].reduce((a, t) => a + HP(t, p).strict, 0) / 3;
const xeAll = (e, p) => ["O1", "O2", "O3"].reduce((a, t) => a + XE(t, e, p).success, 0) / 3;
const red = (e) => (100 * (ME("M2", e, "none").time_mean - ME("M2", e, "persistent").time_mean)) / ME("M2", e, "none").time_mean;
const r0 = (x) => Math.round(x);

const FONT = "Times New Roman";
const BLACK = "000000", GREY = "404040", LIGHT = "F2F2F2", RULE = "BFBFBF";
const W = 13.333, H = 7.5, M = 0.5;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.author = "Project team";
pres.title = "Language-Guided Robots on Affordable Hardware";
pres.theme = { headFontFace: FONT, bodyFontFace: FONT };
for (const t of ["Introduction", "Literature", "Methodology", "Design", "Results", "Discussion"]) pres.addSection({ title: t });

pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: "FFFFFF" },
  objects: [
    { text: { text: "Design Project Minor (CPT 401) · uGDX School of Technology", options: { x: M, y: 7.02, w: 8, h: 0.3, fontFace: FONT, fontSize: 10, color: GREY } } },
  ],
  slideNumber: { x: W - 1.2, y: 7.02, w: 0.7, h: 0.3, fontFace: FONT, fontSize: 10, color: GREY, align: "right" },
  margin: [0.5, 0.5, 0.6, 0.5],
});
pres.defineSlideMaster({ title: "PLAIN", background: { color: "FFFFFF" }, objects: [] });

function pngSize(p) {
  const b = fs.readFileSync(p);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}
function img(s, p, x, y, w, h, align = "center") {
  const { w: iw, h: ih } = pngSize(p);
  const sc = Math.min(w / iw, h / ih);
  const dw = iw * sc, dh = ih * sc;
  const ox = align === "left" ? x : x + (w - dw) / 2;
  s.addImage({ path: p, x: ox, y: y + (h - dh) / 2, w: dw, h: dh });
  return { x: ox, y: y + (h - dh) / 2, w: dw, h: dh };
}
function slide(title, section) {
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: section });
  s.addText(title, { x: M, y: 0.3, w: W - 2 * M, h: 0.75, fontFace: FONT, fontSize: 28, bold: true, color: BLACK, isTextBox: true, margin: 0 });
  return s;
}
function bullets(s, items, x, y, w, h, size = 18) {
  const arr = items.map((t, i) => {
    const sub = t.startsWith("- ");
    return { text: sub ? t.slice(2) : t, options: { bullet: sub ? { indent: 18 } : true, indentLevel: sub ? 1 : 0, breakLine: i < items.length - 1, fontSize: sub ? size - 2 : size, paraSpaceAfter: 6 } };
  });
  s.addText(arr, { x, y, w, h, fontFace: FONT, color: BLACK, valign: "top", isTextBox: true, margin: 0.05 });
}
function caption(s, t, x, y, w) {
  s.addText(t, { x, y, w, h: 0.35, fontFace: FONT, fontSize: 12, italic: true, color: GREY, align: "center", isTextBox: true, margin: 0 });
}
function table(s, rows, x, y, w, colW, size = 14) {
  const data = rows.map((r, i) => r.map((c) => ({ text: String(c), options: { bold: i === 0, fill: { color: i === 0 ? LIGHT : "FFFFFF" } } })));
  s.addTable(data, { x, y, w, colW, fontFace: FONT, fontSize: size + 3, color: BLACK, border: { type: "solid", pt: 0.75, color: RULE }, valign: "middle", margin: 0.06 });
}
function box(s, t, x, y, w, h, size = 18) {
  s.addText(t, { x, y, w, h, fontFace: FONT, fontSize: size, color: BLACK, line: { color: BLACK, width: 1.25 }, margin: 0.15, valign: "middle", isTextBox: true });
}

// ---------------------------------------------------------------- 1 Title
{
  const s = pres.addSlide({ masterName: "PLAIN", sectionTitle: "Introduction" });
  s.addText("uGDX School of Technology", { x: M, y: 0.45, w: W - 2 * M, h: 0.5, fontFace: FONT, fontSize: 22, bold: true, align: "center", color: BLACK });
  s.addText("Design Project Minor (CPT 401) · Final Year B. Tech (Semester VII)", { x: M, y: 0.95, w: W - 2 * M, h: 0.4, fontFace: FONT, fontSize: 16, align: "center", color: GREY });
  s.addText("Language-Guided Robots on Affordable Hardware", { x: 0.8, y: 1.9, w: W - 1.6, h: 0.8, fontFace: FONT, fontSize: 36, bold: true, align: "center", color: BLACK });
  s.addText("Persistent Memory and Cross-Embodiment Transfer — Phase 1–2 Design and Simulation Study", { x: 0.8, y: 2.7, w: W - 1.6, h: 0.6, fontFace: FONT, fontSize: 22, align: "center", color: BLACK });
  s.addText([
    { text: "Presented by", options: { bold: true, breakLine: true } },
    { text: "Amitav  ·  Kshitij  ·  Prarthana", options: { breakLine: true } },
    { text: " ", options: { breakLine: true } },
    { text: "Supervisor", options: { bold: true, breakLine: true } },
    { text: "[Name of the Guide], [Affiliation]", options: { breakLine: true } },
  ], { x: 3.2, y: 3.75, w: W - 6.4, h: 2.2, fontFace: FONT, fontSize: 18, align: "center", color: BLACK });
  s.addText("Academic Year 2026–2027", { x: M, y: 6.4, w: W - 2 * M, h: 0.4, fontFace: FONT, fontSize: 16, align: "center", color: GREY });
}

// ---------------------------------------------------------------- 2 Outline
{
  const s = slide("Outline", "Introduction");
  bullets(s, ["Problem definition and research questions", "Aims, objectives and scope", "Review of literature and research gap", "Research process: phases, options considered, design iterations",
    "System architecture and simulation environment", "Experiments and results (7 experiments, ~1,900 simulated episodes)", "Hypotheses, limitations and conclusion", "Future work (Phases 3–5) and references"], M, 1.3, 7.2, 5.4, 22);
  img(s, FIG("fig_phases.png"), 7.9, 1.6, 4.9, 4.2);
  caption(s, "Project phases: this work covers Phases 0–2", 7.9, 5.9, 4.9);
}

// ---------------------------------------------------------------- 3 Problem
{
  const s = slide("1. Problem Definition", "Introduction");
  s.addText("Overall problem", { x: M, y: 1.2, w: 6, h: 0.4, fontFace: FONT, fontSize: 18, bold: true, color: BLACK });
  box(s, "How can a pretrained vision-language(-action) agent turn a natural-language instruction into safe and successful action on affordable, off-the-shelf robots — drones, ground vehicles and robot arms — without expensive onboard computing, a prebuilt map or extensive robot-specific training, while remembering what it has observed so that it can complete multi-step missions in environments it has never seen?", M, 1.65, W - 2 * M, 1.75, 18);
  s.addText("Problem addressed in this report (Phases 0–2)", { x: M, y: 3.6, w: 8, h: 0.4, fontFace: FONT, fontSize: 18, bold: true, color: BLACK });
  box(s, "In previously unseen simulated indoor environments, can a laptop-hosted modular pipeline built only from pretrained models (zero robot-specific training) (a) locate and approach a named object to a 0.5 m stand-off, (b) find and land on the nearest correct helipad among decoys and (c) complete multi-object missions — while safety never depends on the AI — and how far do (d) persistent memory and (e) thin embodiment adapters let one intelligence layer serve a drone, a ground robot and a robot arm?", M, 4.05, W - 2 * M, 2.0, 18);
}

// ---------------------------------------------------------------- 4 Gaps
{
  const s = slide("Why the Problem Is Hard: Five Gaps", "Introduction");
  table(s, [["Gap", "Why it matters", "Addressed here"],
    ["G1  No persistent spatial-semantic memory", "Objects seen earlier are forgotten; areas are re-explored", "Object + room memory (Experiment 7)"],
    ["G2  Limited long-horizon missions", "Reaching one goal ≠ completing a multi-stage mission", "Sequential subtasks; LLM planner in Phase 3"],
    ["G3  Generalisation to unseen environments", "Layouts, objects and lighting differ from training", "Randomised unseen layouts in every experiment"],
    ["G4  Embodiment dependency", "A policy for one robot cannot command another", "Drone, ground robot and arm share one layer"],
    ["G5  Robot-specific training data", "Training a VLA per robot is expensive", "Zero robot-specific data used; learned adapters in Phase 5"]],
  M, 1.3, W - 2 * M, [3.6, 4.6, 4.13], 16);
}

// ---------------------------------------------------------------- 5 RQs + objectives
{
  const s = slide("Research Questions and Objectives", "Introduction");
  table(s, [["RQ", "Question"],
    ["RQ1", "Which perception design lets a drone find the right object reliably on a laptop?"],
    ["RQ2", "Does persistent memory reduce mission time and repeated exploration?"],
    ["RQ3", "Can one high-level layer serve a drone, a ground robot and an arm via thin adapters?"],
    ["RQ4", "How much robot-specific data does embodiment adaptation need?"],
    ["RQ5", "Does the approach generalise to unseen layouts, lighting and distractors?"],
    ["RQ6", "Which simulator is closest to the physical world, and on which axis?"]], M, 1.3, 7.3, [0.8, 6.5], 14);
  s.addText("Objectives", { x: 8.1, y: 1.3, w: 4.7, h: 0.4, fontFace: FONT, fontSize: 18, bold: true, color: BLACK });
  bullets(s, ["Parse commands into missions; ask when ambiguous", "Detect and localise objects / pads zero-shot", "Search rooms and buildings", "Approach to 0.5 m or land within 0.2 m", "Keep safety independent of the AI", "Persistent semantic memory", "Same layer on three robots", "Controlled comparisons, two simulators"], 8.1, 1.75, 4.7, 5.0, 16);
}

// ---------------------------------------------------------------- 6 Scope
{
  const s = slide("Scope of the Project", "Introduction");
  table(s, [["In scope (Phases 0–2, simulation)", "Out of scope (Phases 3–5)"],
    ["Drone, wheeled ground robot (Husky), robot arm (Franka Panda)", "Building and flying real robots"],
    ["Object search & approach; nearest-helipad landing; multi-object missions; pick-up", "Mobile manipulation, moving targets, outdoor flight"],
    ["Object + explored-room memory; room connectivity given", "Full 3-D scene graph, LLM task planner, replanning"],
    ["Zero-shot models (YOLO-World, OWLv2, SmolVLM); hand-written adapters", "Fine-tuning a VLA; learned adapters; data-efficiency study"],
    ["PyBullet and MuJoCo on a Windows laptop with an 8 GB GPU", "PX4 software-in-the-loop; photorealistic simulators"],
    ["DJI Neo 2 shadow-mode software; custom-drone design and parts list", "Closed-loop control of the Neo 2 (no SDK support found)"]],
  M, 1.3, W - 2 * M, [6.6, 5.73], 16);
}

// ---------------------------------------------------------------- 7 Literature
{
  const s = slide("2. Review of Literature", "Literature");
  table(s, [["Area", "Key works", "Takeaway for this project"],
    ["Vision-language-action models", "OpenVLA, π0, SmolVLA, X-VLA", "Action heads are tied to robot arms; flight needs a new action space"],
    ["Drone / navigation VLAs", "CognitiveDrone, UAV-VLA, NaVILA", "Retraining on 8k+ flights; separate 'what' from 'how'"],
    ["Open-vocabulary perception", "CLIP, OWLv2, Grounding DINO, YOLO-World, SmolVLM", "Targets become text queries; precision on look-alikes uncertain"],
    ["Memory & long-horizon planning", "ReMEmbR, HOV-SG, 3D-Mem, SayPlan", "Established direction; we measure a simple memory vs none"],
    ["Cross-embodiment", "CrossFormer, HPT, NavFoM", "Works, but needs very large datasets; we test the zero-data end"],
    ["Planning, control, simulation", "VFH, SE(3) control, PX4, Gazebo, PyBullet, MuJoCo", "Classical planner + independent fail-safes; Windows-native simulators"]],
  M, 1.3, W - 2 * M, [3.0, 4.2, 5.13], 15);
}

// ---------------------------------------------------------------- 8 Gap / novelty
{
  const s = slide("Research Gap and Contribution", "Literature");
  table(s, [["Component", "Status in literature", "This project"],
    ["LLM/VLM for robot instructions", "Established", "Used as components"],
    ["Detector + VLM verification", "Established parts", "Measured on 3 robots; active top-down verification"],
    ["Persistent semantic memory", "Active research", "Simple memory vs no-memory baselines"],
    ["Cross-embodiment transfer", "Active, data-hungry", "Zero-data hand-written adapters as a baseline"],
    ["Safety independent of AI", "Standard practice", "Held constant across all configurations"],
    ["Affordable combination with controlled comparisons", "Less studied", "Main contribution"]], M, 1.3, 8.2, [3.2, 2.2, 2.8], 15);
  bullets(s, ["The ideas exist individually", "Our contribution: an affordable, modular reference architecture and controlled experiments that quantify each component on three robots under identical conditions"], 9.0, 1.4, 3.8, 5, 19);
}

// ---------------------------------------------------------------- 9 Process: funnel
{
  const s = slide("3. Research Process: From Options to a Testable Core", "Methodology");
  img(s, FIG("fig_funnel.png"), M, 1.2, 7.4, 5.6);
  table(s, [["Decision", "Chosen (reason)"],
    ["Control", "Modular, not end-to-end VLA (VLM as pilot: 0 %)"],
    ["Perception", "Detector + VLM verifier (best accuracy/latency)"],
    ["Large models", "Small local models (7 B needs ~15 GB VRAM)"],
    ["Simulator", "PyBullet + MuJoCo (Windows, 8 GB GPU, all 3 robots)"],
    ["Ranging", "24 beams (our ablation: near-misses 7/40 → 0/40)"]], 8.15, 1.3, 4.7, [1.5, 3.2], 13);
}

// ---------------------------------------------------------------- 10 Design iterations
{
  const s = slide("Design Iterations (Each Triggered by a Measured Failure)", "Methodology");
  table(s, [["Version tried", "Observed", "Change"],
    ["Planner treats all depth points as obstacles", "Hovered 0.8 m from target", "Exclude tracked target; safety filter unchanged"],
    ["Fixed altitude, camera −15°", "Target left view at 0.5 m", "Final-approach descent"],
    ["YOLO-World prompt 'orange'", "Score 0.05 on rendered orange", "Low-threshold proposals + VLM verification"],
    ["8-beam range ring", "Near-misses down to 1.7 cm", "24-beam ring adopted for Phase 2"],
    ["Pad verifier v1 (oblique view)", `Nearest-helipad landing ${r0(strict3(V1))} %`, "v2: verify from directly above"],
    ["Pad verifier v2", "Rotated 'H' read as 'I'", "v3: whole-pad + rotation-invariant query"],
    ["Pad verifier v3", `Nearest-helipad landing ${r0(strict3(V3))} %; 0 % in dim light`, "Kept; dim light traced to colour proposals"]],
  M, 1.3, W - 2 * M, [4.4, 3.9, 4.03], 15);
}

// ---------------------------------------------------------------- 11 Architecture
{
  const s = slide("System Architecture", "Design");
  img(s, FIG("fig_layered.png"), M, 1.2, 8.4, 5.6);
  bullets(s, ["One shared, laptop-hosted intelligence layer", "Independent safety filter — raw range data only, never trusts the AI", "Robot-specific code = thin adapter only",
    "- Drone: velocity loop + fail-safe", "- Ground robot: unicycle (≈10 lines)", "- Arm: inverse kinematics", "Fail-safe on the robot: no setpoint 0.5 s → hover, 3 s → land"], 9.15, 1.4, 3.7, 5.4, 16);
}

// ---------------------------------------------------------------- 12 Block + flowchart
{
  const s = slide("Phase-1 Design: Block Diagram and Mission Logic", "Design");
  img(s, FIG("fig_block_diagram.png"), M, 1.2, 6.4, 5.3);
  caption(s, "Block diagram (laptop chain and drone)", M, 6.55, 6.4);
  img(s, FIG("fig_flowchart.png"), 7.1, 1.2, 5.7, 5.3);
  caption(s, "Mission state machine", 7.1, 6.55, 5.7);
}

// ---------------------------------------------------------------- 13 Simulation choice
{
  const s = slide("Simulation Environment and Compatibility", "Design");
  table(s, [["Simulator", "Windows / 8 GB GPU", "Drone", "Ground", "Arm", "Real firmware", "Used"],
    ["PyBullet", "Yes / Yes", "Yes", "Yes (Husky)", "Yes (Panda)", "No", "Primary"],
    ["MuJoCo", "Yes / Yes", "Yes (6-DOF)", "Possible", "Yes", "No", "Cross-check"],
    ["Gazebo + PX4 SITL", "WSL2 / Yes", "Yes", "Yes", "Yes", "Yes", "Phase 4"],
    ["Webots", "Yes / Yes", "Yes", "Yes", "Yes", "Partial", "No (time)"],
    ["Isaac Sim", "Yes / minimum", "Add-on", "Yes", "Yes", "Via PX4", "Future"],
    ["Habitat", "Linux only", "No", "Yes", "Limited", "No", "Future"],
    ["AirSim / Colosseum", "Yes / heavy", "Yes", "Car", "No", "Via PX4", "No"]],
  M, 1.3, W - 2 * M, [2.4, 2.0, 1.5, 1.6, 1.6, 1.6, 1.63], 15);
}

// ---------------------------------------------------------------- 14 Robots in world
{
  const s = slide("Robots and Environments in the Simulator", "Design");
  img(s, FIG("shot_robots_world.png"), M, 1.15, 7.0, 5.8);
  bullets(s, ["Drone: 3.5-inch ducted quadrotor, gimbal camera, 24-beam ToF ring", "Ground robot: Husky with 0.6 m camera mast", "Arm: Franka Panda with fixed RGB-D camera",
    "Worlds: test room, four-room house (kitchen, office, workshop, storage), helipad field with decoy pads", "Every layout randomised from a seed → unseen environments"], 7.75, 1.3, 5.1, 5.5, 17);
}

// ---------------------------------------------------------------- 15 Sensors
{
  const s = slide("Sensor Data", "Design");
  img(s, FIG("shot_sensors_drone.png"), M, 1.2, W - 2 * M, 2.5);
  caption(s, "Drone: RGB + detections · metric depth · segmentation (evaluation only) · range beams + depth sectors", M, 3.75, W - 2 * M);
  img(s, FIG("shot_sensors_ground.png"), M, 4.15, W - 2 * M, 2.5);
  caption(s, "Ground robot: the same sensor set on a mast camera", M, 6.65, W - 2 * M);
}

// ---------------------------------------------------------------- 16 Experiments
{
  const s = slide("Experiments and Metrics", "Results");
  table(s, [["#", "Experiment", "Design"],
    ["1", "Perception on the drone", "7 configurations × 10 scenarios"],
    ["2", "Simulator cross-check", "PyBullet vs MuJoCo, matched layouts"],
    ["3", "Safety and sensor design", "8 vs 24 range beams; manual crash test; link loss"],
    ["4", "Find the nearest helipad and land", "4 scenarios × 4 detectors"],
    ["5", "Drone vs ground robot", "Same layer; 3 tasks × 3 perceptions"],
    ["6", "Robot arm pick-up", "3 tasks × 3 perceptions"],
    ["7", "Persistent memory", "House missions; none / per-mission / persistent"]], M, 1.3, 7.6, [0.5, 3.3, 3.8], 15);
  bullets(s, ["Success: correct target within ±0.15–0.2 m of stand-off, or landed on the correct pad within 0.2 m", "Wrong-target / decoy landings", "Collisions, minimum clearance", "Mission time, path length, object recall", "Latency per frame", "10 seeds per cell; 95 % Wilson intervals; hypotheses written before testing"], 8.4, 1.3, 4.4, 5.5, 15);
}

// ---------------------------------------------------------------- 17 Result 1
{
  const s = slide("Result 1: Perception on the Drone", "Results");
  img(s, FIG("res_heatmap.png"), M, 1.2, 7.9, 4.0);
  caption(s, "Success (%) per configuration and scenario (PyBullet, seeds 0–9)", M, 5.25, 7.9);
  bullets(s, [`Hybrid detector + VLM verifier (C5): ${r0(OV.C5.nav_succ)} % success, ~${r0(OV.C5.lat_med)} ms per frame`, `Small VLM used directly as the pilot (C4): ${r0(OV.C4.nav_succ)} %`,
    `Removing verification (C6): wrong-target ${r0(OV.C5.wrong)} % → ${r0(OV.C6.wrong)} %`, "Perfect perception (C0): 100 % with zero collisions → all failures are perception", "Remaining hybrid errors occur only with a plain orange ball (look-alike)"], 8.7, 1.3, 4.1, 5.5, 16);
}

// ---------------------------------------------------------------- 18 Orange sequence
{
  const s = slide("Result: Finding the Orange (Drone and Ground Robot)", "Results");
  img(s, AS("orange_strip.png"), M, 1.2, W - 2 * M, 2.55);
  caption(s, "Drone: labelled detections → approach → trajectory → final hold at 0.46 m", M, 3.8, W - 2 * M);
  img(s, AS("orange_ground_strip.png"), M, 4.25, W - 2 * M, 2.4);
  caption(s, "Ground robot: identical intelligence layer with a unicycle adapter", M, 6.65, W - 2 * M);
}

// ---------------------------------------------------------------- 19 Helipad
{
  const s = slide("Result 4: Find the Nearest Helipad and Land", "Results");
  img(s, AS("landing_strip.png"), M, 1.15, W - 2 * M, 2.4);
  img(s, FIG("res_helipad.png"), M, 3.7, 6.8, 3.2);
  bullets(s, [`Verifier v3 (check from directly above): ${r0(strict3(V3))} % nearest-helipad landings, 0 decoy landings`, `Verifier v1 (oblique view): ${r0(strict3(V1))} %`,
    `Colour-only detector: ${r0(strict3(RING))} %; landed on a decoy in ${HP("L3", RING).decoy_landings}/10 decoy runs`, "Dim light: 0 % for every real detector (oracle 100 %) → colour proposal stage is the weak link"], 7.5, 3.75, 5.3, 3.1, 15);
}

// ---------------------------------------------------------------- 20 Drone vs ground
{
  const s = slide("Result 5: Same Intelligence Layer, Two Robots", "Results");
  img(s, FIG("res_xemb.png"), M, 1.25, 8.0, 3.9);
  caption(s, "Success: drone (solid) vs ground robot (hatched), by perception", M, 5.2, 8.0);
  bullets(s, ["Perfect perception: 100 % on both robots → planning, memory and safety transfer unchanged", `Hybrid perception: ${r0(xeAll("drone", "hybrid"))} % (drone) → ${r0(xeAll("ground", "hybrid"))} % (ground robot)`,
    `With look-alikes on the drone: hybrid ${XE("O3", "drone", "hybrid").success} % vs colour ${XE("O3", "drone", "hsv").success} %`, "Without look-alikes colour is best and fastest", "Lesson: perception must be re-calibrated for each robot's camera"], 8.8, 1.3, 4.0, 5.5, 15);
}

// ---------------------------------------------------------------- 21 Arm
{
  const s = slide("Result 6: Robot Arm Pick-Up", "Results");
  img(s, AS("arm_strip.png"), M, 1.15, W - 2 * M, 2.15);
  img(s, FIG("res_arm.png"), M, 3.5, 6.2, 3.35);
  bullets(s, [`Perfect perception: ${AR("A2", "oracle").success} % (inverse-kinematics adapter and grasp are sound)`, `With look-alikes (A2): hybrid ${AR("A2", "hybrid").success} %, colour ${AR("A2", "hsv").success} %`,
    `Dim light (A3): hybrid ${AR("A3", "hybrid").success} %, colour ${AR("A3", "hsv").success} %`, `Single close orange (A1): hybrid only ${AR("A1", "hybrid").success} % → verifier is viewpoint-specific`], 7.0, 3.6, 5.8, 3.2, 15);
}

// ---------------------------------------------------------------- 22 Memory
{
  const s = slide("Result 7: Persistent Memory in Multi-Step Missions", "Results");
  img(s, FIG("shot_result_memory_drone.png"), M, 1.15, 6.6, 3.3);
  caption(s, "Drone, mission M2: without memory (left) vs persistent memory (right)", M, 4.45, 6.6);
  img(s, FIG("res_memory.png"), M, 4.85, 6.6, 2.05);
  bullets(s, [`Repeated missions: mission time −${r0(red("drone"))} % (drone), −${r0(red("ground"))} % (ground robot)`, `${ME("M2", "drone", "persistent").from_memory} % of subtasks served directly from memory`,
    `Object recall ${ME("M2", "drone", "persistent").recall} %`, "All subtasks succeeded in every memory mode — memory changes how fast, not whether", "Per-mission memory is in between → the benefit grows with how long knowledge is kept"], 7.4, 1.3, 5.4, 5.5, 16);
}

// ---------------------------------------------------------------- 23 Safety
{
  const s = slide("Result 3: Safety Layer and Sensor Design", "Results");
  img(s, FIG("shot_fly_on.png"), M, 1.15, 6.1, 2.65);
  caption(s, "Filter ON: manual push into pillars, 0 collisions", M, 3.8, 6.1);
  img(s, FIG("shot_fly_off.png"), 6.75, 1.15, 6.1, 2.65);
  caption(s, "Filter OFF: same input, 2 collisions", 6.75, 3.8, 6.1);
  const a = N1.sensor["pybullet|T4"], b = N1.sensor["pybullet|T4D"];
  bullets(s, [`Minimum clearance ${(a.min * 100).toFixed(1)} cm → ${(b.min * 100).toFixed(1)} cm with 24 instead of 8 range beams (near-misses 7/40 → 0/40)`, "Link loss: hover after 0.5 s, landed safely after 6.15 s (both simulators)",
    "Perfect perception: zero collisions in every scenario", "Simulators: same results on simple scenes; differ with look-alikes (rendering matters)"], M, 4.25, W - 2 * M, 2.6, 16);
}

// ---------------------------------------------------------------- 24 Hypotheses
{
  const s = slide("Hypotheses and Outcomes", "Results");
  table(s, [["ID", "Hypothesis (written before testing)", "Outcome"],
    ["H1", "Better renderer → better detection", "Supported (YOLO-World better in MuJoCo)"],
    ["H3", "Simulators agree on simple scenes, differ with distractors", "Supported"],
    ["H4", "Link-loss behaviour realistic only with real firmware", "Confirmed by construction"],
    ["H5", "No simulator closest to reality on every axis", "Needs Phase-4 real data"],
    ["H6", "Persistent memory cuts repeated-mission time ≥ 20 %", `Supported (−${r0(red("drone"))} % / −${r0(red("ground"))} %)`],
    ["H7", "Same layer works on a ground robot", "Planning yes (100 %); perception partly"],
    ["H8", "VLM verification reduces decoy landings", `Supported (${HP("L3", RING).decoy_landings} → 0); dim light unsolved`],
    ["H9", "Arm perception ranking matches the drone", "Partly"]], M, 1.3, W - 2 * M, [0.8, 6.6, 4.93], 15);
}

// ---------------------------------------------------------------- 25 Limitations
{
  const s = slide("Limitations", "Discussion");
  bullets(s, ["All quantitative results are from simulation with simplified rendering", "Room connectivity of the house was given (object locations were not)", "Memory experiments used perfect perception to isolate the effect of memory",
    "Adapters are hand-written; the arm grasp uses a simplified attachment", "10 seeds per cell (5 for the VLM pilot) → wide confidence intervals", "The verifier cannot separate an orange from a plain orange ball and is viewpoint-sensitive",
    "No VLA was fine-tuned; the VLM-pilot result is zero-shot"], M, 1.3, W - 2 * M, 5.5, 24);
}

// ---------------------------------------------------------------- 26 Conclusion
{
  const s = slide("Conclusion", "Discussion");
  bullets(s, [`One laptop-hosted intelligence layer found objects with ${r0(OV.C5.nav_succ)} % success on the drone`, `Landed on the nearest correct helipad in ${r0(strict3(V3))} % of normal-light runs after three design iterations`,
    "Ran unchanged on a drone, a ground robot and an arm (100 % with perfect perception); perception needs per-robot calibration", `Persistent memory cut repeated-mission time by about a third (−${r0(red("drone"))} % / −${r0(red("ground"))} %)`,
    "A small VLM must not fly the robot directly — use it to verify", "Safety stayed independent of the AI throughout"], M, 1.3, W - 2 * M, 5.5, 24);
}

// ---------------------------------------------------------------- 27 Future work
{
  const s = slide("4. Future Work", "Discussion");
  img(s, FIG("fig_phases.png"), M, 1.15, W - 2 * M, 2.6);
  bullets(s, ["Phase 3: scene-graph memory (rooms, objects, relations), small local LLM task planner, replanning when the world changes",
    "Phase 4: DJI Neo 2 shadow mode (software ready), custom drone, small ground robot, PX4 software-in-the-loop",
    "Phase 5: learned adapters (SmolVLA-style) and a data-efficiency study with 10–300 demonstrations",
    "Perception: fix dim light (learned pad detector / fiducials), separate near-identical objects"], M, 3.95, W - 2 * M, 2.9, 19);
}

// ---------------------------------------------------------------- 28 References
{
  const s = slide("References (selected)", "Discussion");
  const refs = [
    `M. Shukor et al., "SmolVLA: A vision-language-action model for affordable and efficient robotics," arXiv:2506.01844, 2025.`,
    `J. Zheng et al., "X-VLA: Soft-prompted transformer as scalable cross-embodiment vision-language-action model," arXiv:2510.10274, 2025.`,
    `A. Lykov et al., "CognitiveDrone: A VLA model and evaluation benchmark for real-time cognitive task solving and reasoning in UAVs," arXiv:2503.01378, 2025.`,
    `A.-C. Cheng et al., "NaVILA: Legged robot vision-language-action model for navigation," in Proc. RSS, 2025.`,
    `R. Doshi et al., "Scaling cross-embodied learning: One policy for manipulation, navigation, locomotion and aviation," in Proc. CoRL, 2024.`,
    `L. Wang, X. Chen, J. Zhao, and K. He, "Scaling proprioceptive-visual learning with heterogeneous pre-trained transformers," in Proc. NeurIPS, 2024.`,
    `A. Anwar et al., "ReMEmbR: Building and reasoning over long-horizon spatio-temporal memory for robot navigation," arXiv:2409.13682, 2024.`,
    `K. Rana et al., "SayPlan: Grounding large language models using 3D scene graphs for scalable robot task planning," in Proc. CoRL, 2023.`,
    `T. Cheng et al., "YOLO-World: Real-time open-vocabulary object detection," in Proc. IEEE/CVF CVPR, 2024.`,
    `A. Marafioti et al., "SmolVLM: Redefining small and efficient multimodal models," arXiv:2504.05299, 2025.`,
    `E. Todorov, T. Erez, and Y. Tassa, "MuJoCo: A physics engine for model-based control," in Proc. IEEE/RSJ IROS, 2012.`,
  ];
  s.addText(refs.map((t, i) => ({ text: `[${i + 1}] ${t}`, options: { breakLine: i < refs.length - 1, paraSpaceAfter: 4 } })),
    { x: M, y: 1.2, w: W - 2 * M, h: 5.7, fontFace: FONT, fontSize: 15, color: BLACK, valign: "top", isTextBox: true });
}

// ---------------------------------------------------------------- 29 Thank you
{
  const s = pres.addSlide({ masterName: "PLAIN", sectionTitle: "Discussion" });
  s.addText("Thank You", { x: M, y: 2.4, w: W - 2 * M, h: 1.0, fontFace: FONT, fontSize: 44, bold: true, align: "center", color: BLACK });
  s.addText("Questions?", { x: M, y: 3.4, w: W - 2 * M, h: 0.7, fontFace: FONT, fontSize: 28, align: "center", color: BLACK });
  s.addText("Live demo available: interactive simulator (fly.py) and recorded mission videos", { x: M, y: 4.6, w: W - 2 * M, h: 0.5, fontFace: FONT, fontSize: 16, italic: true, align: "center", color: GREY });
}

pres.writeFile({ fileName: path.join(DIR, "Final_Presentation.pptx") }).then((f) => console.log("saved", f));
