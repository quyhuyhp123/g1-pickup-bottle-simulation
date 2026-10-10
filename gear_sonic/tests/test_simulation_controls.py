"""Verify scene edits, ground standby, and reset sequencing without a display."""

from pathlib import Path
from types import SimpleNamespace
import time
import unittest

import mujoco
import numpy as np

from gear_sonic.utils.mujoco_sim.base_sim import DefaultEnv
from gear_sonic.utils.mujoco_sim.configs import SimLoopConfig
from gear_sonic.utils.mujoco_sim.object_reset import BottlePlacement
from gear_sonic.utils.mujoco_sim.interactive_controls import InteractiveSimulationControls


SCENE = Path(__file__).resolve().parents[2] / "gear_sonic/data/robot_model/model_data/g1/scene_43dof.xml"


class BottlePlacementTest(unittest.TestCase):
    def setUp(self):
        self.model = mujoco.MjModel.from_xml_path(str(SCENE))
        self.data = mujoco.MjData(self.model)
        mujoco.mj_forward(self.model, self.data)
        self.placement = BottlePlacement(self.model, self.data)

    def test_place_and_reset_preserve_robot_and_time(self):
        self.data.time = 123.
        self.data.qpos[0] = .02
        self.data.qvel[0] = .2
        robot_q = self.data.qpos[:self.placement.address].copy()
        self.placement.reset(self.model, self.data, [.4, -.15])
        self.data.qpos[self.placement.address + 3:self.placement.address + 7] = [0, 1, 0, 0]
        dof = self.model.joint("red_bottle_free_joint").dofadr[0]
        self.data.qvel[dof:dof + 6] = 1
        self.placement.reset(self.model, self.data)
        np.testing.assert_array_equal(self.data.qpos[:self.placement.address], robot_q)
        self.assertEqual(self.data.time, 123.)
        self.assertEqual(self.data.qvel[0], .2)
        np.testing.assert_array_equal(self.data.qvel[dof:dof + 6], 0)
        np.testing.assert_allclose(self.data.qpos[self.placement.address:self.placement.address + 7],
                                   [.4, -.15, .801, 1, 0, 0, 0])

    def test_invalid_xy_does_not_move_scene(self):
        original = self.data.qpos.copy()
        for xy in ([np.nan, 0], [np.inf, 0], [.1, 0], [.5, .5], [1, 2, 3]):
            with self.assertRaises(ValueError):
                self.placement.reset(self.model, self.data, xy)
            np.testing.assert_array_equal(self.data.qpos, original)
        np.testing.assert_array_equal(self.placement.xy, [.43, -.11])


