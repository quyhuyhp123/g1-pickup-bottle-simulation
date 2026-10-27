"""Validate exported episodes with the actual installed GR00T video/data loader."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from gr00t.configs.data.embodiment_configs import MODALITY_CONFIGS
from gr00t.data.dataset.lerobot_episode_loader import LeRobotEpisodeLoader
from gr00t.data.stats import generate_stats


def validate(root):
    root=Path(root)
    report=json.loads((root/'export_report.json').read_text())
    if report['status']!='complete': raise ValueError('Incomplete export')
    results=[]
    for split in ('train','validation'):
        path=root/split
        generate_stats(path)
        loader=LeRobotEpisodeLoader(path,MODALITY_CONFIGS['unitree_g1_sonic'],decoder_kwargs={'num_ffmpeg_threads':1})
        for i in range(len(loader)):
            episode=loader[i]
            for group,dim in [('action.motion_token',64),('action.left_hand_joints',7),('action.right_hand_joints',7),('state.projected_gravity',3)]:
                values=np.stack(episode[group])
                if values.shape!=(len(episode),dim) or not np.isfinite(values).all():raise ValueError(group)
            image=np.asarray(episode['video.ego_view'].iloc[0])
            if image.shape!=(480,640,3):raise ValueError(f'Unexpected RGB shape: {image.shape}')
            results.append({'split':split,'episode_index':i,'frames':len(episode),'image_shape':list(image.shape)})
            print(f'PASS {split}/{i}: {len(episode)} rows and decoded RGB',flush=True)
    result={'loader_validation_passed':True,'sonic_validated':False,'training_ready':False,
        'note':'Format/readability only. Validation statistics are NOT used for training normalization.', 'episodes':results}
    paths=[root/'export_report.json']
    for split in ('train','validation'):
        paths.extend(p for p in (root/split).rglob('*') if p.is_file())
    result['artifact_sha256']={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in sorted(paths)}
    (root/'loader_validation.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('dataset')
    validate(p.parse_args().dataset)
