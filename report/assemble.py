"""Builds build_report2.js from the validated Phase-1 builder (build_report.js) plus the new parts."""
import re
from pathlib import Path

D = Path(__file__).resolve().parent
old = (D / "build_report.js").read_text(encoding="utf-8").split("\n")
part = lambda n: (D / "parts" / n).read_text(encoding="utf-8")  # noqa: E731


def find(prefix, start=0):
    for i in range(start, len(old)):
        if old[i].startswith(prefix) or prefix in old[i]:
            return i
    raise KeyError(prefix)


i_content = find("// ======================================================================= CONTENT")
i_ch1 = find("// --------------------------------------------------------------- Chapter 1")
i_ch2 = find("// --------------------------------------------------------------- Chapter 2")
i_gap = find('add(H2("2.8 Research Gap"));')
i_ch3 = find("// --------------------------------------------------------------- Chapter 3")
i_an = find('add(H2("3.1 Analysis"));')
i_impl = find('add(H2("3.3 Implementation Methodology"));')
i_hw = find('add(H2("3.4 Details of Hardware and Software"));')
i_res = find("// ---------------------------------------------------------- 3.5 Results")
i_prob = find('add(H3("3.5.10 Problems Encountered"));')
i_ch4 = find("// --------------------------------------------------------------- Chapter 4")
i_refs = find("// ------------------------------------------------------------- references")
i_front = find("// ================================================================== FRONT MATTER")

head = "\n".join(old[:i_ch1])
ch2_old = "\n".join(old[i_ch2:i_gap])
analysis_design = "\n".join(old[i_an:i_impl])
impl = "\n".join(old[i_impl:i_hw])
hw = "\n".join(old[i_hw:i_res])
res_old = "\n".join(old[i_res:i_prob])
tail = "\n".join(old[i_refs:])

# ---- references
new_refs = '''  crossformer: `R. Doshi, H. Walke, O. Mees, S. Dasari, and S. Levine, "Scaling cross-embodied learning: One policy for manipulation, navigation, locomotion and aviation," in Proc. Conf. Robot Learning (CoRL), 2024.`,
  hpt: `L. Wang, X. Chen, J. Zhao, and K. He, "Scaling proprioceptive-visual learning with heterogeneous pre-trained transformers," in Proc. Advances in Neural Information Processing Systems (NeurIPS), 2024.`,
  navfom: `Zhang et al., "Embodied navigation foundation model," in Proc. Int. Conf. Learning Representations (ICLR), 2026, arXiv:2509.12129.`,
  remembr: `A. Anwar, J. Welsh, J. Biswas, S. Pouya, and Y. Chang, "ReMEmbR: Building and reasoning over long-horizon spatio-temporal memory for robot navigation," arXiv:2409.13682, 2024.`,
  hovsg: `A. Werby et al., "Hierarchical open-vocabulary 3D scene graphs for language-grounded robot navigation," in Proc. Robotics: Science and Systems (RSS), 2024.`,
  sayplan: `K. Rana et al., "SayPlan: Grounding large language models using 3D scene graphs for scalable robot task planning," in Proc. Conf. Robot Learning (CoRL), 2023.`,
  threedmem: `Y. Yang et al., "3D-Mem: 3D scene memory for embodied exploration and reasoning," in Proc. IEEE/CVF Conf. Computer Vision and Pattern Recognition (CVPR), 2025, pp. 17294–17303.`,
'''
head = head.replace("  lerobot:", new_refs + "  lerobot:", 1)
head += "\n" + part("helpers_world.js") + "\n"

# ---- renumber old Chapter 3 sections
def renum(s, mapping):
    for a, b in mapping:
        s = s.replace(f'"{a}', f'"__{b}')
    return s.replace('"__', '"')


analysis_design = renum(analysis_design, [("3.1.", "3.2."), ("3.1 ", "3.2 "), ("3.2.1", "3.3.2"), ("3.2.2", "3.3.3"),
                                          ("3.2.3", "3.3.4"), ("3.2.4", "3.3.5"), ("3.2 Design", "3.3 Design")])
analysis_design = analysis_design.replace('add(H2("3.3 Design"));', '''add(H2("3.3 Design"));
add(H3("3.3.1 Layered Architecture"));
const fLay = fig("fig_layered.png", 6.4, "Layered architecture: one shared intelligence layer, an independent safety filter and thin adapters for three robots");
add(P(`${fLay.label} shows the architecture that resulted from Phases 1–2. Everything above the dashed line — mission parsing, perception, persistent memory, planning and the safety filter — is identical code for every robot and runs on the laptop. The only robot-specific parts are the adapters, which translate a common command (a world-frame velocity setpoint or a 3-D target point) into what each body can execute. Section 3.3.2 details the Phase-1 drone instance of this architecture.`));
add(fLay);''')
impl = renum(impl, [("3.3.", "3.5."), ("3.3 ", "3.5 ")])
hw = renum(hw, [("3.4.1", "3.6.1"), ("3.4 ", "3.6 ")])
res_old = renum(res_old, [("3.5 Results", "3.7 Results"), ("3.5.1 Overall", "3.7.1 Experiment 1 — Overall"), ("3.5.2", "3.7.2"),
                          ("3.5.3", "3.7.3"), ("3.5.4", "3.7.4"), ("3.5.5", "3.7.5"), ("3.5.6 Safety", "3.7.6 Experiment 3 — Safety"),
                          ("3.5.7", "3.7.7"), ("3.5.8 Cross", "3.7.8 Experiment 2 — Cross"), ("3.5.9", "3.7.9")])

