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
  crossformer: `R. Doshi, H. Walke, O. Mees, S. Dasari, and S. Levine, "Scaling cross-embodied learning: One policy for manipulation, navigation, locomotion and aviation," in Proc. Conf. Robot Learning (CoRL), 2024.`,
  hpt: `L. Wang, X. Chen, J. Zhao, and K. He, "Scaling proprioceptive-visual learning with heterogeneous pre-trained transformers," in Proc. Advances in Neural Information Processing Systems (NeurIPS), 2024.`,
  navfom: `Zhang et al., "Embodied navigation foundation model," in Proc. Int. Conf. Learning Representations (ICLR), 2026, arXiv:2509.12129.`,
  remembr: `A. Anwar, J. Welsh, J. Biswas, S. Pouya, and Y. Chang, "ReMEmbR: Building and reasoning over long-horizon spatio-temporal memory for robot navigation," arXiv:2409.13682, 2024.`,
  hovsg: `A. Werby et al., "Hierarchical open-vocabulary 3D scene graphs for language-grounded robot navigation," in Proc. Robotics: Science and Systems (RSS), 2024.`,
  sayplan: `K. Rana et al., "SayPlan: Grounding large language models using 3D scene graphs for scalable robot task planning," in Proc. Conf. Robot Learning (CoRL), 2023.`,
  threedmem: `Y. Yang et al., "3D-Mem: 3D scene memory for embodied exploration and reasoning," in Proc. IEEE/CVF Conf. Computer Vision and Pattern Recognition (CVPR), 2025, pp. 17294–17303.`,
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

// ---- Phase 1b-2 numbers (from world_figs.py)
const W = JSON.parse(fs.readFileSync(path.join(DIR, "numbers_world.json"), "utf8").replace(/\bNaN\b/g, "null"));
const HP = (t, p) => (W.helipad || []).find((r) => r.task === t && r.perception === p) || {};
const XE = (t, e, p) => (W.xemb || []).find((r) => r.task === t && r.embodiment === e && r.perception === p) || {};
const AR = (t, p) => (W.arm || []).find((r) => r.task === t && r.perception === p) || {};
const ME = (t, e, m) => (W.memory || []).find((r) => r.task === t && r.embodiment === e && r.memory === m) || {};
const PADNAMES = { oracle: "Oracle", ring: "Ring detector (colour)", v1: "VLM verifier v1 (oblique)", v3: "VLM verifier v3 (top-down, rot.-inv.)" };
const hpAll = (pn) => {
  const rs = (W.helipad || []).filter((r) => r.perception === PADNAMES[pn]);
  const n = rs.reduce((a, r) => a + r.n, 0);
  const k = rs.reduce((a, r) => a + (r.success * r.n) / 100, 0);
  const dec = rs.reduce((a, r) => a + r.decoy_landings, 0);
  const ks = rs.reduce((a, r) => a + (r.strict * r.n) / 100, 0);
  const rs3 = rs.filter((r) => r.task !== "L4");
  const n3 = rs3.reduce((a, r) => a + r.n, 0);
  const ks3 = rs3.reduce((a, r) => a + (r.strict * r.n) / 100, 0);
  const coll = rs.reduce((a, r) => a + r.collisions, 0);
  return { n, succ: n ? (100 * k) / n : null, strict: n ? (100 * ks) / n : null, strict3: n3 ? (100 * ks3) / n3 : null, dec, coll };
};
const xeAll = (e, p) => {
  const rs = ["O1", "O2", "O3"].map((t) => XE(t, e, p)).filter((r) => r.n);
  const n = rs.reduce((a, r) => a + r.n, 0);
  return n ? rs.reduce((a, r) => a + r.success * r.n, 0) / n : null;
};
const v = (x, d = 0) => (x === null || x === undefined || Number.isNaN(x) ? "–" : Number(x).toFixed(d));
const red_abs = (e) => { const a = ME("M2", e, "none").time_mean, b = ME("M2", e, "persistent").time_mean; return a && b ? (100 * (a - b)) / a : null; };


// --------------------------------------------------------------- Chapter 1 (rewritten)
chapter = 1;
add(H1("1. Introduction"));
add(P(`Robots that can be told what to do in plain language — *"find the orange"*, *"land on the nearest helipad"*, *"find the apple, then the lemon"*, *"pick up the orange"* — would make inspection, search, assistive and logistics tasks accessible to non-experts. Recent vision-language models (VLMs) and vision-language-action models (VLAs) make the *understanding* part increasingly available, but deploying them on **affordable, off-the-shelf robots** remains difficult: the models are large, they were trained for specific robot bodies, they do not remember the environment beyond their context window, and they offer no safety guarantees. This report presents the first phases of a project that addresses this deployment problem, evaluated systematically in simulation on three robot types.`));

add(H2("1.1 Problem Definition"));
add(H3("1.1.1 The Overall Problem"));
add(new Paragraph({
  children: runs(`**Overall problem statement.** How can a pretrained vision-language(-action) agent turn a natural-language instruction into safe and successful action on affordable, off-the-shelf robots — drones, ground vehicles and robot arms — without expensive onboard computing, without a prebuilt map and without extensive robot-specific training, while remembering what it has observed so that it can complete multi-step missions in environments it has never seen before?`),
  alignment: AlignmentType.JUSTIFIED, spacing: { before: 120, after: 160 },
  border: { top: { style: BorderStyle.SINGLE, size: 6, color: "2C4F7C", space: 6 }, bottom: { style: BorderStyle.SINGLE, size: 6, color: "2C4F7C", space: 6 },
            left: { style: BorderStyle.SINGLE, size: 6, color: "2C4F7C", space: 8 }, right: { style: BorderStyle.SINGLE, size: 6, color: "2C4F7C", space: 8 } },
  shading: { type: ShadingType.CLEAR, fill: "EEF3FB", color: "auto" },
}));
add(P(`This problem is not solved by any single existing model. Our analysis of the literature (Chapter 2) identifies five gaps that together make it hard:`));
const tGaps = table("Gaps that make language-guided deployment on affordable robots hard", ["Gap", "Why it matters", "What is needed", "Addressed in this report"], [
  ["G1 No persistent spatial-semantic memory", "Policies act on the current view; objects seen earlier are forgotten, so areas are re-explored", "A persistent map of objects, rooms and explored areas", "Initial study (object memory + explored rooms, Exp. 7)"],
  ["G2 Limited long-horizon missions", "Reaching one goal is not the same as completing a multi-stage mission", "Decomposing instructions into subtasks and tracking progress", "Sequential subtasks (Exp. 7); LLM planner in Phase 3"],
  ["G3 Generalisation to unseen environments", "Layouts, objects and lighting differ from training", "Zero-shot pretrained perception", "Randomised unseen layouts, lighting, distractors (all experiments)"],
  ["G4 Embodiment dependency", "A policy for one robot cannot command another (an arm VLA cannot fly)", "A shared intelligence layer + thin robot-specific adapters", "Drone, ground robot and arm share one layer (Exp. 5, 6)"],
  ["G5 Robot-specific training data", "Training a VLA per robot is expensive", "Reuse pretrained knowledge, minimise per-robot data", "Zero robot-specific training used; learned adapters in Phase 5"],
], [21, 29, 24, 26]);
add(tGaps);
add(H3("1.1.2 Problem Addressed in This Report (Phases 0–2)"));
add(P(`The overall problem is too large for one semester, so it was divided into phases (Section 3.1). This report addresses the first, bounded and measurable part:`));
add(new Paragraph({
  children: runs(`**Phase-1/2 problem statement.** In previously unseen simulated indoor environments, can a laptop-hosted modular pipeline built only from pretrained models — with zero robot-specific training — (a) locate and approach a named object to a 0.5 m stand-off, (b) find and land on the nearest correct helipad among decoys, and (c) complete multi-object missions, while safety never depends on the AI components; and to what extent do (d) persistent semantic memory and (e) thin embodiment adapters allow the same intelligence layer to serve a drone, a ground robot and a robot arm?`),
  alignment: AlignmentType.JUSTIFIED, spacing: { before: 120, after: 160 },
  border: { left: { style: BorderStyle.SINGLE, size: 18, color: "D55E00", space: 8 } },
  shading: { type: ShadingType.CLEAR, fill: "FDF1EA", color: "auto" },
}));
const tRQ = table("Research questions and where they are answered", ["RQ", "Question", "Evidence in this report"], [
  ["RQ1", "Which perception design lets a drone find the right object reliably and quickly on a laptop?", "Exp. 1–3 (7 configurations, 2 simulators, ~1,400 episodes)"],
  ["RQ2", "Does persistent memory reduce mission time and repeated exploration compared with a memoryless baseline?", "Exp. 7 (memory none / per-mission / persistent)"],
  ["RQ3", "Can one high-level layer be transferred between a drone, a ground robot and an arm through thin adapters?", "Exp. 5 (drone vs ground), Exp. 6 (arm)"],
  ["RQ4", "How much robot-specific data does embodiment adaptation need?", "Partial: hand-written adapters needed zero data; learned adapters are Phase 5"],
  ["RQ5", "Does the approach generalise to unseen layouts, lighting and distractors?", "All experiments use randomised, unseen layouts; real unseen buildings in Phase 4"],
  ["RQ6", "Which simulator is closest to the physical world, and on which axis?", "Exp. 2 (PyBullet vs MuJoCo), pre-registered hypotheses H1–H5"],
], [8, 52, 40]);
add(tRQ);

