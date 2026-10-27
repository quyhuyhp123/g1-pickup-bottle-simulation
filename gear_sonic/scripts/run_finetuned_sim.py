"""Run the fine-tuned GR00T -> frozen SONIC -> MuJoCo pipeline.

RGB and measured robot state are the only policy inputs. No detector, depth,
IK, trajectory replay, proximity closure, or hand-format adapter is loaded.
"""
import argparse
from collections import deque
import hashlib
import json
import os
from pathlib import Path
import queue
import socket
import subprocess
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[2]
PROFILE='fixed_base_dex3_pd80_3_v1'


def write_report(path,report):
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(report,indent=2)+'\n');temporary.replace(path)


def checkpoint_metadata(path):
    path=Path(path).resolve()
    profile=json.loads((path/'simulation_profile.json').read_text())
    if profile.get('execution_profile_id')!=PROFILE or profile.get('hand_format')!='dex3_joint_radians':
        raise ValueError('Requires the fine-tuned fixed-base native Dex3 checkpoint')
    digest=hashlib.sha256()
    for name in ('config.json','processor_config.json','statistics.json','model.safetensors.index.json','simulation_profile.json'):
        digest.update((path/name).read_bytes())
    if not (path/profile.get('scene_file','')).is_file() or not profile.get('robot_home_qpos'):
        raise ValueError('Checkpoint is missing its static simulation scene/home configuration')
    return dict(model_path=str(path),checkpoint_fingerprint=digest.hexdigest(),profile=profile,
                rgb_depth_ik=False,action_horizon=40,action_rate_hz=50)


def serve(args):
    import torch
    from gr00t.policy.gr00t_policy import Gr00tPolicy
    from gr00t.policy.server_client import PolicyServer
    metadata=checkpoint_metadata(args.model_path)
    policy=Gr00tPolicy(model_path=args.model_path,embodiment_tag='UNITREE_G1_SONIC',device=args.device)
    policy.model.action_head.num_inference_timesteps=args.diffusion_steps
    metadata['inference']={'diffusion_steps':args.diffusion_steps,'sampling_seed':args.sampling_seed}
    class StableSamplingPolicy:
        def get_action(self,observation,options=None):
            if args.sampling_seed<0:return policy.get_action(observation,options)
            with torch.random.fork_rng(devices=[torch.device(args.device).index or 0]):
                torch.manual_seed(args.sampling_seed)
                return policy.get_action(observation,options)
        def reset(self,options=None):return policy.reset(options)
        def get_modality_config(self):return policy.get_modality_config()
    with PolicyServer(StableSamplingPolicy(),host=args.policy_host,port=args.policy_port) as server:
        server.register_endpoint('get_policy_metadata',lambda:metadata,requires_input=False)
        server.run()


class RPC:
    """Thread-owned REQ socket, compatible with GR00T's msgpack_numpy protocol."""
    def __init__(self,host,port,timeout=15000):
        import zmq
        self.zmq=zmq;self.context=zmq.Context();self.host=host;self.port=port;self.timeout=timeout
        self.socket=None;self.connect()
    def connect(self):
        if self.socket is not None:self.socket.close(linger=0)
        self.socket=self.context.socket(self.zmq.REQ)
        self.socket.setsockopt(self.zmq.RCVTIMEO,self.timeout);self.socket.setsockopt(self.zmq.SNDTIMEO,self.timeout)
        self.socket.connect(f'tcp://{self.host}:{self.port}')
    def call(self,endpoint,data=None):
        import msgpack,msgpack_numpy as mnp,numpy as np
        def encode(value):
            if isinstance(value,np.ndarray) and value.dtype.kind=='O':raise ValueError('Object arrays are not supported')
            return mnp.encode(value)
        def decode(value):
            if value.get(b'nd',value.get('nd')) and value.get(b'kind',value.get('kind')) in ('O',b'O'):
                raise ValueError('Object arrays are not supported')
            return mnp.decode(value)
        request={'endpoint':endpoint}
        if data is not None:request['data']=data
        try:
            self.socket.send(msgpack.packb(request,default=encode))
            value=msgpack.unpackb(self.socket.recv(),object_hook=decode,raw=False)
        except self.zmq.error.Again:
            self.connect();raise TimeoutError(f'Policy server timed out: {self.host}:{self.port}')
        if isinstance(value,dict) and 'error' in value:raise RuntimeError(value['error'])
        return value
    def close(self):
        self.socket.close(linger=0);self.context.term()


