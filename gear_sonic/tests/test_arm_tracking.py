"""Arm bias feedforward must improve physical tracking without changing targets."""

from types import SimpleNamespace
import unittest

import mujoco
import numpy as np

from gear_sonic.scripts.run_blue_bottle_pickup import load_anchored_scene
from gear_sonic.utils.mujoco_sim.base_sim import DefaultEnv


class ArmTrackingTest(unittest.TestCase):
    def hold_pose(self, compensate):
        # Fix the pelvis only in this isolated tracking test, so balance and
        # foot movement cannot mask the arm servo error. Production stays free.
        model = load_anchored_scene()
        data = mujoco.MjData(model)
        body = np.array([j for j in range(model.njnt) if any(
            part in model.joint(j).name for part in ("hip", "knee", "ankle", "waist", "shoulder", "elbow", "wrist"))])
        arm = np.array([i for i, j in enumerate(body) if any(
            part in model.joint(int(j)).name for part in ("shoulder", "elbow", "wrist"))])
        q_target = data.qpos[model.jnt_qposadr[body]].copy()
        for name, value in (("right_shoulder_pitch_joint", -.1), ("right_elbow_joint", -.2)):
            q_target[np.flatnonzero(body == model.joint(name).id)[0]] = value
        arm_kp = .003609725 * (2 * np.pi * 10) ** 2
        arm_kd = 4 * .003609725 * 2 * np.pi * 10
        commands = [SimpleNamespace(q=q, dq=0., tau=0., kp=arm_kp if i in arm else 100.,
                                    kd=arm_kd if i in arm else 4.) for i, q in enumerate(q_target)]
        env = DefaultEnv.__new__(DefaultEnv)
        env.config = {"ARM_GRAVITY_COMPENSATION": compensate}
        env.standby = False
        env.num_body_dof = len(body)
        env.body_joint_index = body
        env.arm_motor_indices = arm
        env.arm_dof_addresses = model.jnt_dofadr[body[arm]]
        env.qpos_offset, env.qvel_offset = 7, 6
        env.mj_model, env.mj_data = model, data
        env.unitree_bridge = SimpleNamespace(low_cmd_received=True, use_sensor=False,
            num_body_motor=len(body), low_cmd=SimpleNamespace(motor_cmd=commands))
        target = mujoco.MjData(model)
        site = model.site("right_hand_grasp_center").id
        errors = []
        mujoco.mj_forward(model, data)
        for frame in range(3000):
            data.ctrl[:] = 0.
            data.ctrl[body - 1] = env.compute_body_torques()
            data.ctrl[:] = np.clip(data.ctrl, model.actuator_ctrlrange[:, 0], model.actuator_ctrlrange[:, 1])
            mujoco.mj_step(model, data)
            if frame >= 2700 and frame % 10 == 0:
                target.qpos[:] = data.qpos
                # Measure the arm servo at the same actual waist/base pose;
                # gravity compensation intentionally does not alter the waist.
                target.qpos[model.jnt_qposadr[body[arm]]] = q_target[arm]
                mujoco.mj_forward(model, target)
                errors.append(np.linalg.norm(target.site_xpos[site] - data.site_xpos[site]))
        np.testing.assert_array_equal([c.q for c in commands], q_target)
        return float(np.mean(errors))

    def test_arm_feedforward_reduces_sag_for_identical_sonic_commands(self):
        baseline = self.hold_pose(False)
        compensated = self.hold_pose(True)
        self.assertGreater(baseline, .08)
        self.assertLess(compensated, .025)
        self.assertLess(compensated, baseline * .25)


if __name__ == "__main__":
    unittest.main()
