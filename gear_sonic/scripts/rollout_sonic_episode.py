"""Diagnostic closed-loop SONIC rollout; recorded hand targets, no body IK.

Stationary fixture from recorded model remains enabled. Not hardware deploy.
"""
import argparse
import ast
from collections import deque
import hashlib
import json
import operator
from pathlib import Path
import re
import mujoco
import numpy as np
import onnxruntime as ort
from gear_sonic.scripts.encode_sim_episode import ROOT


def parameters():
    text=(ROOT/'gear_sonic_deploy/src/g1/g1_deploy_onnx_ref/include/policy_parameters.hpp').read_text()
    text=re.sub(r'/\*.*?\*/|//[^\n]*','',text,flags=re.S)
    values={}
    ops={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv}
    def calc(node):
        if isinstance(node,ast.Constant): return node.value
        if isinstance(node,ast.Name): return values[node.id]
        if isinstance(node,ast.UnaryOp) and isinstance(node.op,ast.USub): return -calc(node.operand)
        if isinstance(node,ast.BinOp): return ops[type(node.op)](calc(node.left),calc(node.right))
        raise ValueError('Unsupported parameter expression')
    for name,expr in re.findall(r'const double (\w+)\s*=\s*([^;]+);',text):
        values[name]=calc(ast.parse(expr.strip(),mode='eval').body)
    for name in ('default_angles','g1_action_scale','kps','kds','mujoco_to_isaaclab'):
        expr=re.search(r'\b'+name+r'\s*=\s*\{([^}]+)\}',text).group(1)
        values[name]=np.array([calc(ast.parse(e.strip(),mode='eval').body) for e in expr.split(',') if e.strip()])
    return values


def manipulation_mask(names):
    allowed = {'waist_pitch_joint'} | {'right_'+part+'_joint' for part in
        ('shoulder_pitch','shoulder_roll','shoulder_yaw','elbow','wrist_roll','wrist_pitch','wrist_yaw')}
    if not allowed.issubset(set(names)):
        raise ValueError('Missing manipulation joints')
    return np.array([n in allowed for n in names])


