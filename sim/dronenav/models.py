"""GPU model configurations.

C2  YOLO-World (open-vocabulary, real-time)        + classical planner
C3  OWLv2 (open-vocabulary, slower, more accurate) + classical planner
C4  VLM as high-level policy (discrete actions)    + safety filter     (see policy.py)
C5  Hybrid: YOLO-World proposals -> VLM verification of each candidate crop
    -> depth fusion -> classical planner + safety filter
"""
from __future__ import annotations

import os

import numpy as np

from .perception import Perception, boxes_to_detections

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
VLM_ID = os.environ.get("DRONENAV_VLM", "HuggingFaceTB/SmolVLM-500M-Instruct")
_cache = {}


def _device():
    import torch
    return "cuda" if torch.cuda.is_available() else "cpu"


# ------------------------------------------------------------------ YOLO-World
class YoloWorldPerception(Perception):
    name = "yolo_world"
    needs_gpu = True

    PROMPTS = {"orange": "orange fruit"}  # tested: plain "orange" scores ~0.05 on sim renders, "orange fruit" ~0.2

    def __init__(self, weights="yolov8s-worldv2.pt", conf=0.02):
        from ultralytics import YOLO, settings

        from . import WEIGHTS
        settings.update(weights_dir=str(WEIGHTS))  # CLIP text encoder etc. download here
        self.model = YOLO(str(WEIGHTS / weights))
        self.conf = conf
        self._classes = None

    def raw(self, rgb, query, conf=None):
        q = self.PROMPTS.get(query, query)
        if self._classes != q:
            self.model.set_classes([q])
            self._classes = q
        r = self.model.predict(rgb[..., ::-1], conf=self.conf if conf is None else conf, imgsz=640, verbose=False,
                               device=_device())[0]
        b = r.boxes
        return b.xyxy.cpu().numpy(), b.conf.cpu().numpy()

    def detect(self, sim, pose, query):
        boxes, scores = self.raw(sim.get_rgb(), query)
        return boxes_to_detections(boxes, scores, [query] * len(scores), sim, pose, query)


# ----------------------------------------------------------------------- OWLv2
class OwlV2Perception(Perception):
    name = "owlv2"
    needs_gpu = True

    def __init__(self, model_id="google/owlv2-base-patch16-ensemble", thresh=0.1):
        import torch
        from transformers import Owlv2ForObjectDetection, Owlv2Processor
        self.proc = Owlv2Processor.from_pretrained(model_id)
        self.model = Owlv2ForObjectDetection.from_pretrained(model_id, torch_dtype=torch.float16).to(_device()).eval()
        self.thresh = thresh

    def raw(self, rgb, query):
        import torch
        from PIL import Image
        img = Image.fromarray(rgb)
        inp = self.proc(text=[[f"a photo of an {query}" if query[0] in "aeiou" else f"a photo of a {query}"]],
                        images=img, return_tensors="pt").to(_device())
        inp["pixel_values"] = inp["pixel_values"].half()
        with torch.no_grad():
            out = self.model(**inp)
        # OWLv2 pads to a square; target size = max side
        s = max(rgb.shape[:2])
        pp = getattr(self.proc, "post_process_object_detection", None) or self.proc.post_process_grounded_object_detection
        res = pp(out, threshold=self.thresh, target_sizes=torch.tensor([[s, s]], device=_device()))[0]
        return res["boxes"].float().cpu().numpy(), res["scores"].float().cpu().numpy()

    def detect(self, sim, pose, query):
        boxes, scores = self.raw(sim.get_rgb(), query)
        return boxes_to_detections(boxes, scores, [query] * len(scores), sim, pose, query)


# ------------------------------------------------------------------------- VLM
class VLM:
    """Small local vision-language model used for yes/no verification and
    for the discrete-action policy (C4)."""

    def __init__(self, model_id=VLM_ID):
        import torch
        from transformers import AutoModelForImageTextToText, AutoProcessor
        self.proc = AutoProcessor.from_pretrained(model_id)
        self.model = AutoModelForImageTextToText.from_pretrained(model_id, torch_dtype=torch.bfloat16).to(_device()).eval()
        self.model_id = model_id

    def ask(self, rgb, question, max_new_tokens=5):
        import torch
        from PIL import Image
        msgs = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": question}]}]
        prompt = self.proc.apply_chat_template(msgs, add_generation_prompt=True)
        inp = self.proc(text=prompt, images=[Image.fromarray(rgb)], return_tensors="pt").to(_device())
        with torch.no_grad():
            out = self.model.generate(**inp, max_new_tokens=max_new_tokens, do_sample=False)
        txt = self.proc.batch_decode(out[:, inp["input_ids"].shape[1]:], skip_special_tokens=True)[0]
        return txt.strip()


