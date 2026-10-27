"""Open-loop physical replay of raw MuJoCo episodes (no policy or IK).

Use --viewer for interactive playback. Reports describe trajectory matching,
not SONIC compatibility or automatic grasp success.
"""
import argparse
import contextlib
import json
import time
from pathlib import Path

import mujoco
import numpy as np


def replay(episode, viewer=False, speed=1., report=None):
    episode = Path(episode).resolve()
    meta = json.loads((episode / 'meta.json').read_text())
    if meta.get('status') != 'complete':
        raise ValueError('Episode must be complete')
    if speed <= 0:
        raise ValueError('Speed must be positive')
    model = mujoco.MjModel.from_xml_path(str(episode / 'model.xml'))
    if [model.joint(i).name for i in range(model.njnt)] != meta['joints']:
        raise ValueError('Joint ordering differs from metadata')
    if not np.array_equal(model.actuator_trnid, meta['actuator_trnid']):
        raise ValueError('Actuator mapping differs from metadata')
    if not np.isclose(model.opt.timestep, meta['timestep']):
        raise ValueError('Model timestep differs from recording')
    data = mujoco.MjData(model)
    with np.load(episode / 'initial_state.npz', allow_pickle=False) as initial:
        for key in ('qpos', 'qvel', 'act', 'mocap_pos', 'mocap_quat', 'eq_active'):
            getattr(data, key)[:] = initial[key]
        data.time = float(initial['sim_time'])
        mujoco.mj_forward(model, data)
        data.qacc_warmstart[:] = initial['qacc_warmstart']
    bottle = model.joint('red_bottle_free_joint').qposadr[0]
    hinge = model.jnt_qposadr[model.jnt_type == mujoco.mjtJoint.mjJNT_HINGE]
    errors, recorded_z, replay_z = [], [], []
    count = 0
    first_divergence = None
    wall_start = time.monotonic()
    sim_start = float(data.time)
    if viewer:
        from mujoco import viewer as mj_viewer
        window = mj_viewer.launch_passive(model, data)
    else:
        window = contextlib.nullcontext(None)
    with window as view:
        if view:
            view.cam.lookat[:] = [.3, 0., .85]
            view.cam.distance = 2.
        for chunk in sorted(episode.glob('states_*.npz')):
            with np.load(chunk, allow_pickle=False) as z:
                for i, timestamp in enumerate(z['sim_time']):
                    if view and not view.is_running():
                        break
                    if not np.isclose(data.time, timestamp, atol=1e-8, rtol=0):
                        raise ValueError('Missing/non-contiguous physics samples')
                    if z['ctrl'][i].shape != (model.nu,) or not np.isfinite(z['ctrl'][i]).all():
                        raise ValueError('Invalid ctrl')
                    # Compare PRE-step states; never overwrite trajectory with recorded qpos.
                    ref = z['qpos'][i]
                    joint_error = float(np.max(np.abs(data.qpos[hinge] - ref[hinge])))
                    bottle_error = float(np.linalg.norm(data.qpos[bottle:bottle+3] - ref[bottle:bottle+3]))
                    errors.append((float(timestamp), joint_error, bottle_error))
                    recorded_z.append(float(ref[bottle+2]))
                    replay_z.append(float(data.qpos[bottle+2]))
                    if first_divergence is None and (joint_error > .05 or bottle_error > .02):
                        first_divergence = float(timestamp-sim_start)
                    data.ctrl[:] = z['ctrl'][i]
                    data.qfrc_applied[:] = z['qfrc_applied'][i]
                    data.xfrc_applied[:] = z['xfrc_applied'][i]
                    # Recorder called forward before each step; mirror that solver sequence.
                    mujoco.mj_forward(model, data)
                    mujoco.mj_step(model, data)
                    if not np.isfinite(data.qpos).all():
                        raise ValueError('Replay became non-finite')
                    count += 1
                    if view and count % max(1, round(1/(30*model.opt.timestep))) == 0:
                        view.sync()
                    if view:
                        time.sleep(max(0., wall_start+(data.time-sim_start)/speed-time.monotonic()))
                if view and not view.is_running():
                    break
    if not count:
        raise ValueError('No physics samples replayed')
    a = np.asarray(errors)
    result = dict(episode=str(episode), samples_replayed=count, expected_samples=meta['samples'],
        complete=count == meta['samples'], mujoco_version=mujoco.__version__,
        recorded_mujoco_version=meta['mujoco_version'],
        max_joint_error_rad=float(a[:,1].max()), max_bottle_position_error_m=float(a[:,2].max()),
        final_bottle_position_error_m=float(a[-1,2]), first_divergence_s=first_divergence,
        recorded_peak_lift_m=max(recorded_z)-recorded_z[0],
        replay_peak_lift_m=max(replay_z)-replay_z[0],
        trajectory_match=count == meta['samples'] and first_divergence is None,
        thresholds=dict(joint_rad=.05, bottle_position_m=.02),
        sonic_validated=False,
        limitations='Raw v1 does not record per-step equality/mocap changes or every runtime model change. '
                    'Recorded external forces are reapplied open-loop. Matching is not proof of SONIC compatibility.')
    out = Path(report) if report else episode / 'replay_report.json'
    out.write_text(json.dumps(result, indent=2))
    np.savetxt(out.with_suffix('.csv'), a, delimiter=',',
               header='sim_time,max_joint_error_rad,bottle_position_error_m', comments='')
    print(json.dumps(result, indent=2))
    print(f'Report: {out}')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('episode')
    p.add_argument('--viewer', action='store_true')
    p.add_argument('--speed', type=float, default=1.)
    p.add_argument('--report')
    args = p.parse_args()
    replay(args.episode, args.viewer, args.speed, args.report)
