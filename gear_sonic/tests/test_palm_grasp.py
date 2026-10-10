"""Validate a fixed grasp region, COM diagnostics, X/Y gates and hand blending."""

from pathlib import Path
from types import SimpleNamespace
import time
import unittest

import mujoco
import numpy as np

from gear_sonic.utils.inference.proximity_hand import ProximityHandClosure, ready_to_close
from gear_sonic.utils.mujoco_sim.palm_proximity import (
    PalmProximity, cylinder_surface_distance,
)
from gear_sonic.utils.mujoco_sim.hand_alignment import HandGraspAlignment, cylinder_y_surface_gap
from gear_sonic.utils.mujoco_sim.interactive_controls import InteractiveSimulationControls

SCENE = Path(__file__).resolve().parents[2] / "gear_sonic/data/robot_model/model_data/g1/scene_43dof.xml"


class PalmDistanceTest(unittest.TestCase):
    def test_distance_is_from_surface_including_cylinder_ends(self):
        self.assertAlmostEqual(cylinder_surface_distance([.045, 0, 0], .025, .1), .02)
        self.assertAlmostEqual(cylinder_surface_distance([0, 0, .12], .025, .1), .02)
        self.assertAlmostEqual(cylinder_surface_distance([.045, 0, .12], .025, .1), np.sqrt(2) * .02)
        self.assertAlmostEqual(cylinder_surface_distance([0, 0, 0], .025, .1), -.025)

    def test_world_distance_uses_palm_centre_and_bottle_rotation(self):
        model = mujoco.MjModel.from_xml_path(str(SCENE))
        data = mujoco.MjData(model)
        proximity = PalmProximity(model)
        rotation = np.array([[0., -1., 0.], [1., 0., 0.], [0., 0., 1.]])
        bottle_position = np.array([.43, -.11, .801])
        data.geom_xmat[proximity.bottle] = rotation.ravel()
        data.geom_xpos[proximity.bottle] = bottle_position
        data.geom_xpos[proximity.palm] = bottle_position + rotation @ [.045, 0., 0.]
        # A wrist position elsewhere cannot affect this clearance.
        data.xpos[model.body("right_wrist_yaw_link").id] = [3, 4, 5]
        sample = proximity.measure(data)
        self.assertAlmostEqual(sample["palm_surface_distance_m"], .02)
        np.testing.assert_allclose(sample["palm_center_world_m"], [.43, -.065, .801])
        self.assertAlmostEqual(sample["bottle_tilt_deg"], 0.)


class WholeHandAlignmentTest(unittest.TestCase):
    def test_grasp_reference_is_fixed_in_hand_frame_not_com_or_fingertips(self):
        model = mujoco.MjModel.from_xml_path(str(SCENE))
        data = mujoco.MjData(model)
        alignment = HandGraspAlignment(model)
        mujoco.mj_forward(model, data)
        sample = alignment.measure(data)
        rotation = data.xmat[alignment.root].reshape(3, 3)
        expected = data.xpos[alignment.root] + rotation @ [.12, .05, 0.]
        np.testing.assert_allclose(sample["grasp_center_world_m"], expected)
        self.assertGreater(np.linalg.norm(expected - sample["whole_hand_com_world_m"]), .04)
        self.assertEqual(model.site_group[alignment.grasp_site], 5)
        self.assertFalse(mujoco.MjvOption().sitegroup[5], "Marker must be hidden from default policy camera")
        address = model.joint("red_bottle_free_joint").qposadr[0]
        data.qpos[address:address + 3] = [expected[0], expected[1] + .044, .801]
        mujoco.mj_forward(model, data)
        sample = alignment.measure(data)
        self.assertTrue(ready_to_close(sample, .02, .005, True, True))
        com_before = np.asarray(sample["whole_hand_com_world_m"])
        for name in ("right_hand_middle_0_joint", "right_hand_index_0_joint"):
            data.qpos[model.joint(name).qposadr[0]] = 1.
        mujoco.mj_forward(model, data)
        after = alignment.measure(data)
        np.testing.assert_allclose(after["grasp_center_world_m"], expected)
        self.assertGreater(np.linalg.norm(np.asarray(after["whole_hand_com_world_m"]) - com_before), .001)
        self.assertTrue(ready_to_close(after, .02, .005, True, True))
        # Wrist rotation must rotate the same reference rather than a world offset.
        data.qpos[model.joint("right_wrist_yaw_joint").qposadr[0]] = .5
        mujoco.mj_forward(model, data)
        expected = data.xpos[alignment.root] + data.xmat[alignment.root].reshape(3, 3) @ [.12, .05, 0.]
        np.testing.assert_allclose(alignment.measure(data)["grasp_center_world_m"], expected)

    def test_com_includes_palm_and_all_finger_masses_excludes_arm(self):
        model = mujoco.MjModel.from_xml_path(str(SCENE))
        data = mujoco.MjData(model)
        mujoco.mj_forward(model, data)
        alignment = HandGraspAlignment(model)
        expected_bodies = [b for b in range(model.nbody)
                           if model.body(b).name == "right_wrist_yaw_link"
                           or model.body(b).name.startswith("right_hand_")]
        self.assertEqual(set(alignment.bodies), set(expected_bodies))
        self.assertEqual(len(alignment.bodies), 8)
        expected = sum(model.body_mass[b] * data.xipos[b] for b in expected_bodies) / sum(model.body_mass[b] for b in expected_bodies)
        before = alignment.measure(data)["whole_hand_com_world_m"]
        np.testing.assert_allclose(before, expected)
        np.testing.assert_allclose(before, data.subtree_com[alignment.root])
        # Moving an arm's inertial position cannot be mistaken for hand COM.
        data.xipos[model.body("right_elbow_link").id] = [100, 100, 100]
        np.testing.assert_allclose(alignment.measure(data)["whole_hand_com_world_m"], expected)
        # Bending a finger moves the whole-hand COM while palm geometry stays fixed.
        palm = PalmProximity(model)
        palm_before = data.geom_xpos[palm.palm].copy()
        for name in ("right_hand_middle_0_joint", "right_hand_index_0_joint"):
            data.qpos[model.joint(name).qposadr[0]] = 1.
        mujoco.mj_forward(model, data)
        np.testing.assert_allclose(data.geom_xpos[palm.palm], palm_before)
        self.assertGreater(np.linalg.norm(np.asarray(alignment.measure(data)["whole_hand_com_world_m"]) - before), .001)

    def test_y_gap_uses_world_y_surface_and_actual_bottle_profile(self):
        centre = np.array([.43, -.11, .801])
        rotation = np.eye(3)
        gap = lambda point: cylinder_y_surface_gap(point, centre, rotation, .025, .1)
        self.assertAlmostEqual(gap([.43, -.155, .801]), .02)
        self.assertAlmostEqual(gap([.43, -.065, .801]), .02)
        self.assertAlmostEqual(gap([.434, -.155, .801]), .045 - np.sqrt(.025 ** 2 - .004 ** 2))
        self.assertIsNone(gap([.46, -.155, .801]))
        self.assertIsNone(gap([.43, -.155, 1.]))
        self.assertLess(gap(centre), 0.)
        angle = np.pi / 6
        tilted = np.array([[1., 0., 0.], [0., np.cos(angle), -np.sin(angle)], [0., np.sin(angle), np.cos(angle)]])
        self.assertAlmostEqual(cylinder_y_surface_gap([.43, -.155, .801], centre, tilted, .025, .1), .045 - .025 / np.cos(angle))

    def test_both_x_and_y_must_match_with_detection_and_upright_bottle(self):
        sample = {"x_error_m": .004, "y_surface_gap_m": .019, "bottle_tilt_deg": 0.}
        self.assertTrue(ready_to_close(sample, .02, .005, True, True))
        self.assertTrue(ready_to_close({**sample, "x_error_m": -.005, "y_surface_gap_m": .02}, .02, .005, True, True))
        self.assertFalse(ready_to_close(sample, .02, .005, False, True))
        self.assertFalse(ready_to_close(sample, .02, .005, True, False))
        for fields in ({"x_error_m": .0051}, {"x_error_m": np.nan}, {"y_surface_gap_m": .0201},
                       {"y_surface_gap_m": -.001}, {"y_surface_gap_m": None}, {"bottle_tilt_deg": 31.},
                       {"y_surface_gap_m": np.nan}, {"x_error_m": .1, "palm_surface_distance_m": .001}):
            self.assertFalse(ready_to_close({**sample, **fields}, .02, .005, True, True))


