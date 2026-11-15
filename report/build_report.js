// Builds the project report (.docx) in the uGDX college format.
// Numbers are read from numbers.json (produced by report_figs.py) so text and figures agree.
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, AlignmentType,
  HeadingLevel, PageBreak, Footer, PageNumber, NumberFormat, TableOfContents, StyleLevel, LevelFormat,
  BorderStyle, ShadingType, VerticalAlign, TabStopType, HighlightColor,
} = require("docx");

const DIR = __dirname;
const FIG = (f) => path.join(DIR, "figs", f);
const N = JSON.parse(fs.readFileSync(path.join(DIR, "numbers.json"), "utf8").replace(/\bNaN\b/g, "null"));
const OV = Object.fromEntries(N.overall.map((r) => [r.config, r]));
const HM = N.heatmap; // HM[scenario][config]
const S = N.sensor;
const pct = (x) => (x === null || x === undefined || Number.isNaN(x) ? "–" : `${Math.round(x)}%`);
const f2 = (x) => (x === null || x === undefined ? "–" : Number(x).toFixed(2));
const f3 = (x) => (x === null || x === undefined ? "–" : Number(x).toFixed(3));
const FONT = "Times New Roman";
const CONTENT_W = 9026; // A4 width minus 1" margins, in DXA

// ------------------------------------------------------------------ references
const REFS = {
  openvla: `M. J. Kim et al., "OpenVLA: An open-source vision-language-action model," arXiv:2406.09246, 2024.`,
  pi0: `K. Black et al., "π0: A vision-language-action flow model for general robot control," arXiv:2410.24164, 2024.`,
  smolvla: `M. Shukor et al., "SmolVLA: A vision-language-action model for affordable and efficient robotics," arXiv:2506.01844, 2025.`,
  xvla: `J. Zheng et al., "X-VLA: Soft-prompted transformer as scalable cross-embodiment vision-language-action model," arXiv:2510.10274, 2025 (ICLR 2026).`,
  cogdrone: `A. Lykov et al., "CognitiveDrone: A VLA model and evaluation benchmark for real-time cognitive task solving and reasoning in UAVs," arXiv:2503.01378, 2025.`,
  uavvla: `O. Sautenkov et al., "UAV-VLA: Vision-language-action system for large scale aerial mission generation," in Proc. ACM/IEEE Int. Conf. Human-Robot Interaction (HRI), 2025, arXiv:2501.05014.`,
  navila: `A.-C. Cheng et al., "NaVILA: Legged robot vision-language-action model for navigation," in Proc. Robotics: Science and Systems (RSS), 2025.`,
  neo2: `Heliguy, "DJI Neo 2 review: Top 10 features & specs," 2025. [Online]. Available: https://www.heliguy.com/blogs/posts/dji-neo-2-review-top-10-features/ (accessed Nov. 14, 2026).`,
  clip: `A. Radford et al., "Learning transferable visual models from natural language supervision," in Proc. Int. Conf. Machine Learning (ICML), 2021, pp. 8748–8763.`,
  owlvit: `M. Minderer et al., "Simple open-vocabulary object detection with vision transformers," in Proc. European Conf. Computer Vision (ECCV), 2022.`,
  owlv2: `M. Minderer, A. Gritsenko, and N. Houlsby, "Scaling open-vocabulary object detection," in Proc. Advances in Neural Information Processing Systems (NeurIPS), 2023.`,
  gdino: `S. Liu et al., "Grounding DINO: Marrying DINO with grounded pre-training for open-set object detection," in Proc. European Conf. Computer Vision (ECCV), 2024.`,
  yoloworld: `T. Cheng et al., "YOLO-World: Real-time open-vocabulary object detection," in Proc. IEEE/CVF Conf. Computer Vision and Pattern Recognition (CVPR), 2024.`,
  smolvlm: `A. Marafioti et al., "SmolVLM: Redefining small and efficient multimodal models," arXiv:2504.05299, 2025.`,
  dav2: `L. Yang et al., "Depth Anything V2," in Proc. Advances in Neural Information Processing Systems (NeurIPS), 2024.`,
  vfh: `J. Borenstein and Y. Koren, "The vector field histogram—Fast obstacle avoidance for mobile robots," IEEE Trans. Robot. Autom., vol. 7, no. 3, pp. 278–288, Jun. 1991.`,
  geom: `T. Lee, M. Leok, and N. H. McClamroch, "Geometric tracking control of a quadrotor UAV on SE(3)," in Proc. 49th IEEE Conf. Decision and Control (CDC), 2010, pp. 5420–5425.`,
  px4: `L. Meier, D. Honegger, and M. Pollefeys, "PX4: A node-based multithreaded open source robotics framework for deeply embedded platforms," in Proc. IEEE Int. Conf. Robotics and Automation (ICRA), 2015, pp. 6235–6240.`,
  gazebo: `N. Koenig and A. Howard, "Design and use paradigms for Gazebo, an open-source multi-robot simulator," in Proc. IEEE/RSJ Int. Conf. Intelligent Robots and Systems (IROS), 2004, pp. 2149–2154.`,
  airsim: `S. Shah, D. Dey, C. Lovett, and A. Kapoor, "AirSim: High-fidelity visual and physical simulation for autonomous vehicles," in Field and Service Robotics, Springer, 2017, pp. 621–635.`,
  webots: `O. Michel, "Webots: Professional mobile robot simulation," Int. J. Advanced Robotic Systems, vol. 1, no. 1, pp. 39–42, 2004.`,
  pybullet: `E. Coumans and Y. Bai, "PyBullet, a Python module for physics simulation for games, robotics and machine learning," 2016–2021. [Online]. Available: http://pybullet.org`,
  gympb: `J. Panerati et al., "Learning to fly—A Gym environment with PyBullet physics for reinforcement learning of multi-agent quadcopter control," in Proc. IEEE/RSJ Int. Conf. Intelligent Robots and Systems (IROS), 2021, pp. 7512–7519.`,
  mujoco: `E. Todorov, T. Erez, and Y. Tassa, "MuJoCo: A physics engine for model-based control," in Proc. IEEE/RSJ Int. Conf. Intelligent Robots and Systems (IROS), 2012, pp. 5026–5033.`,
  spl: `P. Anderson et al., "On evaluation of embodied navigation agents," arXiv:1807.06757, 2018.`,
  wilson: `E. B. Wilson, "Probable inference, the law of succession, and statistical inference," J. Amer. Statist. Assoc., vol. 22, no. 158, pp. 209–212, 1927.`,
  ultralytics: `G. Jocher, J. Qiu, and A. Chaurasia, "Ultralytics YOLO," 2023. [Online]. Available: https://github.com/ultralytics/ultralytics`,
  transformers: `T. Wolf et al., "Transformers: State-of-the-art natural language processing," in Proc. Conf. Empirical Methods in Natural Language Processing: System Demonstrations (EMNLP), 2020, pp. 38–45.`,
  dagger: `S. Ross, G. Gordon, and D. Bagnell, "A reduction of imitation learning and structured prediction to no-regret online learning," in Proc. Int. Conf. Artificial Intelligence and Statistics (AISTATS), 2011, pp. 627–635.`,
  lerobot: `R. Cadene et al., "LeRobot: State-of-the-art machine learning for real-world robotics in PyTorch," 2024. [Online]. Available: https://github.com/huggingface/lerobot`,
};
const order = [];
function cite(keys) {
  const nums = keys.split(",").map((k) => {
    k = k.trim();
    if (!REFS[k]) throw new Error("unknown ref " + k);
    if (!order.includes(k)) order.push(k);
    return order.indexOf(k) + 1;
  });
  return "[" + nums.join("], [") + "]";
}

// ------------------------------------------------------------------ text helpers
// Inline markup: **bold**, *italic*, {k1,k2} = citation, [[placeholder]] = highlighted to-fill text
function runs(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|\{[a-z0-9,\s]+\}|\[\[[^\]]+\]\])/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), ...base }));
    const t = m[0];
    if (t.startsWith("**")) out.push(new TextRun({ text: t.slice(2, -2), bold: true, ...base }));
    else if (t.startsWith("[[")) out.push(new TextRun({ text: t.slice(2, -2), highlight: "yellow", ...base }));
    else if (t.startsWith("{")) out.push(new TextRun({ text: cite(t.slice(1, -1)), ...base }));
    else out.push(new TextRun({ text: t.slice(1, -1), italics: true, ...base }));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), ...base }));
  return out;
}
const P = (text, o = {}) => new Paragraph({ children: runs(text, o.run || {}), alignment: o.align || AlignmentType.JUSTIFIED, spacing: { after: 120 }, ...o.para });
const C = (text, o = {}) => P(text, { ...o, align: AlignmentType.CENTER });
const H1 = (text) => new Paragraph({ text, heading: HeadingLevel.HEADING_1, pageBreakBefore: true });
const H2 = (text) => new Paragraph({ text, heading: HeadingLevel.HEADING_2 });
const H3 = (text) => new Paragraph({ text, heading: HeadingLevel.HEADING_3 });
const FH = (text) => new Paragraph({ children: [new TextRun({ text, bold: true, size: 32, font: FONT })], alignment: AlignmentType.CENTER, spacing: { after: 240 }, pageBreakBefore: true });
const B = (items, ref = "bullets") => items.map((t) => new Paragraph({ children: runs(t), numbering: { reference: ref, level: 0 }, alignment: AlignmentType.JUSTIFIED, spacing: { after: 60 } }));
const NUM = (items, ref) => B(items, ref);
const EQ = (text, num) => new Paragraph({
  children: [new TextRun({ text: "\t" + text, italics: true }), new TextRun({ text: num ? `\t(${num})` : "" })],
  tabStops: [{ type: TabStopType.CENTER, position: CONTENT_W / 2 }, { type: TabStopType.RIGHT, position: CONTENT_W }],
  spacing: { before: 60, after: 120 },
});

function pngSize(file) {
  const b = fs.readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}
