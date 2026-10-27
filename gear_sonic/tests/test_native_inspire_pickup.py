"""Contact-based Inspire pickup/place/repeat regression with controlled perception.

No policy server/detector required. Synthetic RGB-D targets isolate physics;
these tests must not be presented as learned-policy or live-perception success.
"""
from pathlib import Path
from types import SimpleNamespace
import unittest

import mujoco
import numpy as np

from gear_sonic.utils.mujoco_sim.base_sim import DefaultEnv
from gear_sonic.utils.mujoco_sim.configs import SimLoopConfig
from gear_sonic.utils.mujoco_sim.inspire_hand import dex3_observation_from_inspire

ROOT = Path(__file__).resolve().parents[2]
SCENE = ROOT / 'models/g1_inspire_ftp/g1_inspire_ftp_pickup.xml'


class NativeObservationTest(unittest.TestCase):
    def test_projection_is_explicit_finite_and_does_not_modify_input(self):
        measured = np.array([1., .2, .4, .5, .6, .7])
        before = measured.copy()
        for side in ('left', 'right'):
            projected = dex3_observation_from_inspire(measured, side)
            self.assertEqual(projected.shape, (7,))
            self.assertTrue(np.isfinite(projected).all())
        np.testing.assert_array_equal(measured, before)
        with self.assertRaises(ValueError):
            dex3_observation_from_inspire([0.] * 7, 'right')


@unittest.skipUnless(SCENE.exists(), 'Build the native Inspire pickup model first')
class NativeInspirePickupTest(unittest.TestCase):
    def test_pickup_place_home_repeat_and_reset(self):
        for xy, destination in (([.43, -.11], [.45, -.05]),
                                ([.4, -.15], [.42, -.12]),
                                ([.46, -.08], [.43, -.11]),
                                ([.43, -.05], [.45, -.05])):
            with self.subTest(xy=xy, destination=destination):
                config = SimLoopConfig(enable_onscreen=False).load_wbc_yaml()
                config.update(GROUND_START=True, ASSISTED_PICKUP=True, FIXED_PICKUP_BASE=True,
                              NATIVE_INSPIRE=True, NUM_HAND_JOINTS=6, NUM_HAND_MOTORS=0,
                              ROBOT_SCENE=str(SCENE))
                env = DefaultEnv(config)
                env.unitree_bridge = SimpleNamespace(PublishLowState=lambda _: None,
                    joystick=None, low_cmd=None, low_cmd_received=False)
                model, data, pickup = env.mj_model, env.mj_data, env.assisted_pickup
                self.assertEqual(model.nu, 41)
                self.assertEqual(len(pickup.hand), 6)
                self.assertEqual(len(set(env.joint_actuator.values())), 41)
                self.assertNotIn(pickup.bottle, model.eq_obj1id)
                self.assertNotIn(pickup.bottle, model.eq_obj2id)
                env.bottle_placement.reset(model, data, xy)
                for _ in range(100):
                    env.sim_step()
                robot_q = np.r_[model.jnt_qposadr[env.body_joint_index],
                                model.jnt_qposadr[env.left_hand_index], model.jnt_qposadr[env.right_hand_index]]
                np.testing.assert_array_equal(data.qpos[robot_q], env.initial_qpos[robot_q])
                env.begin_control_transition()

                def grasp(centre_xy):
                    pickup.start(data)
                    for step in range(6000):
                        pickup.update(data, {'status': 'detected',
                            'world_point_m': [centre_xy[0]-.025, centre_xy[1], .85],
                            'camera_position_world_m': [0., centre_xy[1], 1.2],
                            'capture_monotonic': step // 20})
                        env.sim_step()
                        if pickup.stage in ('success', 'failed'):
                            break
                    self.assertTrue(pickup.success, pickup.snapshot())
                    self.assertGreater(pickup.min_hold_lift, .12)
                    np.testing.assert_array_equal(data.xfrc_applied[pickup.bottle], 0.)

                grasp(xy)
                # Users may leave a lifted bottle waiting before pressing Lower.
                for _ in range(12000):  # 60 simulated seconds at 200 Hz
                    pickup.update(data, {})
                    env.sim_step()
                    if pickup.stage == 'failed':
                        break
                self.assertEqual(pickup.stage, 'success', pickup.snapshot())
                self.assertGreater(data.xpos[pickup.bottle, 2] - pickup.centre_height, .12)
                self.assertTrue(pickup.lower_to_table(data, destination))
                for _ in range(9000):
                    pickup.update(data, {})
                    env.sim_step()
                    if pickup.stage in ('complete', 'failed'):
                        break
                self.assertEqual(pickup.stage, 'complete', pickup.snapshot())
                self.assertTrue(pickup.placed)
                self.assertTrue(pickup.table_support(data))
                self.assertLess(np.linalg.norm(data.xpos[pickup.bottle, :2]-destination), .025)
                self.assertGreater(data.xmat[pickup.bottle].reshape(3, 3)[2, 2], .95)
                np.testing.assert_allclose(data.qpos[pickup.arm_q], pickup.home_arm_q, atol=.05)
                # A fresh detector would observe the settled bottle, not the requested XY.
                grasp(data.xpos[pickup.bottle, :2].copy())
                self.assertFalse(any(w.number for w in data.warning))
                # Inject loss of the held object: Lower must no longer be enabled.
                env.bottle_placement.reset(model, data, xy)
                for _ in range(100):
                    pickup.update(data, {})
                    env.sim_step()
                self.assertEqual(pickup.stage, 'failed')
                self.assertFalse(pickup.success)
                self.assertFalse(pickup.lower_to_table(data, destination))
                env.reset()
                self.assertTrue(env.standby)
                self.assertFalse(pickup.active)
                self.assertEqual(pickup.stage, 'idle')
                np.testing.assert_array_equal(data.qvel, 0.)
                np.testing.assert_allclose(env.coordinate_snapshot()['bottle'], [*xy, .801])


if __name__ == '__main__':
    unittest.main()
