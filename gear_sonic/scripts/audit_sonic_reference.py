"""Teacher-forced reference diagnostic, NOT a closed-loop physics validation."""
import argparse
from collections import deque
import json
from pathlib import Path
import mujoco
import numpy as np
import onnxruntime as ort
from gear_sonic.scripts.rollout_sonic_episode import parameters,ROOT


def audit(reference,output):
    ref=Path(reference);p=parameters();order=p['mujoco_to_isaaclab'].astype(int)
    default=p['default_angles'][order];scale=p['g1_action_scale'][order]
    q=np.loadtxt(ref/'joint_pos.csv',delimiter=',',skiprows=1)
    dq=np.loadtxt(ref/'joint_vel.csv',delimiter=',',skiprows=1)
    quat=np.loadtxt(ref/'body_quat.csv',delimiter=',',skiprows=1)[:,:4]
    omega=np.loadtxt(ref/'body_ang_vel.csv',delimiter=',',skiprows=1)[:,:3]
    r=[]
    for v in quat:
        m=np.zeros(9);mujoco.mju_quat2Mat(m,v);r.append(m.reshape(3,3))
    r=np.array(r)
    opts=ort.SessionOptions();opts.intra_op_num_threads=2
    sessions=[ort.InferenceSession(str(ROOT/'gear_sonic_deploy/policy/release'/f'model_{n}.onnx'),sess_options=opts,providers=['CPUExecutionProvider']) for n in ('encoder','decoder')]
    hist=deque(maxlen=10);last=np.zeros(29);targets=[];tokens=[]
    for i in range(len(q)):
        f=np.minimum(i+np.arange(10)*5,len(q)-1)
        x=np.zeros((1,1762),np.float32);x[0,4:294]=q[f].ravel();x[0,294:584]=dq[f].ravel();x[0,601:661]=(r[i].T@r[f])[...,:2].ravel()
        token=sessions[0].run(None,{'obs_dict':x})[0][0]
        tokens.append(token.copy())
        state=(r[i].T@omega[i],q[i]-default,dq[i],last.copy(),r[i].T@np.array([0.,0.,-1.]))
        if not hist:hist.extend([state]*9)
        hist.append(state)
        obs=np.concatenate([token]+[np.concatenate([s[k] for s in hist]) for k in range(5)]).astype(np.float32)[None]
        last=sessions[1].run(None,{'obs_dict':obs})[0][0]
        targets.append(default+last*scale)
    targets=np.array(targets);error=targets-q
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(out/'reference_targets.npz',target=targets,reference=q,motion_token=np.asarray(tokens))
    report=dict(reference=str(ref),frames=len(q),assumed_reference_fps=50,
        max_target_offset_rad=float(abs(error).max()),rms_target_offset_rad=float(np.sqrt(np.mean(error**2))),
        physics_validated=False,notes='Teacher-forced measured q/dq/base; predicted previous action; target offset includes PD feedforward/tracking demand and is NOT physical tracking error.')
    (out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('reference');p.add_argument('--output',default='outputs/sonic_reference_audit')
    a=p.parse_args();audit(a.reference,a.output)