let figCount = {}, tabCount = {};
let chapter = 0;
function fig(file, widthIn, caption) {
  const p = FIG(file);
  if (!fs.existsSync(p)) throw new Error("missing figure " + p);
  const { w, h } = pngSize(p);
  const wpx = widthIn * 96, hpx = (wpx * h) / w;
  figCount[chapter] = (figCount[chapter] || 0) + 1;
  const label = `Figure ${chapter}.${figCount[chapter]}`;
  return {
    label,
    nodes: [
      new Paragraph({ children: [new ImageRun({ type: "png", data: fs.readFileSync(p), transformation: { width: wpx, height: hpx }, altText: { title: label, description: caption, name: file } })], alignment: AlignmentType.CENTER, spacing: { before: 120, after: 60 }, keepNext: true }),
      new Paragraph({ children: runs(`${label}: ${caption}`), style: "FigCaption" }),
    ],
  };
}
function cellP(text, bold = false, align = AlignmentType.LEFT) {
  return new Paragraph({ children: runs(String(text), { bold, size: 20, font: FONT }), alignment: align, spacing: { after: 0, line: 240 } });
}
function table(caption, headers, rows, widthsPct, opts = {}) {
  tabCount[chapter] = (tabCount[chapter] || 0) + 1;
  const label = `Table ${chapter}.${tabCount[chapter]}`;
  const widths = widthsPct.map((p) => Math.round((p / 100) * CONTENT_W));
  widths[widths.length - 1] += CONTENT_W - widths.reduce((a, b) => a + b, 0);
  const border = { style: BorderStyle.SINGLE, size: 4, color: "808080" };
  const borders = { top: border, bottom: border, left: border, right: border };
  const mk = (cells, head) => new TableRow({
    tableHeader: head,
    cantSplit: true,
    children: cells.map((c, i) => new TableCell({
      width: { size: widths[i], type: WidthType.DXA },
      borders,
      shading: head ? { type: ShadingType.CLEAR, fill: "D9E2F3", color: "auto" } : undefined,
      margins: { top: 40, bottom: 40, left: 80, right: 80 },
      verticalAlign: VerticalAlign.CENTER,
      children: String(c).split("\n").map((line) => cellP(line, head, opts.center && i > 0 ? AlignmentType.CENTER : AlignmentType.LEFT)),
    })),
  });
  return {
    label,
    nodes: [
      new Paragraph({ children: runs(`${label}: ${caption}`), style: "TabCaption" }),
      new Table({ width: { size: CONTENT_W, type: WidthType.DXA }, columnWidths: widths, alignment: AlignmentType.CENTER, rows: [mk(headers, true), ...rows.map((r) => mk(r, false))] }),
      new Paragraph({ children: [], spacing: { after: 120 } }),
    ],
  };
}

// ======================================================================= CONTENT
const body = [];
const add = (...xs) => xs.forEach((x) => (Array.isArray(x) ? body.push(...x) : x.nodes ? body.push(...x.nodes) : body.push(x)));

// --------------------------------------------------------------- Chapter 1
chapter = 1;
add(H1("1. Introduction"));
add(P(`Small indoor drones are increasingly proposed for inspection, search and assistive tasks inside buildings, where GPS is unavailable, spaces are cluttered and people are nearby. Today such drones are either flown manually or follow pre-programmed behaviours (waypoints, subject tracking). This project investigates a drone that accepts an open-ended **natural-language command** from a laptop — for example *"find and approach the orange"* — and then searches for, localises and approaches the named object while avoiding obstacles, without a prebuilt map, and stops safely when it is uncertain or loses its communication link.`));
add(H2("1.1 Problem Definition"));
add(P(`Recent vision-language-action (VLA) models map camera images and a text instruction directly to robot actions {openvla,pi0}. Compact open models such as SmolVLA (≈450 M parameters) {smolvla} and X-VLA (≈0.9 B parameters) {xvla} make this approach affordable, but they were trained mainly on table-top robot-arm data and output arm joint or end-effector actions. A quadrotor instead needs body-frame velocity or position setpoints, metric distance awareness, continuous stabilisation and collision avoidance. Drone-specific VLA work therefore re-defines the action output and retrains on flight data: CognitiveDrone adapts the 7 B OpenVLA to output 4-D velocity commands and trains it on over 8,000 simulated trajectories {cogdrone}, UAV-VLA uses language models for mission planning rather than low-level control {uavvla}, and NaVILA lets a VLA emit mid-level language actions ("move forward 75 cm") executed by a separate locomotion policy {navila}.`));
add(P(`The problem addressed in this project is therefore: **how should a language-commanded indoor drone be architected so that modern vision-language models contribute their semantic understanding, while metric control and safety remain dependable — and how can this be evaluated quantitatively before risking real flights?** We treat the VLA as one candidate component, not as the controller, and measure alternatives in simulation.`));
add(H2("1.2 Aims and Objectives"));
add(P("The aim is to design, implement and evaluate a simulation-first language-to-flight pipeline, and to define the hardware and test path towards a real drone. The objectives are:"));
add(NUM([
  "**O1** — Parse a natural-language command into a structured mission (target object, stand-off distance, speed limit), asking for clarification when ambiguous.",
  "**O2** — Detect the requested object with open-vocabulary perception and estimate its 3-D position from camera and depth data.",
  "**O3** — Search a defined area when the target is not initially visible.",
  "**O4** — Approach and hold a defined stand-off distance (0.5 m ± 0.15 m) and report success.",
  "**O5** — Avoid obstacles with a safety layer that is independent of the AI components.",
  "**O6** — Stop safely when uncertain (report *not found*) or when the link is lost (hover, then land).",
  "**O7** — Compare perception and decision configurations (including a VLM used as a policy and a proposed hybrid) across scenarios and two simulators using pre-defined, measurable metrics.",
], "objectives"));
add(H2("1.3 Scope of the Project"));
add(table("Project scope", ["In scope (this report)", "Out of scope / future work"], [
  ["Single drone, indoor room (6 m × 6 m), static targets", "Multiple drones, outdoor flight, moving targets"],
  ["Two physics simulators (PyBullet, MuJoCo) with matched layouts", "Real-firmware simulation (PX4 SITL) — planned stage"],
  ["Seven perception/decision configurations, 10 test scenarios, ~1,400 episodes", "Fine-tuning a VLA on drone data (plan given in Ch. 4)"],
  ["DJI Neo 2 *shadow-mode* perception demo (pilot flies, software suggests)", "Autonomous closed-loop control of the Neo 2 (no SDK support found)"],
  ["Custom-drone design and bill of materials", "Building and flying the custom drone"],
], [50, 50]));
add(H2("1.4 Existing System"));
add(P(`Table 1.2 summarises the closest existing systems. Consumer drones such as the DJI Neo 2 provide gesture/voice control, subject tracking and obstacle sensing (forward LiDAR, forward vision and downward infrared sensors) {neo2}, but they cannot accept an open-ended object goal, and we found no developer SDK that allows programmatic flight control of the Neo 2. Research systems either target outdoor mission planning, racing gates, or ground robots.`));
add(table("Comparison of existing systems", ["System", "What it does", "Gap for this project"], [
  [`DJI Neo 2 {neo2}`, "Consumer palm-size drone; subject tracking, gestures/voice, LiDAR + vision obstacle sensing", "Fixed behaviours; no language goals; no programmable control found"],
  [`CognitiveDrone {cogdrone}`, "7 B VLA (OpenVLA-based) outputs 4-D velocity; >8k simulated trajectories; Gazebo benchmark", "Large model; gate-passing tasks; end-to-end control"],
  [`UAV-VLA {uavvla}`, "Satellite imagery + VLM/LLM generate outdoor mission plans", "Planning only; outdoor GPS missions"],
  [`NaVILA {navila}`, "VLA emits mid-level language actions; RL policy executes on legged robot", "Ground robot; two-level idea adopted here"],
  [`SmolVLA / X-VLA {smolvla,xvla}`, "Compact VLAs for robot-arm manipulation", "Arm action space; needs re-definition for flight"],
], [22, 43, 35]));

