import unittest
import ast
from pathlib import Path
import numpy as np
from gear_sonic.scripts.export_gr00t_candidate_dataset import past_camera_indices, projected_gravity, GROUPS, HAND_STATE_ORDER, export

class ExportTest(unittest.TestCase):
    def test_camera_is_past_not_nearest_future(self):
        t=np.arange(21)*.005; ids=np.full(21,-1);ids[[0,20]]=[0,1]
        rows,age=past_camera_indices(t,ids,np.array([0,4,19,20]))
        np.testing.assert_array_equal(rows,[0,0,0,20])
        self.assertAlmostEqual(age[2],.095)
    def test_missing_and_stale_camera_rejected(self):
        for ids in (np.array([-1,1]),np.array([0,-1])):
            with self.assertRaises(ValueError):past_camera_indices(np.array([0.,.2]),ids,np.array([0,1]))
    def test_gravity_rotates_world_into_base(self):
        q=np.array([[1.,0,0,0],[2**-.5,0,2**-.5,0]])
        np.testing.assert_allclose(projected_gravity(q),[[0,0,-1],[1,0,0]],atol=1e-12)
    def test_joint_order_unique_and_expected_dimensions(self):
        names=sum(GROUPS.values(),[])
        self.assertEqual(len(names),43);self.assertEqual(len(set(names)),43)
    def test_export_needs_explicit_experimental_flag(self):
        with self.assertRaisesRegex(ValueError,'experimental'): export('unused','unused')
    def test_state_order_matches_live_robot_model(self):
        path=Path(__file__).parents[1]/'data/robot_model/supplemental_info/g1/g1_supplemental_info.py'
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='joint_groups' for t in node.targets):
                expected=ast.literal_eval(node.value)
                break
        else:self.fail('RobotModel joint groups missing')
        for group,names in GROUPS.items():
            if group.endswith('_hand'):names=[names[i] for i in HAND_STATE_ORDER]
            self.assertEqual(names,expected[group]['joints'])

if __name__=='__main__':unittest.main()
