"""The normal simulation command enables grasp-centre gating; hardware stays unchanged."""

import unittest

import tyro

from gear_sonic.scripts.launch_inference import InferenceLaunchConfig, _resolve_sim_grasp_config


class SimGraspDefaultsTest(unittest.TestCase):
    def parse(self, args):
        config = tyro.cli(InferenceLaunchConfig, args=args)
        _resolve_sim_grasp_config(config)
        return config

    def test_user_simulation_command_enables_grasp_centre_gate(self):
        config = self.parse(["--sim", "--policy-host", "127.0.0.1", "--policy-port", "5550",
                             "--no-data-exporter", "--inspire-ftp-hands", "--prompt", "grab the bottle"])
        self.assertEqual(config.sim_grasp_distance, .02)
        self.assertEqual(config.sim_grasp_x_tolerance, .005)

    def test_explicit_checkpoint_only_hand_control_is_preserved(self):
        self.assertEqual(self.parse(["--sim", "--sim-grasp-distance", "0"]).sim_grasp_distance, 0.)

    def test_assisted_command_owns_closure_and_parses_bottle_xy(self):
        config = self.parse(['--sim', '--sim-assisted-pickup', '--sim-fixed-base', '--sim-bottle-xy', '.40', '-.15'])
        self.assertTrue(config.sim_fixed_base)
        self.assertEqual(config.sim_grasp_distance, 0.)
        self.assertEqual(config.sim_bottle_xy, (.40, -.15))

    def test_hardware_and_disabled_detector_have_no_com_override(self):
        self.assertEqual(self.parse([]).sim_grasp_distance, 0.)
        self.assertEqual(self.parse(["--sim", "--no-bottle-detection"]).sim_grasp_distance, 0.)


if __name__ == "__main__":
    unittest.main()