add(H2("1.2 Aims and Objectives"));
add(P("The aim is to establish, in simulation, a safe and modular language-to-action architecture for affordable robots and to measure what each component contributes. Objectives:"));
add(NUM([
  "**O1** — Parse a natural-language command into a mission of subtasks, asking for clarification when ambiguous.",
  "**O2** — Detect and localise the requested object or landing pad with pretrained, zero-shot perception.",
  "**O3** — Search an area or a multi-room building when the target is not visible.",
  "**O4** — Approach to a 0.5 m stand-off, or land within 0.2 m of the correct helipad, and report.",
  "**O5** — Keep safety (obstacle clearance, geofence, link-loss fail-safe) independent of all AI components.",
  "**O6** — Maintain a persistent semantic memory of objects and explored rooms and use it across subtasks and missions.",
  "**O7** — Run the same intelligence layer on a drone, a ground robot and a robot arm through thin embodiment adapters.",
  "**O8** — Compare alternatives under identical, pre-defined scenarios and metrics, across two simulators.",
], "objectives"));

add(H2("1.3 Scope of the Project"));
add(table("Scope of this report", ["In scope (Phases 0–2, simulation)", "Out of scope (Phases 3–5)"], [
  ["Three embodiments in simulation: drone, wheeled ground robot (Husky), arm (Franka Panda)", "Building and flying real robots (Phase 4)"],
  ["Tasks: object search & approach; find nearest helipad & land; multi-object missions; pick-up", "Mobile manipulation, moving targets, outdoor flight"],
  ["Persistent object memory + explored-room memory; known room connectivity (floor plan)", "Full 3-D scene graph, LLM task planner, replanning under environment change (Phase 3)"],
  ["Zero-shot models (YOLO-World, OWLv2, SmolVLM); hand-written embodiment adapters", "Fine-tuning a VLA, learned adapters, data-efficiency study (Phase 5)"],
  ["Two simulators (PyBullet, MuJoCo) on a Windows laptop with an 8 GB GPU", "PX4 software-in-the-loop, Isaac Sim / Habitat photorealistic scenes"],
  ["DJI Neo 2 shadow-mode software (ready); custom-drone design and parts list", "Closed-loop control of the Neo 2 (no SDK support found)"],
], [55, 45]));

add(H2("1.4 Existing System"));
add(P(`Table ${chapter}.${(tabCount[chapter] || 0) + 1} summarises the closest existing systems. Consumer drones such as the DJI Neo 2 offer gesture/voice control, subject tracking and obstacle sensing {neo2} but cannot accept open-ended goals or be programmed. Research systems address individual gaps — memory {remembr,hovsg}, mission planning {sayplan}, cross-embodiment policies {crossformer,hpt,navfom} or drone VLAs {cogdrone,uavvla} — typically with large models, large datasets or expensive hardware.`));
add(table("Comparison of existing systems", ["System", "What it does", "Gap relative to this project"], [
  [`DJI Neo 2 {neo2}`, "Consumer palm-size drone; tracking, gestures/voice, LiDAR + vision sensing", "No language goals; no programmable control found"],
  [`CognitiveDrone {cogdrone}`, "7 B VLA outputs 4-D velocity; >8k simulated trajectories", "Large model; end-to-end control; gate tasks only"],
  [`UAV-VLA {uavvla}`, "VLM/LLM generate outdoor mission plans from satellite images", "Planning only; outdoor GPS missions"],
  [`NaVILA {navila}`, "VLA emits mid-level language actions; RL policy executes on a legged robot", "Single embodiment; two-level idea adopted here"],
  [`CrossFormer {crossformer}`, "One policy for arms, wheeled robots, quadrupeds and a Tello drone", "Trained on 900k trajectories; no persistent memory"],
  [`ReMEmbR {remembr}`, "Long-horizon spatio-temporal memory for robot navigation (VLM captions + retrieval)", "Single robot; question answering focus"],
  [`SayPlan {sayplan}`, "LLM plans over a 3-D scene graph with replanning", "Assumes a pre-built scene graph; mobile manipulator only"],
], [20, 45, 35]));

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
// --------------------------------------------------------------- Chapter 2 additions
add(H2("2.8 Persistent Spatial-Semantic Memory and Long-Horizon Planning"));
add(P(`Several works give robots a memory beyond the model's context window. ReMEmbR {remembr} captions robot video with a VLM, stores captions with time and position in a vector database and answers spatial and temporal questions with an LLM agent. HOV-SG {hovsg} builds a hierarchical open-vocabulary 3-D scene graph (floor → room → object) for language-grounded navigation, and 3D-Mem {threedmem} keeps "memory snapshots" of informative views plus "frontier snapshots" for exploration. For long-horizon missions, SayPlan {sayplan} lets an LLM search a 3-D scene graph, plan, and replan when a step fails — the same idea as the "door closed → replan" example in our proposal. **Implication for this project:** memory and mission planning are established research directions; our contribution is not a new memory representation but a *controlled measurement* of what a simple persistent object-and-room memory buys on affordable robots, as a baseline for the richer scene graph planned in Phase 3.`));
add(H2("2.9 Cross-Embodiment Policies and Adapters"));
add(P(`CrossFormer {crossformer} trains one transformer policy on 900k trajectories from 20 embodiments (arms, wheeled robots, quadrupeds) and controls a quadcopter it was never trained on. Heterogeneous Pre-trained Transformers (HPT) {hpt} use embodiment-specific *stems* (input tokenisers) and *heads* (action decoders) around a shared trunk, so a new robot needs only small new parts — the "lightweight adapter" idea in its learned form. NavFoM {navfom} trains one navigation model on about eight million samples across drones, quadrupeds, wheeled robots and cars. These systems show that sharing intelligence across bodies works, but they rely on very large datasets and GPUs. **Implication:** we test the low-cost end of this spectrum — a shared, modular intelligence layer with *hand-written* adapters and zero robot-specific training — which also provides the baseline that learned adapters (Phase 5) must beat.`));
add(H2("2.10 Positioning and Novelty"));
const tNov = table("What is established and what this project contributes", ["Component", "Status in the literature", "This project"], [
  ["Using an LLM/VLM for robot instructions", "Established {openvla,pi0,smolvla}", "Used as components, not claimed as new"],
  ["Open-vocabulary detection + VLM verification", "Established parts {owlv2,yoloworld,smolvlm}", "Measured on drone, ground robot and arm; active top-down verification for landing"],
  ["Persistent spatial-semantic memory", "Active research {remembr,hovsg,threedmem}", "Simple object + room memory measured against no-memory baselines"],
  ["Cross-embodiment transfer", "Active research, data-hungry {crossformer,hpt,navfom}", "Zero-data, hand-written adapters on three robots as a low-cost baseline"],
  ["Safety independent of the AI", "Standard in robotics practice {px4}", "Kept constant across all configurations; quantified by ablation"],
  ["Combination on affordable hardware with controlled comparisons", "Less studied", "Main contribution: an affordable reference architecture + systematic simulation evidence"],
], [28, 32, 40]);
add(P(`${tNov.label} positions the work honestly. The individual ideas exist; what this project contributes is an affordable, modular reference architecture and a set of controlled experiments that quantify each component's contribution on three robot types under identical conditions.`));
add(tNov);

