import unittest
import numpy as np
from gear_sonic.scripts.encode_sim_episode import body_order
from gear_sonic.scripts.rollout_sonic_episode import manipulation_mask

class ManipulationMaskTest(unittest.TestCase):
    def test_only_right_arm_and_waist_pitch_are_selected(self):
        names=[n.replace('_link','_joint') if n!='torso_link' else 'waist_pitch_joint' for n in body_order()]
        mask=manipulation_mask(names)
        self.assertEqual(mask.sum(),8)
        for name, selected in zip(names,mask):
            if any(part in name for part in ('hip','knee','ankle')) or name.startswith('left_'):
                self.assertFalse(selected, name)
        self.assertFalse(mask[names.index('waist_roll_joint')])
        self.assertFalse(mask[names.index('waist_yaw_joint')])
        self.assertTrue(mask[names.index('waist_pitch_joint')])
        reverse=names[::-1]
        np.testing.assert_array_equal(manipulation_mask(reverse),mask[::-1])

    def test_incomplete_model_rejected(self):
        with self.assertRaises(ValueError): manipulation_mask(['waist_pitch_joint'])

if __name__=='__main__':unittest.main()
