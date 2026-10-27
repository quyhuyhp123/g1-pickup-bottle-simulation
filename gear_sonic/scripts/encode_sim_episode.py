"""Generate candidate SONIC G1-mode tokens, NOT a training-ready dataset.

Matches legacy deploy observation_config.yaml gatherer layout. Offline reference
heading is kept in recorded world coordinates (no additional heading offset).
Decoder closed-loop validation remains required.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import mujoco
import numpy as np
import onnxruntime as ort
import yaml

ROOT = Path(__file__).resolve().parents[2]
DIMS = dict(encoder_mode_4=4, motion_joint_positions_10frame_step5=290,
    motion_joint_velocities_10frame_step5=290, motion_root_z_position_10frame_step5=10,
    motion_root_z_position=1, motion_anchor_orientation=6,
    motion_anchor_orientation_10frame_step5=60,
    motion_joint_positions_lowerbody_10frame_step5=120,
    motion_joint_velocities_lowerbody_10frame_step5=120, vr_3point_local_target=9,
    vr_3point_local_orn_target=12, smpl_joints_10frame_step1=720,
    smpl_anchor_orientation_10frame_step1=60, motion_joint_positions_wrists_10frame_step1=60)


def body_order():
    tree = ast.parse((ROOT/'gear_sonic/envs/manager_env/robots/g1.py').read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id=='G1_ISAACLAB_JOINTS' for t in node.targets):
            return ast.literal_eval(node.value)[1:]
    raise ValueError('IsaacLab body ordering unavailable')


def encode(episode, model_path, config_path):
    episode, model_path, config_path = map(Path, (episode, model_path, config_path))
    meta = json.loads((episode/'meta.json').read_text())
    replay = json.loads((episode/'replay_report.json').read_text())
    if meta['status'] != 'complete' or not replay['trajectory_match']:
        raise ValueError('Requires a completed episode with matching physical replay')
    cfg = yaml.safe_load(config_path.read_text())['encoder']
    offsets, dim = {}, 0
    for field in cfg['encoder_observations']:
        if field.get('enabled', True):
            offsets[field['name']] = dim
            dim += DIMS[field['name']]  # Reject unsupported layouts instead of guessing.
    required = next(m for m in cfg['encoder_modes'] if m['name']=='g1')['required_observations']
    expected = {'encoder_mode_4', 'motion_joint_positions_10frame_step5',
                'motion_joint_velocities_10frame_step5', 'motion_anchor_orientation_10frame_step5'}
    if set(required) != expected:
        raise ValueError('Unsupported G1 mode schema')
    options = ort.SessionOptions(); options.intra_op_num_threads = 2
    session = ort.InferenceSession(str(model_path), sess_options=options, providers=['CPUExecutionProvider'])
    if session.get_inputs()[0].shape != [1, dim] or session.get_outputs()[0].shape != [1, 64]:
        raise ValueError('ONNX shape does not match observation config')
    model = mujoco.MjModel.from_xml_path(str(episode/'model.xml'))
    names = body_order()
    joints = np.array([int(model.body(n).jntadr[0]) for n in names])
    if len(joints)!=29 or len(set(joints))!=29 or np.any(model.jnt_type[joints]!=mujoco.mjtJoint.mjJNT_HINGE):
        raise ValueError('Invalid 29-joint mapping')
    chunks = []
    for file in sorted(episode.glob('states_*.npz')):
        with np.load(file) as z:
            chunks.append({k:z[k].copy() for k in ('sim_time','qpos','qvel')})
    arrays = {k:np.concatenate([z[k] for z in chunks]) for k in chunks[0]}
    dt = float(meta['timestep']); stride = round(.02/dt)
    if stride<1 or not np.isclose(stride*dt,.02) or not np.allclose(np.diff(arrays['sim_time']),dt):
        raise ValueError('Expected contiguous simulation samples divisible into 50 Hz')
    rows = np.arange(0, len(arrays['qpos']), stride)
    q = arrays['qpos'][rows][:,model.jnt_qposadr[joints]]
    dq = arrays['qvel'][rows][:,model.jnt_dofadr[joints]]
    root = int(model.joint('floating_base_joint').qposadr[0])
    quat = arrays['qpos'][rows, root+3:root+7]
    rotations = []
    for v in quat:
        r = np.zeros(9); mujoco.mju_quat2Mat(r,v); rotations.append(r.reshape(3,3))
    rotations = np.asarray(rotations)
    inputs, tokens = [], []
    for i in range(len(rows)):
        future = np.minimum(i+np.arange(10)*5,len(rows)-1)
        x = np.zeros((1,dim),np.float32)
        values = dict(encoder_mode_4=np.zeros(4), motion_joint_positions_10frame_step5=q[future].ravel(),
            motion_joint_velocities_10frame_step5=dq[future].ravel(),
            motion_anchor_orientation_10frame_step5=(rotations[i].T @ rotations[future])[...,:2].reshape(-1))
        for key,v in values.items(): x[0,offsets[key]:offsets[key]+len(v)]=v
        token = session.run(None,{session.get_inputs()[0].name:x})[0]
        if not np.isfinite(token).all(): raise ValueError('Non-finite encoder output')
        inputs.append(x[0]); tokens.append(token[0])
    out = episode/'sonic_candidate'; out.mkdir(exist_ok=True)
    np.savez_compressed(out/'tokens.npz', motion_token=np.asarray(tokens), encoder_input=np.asarray(inputs),
        sim_time=arrays['sim_time'][rows], source_row=rows,
        full_future_window=np.arange(len(rows))+45<len(rows), joint_pos=q, joint_vel=dq)
    report = dict(training_ready=False, sonic_validated=False, mode='g1', fps=50, tokens=len(tokens),
        token_shape=list(np.asarray(tokens).shape), input_dimension=dim,
        encoder_sha256=hashlib.sha256(model_path.read_bytes()).hexdigest(),
        config_sha256=hashlib.sha256(config_path.read_bytes()).hexdigest(),
        joint_names=[model.joint(int(j)).name for j in joints],
        heading='Recorded base-relative future orientation; identity extra heading offset',
        future_window_s=.9, tail='Clamp to final frame; use full_future_window mask',
        limitation='Finite encoder output only. Decoder/SONIC rollout and hand-label convention not validated.')
    (out/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('episode')
    p.add_argument('--encoder',default=str(ROOT/'gear_sonic_deploy/policy/release/model_encoder.onnx'))
    p.add_argument('--config',default=str(ROOT/'gear_sonic_deploy/policy/release/observation_config.yaml'))
    a=p.parse_args(); encode(a.episode,a.encoder,a.config)