def validate_server(actual,expected):
    if actual.get('checkpoint_fingerprint')!=expected['checkpoint_fingerprint']:
        raise ValueError('Server is running a different checkpoint. Start this command without --external-server.')
    profile=actual.get('profile',{})
    if profile.get('execution_profile_id')!=PROFILE or profile.get('hand_format')!='dex3_joint_radians':
        raise ValueError('Wrong controller/hand profile on server')


class ModelWorker:
    def __init__(self,args,expected):
        self.args=args;self.expected=expected;self.requests=queue.Queue(maxsize=1);self.results=queue.Queue()
        self.stop=threading.Event();self.thread=threading.Thread(target=self.run,daemon=True);self.thread.start()
    def run(self):
        client=RPC(self.args.policy_host,self.args.policy_port,timeout=2000)
        try:
            deadline=time.monotonic()+90
            while not self.stop.is_set():
                try:
                    metadata=client.call('get_policy_metadata');validate_server(metadata,self.expected)
                    self.results.put(('ready',metadata));break
                except TimeoutError:
                    if time.monotonic()>deadline:raise
                except Exception as exc:raise RuntimeError('Cannot verify fine-tuned server: '+str(exc)) from exc
            client.timeout=15000;client.connect()
            while not self.stop.is_set():
                try:generation,observation=self.requests.get(timeout=.1)
                except queue.Empty:continue
                try:
                    begin=time.monotonic()
                    action,_=client.call('get_action',{'observation':observation,'options':None})
                    self.results.put(('action',generation,action,time.monotonic()-begin))
                except Exception as exc:self.results.put(('error',generation,str(exc)))
        except Exception as exc:self.results.put(('fatal',str(exc)))
        finally:client.close()


class PolicyViewer:
    """Main-thread GLFW viewer; no passive render thread shares the camera context."""
    def __init__(self,simulation,key_callback):
        import glfw
        self.glfw=glfw;self.sim=simulation;self.mj=simulation.mj
        if not glfw.init():raise RuntimeError('Cannot initialize the simulation display')
        # MuJoCo Renderer creates a hidden GLFW context and leaves VISIBLE=False
        # in GLFW's global window hints. The interactive window must reset it.
        glfw.default_window_hints()
        glfw.window_hint(glfw.VISIBLE,glfw.TRUE)
        self.window=glfw.create_window(1000,760,'Fine-tuned GR00T -> SONIC -> Dex3 | RGB-D/IK OFF',None,None)
        if self.window is None:raise RuntimeError('Cannot open simulation window')
        glfw.make_context_current(self.window);glfw.swap_interval(0)
        self.cam=self.mj.MjvCamera();self.mj.mjv_defaultCamera(self.cam)
        self.opt=self.mj.MjvOption();self.scene=self.mj.MjvScene(simulation.model,maxgeom=10000)
        for flag in ('mjRND_SHADOW','mjRND_REFLECTION','mjRND_SKYBOX','mjRND_FOG'):
            self.scene.flags[getattr(self.mj.mjtRndFlag,flag)]=0
        self.context=self.mj.MjrContext(simulation.model,self.mj.mjtFontScale.mjFONTSCALE_100)
        self.mouse=(0.,0.)
        def key(w,k,sc,action,mods):
            if action==glfw.PRESS:
                if k==glfw.KEY_ESCAPE:glfw.set_window_should_close(w,True)
                else:key_callback(k)
        glfw.set_key_callback(self.window,key)
        glfw.set_mouse_button_callback(self.window,lambda w,b,a,mods:setattr(self,'mouse',glfw.get_cursor_pos(w)))
        glfw.set_cursor_pos_callback(self.window,self.motion)
        glfw.set_scroll_callback(self.window,lambda w,x,y:self.mj.mjv_moveCamera(simulation.model,self.mj.mjtMouse.mjMOUSE_ZOOM,0.,-.05*y,self.cam))
    def motion(self,window,x,y):
        g=self.glfw;dx=x-self.mouse[0];dy=y-self.mouse[1];self.mouse=(x,y)
        height=max(1,g.get_window_size(window)[1]);action=None
        if g.get_mouse_button(window,g.MOUSE_BUTTON_RIGHT)==g.PRESS:action=self.mj.mjtMouse.mjMOUSE_ROTATE_V
        elif g.get_mouse_button(window,g.MOUSE_BUTTON_MIDDLE)==g.PRESS:action=self.mj.mjtMouse.mjMOUSE_MOVE_V
        if action is not None:self.mj.mjv_moveCamera(self.sim.model,action,dx/height,dy/height,self.cam)
    def is_running(self):
        self.glfw.poll_events()
        return self.window is not None and not self.glfw.window_should_close(self.window)
    def sync(self):
        g=self.glfw;mj=self.mj;g.make_context_current(self.window)
        width,height=g.get_framebuffer_size(self.window)
        if min(width,height)<=0:return
        mj.mjv_updateScene(self.sim.model,self.sim.data,self.opt,None,self.cam,mj.mjtCatBit.mjCAT_ALL,self.scene)
        rect=mj.MjrRect(0,0,width,height);mj.mjr_render(rect,self.scene,self.context)
        text=f"NEW GR00T -> SONIC -> Dex3 | RGB-D/IK OFF\nF6 Start | F5 Reset | Right drag rotate | Middle drag pan | Wheel zoom\nSim {self.sim.data.time:.2f}s | Model calls {self.sim.model_calls} | {'WAITING FOR MODEL' if self.sim.pending else 'RUNNING' if self.sim.running else 'READY / IDLE'}"
        mj.mjr_overlay(mj.mjtFont.mjFONT_NORMAL,mj.mjtGridPos.mjGRID_TOPLEFT,rect,text,'',self.context)
        g.swap_buffers(self.window)
    def close(self):
        if self.window is not None:
            self.glfw.make_context_current(self.window);self.context.free()
            self.glfw.destroy_window(self.window);self.window=None


