"""Export clean demonstrations to experimental LeRobot v2.1 (NOT rollout validated).
Run using Isaac-GR00T's Python (numpy, pandas, pyarrow, OpenCV).
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np

GROUPS = {
    'left_leg': ['left_'+s+'_joint' for s in ('hip_pitch','hip_roll','hip_yaw','knee','ankle_pitch','ankle_roll')],
    'right_leg': ['right_'+s+'_joint' for s in ('hip_pitch','hip_roll','hip_yaw','knee','ankle_pitch','ankle_roll')],
    'waist': ['waist_'+s+'_joint' for s in ('yaw','roll','pitch')],
}
for side in ('left','right'):
    GROUPS[side+'_arm'] = [side+'_'+s+'_joint' for s in ('shoulder_pitch','shoulder_roll','shoulder_yaw','elbow','wrist_roll','wrist_pitch','wrist_yaw')]
for side in ('left','right'):
    GROUPS[side+'_hand'] = [side+'_hand_'+s+'_joint' for s in ('thumb_0','thumb_1','thumb_2','middle_0','middle_1','index_0','index_1')]
# Observation groups follow RobotModel.get_joint_group_indices; hand actions
# retain the MuJoCo/SDK motor order used by the sender and assisted controller.
HAND_STATE_ORDER = [5, 6, 3, 4, 0, 1, 2]


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2)+'\n')


def past_camera_indices(times, frame_ids, rows, max_age=.101):
    camera_rows = np.flatnonzero(frame_ids >= 0)
    indices = np.searchsorted(times[camera_rows], times[rows], side='right')-1
    if np.any(indices < 0):
        raise ValueError('No past camera frame for an action')
    selected = camera_rows[indices]
    age = times[rows]-times[selected]
    if np.any(age < -1e-8) or np.any(age > max_age):
        raise ValueError('Camera stale or future frame selected')
    return selected, age


def projected_gravity(quat):
    quat = np.asarray(quat, dtype=np.float64)
    norm = np.linalg.norm(quat, axis=-1)
    if not np.allclose(norm, 1, atol=1e-3):
        raise ValueError('Invalid base quaternion')
    w,x,y,z = (quat/norm[:,None]).T
    return np.column_stack((2*(w*y-x*z), -2*(y*z+w*x), 2*(x*x+y*y)-1))


def export(clean, output, experimental=False, refined_root=None):
    if not experimental:
        raise ValueError('Requires --experimental-unvalidated-sonic: labels have not passed rollout')
    import cv2
    import pandas as pd
    clean, output = Path(clean).resolve(), Path(output).resolve()
    manifest = json.loads((clean/'manifest.json').read_text())
    if manifest['status'] != 'complete' or output.exists():
        raise ValueError('Requires complete clean dataset and a NEW output directory')
    output.mkdir(parents=True)
    report = dict(status='building', training_ready=False, sonic_validated=False,
        purpose='Training pipeline experiment only; not a deployable pickup policy',
        embodiment='unitree_g1_sonic', fps=50, action_horizon=40,
        hand_contract='native Dex3 radians, NOT CloudWalk Inspire normalized grip',
        left_hand_action='Initial recorded pose held constant (fixed-pickup controller convention)',
        right_hand_action='Recorded assisted_hand_target, ordered by joint names',
        camera='Latest past RGB at each 50 Hz row; source camera 10 Hz; no future image',
        state='Measured joint radians and base-frame gravity at action timestamp',
        excluded='Partial encoder future windows; rows outside clean label_window', episodes=[])
    if refined_root:
        report.update(training_ready_for_fixed_base_profile=True,
            execution_profile_id='fixed_base_dex3_pd80_3_v1',
            motion_token_source='Offline inverse fitting through frozen SONIC, verified by saved-token physics replay',
            purpose='Fine-tuning labels for the verified fixed-base collection controller profile')
    dump(output/'export_report.json',report)
    state_meta={}; start=0
    state_names=[]
    for group,names in {**GROUPS,'projected_gravity':['gravity_x','gravity_y','gravity_z']}.items():
        if group.endswith('_hand'): names=[names[i] for i in HAND_STATE_ORDER]
        state_meta[group]={'start':start,'end':start+len(names)}
        start+=len(names);state_names.extend(names)
    action_meta={'motion_token':{'start':0,'end':64},'left_hand_joints':{'start':64,'end':71},'right_hand_joints':{'start':71,'end':78}}
    for split in ('train','validation'):
        dest=output/split
        entries=[e for e in manifest['episodes'] if e['split']==split]
        episode_meta=[]; total=0
        for index,entry in enumerate(entries):
            folder=clean/'episodes'/entry['episode']
            selection=json.loads((folder/'selection.json').read_text())
            raw=Path(selection['source'])
            # Ensure cached tokens still refer to the exact raw files used by clean.
            for filename,digest in selection['source_sha256'].items():
                if hashlib.sha256((raw/filename).read_bytes()).hexdigest()!=digest:
                    raise ValueError(f'Source changed: {raw/filename}')
            meta=json.loads((folder/'source_meta.json').read_text())
            with np.load(folder/'samples.npz') as z: a={k:z[k] for k in z.files}
            with np.load(raw/'sonic_candidate/tokens.npz') as z: tok={k:z[k] for k in z.files}
            candidate=json.loads((raw/'sonic_candidate/report.json').read_text())
            refined_info=None
            refined_present=np.ones(len(tok['source_row']),dtype=bool)
            if refined_root:
                refined_folder=Path(refined_root)/entry['episode']
                refined_info=json.loads((refined_folder/'refinement_report.json').read_text())
                if (refined_info.get('status')!='complete' or not refined_info.get('saved_token_replay_passed')
                    or refined_info.get('execution_profile_id')!='fixed_base_dex3_pd80_3_v1'):
                    raise ValueError(f'Refined tokens not validated for this profile: {entry["episode"]}')
                token_file=refined_folder/'fitting_rollout/executed_tokens.npz'
                if hashlib.sha256(token_file.read_bytes()).hexdigest()!=refined_info['saved_token_sha256']:
                    raise ValueError('Refined tokens changed since replay')
                replay_file=refined_folder/'saved_token_replay/rollout_report.json'
                if hashlib.sha256(replay_file.read_bytes()).hexdigest()!=refined_info['saved_token_replay_sha256']:
                    raise ValueError('Refined replay report changed')
                replay_info=json.loads(replay_file.read_text())
                if (replay_info['target_source']!='decoder' or replay_info['controller']!='collection'
                    or replay_info['token_refinement_online'] or not replay_info['grasp_lift_success']
                    or not replay_info['trajectory_match']):
                    raise ValueError('Requires a successful independent decoder-only token replay')
                for filename,digest in refined_info['source_sha256'].items():
                    if hashlib.sha256((raw/filename).read_bytes()).hexdigest()!=digest:
                        raise ValueError(f'Refinement source changed: {filename}')
                with np.load(token_file) as rz:
                    ri=np.searchsorted(rz['source_row'],tok['source_row'])
                    refined_present=ri<len(rz['source_row'])
                    refined_present &= rz['source_row'][np.minimum(ri,len(rz['source_row'])-1)]==tok['source_row']
                    tok['motion_token'][refined_present]=rz['motion_token'][ri[refined_present]]
            rows=np.searchsorted(a['source_row'],tok['source_row'])
            valid=rows<len(a['source_row'])
            valid &= a['source_row'][np.minimum(rows,len(a['source_row'])-1)]==tok['source_row']
            valid &= tok['full_future_window']
            valid &= refined_present
            # Do not encode future placement/lowering motion into pickup labels.
            future_rows = round(candidate['future_window_s']/meta['timestep'])
            valid &= tok['source_row'] + future_rows <= a['source_row'][-1]
            valid &= a['label_window'][np.minimum(rows,len(a['source_row'])-1)]
            token_rows=np.flatnonzero(valid); rows=rows[valid]
            if len(rows)<40 or not np.allclose(np.diff(a['sim_time'][rows]),.02):
                raise ValueError(f'Insufficient or noncontiguous 50Hz labels: {folder}')
            if not np.allclose(a['sim_time'][rows],tok['sim_time'][token_rows]):
                raise ValueError('Token timestamp mismatch')
            addresses=dict(zip(meta['joints'],meta['jnt_qposadr']))
            q=a['qpos'][rows]
            if not np.allclose(tok['joint_pos'][token_rows],
                               q[:,[addresses[n] for n in candidate['joint_names']]]):
                raise ValueError('Cached token reference does not match recorded joint state')
            groups=[q[:,[addresses[n] for n in names]] for names in GROUPS.values()]
            # Match native Dex3 prepare_observation's left finger coupling.
            groups[5]=groups[5].copy();groups[5][:,5:7]=groups[5][:,3:5]
            groups[5]=groups[5][:,HAND_STATE_ORDER]
            groups[6]=groups[6][:,HAND_STATE_ORDER]
            base=addresses['floating_base_joint']
            state=np.concatenate(groups+[projected_gravity(q[:,base+3:base+7])],axis=1).astype('float32')
            with np.load(folder/'source_initial_state.npz') as z:
                left=z['qpos'][[addresses[n] for n in GROUPS['left_hand']]]
            hand_names=[meta['joints'][j] for j in meta['assisted_hand_joint_ids']]
            hand_order=[hand_names.index(n) for n in GROUPS['right_hand']]
            action=np.column_stack((tok['motion_token'][token_rows],np.broadcast_to(left,(len(rows),7)),a['assisted_hand_target'][rows][:,hand_order])).astype('float32')
            if state.shape[1]!=46 or action.shape[1]!=78 or not np.isfinite(state).all() or not np.isfinite(action).all():
                raise ValueError('Non-finite or wrong-dimensional labels')
            camera_rows,age=past_camera_indices(a['sim_time'],a['frame_id'],rows)
            path=dest/'videos/chunk-000/observation.images.ego_view'/f'episode_{index:06d}.mp4'
            path.parent.mkdir(parents=True,exist_ok=True)
            writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*'mp4v'),50,(640,480))
            if not writer.isOpened(): raise RuntimeError('Cannot open video encoder')
            cache_id=None; image=None
            try:
                for cr in camera_rows:
                    frame_id=int(a['frame_id'][cr])
                    if frame_id!=cache_id:
                        image_path=folder/'rgb'/f'{frame_id:06d}.png'
                        if hashlib.sha256(image_path.read_bytes()).hexdigest()!=selection['image_sha256'][image_path.name]:
                            raise ValueError(f'Clean image changed: {image_path}')
                        image=cv2.imread(str(image_path))
                        if image is None or image.shape!=(480,640,3): raise ValueError('Invalid image')
                        cache_id=frame_id
                    writer.write(image)
            finally: writer.release()
            n=len(rows)
            frame=pd.DataFrame({'observation.state':list(state),'action':list(action),
                'timestamp':np.arange(n,dtype='float32')/50,'frame_index':np.arange(n),
                'episode_index':np.full(n,index),'task_index':np.zeros(n,dtype='int64'),
                'index':np.arange(total,total+n), 'source_row':a['source_row'][rows],
                'source_sim_time':a['sim_time'][rows], 'source_frame_id':a['frame_id'][camera_rows],
                'camera_age_s':age})
            parquet=dest/'data/chunk-000'/f'episode_{index:06d}.parquet'
            parquet.parent.mkdir(parents=True,exist_ok=True);frame.to_parquet(parquet,index=False)
            total+=n
            episode_meta.append({'episode_index':index,'tasks':[meta['prompt']],'length':n})
            provenance=dict(source=entry['episode'],split=split,episode_index=index,
                frames=n,max_camera_age_s=float(age.max()),encoder_sha256=candidate['encoder_sha256'],
                encoder_seed_token_sha256=hashlib.sha256((raw/'sonic_candidate/tokens.npz').read_bytes()).hexdigest())
            if refined_info:provenance['refined_token_sha256']=refined_info['saved_token_sha256']
            report['episodes'].append(provenance)
            print(f'{split} {index}: {entry["episode"]}: {n} rows',flush=True)
        if len({e['tasks'][0] for e in episode_meta})!=1: raise ValueError('Expected one task')
        features={'observation.state':{'dtype':'float32','shape':[46],'names':state_names},
            'action':{'dtype':'float32','shape':[78],'names':[f'token_{i}' for i in range(64)]+GROUPS['left_hand']+GROUPS['right_hand']},
            'observation.images.ego_view':{'dtype':'video','shape':[480,640,3],'names':['height','width','channels'],
                'info':{'video.fps':50,'video.height':480,'video.width':640,'video.codec':'mpeg4','video.pix_fmt':'yuv420p','video.channels':3,'has_audio':False}}}
        for name in ('timestamp','frame_index','episode_index','task_index','index'):
            features[name]={'dtype':'float32' if name=='timestamp' else 'int64','shape':[1],'names':None}
        dump(dest/'meta/info.json',dict(codebase_version='v2.1',robot_type='g1_dex3_experimental_sonic',
            total_episodes=len(entries),total_frames=total,total_tasks=1,total_videos=len(entries),total_chunks=1,chunks_size=1000,fps=50,
            splits={'train':f'0:{len(entries)}'},features=features,
            data_path='data/chunk-{episode_chunk:03d}/episode_{episode_index:06d}.parquet',
            video_path='videos/chunk-{episode_chunk:03d}/{video_key}/episode_{episode_index:06d}.mp4'))
        dump(dest/'meta/modality.json',{'state':state_meta,'action':action_meta,'video':{'ego_view':{'original_key':'observation.images.ego_view'}},'annotation':{'human.task_description':{'original_key':'task_index'}}})
        (dest/'meta/episodes.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in episode_meta))
        (dest/'meta/tasks.jsonl').write_text(json.dumps({'task_index':0,'task':episode_meta[0]['tasks'][0]})+'\n')
    report['status']='complete';dump(output/'export_report.json',report)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--clean',default='outputs/ik_clean_pickup_v1')
    p.add_argument('--output',required=True)
    p.add_argument('--experimental-unvalidated-sonic',action='store_true')
    p.add_argument('--refined-root',help='Root containing per-episode successful frozen-decoder refinement reports')
    a=p.parse_args();export(a.clean,a.output,a.experimental_unvalidated_sonic,a.refined_root)
