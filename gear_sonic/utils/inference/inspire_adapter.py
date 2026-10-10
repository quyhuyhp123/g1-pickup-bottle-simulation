"""Experimental Inspire FTP grip-to-Dex3 adapter for simulation.

Source: https://huggingface.co/datasets/cloudwalk-research/gr00t-g1-grab-bottle-right-hand-v2
The source describes hand vectors whose sum is 0.9 open and 6.0 closed.
The first five channels range 0..1, channel 5 ranges .9..1, and channel 6
is a grip pad. This preserves grip intent, not Inspire finger kinematics.
"""
import numpy as np


def inspire_grip_to_dex3(hand, closed_pose):
    hand = np.asarray(hand, dtype=np.float32)
    if hand.shape[-1] != 7 or not np.isfinite(hand).all():
        raise ValueError("Expected finite Inspire hand vectors with seven channels")
    grip = np.clip(hand[..., :5].mean(axis=-1, keepdims=True), 0.0, 1.0)
    return grip * np.asarray(closed_pose, dtype=np.float32)
