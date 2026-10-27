"""Policy finger timing is the default; proximity closure requires an explicit opt-in."""

import unittest
import builtins
from unittest.mock import patch

import tyro

from gear_sonic.scripts.launch_inference import InferenceLaunchConfig, _resolve_sim_grasp_config, _bootstrap_venv


class SimGraspDefaultsTest(unittest.TestCase):
    def test_bootstrap_without_tyro_reexecutes_before_config_is_parsed(self):
        original_import = builtins.__import__
        def missing_tyro(name, *args, **kwargs):
            if name == 'tyro':
                raise ImportError('tyro absent from system Python')
            return original_import(name, *args, **kwargs)
        with patch('builtins.__import__', side_effect=missing_tyro), \
             patch('gear_sonic.scripts.launch_inference.os.execv') as reexec, \
             patch('pathlib.Path.exists', return_value=True):
            _bootstrap_venv()
        self.assertTrue(reexec.call_args.args[0].endswith('/.venv_inference/bin/python'))

    def parse(self, args):
        config = tyro.cli(InferenceLaunchConfig, args=args)
        _resolve_sim_grasp_config(config)
        return config

    def test_user_simulation_command_preserves_policy_grasp_timing(self):
        config = self.parse(["--sim", "--policy-host", "127.0.0.1", "--policy-port", "5550",
                             "--no-data-exporter", "--inspire-ftp-hands", "--prompt", "grab the bottle"])
        self.assertEqual(config.sim_grasp_distance, 0.)
        self.assertEqual(config.sim_grasp_x_tolerance, .005)
        self.assertTrue(config.sim_policy_control)
        self.assertFalse(config.bottle_detection)
        self.assertTrue(config.inspire_ftp_hands)

    def test_explicit_checkpoint_only_hand_control_is_preserved(self):
        self.assertEqual(self.parse(["--sim", "--sim-grasp-distance", "0"]).sim_grasp_distance, 0.)

    def test_assisted_command_owns_closure_and_parses_bottle_xy(self):
        config = self.parse(['--sim', '--sim-assisted-pickup', '--sim-fixed-base', '--sim-bottle-xy', '.40', '-.15'])
        self.assertTrue(config.sim_fixed_base)
        self.assertFalse(config.sim_policy_control)
        self.assertTrue(config.bottle_detection)
        self.assertEqual(config.sim_grasp_distance, 0.)
        self.assertEqual(config.sim_bottle_xy, (.40, -.15))

    def test_hardware_and_disabled_detector_have_no_com_override(self):
        self.assertEqual(self.parse([]).sim_grasp_distance, 0.)
        self.assertEqual(self.parse(["--sim", "--no-bottle-detection"]).sim_grasp_distance, 0.)

    def test_policy_profile_disables_all_local_motion_corrections(self):
        config = self.parse(['--sim', '--sim-policy-control'])
        self.assertTrue(config.inspire_ftp_hands)
        self.assertFalse(config.bottle_detection)
        self.assertTrue(config.sim_arm_gravity_compensation)
        self.assertFalse(config.sim_assisted_pickup)
        self.assertFalse(config.sim_fixed_base)
        self.assertEqual(config.sim_grasp_distance, 0.)
        self.assertTrue(config.action_diagnostic_path)

    def test_policy_profile_rejects_conflicting_owners_and_hardware(self):
        for args in (['--sim-policy-control'], ['--sim', '--sim-policy-control', '--sim-assisted-pickup'],
                     ['--sim', '--sim-policy-control', '--sim-native-inspire'],
                     ['--sim', '--sim-policy-control', '--sim-grasp-distance', '.02']):
            with self.subTest(args=args), self.assertRaises(ValueError):
                self.parse(args)


if __name__ == "__main__":
    unittest.main()