add(H2("2.11 Research Gap"));
add(P(`The literature shows that (i) VLAs need action-space adaptation and large flight datasets before they can control a drone, (ii) open-vocabulary detectors and small VLMs offer semantics but uncertain precision, (iii) memory and cross-embodiment transfer are active research areas whose strongest results rely on large datasets and GPUs, and (iv) little work quantifies, under identical scenarios, how much each component contributes on affordable robots, or how results differ between simulators. This project addresses that gap with a modular, laptop-hosted architecture, an independent safety layer, controlled comparisons across seven perception configurations, three robots, four task types and two simulators, and an explicit phase plan towards learned adapters and real hardware.`));

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
add(P(`Development was iterative: each version was measured, and changes were made only in response to a measured failure. ${tIt.label} lists the most important iterations; the full problem log is in Section 3.7.16.`));
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

add(H2("3.2 Analysis"));
add(H3("3.2.1 Requirements"));
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
add(H3("3.2.2 Use-Case Diagram"));
const fUC = fig("fig_usecase.png", 5.6, "Use-case diagram of the language-commanded drone system");
add(P(`${fUC.label} shows three actors. The **operator** issues commands, answers clarification questions and monitors the camera and status. The **safety pilot** holds an independent RC link and can abort or take over at any time. The **drone** (flight controller and sensors) executes search and approach.`));
add(fUC);
add(H3("3.2.3 Data Flow Diagram"));
const fDFD = fig("fig_dfd.png", 6.3, "Data flow diagram — level 0 (context) and level 1 (processes)");
add(P(`At level 0 (${fDFD.label}) the navigation system exchanges commands and reports with the operator, and setpoints and sensor data with the drone. Level 1 decomposes it into five processes — parse, perceive, track & map, plan and safety filter — and one data store, the episode log, from which every metric in Section 3.7 is computed.`));
add(fDFD);
add(H3("3.2.4 Data Dictionary"));
add(table("Data dictionary of the main messages", ["Data item", "Fields (type, unit)", "Producer → consumer"], [
  ["Mission", "intent (find_approach | abort), target (string), standoff_m (float, m, clamped 0.4–2.0), max_speed (m/s), clarify (string | null)", "Parser → state machine"],
  ["Detection", "label, conf (0–1), pos (x, y, z world, m), bbox (px), dist (m)", "Perception → belief"],
  ["Target belief", "pos (m), hits (int), last_seen (s), conf", "Belief → planner"],
  ["Obstacle ray", "unit direction (world), range (m); from ToF ring and depth sectors", "Sensors → planner, safety filter"],
  ["Setpoint", "vx, vy, vz (m/s, world), yaw_rate (rad/s) at 20 Hz", "Safety filter → flight controller"],
  ["Episode record", "scenario, seed, config, success, final_dist, SPL, collisions, min_clearance, latency, state log", "Runner → analysis"],
], [18, 57, 25]));