class LearnedSimulation:
    def __init__(self,args):
        import mujoco,numpy as np,onnxruntime as ort
        self.mj=mujoco;self.np=np;self.args=args;self.metadata=checkpoint_metadata(args.model_path)
        self.profile=self.metadata['profile'];self.model=m=mujoco.MjModel.from_xml_path(str(Path(args.model_path)/self.profile['scene_file']))
        self.data=d=mujoco.MjData(m);m.opt.timestep=.005
        self.home=m.qpos0.copy()
        for name,value in self.profile['robot_home_qpos'].items():
            joint=m.joint(name);qa=int(joint.qposadr[0]);self.home[qa:qa+len(value)]=value
        self.held_home=self.home.copy()
        for name,value in self.profile.get('held_joint_home_qpos',{}).items():
            qa=int(m.joint(name).qposadr[0]);self.held_home[qa:qa+len(value)]=value
        names=self.profile['body_joint_names'];self.body=np.array([m.joint(n).id for n in names])
        self.bq=m.jnt_qposadr[self.body];self.bv=m.jnt_dofadr[self.body]
        controlled={'waist_pitch_joint'}|{'right_'+part+'_joint' for part in ('shoulder_pitch','shoulder_roll','shoulder_yaw','elbow','wrist_roll','wrist_pitch','wrist_yaw')}
        self.moving=np.array([name in controlled for name in names]);self.held=~self.moving
        if int(self.moving.sum())!=8:raise ValueError('Invalid trained body joint mapping')
        self.hands=np.array([m.joint(side+'_hand_'+name+'_joint').id for side in ('left','right') for name in self.profile['hand_motor_order']])
        self.hq=m.jnt_qposadr[self.hands];self.hv=m.jnt_dofadr[self.hands]
        motor=lambda js:np.array([np.flatnonzero(m.actuator_trnid[:,0]==j).item() for j in js])
        self.bmot=motor(self.body);self.hmot=motor(self.hands)
        self.default=np.asarray(self.profile['sonic_default_angles']);self.scale=np.asarray(self.profile['sonic_action_scale'])
        if self.default.shape!=(29,) or self.scale.shape!=(29,):raise ValueError('Invalid SONIC action mapping')
        self.bottle_joint=m.joint('red_bottle_free_joint').id;self.bottle_qa=int(m.jnt_qposadr[self.bottle_joint])
        self.bottle_body=int(m.jnt_bodyid[self.bottle_joint]);self.root_qa=int(m.joint('floating_base_joint').qposadr[0])
        self.root_va=int(m.joint('floating_base_joint').dofadr[0])
        if not np.any(m.eq_active0):raise ValueError('Training profile requires the pelvis fixture')
        if any(int(m.eq_obj1id[i])==self.bottle_body or int(m.eq_obj2id[i])==self.bottle_body for i in range(m.neq)):
            raise ValueError('Bottle must be a free object, never attached by equality constraints')
        self.xy=self.home[self.bottle_qa:self.bottle_qa+2].copy()
        from gear_sonic.utils.mujoco_sim.object_reset import BottlePlacement
        mujoco.mj_forward(m,d)
        self.placement=BottlePlacement(m,d)
        if args.bottle_xy is not None:self.xy[:]=self.placement.validate(args.bottle_xy)
        self.generation=0;self.running=False;self.ready=False;self.pending=False;self.chunk=None;self.fatal=False
        self.history=deque(maxlen=10);self.last=np.zeros(29);self.frames=0;self.model_calls=0;self.latency=0.
        self.viewer=None;self.panel=None;self.closed=False;self.error='Loading/verifying fine-tuned server...'
        self.events=queue.Queue();self.renderer=mujoco.Renderer(m,height=480,width=640)
        opts=ort.SessionOptions();opts.intra_op_num_threads=2
        self.decoder_path=ROOT/'gear_sonic_deploy/policy/release/model_decoder.onnx'
        if hashlib.sha256(self.decoder_path.read_bytes()).hexdigest()!=self.profile['sonic_decoder_sha256']:
            raise ValueError('SONIC decoder differs from the model used to prepare these training labels')
        self.decoder=ort.InferenceSession(str(self.decoder_path),sess_options=opts,providers=['CPUExecutionProvider'])
        if self.decoder.get_inputs()[0].shape!=[1,994]:raise ValueError('Wrong SONIC decoder schema')
        self.worker=ModelWorker(args,self.metadata)
        self.output=Path(args.output);self.output.mkdir(parents=True,exist_ok=True)
        self.log=(self.output/'actions.jsonl').open('w')
        self.video=None;self.video_camera=None;self.last_video=-1.
        if args.video:
            import cv2
            self.video=cv2.VideoWriter(str(self.output/'policy_simulation.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),20,(640,480))
            if not self.video.isOpened():raise RuntimeError('Cannot create simulation video')
            self.video_camera=mujoco.MjvCamera();mujoco.mjv_defaultCamera(self.video_camera)
            self.video_camera.lookat[:]=[.25,0.,.85];self.video_camera.distance=1.8;self.video_camera.azimuth=135.;self.video_camera.elevation=-20.
        self.reset()
    def reset(self):
        m,d,np,mj=self.model,self.data,self.np,self.mj
        self.generation+=1;self.running=False;self.pending=False;self.chunk=None
        while True:
            try:self.worker.requests.get_nowait()
            except queue.Empty:break
        mj.mj_resetData(m,d);d.qpos[:]=self.home;d.qpos[self.bottle_qa:self.bottle_qa+2]=self.xy
        d.qvel[:]=0;d.ctrl[:]=0;d.xfrc_applied[:]=0;d.qfrc_applied[:]=0;mj.mj_forward(m,d)
        self.initial_z=float(d.qpos[self.bottle_qa+2]);self.peak_lift=0.;self.longest_hold=0.;self.hold=0.
        self.history.clear();self.last=np.zeros(29);self.frames=0;self.model_calls=0;self.last_video=-1.
        self.body_target=d.qpos[self.bq].copy();self.hand_target=d.qpos[self.hq].copy()
        self.error='' if self.ready else 'Loading/verifying fine-tuned server...'
        self.trace('reset')
    def trace(self,event,**fields):
        if hasattr(self,'log'):
            self.log.write(json.dumps(dict(event=event,wall_time=time.time(),sim_time=float(self.data.time),generation=self.generation,**fields))+'\n');self.log.flush()
    def start(self):
        if self.ready and not self.running:
            self.running=True;self.error='';self.trace('start')
    def observation(self):
        m,d,np=self.model,self.data,self.np
        self.mj.mj_forward(m,d)  # RGB and joint state must describe the same physics state.
        self.renderer.update_scene(d,camera='head_camera');rgb=self.renderer.render().copy()
        state={}
        for name,names in self.profile['state_joint_groups'].items():
            values=d.qpos[[int(m.joint(j).qposadr[0]) for j in names]].copy()
            if name=='left_hand':values[:2]=values[2:4]  # Same left-finger coupling as training observations.
            state[name]=values.astype('float32')[None,None]
        rotation=np.zeros(9);self.mj.mju_quat2Mat(rotation,d.qpos[self.root_qa+3:self.root_qa+7])
        state['projected_gravity']=(rotation.reshape(3,3).T@np.array([0.,0.,-1.])).astype('float32')[None,None]
        return dict(video={'ego_view':rgb[None,None]},state=state,language={'annotation.human.task_description':[[self.args.prompt]]})
    def pump_results(self):
        from gear_sonic.utils.inference.policy_control import policy_action_step
        while True:
            try:item=self.worker.results.get_nowait()
            except queue.Empty:break
            if item[0]=='ready':
                self.ready=True;self.error='';self.trace('verified_server',checkpoint=item[1]['checkpoint_fingerprint'])
            elif item[0]=='fatal':self.error=item[1];self.running=False;self.ready=False;self.fatal=True
            elif item[1]==self.generation:
                self.pending=False
                if item[0]=='error':self.error=item[2];self.running=False;self.trace('error',message=self.error)
                else:
                    # Validate the complete chunk before any action reaches physics.
                    for i in range(40):policy_action_step(item[2],i)
                    key='motion_token' if 'motion_token' in item[2] else 'action.motion_token'
                    if self.np.asarray(item[2][key]).shape!=(1,40,64):raise ValueError('Expected exactly one 40-step policy chunk')
                    self.chunk=item[2];self.chunk_index=0;self.latency=item[3];self.model_calls+=1
                    self.trace('model_reply',latency_s=self.latency)
    def next_control_tick(self):
        from gear_sonic.utils.inference.policy_control import policy_action_step
        if not self.running:return False
        if self.chunk is None:
            if not self.pending:
                observation=self.observation()
                self.trace('model_request',policy_inputs=list(observation),
                           state={k:v.tolist() for k,v in observation['state'].items()},
                           rgb_sha256=hashlib.sha256(observation['video']['ego_view'].tobytes()).hexdigest())
                self.worker.requests.put_nowait((self.generation,observation));self.pending=True
            return False
        token,left,right,index=policy_action_step(self.chunk,self.chunk_index)
        m,d,np,mj=self.model,self.data,self.np,self.mj
        rot=np.zeros(9);mj.mju_quat2Mat(rot,d.qpos[self.root_qa+3:self.root_qa+7]);rot=rot.reshape(3,3)
        current=(d.qvel[self.root_va+3:self.root_va+6].copy(),d.qpos[self.bq].copy()-self.default,d.qvel[self.bv].copy(),self.last.copy(),rot.T@np.array([0.,0.,-1.]))
        if not self.history:self.history.extend([current]*9)
        self.history.append(current)
        obs=np.concatenate([token]+[np.concatenate([h[k] for h in self.history]) for k in range(5)]).astype('float32')[None]
        self.last=self.decoder.run(None,{'obs_dict':obs})[0][0]
        if not np.isfinite(self.last).all():raise ValueError('SONIC produced non-finite commands')
        self.body_target=self.default+self.scale*self.last
        self.hand_target=np.r_[left,right]
        # Recorded robot trajectories/object coordinates are never read here.
        self.trace('action',chunk_index=int(index),motion_token=token.tolist(),left_hand=left.tolist(),right_hand=right.tolist(),sonic_target=self.body_target.tolist())
        for _ in range(4):
            mj.mj_forward(m,d);d.ctrl[:]=0.;d.xfrc_applied[:]=0.;d.qfrc_applied[:]=0.
            tau=self.profile['body_kp']*(self.body_target-d.qpos[self.bq])-self.profile['body_kd']*d.qvel[self.bv]+d.qfrc_bias[self.bv]
            tau[self.held]=self.profile['held_kp']*(self.held_home[self.bq[self.held]]-d.qpos[self.bq[self.held]])-self.profile['held_kd']*d.qvel[self.bv[self.held]]+d.qfrc_bias[self.bv[self.held]]
            hand=self.profile['hand_kp']*(self.hand_target-d.qpos[self.hq])-self.profile['hand_kd']*d.qvel[self.hv]+d.qfrc_bias[self.hv]
            d.ctrl[self.bmot]=np.clip(tau,m.actuator_ctrlrange[self.bmot,0],m.actuator_ctrlrange[self.bmot,1])
            d.ctrl[self.hmot]=np.clip(hand,m.actuator_ctrlrange[self.hmot,0],m.actuator_ctrlrange[self.hmot,1])
            lift=float(d.qpos[self.bottle_qa+2]-self.initial_z);self.peak_lift=max(self.peak_lift,lift)
            fingers=set()
            for c in d.contact:
                bodies=[int(m.geom_bodyid[g]) for g in (c.geom1,c.geom2)]
                if self.bottle_body in bodies:
                    other=bodies[1] if bodies[0]==self.bottle_body else bodies[0]
                    for finger in ('thumb','index','middle'):
                        if (m.body(other).name or '').startswith('right_hand_'+finger):fingers.add(finger)
            bottle_rot=np.zeros(9);mj.mju_quat2Mat(bottle_rot,d.qpos[self.bottle_qa+3:self.bottle_qa+7])
            grasp=lift>.12 and 'thumb' in fingers and bool(fingers & {'index','middle'}) and bottle_rot[8]>.85
            self.hold=self.hold+m.opt.timestep if grasp else 0.;self.longest_hold=max(self.longest_hold,self.hold)
            if self.video is not None and d.time-self.last_video>=.05-1e-9:
                import cv2
                self.renderer.update_scene(d,camera=self.video_camera)
                self.video.write(cv2.cvtColor(self.renderer.render(),cv2.COLOR_RGB2BGR));self.last_video=float(d.time)
            mj.mj_step(m,d)
        if not np.isfinite(d.qpos).all():raise ValueError('Non-finite simulation state')
        self.frames+=1;self.chunk_index+=1
        if self.chunk_index>=self.args.execute_steps:self.chunk=None
        return True
    def report(self,status):
        return dict(status=status,model_path=self.metadata['model_path'],checkpoint_fingerprint=self.metadata['checkpoint_fingerprint'],
            server_verified=self.ready,
            execution_profile_id=PROFILE,control_pipeline='fine-tuned GR00T -> SONIC ONNX -> MuJoCo PD',
            rgb_depth_ik=False,detector_enabled=False,ik_enabled=False,recorded_actions_used=False,hand_adapter='none / native Dex3 radians',
            policy_observation_keys=['video','state','language'],
            sonic_controlled_joints=[n for n,selected in zip(self.profile['body_joint_names'],self.moving) if selected],
            held_joint_count=int(self.held.sum()),diffusion_steps=self.args.diffusion_steps,
            execute_steps=self.args.execute_steps,sampling_seed=self.args.sampling_seed,
            forbidden_modules_loaded=[name for name in sys.modules if name.startswith(('gear_sonic.utils.mujoco_sim.assisted_pickup','gear_sonic.scripts.run_bottle_detector','gear_sonic.scripts.refine_sonic_episode','gear_sonic.scripts.run_blue_bottle_pickup'))],
            model_calls=self.model_calls,decoder_steps=self.frames,simulation_time_s=float(self.data.time),
            peak_bottle_lift_m=self.peak_lift,final_bottle_lift_m=float(self.data.qpos[self.bottle_qa+2]-self.initial_z),
            opposed_contact_hold_s=self.longest_hold,pickup_success=self.longest_hold>=1. and float(self.data.qpos[self.bottle_qa+2]-self.initial_z)>.10,error=self.error,
            bottle_xy=self.xy.tolist(),last_inference_latency_s=self.latency)
    def close(self):
        self.worker.stop.set()
        if self.video is not None:self.video.release()
        # Free GL resources while their owning context still exists.
        if self.renderer._gl_context:self.renderer._gl_context.make_current()
        if self.renderer._mjr_context:
            self.renderer._mjr_context.free();self.renderer._mjr_context=None
        self.renderer.close()
        if self.viewer is not None:self.viewer.close()
        self.log.close()


def simulate(args):
    import mujoco
    simulation=LearnedSimulation(args);panel=None;closing=False
    started=time.monotonic();last_render=0.;last_status=0.;next_tick=0.;auto_started=False
    try:
        if not args.headless:
            import tkinter as tk
            from tkinter import ttk
            panel=tk.Tk();panel.title('Fine-tuned GR00T -> SONIC | Dex3')
            ttk.Label(panel,text='RGB + robot state -> new GR00T -> SONIC -> MuJoCo').pack(padx=12,pady=8)
            ttk.Label(panel,text='RGB-D / YOLO / IK OFF | Hands: native Dex3').pack()
            frame=ttk.Frame(panel);frame.pack(pady=8)
            xv=tk.StringVar(value=str(simulation.xy[0]));yv=tk.StringVar(value=str(simulation.xy[1]))
            for label,value in [('Bottle X',xv),('Bottle Y',yv)]:
                ttk.Label(frame,text=label).pack(side='left');ttk.Entry(frame,textvariable=value,width=9).pack(side='left',padx=4)
            def place():
                if simulation.running:simulation.error='Reset before changing bottle X/Y';return
                try:
                    xy=simulation.np.array([float(xv.get()),float(yv.get())])
                    if not simulation.np.isfinite(xy).all():raise ValueError('X/Y must be finite')
                    simulation.xy[:]=simulation.placement.validate(xy);simulation.reset()
                except ValueError as exc:simulation.error=str(exc)
            ttk.Button(panel,text='Apply bottle X/Y (scene only)',command=place).pack()
            buttons=ttk.Frame(panel);buttons.pack(pady=8)
            start_button=ttk.Button(buttons,text='Start (F6)',command=simulation.start);start_button.pack(side='left',padx=5)
            ttk.Button(buttons,text='Reset all (F5)',command=simulation.reset).pack(side='left',padx=5)
            status=tk.StringVar();ttk.Label(panel,textvariable=status,wraplength=520).pack(padx=12,pady=8)
            def close():
                nonlocal closing
                closing=True
            panel.protocol('WM_DELETE_WINDOW',close)
            panel.bind('<F6>',lambda e:simulation.start());panel.bind('<F5>',lambda e:simulation.reset())
            def key(k):
                if k==295:simulation.events.put('start')
                elif k==294 or k in (ord('R'),ord('r')):simulation.events.put('reset')
            simulation.viewer=PolicyViewer(simulation,key)
            simulation.viewer.cam.lookat[:]=[.25,0.,.85];simulation.viewer.cam.distance=1.8
            simulation.viewer.cam.azimuth=135.;simulation.viewer.cam.elevation=-20.
        while not closing:
            simulation.pump_results()
            while not simulation.events.empty():
                getattr(simulation,simulation.events.get_nowait())()
            if args.auto_start and simulation.ready and not auto_started:
                simulation.start();auto_started=True
            now=time.monotonic()
            if simulation.running and (args.headless or now>=next_tick):
                if simulation.next_control_tick():next_tick=time.monotonic()+.02
            if args.headless and simulation.fatal:raise RuntimeError(simulation.error)
            if simulation.error and args.headless and simulation.ready and not simulation.running:raise RuntimeError(simulation.error)
            if simulation.data.time>=args.duration and args.duration>0:break
            if now-started>args.max_wall_seconds and args.headless:raise TimeoutError('Headless run exceeded wall-time limit')
            if panel is not None and now-last_render>.033:
                if not simulation.viewer.is_running():break
                simulation.viewer.sync()
                start_button.configure(state='normal' if simulation.ready and not simulation.running else 'disabled')
                status.set(f"{'RUNNING' if simulation.running else 'WAITING'} | sim {simulation.data.time:.2f}s | model calls {simulation.model_calls}\n"
                           f"Policy latency {simulation.latency:.3f}s | lift {simulation.peak_lift*100:.1f}cm\n{simulation.error}")
                panel.update();last_render=now
            if now-last_status>1.:
                report=simulation.report('running' if simulation.running else 'standby')
                write_report(simulation.output/'run_report.json',report);last_status=now
            time.sleep(.001)
        report=simulation.report('complete');write_report(simulation.output/'run_report.json',report)
        print(json.dumps(report,indent=2),flush=True)
    except Exception as exc:
        simulation.error=str(exc);report=simulation.report('failed')
        write_report(simulation.output/'run_report.json',report);raise
    finally:
        simulation.close()
        if panel is not None:panel.destroy()


def launch(args):
    checkpoint_metadata(args.model_path)
    output=Path(args.output).resolve();output.mkdir(parents=True,exist_ok=True)
    port=args.policy_port
    if not args.external_server:
        for candidate in range(port,port+20):
            with socket.socket() as s:
                try:s.bind((args.policy_host,candidate));port=candidate;break
                except OSError:continue
        else:raise RuntimeError('No free policy port found')
    args.policy_port=port
    common=['--model-path',str(Path(args.model_path).resolve()),'--policy-host',args.policy_host,'--policy-port',str(port),
            '--prompt',args.prompt,'--execute-steps',str(args.execute_steps),'--duration',str(args.duration),
            '--max-wall-seconds',str(args.max_wall_seconds),'--output',str(output),
            '--diffusion-steps',str(args.diffusion_steps),'--sampling-seed',str(args.sampling_seed)]
    env=dict(os.environ,HF_HUB_OFFLINE='1',TOKENIZERS_PARALLELISM='false',NO_ALBUMENTATIONS_UPDATE='1',
             PYTHONPATH=str(ROOT)+os.pathsep+str(ROOT.parent/'Isaac-GR00T'))
    owned=None;sim=None;log=None
    try:
        if not args.external_server:
            log=(output/'server.log').open('w')
            owned=subprocess.Popen([str(ROOT.parent/'Isaac-GR00T/.venv/bin/python'),str(Path(__file__).resolve()),'--mode','server',
                '--device',args.device,*common],env=env,stdout=log,stderr=subprocess.STDOUT)
        sim_args=[str(ROOT/'.venv_sim/bin/python'),str(Path(__file__).resolve()),'--mode','sim',*common]
        for flag in ('headless','auto_start','video'):
            if getattr(args,flag):sim_args.append('--'+flag.replace('_','-'))
        if args.bottle_xy is not None:sim_args+=['--bottle-xy',*[str(x) for x in args.bottle_xy]]
        if args.headless:env['MUJOCO_GL']='egl'
        print(f'Fine-tuned policy server: {args.policy_host}:{port}\nModel: {args.model_path}\nLogs: {output}\nRGB-D/IK OFF; native Dex3; Start F6 / Reset F5.',flush=True)
        sim=subprocess.Popen(sim_args,env=env)
        while sim.poll() is None:
            if owned is not None and owned.poll() is not None:raise RuntimeError(f'Policy server stopped. Read {output/"server.log"}')
            time.sleep(.2)
        if sim.returncode:raise RuntimeError(f'Simulator exited {sim.returncode}; read {output/"run_report.json"}')
    finally:
        for process in (sim,owned):
            if process is not None and process.poll() is None:
                process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait()
        if log is not None:log.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=['run','server','sim'],default='run')
    p.add_argument('--model-path',default=str(ROOT/'outputs/gr00t_g1_dex3_finetune_v1/checkpoint-best'))
    p.add_argument('--policy-host',default='127.0.0.1');p.add_argument('--policy-port',type=int,default=5551)
    p.add_argument('--device',default='cuda:0');p.add_argument('--prompt',default='grab the bottle')
    p.add_argument('--diffusion-steps',type=int,default=16,help='Flow-matching integration steps during model inference')
    p.add_argument('--sampling-seed',type=int,default=42,help='Fixed inference noise for repeatable actions; -1 uses fresh noise')
    p.add_argument('--external-server',action='store_true');p.add_argument('--bottle-xy',nargs=2,type=float)
    p.add_argument('--headless',action='store_true');p.add_argument('--auto-start',action='store_true')
    p.add_argument('--video',action='store_true',help='Save a 20 FPS video of actual policy-controlled physics')
    p.add_argument('--execute-steps',type=int,default=10,help='Execute this many 50Hz actions before a fresh model query')
    p.add_argument('--duration',type=float,default=0.,help='Stop after this many simulation seconds; 0 keeps GUI open')
    p.add_argument('--max-wall-seconds',type=float,default=240.)
    p.add_argument('--output',default=str(ROOT/'outputs/finetuned_policy_sim'/time.strftime('session_%Y%m%d_%H%M%S')))
    a=p.parse_args()
    if not 1<=a.execute_steps<=40:p.error('execute-steps must be 1..40')
    if not 1<=a.diffusion_steps<=64:p.error('diffusion-steps must be 1..64')
    if a.headless and (not a.auto_start or a.duration<=0):p.error('headless requires --auto-start and --duration > 0')
    if a.headless:os.environ.setdefault('MUJOCO_GL','egl')
    {'run':launch,'server':serve,'sim':simulate}[a.mode](a)

if __name__=='__main__':main()