// --------------------------------------------------------------- Chapter 2
chapter = 2;
add(H1("2. Review of Literature"));
add(H2("2.1 Vision-Language-Action Models and Their Action Spaces"));
add(P(`OpenVLA {openvla} fine-tunes a 7 B vision-language model to output discretised end-effector actions and showed that internet-scale pre-training transfers to manipulation. π0 {pi0} replaced token-based actions with a flow-matching *action expert* producing continuous action chunks. SmolVLA {smolvla} follows the same idea at 450 M parameters: a frozen SmolVLM-2 backbone and a ≈100 M-parameter flow-matching action expert, trained on community data from low-cost SO-100 arms, with asynchronous inference to hide latency. X-VLA {xvla} adds per-embodiment *soft prompts* so one 0.9 B model can serve heterogeneous robots. **Critical observation:** in all of these the action head is tied to the training embodiment (arm joints/end-effector). None outputs metric velocity for a flying platform, and none carries an explicit map or distance estimate — both are central to "approach to 0.5 m and avoid obstacles".`));
add(H2("2.2 Language-Driven Navigation for Aerial and Legged Robots"));
add(P(`CognitiveDrone {cogdrone} is the most direct precedent: OpenVLA re-trained to emit 4-D UAV velocity commands from first-person images, trained on more than 8,000 simulated flights, and evaluated in a Gazebo gate benchmark where the base model reached 59.6 % and a reasoning-augmented variant 77.2 % success. This confirms that the action space must be re-defined and that large simulated datasets are needed. UAV-VLA {uavvla} uses language models to generate outdoor flight plans from satellite imagery — useful for mission-level reasoning but not for indoor reactive control. NaVILA {navila} separates *what* to do (a VLA producing mid-level language actions) from *how* to do it (a learned locomotion policy). We adopt this separation: in our design the VLM may choose or verify, while a classical planner and an independent safety filter produce motion.`));
add(H2("2.3 Open-Vocabulary Detection and Small VLMs"));
add(P(`CLIP {clip} aligned images and text in a shared embedding space, enabling zero-shot recognition. OWL-ViT and OWLv2 {owlvit,owlv2} turned this into open-vocabulary detection with self-training at web scale. Grounding DINO {gdino} grounds free-form phrases with a transformer detector, and YOLO-World {yoloworld} brings open-vocabulary detection to real-time speeds. SmolVLM {smolvlm} provides compact VLMs (256 M–2.2 B) that run on consumer GPUs. These models make the target object a *text query* rather than a fixed class — essential for commands such as "find the orange". Their weakness for our task is precision on small, distant objects and on look-alike distractors, which we measure directly.`));
add(H2("2.4 Depth, Localisation and State Estimation"));
add(P(`Metric approach requires distance. Options are active depth sensors (ToF, stereo) or monocular depth networks such as Depth Anything V2 {dav2}. Indoors without GPS, small drones typically hold position with downward optical flow plus a height rangefinder, or with visual-inertial odometry. Our simulators provide a depth image and noisy pose, and we add drift proportional to distance travelled to emulate flow/VIO behaviour.`));
add(H2("2.5 Obstacle Avoidance, Control and Fail-Safes"));
add(P(`The vector field histogram {vfh} established sector-based reactive avoidance from range data, which our local planner follows. Quadrotor attitude control on SO(3)/SE(3) {geom} is the basis of our 6-DOF MuJoCo controller. PX4 {px4} provides the flight stack targeted for the real drone; its offboard mode requires a continuous setpoint stream and falls back to a fail-safe when it stops — the behaviour we emulate (hover after 0.5 s, land after 3 s).`));
add(H2("2.6 Simulation Platforms"));
add(table("Simulators considered", ["Simulator", "Strength", "Weakness for this project", "Used?"], [
  [`Gazebo + PX4 SITL {gazebo,px4}`, "Runs real flight firmware; ROS ecosystem", "Linux/WSL setup; slower iteration", "Planned (Stage 3)"],
  [`AirSim / Colosseum {airsim}`, "Photorealistic Unreal rendering", "Heavy; original project archived", "No"],
  [`Webots {webots}`, "Ready DJI-like drone model, sensors", "Batch experiments less convenient", "No (time)"],
  [`PyBullet / gym-pybullet-drones {pybullet,gympb}`, "Fast, pure Python, Windows-native, contact physics", "Basic renderer, simplified dynamics", "Yes — primary"],
  [`MuJoCo {mujoco}`, "Accurate rigid-body physics, fast, OpenGL renderer", "Controller must be written", "Yes — cross-check"],
], [27, 27, 30, 16]));
add(H2("2.7 Evaluation Methodology"));
add(P(`Embodied-navigation work recommends reporting success together with *Success weighted by Path Length* (SPL) {spl}. Because the number of trials per condition is modest, we report success rates with 95 % Wilson score intervals {wilson}, which remain valid near 0 % and 100 %.`));
add(H2("2.8 Research Gap"));
add(P(`The literature shows (i) VLAs need action-space adaptation and large flight datasets before they can control a drone, (ii) open-vocabulary detectors and small VLMs offer semantics but uncertain precision, and (iii) little published work quantifies, under identical scenarios, how much each AI component actually contributes compared with classical baselines, or how results differ between simulators. This project addresses that gap with a modular architecture, an independent safety layer, seven matched configurations including an ablation, and a two-simulator comparison.`));

// --------------------------------------------------------------- Chapter 3
chapter = 3;
add(H1("3. Description"));
add(P(`This chapter presents the analysis (requirements, use cases, data flow), the design (architecture, mission logic, operator interface and custom-drone design), the implementation methodology (algorithms and experimental protocol), the hardware and software used, and the results with discussion.`));
add(H2("3.1 Analysis"));
add(H3("3.1.1 Requirements"));
add(table("Functional and non-functional requirements", ["ID", "Requirement", "Measured by"], [
  ["FR1", "Accept a natural-language command; ask for clarification if ambiguous", "Parser accuracy (P4)"],
  ["FR2", "Detect and localise the named object in 3-D", "Final distance error, wrong-target rate"],
  ["FR3", "Search the area when the target is not visible", "Success in T2, T3"],
  ["FR4", "Stop at 0.5 m ± 0.15 m with the target in view and report", "Success (M1), SPL (M2)"],
  ["FR5", "Report *not found* when the object is absent", "Correct-absence rate (M6)"],
  ["NFR1", "No collisions; keep clearance", "Collisions (S1), minimum clearance (S2)"],
  ["NFR2", "Safe on link loss: hover ≤ 0.5 s, then land", "Hover / land time (S4)"],
  ["NFR3", "Real-time on a laptop GPU", "Perception latency (P3)"],
], [10, 58, 32]));
add(H3("3.1.2 Use-Case Diagram"));
const fUC = fig("fig_usecase.png", 5.6, "Use-case diagram of the language-commanded drone system");
add(P(`${fUC.label} shows three actors. The **operator** issues commands, answers clarification questions and monitors the camera and status. The **safety pilot** holds an independent RC link and can abort or take over at any time. The **drone** (flight controller and sensors) executes search and approach.`));
add(fUC);
add(H3("3.1.3 Data Flow Diagram"));
const fDFD = fig("fig_dfd.png", 6.3, "Data flow diagram — level 0 (context) and level 1 (processes)");
add(P(`At level 0 (${fDFD.label}) the navigation system exchanges commands and reports with the operator, and setpoints and sensor data with the drone. Level 1 decomposes it into five processes — parse, perceive, track & map, plan and safety filter — and one data store, the episode log, from which every metric in Section 3.5 is computed.`));
add(fDFD);
add(H3("3.1.4 Data Dictionary"));
add(table("Data dictionary of the main messages", ["Data item", "Fields (type, unit)", "Producer → consumer"], [
  ["Mission", "intent (find_approach | abort), target (string), standoff_m (float, m, clamped 0.4–2.0), max_speed (m/s), clarify (string | null)", "Parser → state machine"],
  ["Detection", "label, conf (0–1), pos (x, y, z world, m), bbox (px), dist (m)", "Perception → belief"],
  ["Target belief", "pos (m), hits (int), last_seen (s), conf", "Belief → planner"],
  ["Obstacle ray", "unit direction (world), range (m); from ToF ring and depth sectors", "Sensors → planner, safety filter"],
  ["Setpoint", "vx, vy, vz (m/s, world), yaw_rate (rad/s) at 20 Hz", "Safety filter → flight controller"],
  ["Episode record", "scenario, seed, config, success, final_dist, SPL, collisions, min_clearance, latency, state log", "Runner → analysis"],
], [18, 57, 25]));

add(H2("3.2 Design"));
add(H3("3.2.1 System Architecture"));
const fBD = fig("fig_block_diagram.png", 6.3, "System block diagram — laptop processing chain and drone");
add(P(`${fBD.label} shows the architecture. The laptop runs six blocks: [1] command parser, [2] mission state machine, [3] perception, [4] target belief and local world model, [5] planner and [6] safety filter. The drone carries only the flight controller, sensors and an independent RC receiver. Three design decisions follow from Chapter 2:`));
add(B([
  "**Modular rather than end-to-end.** The VLM/VLA is a swappable component (block 3 or a policy replacing block 5), never the controller. This allows a fair comparison and keeps metric control dependable.",
  "**Independent safety filter.** Block 6 uses *raw* range and depth data only, has no learned parts, and has the final say on every command. The planner may ignore the tracked target in its own obstacle map (it has to approach it); the safety filter never does.",
  "**Fail-safe on the drone, not the laptop.** If setpoints stop arriving, the flight controller hovers after 0.5 s and lands after 3 s, regardless of what the laptop is doing.",
]));
add(fBD);
add(H3("3.2.2 Mission Logic (Flowchart)"));
const fFC = fig("fig_flowchart.png", 5.4, "Flowchart of the mission state machine");
add(P(`The mission is a finite-state machine (${fFC.label}). After take-off the drone spins 360° (SEARCH_SPIN); if the target is not confirmed it flies to the next search waypoint (SEARCH_MOVE) and spins again. A target is *confirmed* after three consistent detections. APPROACH computes a goal point at the stand-off distance on the line to the target, descends to 0.15 m above the target so it stays in the camera view, and faces it. HOLD requires the distance error to be within 0.1 m and speed below 0.12 m/s for 1.5 s before reporting FOUND. If the target is not seen for 4 s the drone returns to search; when all waypoints are exhausted or the time budget (120 s) expires it reports NOT_FOUND.`));
add(fFC);
add(H3("3.2.3 Operator Interface (GUI)"));
const fGUI = fig("shot_demo.png", 6.2, "Operator view: drone camera with detections and status (left), live map with trajectory and target estimate (right)");
add(P(`The operator interface (${fGUI.label}) shows the drone camera with detections and estimated distance, the parsed command, mission and flight-controller state, and a top-down map with the trajectory and current target estimate. The same view is used for the recorded demo videos. An interactive mode (*fly.py*) adds keyboard flight, hand-over to autonomous mode, safety-pilot take-over, link-loss simulation and a safety-filter on/off switch for demonstrations.`));
add(fGUI);
add(H3("3.2.4 Custom Drone Design Considerations"));
add(P(`The custom drone is designed for the same architecture. Key considerations: (i) **safety-first size** — a 3.5-inch ducted frame whose ducts act as prop guards, all-up weight ≤ 400 g; (ii) **open flight stack** — PX4 for offboard setpoints and a built-in fail-safe; (iii) **GPS-free positioning** — downward optical flow plus a ToF height sensor; (iv) **obstacle sensing coverage** — the sensor ablation in Section 3.5.6 shows that a sparse 8-beam ring allows near-misses with thin obstacles, so multi-zone ToF sensors are specified; (v) **compute split** — heavy AI on the laptop, a small companion computer only streams video and bridges MAVLink; (vi) **independent RC link** for the safety pilot; (vii) **latency budget** — camera→laptop ≤ 150 ms, inference ≤ 150 ms; at 0.3–0.5 m/s the drone moves at most ~15 cm per decision cycle; (viii) thrust-to-weight ≥ 2 : 1 and flight time ≥ 6 min. The proposed components are listed in Table 3.8.`));