add(H2("3.3 Design"));
add(H3("3.3.1 Layered Architecture"));
const fLay = fig("fig_layered.png", 6.4, "Layered architecture: one shared intelligence layer, an independent safety filter and thin adapters for three robots");
add(P(`${fLay.label} shows the architecture that resulted from Phases 1–2. Everything above the dashed line — mission parsing, perception, persistent memory, planning and the safety filter — is identical code for every robot and runs on the laptop. The only robot-specific parts are the adapters, which translate a common command (a world-frame velocity setpoint or a 3-D target point) into what each body can execute. Section 3.3.2 details the Phase-1 drone instance of this architecture.`));
add(fLay);
add(H3("3.3.2 System Architecture"));
const fBD = fig("fig_block_diagram.png", 6.3, "System block diagram — laptop processing chain and drone");
add(P(`${fBD.label} shows the architecture. The laptop runs six blocks: [1] command parser, [2] mission state machine, [3] perception, [4] target belief and local world model, [5] planner and [6] safety filter. The drone carries only the flight controller, sensors and an independent RC receiver. Three design decisions follow from Chapter 2:`));
add(B([
  "**Modular rather than end-to-end.** The VLM/VLA is a swappable component (block 3 or a policy replacing block 5), never the controller. This allows a fair comparison and keeps metric control dependable.",
  "**Independent safety filter.** Block 6 uses *raw* range and depth data only, has no learned parts, and has the final say on every command. The planner may ignore the tracked target in its own obstacle map (it has to approach it); the safety filter never does.",
  "**Fail-safe on the drone, not the laptop.** If setpoints stop arriving, the flight controller hovers after 0.5 s and lands after 3 s, regardless of what the laptop is doing.",
]));
add(fBD);
add(H3("3.3.3 Mission Logic (Flowchart)"));
const fFC = fig("fig_flowchart.png", 5.4, "Flowchart of the mission state machine");
add(P(`The mission is a finite-state machine (${fFC.label}). After take-off the drone spins 360° (SEARCH_SPIN); if the target is not confirmed it flies to the next search waypoint (SEARCH_MOVE) and spins again. A target is *confirmed* after three consistent detections. APPROACH computes a goal point at the stand-off distance on the line to the target, descends to 0.15 m above the target so it stays in the camera view, and faces it. HOLD requires the distance error to be within 0.1 m and speed below 0.12 m/s for 1.5 s before reporting FOUND. If the target is not seen for 4 s the drone returns to search; when all waypoints are exhausted or the time budget (120 s) expires it reports NOT_FOUND.`));
add(fFC);
add(H3("3.3.4 Operator Interface (GUI)"));
const fGUI = fig("shot_demo.png", 6.2, "Operator view: drone camera with detections and status (left), live map with trajectory and target estimate (right)");
add(P(`The operator interface (${fGUI.label}) shows the drone camera with detections and estimated distance, the parsed command, mission and flight-controller state, and a top-down map with the trajectory and current target estimate. The same view is used for the recorded demo videos. An interactive mode (*fly.py*) adds keyboard flight, hand-over to autonomous mode, safety-pilot take-over, link-loss simulation and a safety-filter on/off switch for demonstrations.`));
add(fGUI);
add(H3("3.3.5 Custom Drone Design Considerations"));
add(P(`The custom drone is designed for the same architecture. Key considerations: (i) **safety-first size** — a 3.5-inch ducted frame whose ducts act as prop guards, all-up weight ≤ 400 g; (ii) **open flight stack** — PX4 for offboard setpoints and a built-in fail-safe; (iii) **GPS-free positioning** — downward optical flow plus a ToF height sensor; (iv) **obstacle sensing coverage** — the sensor ablation in Section 3.7.6 shows that a sparse 8-beam ring allows near-misses with thin obstacles, so multi-zone ToF sensors are specified; (v) **compute split** — heavy AI on the laptop, a small companion computer only streams video and bridges MAVLink; (vi) **independent RC link** for the safety pilot; (vii) **latency budget** — camera→laptop ≤ 150 ms, inference ≤ 150 ms; at 0.3–0.5 m/s the drone moves at most ~15 cm per decision cycle; (viii) thrust-to-weight ≥ 2 : 1 and flight time ≥ 6 min. The proposed components are listed in Section 3.6.1.`));


// --------------------------------------------------------------- 3.4 Simulation environment and compatibility
add(H2("3.4 Simulation Environment and Compatibility"));
add(H3("3.4.1 Simulator Selection"));
add(P(`Seven simulators were assessed against the project's constraints. The decisive factors were: runs natively on the available Windows laptop with an 8 GB GPU, supports all three robot types, allows hundreds of fast repeatable episodes, and can be scripted from Python. PyBullet satisfied all of them and was chosen as the primary simulator; MuJoCo was added as an independent cross-check with different dynamics and rendering. Simulators with real flight firmware (PX4 + Gazebo) or photorealistic scanned buildings (Habitat, Isaac Sim) are planned for later phases.`));
add(table("Simulator compatibility with the project constraints and robot types", ["Simulator", "Windows / 8 GB GPU", "Drone", "Ground robot", "Arm", "Real firmware", "Visual realism", "Used"], [
  ["PyBullet", "Yes / Yes", "Yes (custom model)", "Yes (Husky)", "Yes (Panda, KUKA)", "No", "Low", "Primary"],
  ["MuJoCo", "Yes / Yes", "Yes (6-DOF)", "Possible", "Yes", "No", "Medium", "Cross-check"],
  ["Gazebo + PX4 SITL", "WSL2 / Yes", "Yes", "Yes", "Yes", "Yes (PX4)", "Medium", "Phase 4"],
  ["Webots", "Yes / Yes", "Yes (Mavic model)", "Yes", "Yes", "Partial", "Medium", "Not used (time)"],
  ["Isaac Sim (+ Pegasus)", "Yes / at minimum spec", "Yes (Linux add-on)", "Yes", "Yes", "Via PX4", "High", "Future"],
  ["Habitat", "Linux only", "No", "Yes", "Limited", "No", "High (scans)", "Future (memory)"],
  ["AirSim / Colosseum", "Yes / heavy", "Yes", "Car", "No", "Via PX4", "High", "No (archived)"],
], [17, 14, 13, 12, 12, 11, 10, 11], { center: true }));
add(H3("3.4.2 Robots Imported into the Simulation"));
const fRW = fig("shot_robots_world.png", 6.3, "Robots and environments in the simulator: quadrotor model, drone in the test room, Husky ground robot, multi-room house, helipad scene, Franka Panda arm");
add(P(`${fRW.label} shows the three embodiments and environments. The drone is modelled as a 3.5-inch ducted quadrotor (body, arms, motors, ducted propellers, battery and front camera) attached to an invisible collision body; the ground robot uses the Clearpath Husky model scaled to 0.6 m with a camera mast; the arm is a Franka Emika Panda on a table with a fixed RGB-D camera. All models and scenes are loaded from the PyBullet distribution {pybullet} or generated procedurally from seeded scenario descriptions.`));
add(fRW);
add(table("Embodiments and their sensors and adapters", ["", "Drone", "Ground robot", "Arm"], [
  ["Body", "0.24 × 0.24 m, 0.35 kg, ducted", "0.6 × 0.4 m (Husky model, scaled)", "7-DOF Franka Panda + gripper"],
  ["Camera", "320 × 240, 60° v-FOV, gimbal −15° (−35° search, −90° landing)", "Same, on a 0.6 m mast, −12°", "Same, fixed 1.3 m above table, −58°"],
  ["Range sensing", "24-beam ToF ring + up/down", "24-beam ToF ring at body height", "–"],
  ["Command interface", "World velocity (vx, vy, vz, ψ̇)", "Same", "3-D target point"],
  ["Embodiment adapter", "Velocity loop, attitude lag, FC fail-safe", "Unicycle: (vx, vy, ψ̇) → (v, ω)", "Inverse kinematics → joint targets"],
  ["Robot-specific training data", "None", "None", "None"],
], [22, 28, 25, 25]));
add(H3("3.4.3 Sensor Data"));
const fSD = fig("shot_sensors_drone.png", 6.4, "Drone sensor data in one frame: RGB with detections, depth, segmentation (evaluation only) and the range ring with depth sectors");
const fSG = fig("shot_sensors_ground.png", 6.4, "The same sensor set on the ground robot (mast camera, ring at body height)");
add(P(`${fSD.label} and ${fSG.label} show what each robot perceives at one instant: the RGB image with detections and estimated distances, the metric depth image used for 3-D localisation and obstacle sectors, the segmentation image (used only by the evaluator and the oracle configuration), and the horizontal range beams plus depth sectors used by the planner and the safety filter.`));
add(fSD, fSG);
add(H3("3.4.4 Scenarios per Robot"));
add(table("Scenario families, robots and experiments", ["Family", "Scenarios", "Robots", "Seeds × configs"], [
  ["T (Phase 1)", "T1 visible · T2 behind · T3 hidden · T4 clutter · T5 distractors · T6 absent · T7 lighting · T8 noise · T9 link loss · T10 paraphrases · T4D dense ranging", "Drone (PyBullet, MuJoCo)", "10–20 × 7"],
  ["O", "O1 visible · O2 hidden behind wall · O3 among distractors", "Drone, ground robot", "10 × 3"],
  ["L", "L1 one helipad · L2 several (nearest) · L3 + decoy pads (X, plain) · L4 + dim light", "Drone", "10 × 4"],
  ["M", "M1 house, find 3 objects in sequence · M2 two consecutive 3-object missions", "Drone, ground robot", "10 × 2–3 memory modes"],
  ["A", "A1 orange alone · A2 + distractors · A3 + dim light", "Arm", "10 × 3"],
], [12, 50, 20, 18]));

