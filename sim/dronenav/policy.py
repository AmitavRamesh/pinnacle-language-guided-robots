"""C4: VLM as a high-level policy with a discrete action space (zero-shot, no
fine-tuning). This is the 'VLA-style' option B from the architecture: the model
chooses *what* to do; motion primitives + the safety filter decide *how*.

Action space: left | right | center (fly forward) | close (stop & report) | none (explore)
"""
from __future__ import annotations

import math

import numpy as np

from .planner import FLY_Z, VZ_MAX, wrap

TURN = math.radians(30)
FWD = 0.5
V_FWD = 0.35
YAW_RATE = 0.7
ACTIONS = ["left", "right", "center", "close", "none"]


class VLMPolicy:
    name = "vlm_policy"
    is_policy = True
    needs_gpu = True

    def __init__(self, vlm):
        self.vlm = vlm

    def prompt(self, query):
        return (f"This is the camera view of a small drone searching for the {query} (the fruit). "
                f"Where is the {query} in the image? Answer with exactly one word: "
                f"left, right, center, close (if it is large and near), or none (if not visible).")

    def decide(self, rgb, query):
        ans = self.vlm.ask(rgb, self.prompt(query), max_new_tokens=4).lower()
        for a in ACTIONS:
            if a in ans:
                return a
        return "none"

    def detect(self, sim, pose, query):  # unused; keeps the Perception interface
        return []


class PolicyMission:
    """Executes discrete VLM decisions as motion primitives."""

    def __init__(self, time_budget=120.0, **_):
        self.state = "TAKEOFF"
        self.budget = time_budget
        self.reports, self.log = [], []
        self.lost_count = 0
        self.action, self.action_end = None, 0.0
        self.yaw_goal, self.fwd_dir = None, None
        self.none_streak = 0
        self.decisions = []

    def _set(self, s, t):
        if s != self.state:
            self.log.append((round(t, 2), self.state, s))
            self.state = s

    def done(self):
        return self.state in ("FOUND", "NOT_FOUND")

    def want_decision(self, t):
        return self.state == "POLICY" and t >= self.action_end

    def set_action(self, a, t, pose):
        self.decisions.append((round(t, 2), a))
        self.action = a
        if a in ("left", "right"):
            self.yaw_goal = wrap(pose.yaw + (TURN if a == "left" else -TURN))
            self.action_end = t + TURN / YAW_RATE + 0.2
            self.none_streak = 0
        elif a == "center":
            self.fwd_dir = np.array([math.cos(pose.yaw), math.sin(pose.yaw)])
            self.action_end = t + FWD / V_FWD
            self.none_streak = 0
        elif a == "close":
            self._set("FOUND", t)
            self.reports.append((t, "found"))
        else:  # none -> explore: rotate 45 deg; after a full turn, move forward 1 m
            self.none_streak += 1
            if self.none_streak % 9 == 0:
                self.action = "explore_fwd"
                self.fwd_dir = np.array([math.cos(pose.yaw), math.sin(pose.yaw)])
                self.action_end = t + 1.0 / V_FWD
            else:
                self.action = "explore_turn"
                self.yaw_goal = wrap(pose.yaw + math.radians(45))
                self.action_end = t + math.radians(45) / YAW_RATE + 0.2

    def tick(self, t, pose, belief, rays):
        v = np.zeros(3)
        if t > self.budget and not self.done():
            self._set("NOT_FOUND", t)
            self.reports.append((t, "not_found"))
        if self.state == "TAKEOFF":
            v[2] = VZ_MAX
            if pose.pos[2] > FLY_Z - 0.1:
                self._set("POLICY", t)
            return v, 0.0
        v[2] = np.clip(1.2 * (FLY_Z - pose.pos[2]), -VZ_MAX, VZ_MAX)
        if self.done() or t >= self.action_end or self.action is None:
            return v, 0.0
        yr = 0.0
        if self.action in ("left", "right", "explore_turn"):
            yr = float(np.clip(2.0 * wrap(self.yaw_goal - pose.yaw), -YAW_RATE, YAW_RATE))
        elif self.action in ("center", "explore_fwd"):
            v[:2] = V_FWD * self.fwd_dir
        return v, yr
