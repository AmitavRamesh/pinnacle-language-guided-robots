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