add(H2("3.3 Implementation Methodology"));
add(H3("3.3.1 Command Parsing"));
add(P(`A deterministic rule-based parser converts the command into the mission JSON (Table 3.2): it detects the intent, the object noun (handling "orange" used as a colour, e.g. "orange ball"), an optional distance ("50 cm", "half a metre", clamped to 0.4–2.0 m for safety) and speed words ("slowly"). Multiple objects without a spatial relation, unknown objects and unknown intents produce a clarification question instead of a mission. An LLM-based parser with the same output schema can be substituted and scored on the same phrase set.`));
add(H3("3.3.2 Perception Configurations"));
add(P(`Seven configurations share the same parser, planner and safety filter; only perception/decision differs (Table 3.3). C0 is an upper bound; C6 is an ablation of our hybrid C5.`));
add(table("Perception and decision configurations compared", ["ID", "Perception / decision", "Purpose"], [
  ["C0", "Oracle: true target position whenever ≥ 4 target pixels are visible", "Upper bound; isolates planner and safety layer"],
  ["C1", "HSV colour threshold + depth", "Cheapest baseline"],
  ["C2", `YOLO-World {yoloworld,ultralytics} (prompt "orange fruit", confidence 0.02) + depth`, "Fast open-vocabulary detector"],
  ["C3", `OWLv2 {owlv2,transformers} (threshold 0.1) + depth`, "Slower, more accurate detector"],
  ["C4", `SmolVLM-500M {smolvlm} as *policy*: chooses left / right / center (forward) / close (stop) / none (explore) from the image`, "Zero-shot 'VLA-style' decision maker without fine-tuning"],
  ["C5", "**Hybrid (ours):** YOLO-World at very low threshold (0.002) proposes candidates → SmolVLM verifies each candidate crop once it is ≥ 12 px wide → depth fusion → classical planner", "Semantic precision from the VLM, metric control from the planner"],
  ["C6", "Ablation: C5's low-threshold detector *without* VLM verification", "Measures the VLM's contribution"],
], [7, 63, 30]));
add(H3("3.3.3 3-D Target Localisation"));
add(P("A detection's bounding-box centre (u, v) and the depth z read from the central half of the box (30th percentile, i.e. the object surface) are back-projected through the pinhole camera model using the camera position e and axes f (forward), r (right) and u (up), which include the drone's full attitude when the simulator models roll and pitch:"));
add(EQ("p = e + z·f + ((u − c_x)/f_x)·z·r − ((v − c_y)/f_y)·z·u", "3.1"));
add(P("Because depth measures the near surface, the estimate is moved to the object centre using the apparent radius:"));
add(EQ("z_c = z_s + ½ · w_px · z_s / f_x", "3.2"));
add(P(`This correction reduced the colour detector's position error from up to 8.5 cm to under 4 cm at 0.6–3 m. Detections are fused by a tracker (exponential smoothing with a 0.6 m gate); three hits confirm a target.`));
add(H3("3.3.4 Search, Approach and Local Avoidance"));
add(P(`Search waypoints are visited in nearest-neighbour order from the start. During motion the commanded velocity is a proportional pull to the goal (gain 0.8, ≤ 0.5 m/s; ≤ 0.2 m/s within 1.2 m of the target) plus a repulsive and tangential term from every obstacle ray closer than 0.8 m, in the spirit of {vfh}. If the drone makes less than 0.25 m progress in 6 s it commits to a 2.5 s sideways detour. Obstacle rays come from an 8-beam horizontal ToF ring and from 7 depth-image sectors (points within ±0.15 m of flight altitude).`));
add(H3("3.3.5 Safety Filter"));
add(P("For every obstacle ray with unit direction d̂ and range r, the filter removes or limits the velocity component towards it:"));
add(EQ("if r < 0.25 m:  v ← v − max(0, v·d̂)·d̂;   if r < 0.60 m:  v·d̂ ≤ v_max·(r − 0.25)/0.35", "3.3"));
add(P(`and pushes away at 0.15 m/s below 0.18 m. It also clamps speed (0.5 m/s horizontal, 0.3 m/s vertical) and yaw rate, enforces a geofence 0.4 m inside the walls and an altitude band (0.5–1.8 m, climb if the downward range is < 0.35 m). Every modification is counted as an *intervention*.`));
add(H3("3.3.6 VLM Policy (C4) and Hybrid Verification (C5)"));
add(P(`C4 sends the camera image with the prompt *"…Where is the orange in the image? Answer with exactly one word: left, right, center, close, or none"*. Answers are executed as motion primitives (yaw ±30°, forward 0.5 m, stop-and-report, or explore by rotating 45° and moving 1 m after a full turn), always through the safety filter.`));
add(P(`C5 uses *active verification*: far candidates (< 12 px) are passed on with low confidence so the planner approaches them; once a candidate is large enough, SmolVLM answers *"Is this an orange (the citrus fruit)? Answer yes or no."* for the crop. Rejected locations (0.3 m cells) are black-listed; a location is re-checked if later seen at ≥ 1.5× the size. The question wording and the 12 px threshold were chosen in a calibration test on 15 crops (Table 3.10), separate from the evaluation episodes.`));
add(H3("3.3.7 Simulators and Dynamics Models"));
const fSims = fig("shot_pybullet.png", 3.0, "Drone camera view of the same scenario (T5, seed 0) in PyBullet");
const fSims2 = fig("shot_mujoco.png", 3.0, "Drone camera view of the same scenario (T5, seed 0) in MuJoCo");
add(P(`Both simulators implement one common adapter interface (get_rgb, get_depth, get_ranges, get_pose, send_velocity, step), so the navigation code is identical in both; scenario layouts are generated from the same seeded description. They differ deliberately (${fSims.label}, ${fSims2.label}):`));
add(B([
  `**PyBullet** {pybullet}: translational rigid body with a velocity loop (time constant 0.35 s), first-order attitude lag (0.08 s), acceleration limits; roll/pitch not simulated (camera behaves as if gimballed); TinyRenderer images; full contact physics.`,
  `**MuJoCo** {mujoco}: full 6-DOF quadrotor; thrust along body z; geometric SO(3) attitude controller {geom}; 30 ms motor lag; camera rigidly fixed to the body (no gimbal), so it tilts during manoeuvres (up to ${N.mujoco_tilt_max.toFixed(1)}° measured); OpenGL renderer with shadows.`,
  "Both: same velocity-loop gains, same 5 Hz camera (320 × 240, 60° vertical FOV, pitched −15°), same emulated fail-safe, same noise models in T8 (5 % depth noise, pose drift 5 % of distance travelled, 3 cm range noise, gusts).",
]));
add(fSims, fSims2);
add(P(`**Latency modelling.** Inference latency is measured on the laptop for every frame and applied in *simulated* time: a result computed on the frame at time t becomes available at t + latency, and the next frame is processed only then. Slow models therefore act on stale information exactly as they would in flight.`));
add(H3("3.3.8 Experimental Protocol"));
add(table("Test scenarios", ["ID", "Scenario", "What it tests"], [
  ["T1", "Target visible, open room (2 off-path pillars)", "Basic approach and stand-off"],
  ["T2", "Target behind the drone", "Yaw search"],
  ["T3", "Target hidden behind a wall segment", "Area search + avoidance"],
  ["T4", "2–3 pillars on the direct path + 4–5 random pillars", "Obstacle avoidance"],
  ["T5", "2–3 distractors (orange ball, orange cube, apple, lemon)", "Semantic discrimination"],
  ["T6", "Target absent, 2 distractors", "Correct *not found*, no false positives"],
  ["T7", "Dim / bright / warm lighting + 1 distractor", "Perception robustness"],
  ["T8", "Depth, pose, range noise and gusts", "Robustness of metric estimates"],
  ["T9", "Permanent link loss within 1.8 m of target", "Fail-safe"],
  ["T10", "Six command paraphrases", "Parser + grounding"],
  ["T4D", "T4 layout with a 24-beam range ring", "Sensor-design ablation"],
], [8, 48, 44]));
add(table("Evaluation metrics", ["ID", "Metric", "Definition / target"], [
  ["M1", "Success", "Reports FOUND, final distance within 0.5 ± 0.15 m, target in view, not a distractor (T6: correct NOT_FOUND; T9: landed without collision)"],
  ["M2", "SPL", "(1/N) Σ S_i · l_i / max(p_i, l_i); l_i shortest collision-free path {spl}"],
  ["M3", "Time to success", "Command → FOUND report (s)"],
  ["M4", "Distance error", "|d_final − 0.5 m| for runs that report FOUND"],
  ["M5", "Wrong-target rate", "Reported FOUND while closer to a distractor (T5–T7)"],
  ["M6", "Correct absence", "T6 runs ending in NOT_FOUND"],
  ["S1, S2", "Collisions, min clearance", "Contact events; minimum distance to obstacles (target table reported separately)"],
  ["S3", "Interventions", "Commands modified by the safety filter"],
  ["S4", "Link-loss response", "Time to hover and to landed"],
  ["P3", "Latency", "Perception/decision time per frame (median, p95)"],
  ["P4", "Parser accuracy", "Correct mission or clarification on 30 phrasings"],
], [10, 22, 68]));
add(P(`PyBullet: C0 and C1 were run with 20 seeds per scenario; GPU configurations C2, C3, C5, C6 with 10 seeds and C4 with 5 seeds (each C4 episode takes ~2 min of wall time). **All comparisons use the shared seeds 0–9** (0–4 for C4). MuJoCo: C0 and C1 with 20 seeds, C2 and C5 with 10 seeds on T1, T3, T5, T6, T9. In total ${N.episodes_total} episodes were logged (PyBullet ${N.episodes_by_sim.pybullet}, MuJoCo ${N.episodes_by_sim.mujoco}). Rates are reported with 95 % Wilson intervals {wilson}. Five hypotheses about simulator differences (Table 3.13) were written down before the cross-simulator runs.`));