add(H2("3.5 Implementation Methodology"));
add(H3("3.5.1 Command Parsing"));
add(P(`A deterministic rule-based parser converts the command into the mission JSON (data dictionary, Section 3.2.4): it detects the intent, the object noun (handling "orange" used as a colour, e.g. "orange ball"), an optional distance ("50 cm", "half a metre", clamped to 0.4–2.0 m for safety) and speed words ("slowly"). Multiple objects without a spatial relation, unknown objects and unknown intents produce a clarification question instead of a mission. An LLM-based parser with the same output schema can be substituted and scored on the same phrase set.`));
add(H3("3.5.2 Perception Configurations"));
add(P(`Seven configurations share the same parser, planner and safety filter; only perception/decision differs (table below). C0 is an upper bound; C6 is an ablation of our hybrid C5.`));
add(table("Perception and decision configurations compared", ["ID", "Perception / decision", "Purpose"], [
  ["C0", "Oracle: true target position whenever ≥ 4 target pixels are visible", "Upper bound; isolates planner and safety layer"],
  ["C1", "HSV colour threshold + depth", "Cheapest baseline"],
  ["C2", `YOLO-World {yoloworld,ultralytics} (prompt "orange fruit", confidence 0.02) + depth`, "Fast open-vocabulary detector"],
  ["C3", `OWLv2 {owlv2,transformers} (threshold 0.1) + depth`, "Slower, more accurate detector"],
  ["C4", `SmolVLM-500M {smolvlm} as *policy*: chooses left / right / center (forward) / close (stop) / none (explore) from the image`, "Zero-shot 'VLA-style' decision maker without fine-tuning"],
  ["C5", "**Hybrid (ours):** YOLO-World at very low threshold (0.002) proposes candidates → SmolVLM verifies each candidate crop once it is ≥ 12 px wide → depth fusion → classical planner", "Semantic precision from the VLM, metric control from the planner"],
  ["C6", "Ablation: C5's low-threshold detector *without* VLM verification", "Measures the VLM's contribution"],
], [7, 63, 30]));
add(H3("3.5.3 3-D Target Localisation"));
add(P("A detection's bounding-box centre (u, v) and the depth z read from the central half of the box (30th percentile, i.e. the object surface) are back-projected through the pinhole camera model using the camera position e and axes f (forward), r (right) and u (up), which include the drone's full attitude when the simulator models roll and pitch:"));
add(EQ("p = e + z·f + ((u − c_x)/f_x)·z·r − ((v − c_y)/f_y)·z·u", "3.1"));
add(P("Because depth measures the near surface, the estimate is moved to the object centre using the apparent radius:"));
add(EQ("z_c = z_s + ½ · w_px · z_s / f_x", "3.2"));
add(P(`This correction reduced the colour detector's position error from up to 8.5 cm to under 4 cm at 0.6–3 m. Detections are fused by a tracker (exponential smoothing with a 0.6 m gate); three hits confirm a target.`));
add(H3("3.5.4 Search, Approach and Local Avoidance"));
add(P(`Search waypoints are visited in nearest-neighbour order from the start. During motion the commanded velocity is a proportional pull to the goal (gain 0.8, ≤ 0.5 m/s; ≤ 0.2 m/s within 1.2 m of the target) plus a repulsive and tangential term from every obstacle ray closer than 0.8 m, in the spirit of {vfh}. If the drone makes less than 0.25 m progress in 6 s it commits to a 2.5 s sideways detour. Obstacle rays come from an 8-beam horizontal ToF ring and from 7 depth-image sectors (points within ±0.15 m of flight altitude).`));
add(H3("3.5.5 Safety Filter"));
add(P("For every obstacle ray with unit direction d̂ and range r, the filter removes or limits the velocity component towards it:"));
add(EQ("if r < 0.25 m:  v ← v − max(0, v·d̂)·d̂;   if r < 0.60 m:  v·d̂ ≤ v_max·(r − 0.25)/0.35", "3.3"));
add(P(`and pushes away at 0.15 m/s below 0.18 m. It also clamps speed (0.5 m/s horizontal, 0.3 m/s vertical) and yaw rate, enforces a geofence 0.4 m inside the walls and an altitude band (0.5–1.8 m, climb if the downward range is < 0.35 m). Every modification is counted as an *intervention*.`));
add(H3("3.5.6 VLM Policy (C4) and Hybrid Verification (C5)"));
add(P(`C4 sends the camera image with the prompt *"…Where is the orange in the image? Answer with exactly one word: left, right, center, close, or none"*. Answers are executed as motion primitives (yaw ±30°, forward 0.5 m, stop-and-report, or explore by rotating 45° and moving 1 m after a full turn), always through the safety filter.`));
add(P(`C5 uses *active verification*: far candidates (< 12 px) are passed on with low confidence so the planner approaches them; once a candidate is large enough, SmolVLM answers *"Is this an orange (the citrus fruit)? Answer yes or no."* for the crop. Rejected locations (0.3 m cells) are black-listed; a location is re-checked if later seen at ≥ 1.5× the size. The question wording and the 12 px threshold were chosen in a calibration test on 15 crops (Section 3.7.2), separate from the evaluation episodes.`));
add(H3("3.5.7 Simulators and Dynamics Models"));
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
add(H3("3.5.8 Experimental Protocol"));
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
add(P(`PyBullet: C0 and C1 were run with 20 seeds per scenario; GPU configurations C2, C3, C5, C6 with 10 seeds and C4 with 5 seeds (each C4 episode takes ~2 min of wall time). **All comparisons use the shared seeds 0–9** (0–4 for C4). MuJoCo: C0 and C1 with 20 seeds, C2 and C5 with 10 seeds on T1, T3, T5, T6, T9. In total ${N.episodes_total} episodes were logged (PyBullet ${N.episodes_by_sim.pybullet}, MuJoCo ${N.episodes_by_sim.mujoco}). Rates are reported with 95 % Wilson intervals {wilson}. Hypotheses H1–H5 about simulator differences (Section 3.1.4) were written down before the cross-simulator runs.`));


