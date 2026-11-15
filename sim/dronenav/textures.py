"""Procedural textures so the target looks like a fruit, not just an orange blob."""
from pathlib import Path

import cv2
import numpy as np

ASSETS = Path(__file__).resolve().parent.parent / "assets"


def _peel(base_bgr, seed, dimple=18, spots=None, size=256):
    rng = np.random.default_rng(seed)
    img = np.zeros((size, size, 3), np.float32)
    img[:] = base_bgr
    # dimpled peel: blurred noise as shading
    n = rng.normal(0, 1, (size, size)).astype(np.float32)
    n = cv2.GaussianBlur(n, (0, 0), 1.5)
    img *= (1 + 0.08 * n)[..., None]
    # large-scale shading variation
    g = cv2.GaussianBlur(rng.normal(0, 1, (size, size)).astype(np.float32), (0, 0), 25)
    img *= (1 + 0.6 * g / (np.abs(g).max() + 1e-6) * 0.25)[..., None]
    if spots:
        for _ in range(spots[0]):
            c = tuple(int(v) for v in rng.integers(0, size, 2))
            cv2.circle(img, c, int(rng.integers(2, 5)), spots[1], -1)
    # stem at the top of the UV map
    cv2.ellipse(img, (size // 2, 6), (10, 5), 0, 0, 360, (30, 80, 40), -1)
    return np.clip(img, 0, 255).astype(np.uint8)


def ensure_textures() -> dict:
    ASSETS.mkdir(parents=True, exist_ok=True)
    specs = {
        "orange_peel": ((20, 130, 240), 1, (40, (10, 90, 200))),
        "apple": ((30, 30, 190), 2, (60, (60, 160, 230))),
        "lemon": ((40, 220, 245), 3, (30, (30, 180, 210))),
    }
    paths = {}
    for name, (bgr, seed, spots) in specs.items():
        p = ASSETS / f"{name}.png"
        if not p.exists():
            cv2.imwrite(str(p), _peel(bgr, seed, spots=spots))
        paths[name] = str(p)
    return paths


def _pad(kind, size=512):
    """Landing pads: 'H' helipad, 'X' decoy (closed/no-landing pad), 'plain' decoy."""
    img = np.full((size, size, 3), (70, 70, 70), np.uint8)  # asphalt square
    c = size // 2
    cv2.circle(img, (c, c), int(size * 0.47), (40, 200, 240), -1)  # yellow disc (BGR)
    cv2.circle(img, (c, c), int(size * 0.40), (60, 60, 60), -1)  # dark inner disc
    w = int(size * 0.07)
    if kind == "H":
        cv2.rectangle(img, (c - int(size * .17), c - int(size * .2)), (c - int(size * .17) + w, c + int(size * .2)), (255, 255, 255), -1)
        cv2.rectangle(img, (c + int(size * .17) - w, c - int(size * .2)), (c + int(size * .17), c + int(size * .2)), (255, 255, 255), -1)
        cv2.rectangle(img, (c - int(size * .17), c - w // 2), (c + int(size * .17), c + w // 2), (255, 255, 255), -1)
    elif kind == "X":
        d = int(size * .2)
        cv2.line(img, (c - d, c - d), (c + d, c + d), (255, 255, 255), w)
        cv2.line(img, (c - d, c + d), (c + d, c - d), (255, 255, 255), w)
    return img


def ensure_pad_textures() -> dict:
    ASSETS.mkdir(parents=True, exist_ok=True)
    out = {}
    for k in ["H", "X", "plain"]:
        p = ASSETS / f"pad_{k}.png"
        if not p.exists():
            cv2.imwrite(str(p), _pad(k))
        out[k] = str(p)
    return out
