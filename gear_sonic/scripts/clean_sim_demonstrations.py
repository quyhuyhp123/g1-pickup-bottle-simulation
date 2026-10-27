"""Create a separate, indexed pickup-only raw dataset. Not LeRobot/SONIC labels."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import numpy as np
from gear_sonic.scripts.inspect_sim_episode import inspect


def select_window(stages, times, context=.9, success_seconds=2., allow_reviewed_hold=False):
    starts=np.flatnonzero(stages=='approach')
    if not len(starts): raise ValueError('No approach phase')
    start=int(starts[0])
    successes=np.flatnonzero((stages=='success') & (np.arange(len(stages))>=start))
    if not len(successes):
        holds=np.flatnonzero(stages=='hold')
        if not allow_reviewed_hold or not len(holds) or stages[-1]!='hold':
            raise ValueError('No completed hold/success phase')
        success=len(stages)-1
    else:
        success=int(successes[0])
    stops=np.flatnonzero(np.isin(stages, ['transfer','lower','release','retreat','return_home','done','failed']) & (np.arange(len(stages))>start))
    limit=int(stops[0]) if len(stops) else len(stages)
    if success>=limit: raise ValueError('Success occurs after interruption/placement')
    stop=min(limit,int(np.searchsorted(times,times[success]+success_seconds,side='right')))
    if not np.any(stages[start:stop]=='lift') or not np.any(stages[start:stop]=='hold'):
        raise ValueError('Missing lift/hold phase')
    lo=int(np.searchsorted(times,times[start]-context,side='left'))
    # Context remains available for later encoding; it is NOT a training label.
    hi=min(limit,int(np.searchsorted(times,times[stop-1]+context,side='right')))
    return lo,start,stop,hi


def clean(source, output, confirmed=False, seed=42):
    source=Path(source).resolve();output=Path(output).resolve()
    if output.exists(): raise ValueError('Output already exists; choose a new directory')
    episodes=sorted(source.glob('episode_*'))
    if len(episodes)<3: raise ValueError('Need at least 3 episodes for episode-level split')
    records=[]
    # Validate ALL sources before writing any cleaned files.
    for p in episodes:
        inspect(p)
        meta=json.loads((p/'meta.json').read_text())
        if meta.get('outcome') in ('failure','discard'): raise ValueError(f'Excluded outcome: {p.name}')
        if meta.get('outcome')!='success' and not confirmed:
            raise ValueError(f'{p.name}: success not reviewed; review or pass explicit confirmation')
        replay=json.loads((p/'replay_report.json').read_text())
        if not replay.get('trajectory_match') or replay.get('samples_replayed')!=meta['samples']:
            raise ValueError(f'{p.name}: replay incomplete or mismatched')
        stages=[];times=[]
        for f in sorted(p.glob('states_*.npz')):
            with np.load(f,allow_pickle=False) as z:
                stages.extend(z['stage'].tolist());times.extend(z['sim_time'].tolist())
        stages=np.array(stages);times=np.array(times)
        window=select_window(stages,times,allow_reviewed_hold=confirmed or meta.get("outcome")=="success")
        records.append((p,meta,stages,times,window))
    rng=np.random.default_rng(seed);order=rng.permutation(len(records))
    nval=max(1,round(len(records)*.2));val=set(order[:nval].tolist())
    output.mkdir(parents=True)
    manifest=dict(format='clean_pickup_raw_v1',status='building',training_ready=False,
        sonic_validated=False,source_root=str(source),seed=seed,
        split_method='seeded whole-episode split; not a guarantee of spatial generalization',
        task='grab the bottle',context_seconds=.9,success_seconds=2.,episodes=[])
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2))
    for k,(p,meta,stages,times,(lo,start,stop,hi)) in enumerate(records):
        dest=output/'episodes'/p.name; (dest/'rgb').mkdir(parents=True)
        chunks=[];hashes={}
        for f in sorted(p.glob('states_*.npz')):
            hashes[f.name]=hashlib.sha256(f.read_bytes()).hexdigest()
            with np.load(f,allow_pickle=False) as z: chunks.append({key:z[key].copy() for key in z.files})
        data={key:np.concatenate([c[key] for c in chunks])[lo:hi] for key in chunks[0]}
        data['source_row']=np.arange(lo,hi)
        data['label_window']=(data['source_row']>=start)&(data['source_row']<stop)
        # These timestamps/frame IDs retain their original meanings. No resampling.
        np.savez_compressed(dest/'samples.npz',**data)
        image_hashes={}
        for frame in data['frame_id'][data['frame_id']>=0]:
            name=f'{int(frame):06d}.png';f=p/'rgb'/name
            shutil.copy2(f,dest/'rgb'/name);image_hashes[name]=hashlib.sha256(f.read_bytes()).hexdigest()
        for name in ('meta.json','model.xml','initial_state.npz','replay_report.json'):
            shutil.copy2(p/name,dest/('source_'+name))
            hashes[name]=hashlib.sha256((p/name).read_bytes()).hexdigest()
        info=dict(episode=p.name,split='validation' if k in val else 'train',source=str(p),
            outcome='success',outcome_evidence='source_metadata' if meta.get('outcome')=='success' else 'user_confirmed_all_10_episodes',
            controller_success_seen=bool(np.any(stages[start:stop]=='success')),
            review_note='User confirmed quality; controller success not reached' if not np.any(stages[start:stop]=='success') else '',
            source_samples=meta['samples'],retained_samples=hi-lo,label_samples=stop-start,
            retained_range=[lo,hi],label_range=[start,stop],ranges='half-open source-row indices',
            phase_counts={str(v):int(np.sum(stages[start:stop]==v)) for v in np.unique(stages[start:stop])},
            retained_frames=int(np.sum(data['frame_id']>=0)),source_sha256=hashes,image_sha256=image_hashes,
            source_initial_state_note='Initial state is for the full source episode, NOT the trimmed start; use original for physics replay',
            training_ready=False,sonic_validated=False)
        (dest/'selection.json').write_text(json.dumps(info,indent=2))
        manifest['episodes'].append({key:info[key] for key in ('episode','split','label_samples','retained_samples','retained_frames','label_range','retained_range','phase_counts')})
    manifest['status']='complete'
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2))
    for split in ('train','validation'):
        (output/f'{split}.txt').write_text(''.join('episodes/'+e['episode']+'\n' for e in manifest['episodes'] if e['split']==split))
    (output/'README.md').write_text('''# Clean pickup raw dataset

This is a separate raw selection, NOT a LeRobot dataset or validated SONIC training set.
`manifest.json` defines episode-level train/validation splits. `samples.npz` retains
original simulation timestamps and frame IDs. `label_window` selects approach,
close, lift, hold and up to 2 seconds of success; retained surrounding context is
not a label. No placement/release/retreat labels are included.
`source_row` maps each sample back to the original recording. RGB filenames use
original frame IDs; -1 means no image at that physics step. Do not assume 200Hz RGB.
Original metadata/model/initial state/replay report are copied with `source_` prefix.
The source initial state is NOT the state at the trimmed start. Replay originals.
No sonic_candidate tokens are copied. Hand targets are still Dex3 joint targets,
not normalized Inspire labels. Further action-contract and SONIC validation is required.
''')
    print(f'CLEAN COMPLETE: {len(records)-nval} train, {nval} validation -> {output}')
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',default='outputs/ik_demonstrations');p.add_argument('--output',required=True)
    p.add_argument('--user-confirmed-success-all',action='store_true');p.add_argument('--seed',type=int,default=42)
    a=p.parse_args();clean(a.source,a.output,a.user_confirmed_success_all,a.seed)