// --------------------------------------------------------------- 3.5 additions (Phase 1b-2 methods)
add(H3("3.5.9 Persistent Semantic Memory and Room Topology"));
add(P(`The memory stores, for every label, a list of entries {position, hits, last-seen time, confidence}; a new detection within 0.5 m of an entry updates it (exponential smoothing), otherwise it creates a new entry. An entry is trusted after two hits. The memory also stores which rooms have been fully explored (a 360° look completed inside them). The building's room connectivity — four rooms joined by four doors — is given, as a floor plan would be; **object locations are not**. Routes between rooms are planned on this graph through door centres. At the start of every subtask the mission checks memory first: a remembered object is reached directly and must be re-confirmed by perception on arrival (otherwise the entry is discarded as stale and search resumes); unexplored rooms are searched nearest-first. Three memory modes are compared: *none* (memory cleared at every subtask), *per-mission* (kept within a mission, cleared between missions) and *persistent* (kept across missions).`));
add(H3("3.5.10 Helipad Landing Procedure"));
add(P(`For "find the nearest helipad and land", the drone climbs to 1.6 m with the gimbal at −35° and performs a 360° look, storing every landing-pad candidate. Candidates are visited nearest-first. Above a candidate the gimbal turns to −90° and the marking is checked from directly above; decoys (X or plain pads) are rejected and the next-nearest candidate is visited. On a confirmed helipad the drone aligns within 0.1 m at 1.0 m altitude, then descends at 0.25 m/s while every pad sighting refines the pad position; the floor-clearance rule of the safety filter is replaced by a landing mode, all other rules stay active. Three pad detectors are compared: an oracle, a classical yellow-ring detector (finds pads but cannot read the marking) and the ring detector plus SmolVLM verification (three versions, Section 3.1.3).`));
add(H3("3.5.11 Embodiment Adapters"));
add(P("All three robots receive commands from the same planner. The adapters are the only embodiment-specific code and use no training data:"));
add(B([
  "**Drone:** world-frame velocity is tracked by the flight-controller emulation (velocity loop, attitude lag, fail-safe), as in Phase 1, plus a tiltable camera gimbal.",
  "**Ground robot (differential drive):** with heading error e = wrap(atan2(v_y, v_x) − ψ), the adapter outputs turn rate ω = clip(2.5·e, ±1.2 rad/s) and forward speed v = min(|v|, 0.6 m/s)·max(0, cos e)²; vertical commands are ignored. Its obstacle band is set to 0.05–0.55 m above the floor (what it could drive into).",
  "**Arm:** a 3-D target point is converted by inverse kinematics into joint targets for a pre-grasp pose 15 cm above the object, a descent to the object centre, a grasp and a 20 cm lift. Grasp simplification: when the open gripper is within 3 cm of the object centre and closes, the object is attached with a fixed constraint.",
]));
add(H3("3.5.12 Phase 1b–2 Protocol"));
add(P(`Every Phase 1b–2 cell uses 10 seeds (unseen, randomised layouts) in PyBullet with the 24-beam ring adopted from Phase 1. Configurations: oracle, colour (HSV) and hybrid (YOLO-World multi-class proposals + SmolVLM verification) for objects; oracle, ring detector and VLM-verified ring detector for pads; memory modes as above (perception fixed to the oracle in Experiment 7 to isolate the effect of memory). Object-approach success requires reporting arrival within ±0.2 m of the robot's stand-off (0.45 m drone, 0.8 m ground robot) at the correct object; landing success requires landing on a helipad (not a decoy) within 0.2 m of its centre; arm success requires lifting the correct object more than 10 cm.`));

add(H2("3.6 Details of Hardware and Software"));
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
add(H3("3.6.1 Proposed Custom-Drone Components"));
add(table("Tentative bill of materials for the custom drone (prices approximate — to be verified with suppliers)", ["Subsystem", "Suggested component (or equivalent)", "Reason", "≈ USD"], [
  ["Frame", "3.5-inch ducted (cinewhoop) frame", "Ducts act as prop guards", "30–50"],
  ["Flight controller", "PX4-supported H7 board (e.g. Holybro Kakute H7, Matek H743-mini)", "Runs PX4; enough UARTs", "50–80"],
  ["ESC", "4-in-1, 35–45 A, DShot", "Matches 3.5-inch on 4S", "40–60"],
  ["Motors / props", "4 × 1404–1505 class, 3000–4000 KV; ducted 3.5-inch props", "Thrust for ≈ 350 g AUW", "60–80"],
  ["Battery", "4S 650–850 mAh LiPo × 3 + charger", "5–7 min per pack", "60–90"],
  ["Flow + height", "Combined optical-flow + ToF module with PX4 support", "GPS-free position hold", "25–80"],
  ["Obstacle sensing", "3–4 × multi-zone ToF (VL53L5CX, 8 × 8 zones)", "Dense coverage (Section 3.7.6)", "30–60"],
  ["Companion computer", "Raspberry Pi Zero 2 W or Radxa Zero 3W", "Video stream + MAVLink bridge", "20–40"],
  ["Camera", "Raspberry Pi Camera Module 3 Wide (120°)", "Wide FOV, good low light", "35"],
  ["RC safety link", "ExpressLRS receiver + transmitter with kill switch", "Override independent of laptop", "80–120"],
  ["Safety equipment", "Net enclosure, LiPo bag, battery checker", "Supervised tests", "30–100"],
  ["Total", "", "", "≈ 500–800"],
], [17, 38, 30, 15]));


