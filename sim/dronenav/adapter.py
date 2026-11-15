"""Simulator-agnostic interface. The navigation pipeline only talks to this class,
so the same code runs in PyBullet, Webots, MuJoCo or PX4 SITL."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class CameraIntrinsics:
    width: int
    height: int
    fx: float
    fy: float
    cx: float
    cy: float
    pitch_deg: float  # camera pitch relative to body (negative = looking down)
    offset: tuple = (0.10, 0.0, 0.0)  # camera position in body frame (x fwd, y left, z up)


@dataclass
class Pose:
    pos: np.ndarray  # world x, y, z (m)
    yaw: float  # rad
    vel: np.ndarray = field(default_factory=lambda: np.zeros(3))
    rot: np.ndarray | None = None  # 3x3 body->world rotation if the sim models roll/pitch (camera not gimballed)


# Horizontal range sensor ring: bearing (rad, body frame, CCW from forward)
RANGE_BEARINGS = np.deg2rad([0, 45, 90, 135, 180, 225, 270, 315])
RANGE_MAX = 4.0


def ring_bearings(n=8):
    """n evenly spaced horizontal range beams (8 = sparse single-zone ToF ring;
    24 ~ multi-zone ToF sensors covering the same circle more densely)."""
    return np.linspace(0, 2 * np.pi, n, endpoint=False)


class SimAdapter:
    """Every simulator implements these methods."""

    name = "base"
    dt_control = 0.05  # 20 Hz setpoint stream

    def reset(self, scenario: dict, seed: int) -> None: ...

    def step(self) -> None:
        """Advance the simulation by dt_control seconds."""

    def time(self) -> float: ...

    def get_rgb(self) -> np.ndarray: ...  # HxWx3 uint8

    def get_depth(self) -> np.ndarray: ...  # HxW float metres (z-depth)

    def get_ranges(self) -> dict: ...  # {"ring": np.array(8), "down": float, "up": float}

    def get_pose(self) -> Pose: ...

    def send_velocity(self, vx: float, vy: float, vz: float, yaw_rate: float) -> None:
        """World-frame velocity setpoint. Must be re-sent every control period,
        otherwise the emulated flight-controller failsafe triggers."""

    def camera(self) -> CameraIntrinsics: ...

    def fc_mode(self) -> str: ...  # "OFFBOARD", "HOVER_FAILSAFE", "LANDING", "LANDED"

    # ---- ground truth, used ONLY by the evaluator and the oracle perception (C0)
    def gt(self) -> dict: ...
