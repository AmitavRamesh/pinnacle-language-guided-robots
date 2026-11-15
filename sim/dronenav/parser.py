"""Command parser: natural language -> structured mission JSON.
Rule-based baseline (deterministic, offline). An LLM parser with the same output
schema can be swapped in; both are scored on the same phrase set (metric P4)."""
from __future__ import annotations

import re

KNOWN = ["orange", "apple", "lemon", "ball", "cube", "box", "bottle", "cup", "chair", "door"]
NUM = {"half a": 0.5, "half": 0.5, "one": 1.0, "a": 1.0}


def parse(cmd: str) -> dict:
    c = cmd.lower().strip()
    out = {"intent": None, "target": None, "standoff_m": 0.5, "search_area": "room",
           "max_speed": 0.5, "clarify": None}
    if re.search(r"\b(land|stop|abort|cancel)\b", c) and not re.search(r"\b(find|approach|go|fly|locate)\b", c):
        out["intent"] = "abort"
        return out
    if re.search(r"\b(find|approach|go to|fly (to|near|towards)|locate|search|look for|get close)\b", c):
        out["intent"] = "find_approach"
    objs = [o for o in KNOWN if re.search(rf"\b{o}s?\b", c)]
    if "orange" in objs and re.search(r"orange (ball|cube|box|cup|bottle)", c):
        objs = [o for o in objs if o != "orange"]  # 'orange' used as colour
    if len(objs) == 1:
        out["target"] = objs[0]
        m = re.search(rf"orange (ball|cube|box|cup|bottle)", c)
        if m:
            out["target"] = m.group(0)
    elif len(objs) > 1:
        out["target"] = objs[0]
        if not re.search(r"\b(next to|near|beside|on)\b", c):
            out["clarify"] = f"Several objects mentioned ({', '.join(objs)}). Which one should I approach?"
    m = re.search(r"(\d+(?:\.\d+)?)\s*(cm|centimet\w*|m\b|metres?|meters?)", c)
    if m:
        val = float(m.group(1))
        out["standoff_m"] = val / 100 if m.group(2).startswith("c") else val
    else:
        m = re.search(r"(half a|half|one|a) (metre|meter)", c)
        if m:
            out["standoff_m"] = NUM[m.group(1)]
    if re.search(r"\b(slow|slowly|carefully|gently)\b", c):
        out["max_speed"] = 0.3
    if out["intent"] is None:
        out["clarify"] = "I did not understand the task. Should I find and approach an object?"
    elif out["target"] is None:
        out["clarify"] = "Which object should I find?"
    out["standoff_m"] = min(max(out["standoff_m"], 0.4), 2.0)  # safety clamp
    return out


# Phrase set for metric P4: (command, expected target or None, expects_clarification)
TEST_SET = [
    ("find and approach the orange", "orange", False),
    ("go to the orange", "orange", False),
    ("fly near the orange and stop half a metre away", "orange", False),
    ("locate the orange fruit", "orange", False),
    ("can you find the orange for me", "orange", False),
    ("approach the orange, stay 50 cm away", "orange", False),
    ("search for an orange in the room", "orange", False),
    ("look for the oranges", "orange", False),
    ("get close to the orange slowly", "orange", False),
    ("fly towards the orange carefully", "orange", False),
    ("find the apple", "apple", False),
    ("go to the lemon and stop 1 m away", "lemon", False),
    ("approach the orange ball", "orange ball", False),
    ("find the orange cube", "orange cube", False),
    ("find the orange next to the apple", "orange", False),
    ("go to the orange on the table", "orange", False),
    ("find the orange or the apple", None, True),
    ("approach the apple and the lemon", None, True),
    ("go over there", None, True),
    ("find it", None, True),
    ("do a flip", None, True),
    ("orange", None, True),
    ("stop", None, False),
    ("land now", None, False),
    ("find the orange and stay 2 metres away", "orange", False),
    ("approach the orange at 30 cm", "orange", False),  # clamped to 0.4 m
    ("find the fruit", None, True),
    ("fly to the orange thing", "orange", False),
    ("locate the citrus", None, True),
    ("go find me an orange please", "orange", False),
]


def score_parser(fn=parse):
    rows = []
    for cmd, tgt, clar in TEST_SET:
        r = fn(cmd)
        if tgt is None and not clar:  # abort commands
            ok = r["intent"] == "abort"
        elif clar:
            ok = r["clarify"] is not None
        else:
            ok = r["clarify"] is None and r["target"] == tgt
        rows.append(dict(command=cmd, expected=tgt, expect_clarify=clar, got=r["target"],
                         clarify=r["clarify"], intent=r["intent"], correct=ok))
    return rows