def get_vlm():
    if "vlm" not in _cache:
        _cache["vlm"] = VLM()
    return _cache["vlm"]


def get_yolo():
    if "yolo" not in _cache:
        _cache["yolo"] = YoloWorldPerception()
    return _cache["yolo"]


def crop(rgb, box, pad=0.6, out=224):
    import cv2
    H, W = rgb.shape[:2]
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    s = max(w, h) * (1 + 2 * pad) / 2 + 4
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    a, b = int(max(0, cx - s)), int(max(0, cy - s))
    c, d = int(min(W, cx + s)), int(min(H, cy + s))
    return cv2.resize(rgb[b:d, a:c], (out, out), interpolation=cv2.INTER_CUBIC)


# ---------------------------------------------------------------------- hybrid
class HybridPerception(Perception):
    """C5: detector proposes, VLM verifies each new candidate once (cached by
    world-position cell), depth gives metric position."""
    name = "hybrid"
    needs_gpu = True
    CELL = 0.3

    DET_CONF = 0.002  # detector as high-recall proposal generator; the VLM supplies precision
    MIN_VERIFY_PX = 12  # below this the crop is too small for the VLM to judge (calibration test)
    QUESTION = "Is this an {q} (the citrus fruit)? Answer yes or no."

    def __init__(self):
        self.det = get_yolo()
        self.vlm = get_vlm()
        self.verdicts = {}  # cell -> (verdict, box width at verification)
        self.vlm_calls = 0

    def reset(self):
        self.verdicts = {}
        self.vlm_calls = 0

    def _key(self, pos):
        return tuple(np.round(pos[:2] / self.CELL).astype(int))

    def detect(self, sim, pose, query):
        """Active verification: small (far) candidates are passed on as low-confidence
        so the planner approaches them; once a candidate is >= MIN_VERIFY_PX wide the
        VLM checks it. Rejected cells are blacklisted; a cell is re-checked if it is
        seen >= 1.5x larger than at its last check."""
        rgb = sim.get_rgb()
        boxes, scores = self.det.raw(rgb, query, conf=self.DET_CONF)
        dets = boxes_to_detections(boxes, scores, [query] * len(scores), sim, pose, query)
        out = []
        for d in dets:
            k = self._key(d.pos)
            w = max(d.bbox[2] - d.bbox[0], d.bbox[3] - d.bbox[1])
            prev = self.verdicts.get(k)
            if w >= self.MIN_VERIFY_PX and (prev is None or w >= 1.5 * prev[1]):
                ans = self.vlm.ask(crop(rgb, d.bbox), self.QUESTION.format(q=query), max_new_tokens=3).lower()
                self.vlm_calls += 1
                prev = self.verdicts[k] = (ans.startswith("yes"), w)
            if prev is None:
                d.conf = min(d.conf, 0.3)  # unverified candidate: approach to verify
                out.append(d)
            elif prev[0]:
                d.conf = max(d.conf, 0.6)
                out.append(d)
        return out


class YoloLowNoVerify(Perception):
    """C6 ablation: C5's low-threshold detector WITHOUT VLM verification."""
    name = "yolo_low_noverify"
    needs_gpu = True

    def __init__(self):
        self.det = get_yolo()

    def detect(self, sim, pose, query):
        boxes, scores = self.det.raw(sim.get_rgb(), query, conf=HybridPerception.DET_CONF)
        return boxes_to_detections(boxes, scores, [query] * len(scores), sim, pose, query)


def make(cfg):
    if cfg == "C6":
        return YoloLowNoVerify()
    if cfg == "C2":
        return get_yolo()
    if cfg == "C3":
        return OwlV2Perception()
    if cfg == "C5":
        return HybridPerception()
    if cfg == "C4":
        from .policy import VLMPolicy
        return VLMPolicy(get_vlm())
    raise ValueError(cfg)