def rollout(episode, arm_bias=True, history_seed="repeat", body_control="auto",
            start_stage=None, controller="sonic", target_source="decoder",
            tokens_file=None, output_dir=None, token_refiner=None, pickup_only=False,
            video_path=None):
    p=Path(episode); meta=json.loads((p/'meta.json').read_text())
    candidate=json.loads((p/'sonic_candidate/report.json').read_text())
    with np.load(tokens_file or p/'sonic_candidate/tokens.npz') as z:
        tokens=z['motion_token'].copy(); rows=z['source_row'].copy()
    chunks=[]
    for f in sorted(p.glob('states_*.npz')):
        with np.load(f) as z: chunks.append({k:z[k].copy() for k in ('qpos','qvel','assisted_hand_target','assisted_arm_target','stage','sim_time','xfrc_applied','qfrc_applied') if k in z})
    raw={k:np.concatenate([c[k] for c in chunks]) for k in chunks[0]}
    m=mujoco.MjModel.from_xml_path(str(p/'model.xml')); d=mujoco.MjData(m)
    reference_probe = meta.get('kind') == 'synthetic_reference_probe_NOT_DEMONSTRATION'
    if reference_probe:
        # Earlier synthetic probes intentionally contain no recorder telemetry.
        meta.setdefault('assisted_arm_joint_ids',[
            m.joint(name).id for name,selected in zip(candidate['joint_names'],manipulation_mask(candidate['joint_names'])) if selected])
        n=len(raw['qpos'])
        raw.setdefault('stage',np.full(n,'reference'))
        raw.setdefault('sim_time',np.arange(n)*m.opt.timestep)
        raw.setdefault('xfrc_applied',np.zeros((n,m.nbody,6)))
        raw.setdefault('qfrc_applied',np.zeros((n,m.nv)))
        raw.setdefault('assisted_arm_target',raw['qpos'][:,m.jnt_qposadr[meta['assisted_arm_joint_ids']]])
    end_row=len(raw['qpos'])
    if pickup_only:
        terminal=np.flatnonzero(np.isin(raw['stage'],['transfer','lower','release','retreat','return_home','done','failed']))
        if len(terminal):end_row=int(terminal[0])
        keep=rows<end_row;rows=rows[keep];tokens=tokens[keep]
    with np.load(p/'initial_state.npz') as z:
        for k in ('qpos','qvel','act','eq_active','mocap_pos','mocap_quat'): getattr(d,k)[:]=z[k]
        d.time=float(z['sim_time'])
    initial_qpos=d.qpos.copy()
    if start_stage:
        matches=np.flatnonzero(raw['stage']==start_stage)
        if not len(matches): raise ValueError('Requested start stage absent')
        first=int(np.searchsorted(rows,matches[0]))
        rows=rows[first:];tokens=tokens[first:]
        if not len(rows):raise ValueError('No token rows in requested phase window')
        d.qpos[:]=raw['qpos'][rows[0]];d.qvel[:]=raw['qvel'][rows[0]]
        d.time=float(raw['sim_time'][rows[0]])
    mujoco.mj_forward(m,d)
    if not start_stage:
        with np.load(p/'initial_state.npz') as z:
            if 'qacc_warmstart' in z:d.qacc_warmstart[:]=z['qacc_warmstart']
    if body_control == 'auto':
        body_control = 'full' if reference_probe else 'manipulation'
    if body_control == 'manipulation' and not np.any(d.eq_active):
        raise ValueError('Manipulation mode requires the recorded base fixture')
    param=parameters(); order=param['mujoco_to_isaaclab'].astype(int)
    default,scale,kp,kd=[param[k][order] for k in ('default_angles','g1_action_scale','kps','kds')]
    joints=np.array([m.joint(n).id for n in candidate['joint_names']]);qa=m.jnt_qposadr[joints];va=m.jnt_dofadr[joints]
    def actuators(js):
        return np.array([np.flatnonzero(m.actuator_trnid[:,0]==j).item() for j in js])
    motors=actuators(joints)
    if controller not in ('sonic','collection') or target_source not in ('decoder','expert'):
        raise ValueError('Unknown controller/target source')
    if (controller=='collection' or target_source=='expert' or token_refiner is not None) and body_control!='manipulation':
        raise ValueError('Collection/refinement diagnostic requires fixed-base manipulation')
    home_body=initial_qpos[qa].copy()
    moving=manipulation_mask(candidate['joint_names']) if body_control == 'manipulation' else np.ones(29,dtype=bool)
    held=~moving
    held_drift=[]; base_drift=[]; initial_base=d.qpos[:3].copy(); applied_targets=[]
    hands=np.array([i for i in range(m.njnt) if '_hand_' in (m.joint(i).name or '')]);hm=actuators(hands)
    hq=m.jnt_qposadr[hands];hv=m.jnt_dofadr[hands];hand_target=initial_qpos[hq].copy()
    right=meta['assisted_hand_joint_ids']; right_slots=[list(hands).index(j) for j in right]
    arm=np.array(['shoulder' in n or 'elbow' in n or 'wrist' in n for n in candidate['joint_names']])
    root=m.joint('floating_base_joint');rootqa=int(root.qposadr[0]);rootva=int(root.dofadr[0])
    bottle=int(m.joint('red_bottle_free_joint').qposadr[0]);z0=d.qpos[bottle+2]
    history=deque(maxlen=10);last=np.zeros(29);trace=[]; details=[]
    arm_slots=[list(joints).index(j) for j in meta['assisted_arm_joint_ids']]
    bottle_body=int(m.jnt_bodyid[m.joint('red_bottle_free_joint').id])
    grasp_hold_s=0.;longest_grasp_hold_s=0.;refined=[];decoder_obs=[]
    first_active=int(np.flatnonzero(raw['stage']!='idle')[0]) if np.any(raw['stage']!='idle') else len(raw['stage'])
    def contact_grasp():
        groups=set()
        for c in d.contact:
            bodies=[int(m.geom_bodyid[g]) for g in (c.geom1,c.geom2)]
            if bottle_body in bodies:
                other=bodies[1] if bodies[0]==bottle_body else bodies[0]
                name=m.body(other).name or ''
                for finger in ('thumb','index','middle'):
                    if name.startswith('right_hand_'+finger):groups.add(finger)
        return 'thumb' in groups and bool(groups & {'index','middle'})
    path=ROOT/'gear_sonic_deploy/policy/release/model_decoder.onnx'
    opts=ort.SessionOptions();opts.intra_op_num_threads=2
    decoder=ort.InferenceSession(str(path),sess_options=opts,providers=['CPUExecutionProvider'])
    if decoder.get_inputs()[0].shape != [1,994]: raise ValueError('Unsupported decoder shape')
    stride=round(.02/m.opt.timestep)
    if not np.isclose(stride*m.opt.timestep,.02): raise ValueError('Invalid timestep')
    if not len(rows) or np.any(np.diff(rows)!=stride) or np.any(rows<0) or rows[-1]>=len(raw['qpos']):
        raise ValueError('Token rows must be contiguous at 50Hz within this episode')
    renderer=writer=camera=None
    if video_path:
        import cv2
        video_path=Path(video_path);video_path.parent.mkdir(parents=True,exist_ok=True)
        renderer=mujoco.Renderer(m,height=480,width=640)
        camera=mujoco.MjvCamera();mujoco.mjv_defaultCamera(camera)
        camera.lookat[:]=[.25,0.,.85];camera.distance=1.8;camera.azimuth=135.;camera.elevation=-20.
        writer=cv2.VideoWriter(str(video_path),cv2.VideoWriter_fourcc(*'mp4v'),20,(640,480))
        if not writer.isOpened():renderer.close();raise RuntimeError('Cannot open rollout video')
    for t,row in enumerate(rows):
        rot=np.zeros(9);mujoco.mju_quat2Mat(rot,d.qpos[rootqa+3:rootqa+7]);rot=rot.reshape(3,3)
        current=(d.qvel[rootva+3:rootva+6].copy(),d.qpos[qa].copy()-default,
                 d.qvel[va].copy(),last.copy(),rot.T @ np.array([0.,0.,-1.]))
        if not history:
            seed = current if history_seed == 'repeat' else tuple(np.zeros_like(v) for v in current)
            if history_seed == 'zero': seed = (*seed[:4], np.array([0.,0.,-1.]))
            history.extend([seed]*9)
        history.append(current)
        obs=np.concatenate([tokens[t]]+[np.concatenate([h[k] for h in history]) for k in range(5)]).astype(np.float32)[None]
        if token_refiner is not None:
            obs[0,:64]=token_refiner(t,int(row),obs[0].copy(),raw['assisted_arm_target'][row].copy(),np.asarray(arm_slots),default,scale)
        refined.append(obs[0,:64].copy());decoder_obs.append(obs[0].copy())
        last=decoder.run(None,{decoder.get_inputs()[0].name:obs})[0][0]
        if not np.isfinite(last).all(): raise ValueError('Non-finite decoder action')
        target=default+scale*last
        if target_source=='expert':
            target[arm_slots]=raw['assisted_arm_target'][row] if raw['stage'][row]!='idle' else home_body[arm_slots]
        applied_target=target.copy()
        applied_target[held]=home_body[held]
        applied_targets.append(applied_target.copy())
        details.append(np.stack([raw['qpos'][row,qa], d.qpos[qa].copy(), target.copy()]))
        for step in range(min(stride,end_row-row)):
            index=row+step
            # Raw v1 can retain stale targets while its controller is inactive.
            # Idle targets must never close the hand or move the arm.
            active=raw['stage'][index]!='idle'
            if active:hand_target[right_slots]=raw['assisted_hand_target'][index]
            # Recorded startup support only; no external task force is replayed.
            d.xfrc_applied[:]=0.;d.qfrc_applied[:]=0.
            if index<first_active:
                d.xfrc_applied[:]=raw['xfrc_applied'][index]
                d.qfrc_applied[:]=raw['qfrc_applied'][index]
            mujoco.mj_forward(m,d)
            d.ctrl[:]=0
            if target_source=='expert' and active:target[arm_slots]=raw['assisted_arm_target'][index]
            tau=kp*(target-d.qpos[qa])-kd*d.qvel[va]
            if arm_bias: tau[arm]+=d.qfrc_bias[va[arm]]
            if controller=='collection':
                tau[moving]=80.*(target[moving]-d.qpos[qa[moving]])-3.*d.qvel[va[moving]]+d.qfrc_bias[va[moving]]
                if not active:tau[moving]=100.*(home_body[moving]-d.qpos[qa[moving]])-4.*d.qvel[va[moving]]+d.qfrc_bias[va[moving]]
            # Match fixed-pickup collection: unused joints held by PD, not qpos overwrite.
            tau[held]=100.*(home_body[held]-d.qpos[qa[held]])-4.*d.qvel[va[held]]+d.qfrc_bias[va[held]]
            held_drift.append(float(np.max(np.abs(d.qpos[qa[held]]-home_body[held]))) if held.any() else 0.)
            base_drift.append(float(np.linalg.norm(d.qpos[:3]-initial_base)))
            d.ctrl[motors]=np.clip(tau,m.actuator_ctrlrange[motors,0],m.actuator_ctrlrange[motors,1])
            ht=8*(hand_target-d.qpos[hq])-.2*d.qvel[hv]+d.qfrc_bias[hv]
            d.ctrl[hm]=np.clip(ht,m.actuator_ctrlrange[hm,0],m.actuator_ctrlrange[hm,1])
            bottle_rot=np.zeros(9);mujoco.mju_quat2Mat(bottle_rot,d.qpos[bottle+3:bottle+7])
            lifted=(d.qpos[bottle+2]-z0)>.12
            grasp_hold_s=grasp_hold_s+m.opt.timestep if lifted and contact_grasp() and bottle_rot[8]>.85 else 0.
            longest_grasp_hold_s=max(longest_grasp_hold_s,grasp_hold_s)
            trace.append([d.time,float(np.max(np.abs(d.qpos[qa]-raw['qpos'][index,qa]))),
                float(np.linalg.norm(d.qpos[bottle:bottle+3]-raw['qpos'][index,bottle:bottle+3])),d.qpos[bottle+2]-z0])
            if renderer is not None and (len(trace)-1)%max(1,round(1/(20*m.opt.timestep)))==0:
                renderer.update_scene(d,camera=camera)
                writer.write(cv2.cvtColor(renderer.render(),cv2.COLOR_RGB2BGR))
            mujoco.mj_step(m,d)
            if not np.isfinite(d.qpos).all(): raise ValueError('Non-finite rollout state')
    if writer is not None:writer.release();renderer.close()
    a=np.array(trace)
    reference_probe = meta.get('kind') == 'synthetic_reference_probe_NOT_DEMONSTRATION'
    result=dict(episode=str(p),steps=len(a),max_joint_error_rad=float(a[:,1].max()),
        max_bottle_error_m=float(a[:,2].max()),peak_lift_m=float(a[:,3].max()),final_lift_m=float(a[-1,3]),
        trajectory_match=bool(a[:,1].max()<.05 and a[:,2].max()<.02),
        training_ready=False,sonic_validated=False,arm_bias=arm_bias,
        controller=controller,target_source=target_source,start_stage=start_stage,
        pickup_only=pickup_only,end_source_row_exclusive=end_row,
        video_path=str(video_path) if video_path else None,
        token_source=str(tokens_file or p/'sonic_candidate/tokens.npz'),
        token_refinement_online=token_refiner is not None,
        longest_opposed_contact_lift_hold_s=longest_grasp_hold_s,
        grasp_lift_success=bool(longest_grasp_hold_s>=1. and a[-1,3]>.10),
        body_control=body_control,sonic_controlled_joints=np.array(candidate['joint_names'])[moving].tolist(),
        held_joints=np.array(candidate['joint_names'])[held].tolist(),
        max_held_joint_drift_rad=max(held_drift),max_base_translation_m=max(base_drift),
        previous_action_history='Raw decoder actions retained as in deploy; held motor targets overridden downstream',
        decoder_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        conditions=f'Diagnostic at 50Hz; active equalities: {int(np.count_nonzero(d.eq_active))}; recorded hand targets; target_source={target_source}; controller={controller}; no IK or recorded body ctrl; only pre-task startup support forces restored.',
        limitations='History seeded by repeating initial state with zero previous action; offline tokens use expert base orientation, not rollout base; DDS timing/gain overrides not reproduced.')
    if reference_probe:
        for key in ('max_bottle_error_m','peak_lift_m','final_lift_m','trajectory_match'):
            result.pop(key, None)
        result['reference_probe'] = True
        result['physics_reference_validated'] = False
        result['notes'] = 'Free-base reference diagnostic; bottle metrics not applicable. Not a demonstration or verified deploy reproduction.'
    details=np.asarray(details)
    per_joint=np.max(np.abs(details[:,1]-details[:,0]),axis=0)
    worst=int(np.argmax(per_joint))
    exceed=np.argwhere(np.abs(details[:,1]-details[:,0])>.05)
    result.update(history_seed=history_seed,worst_joint=candidate['joint_names'][worst],
        first_error_over_005rad_s=float(exceed[0,0]*.02) if len(exceed) else None,
        per_joint_max_error_rad=dict(zip(candidate['joint_names'],per_joint.tolist())))
    out=Path(output_dir) if output_dir else p/'sonic_candidate'/('rollout_'+body_control+'_'+controller+'_'+target_source+('_'+start_stage if start_stage else ''))
    out.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(out/'executed_tokens.npz',motion_token=np.asarray(refined),source_row=rows,
                        sim_time=raw['sim_time'][rows],decoder_input=np.asarray(decoder_obs))
    np.savez_compressed(out/f'rollout_joint_diagnostics_{history_seed}.npz',
        reference=details[:,0], actual=details[:,1], target=details[:,2], applied_target=np.asarray(applied_targets),
        joint_names=np.array(candidate['joint_names']))
    (out/f'rollout_report_{history_seed}.json').write_text(json.dumps(result,indent=2))
    (out/'rollout_report.json').write_text(json.dumps(result,indent=2))
    np.savetxt(out/'rollout_errors.csv',a,delimiter=',',header='time,max_joint_error_rad,bottle_error_m,lift_m',comments='')
    print(json.dumps(result,indent=2));return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('episode');p.add_argument('--no-arm-bias',action='store_true');p.add_argument('--history-seed',choices=['repeat','zero'],default='repeat')
    p.add_argument('--body-control',choices=['auto','manipulation','full'],default='auto')
    p.add_argument('--start-stage',choices=['detecting','approach'])
    p.add_argument('--controller',choices=['sonic','collection'],default='sonic')
    p.add_argument('--target-source',choices=['decoder','expert'],default='decoder')
    p.add_argument('--tokens-file');p.add_argument('--output-dir')
    p.add_argument('--pickup-only',action='store_true')
    p.add_argument('--video-path')
    a=p.parse_args();rollout(a.episode,not a.no_arm_bias,a.history_seed,a.body_control,a.start_stage,a.controller,a.target_source,a.tokens_file,a.output_dir,pickup_only=a.pickup_only,video_path=a.video_path)
