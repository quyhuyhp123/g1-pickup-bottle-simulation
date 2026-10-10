"""Physical grasp regression with controlled RGB-D target inputs, without GUI/server."""

from types import SimpleNamespace
import unittest

import numpy as np

from gear_sonic.utils.mujoco_sim.base_sim import DefaultEnv
from gear_sonic.utils.mujoco_sim.configs import SimLoopConfig


class AssistedPickupTest(unittest.TestCase):
    def test_free_bottle_lifts_with_small_target_changes_and_reset_clears_target(self):
        for xy, offset in (([.43, -.11], [0., .03]), ([.4, -.15], [0., .03]),
                           ([.4007882341, -.1492650940], [0., .03]), ([.46, -.08], [0., .03]),
                           ([.43, -.11], [.02, 0.]), ([.43, -.11], [0., 0.]), ([.43, -.11], [.02, .06]),
                           ([.43, -.08], [.02, .03])):
            with self.subTest(xy=xy):
                config = SimLoopConfig(enable_onscreen=False).load_wbc_yaml()
                config.update(GROUND_START=True, ASSISTED_PICKUP=True, FIXED_PICKUP_BASE=True)
                env = DefaultEnv(config, onscreen=False)
                env.unitree_bridge = SimpleNamespace(PublishLowState=lambda _: None,
                    joystick=None, low_cmd=None, low_cmd_received=False)
                env.bottle_placement.reset(env.mj_model, env.mj_data, xy)
                for _ in range(100):
                    env.sim_step()
                np.testing.assert_allclose(env.coordinate_snapshot()['bottle'][:2], xy, atol=.001)
                env.begin_control_transition()
                pickup = env.assisted_pickup
                pickup.start(env.mj_data)
                for step in range(6000):
                    # Controlled perception input isolates contact/control from
                    # detector uncertainty; separate live trials exercise YOLO.
                    detection = {'status': 'detected', 'world_point_m': [xy[0]-.025, xy[1], .85],
                        'camera_position_world_m': [0., xy[1], 1.2], 'capture_monotonic': step // 20}
                    pickup.update(env.mj_data, detection)
                    env.sim_step()
                    if pickup.stage in ('success', 'failed'):
                        break
                self.assertTrue(pickup.success, pickup.snapshot())
                self.assertGreater(pickup.min_hold_lift, .12)
                self.assertTrue(pickup.hold_contacts)
                np.testing.assert_array_equal(env.mj_data.xfrc_applied[pickup.bottle], 0.)
                self.assertNotIn(pickup.bottle, env.mj_model.eq_obj1id)
                self.assertNotIn(pickup.bottle, env.mj_model.eq_obj2id)
                destination = (np.array(xy) + offset).tolist()
                with self.assertRaises(ValueError):
                    pickup.lower_to_table(env.mj_data, [float('nan'), 0.])
                self.assertEqual(pickup.stage, 'success')
                self.assertTrue(pickup.lower_to_table(env.mj_data, destination))
                self.assertFalse(pickup.lower_to_table(env.mj_data))
                for _ in range(9000):
                    pickup.update(env.mj_data, {})
                    env.sim_step()
                    if pickup.placed:
                        self.assertGreater(env.mj_data.xmat[pickup.bottle].reshape(3, 3)[2, 2], .95)
                    if pickup.stage in ('complete', 'failed'):
                        break
                self.assertTrue(pickup.placed, (pickup.snapshot(), env.mj_data.xpos[pickup.bottle].copy(), env.mj_data.xmat[pickup.bottle].reshape(3,3)[2,2]))
                self.assertEqual(pickup.stage, 'complete', pickup.snapshot())
                np.testing.assert_allclose(env.mj_data.qpos[pickup.arm_q], pickup.home_arm_q, atol=.05)
                self.assertEqual(pickup.fraction, 0.)
                for _ in range(500):
                    pickup.update(env.mj_data, {})
                    env.sim_step()
                self.assertTrue(pickup.table_support(env.mj_data))
                np.testing.assert_allclose(env.mj_data.xpos[pickup.bottle, :2], destination, atol=.025)
                self.assertGreater(env.mj_data.xmat[pickup.bottle].reshape(3, 3)[2, 2], .95)
                # Next Start uses the newly placed bottle, without a scene reset.
                pickup.start(env.mj_data)
                for step in range(6000):
                    detection = {'status': 'detected',
                        'world_point_m': [destination[0]-.025, destination[1], .85],
                        'camera_position_world_m': [0., destination[1], 1.2],
                        'capture_monotonic': step // 20}
                    pickup.update(env.mj_data, detection)
                    env.sim_step()
                    if pickup.stage in ('success', 'failed'):
                        break
                self.assertTrue(pickup.success, pickup.snapshot())
                self.assertGreater(pickup.min_hold_lift, .12)
                env.reset()
                self.assertTrue(env.standby)
                self.assertFalse(pickup.active)
                self.assertIsNone(pickup.target)
                self.assertEqual(pickup.samples, [])
                self.assertEqual(pickup.stage, 'idle')
                np.testing.assert_allclose(env.coordinate_snapshot()['bottle'], [*xy, .801])
                np.testing.assert_array_equal(env.mj_data.qvel, 0.)


if __name__ == '__main__':
    unittest.main()