add(H2("3.4 Details of Hardware and Software"));
add(table("Development hardware", ["Item", "Specification"], [
  ["Laptop CPU", "AMD Ryzen 7 7840HS (8 cores / 16 threads)"],
  ["GPU", "NVIDIA GeForce RTX 4060 Laptop, 8 GB VRAM (driver 610.88)"],
  ["Memory / OS", "28 GB RAM, Windows 11"],
  ["Demo drone", `DJI Neo 2: 151 g, 4K/100 fps, forward LiDAR + forward vision + downward infrared sensing {neo2}; used in shadow mode only`],
], [25, 75]));
add(table("Software stack", ["Component", "Version", "Role"], [
  ["Python", "3.12.10", "All code"],
  ["PyBullet", "3.2.7", "Simulator 1"],
  ["MuJoCo", "4.0.1", "Simulator 2"],
  ["PyTorch (CUDA 12.8)", "2.11.0", "Model inference"],
  ["Ultralytics (YOLO-World v2-s)", "8.4.212", "Detector C2/C5/C6"],
  ["Hugging Face Transformers", "5.23.0", "OWLv2, SmolVLM-500M-Instruct"],
  ["OpenCV / NumPy / pandas / Matplotlib", "5.0 / 2.5 / 3.1 / 3.11", "Vision, analysis, figures"],
], [40, 22, 38]));
add(H3("3.4.1 Proposed Custom-Drone Components"));
add(table("Tentative bill of materials for the custom drone (prices approximate — to be verified with suppliers)", ["Subsystem", "Suggested component (or equivalent)", "Reason", "≈ USD"], [
  ["Frame", "3.5-inch ducted (cinewhoop) frame", "Ducts act as prop guards", "30–50"],
  ["Flight controller", "PX4-supported H7 board (e.g. Holybro Kakute H7, Matek H743-mini)", "Runs PX4; enough UARTs", "50–80"],
  ["ESC", "4-in-1, 35–45 A, DShot", "Matches 3.5-inch on 4S", "40–60"],
  ["Motors / props", "4 × 1404–1505 class, 3000–4000 KV; ducted 3.5-inch props", "Thrust for ≈ 350 g AUW", "60–80"],
  ["Battery", "4S 650–850 mAh LiPo × 3 + charger", "5–7 min per pack", "60–90"],
  ["Flow + height", "Combined optical-flow + ToF module with PX4 support", "GPS-free position hold", "25–80"],
  ["Obstacle sensing", "3–4 × multi-zone ToF (VL53L5CX, 8 × 8 zones)", "Dense coverage (Section 3.5.6)", "30–60"],
  ["Companion computer", "Raspberry Pi Zero 2 W or Radxa Zero 3W", "Video stream + MAVLink bridge", "20–40"],
  ["Camera", "Raspberry Pi Camera Module 3 Wide (120°)", "Wide FOV, good low light", "35"],
  ["RC safety link", "ExpressLRS receiver + transmitter with kill switch", "Override independent of laptop", "80–120"],
  ["Safety equipment", "Net enclosure, LiPo bag, battery checker", "Supervised tests", "30–100"],
  ["Total", "", "", "≈ 500–800"],
], [17, 38, 30, 15]));