fix = [("into the mission JSON (Table 3.2)", "into the mission JSON (data dictionary, Section 3.2.4)"),
       ("only perception/decision differs (Table 3.3)", "only perception/decision differs (table below)"),
       ("The proposed components are listed in Table 3.8.", "The proposed components are listed in Section 3.6.1."),
       ("calibration test on 15 crops (Table 3.10)", "calibration test on 15 crops (Section 3.7.2)"),
       ("Five hypotheses about simulator differences (Table 3.13) were written down before the cross-simulator runs.",
        "Hypotheses H1–H5 about simulator differences (Section 3.1.4) were written down before the cross-simulator runs."),
       ("Section 3.5.6", "Section 3.7.6"), ("in Section 3.5 is computed", "in Section 3.7 is computed"),
       ("Dense coverage (Section 3.5.6)", "Dense coverage (Section 3.7.6)")]
blob = "\n".join([analysis_design, impl, hw, res_old])
for a, b in fix:
    blob = blob.replace(a, b)
analysis_design, impl, hw, res_old = blob.split("\n", 0)[0], "", "", ""  # recombined below
ch3_old_all = blob

# split recombined blob back at the implementation heading so the new sim section goes before it
k_impl = ch3_old_all.index('add(H2("3.5 Implementation Methodology"));')
k_hw = ch3_old_all.index('add(H2("3.6 Details of Hardware and Software"));')
k_res = ch3_old_all.index("// ---------------------------------------------------------- 3.5 Results")
A, B, Cc, R = ch3_old_all[:k_impl], ch3_old_all[k_impl:k_hw], ch3_old_all[k_hw:k_res], ch3_old_all[k_res:]

gap = '''add(H2("2.11 Research Gap"));
add(P(`The literature shows that (i) VLAs need action-space adaptation and large flight datasets before they can control a drone, (ii) open-vocabulary detectors and small VLMs offer semantics but uncertain precision, (iii) memory and cross-embodiment transfer are active research areas whose strongest results rely on large datasets and GPUs, and (iv) little work quantifies, under identical scenarios, how much each component contributes on affordable robots, or how results differ between simulators. This project addresses that gap with a modular, laptop-hosted architecture, an independent safety layer, controlled comparisons across seven perception configurations, three robots, four task types and two simulators, and an explicit phase plan towards learned adapters and real hardware.`));
'''
content = "\n".join([part("ch1.js"), ch2_old, part("ch2_extra.js"), gap, part("ch3_process.js"), A, part("ch3_sim.js"), B,
                     part("ch3_methods2.js"), Cc, R, part("results2.js"), part("ch4_app.js")])
content = content.replace("Section 3.7.3 for the remaining failures", "Section 3.7.11")
content = content.replace('"Kept; remaining failures analysed in Section 3.7.3"', '"Kept; remaining failures analysed in Section 3.7.11"')
content = content.replace("the full problem log is in Section 3.7.9", "the full problem log is in Section 3.7.16")
content = content.replace("(Table 3.x parts list)", "(parts list in Section 3.6.1)")

# ---- front matter: title, abstract, abbreviations
tail = re.sub(r'const TITLE = ".*?";', 'const TITLE = "Language-Guided Robots on Affordable Hardware: Persistent Memory and Cross-Embodiment Transfer — Phase 1–2 Design and Simulation Study";', tail)
a0 = tail.index("const abstract = [")
a1 = tail.index("];", a0) + 2
tail = tail[:a0] + part("abstract.js") + tail[a1:]
tail = tail.replace('["HSV", "Hue–saturation–value colour space"],', '["HSV", "Hue–saturation–value colour space"], ["IK", "Inverse kinematics"],')
tail = tail.replace('["SPL", "Success weighted by path length"],', '["SPL", "Success weighted by path length"], ["UGV", "Unmanned ground vehicle"],')
tail = tail.replace('["VLM", "Vision-language model"],', '["VLM", "Vision-language model"], ["VLN", "Vision-language navigation"],')

out = head + "\n" + content + "\n" + tail
out = out.replace('path.join(DIR, "Project_Report.docx")', 'path.join(DIR, "Project_Report_v2.docx")')
(D / "build_report2.js").write_text(out, encoding="utf-8")
print("assembled", len(out), "chars")
