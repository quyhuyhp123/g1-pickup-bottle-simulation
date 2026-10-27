"""Load the merged GR00T checkpoint through Gr00tPolicy and measure held-out actions.
Open-loop only: finite actions / RMSE do not prove closed-loop bottle pickup.
"""
import argparse
import json
from pathlib import Path
import numpy as np
import torch
from gear_sonic.scripts.finetune_gr00t_g1 import EpisodeSampler


def evaluate(args):
    from gr00t.policy.gr00t_policy import Gr00tPolicy
    policy=Gr00tPolicy(model_path=args.checkpoint,embodiment_tag='UNITREE_G1_SONIC',device='cuda:0')
    sampler=EpisodeSampler(Path(args.dataset)/'validation',policy.modality_configs)
    predictions=[];targets=[];records=[]
    for i,(e,t) in enumerate(sampler.validation_keys(args.samples_per_episode)):
        sample=sampler.sample(e,t)
        observation={'video':{'ego_view':sample.images['ego_view'][0][None,None]},
            'state':{k:v[None] for k,v in sample.states.items()},
            'language':{'annotation.human.task_description':[[sample.text]]}}
        torch.manual_seed(20000+i)
        action,_=policy.get_action(observation)
        predicted={}
        for key,width in [('motion_token',64),('left_hand_joints',7),('right_hand_joints',7)]:
            value=np.asarray(action.get(key,action.get('action.'+key)))
            if value.shape!=(1,40,width) or not np.isfinite(value).all():raise ValueError(f'Invalid {key}: {value.shape}')
            predicted[key]=value[0]
        pred=np.concatenate(list(predicted.values()),axis=1)
        target=np.concatenate([sample.actions[k] for k in predicted],axis=1)
        predictions.append(pred);targets.append(target)
        records.append(dict(episode=e,frame=t,motion_token_rmse=float(np.sqrt(np.mean((pred[:,:64]-target[:,:64])**2))),
            right_hand_rmse_rad=float(np.sqrt(np.mean((pred[:,71:]-target[:,71:])**2)))))
        print('EVAL',records[-1],flush=True)
    predictions=np.asarray(predictions);targets=np.asarray(targets)
    output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(output/'predictions.npz',predictions=predictions,targets=targets)
    report=dict(checkpoint=str(Path(args.checkpoint).resolve()),policy_reload_passed=True,finite_action_shapes_passed=True,
        samples=len(records),validation_episodes=len(sampler.tables),
        motion_token_rmse=float(np.sqrt(np.mean((predictions[:,:,:64]-targets[:,:,:64])**2))),
        right_hand_rmse_rad=float(np.sqrt(np.mean((predictions[:,:,71:]-targets[:,:,71:])**2))),
        closed_loop_pickup_validated=False,records=records)
    (output/'evaluation_report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--checkpoint',required=True)
    p.add_argument('--dataset',default='outputs/gr00t_dex3_refined_v1');p.add_argument('--output',required=True)
    p.add_argument('--samples-per-episode',type=int,default=8)
    evaluate(p.parse_args())
