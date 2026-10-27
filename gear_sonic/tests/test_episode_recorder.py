import json
import tempfile
import unittest
from pathlib import Path
import mujoco
import numpy as np
from gear_sonic.utils.mujoco_sim.episode_recorder import EpisodeRecorder
from gear_sonic.scripts.inspect_sim_episode import inspect

class FakeRenderer:
    def update_scene(self, data, camera):
        self.t = data.time
    def render(self):
        return np.full((480, 640, 3), int(self.t * 10) % 255, dtype=np.uint8)
    def close(self):
        pass

class RecorderTest(unittest.TestCase):
    def test_synchronized_steps_chunks_and_episode_boundaries(self):
        model = mujoco.MjModel.from_xml_string('''<mujoco><option timestep=".005"/><worldbody>
        <camera name="head_camera"/><body><joint name="hinge"/><geom type="sphere" size=".1"/></body>
        </worldbody><actuator><motor joint="hinge"/></actuator></mujoco>''')
        data = mujoco.MjData(model)
        with tempfile.TemporaryDirectory() as root:
            r = EpisodeRecorder(model, root, 'grab the bottle', renderer=FakeRenderer())
            for i in range(205):
                data.ctrl[:] = i * .001
                r.capture(data, True, 1)
                mujoco.mj_step(model, data)
            r.capture(data, False, 1)
            path = next(Path(root).iterdir())
            self.assertEqual(inspect(path), 205)
            with np.load(path / 'states_000000.npz') as z:
                self.assertEqual(z['sim_time'][0], 0.)
                np.testing.assert_allclose(z['ctrl'][:, 0], np.arange(200)*.001)
            self.assertFalse(json.loads((path/'meta.json').read_text())['training_ready'])
            r.capture(data, True, 2)
            r.close()
            self.assertEqual(len(list(Path(root).iterdir())), 2)
            (path/'rgb/000000.png').unlink()
            with self.assertRaises(ValueError):
                inspect(path)

if __name__ == '__main__': unittest.main()