class HandClosureTest(unittest.TestCase):
    def test_smooth_close_hold_and_reset(self):
        closed = np.array([0., -.7, -.7, 1., 1.5, 1., 1.5], dtype=np.float32)
        closure = ProximityHandClosure(closed, duration=.3)
        policy = closed * .1
        original = policy.copy()
        np.testing.assert_array_equal(closure.apply(policy, 0.)[0], np.zeros(7))
        closure.activate(policy, 10., .019)
        closure.activate(closed, 11., 0.)  # Repeated triggers do not restart the blend.
        blended, fraction = closure.apply(np.zeros(7), 10.15)
        self.assertAlmostEqual(fraction, .5)
        np.testing.assert_allclose(blended, (original + closed) / 2., atol=1e-6)
        np.testing.assert_array_equal(policy, original)
        np.testing.assert_allclose(closure.apply(np.zeros(7), 12.)[0], closed)
        closure.reset()
        np.testing.assert_array_equal(closure.apply(np.zeros(7), 13.)[0], 0.)
        self.assertIsNone(closure.trigger_distance)


class TriggerChannelTest(unittest.TestCase):
    def test_one_right_hand_request_per_trial_only_while_running(self):
        sent = []
        controls = InteractiveSimulationControls.__new__(InteractiveSimulationControls)
        controls.env = SimpleNamespace(mj_data=None, scene_changed_at=0., config={"SIM_GRASP_DISTANCE": .02})
        sample = {"x_error_m": .004, "y_surface_gap_m": .019, "bottle_tilt_deg": 0., "distance_source": "MuJoCo"}
        controls.hand_alignment = SimpleNamespace(measure=lambda _: sample)
        controls.channel = SimpleNamespace(send=lambda message: sent.append(message) or True)
        controls.detector_socket = True
        controls.detector_result = {"status": "detected", "capture_monotonic": time.monotonic()}
        controls.recognition_scene = 0.
        controls.client_seen = time.monotonic()
        controls.pending = None
        controls.serial = 0
        controls.grasp_latched = False
        controls.bottle_seen = False
        controls.phase = "idle"
        controls.check_hand_alignment()
        self.assertEqual(sent, [])
        self.assertTrue(controls.bottle_seen)
        controls.phase = "running"
        sample["x_error_m"] = .008
        controls.check_hand_alignment()
        self.assertEqual(sent, [])
        sample["x_error_m"] = .004
        controls.check_hand_alignment()
        self.assertEqual(sent, [{"command": "close_right_hand", "id": 1, "source": "MuJoCo", **sample}])
        controls.pending = None
        controls.check_hand_alignment()
        self.assertEqual(len(sent), 1)
        controls.env.scene_changed_at = time.monotonic() + 1.
        controls.check_hand_alignment()
        self.assertFalse(controls.bottle_seen)


if __name__ == "__main__":
    unittest.main()
