import json
from pathlib import Path
import queue
from collections import deque
from types import SimpleNamespace
import unittest
import numpy as np
import mujoco
from gear_sonic.scripts.run_finetuned_sim import LearnedSimulation,PolicyViewer,validate_server
from gear_sonic.scripts.launch_inference import InferenceLaunchConfig,_resolve_sim_grasp_config

class FineTunedSimulationTest(unittest.TestCase):
    def test_bottle_position_enters_policy_only_as_rgb(self):
        from gear_sonic.scripts.export_gr00t_candidate_dataset import GROUPS,HAND_STATE_ORDER
        groups={k:([v[i] for i in HAND_STATE_ORDER] if k.endswith('_hand') else v) for k,v in GROUPS.items()}
        joints=''.join(f'<body><joint name="{n}"/><geom size=".01" mass=".1"/></body>' for names in GROUPS.values() for n in names)
        model=mujoco.MjModel.from_xml_string('<mujoco><worldbody><body><freejoint name="floating_base_joint"/><geom size=".1" mass="1"/>'+joints+'</body><body pos=".4 -.1 .8"><freejoint name="bottle"/><geom size=".03" mass=".1"/></body></worldbody></mujoco>')
        sim=LearnedSimulation.__new__(LearnedSimulation);sim.model=model;sim.data=mujoco.MjData(model)
        sim.mj=mujoco;sim.np=np;sim.profile={'state_joint_groups':groups};sim.root_qa=0;sim.args=SimpleNamespace(prompt='grab the bottle')
        bottle_qa=int(model.joint('bottle').qposadr[0])
        class ImageRenderer:
            def update_scene(self,data,camera):self.x=data.qpos[bottle_qa]
            def render(self):return np.full((480,640,3),round(self.x*100),dtype=np.uint8)
        sim.renderer=ImageRenderer();before=sim.observation()
        sim.data.qpos[bottle_qa]=.5;after=sim.observation()
        self.assertEqual(set(after),{'video','state','language'})
        self.assertEqual(after['video']['ego_view'].shape,(1,1,480,640,3))
        self.assertFalse(np.array_equal(before['video']['ego_view'],after['video']['ego_view']))
        for key in before['state']:np.testing.assert_array_equal(before['state'][key],after['state'][key])
    def test_middle_mouse_pan_uses_current_mujoco_camera_api(self):
        view=PolicyViewer.__new__(PolicyViewer);view.mouse=(0.,0.);view.mj=mujoco
        view.cam=mujoco.MjvCamera();mujoco.mjv_defaultCamera(view.cam)
        view.sim=SimpleNamespace(model=mujoco.MjModel.from_xml_string('<mujoco/>'))
        view.glfw=SimpleNamespace(PRESS=1,MOUSE_BUTTON_RIGHT=2,MOUSE_BUTTON_MIDDLE=3,
            get_window_size=lambda w:(800,600),get_mouse_button=lambda w,b:1 if b==3 else 0)
        initial=view.cam.lookat.copy();view.motion(None,20.,30.)
        self.assertFalse(np.array_equal(initial,view.cam.lookat))
    def test_launcher_selects_native_model_without_legacy_owners(self):
        config=InferenceLaunchConfig(sim=True,sim_finetuned_policy=True)
        _resolve_sim_grasp_config(config)
        self.assertFalse(config.inspire_ftp_hands)
        self.assertFalse(config.bottle_detection)
        self.assertFalse(config.sim_policy_control)
        self.assertFalse(config.data_exporter)
    def test_mixed_assistance_is_rejected(self):
        for field in ('sim_assisted_pickup','sim_native_inspire','sim_fixed_base','inspire_ftp_hands','sim_grasp_distance'):
            config=InferenceLaunchConfig(sim=True,sim_finetuned_policy=True)
            setattr(config,field,.02 if field=='sim_grasp_distance' else True)
            with self.assertRaises(ValueError):_resolve_sim_grasp_config(config)
    def test_server_checkpoint_and_hand_contract_must_match(self):
        good={'checkpoint_fingerprint':'abc','profile':{'execution_profile_id':'fixed_base_dex3_pd80_3_v1','hand_format':'dex3_joint_radians'}}
        validate_server(good,{'checkpoint_fingerprint':'abc'})
        with self.assertRaises(ValueError):validate_server(good,{'checkpoint_fingerprint':'old_v10'})
        good['profile']['hand_format']='inspire_normalized_grip'
        with self.assertRaises(ValueError):validate_server(good,{'checkpoint_fingerprint':'abc'})
    def test_reset_discards_queued_actions_and_restores_all_state(self):
        model=mujoco.MjModel.from_xml_string('''<mujoco><worldbody>
          <body><freejoint name="robot"/><geom size=".1" mass="1"/>
            <body><joint name="hinge"/><geom size=".1" mass="1"/></body></body>
          <body pos=".4 -.1 .8"><freejoint name="bottle"/><geom size=".03" mass=".1"/></body>
          </worldbody></mujoco>''')
        sim=LearnedSimulation.__new__(LearnedSimulation)
        sim.model=model;sim.data=mujoco.MjData(model);sim.mj=mujoco;sim.np=np
        sim.home=model.qpos0.copy();sim.generation=1;sim.ready=True
        sim.worker=SimpleNamespace(requests=queue.Queue(maxsize=1));sim.worker.requests.put(('old','old observation'))
        sim.bottle_qa=int(model.joint('bottle').qposadr[0]);sim.xy=np.array([.45,-.05])
        sim.bq=np.array([7]);sim.hq=np.array([7]);sim.history=deque([1])
        sim.data.qpos[7]=.6;sim.data.qvel[:]=2.;sim.data.ctrl[:]=1.
        sim.reset()
        self.assertEqual(sim.generation,2);self.assertTrue(sim.worker.requests.empty())
        np.testing.assert_array_equal(sim.data.qpos[:8],sim.home[:8])
        np.testing.assert_array_equal(sim.data.qvel,0.)
        np.testing.assert_array_equal(sim.data.qpos[sim.bottle_qa:sim.bottle_qa+2],sim.xy)
        self.assertIsNone(sim.chunk);self.assertFalse(sim.running);self.assertFalse(sim.pending)
        self.assertEqual(len(sim.history),0)
        np.testing.assert_array_equal(sim.last,0.)

if __name__=='__main__':unittest.main()
