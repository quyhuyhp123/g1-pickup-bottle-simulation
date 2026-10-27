"""Preview native Inspire FTP hands on G1 (simulation only, no DDS/policy server).

Space toggles both hands; L/R toggle a side; Backspace restores the scene.
Position sliders in MuJoCo's Control panel expose all 41 active joints.
"""
import argparse
from pathlib import Path
import time
import threading

import mujoco
import mujoco.viewer
import numpy as np

from gear_sonic.scripts.prepare_inspire_ftp_sim import HAND_NAMES, ROOT


def initialize(model, data):
    mujoco.mj_resetData(model, data)
    home = {'left_shoulder_pitch_joint': -.3, 'right_shoulder_pitch_joint': -.3,
            'left_elbow_joint': 1.1, 'right_elbow_joint': 1.1}
    for name, value in home.items():
        data.qpos[model.joint(name).qposadr[0]] = value
    for i in range(model.nu):
        joint = model.actuator_trnid[i, 0]
        data.ctrl[i] = data.qpos[model.jnt_qposadr[joint]]
    mujoco.mj_forward(model, data)


def hand_actuators(model, side):
    return np.array([model.actuator(side+'_'+name+'_joint_act').id for name in HAND_NAMES])


def main(args):
    if not args.scene.exists():
        raise SystemExit('Run .venv_sim/bin/python gear_sonic/scripts/prepare_inspire_ftp_sim.py first.')
    model = mujoco.MjModel.from_xml_path(str(args.scene))
    data = mujoco.MjData(model)
    initialize(model, data)
    closed = {'left': False, 'right': False}
    lock = threading.Lock()
    reset = threading.Event()
    def key(code):
        with lock:
            if code == 32:
                closed['left'] = closed['right'] = not closed['right']
            elif code in (ord('L'), ord('R')):
                side = 'left' if code == ord('L') else 'right'
                closed[side] = not closed[side]
            elif code == 259:
                reset.set()
    print('Native Inspire FTP preview: SPACE both hands; L/R one hand; Backspace reset. Pelvis fixed.')
    print('This preview does not connect to GR00T/SONIC or robot hardware.')
    with mujoco.viewer.launch_passive(model, data, key_callback=key) as viewer:
        viewer.cam.lookat[:] = [.1, 0, .9]
        viewer.cam.distance = 2.
        viewer.cam.azimuth = 130
        viewer.cam.elevation = -15
        last_view = 0.
        while viewer.is_running():
            start = time.monotonic()
            with lock:
                if reset.is_set():
                    initialize(model, data)
                    closed = {'left': False, 'right': False}
                    reset.clear()
                for side in closed:
                    indices = hand_actuators(model, side)
                    target = model.actuator_ctrlrange[indices, 1] * (.85 if closed[side] else 0.)
                    data.ctrl[indices] += np.clip(target-data.ctrl[indices], -.0008, .0008)
            mujoco.mj_step(model, data)
            if start-last_view >= 1/60:
                viewer.sync()
                last_view = start
            time.sleep(max(0., model.opt.timestep-(time.monotonic()-start)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene', type=Path, default=ROOT/'models/g1_inspire_ftp/g1_inspire_ftp.xml')
    main(parser.parse_args())
