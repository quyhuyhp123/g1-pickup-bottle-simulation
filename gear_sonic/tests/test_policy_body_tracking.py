"""SONIC target ownership and optional low-level arm tracking feedforward."""

from types import SimpleNamespace
import unittest
import numpy as np

from gear_sonic.utils.mujoco_sim.base_sim import DefaultEnv
from gear_sonic.utils.mujoco_sim.configs import SimLoopConfig


class PolicyBodyTrackingTest(unittest.TestCase):
    def test_bias_changes_torque_without_changing_sonic_joint_targets(self):
        config=SimLoopConfig(enable_onscreen=False).load_wbc_yaml()
        config.update(POLICY_CONTROL=True,ASSISTED_PICKUP=False,FIXED_PICKUP_BASE=False,
                      SIM_GRASP_DISTANCE=0.,ARM_GRAVITY_COMPENSATION=False,GROUND_START=True)
        env=DefaultEnv(config)
        self.assertIsNone(env.assisted_pickup)
        self.assertEqual(env.mj_model.neq,0)
        joints=env.body_joint_index
        actual=env.mj_data.qpos[env.mj_model.jnt_qposadr[joints]]
        commands=[SimpleNamespace(q=float(q+.05),dq=0.,kp=20.,kd=1.,tau=0.) for q in actual]
        env.unitree_bridge=SimpleNamespace(low_cmd=SimpleNamespace(motor_cmd=commands),
                                          num_body_motor=29,use_sensor=False,low_cmd_received=True)
        env.begin_control_transition()
        targets=np.array([c.q for c in commands])
        no_bias=env.compute_body_torques()
        env.config['ARM_GRAVITY_COMPENSATION']=True
        with_bias=env.compute_body_torques()
        expected=np.zeros(29)
        expected[env.arm_motor_indices]=env.mj_data.qfrc_bias[env.arm_dof_addresses]
        np.testing.assert_allclose(with_bias-no_bias,expected,atol=1e-12)
        np.testing.assert_array_equal([c.q for c in commands],targets)
        self.assertGreater(np.max(np.abs(expected)),.1)


if __name__=='__main__':unittest.main()
