"""Action ownership and malformed-chunk regression for GR00T -> SONIC."""

import unittest
import json
import tempfile
from pathlib import Path
import numpy as np
from gear_sonic.utils.inference.policy_control import policy_action_step, validate_policy_simulation


class PolicyControlTest(unittest.TestCase):
    def test_playback_accounts_for_camera_age_and_delayed_publisher(self):
        from gear_sonic.utils.inference.policy_control import policy_step_at
        # Frame captured at 10.0, request at 10.2, result at 10.36:
        # request-only compensation would incorrectly use step 8, not 18.
        self.assertEqual(policy_step_at(10.36, 10., 50., 40), 18)
        self.assertEqual(policy_step_at(10.42, 10., 50., 40), 21)
        self.assertEqual(policy_step_at(10.36, 10.36, 50., 40), 0)
        self.assertEqual(policy_step_at(11., 10., 50., 40), 39)

    def test_refresh_precedes_exhaustion_despite_delayed_observation(self):
        from gear_sonic.utils.inference.policy_control import policy_chunk_needs_refresh
        # 0.8 s trajectory, 0.16 s inference, two periods scheduling margin.
        self.assertFalse(policy_chunk_needs_refresh(10.36, 10., 50., 40, .16))
        self.assertTrue(policy_chunk_needs_refresh(10.61, 10., 50., 40, .16))
        self.assertTrue(policy_chunk_needs_refresh(11., 10., 50., 40, .16))

    def chunk(self):
        return {'motion_token': np.arange(3*64, dtype=np.float32).reshape(1,3,64)/200.,
                'left_hand_joints': np.arange(21, dtype=np.float32).reshape(1,3,7)/21.,
                'right_hand_joints': np.arange(21, dtype=np.float32).reshape(1,3,7)/42.}

    def test_motion_and_finger_timing_are_unchanged_and_synchronized(self):
        for prefix in ('', 'action.'):
            chunk = {prefix+k:v for k,v in self.chunk().items()}
            token, left, right, index = policy_action_step(chunk, 1)
            self.assertEqual(index, 1)
            np.testing.assert_array_equal(token, chunk[prefix+'motion_token'][0,1])
            np.testing.assert_array_equal(right, chunk[prefix+'right_hand_joints'][0,1])
            np.testing.assert_array_equal(left, chunk[prefix+'left_hand_joints'][0,1])
            token[:] = 0.
            self.assertGreater(chunk[prefix+'motion_token'][0,1].sum(), 0.)

    def test_bad_chunks_are_rejected_instead_of_mixing_commands(self):
        cases=[]
        c=self.chunk();c['motion_token'][0,0,0]=np.nan;cases.append(c)
        c=self.chunk();c['right_hand_joints']=np.zeros((1,2,7));cases.append(c)
        c=self.chunk();c['motion_token']=np.zeros((2,3,64));cases.append(c)
        c=self.chunk();c['right_hand_joints']=np.zeros((1,3,6));cases.append(c)
        c=self.chunk();del c['motion_token'];cases.append(c)
        for chunk in cases:
            with self.subTest(keys=list(chunk)), self.assertRaises(ValueError):
                policy_action_step(chunk, 0)

    def test_no_simulation_override_can_enter_policy_profile(self):
        validate_policy_simulation({'POLICY_CONTROL': True, 'ARM_GRAVITY_COMPENSATION': True})
        for key in ('ASSISTED_PICKUP','FIXED_PICKUP_BASE','SIM_GRASP_DISTANCE',
                    'NATIVE_INSPIRE'):
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_policy_simulation({'POLICY_CONTROL':True,key:True})

    def test_audit_detects_replaced_token_instead_of_claiming_policy_success(self):
        from gear_sonic.scripts.check_policy_control_trace import audit_trace
        action=self.chunk()
        token,left,right,index=policy_action_step(action,1)
        rows=[{'event':'raw_chunk','input_state':{'left_hand':[0.]*7,'right_hand':[0.]*7}},
              {'event':'chunk_selected','chunk_id':1,'action':{k:v.tolist() for k,v in action.items()}},
              {'event':'published','chunk_id':1,'index':index,'motion_token':token.tolist(),
               'raw_motion_token':token.tolist(),'raw_left_hand':left.tolist(),
               'raw_right_hand':right.tolist(),'closure_fraction':None,'body_source':'GR00T'}]
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'trace.jsonl'
            path.write_text(''.join(json.dumps(row)+'\n' for row in rows))
            report=audit_trace(path)
            self.assertTrue(report['policy_routing_verified'])
            self.assertIsInstance(report['pickup_success'],str)
            rows[-1]['motion_token']=[0.]*64
            path.write_text(''.join(json.dumps(row)+'\n' for row in rows))
            report=audit_trace(path)
            self.assertFalse(report['policy_routing_verified'])
            self.assertEqual(report['ownership_violation_lines'],[3])


if __name__=='__main__':
    unittest.main()
