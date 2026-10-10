"""Physical, assisted Dex3 bottle pickup in MuJoCo.

This is an IK grasp primitive using simulator ground truth, not GR00T inference.
The pelvis is anchored to the world for this manipulation test. The bottle
remains a free body: no weld, teleport, or external lifting force is applied.

Run from repository root with .venv_sim/bin/python. Use --headless for validation.
"""
import argparse
import json
from pathlib import Path
import tempfile
import time
import xml.etree.ElementTree as ET

import mujoco
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[2]
SCENE = ROOT / 'gear_sonic/data/robot_model/model_data/g1/scene_43dof.xml'


def load_anchored_scene(scene=SCENE):
    scene = Path(scene)
    original = mujoco.MjModel.from_xml_path(str(scene))
    with tempfile.TemporaryDirectory() as directory:
        expanded = Path(directory) / 'scene.xml'
        mujoco.mj_saveLastXML(str(expanded), original)
        tree = ET.parse(expanded)
        root = tree.getroot()
        root.find('compiler').set('meshdir', str(scene.parent / 'meshes'))
        equality = root.find('equality')
        if equality is None:
            equality = ET.SubElement(root, 'equality')
        ET.SubElement(equality, 'weld', body1='pelvis', solref='.002 1')
        model = mujoco.MjModel.from_xml_string(ET.tostring(root, encoding='unicode'))
    model.opt.timestep = .001
    return model


