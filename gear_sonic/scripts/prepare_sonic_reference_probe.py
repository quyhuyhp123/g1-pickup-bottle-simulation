"""Build a synthetic reference fixture for physics diagnostics, never expert data."""
import json
from pathlib import Path
import mujoco
import numpy as np
from gear_sonic.scripts.encode_sim_episode import ROOT,body_order


def prepare():
    ref=ROOT/'gear_sonic_deploy/reference/example/macarena_001__A545'
    out=ROOT/'outputs/sonic_reference_physics';out.mkdir(exist_ok=True)
    source=ROOT/'outputs/ik_demonstrations/episode_20261026_224629_65003197/model.xml'
    m=mujoco.MjModel.from_xml_path(str(source));m.eq_active0[:]=0
    # Remove manipulation props from locomotion reference probe; preserve floor/robot.
    for g in range(m.ngeom):
        n=m.geom(g).name or ''
        if any(word in n for word in ('table','bottle')):
            m.geom_contype[g]=0;m.geom_conaffinity[g]=0
    joints=np.array([int(m.body(n).jntadr[0]) for n in body_order()]);qa=m.jnt_qposadr[joints];va=m.jnt_dofadr[joints]
    load=lambda f:np.loadtxt(ref/f,delimiter=',',skiprows=1)
    q,dq=load('joint_pos.csv'),load('joint_vel.csv');bp=load('body_pos.csv')[:,:3];bq=load('body_quat.csv')[:,:4]
    bv=load('body_lin_vel.csv')[:,:3];bw=load('body_ang_vel.csv')[:,:3]
    d=mujoco.MjData(m);d.qpos[qa]=q[0];d.qvel[va]=dq[0]
    d.qpos[:3]=bp[0];d.qpos[3:7]=bq[0];d.qvel[:3]=bv[0]
    r=np.zeros(9);mujoco.mju_quat2Mat(r,bq[0]);d.qvel[3:6]=r.reshape(3,3).T@bw[0]
    mujoco.mj_forward(m,d)
    mujoco.mj_saveLastXML(str(out/'model.xml'),m)
    np.savez(out/'initial_state.npz',**{k:getattr(d,k).copy() for k in ('qpos','qvel','act','eq_active','mocap_pos','mocap_quat')},sim_time=np.array(0.))
    stride=round(.02/m.opt.timestep);n=len(q)*stride
    times=np.arange(n)*m.opt.timestep;rt=np.arange(len(q))*.02
    rawq=np.tile(d.qpos,(n,1));rawv=np.tile(d.qvel,(n,1))
    for k in range(29):
        rawq[:,qa[k]]=np.interp(times,rt,q[:,k]);rawv[:,va[k]]=np.interp(times,rt,dq[:,k])
    right=[m.joint('right_hand_'+name+'_joint').id for name in ('thumb_0','thumb_1','thumb_2','middle_0','middle_1','index_0','index_1')]
    np.savez_compressed(out/'states_000000.npz',qpos=rawq,qvel=rawv,assisted_hand_target=np.zeros((n,7)))
    (out/'meta.json').write_text(json.dumps(dict(kind='synthetic_reference_probe_NOT_DEMONSTRATION',assisted_hand_joint_ids=right)))
    candidate=out/'sonic_candidate';candidate.mkdir(exist_ok=True)
    with np.load(ROOT/'outputs/sonic_reference_audit/reference_targets.npz') as z:
        np.savez(candidate/'tokens.npz',motion_token=z['motion_token'],source_row=np.arange(len(q))*stride)
    (candidate/'report.json').write_text(json.dumps(dict(joint_names=[m.joint(int(j)).name for j in joints],training_ready=False)))
    print(out)

if __name__=='__main__':prepare()