// ---------------------------------------------------------- 3.5 Results
add(H2("3.7 Results and Discussions"));
add(H3("3.7.1 Experiment 1 — Overall Results"));
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
add(H3("3.7.2 Perception Findings: the Simulation Domain Gap"));
add(P(`YOLO-World rated the rendered orange poorly: at 1.2 m the prompt "orange" scored 0.05, "fruit" 0.04 and "ball" 0.12, while "orange fruit" scored 0.21; at 0.6 m all prompts scored below 0.04 except "ball" (0.36). The synthetic textured sphere looks more like a ball than a fruit to a detector trained on real photographs. This explains C2's frequent target loss at close range (mean ${"2.7"} re-searches per episode) and motivated C5's low-threshold proposal + verification design. OWLv2 detected the orange at 1.2 m and 0.6 m (scores 0.16 and 0.40) at ~${OV.C3.lat_med.toFixed(0)} ms per frame.`));
add(table("Verifier calibration (crops at the true projected object position, PyBullet)", ["Object", "SmolVLM answer\n(2.0 / 1.2 / 0.7 m)", "CLIP top label\n(2.0 / 1.2 / 0.7 m)"], [
  ["Orange (target)", "Yes / Yes / Yes", "orange cube / orange ball / orange ball"],
  ["Plain orange ball", "Yes / Yes / Yes", "orange ball / orange ball / orange ball"],
  ["Orange cube", "No / No / No", "orange cube (all)"],
  ["Apple", "No / No / No", "red apple (all)"],
  ["Lemon", "No / No / No", "yellow lemon (all)"],
], [24, 34, 42]));
add(P(`With correct crops and the question "Is this an orange (the citrus fruit)?", SmolVLM accepted the orange and rejected the cube, apple and lemon at every distance, but **could not distinguish the orange from a plain orange ball**. An earlier wording ("…a real orange fruit…") produced "No" for most crops; CLIP {clip} classified most objects correctly but labelled the orange as a ball. SmolVLM was therefore selected as the verifier, with the ball confusion recorded as a known limitation.`));
add(H3("3.7.3 Distractor Analysis"));
const dist = Object.fromEntries(N.distractor.map((r) => [`${r.config}|${r.ball_present}`, r]));
const drow = (c, nm) => [nm, `${dist[c + "|true"].wrong} / ${dist[c + "|true"].episodes}`, `${dist[c + "|false"].wrong} / ${dist[c + "|false"].episodes}`];
const tD = table("Wrong-target episodes in T5–T7, split by whether a plain orange ball was present (PyBullet, seeds 0–9)", ["Configuration", "Orange ball present", "No orange ball"], [drow("C1", "C1 Colour"), drow("C3", "C3 OWLv2"), drow("C6", "C6 C5 without VLM"), drow("C5", "C5 Hybrid (ours)")], [40, 30, 30], { center: true });
add(P(`${tD.label} isolates the cause of the remaining errors. **Every one of C5's wrong-target episodes occurred in a scene containing the plain orange ball** (${dist["C5|true"].wrong}/${dist["C5|true"].episodes} with the ball, ${dist["C5|false"].wrong}/${dist["C5|false"].episodes} without), exactly as the calibration predicted. Without verification (C6) the drone was also fooled by the cube, lemon and apple (${dist["C6|false"].wrong}/${dist["C6|false"].episodes} without a ball). OWLv2 was almost always fooled when a ball was present (${dist["C3|true"].wrong}/${dist["C3|true"].episodes}). In the real world a better verifier (larger VLM, closer verification distance or multiple viewpoints) is needed for such near-identical distractors.`));
add(tD);
add(H3("3.7.4 Trajectories"));
const fTR = fig("res_trajectories.png", 6.4, "Top-down trajectories for seed 0 of each scenario (PyBullet); triangle = start, coloured dots = objects");
add(P(`${fTR.label} shows representative paths. In T3 the drone searches, discovers the target from a waypoint and routes around the wall; in T4 it weaves between pillars; in T6 it completes the full search pattern before reporting NOT_FOUND.`));
add(fTR);
add(H3("3.7.5 Latency"));
const fLAT = fig("res_latency.png", 5.2, "Perception/decision latency per configuration (log scale; median and 95th percentile)");
add(P(`${fLAT.label}: colour thresholding needs ~1 ms, YOLO-World-based configurations 16–21 ms median (the VLM in C5 is called only ${OV.C5.vlm_calls.toFixed(1)} times per episode on average, so its cost is amortised), OWLv2 ~${OV.C3.lat_med.toFixed(0)} ms (p95 ${OV.C3.lat_p95.toFixed(0)} ms) and the VLM policy ~${OV.C4.lat_med.toFixed(0)} ms per decision. Five processes shared one GPU during the experiments, so absolute latencies are pessimistic; the ranking is what matters.`));
add(fLAT);
add(H3("3.7.6 Experiment 3 — Safety: Collisions, Near-Misses and Sensor Design"));
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
add(H3("3.7.7 Link-Loss Fail-Safe"));
const fLL = fig("shot_linkloss.png", 6.0, "Link-loss test: hover 0.5 s after the last setpoint, landing from 3 s, landed safely");
add(P(`In all T9 runs where the link was lost (both simulators) the flight controller entered hover exactly 0.5 s after the last setpoint and was landed 6.15 s after the loss, without collision (${fLL.label}). The identical numbers in both simulators are expected: both execute our own fail-safe emulation, so this test verifies the logic, not real firmware timing (see H4).`));
add(fLL);
add(H3("3.7.8 Experiment 2 — Cross-Simulator Comparison"));
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
add(H3("3.7.9 Command Parsing"));
add(P(`The rule-based parser handled all ${N.parser.n} test phrasings correctly (${N.parser.correct}/${N.parser.n}), including distances ("half a metre", "50 cm"), colour-as-adjective ("orange ball"), clarification of ambiguous requests ("find the orange or the apple", "go over there") and abort commands. Because the phrase set was written together with the parser, this result is optimistic; an independent phrase set collected from other users is needed.`));
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

// --------------------------------------------------------------- Chapter 4 (rewritten)
chapter = 4;
add(H1("4. Future Work"));
const fRM2 = fig("fig_phases.png", 6.4, "Remaining phases of the project");
add(P(`The results of Phases 0–2 define what comes next (${fRM2.label}). Each phase has a question, a test and an exit criterion.`));
add(fRM2);
add(H2("4.1 Phase 3 — Scene-Graph Memory, LLM Task Planner and Replanning"));
add(P(`The simple object-and-room memory of Phase 2 will be extended into the three-layer world representation of the research proposal: (1) a topological graph of rooms and doors discovered online rather than given, (2) a metric map of robot and object positions, and (3) a semantic scene graph with object identities, relations ("on the table in the kitchen"), timestamps and confidence {hovsg,sayplan}. A small local LLM (e.g. a 3–8 B model served on the laptop) will decompose missions such as *"find the charging station in the building and report its location"* into a task graph and replan when the world changes (a closed door, a moved object). **Tests:** missions with environment changes mid-execution; metrics: mission completion, recovery time, replanning success, object-recall accuracy.`));
add(H2("4.2 Phase 4 — Real Hardware"));
add(B([
  "**DJI Neo 2 shadow mode:** the pilot flies; the pipeline runs on the recorded video and overlays detections and the command it would send (software ready: *neo2_shadow.py*). Output: the measured sim-to-real perception gap that hypothesis H5 needs.",
  "**Custom drone** (parts list in Section 3.6.1): bench tests with props off (link, latency, every fail-safe triggered deliberately), tethered hover, then netted-area flights at ≤ 0.3 m/s with a safety pilot on an independent kill switch.",
  "**Small ground robot** (e.g. a low-cost differential-drive base with a camera) running the *same* intelligence layer through the ground adapter — the real-world version of Experiment 5.",
  "**PX4 software-in-the-loop with Gazebo** {px4,gazebo} to test fail-safe timing with real firmware (H4).",
]));
add(H2("4.3 Phase 5 — Learned Adapters and Data Efficiency"));
add(P(`Phase 2 used hand-written adapters and zero robot-specific data. Phase 5 asks how much data a *learned* adapter needs (RQ4). Following HPT {hpt} and NaVILA {navila}, a VLA such as SmolVLA {smolvla} will be adapted as a mid-level policy: the arm action head is replaced by drone or ground-robot actions, drone state is added as proprioception, and the action expert is trained on demonstrations generated by the Phase-1/2 planner in simulation (stored in LeRobot format {lerobot}) with DAgger corrections {dagger}. The experiment will vary the number of demonstrations (10, 30, 100, 300) and compare the learned policy with the hand-written adapter and the hybrid C5 on the same scenarios and metrics.`));
add(H2("4.4 Perception and Evaluation Improvements"));
add(B([
  "Separating near-identical objects (orange vs plain orange ball): larger or fine-tuned verifier, multi-view verification, closer inspection before committing.",
  "Photorealistic multi-room environments (Habitat scans or Isaac Sim) to reduce the rendering gap measured in Phase 1.",
  "Fixed modelled latency per model for exactly reproducible runs, alongside live measurements; independent phrase sets for the command parser.",
]));

