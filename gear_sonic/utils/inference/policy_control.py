"""Select model actions without changing their motion token or grasp timing."""

import numpy as np


def policy_step_at(now, origin, rate, horizon):
    """Select a step by elapsed time, not by the number of publisher iterations."""
    if rate <= 0 or horizon <= 0 or not np.isfinite([now, origin, rate]).all():
        raise ValueError('Invalid policy playback clock')
    return min(max(int(np.floor((now - origin) * rate + 1e-8)), 0), horizon - 1)


def policy_chunk_needs_refresh(now, origin, rate, horizon, inference_latency):
    """Request a replacement before the current trajectory runs out.

    Include two publisher periods as scheduling margin. The inference latency
    is measured from request to reply; camera age is already in the origin.
    """
    return now - origin >= horizon / rate - max(inference_latency, 0.) - 2. / rate


def policy_action_step(action, index):
    """Validate and copy one synchronized step from a server action chunk.

    Both supported key layouts are accepted. Different horizons, extra batch
    members and nonfinite commands are errors, rather than silently mixing steps.
    Hand values here remain in the checkpoint's action convention.
    """
    arrays = []
    for key, width in (('motion_token', 64), ('left_hand_joints', 7), ('right_hand_joints', 7)):
        value = action.get(key, action.get('action.' + key))
        if value is None:
            raise ValueError(f'Missing policy action {key}')
        value = np.asarray(value, dtype=np.float32)
        if value.ndim == 3 and value.shape[0] == 1:
            value = value[0]
        if value.ndim == 1:
            value = value[None, :]
        if value.ndim != 2 or value.shape[1] != width or not len(value) or not np.isfinite(value).all():
            raise ValueError(f'Invalid {key}: expected finite (1,T,{width}) or (T,{width}), got {value.shape}')
        arrays.append(value)
    if len({len(value) for value in arrays}) != 1:
        raise ValueError('Policy motion and hand horizons do not match')
    step = min(max(int(index), 0), len(arrays[0]) - 1)
    return (*(value[step].copy() for value in arrays), step)


def validate_policy_simulation(config):
    """Reject mixed ownership before opening a simulator or creating fixtures."""
    if not config.get('POLICY_CONTROL', False):
        return
    conflicts = ('ASSISTED_PICKUP', 'FIXED_PICKUP_BASE', 'NATIVE_INSPIRE', 'SIM_GRASP_DISTANCE')
    active = [key for key in conflicts if config.get(key)]
    if active:
        raise ValueError('GR00T/SONIC policy mode cannot enable: ' + ', '.join(active))
