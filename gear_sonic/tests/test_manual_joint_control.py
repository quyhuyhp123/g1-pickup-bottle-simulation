import unittest
from unittest.mock import patch
import glfw
import mujoco
import numpy as np
from gear_sonic.scripts.run_manual_joint_control import ManualJoints, PickingViewer


class ManualJointControlTest(unittest.TestCase):
    def setUp(self):
        self.c = ManualJoints()

    def test_selection_limits_and_home(self):
        c = self.c
        self.assertEqual(len(c.groups['left']), 14)
        self.assertEqual(len(c.groups['right']), 14)
        c.command('1'); c.command('Left')
        self.assertEqual(c.index, 13)
        c.set_target(1e6)
        self.assertEqual(c.targets[c.selected], c.model.jnt_range[c.joints[c.selected], 1])
        c.command('2'); c.command('Right')
        self.assertEqual(c.index, 0)
        before = c.targets.copy(); c.command('Up')
        self.assertAlmostEqual(c.targets[c.selected]-before[c.selected], np.deg2rad(2))
        c.command('Down'); np.testing.assert_allclose(c.targets, before)
        with self.assertRaises(ValueError): c.set_target(float('nan'))
        c.command('h'); np.testing.assert_array_equal(c.targets, c.home[c.qa])

    def test_mouse_camera_callbacks_with_installed_mujoco(self):
        # Exercise the real MuJoCo API without requiring a display/context.
        viewer = PickingViewer.__new__(PickingViewer)
        viewer.control = self.c
        viewer.cam = mujoco.MjvCamera()
        viewer.cam.distance = 2.
        viewer.cam.elevation = -20.
        viewer.mouse = (0., 0.)
        before = viewer.cam.distance
        viewer.scroll(None, 0., 1.)
        self.assertNotEqual(viewer.cam.distance, before)
        self.assertGreater(viewer.cam.distance, 0.)
        for button in (glfw.MOUSE_BUTTON_RIGHT, glfw.MOUSE_BUTTON_MIDDLE):
            before = np.r_[viewer.cam.azimuth, viewer.cam.elevation, viewer.cam.lookat].copy()
            with patch.object(glfw, 'get_window_size', return_value=(1000, 800)), \
                 patch.object(glfw, 'get_mouse_button', side_effect=lambda w, b: glfw.PRESS if b == button else glfw.RELEASE):
                viewer.motion(None, viewer.mouse[0]+40, viewer.mouse[1]+20)
            after = np.r_[viewer.cam.azimuth, viewer.cam.elevation, viewer.cam.lookat]
            self.assertFalse(np.array_equal(before, after))
            self.assertTrue(np.isfinite(after).all())

    def test_leg_and_waist_selection_motion_and_home(self):
        c = self.c
        self.assertEqual(len(c.joints), 43)
        self.assertEqual(len(set(c.joints)), 43)
        for key, group in [('3', 'left_leg'), ('4', 'right_leg'), ('5', 'waist')]:
            c.index = 13
            c.command(key)
            self.assertEqual(c.side, group)
            self.assertLess(c.index, len(c.groups[group]))
            c.index = 0
            before = c.data.qpos[c.qa[c.selected]]
            c.set_target(np.rad2deg(before)+8)
            for _ in range(300):
                c.step()
            self.assertGreater(abs(c.data.qpos[c.qa[c.selected]]-before), .02)
            np.testing.assert_array_equal(c.data.qpos[c.lock_q], c.home[c.lock_q])
            self.assertTrue(np.isfinite(c.data.qpos).all())
        c.command('h')
        np.testing.assert_array_equal(c.targets, c.home[c.qa])

    def test_home_resets_actual_state_of_all_joints_and_preserves_bottle(self):
        c = self.c
        c.data.qpos[c.qa] += .05
        c.data.qvel[c.robot_v] = .3
        c.targets[:] += .1
        c.setpoints[:] += .08
        c.data.ctrl[:] = 1.
        c.data.qacc_warmstart[:] = 2.
        other_q = np.setdiff1d(np.arange(c.model.nq), c.robot_q)
        other_v = np.setdiff1d(np.arange(c.model.nv), c.robot_v)
        object_q = c.data.qpos[other_q].copy()
        object_v = c.data.qvel[other_v].copy()
        c.command('H')
        np.testing.assert_array_equal(c.data.qpos[c.robot_q], c.home[c.robot_q])
        np.testing.assert_array_equal(c.data.qvel[c.robot_v], 0.)
        np.testing.assert_array_equal(c.targets, c.home[c.qa])
        np.testing.assert_array_equal(c.setpoints, c.targets)
        np.testing.assert_array_equal(c.data.ctrl, 0.)
        np.testing.assert_array_equal(c.data.qpos[other_q], object_q)
        np.testing.assert_array_equal(c.data.qvel[other_v], object_v)
        for _ in range(20):
            c.step()
        self.assertLess(np.max(np.abs(c.data.qpos[c.qa]-c.home[c.qa])), .03)

    def test_each_link_selects_its_own_joint_and_recolors_only_that_link(self):
        c = self.c
        for i, joint in enumerate(c.joints):
            body = int(c.model.jnt_bodyid[joint])
            self.assertTrue(c.select_body(body))
            self.assertEqual(c.selected, i)
            before = c.targets.copy()
            c.command('Up')
            other = np.arange(len(c.targets)) != i
            np.testing.assert_array_equal(c.targets[other], before[other])
            geoms = np.flatnonzero(c.model.geom_bodyid == body)
            for g in geoms:
                np.testing.assert_allclose(c.model.geom_rgba[g], [.1, 1., .2, 1.])
            c.highlight()
        selected = c.selected
        self.assertFalse(c.select_body(c.model.body('red_bottle').id))
        self.assertFalse(c.select_body(-1))
        self.assertEqual(c.selected, selected)
        first_body = int(c.model.jnt_bodyid[c.joints[0]])
        for g in np.flatnonzero(c.model.geom_bodyid == first_body):
            np.testing.assert_array_equal(c.model.geom_rgba[g], c.original_rgba[g])

    def test_physics_moves_arm_without_unfixing_body_or_teleporting_object(self):
        c = self.c
        before = c.data.qpos[c.qa[c.selected]]
        c.set_target(np.rad2deg(before)+10)
        initial_object = c.data.qpos[c.model.joint('red_bottle_free_joint').qposadr[0]+2]
        c.step()
        self.assertLessEqual(abs(c.setpoints[c.selected]-before), np.deg2rad(30)*c.model.opt.timestep+1e-10)
        for _ in range(300):c.step()
        np.testing.assert_array_equal(c.data.qpos[c.lock_q], c.home[c.lock_q])
        np.testing.assert_array_equal(c.data.qvel[c.lock_v], 0.)
        self.assertGreater(c.data.qpos[c.qa[c.selected]]-before, .05)
        self.assertTrue(np.isfinite(c.data.qpos).all())
        self.assertLess(c.data.qpos[c.model.joint('red_bottle_free_joint').qposadr[0]+2], initial_object)


if __name__ == '__main__':unittest.main()
