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
