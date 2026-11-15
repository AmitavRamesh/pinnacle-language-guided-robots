"""Keeps every cache, model download and temp file on D:\\pinnacle\\.cache.
Imported before torch/transformers/ultralytics, so the env vars take effect."""
import os
import tempfile
from pathlib import Path

CACHE = Path(__file__).resolve().parents[2] / ".cache"  # D:\pinnacle\.cache
WEIGHTS = CACHE / "weights"
_env = {
    "HF_HOME": CACHE / "hf",
    "HF_HUB_CACHE": CACHE / "hf" / "hub",
    "TORCH_HOME": CACHE / "torch",
    "YOLO_CONFIG_DIR": CACHE / "ultralytics",
    "MPLCONFIGDIR": CACHE / "mpl",
    "PIP_CACHE_DIR": CACHE / "pip",
    "TMP": CACHE / "tmp",
    "TEMP": CACHE / "tmp",
}
for k, v in _env.items():
    v.mkdir(parents=True, exist_ok=True)
    os.environ[k] = str(v)
WEIGHTS.mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(CACHE / "tmp")