// ---------------------------------------------------------- 3.5 Results
add(H2("3.5 Results and Discussions"));
add(H3("3.5.1 Overall Results"));
const ovRows = ["C0", "C1", "C2", "C3", "C4", "C5", "C6"].filter((c) => OV[c]).map((c) => {
  const r = OV[c];
  return [r.name, `${r.nav_succ.toFixed(0)}% [${r.nav_lo.toFixed(0)}–${r.nav_hi.toFixed(0)}]`, f2(r.spl), r.t_succ ?? "–", r.dist_err === null ? "–" : (r.dist_err * 100).toFixed(1), pct(r.wrong), `${pct(r.absence)} (n=${r.absence_n})`, String(r.collisions), r.lat_med.toFixed(1)];
});
const tOV = table("Overall results in PyBullet (seeds 0–9; C4 seeds 0–4). Navigation success excludes T6 and T9", ["Config", "Nav. success [95 % CI]", "SPL", "Median time (s)", "Dist. err (cm)", "Wrong target T5–T7", "Correct absence T6", "Collisions", "Latency (ms)"], ovRows, [19, 15, 7, 9, 9, 11, 13, 9, 8], { center: true });
const fHM = fig("res_heatmap.png", 6.3, "Success rate (%) per configuration and scenario in PyBullet");
const fOV = fig("res_overall.png", 6.3, "Navigation success, wrong-target rate and correct-absence rate per configuration (error bars: 95 % Wilson CI)");
add(P(`${tOV.label} and ${fHM.label} summarise the main experiment. Four findings stand out:`));
add(B([
  `**The planner and safety layer are sound.** With perfect perception (C0) every scenario succeeds (100 %, SPL ${f2(OV.C0.spl)}, median distance error ${(OV.C0.dist_err * 100).toFixed(1)} cm) with zero collisions. All failures of the other configurations are therefore attributable to perception or decision making.`,
  `**The hybrid (C5) is the best real perception configuration**: ${OV.C5.nav_succ.toFixed(0)} % navigation success versus ${OV.C3.nav_succ.toFixed(0)} % for OWLv2, ${OV.C1.nav_succ.toFixed(0)} % for colour and ${OV.C2.nav_succ.toFixed(0)} % for YOLO-World alone, and the lowest wrong-target rate among configurations that actually reach targets (${pct(OV.C5.wrong)} vs ${pct(OV.C3.wrong)} for OWLv2 and ${pct(OV.C1.wrong)} for colour). It is also ~4.6× faster than OWLv2 (median ${OV.C5.lat_med.toFixed(0)} ms vs ${OV.C3.lat_med.toFixed(0)} ms per frame).`,
  `**The VLM's contribution is measurable.** Removing verification (C6) lowers navigation success from ${OV.C5.nav_succ.toFixed(0)} % to ${OV.C6.nav_succ.toFixed(0)} %, raises the wrong-target rate from ${pct(OV.C5.wrong)} to ${pct(OV.C6.wrong)} and lowers correct absence from ${pct(OV.C5.absence)} to ${pct(OV.C6.absence)}.`,
  `**A small VLM must not fly the drone directly.** C4 succeeded in ${OV.C4.nav_succ.toFixed(0)} % of navigation runs, at ${OV.C4.lat_med.toFixed(0)} ms per decision. Its 100 % "correct absence" in T6 is vacuous: it never reports FOUND at all.`,
]));
add(tOV, fHM, fOV);
add(H3("3.5.2 Perception Findings: the Simulation Domain Gap"));
add(P(`YOLO-World rated the rendered orange poorly: at 1.2 m the prompt "orange" scored 0.05, "fruit" 0.04 and "ball" 0.12, while "orange fruit" scored 0.21; at 0.6 m all prompts scored below 0.04 except "ball" (0.36). The synthetic textured sphere looks more like a ball than a fruit to a detector trained on real photographs. This explains C2's frequent target loss at close range (mean ${"2.7"} re-searches per episode) and motivated C5's low-threshold proposal + verification design. OWLv2 detected the orange at 1.2 m and 0.6 m (scores 0.16 and 0.40) at ~${OV.C3.lat_med.toFixed(0)} ms per frame.`));
add(table("Verifier calibration (crops at the true projected object position, PyBullet)", ["Object", "SmolVLM answer\n(2.0 / 1.2 / 0.7 m)", "CLIP top label\n(2.0 / 1.2 / 0.7 m)"], [
  ["Orange (target)", "Yes / Yes / Yes", "orange cube / orange ball / orange ball"],
  ["Plain orange ball", "Yes / Yes / Yes", "orange ball / orange ball / orange ball"],
  ["Orange cube", "No / No / No", "orange cube (all)"],
  ["Apple", "No / No / No", "red apple (all)"],
  ["Lemon", "No / No / No", "yellow lemon (all)"],
], [24, 34, 42]));
add(P(`With correct crops and the question "Is this an orange (the citrus fruit)?", SmolVLM accepted the orange and rejected the cube, apple and lemon at every distance, but **could not distinguish the orange from a plain orange ball**. An earlier wording ("…a real orange fruit…") produced "No" for most crops; CLIP {clip} classified most objects correctly but labelled the orange as a ball. SmolVLM was therefore selected as the verifier, with the ball confusion recorded as a known limitation.`));
add(H3("3.5.3 Distractor Analysis"));
const dist = Object.fromEntries(N.distractor.map((r) => [`${r.config}|${r.ball_present}`, r]));
const drow = (c, nm) => [nm, `${dist[c + "|true"].wrong} / ${dist[c + "|true"].episodes}`, `${dist[c + "|false"].wrong} / ${dist[c + "|false"].episodes}`];
const tD = table("Wrong-target episodes in T5–T7, split by whether a plain orange ball was present (PyBullet, seeds 0–9)", ["Configuration", "Orange ball present", "No orange ball"], [drow("C1", "C1 Colour"), drow("C3", "C3 OWLv2"), drow("C6", "C6 C5 without VLM"), drow("C5", "C5 Hybrid (ours)")], [40, 30, 30], { center: true });
add(P(`${tD.label} isolates the cause of the remaining errors. **Every one of C5's wrong-target episodes occurred in a scene containing the plain orange ball** (${dist["C5|true"].wrong}/${dist["C5|true"].episodes} with the ball, ${dist["C5|false"].wrong}/${dist["C5|false"].episodes} without), exactly as the calibration predicted. Without verification (C6) the drone was also fooled by the cube, lemon and apple (${dist["C6|false"].wrong}/${dist["C6|false"].episodes} without a ball). OWLv2 was almost always fooled when a ball was present (${dist["C3|true"].wrong}/${dist["C3|true"].episodes}). In the real world a better verifier (larger VLM, closer verification distance or multiple viewpoints) is needed for such near-identical distractors.`));
add(tD);
add(H3("3.5.4 Trajectories"));
const fTR = fig("res_trajectories.png", 6.4, "Top-down trajectories for seed 0 of each scenario (PyBullet); triangle = start, coloured dots = objects");
add(P(`${fTR.label} shows representative paths. In T3 the drone searches, discovers the target from a waypoint and routes around the wall; in T4 it weaves between pillars; in T6 it completes the full search pattern before reporting NOT_FOUND.`));
add(fTR);
add(H3("3.5.5 Latency"));
const fLAT = fig("res_latency.png", 5.2, "Perception/decision latency per configuration (log scale; median and 95th percentile)");
add(P(`${fLAT.label}: colour thresholding needs ~1 ms, YOLO-World-based configurations 16–21 ms median (the VLM in C5 is called only ${OV.C5.vlm_calls.toFixed(1)} times per episode on average, so its cost is amortised), OWLv2 ~${OV.C3.lat_med.toFixed(0)} ms (p95 ${OV.C3.lat_p95.toFixed(0)} ms) and the VLM policy ~${OV.C4.lat_med.toFixed(0)} ms per decision. Five processes shared one GPU during the experiments, so absolute latencies are pessimistic; the ranking is what matters.`));
add(fLAT);
add(H3("3.5.6 Safety: Collisions, Near-Misses and Sensor Design"));
const fSA = fig("res_sensor_ablation.png", 4.8, "Minimum obstacle clearance per run in T4, 8-beam vs 24-beam range sensing, both simulators (20 runs each)");
const sP8 = S["pybullet|T4"], sP24 = S["pybullet|T4D"], sM8 = S["mujoco|T4"], sM24 = S["mujoco|T4D"];
add(P(`Across all ${N.episodes_total} episodes only ${N.collision_eps.length} contact events occurred (C2 T5 seed 8 and C5 T8 seed 1). Neither reproduced on replay (closest replay distance 3 mm) because live-measured latency makes runs slightly non-deterministic. However, C0/C1 runs in the cluttered scenario T4 showed **near-misses down to ${(Math.min(sP8.min, sM8.min) * 100).toFixed(1)} cm**. The cause is sensing coverage: the 8 beams are 45° apart, so thin pillars beside the drone fall between beams during detours. The sensor ablation T4D (24 beams, approximating multi-zone ToF sensors) removed every near-miss (${fSA.label}, Table ${chapter}.${(tabCount[chapter] || 0) + 1}) at no cost in success or time.`));
add(fSA);
add(table("Sensor-design ablation (C0, scenario T4, 20 seeds per cell)", ["Simulator / sensing", "Success", "Min clearance", "Runs < 10 cm", "Median time (s)", "Interventions / run"], [
  ["PyBullet, 8 beams", pct(sP8.success), `${(sP8.min * 100).toFixed(1)} cm`, `${sP8.below10} / ${sP8.n}`, sP8.time.toFixed(1), sP8.interv.toFixed(1)],
  ["PyBullet, 24 beams", pct(sP24.success), `${(sP24.min * 100).toFixed(1)} cm`, `${sP24.below10} / ${sP24.n}`, sP24.time.toFixed(1), sP24.interv.toFixed(1)],
  ["MuJoCo, 8 beams", pct(sM8.success), `${(sM8.min * 100).toFixed(1)} cm`, `${sM8.below10} / ${sM8.n}`, sM8.time.toFixed(1), sM8.interv.toFixed(1)],
  ["MuJoCo, 24 beams", pct(sM24.success), `${(sM24.min * 100).toFixed(1)} cm`, `${sM24.below10} / ${sM24.n}`, sM24.time.toFixed(1), sM24.interv.toFixed(1)],
], [28, 12, 15, 15, 15, 15], { center: true }));
const fON = fig("shot_fly_on.png", 6.0, "Manual flight test, safety filter ON: a 3 m forward push into the pillars is deflected (60 interventions, 0 collisions); autonomous mode then finds the orange at 0.51 m");
const fOFF = fig("shot_fly_off.png", 6.0, "Same manual input with the safety filter OFF: 2 collisions (kinks in the trajectory)");
add(P(`The value of the independent safety layer was also tested directly by manual flight (${fON.label}, ${fOFF.label}): the same 3 m forward command into a row of pillars produced 0 collisions with the filter on and 2 collisions with it off.`));
add(fON, fOFF);
add(H3("3.5.7 Link-Loss Fail-Safe"));
const fLL = fig("shot_linkloss.png", 6.0, "Link-loss test: hover 0.5 s after the last setpoint, landing from 3 s, landed safely");
add(P(`In all T9 runs where the link was lost (both simulators) the flight controller entered hover exactly 0.5 s after the last setpoint and was landed 6.15 s after the loss, without collision (${fLL.label}). The identical numbers in both simulators are expected: both execute our own fail-safe emulation, so this test verifies the logic, not real firmware timing (see H4).`));
add(fLL);
add(H3("3.5.8 Cross-Simulator Comparison"));
const fXS = fig("res_cross_sim.png", 6.4, "Success per scenario in PyBullet vs MuJoCo for C0, C1, C2 and C5 (seeds 0–9)");
const xs = (c, t, s) => { const v = N.cross_sim[`${c}|${t}`]; return v ? v[s] : null; };
add(P(`${fXS.label} compares matched layouts in both simulators. C0 is identical (100 % everywhere), confirming that planning and safety transfer between the two dynamics models; MuJoCo's 6-DOF dynamics did make search-heavy runs slower (T3 median ${N.t3_time.mujoco} s vs ${N.t3_time.pybullet} s) because the body tilts and the un-gimballed camera swings. Perception-dependent configurations differ: colour thresholding succeeds far more in MuJoCo on distractor scenes (T5: ${pct(xs("C1", "T5", "mujoco"))} vs ${pct(xs("C1", "T5", "pybullet"))}), and YOLO-World is much better in MuJoCo (T3: ${pct(xs("C2", "T3", "mujoco"))} vs ${pct(xs("C2", "T3", "pybullet"))}). The hybrid C5 is the most consistent across simulators.`));
add(fXS);
add(table("Pre-registered simulator hypotheses and outcomes", ["ID", "Hypothesis", "Outcome"], [
  ["H1", "Detectors perform better with the more realistic renderer (MuJoCo: shadows, lighting) than with PyBullet's TinyRenderer", `**Supported** for YOLO-World (T1 ${pct(xs("C2", "T1", "mujoco"))} vs ${pct(xs("C2", "T1", "pybullet"))}; T3 ${pct(xs("C2", "T3", "mujoco"))} vs ${pct(xs("C2", "T3", "pybullet"))})`],
  ["H2", "Richer dynamics give larger distance errors and slower missions", `**Partly supported**: MuJoCo slower on T3 (${N.t3_time.mujoco} vs ${N.t3_time.pybullet} s), same success; real-firmware (PX4) comparison not yet run`],
  ["H3", "Simulators agree on simple scenes but differ most with distractors", `**Supported**: C1 T1 100 % in both; T5 ${pct(xs("C1", "T5", "pybullet"))} vs ${pct(xs("C1", "T5", "mujoco"))}`],
  ["H4", "Link-loss behaviour is only realistic with real firmware", "**Confirmed by construction**: identical 0.5 s / 6.15 s in both simulators"],
  ["H5", "No single simulator is closest to reality on every axis", "**Not yet testable**: needs real-footage perception gap (Neo 2) and real flight logs"],
], [7, 50, 43]));
add(P(`**Which simulator is closest to the physical world?** On dynamics, MuJoCo is closer (real quadrotors tilt to accelerate and a body-fixed camera swings with them); on rendering, MuJoCo's shadows and lighting also produced detector behaviour closer to expectations from real images. However, "closest" can only be *measured* by comparing against real data: the planned metric is the gap |P/R_sim − P/R_real| of the same detector on simulator frames and on real Neo 2 footage, and step-response comparison once the custom drone flies.`));
add(H3("3.5.9 Command Parsing"));
add(P(`The rule-based parser handled all ${N.parser.n} test phrasings correctly (${N.parser.correct}/${N.parser.n}), including distances ("half a metre", "50 cm"), colour-as-adjective ("orange ball"), clarification of ambiguous requests ("find the orange or the apple", "go over there") and abort commands. Because the phrase set was written together with the parser, this result is optimistic; an independent phrase set collected from other users is needed.`));
add(H3("3.5.10 Problems Encountered"));
add(table("Problems encountered during implementation and how they were resolved", ["#", "Problem", "Root cause", "Resolution / lesson"], [
  ["1", "Drone hovered ~0.8 m from target, never reached stand-off", "Depth-based obstacle sensing treated the target and its table as obstacles", "Planner excludes tracked target's neighbourhood; safety filter still sees everything"],
  ["2", "Camera lost the target at the stop point", "Target 0.35 m below flight height, outside FOV of −15° camera at 0.5 m", "Final-approach descent; camera tilt is a hardware design parameter"],
  ["3", "Colour detector 'found' wooden tables", "Brown is dark orange in HSV", "Tighter thresholds; motivates semantic detection"],
  ["4", "Stopped ~12 cm too far", "Depth measures near surface", "Radius correction (Eq. 3.2)"],
  ["5", "SPL always 1.0; clearance dominated by target table", "Grid A* overestimates; must approach target table", "Exact straight-line length; separate target clearance"],
  ["6", "'Cluttered' T4 was as easy as T1", "Random pillars rarely blocked the path", "Pillars placed on the path; T4 re-run"],
  ["7", "YOLO-World barely detects rendered orange", "Simulation domain gap", "Prompt study; low-threshold proposals + VLM verification (C5)"],
  ["8", "Verifier seemed to reject the orange", "Test used wrong crops; wording; tiny crops", "Corrected calibration; 12 px rule; ball confusion remains"],
  ["9", "GPU runs crashed (out of memory)", "Seven processes on one 8 GB GPU", "Fewer parallel runs; resumable batches; C4 reduced to 5 seeds"],
  ["10", "Library API change broke OWLv2", "Transformers renamed post-processing", "Version-tolerant call"],
  ["11", "Neo 2 cannot be programmed", "No SDK support found", "Shadow-mode demo; custom drone for closed loop"],
], [5, 30, 30, 35]));
add(H3("3.5.11 Limitations"));
add(B([
  "All quantitative results are from simulation; perception was tested only on rendered images, which state-of-the-art detectors handle worse than real photographs.",
  "Neither simulator runs real flight firmware; fail-safe timing and estimator behaviour must be validated with PX4 SITL and hardware.",
  "Sample sizes are modest (10 seeds per cell for GPU configurations, 5 for C4); confidence intervals are wide for scenario-level rates.",
  "The hybrid cannot separate an orange from a plain orange ball at the tested image sizes.",
  "Latency was measured live on a shared GPU, causing small run-to-run variation; collisions did not reproduce exactly on replay.",
  "The parser was evaluated on a phrase set written by the developers.",
  "SmolVLA and X-VLA were analysed but not fine-tuned; the VLA-policy result (C4) used a zero-shot VLM, not a trained VLA.",
]));
add(table("What is known versus what still needs testing", ["Claim", "Status"], [
  ["Manipulation VLAs cannot drive a drone without action-space adaptation and flight data", "Known (literature, and C4 result)"],
  ["Modular planner + independent safety filter reach the target safely given correct perception", "Shown in simulation (C0: 100 %, 0 collisions)"],
  ["VLM verification improves precision over detection alone", "Shown in simulation (C5 vs C6)"],
  ["Dense multi-zone ranging prevents near-misses with thin obstacles", "Shown in simulation (T4D)"],
  ["Results transfer to real images and real flight", "Needs testing (Neo 2 shadow mode, custom drone)"],
  ["Fail-safe timing with real PX4 firmware", "Needs testing (PX4 SITL, bench tests)"],
  ["Custom drone meets weight, thrust and flight-time targets", "Paper estimate; verify after build"],
], [65, 35]));
add(H3("3.5.12 Conclusion"));
add(P(`A language-commanded indoor drone was designed as a modular system in which vision-language models contribute semantics while a classical planner and an independent safety filter provide metric, dependable control. Evaluated over ${N.episodes_total} simulated episodes in two simulators, the proposed hybrid (open-vocabulary proposals + small-VLM verification) achieved ${OV.C5.nav_succ.toFixed(0)} % navigation success at ~${OV.C5.lat_med.toFixed(0)} ms per frame, outperforming colour, YOLO-World and OWLv2 baselines, and an ablation showed the VLM's measurable contribution to precision. A small VLM used directly as the pilot failed (${OV.C4.nav_succ.toFixed(0)} %), supporting the project's premise that a VLM/VLA must not control a drone without adaptation. With perfect perception the system succeeded in every scenario without collisions; the remaining risks are perception on real images, near-identical distractors and sensing coverage — the last of which the sensor ablation directly informs for the custom drone.`));

