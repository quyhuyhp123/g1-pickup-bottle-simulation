"""Optional simulation hand closure; body motion stays with GR00T/SONIC."""

import numpy as np


def ready_to_close(sample, y_threshold, x_tolerance, running, bottle_seen):
    """Both world-X alignment and nonnegative world-Y surface clearance must hold."""
    error = sample.get("x_error_m")
    gap = sample.get("y_surface_gap_m")
    return bool(running and bottle_seen and error is not None and gap is not None
                and np.isfinite(error) and np.isfinite(gap)
                and abs(error) <= x_tolerance + 1e-9
                and -1e-9 <= gap <= y_threshold + 1e-9
                and sample.get("bottle_tilt_deg", 180.) < 30.)


class ProximityHandClosure:
    def __init__(self, closed_pose, duration=.3):
        self.closed_pose = np.asarray(closed_pose, dtype=np.float32)
        if (self.closed_pose.shape != (7,) or not np.isfinite(self.closed_pose).all()
                or not np.isfinite(duration) or duration <= 0):
            raise ValueError("Expected a finite seven-joint pose and positive closure duration")
        self.duration = duration
        self.reset()

    def reset(self):
        self.started = None
        self.start_pose = None
        self.trigger_distance = None
        self.trigger_x_error = None

    def activate(self, current_pose, now, distance, x_error=None):
        if self.started is not None:
            return
        self.start_pose = np.asarray(current_pose, dtype=np.float32).copy()
        if self.start_pose.shape != (7,) or not np.isfinite(self.start_pose).all():
            raise ValueError("Invalid current hand pose")
        self.started = now
        self.trigger_distance = distance
        self.trigger_x_error = x_error

    def apply(self, policy_pose, now):
        if self.started is None:
            # In this opt-in mode closure must start at the distance trigger,
            # even when a policy chunk would close the fingers earlier.
            return np.zeros(7, dtype=np.float32), None
        fraction = float(np.clip((now - self.started) / self.duration, 0., 1.))
        return (self.start_pose + fraction * (self.closed_pose - self.start_pose)), fraction
