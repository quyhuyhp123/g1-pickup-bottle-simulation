"""Validate raw recorder output and optionally export review MP4; not training conversion."""
import argparse
import json
from pathlib import Path
import cv2
import numpy as np


def inspect(path, video=False, outcome=None):
    path = Path(path)
    meta = json.loads((path / 'meta.json').read_text())
    if meta['status'] != 'complete':
        raise ValueError('Episode incomplete (recording or interrupted); do not train on it')
    n = 0
    last = None
    frames = []
    for file in sorted(path.glob('states_*.npz')):
        with np.load(file, allow_pickle=False) as z:
            t = z['sim_time']
            if not len(t) or not np.isfinite(t).all() or np.any(np.diff(t) <= 0):
                raise ValueError(f'Invalid timestamps: {file}')
            if last is not None and not np.isclose(t[0]-last, meta['timestep']):
                raise ValueError('Discontinuous chunks')
            if len(t)>1 and not np.allclose(np.diff(t), meta['timestep']):
                raise ValueError('Missing physics steps')
            for key in ('qpos', 'qvel', 'ctrl', 'camera_xpos', 'camera_xmat'):
                if len(z[key]) != len(t) or not np.isfinite(z[key]).all():
                    raise ValueError(f'Invalid {key}')
            frames.extend(int(f) for f in z['frame_id'] if f >= 0)
            n += len(t)
            last = t[-1]
    if n == 0 or n != meta['samples'] or frames != list(range(meta['frames'])) or not frames:
        raise ValueError('Sample/frame counts inconsistent or empty')
    writer = None
    try:
        if video:
            writer = cv2.VideoWriter(str(path / 'review.mp4'), cv2.VideoWriter_fourcc(*'mp4v'),
                                     meta['fps_requested'], tuple(meta['image_size']))
            if not writer.isOpened():
                raise RuntimeError('MP4 encoder unavailable')
        for i in frames:
            img = cv2.imread(str(path / 'rgb' / f'{i:06d}.png'))
            if img is None or list(img.shape[1::-1]) != meta['image_size']:
                raise ValueError(f'Missing/invalid image {i}')
            if writer:
                writer.write(img)
    finally:
        if writer:
            writer.release()
    if outcome:
        meta['outcome'] = outcome
        (path / 'meta.json').write_text(json.dumps(meta, indent=2))
    print(f'OK: {n} physics samples, {len(frames)} camera frames. Raw data, NOT SONIC training-ready.')
    return n


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('episode')
    p.add_argument('--video', action='store_true')
    p.add_argument('--outcome', choices=['success', 'failure', 'discard'])
    a = p.parse_args()
    inspect(a.episode, a.video, a.outcome)