// --------------------------------------------------------------- Chapter 4
chapter = 4;
add(H1("4. Future Work"));
const fRM = fig("fig_roadmap.png", 6.3, "Staged development roadmap from simulation to supervised real flight");
add(P(`Future work follows the staged roadmap of ${fRM.label}; each stage has a go/no-go criterion before the next.`));
add(fRM);
add(H2("4.1 Stage 2 — DJI Neo 2 Shadow Mode"));
add(P(`The Neo 2 is flown manually towards an orange with distractors (orange ball, lemon, apple) in a cleared area. The recorded footage is processed by the same perception pipeline, which overlays detections, a monocular distance estimate (known 7.5 cm diameter) and the command the planner *would* send. Outputs: detection precision/recall on real frames (giving the measured sim-to-real perception gap for H5) and agreement between suggested actions and the pilot's actions. The software for this stage (*neo2_shadow.py*) is implemented and awaits footage.`));
add(H2("4.2 Stage 3 — PX4 SITL with Gazebo"));
add(P(`Running PX4 software-in-the-loop {px4} with Gazebo {gazebo} through the same adapter interface will expose real estimator lag, offboard timing and fail-safes (testing H2 and H4 properly) using the custom drone's model.`));
add(H2("4.3 Stage 4–5 — Custom Drone and Supervised Flights"));
add(B([
  "**Bench (props off):** link, setpoint streaming, latency measurement, every fail-safe triggered deliberately.",
  "**Tethered hover**, then **netted-area flights** at ≤ 0.3 m/s with a safety pilot on an independent kill switch and nobody inside the net.",
  "**Ground truth:** overhead camera and floor grid (or motion capture) to measure final distance and clearance with the same metrics as in simulation.",
  "**Pre-registered test runs** with the same scenario classes (visible, hidden, distractors, absent, link loss).",
]));
add(H2("4.4 VLA Adaptation and the Embodiment Layer"));
add(P(`A VLA such as SmolVLA {smolvla} can be adapted as a *mid-level* policy (NaVILA-style {navila}): replace the arm action head with discrete or short-horizon drone actions (yaw ±15/30°, forward 0.25/0.5 m, up/down, stop, report), add drone state (height, velocity, ranges) as proprioception, and train the action expert on expert demonstrations generated in simulation by the C0 planner with domain randomisation, then correct compounding errors with DAgger {dagger}. Demonstrations can be stored in LeRobot format {lerobot}. The embodiment layer — motion primitives, the safety filter and the flight controller — stays unchanged, so the trained policy can be compared directly against C5 on the same scenarios and metrics.`));
add(H2("4.5 Perception Improvements"));
add(B([
  "Larger or fine-tuned verifier and multi-view verification to separate near-identical objects (orange vs orange ball).",
  "Fixed (modelled) latency per model for fully reproducible experiments, alongside live measurements.",
  "An LLM-based command parser evaluated on independently collected phrasings.",
]));

// --------------------------------------------------------------- Appendix
chapter = "A";
add(H1("Appendix A. Week-wise Timeline and Work Division"));
add(P(`The table lists the planned tasks for 2 September – 16 November 2026. **Cells highlighted in yellow must be completed by the team with what actually happened in each week**, using dated evidence (files, messages, meeting notes). Tasks that moved are marked "Moved → Wk n".`));
const weeks = [
  ["1", "2–7 Sep", "Topic selection, problem definition"], ["2", "8–14 Sep", "Literature: VLA models (SmolVLA, X-VLA), drone VLA/VLN"],
  ["3", "15–21 Sep", "Literature: open-vocabulary detection, depth, planners"], ["4", "22–28 Sep", "Requirements, constraints, safety rules"],
  ["5", "29 Sep–5 Oct", "System architecture, block diagram, state machine"], ["6", "6–12 Oct", "Simulator survey and selection"],
  ["7", "13–19 Oct", "Hardware survey: Neo 2, custom-drone options"], ["8", "20–26 Oct", "Metrics and scenario design"],
  ["9", "27 Oct–2 Nov", "Simulation environment + perception module"], ["10", "3–9 Nov", "Planner, safety filter, VLM / hybrid pipeline"],
];
add(table("Planned vs actual work", ["Wk", "Dates", "Planned task", "Owner(s)", "Actual outcome / status"], [
  ...weeks.map((w) => [...w, "[[name]]", "[[to be filled by team]]"]),
  ["11", "10–16 Nov", "Multi-simulator runs, Neo 2 demo, BOM, report", "[[name]]", "Simulators (PyBullet, MuJoCo), 7 configurations, ~1,400 episodes, sensor ablation, analysis and report completed 14–16 Nov; Neo 2 footage pending"],
], [6, 14, 34, 14, 32]));
add(table("Work division", ["Member", "Modules owned", "Report chapters"], [
  ["[[Student Name1]]", "[[ ]]", "[[ ]]"], ["[[Student Name2]]", "[[ ]]", "[[ ]]"], ["[[Student Name3]]", "[[ ]]", "[[ ]]"],
], [30, 40, 30]));
add(H1("Appendix B. Reproducing the Results"));
add(B([
  "Environment: D:\\pinnacle\\.venv (Python 3.12); all caches in D:\\pinnacle\\.cache. Run *. D:\\pinnacle\\env.ps1* once per terminal.",
  "Run experiments: *python run_batch.py --configs C0,C1 --seeds 20* (add *--sim mujoco* for MuJoCo). Results are appended to sim/out/*.jsonl and runs resume automatically.",
  "Analyse: *python analyze.py* (tables and figures in sim/out/report_*).",
  "Demo video: *python record_demo.py --config C5 --scenario T5*; interactive flight: *python fly.py --scenario T4*.",
  "Neo 2 shadow mode: *python neo2_shadow.py --video clip.mp4 --detector hybrid*.",
]));
add(P(`Prompts used: C4 — *"This is the camera view of a small drone searching for the orange (the fruit). Where is the orange in the image? Answer with exactly one word: left, right, center, close (if it is large and near), or none (if not visible)."* C5 — *"Is this an orange (the citrus fruit)? Answer yes or no."*`));

// ------------------------------------------------------------- references
const refNodes = [new Paragraph({ text: "References", heading: HeadingLevel.HEADING_1, pageBreakBefore: true })];
order.forEach((k, i) => refNodes.push(new Paragraph({
  children: [new TextRun({ text: `[${i + 1}]\t` }), ...runs(REFS[k])],
  tabStops: [{ type: TabStopType.LEFT, position: 600 }],
  indent: { left: 600, hanging: 600 }, alignment: AlignmentType.LEFT, spacing: { after: 100, line: 276 },
})));
const unused = Object.keys(REFS).filter((k) => !order.includes(k));
if (unused.length) console.log("note: unused refs", unused);

