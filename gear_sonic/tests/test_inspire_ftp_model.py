"""Topology/inertia and independent finger-control checks for the downloaded FTP model."""
from pathlib import Path
import unittest
import mujoco
import numpy as np
from gear_sonic.scripts.run_inspire_ftp_sim import initialize, hand_actuators, ROOT

SCENE = ROOT/'models/g1_inspire_ftp/g1_inspire_ftp.xml'

@unittest.skipUnless(SCENE.exists(), 'Run prepare_inspire_ftp_sim.py to download native Inspire model')
class InspireFTPModelTest(unittest.TestCase):
    def test_native_topology_and_open_close(self):
        model = mujoco.MjModel.from_xml_path(str(SCENE))
        data = mujoco.MjData(model)
        initialize(model, data)
        self.assertEqual(model.nu, 41)
        self.assertEqual(model.njnt, 55)  # 53 hinges + robot and bottle free joints
        self.assertEqual(sum(model.eq_type == mujoco.mjtEq.mjEQ_JOINT), 12)
        for side in ('left', 'right'):
            self.assertAlmostEqual(float(model.body(side+'_base_link').mass[0]), .62266)
        right = hand_actuators(model, 'right')
        left = hand_actuators(model, 'left')
        right_q = model.jnt_qposadr[model.actuator_trnid[right, 0]]
        left_q = model.jnt_qposadr[model.actuator_trnid[left, 0]]
        for step in range(3000):
            target = model.actuator_ctrlrange[right, 1]*.5
            data.ctrl[right] += np.clip(target-data.ctrl[right], -.0008, .0008)
            mujoco.mj_step(model, data)
        self.assertGreater(float(np.mean(data.qpos[right_q])), .2)
        self.assertLess(float(np.max(np.abs(data.qpos[left_q]))), .1)
        for _ in range(3000):
            data.ctrl[right] += np.clip(-data.ctrl[right], -.0008, .0008)
            mujoco.mj_step(model, data)
        self.assertLess(float(np.max(np.abs(data.qpos[right_q]))), .1)
        self.assertTrue(np.isfinite(data.qpos).all())
        self.assertFalse(any(w.number for w in data.warning))
        initialize(model, data)
        np.testing.assert_array_equal(data.qvel, 0.)

if __name__ == '__main__':
    unittest.main()
