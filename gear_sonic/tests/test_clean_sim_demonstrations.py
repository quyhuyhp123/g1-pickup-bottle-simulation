import unittest
import numpy as np
from gear_sonic.scripts.clean_sim_demonstrations import select_window

class SelectionTest(unittest.TestCase):
    def test_trim_idle_and_placement_keep_context(self):
        stages=np.array(['idle']*20+['approach']*10+['close']*10+['lift']*10+['hold']*10+['success']*5+['lower']*20)
        lo,start,stop,hi=select_window(stages,np.arange(len(stages))*.1)
        self.assertEqual(start,20);self.assertEqual(stop,65);self.assertEqual(hi,65)
        self.assertLess(lo,start);self.assertNotIn('lower',stages[lo:hi])
    def test_failed_or_incomplete_rejected(self):
        for sequence in (['approach','failed','success'],['approach','close','lift','hold']):
            with self.assertRaises(ValueError):select_window(np.array(sequence),np.arange(len(sequence))*.1)
    def test_user_review_can_accept_truncated_hold(self):
        stages=np.array(['idle','approach','close','lift','hold','hold'])
        lo,start,stop,hi=select_window(stages,np.arange(6)*.1,allow_reviewed_hold=True)
        self.assertEqual(stop,6)
        self.assertEqual(start,1)

    def test_long_success_tail_bounded(self):
        stages=np.array(['approach','close','lift','hold']+['success']*100)
        lo,start,stop,hi=select_window(stages,np.arange(len(stages))*.1)
        self.assertLess(stop,30);self.assertGreater(hi,stop)

if __name__=='__main__':unittest.main()