class GroundStandbyTest(unittest.TestCase):
    def setUp(self):
        config = SimLoopConfig(enable_onscreen=False).load_wbc_yaml()
        config["GROUND_START"] = True
        self.env = DefaultEnv(config, onscreen=False)
        self.env.unitree_bridge = SimpleNamespace(PublishLowState=lambda obs: None, joystick=None)

    def test_idle_robot_has_floor_contacts_without_lifting(self):
        for _ in range(1000):
            self.env.sim_step()
        self.assertTrue(self.env.standby)
        self.assertLess(abs(self.env.mj_data.qpos[2] - .793), .02)
        self.assertLess(np.linalg.norm(self.env.mj_data.qvel[:6]), .02)
        model, data = self.env.mj_model, self.env.mj_data
        floor = model.geom("floor").id
        foot_contacts = 0
        for contact in data.contact:
            other = contact.geom2 if contact.geom1 == floor else contact.geom1 if contact.geom2 == floor else None
            if other is not None and "ankle" in model.body(int(model.geom_bodyid[other])).name:
                foot_contacts += 1
        self.assertGreater(foot_contacts, 0)
        positions, velocities, _ = self.env._idle_robot_indices
        np.testing.assert_array_equal(data.qpos[positions], self.env.initial_qpos[positions])
        np.testing.assert_array_equal(data.qvel[velocities], 0.)
        self.assertLess(data.xpos[model.body('red_bottle').id, 2], .801)

    def test_lock_ignores_robot_disturbance_and_preserves_bottle_velocity(self):
        env = self.env
        env.hold_initial_robot_pose()
        positions, velocities, _ = env._idle_robot_indices
        env.mj_data.qpos[0] = .3
        env.mj_data.qvel[velocities] = 2.
        bottle_v = int(env.mj_model.joint('red_bottle_free_joint').dofadr[0])
        env.mj_data.qvel[bottle_v] = .1
        env.hold_initial_robot_pose()
        np.testing.assert_array_equal(env.mj_data.qpos[positions], env.initial_qpos[positions])
        np.testing.assert_array_equal(env.mj_data.qvel[velocities], 0.)
        self.assertEqual(env.mj_data.qvel[bottle_v], .1)
        env.begin_control_transition()
        self.assertFalse(env.standby)
        env.mj_data.qpos[0] = .2
        env.hold_initial_robot_pose()
        self.assertEqual(env.mj_data.qpos[0], .2)

    def test_startup_torque_transfer_has_smooth_endpoints_and_reset_clears_it(self):
        env = self.env
        env.begin_control_transition()
        body, hands = np.full(29, 4.), np.full(14, 2.)
        initial, _ = env.blend_startup_torques(body, hands)
        env.mj_data.time = 1.
        middle, _ = env.blend_startup_torques(body, hands)
        np.testing.assert_allclose(middle, .5 * (initial + body))
        env.mj_data.time = 2.
        final, fingers = env.blend_startup_torques(body, hands)
        np.testing.assert_array_equal(final, body)
        np.testing.assert_array_equal(fingers, hands)
        self.assertIsNone(env._control_transition_started)
        env.begin_control_transition()
        env.reset()
        self.assertIsNone(env._control_transition_started)
        self.assertTrue(env.standby)

    def test_robot_reset_restores_ground_and_selected_bottle(self):
        self.env.bottle_placement.reset(self.env.mj_model, self.env.mj_data, [.4, -.15])
        self.env.standby = False
        self.env.release_ground_support()
        self.env.mj_data.qpos[:3] = [1, 1, .3]
        self.env.mj_data.qvel[:] = 3
        self.env.reset()
        self.assertTrue(self.env.standby)
        self.assertTrue(self.env.elastic_band.enable)
        np.testing.assert_array_equal(self.env.mj_data.qpos[:7], self.env.mj_model.qpos0[:7])
        np.testing.assert_array_equal(self.env.mj_data.qvel, 0)
        np.testing.assert_allclose(self.env.coordinate_snapshot()["bottle"], [.4, -.15, .801])

    def test_initial_bottle_xy_is_used_by_reset_and_panel_state(self):
        config = SimLoopConfig(enable_onscreen=False).load_wbc_yaml()
        config.update(GROUND_START=True, BOTTLE_XY=(.4, -.15))
        env = DefaultEnv(config, onscreen=False)
        np.testing.assert_allclose(env.bottle_placement.xy, [.4, -.15])
        np.testing.assert_allclose(env.coordinate_snapshot()['bottle'], [.4, -.15, .801])
        env.reset()
        np.testing.assert_allclose(env.coordinate_snapshot()['bottle'], [.4, -.15, .801])

    def test_start_after_complete_restarts_pickup_without_resetting_scene(self):
        from unittest.mock import Mock
        pickup = SimpleNamespace(active=True, stage='complete', start=Mock())
        self.env.assisted_pickup = pickup
        controls = InteractiveSimulationControls.__new__(InteractiveSimulationControls)
        controls.env = self.env
        controls.phase = 'running'
        controls.pending = None
        controls.client_seen = time.monotonic()
        controls.detector_result = {'status': 'detected'}
        self.env.bottle_placement.reset(self.env.mj_model, self.env.mj_data, [.45, -.08])
        before = self.env.mj_data.qpos.copy()
        self.assertTrue(controls.can_repeat_pickup())
        controls.handle({'command': 'start'})
        pickup.start.assert_called_once_with(self.env.mj_data)
        np.testing.assert_array_equal(self.env.mj_data.qpos, before)
        self.assertEqual(controls.phase, 'running')
        self.assertIsNone(controls.detector_result)
        self.assertFalse(controls.bottle_seen)
        pickup.stage = 'detecting'
        self.assertFalse(controls.can_repeat_pickup())
        controls.handle({'command': 'start'})
        self.assertEqual(pickup.start.call_count, 1)

    def test_reset_waits_for_policy_ack_and_ignores_old_ack(self):
        messages = []
        class Channel:
            def send(self, message):
                messages.append(message)
                return True
            def receive(self):
                return acknowledgements.pop(0) if acknowledgements else None
        controls = InteractiveSimulationControls.__new__(InteractiveSimulationControls)
        controls.env = self.env
        controls.channel = Channel()
        controls.controller_state = SimpleNamespace(get_msg=lambda: None)
        controls.controller_seen = 0.
        controls.client_seen = time.monotonic()
        controls.client_status = {"paused": False}
        controls.pending = None
        controls.serial = 0
        controls.phase = "running"
        controls.phase_since = time.monotonic()
        controls.error = ""
        controls.panel = None
        controls.detector_socket = None
        controls.detector_result = None
        controls.last_ui_update = time.monotonic()
        self.env.mj_data.qpos[0] = .12
        controls.handle({"command": "reset"})
        self.assertEqual(controls.phase, "resetting")
        self.assertEqual(self.env.mj_data.qpos[0], .12)
        self.assertEqual(messages[-1]["command"], "pause")
        acknowledgements = [{"type": "ack", "id": 0, "ok": True}]
        controls.poll()
        self.assertEqual(self.env.mj_data.qpos[0], .12)
        acknowledgements.append({"type": "ack", "id": 1, "ok": True})
        controls.poll()
        self.assertEqual(controls.phase, "idle")
        self.assertEqual(self.env.mj_data.qpos[0], 0.)
        # Reset must also supersede a Start still waiting for its prepare ACK.
        controls.pending = ({'command': 'prepare', 'id': 99}, time.monotonic())
        controls.phase = 'preparing'
        self.env.standby = False
        controls.handle({'command': 'reset'})
        self.assertTrue(self.env.standby)
        self.assertEqual(controls.phase, 'resetting')
        self.assertEqual(messages[-1]['command'], 'pause')
        acknowledgements.extend([{'type': 'ack', 'id': 99, 'ok': True},
                                 {'type': 'ack', 'id': messages[-1]['id'], 'ok': True}])
        controls.poll()
        self.assertEqual(controls.phase, 'idle')


if __name__ == "__main__":
    unittest.main()