// --------------------------------------------------------------- Appendix A: timeline by phases
chapter = "A";
add(H1("Appendix A. Project Timeline, Phases and Work Division"));
add(P(`The project was carried out in the phases described in Section 3.1. The table records, for each phase, the activities, the outputs and the evidence that documents them. **Dates and owners highlighted in yellow must be filled in by the team from their own records** (meeting notes, messages, file dates); the evidence column lists the files produced by this report's work.`));
add(table("Project phases: activities, outputs and evidence", ["Phase", "Dates", "Activities", "Outputs", "Evidence"], [
  ["0 Problem framing", "[[dates]]", "Topic selection; literature on VLA/VLN, drone VLAs, memory, cross-embodiment; research proposal; tool survey", "Problem statement, gaps G1–G5, proposal deck, plan", "Research proposal (.pptx), Ch. 1–2"],
  ["1 Single-goal drone", "[[dates]]", "Simulator setup; 7 perception configurations; 10 scenarios; MuJoCo cross-check; sensor ablation", "~1,400 episodes, Phase-1 results", "sim/out/results*.jsonl"],
  ["1b Task + embodiment diversity", "[[dates]]", "Helipad task and 3 verifier iterations; Husky ground robot; Franka arm", "Experiments 4–6", "sim/out/world_L/O/A.jsonl"],
  ["2 Memory + missions", "[[dates]]", "Semantic memory, room topology, multi-object missions", "Experiment 7", "sim/out/world_M.jsonl"],
  ["Report + presentation", "[[dates]]", "Analysis, figures, report, demo videos", "This report, demo videos", "report/, sim/out/demo_*.mp4"],
], [15, 10, 33, 21, 21]));
add(table("Work division", ["Member", "Modules / experiments owned", "Report sections"], [
  ["Prarthana Yadwad (2309096)", "[[ ]]", "[[ ]]"], ["Kshitij Pujari (2307582)", "[[ ]]", "[[ ]]"], ["Amitav Ramesh (2305377)", "[[ ]]", "[[ ]]"],
], [30, 40, 30]));
add(H1("Appendix B. Reproducing the Results"));
add(B([
  "Environment: D:\\pinnacle\\.venv (Python 3.12); all caches in D:\\pinnacle\\.cache. Run *. D:\\pinnacle\\env.ps1* once per terminal.",
  "Phase 1: *python run_batch.py --configs C0,C1 --seeds 20* (add *--sim mujoco*); analysis *python analyze.py*.",
  "Phase 1b–2: *python run_world.py --exp O|L|M|A* (resumable; results in sim/out/world_*.jsonl).",
  "Screenshots: *python showcase.py*; demo video: *python record_demo.py --config C5 --scenario T5*; interactive flight: *python fly.py --scenario T4*.",
  "Neo 2 shadow mode: *python neo2_shadow.py --video clip.mp4 --detector hybrid*.",
]));
add(P(`Prompts: C4 — *"…Where is the orange in the image? Answer with exactly one word: left, right, center, close, or none."* C5 — *"Is this an orange (the citrus fruit)? Answer yes or no."* Pad verifier v3 — *"This is a landing pad seen from above. Is there a large letter H painted in the middle? Answer yes or no."* (asked on the crop and on the crop rotated by 90°).`));

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
const TITLE = "Language-Guided Robots on Affordable Hardware: Persistent Memory and Cross-Embodiment Transfer — Phase 1–2 Design and Simulation Study";
const cline = (t, o = {}) => new Paragraph({ children: runs(t, { size: o.size || 24, bold: o.bold, font: FONT }), alignment: AlignmentType.CENTER, spacing: { after: o.after ?? 120, line: 276 } });
const STU = [["Prarthana Yadwad", "2309096"], ["Kshitij Pujari", "2307582"], ["Amitav Ramesh", "2305377"]];
const students = (y) => STU.map(([n, id]) => new Paragraph({ children: [new TextRun({ text: n, size: 24 }), new TextRun({ text: "\t" }), new TextRun({ text: id, size: 24 })], tabStops: [{ type: TabStopType.LEFT, position: 3600 }, { type: TabStopType.LEFT, position: 6000 }], indent: { left: 2600 }, spacing: { after: 60 } }));
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
  new Paragraph({ children: [new TextRun({ text: "Dr Sneha Talreja", size: 24 })], alignment: AlignmentType.CENTER }),
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
  new Paragraph({ children: [new TextRun({ text: "(Dr Sneha Talreja)", size: 24 })] }),
];
const ack = [
  FH("Acknowledgement"),
  P(`We express our sincere gratitude to our guide, Dr Sneha Talreja, for continuous guidance and feedback throughout this project. We thank the faculty of uGDX School of Technology for providing the opportunity and resources for the Design Project Minor course, and our peers for their suggestions. We also acknowledge the open-source communities behind PyBullet, MuJoCo, PyTorch, Ultralytics and Hugging Face, whose tools made this work possible.`),
];
const abstract = [
  FH("Abstract"),
  P(`Vision-language models make it possible to give robots instructions in plain language, but deploying them on affordable, off-the-shelf robots is hard: the models are large and robot-specific, they forget what they have seen, and they provide no safety guarantees. This project addresses the problem of turning natural-language instructions into safe action on affordable drones, ground vehicles and robot arms, without a prebuilt map, expensive onboard computing or robot-specific training, while remembering the environment across multi-step missions. The work was organised in phases; this report covers Phases 0–2 in simulation. We designed a modular, laptop-hosted architecture in which zero-shot detectors propose candidates, a small vision-language model verifies them, a persistent semantic memory stores objects and explored rooms, a classical planner acts, and an independent, learning-free safety filter has the final say; thin adapters connect this shared layer to each robot. Seven perception configurations were compared over about 1,400 drone episodes in two simulators (PyBullet and MuJoCo); the hybrid design reached ${v(OV.C5.nav_succ)} % navigation success at about ${v(OV.C5.lat_med)} ms per frame, whereas a small vision-language model used directly as the pilot failed in every run. Further experiments added task and embodiment diversity: finding and landing on the nearest helipad among decoys (${v(hpAll("v3").strict3)} % in normal light after three verifier iterations, against ${v(hpAll("ring").strict3)} % for colour-only detection; dim light remains unsolved), the same intelligence layer on a wheeled ground robot and on a Franka Panda arm, and multi-object missions in a four-room house, where persistent memory reduced repeated-mission time by about ${v(red_abs("drone"))} % (drone) and ${v(red_abs("ground"))} % (ground robot). The report documents the options considered, the design iterations and pre-registered hypotheses, and closes with a phase plan towards scene-graph memory with an LLM task planner, real hardware (DJI Neo 2 shadow mode and a custom drone) and learned embodiment adapters.`),
  P(`**Keywords:** embodied AI, vision-language models, drones, cross-embodiment, persistent memory, safety filter, simulation.`),
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
  ["HSV", "Hue–saturation–value colour space"], ["IK", "Inverse kinematics"], ["LLM", "Large language model"], ["MAVLink", "Micro Air Vehicle Link protocol"],
  ["NL", "Natural language"], ["PX4", "Open-source autopilot flight stack"], ["RC", "Radio control"], ["SITL", "Software-in-the-loop"],
  ["SPL", "Success weighted by path length"], ["UGV", "Unmanned ground vehicle"], ["ToF", "Time of flight (range sensor)"], ["VIO", "Visual-inertial odometry"],
  ["VLA", "Vision-language-action model"], ["VLM", "Vision-language model"], ["VLN", "Vision-language navigation"],
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
const out = path.join(DIR, "Project_Report_v2.docx");
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(out, buf); console.log("wrote", out, "refs:", order.length, "figs:", JSON.stringify(figCount), "tables:", JSON.stringify(tabCount)); });