// ================================================================== FRONT MATTER
const TITLE = "Language-Commanded Indoor Drone for Object Search and Approach: A Simulation-First Study with Vision-Language Models";
const cline = (t, o = {}) => new Paragraph({ children: runs(t, { size: o.size || 24, bold: o.bold, font: FONT }), alignment: AlignmentType.CENTER, spacing: { after: o.after ?? 120, line: 276 } });
const students = (y) => [1, 2, 3].map((i) => new Paragraph({ children: [new TextRun({ text: `Student Name${i}`, highlight: "yellow", size: 24 }), new TextRun({ text: "\t" }), new TextRun({ text: "App ID", highlight: "yellow", size: 24 })], tabStops: [{ type: TabStopType.LEFT, position: 3600 }, { type: TabStopType.LEFT, position: 6000 }], indent: { left: 2600 }, spacing: { after: 60 } }));
const titlePage = [
  cline("uGDX School of Technology", { size: 32, bold: true, after: 600 }),
  cline("Project Report on", { size: 26, after: 240 }),
  cline(`"${TITLE}"`, { size: 30, bold: true, after: 480 }),
  cline("Submitted in partial fulfillment of the requirements"),
  cline("for the course", { after: 360 }),
  cline("Course: Design Project Minor (CPT 401)"),
  cline("Class: Final Year B. Tech (Semester VII)", { after: 480 }),
  cline("By", { after: 240 }),
  ...students(),
  cline("", { after: 360 }),
  cline("Supervisor:"),
  new Paragraph({ children: [new TextRun({ text: "Name of the Guide", highlight: "yellow", size: 24 })], alignment: AlignmentType.CENTER }),
  new Paragraph({ children: [new TextRun({ text: "(Affiliation)", highlight: "yellow", size: 24 })], alignment: AlignmentType.CENTER, spacing: { after: 600 } }),
  cline("AY: 2026-2027", { bold: true }),
];
const certPage = [
  new Paragraph({ children: [new PageBreak()] }),
  cline("uGDX School of Technology", { size: 32, bold: true, after: 480 }),
  cline("CERTIFICATE", { size: 32, bold: true, after: 480 }),
  new Paragraph({ children: [new TextRun({ text: `This is to certify that the project entitled "${TITLE}" is a bonafide work of`, size: 24 })], alignment: AlignmentType.JUSTIFIED, spacing: { after: 240, line: 360 } }),
  ...students(),
  new Paragraph({ children: [new TextRun({ text: `submitted in partial fulfilment of the requirement for the course "Design Project Minor" of Final Year of Bachelor degree in Technology (CS, AI & ML) during academic year 2026-27.`, size: 24 })], alignment: AlignmentType.JUSTIFIED, spacing: { before: 240, after: 1600, line: 360 } }),
  new Paragraph({ children: [new TextRun({ text: "Supervisor/Guide", size: 24 }), new TextRun({ text: "\tExaminer", size: 24 })], tabStops: [{ type: TabStopType.RIGHT, position: CONTENT_W }] }),
  new Paragraph({ children: [new TextRun({ text: "(Name of the Guide)", highlight: "yellow", size: 24 })] }),
];
const ack = [
  FH("Acknowledgement"),
  P(`We express our sincere gratitude to our guide, [[Name of the Guide]], for continuous guidance and feedback throughout this project. We thank the faculty of uGDX School of Technology for providing the opportunity and resources for the Design Project Minor course, and our peers for their suggestions. We also acknowledge the open-source communities behind PyBullet, MuJoCo, PyTorch, Ultralytics and Hugging Face, whose tools made this work possible.`),
];
const abstract = [
  FH("Abstract"),
  P(`This project investigates how a small indoor drone can accept a natural-language command such as "find and approach the orange" and then search for, localise and approach the named object while avoiding obstacles, without a prebuilt map, and stop safely when uncertain or disconnected. Vision-language-action (VLA) models such as SmolVLA and X-VLA are trained on robot-arm data and output arm actions, so we do not let a VLA control the drone directly. Instead we designed a modular architecture: a command parser, open-vocabulary perception, a target tracker, a classical search-and-approach planner and an independent, learning-free safety filter, with fail-safes on the flight controller. Seven configurations were compared under identical conditions: an oracle upper bound, colour thresholding, YOLO-World, OWLv2, a small vision-language model (SmolVLM) used directly as the pilot, a proposed hybrid in which a low-threshold detector proposes candidates and the VLM verifies them, and an ablation of the hybrid without verification. Ten scenarios (hidden targets, clutter, distractors, absent target, lighting, sensor noise, link loss and paraphrased commands) were run in two simulators with different dynamics and renderers (PyBullet and MuJoCo), ${N.episodes_total} episodes in total. With perfect perception the system succeeded in every scenario without collisions. The hybrid achieved ${OV.C5.nav_succ.toFixed(0)} % navigation success at ${OV.C5.lat_med.toFixed(0)} ms per frame, versus ${OV.C3.nav_succ.toFixed(0)} % for OWLv2 and ${OV.C2.nav_succ.toFixed(0)} % for YOLO-World alone; removing verification lowered success to ${OV.C6.nav_succ.toFixed(0)} % and more than doubled the wrong-target rate. The VLM used as the pilot failed in every navigation run (${OV.C4.nav_succ.toFixed(0)} %). A sensor ablation showed that denser range sensing raised minimum obstacle clearance from about 2 cm to 12 cm. The report closes with a custom-drone design and a staged plan through DJI Neo 2 shadow-mode tests, PX4 software-in-the-loop and supervised real flights.`),
  P(`**Keywords:** indoor drone, natural-language commands, vision-language models, open-vocabulary detection, safety filter, simulation.`),
];
const toc = [FH("Table of Contents"), new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1-3" })];
const lofLot = [
  FH("List of Figures"), new TableOfContents("List of Figures", { hyperlink: true, stylesWithLevels: [new StyleLevel("Figure Caption", 1)] }),
  new Paragraph({ children: [new TextRun({ text: "List of Tables", bold: true, size: 32 })], alignment: AlignmentType.CENTER, spacing: { before: 480, after: 240 } }),
  new TableOfContents("List of Tables", { hyperlink: true, stylesWithLevels: [new StyleLevel("Table Caption", 1)] }),
];
const abbr = [
  ["AUW", "All-up weight"], ["CI", "Confidence interval"], ["DFD", "Data flow diagram"], ["DOF", "Degrees of freedom"],
  ["ESC", "Electronic speed controller"], ["FC", "Flight controller"], ["FOV", "Field of view"], ["GPU", "Graphics processing unit"],
  ["HSV", "Hue–saturation–value colour space"], ["LLM", "Large language model"], ["MAVLink", "Micro Air Vehicle Link protocol"],
  ["NL", "Natural language"], ["PX4", "Open-source autopilot flight stack"], ["RC", "Radio control"], ["SITL", "Software-in-the-loop"],
  ["SPL", "Success weighted by path length"], ["ToF", "Time of flight (range sensor)"], ["VIO", "Visual-inertial odometry"],
  ["VLA", "Vision-language-action model"], ["VLM", "Vision-language model"],
];
const notation = [
  ["d*", "Stand-off distance (0.5 m)"], ["d_final", "Final 3-D distance from drone to target centre (m)"],
  ["p, e", "Target position, camera position in world frame (m)"], ["f, r, u", "Camera forward, right and up unit vectors"],
  ["f_x, f_y, c_x, c_y", "Camera focal lengths and principal point (px)"], ["z_s, z_c", "Depth to object surface, to object centre (m)"],
  ["v, ψ̇", "Commanded velocity (m/s), yaw rate (rad/s)"], ["d̂, r", "Obstacle ray direction (unit vector), range (m)"],
  ["τ_v", "Velocity-loop time constant (s)"], ["S_i, l_i, p_i", "Success flag, shortest path length, travelled path length of episode i"],
];
const mkAbbr = (title, rows, h) => {
  const save = chapter; chapter = 0;
  const t = table(title, h, rows, [25, 75]);
  chapter = save;
  return t.nodes.slice(1); // no numbered caption in front matter
};
const front = [...ack, ...abstract, ...toc, ...lofLot,
  FH("Abbreviations"), ...mkAbbr("Abbreviations", abbr, ["Abbreviation", "Meaning"]),
  FH("Notation and Nomenclature"), ...mkAbbr("Notation", notation, ["Symbol", "Meaning"])];

// ======================================================================= DOCUMENT
const pageNumFooter = () => new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 22 })] })] });
const page = { size: { width: 11906, height: 16838 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } };
const doc = new Document({
  creator: "Project team",
  title: TITLE,
  features: { updateFields: true },
  styles: {
    default: { document: { run: { font: FONT, size: 24 }, paragraph: { spacing: { line: 360 } } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: 32, bold: true, color: "000000" }, paragraph: { spacing: { before: 0, after: 240 }, keepNext: true, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: 28, bold: true, color: "000000" }, paragraph: { spacing: { before: 240, after: 120 }, keepNext: true, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: 24, bold: true, color: "000000" }, paragraph: { spacing: { before: 180, after: 100 }, keepNext: true, outlineLevel: 2 } },
      { id: "FigCaption", name: "Figure Caption", basedOn: "Normal", next: "Normal", run: { font: FONT, size: 22, bold: false }, paragraph: { alignment: AlignmentType.CENTER, spacing: { before: 0, after: 240, line: 276 } } },
      { id: "TabCaption", name: "Table Caption", basedOn: "Normal", next: "Normal", run: { font: FONT, size: 22 }, paragraph: { alignment: AlignmentType.CENTER, spacing: { before: 120, after: 80, line: 276 }, keepNext: true } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 300 } } } }] },
      { reference: "objectives", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 300 } } } }] },
    ],
  },
  sections: [
    { properties: { page }, children: [...titlePage, ...certPage] },
    { properties: { page: { ...page, pageNumbers: { start: 1, formatType: NumberFormat.LOWER_ROMAN } } }, footers: { default: pageNumFooter() }, children: front },
    { properties: { page: { ...page, pageNumbers: { start: 1, formatType: NumberFormat.DECIMAL } } }, footers: { default: pageNumFooter() }, children: [...body, ...refNodes] },
  ],
});
const out = path.join(DIR, "Project_Report.docx");
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(out, buf); console.log("wrote", out, "refs:", order.length, "figs:", JSON.stringify(figCount), "tables:", JSON.stringify(tabCount)); });
