"""Offline decoder-aware token fitting for fixed-base Dex3 demonstrations.

SONIC weights stay frozen. Expert arm targets are used ONLY during offline
label fitting. A separate replay of the saved tokens is required for validation.
Requires .venv_sim (torch, MuJoCo, ORT), plus an ONNX-capable Python for extraction.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import numpy as np
import torch
from gear_sonic.scripts.rollout_sonic_episode import ROOT, rollout

EXTRACT = '''
import sys,onnx,numpy as np
from onnx import numpy_helper
m=onnx.load(sys.argv[1]);a={i.name:numpy_helper.to_array(i) for i in m.graph.initializer}
nodes=[n for n in m.graph.node if n.op_type=='MatMul']
assert len(nodes)==7 and len([n for n in m.graph.node if n.op_type=='Sigmoid'])==6
weights={}
for i,n in enumerate(nodes):
 weights[f'w{i}']=a[n.input[1]]
 weights[f'b{i}']=a[f'module.decoders.g1_dyn.module.{i*2}.bias']
assert weights['w0'].shape==(994,2048) and weights['w6'].shape==(512,29)
np.savez(sys.argv[2],**weights)
'''

class FrozenDecoder:
    def __init__(self, weights, device='cuda'):
        self.device=torch.device(device)
        with np.load(weights) as z:
            self.layers=[(torch.tensor(z[f'w{i}'],device=device),torch.tensor(z[f'b{i}'],device=device)) for i in range(7)]
    def __call__(self,x):
        for i,(w,b) in enumerate(self.layers):
            x=x@w+b
            if i<6:x=torch.nn.functional.silu(x)
        return x

class TokenFitter:
    def __init__(self,model,onnx_session,tolerance=2e-4,iterations=16):
        self.model=model;self.session=onnx_session;self.tolerance=tolerance;self.iterations=iterations
        self.previous_shift=None;self.log=[];self.parity_max=0.
    def __call__(self,t,row,obs,expert,slots,default,scale):
        device=self.model.device
        tensor=lambda x:torch.as_tensor(x,dtype=torch.float32,device=device)
        # Confirm the differentiable decoder actually reproduces this ONNX model.
        with torch.no_grad():pred=self.model(tensor(obs)).cpu().numpy()
        actual=self.session.run(None,{'obs_dict':obs[None].astype('float32')})[0][0]
        parity=float(np.max(abs(pred-actual)));self.parity_max=max(self.parity_max,parity)
        if parity>2e-4:raise RuntimeError(f'PyTorch/ONNX parity failed: {parity}')
        prop=tensor(obs[64:]);seed=tensor(obs[:64]);want=tensor(expert)
        ids=torch.as_tensor(slots,device=device);sc=tensor(scale[slots]);df=tensor(default[slots])
        def f(z):return self.model(torch.cat((z,prop)))[ids]*sc+df
        token=seed.clone()
        if self.previous_shift is not None:
            warm=seed+self.previous_shift
            with torch.no_grad():
                if torch.square(f(warm)-want).sum()<torch.square(f(token)-want).sum():token=warm
        eye=torch.eye(len(slots),device=device)
        for iteration in range(self.iterations):
            token=token.detach().requires_grad_(True)
            error=f(token)-want
            if float(error.detach().abs().max())<self.tolerance:break
            jac=torch.func.jacrev(f)(token)
            delta=jac.T@torch.linalg.solve(jac@jac.T+1e-5*eye,-error)
            delta=delta*min(1.,2./max(float(delta.detach().norm()),1e-12))
            score=float(error.detach().square().sum());best=token.detach();best_score=score
            with torch.no_grad():
                for factor in (1.,.5,.25,.1):
                    trial=token+factor*delta;trial_score=float((f(trial)-want).square().sum())
                    if trial_score<best_score:best=trial.detach();best_score=trial_score
            token=best
        with torch.no_grad():error=float((f(token)-want).abs().max())
        self.previous_shift=(token.detach()-seed).detach()
        record=dict(source_row=row,iterations=iteration+1,max_target_error_rad=error,
                    token_shift_l2=float(self.previous_shift.norm()))
        self.log.append(record)
        if t%100==0:print('REFINE',t,record,flush=True)
        if error>.01:raise RuntimeError(f'Token target fit failed at row {row}: {error} rad')
        return token.detach().cpu().numpy()


def refine(args):
    import onnxruntime as ort
    out=Path(args.output).resolve()
    if out.exists():raise ValueError('Use a new output directory')
    out.mkdir(parents=True)
    path=ROOT/'gear_sonic_deploy/policy/release/model_decoder.onnx'
    weights=out/'decoder_weights.npz'
    subprocess.run([args.onnx_python,'-c',EXTRACT,str(path),str(weights)],check=True)
    torch.set_num_threads(2);torch.backends.cuda.matmul.allow_tf32=False
    model=FrozenDecoder(weights,args.device)
    options=ort.SessionOptions();options.intra_op_num_threads=2
    session=ort.InferenceSession(str(path),sess_options=options,providers=['CPUExecutionProvider'])
    fitter=TokenFitter(model,session,iterations=args.iterations)
    report={'status':'fitting','sonic_validated':False,'training_ready':False,
        'execution_profile_id':'fixed_base_dex3_pd80_3_v1',
        'source_episode':str(Path(args.episode).resolve()),
        'source_sha256':{str(p.relative_to(Path(args.episode))):hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in list(Path(args.episode).glob('states_*.npz'))+
                        [Path(args.episode)/n for n in ('meta.json','model.xml','initial_state.npz','sonic_candidate/tokens.npz')]},
        'decoder_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'method':'Offline frozen-decoder inverse fitting to recorded expert arm joint targets',
        'conditions':'Fixed pelvis + held legs/left arm; collection PD80/3 with bias; recorded Dex3 finger targets',
        'warning':'New label convention. Does not fix the original v10 checkpoint or validate hardware.',
        'no_runtime_expert':'Validation must replay saved tokens without target fitting or IK'}
    def save(): (out/'refinement_report.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        fitted=rollout(args.episode,start_stage='approach',controller='collection',
                      output_dir=out/'fitting_rollout',token_refiner=fitter,pickup_only=True)
        report.update(status='replaying',fit_max_error_rad=max(x['max_target_error_rad'] for x in fitter.log),
                      pytorch_onnx_max_action_error=fitter.parity_max,
                      token_shift_max_l2=max(x['token_shift_l2'] for x in fitter.log))
        (out/'fit_trace.json').write_text(json.dumps(fitter.log,indent=2)+'\n');save()
        del model,fitter
        if torch.cuda.is_available():torch.cuda.empty_cache()
        replay=rollout(args.episode,start_stage='approach',controller='collection',
                       tokens_file=out/'fitting_rollout/executed_tokens.npz',output_dir=out/'saved_token_replay',pickup_only=True)
        validated=bool(replay['grasp_lift_success'] and replay['trajectory_match'])
        report.update(status='complete',saved_token_replay_passed=validated,
            execution_validated_for_this_profile=validated,
            saved_token_sha256=hashlib.sha256((out/'fitting_rollout/executed_tokens.npz').read_bytes()).hexdigest(),
            saved_token_replay_sha256=hashlib.sha256((out/'saved_token_replay/rollout_report.json').read_bytes()).hexdigest(),
            replay_max_joint_error_rad=replay['max_joint_error_rad'],
            replay_peak_lift_m=replay['peak_lift_m'],replay_final_lift_m=replay['final_lift_m'],
            opposed_contact_lift_hold_s=replay['longest_opposed_contact_lift_hold_s'])
        save();print('REFINEMENT RESULT',json.dumps(report,indent=2),flush=True)
    except Exception as exc:
        report.update(status='failed',error=f'{type(exc).__name__}: {exc}');save();raise
    finally:
        # Extracted weights are a disposable view; original ONNX is unchanged.
        weights.unlink(missing_ok=True)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('episode');p.add_argument('--output',required=True)
    p.add_argument('--onnx-python',default=str(ROOT/'.venv_inference/bin/python'))
    p.add_argument('--device',default='cuda');p.add_argument('--iterations',type=int,default=16)
    refine(p.parse_args())
