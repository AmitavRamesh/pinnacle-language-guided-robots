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
