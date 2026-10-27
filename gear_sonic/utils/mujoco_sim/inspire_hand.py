"""Simulation-only compatibility for native FTP hands and the legacy Dex3 policy schema.

The VLA/SONIC transport still expects seven Dex3 angles per hand. This projection
preserves measured flexion approximately; it is NOT a calibrated CloudWalk or
hardware Inspire observation/action mapping. The native assisted controller owns
all six real simulated motors, and never consumes projected Dex3 commands.
"""
import numpy as np


def dex3_observation_from_inspire(joints, side):
    q = np.asarray(joints, dtype=float)
    if q.shape != (6,) or not np.isfinite(q).all() or side not in ('left', 'right'):
        raise ValueError('Expected six finite native Inspire motor angles and a hand side')
    # Native order: thumb opposition, thumb flexion, index, middle, ring, little.
    flex = np.clip(q[1:4] / np.array([.5864, 1.4381, 1.4381]), 0., 1.)
    thumb, index, middle = flex
    right = np.array([0., -.7*thumb, -.7*thumb, middle, 1.5*middle, index, 1.5*index])
    return right if side == 'right' else -right