class BottlePickup:
    def __init__(self, offset=(0., 0.)):
        self.model = m = load_anchored_scene()
        self.data = d = mujoco.MjData(m)
        self.arm = [m.joint('waist_pitch_joint').id] + [m.joint('right_' + name + '_joint').id for name in
            ['shoulder_pitch', 'shoulder_roll', 'shoulder_yaw', 'elbow', 'wrist_roll', 'wrist_pitch', 'wrist_yaw']]
        self.arm_adr = m.jnt_qposadr[self.arm]
        self.hand = [m.joint('right_hand_' + name + '_joint').id for name in
                     ['thumb_0', 'thumb_1', 'thumb_2', 'middle_0', 'middle_1', 'index_0', 'index_1']]
        self.hand_adr = m.jnt_qposadr[self.hand]
        self.closed = np.array([0., -.7, -.7, 1., 1.5, 1., 1.5])
        self.wrist = m.body('right_wrist_yaw_link').id
        self.bottle = m.body('red_bottle').id
        bottle_adr = m.joint('red_bottle_free_joint').qposadr[0]
        d.qpos[bottle_adr:bottle_adr + 2] += offset
        mujoco.mj_forward(m, d)
        self.initial_bottle_z = float(d.xpos[self.bottle, 2])
        # Dex3 grasp center lies about 12 cm forward and 5 cm left of wrist.
        # Grasp the straight cylindrical section, 4 cm above the body origin.
        self.goal = d.xpos[self.bottle].copy() + np.array([-.12, -.05, .04])
        guess = np.array([.3, 0., -.2, 0., .8, 0., 0., 0.])
        self.grasp_q = self.ik(self.goal, guess)
        pre = self.ik(self.goal + np.array([-.10, 0., .08]), self.grasp_q)
        d.qpos[self.arm_adr] = pre
        self.target = d.qpos.copy()
        act_joints = m.actuator_trnid[:, 0]
        self.act_q = m.jnt_qposadr[act_joints]
        self.act_v = m.jnt_dofadr[act_joints]
        hand_mask = np.array(['hand_' in m.joint(int(j)).name for j in act_joints])
        self.kp = np.where(hand_mask, 8., 100.)
        self.kd = np.where(hand_mask, .2, 4.)
        self.trace = []

    def ik(self, position, guess):
        m = self.model
        scratch = mujoco.MjData(m)
        scratch.qpos[:] = self.data.qpos
        lower = m.jnt_range[self.arm, 0] + .001
        upper = m.jnt_range[self.arm, 1] - .001
        def residual(q):
            scratch.qpos[self.arm_adr] = q
            mujoco.mj_forward(m, scratch)
            rotation_error = Rotation.from_matrix(scratch.xmat[self.wrist].reshape(3, 3).T).as_rotvec()
            return np.r_[scratch.xpos[self.wrist] - position, .1 * rotation_error]
        solution = least_squares(residual, np.clip(guess, lower, upper), bounds=(lower, upper),
                                 max_nfev=150, ftol=1e-8, xtol=1e-8, gtol=1e-8)
        if np.linalg.norm(residual(solution.x)) > .005:
            raise RuntimeError('Bottle is outside this assisted grasp primitive workspace')
        return solution.x

    def hand_contacts(self):
        m, d = self.model, self.data
        fingers = set()
        for c in d.contact:
            a, b = int(m.geom_bodyid[c.geom1]), int(m.geom_bodyid[c.geom2])
            if a == self.bottle or b == self.bottle:
                other = b if a == self.bottle else a
                name = m.body(other).name
                if name.startswith('right_hand_'):
                    fingers.add(name)
        return sorted(fingers)

    def step(self):
        m, d = self.model, self.data
        mujoco.mj_forward(m, d)
        torque = self.kp * (self.target[self.act_q] - d.qpos[self.act_q])
        torque -= self.kd * d.qvel[self.act_v]
        torque += d.qfrc_bias[self.act_v]
        d.ctrl[:] = np.clip(torque, m.actuator_ctrlrange[:, 0], m.actuator_ctrlrange[:, 1])
        mujoco.mj_step(m, d)

    def run(self, frame_callback=None):
        m, d = self.model, self.data
        for stage, seconds in [('approach', 2.), ('close', 2.5), ('lift', 2.), ('hold', 3.)]:
            start = self.target[self.arm_adr].copy()
            end = self.grasp_q if stage == 'approach' else start
            if stage == 'lift':
                end = self.ik(self.goal + np.array([0., 0., .18]), self.grasp_q)
            count = int(seconds / m.opt.timestep)
            for index in range(count):
                fraction = min((index + 1) / (count * .75), 1.)
                fraction = fraction * fraction * (3 - 2 * fraction)
                self.target[self.arm_adr] = start + fraction * (end - start)
                if stage == 'close':
                    self.target[self.hand_adr] = self.closed * fraction
                self.step()
                if index % 40 == 0:
                    mujoco.mj_forward(m, d)
                    sample = {'stage': stage, 'time_s': float(d.time),
                              'bottle_world_m': d.xpos[self.bottle].tolist(),
                              'wrist_world_m': d.xpos[self.wrist].tolist(),
                              'hand_contacts': self.hand_contacts()}
                    self.trace.append(sample)
                    if frame_callback:
                        frame_callback(stage)
            print(stage, 'bottle height:', round(float(d.xpos[self.bottle, 2]), 4), flush=True)
        holds = [s for s in self.trace if s['stage'] == 'hold']
        minimum_lift = min(s['bottle_world_m'][2] for s in holds) - self.initial_bottle_z
        opposed = all(any('thumb' in n for n in s['hand_contacts']) and
                      any('index' in n or 'middle' in n for n in s['hand_contacts']) for s in holds)
        return {'success': bool(minimum_lift > .12 and opposed),
                'mode': 'assisted IK; pelvis anchored; physical free-body grasp',
                'minimum_lift_during_hold_m': minimum_lift, 'hold_duration_s': 3.,
                'opposed_finger_contacts_throughout_hold': opposed, 'trace': self.trace}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--record', action='store_true', help='Save third-person and ego videos')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'outputs/blue_bottle_pickup')
    parser.add_argument('--bottle-offset', nargs=2, type=float, default=[0., 0.], metavar=('X', 'Y'))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    pickup = BottlePickup(args.bottle_offset)
    m, d = pickup.model, pickup.data
    viewer = renderer = None
    writers = {}
    if not args.headless:
        import mujoco.viewer as mjviewer
        viewer = mjviewer.launch_passive(m, d)
        viewer.cam.azimuth = 130
        viewer.cam.elevation = -20
        viewer.cam.distance = 2.2
        viewer.cam.lookat[:] = [.25, 0., .8]
    camera = mujoco.MjvCamera()
    camera.azimuth, camera.elevation, camera.distance = 130, -20, 2.2
    camera.lookat[:] = [.25, 0., .8]
    if args.record:
        import cv2
        renderer = mujoco.Renderer(m, height=480, width=640)
        for name in ['third_person', 'ego_view']:
            writers[name] = cv2.VideoWriter(str(args.output_dir / (name + '.mp4')),
                                            cv2.VideoWriter_fourcc(*'mp4v'), 25., (640, 480))
            if not writers[name].isOpened():
                raise RuntimeError('Video writer could not open ' + name)
    def frame(stage):
        if viewer:
            if not viewer.is_running():
                raise KeyboardInterrupt
            viewer.sync()
            time.sleep(.04)
        if renderer:
            for name, cam in [('third_person', camera), ('ego_view', 'head_camera')]:
                renderer.update_scene(d, camera=cam)
                rgb = renderer.render()
                writers[name].write(rgb[:, :, ::-1])
                if stage == 'hold':
                    cv2.imwrite(str(args.output_dir / (name + '_held.jpg')), rgb[:, :, ::-1])
    try:
        report = pickup.run(frame)
        (args.output_dir / 'report.json').write_text(json.dumps(report, indent=2))
        print(json.dumps({k: v for k, v in report.items() if k != 'trace'}, indent=2))
        if not report['success']:
            raise SystemExit('Grasp failed physical lift/contact checks')
        if viewer:
            print('Pickup succeeded. Close the viewer to finish.', flush=True)
            while viewer.is_running():
                for _ in range(40):
                    pickup.step()
                viewer.sync()
                time.sleep(.04)
    finally:
        if viewer:
            viewer.close()
        if renderer:
            renderer.close()
        for writer in writers.values():
            writer.release()


if __name__ == '__main__':
    main()
