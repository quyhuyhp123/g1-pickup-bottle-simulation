"""Fine-tune v10 on verified fixed-base Dex3 labels; merge to a normal HF checkpoint.

Frozen VLM/SONIC, G1-only state/action projectors, LoRA on action-head attention/FFN.
Run with Isaac-GR00T Python and PYTHONPATH pointing to that repository.
"""
import argparse
from collections import OrderedDict
import hashlib
import json
import math
import os
from pathlib import Path
import random
import time
import numpy as np
import torch
from torch import nn


class G1Linear(nn.Module):
    def __init__(self,base,category):
        super().__init__();self.base=base;self.category=category
        self.W=nn.Parameter(base.W[category].detach().float().clone())
        self.b=nn.Parameter(base.b[category].detach().float().clone())
    def forward(self,x,cat_ids):
        if not bool(torch.all(cat_ids==self.category)):raise ValueError('G1-only projector received another embodiment')
        return torch.nn.functional.linear(x,self.W.T,self.b)
    @torch.no_grad()
    def merge(self):
        self.base.W[self.category].copy_(self.W);self.base.b[self.category].copy_(self.b)
        return self.base


class LoRALinear(nn.Module):
    def __init__(self,base,rank=8):
        super().__init__();self.base=base;self.rank=rank
        self.A=nn.Parameter(torch.empty(rank,base.in_features,device=base.weight.device,dtype=torch.float32))
        self.B=nn.Parameter(torch.zeros(base.out_features,rank,device=base.weight.device,dtype=torch.float32))
        nn.init.kaiming_uniform_(self.A,a=math.sqrt(5));self.dropout=nn.Dropout(.05)
    def forward(self,x):
        delta=torch.nn.functional.linear(torch.nn.functional.linear(self.dropout(x),self.A),self.B)
        return self.base(x)+delta.to(x.dtype)
    @torch.no_grad()
    def merge(self):
        self.base.weight.add_((self.B@self.A).to(self.base.weight.dtype));return self.base


def replace_module(model,name,module):
    parent,_,leaf=name.rpartition('.')
    setattr(model.get_submodule(parent) if parent else model,leaf,module)


class EpisodeSampler:
    """Keep numeric tables small and decode/cache only requested video frames."""
    def __init__(self,path,modality):
        from gr00t.data.dataset.lerobot_episode_loader import LeRobotEpisodeLoader
        from torchcodec.decoders import VideoDecoder
        self.loader=LeRobotEpisodeLoader(path,modality)
        self.modality=modality;self.tables=[];self.decoders=[];self.images=OrderedDict()
        self.prompt=[]
        for i,ep in enumerate(self.loader.episodes_metadata):
            self.tables.append(self.loader._load_parquet_data(ep['episode_index']))
            self.prompt.append(ep['tasks'][0])
            filename=Path(path)/self.loader.video_path_pattern.format(episode_chunk=ep['episode_index']//self.loader.chunk_size,
                video_key='observation.images.ego_view',episode_index=ep['episode_index'])
            self.decoders.append(VideoDecoder(str(filename),dimension_order='NHWC',num_ffmpeg_threads=1))
        self.counts=np.array([len(x)-39 for x in self.tables])
        if np.any(self.counts<=0):raise ValueError('Episode shorter than action horizon')
    def sample(self,episode,frame):
        from gr00t.data.types import VLAStepData,EmbodimentTag
        key=(episode,int(frame));df=self.tables[episode]
        if key not in self.images:
            self.images[key]=self.decoders[episode].get_frame_at(int(frame)).data.numpy()
            if len(self.images)>128:self.images.popitem(last=False)
        return VLAStepData(images={'ego_view':[self.images[key]]},
            states={g:np.stack(df['state.'+g].iloc[[frame]]).astype('float32') for g in self.modality['state'].modality_keys},
            actions={g:np.stack(df['action.'+g].iloc[frame:frame+40]).astype('float32') for g in self.modality['action'].modality_keys},
            text=self.prompt[episode],embodiment=EmbodimentTag.UNITREE_G1_SONIC)
    def random_sample(self,rng):
        e=int(rng.choice(len(self.counts),p=self.counts/self.counts.sum()))
        return self.sample(e,int(rng.integers(self.counts[e])))
    def validation_keys(self,per_episode):
        return [(e,int(t)) for e,n in enumerate(self.counts) for t in np.linspace(0,n-1,per_episode,dtype=int)]


def dump(path,value):path.write_text(json.dumps(value,indent=2)+'\n')


def train(args):
    from gr00t.configs.base_config import get_default_config
    from gr00t.model.gr00t_n1d7.setup import Gr00tN1d7Pipeline
    from huggingface_hub import snapshot_download
    from safetensors.torch import save_file,load_file
    from transformers import set_seed
    from torch.utils.checkpoint import checkpoint
    root=Path(args.dataset).resolve();out=Path(args.output).resolve();base=Path(args.checkpoint).resolve()
    export=json.loads((root/'export_report.json').read_text())
    if not export.get('training_ready_for_fixed_base_profile'):raise ValueError('Requires verified refined labels')
    validation=json.loads((root/'loader_validation.json').read_text())
    if not validation['loader_validation_passed']:raise ValueError('Dataset validation failed')
    for f,h in validation['artifact_sha256'].items():
        if hashlib.sha256((root/f).read_bytes()).hexdigest()!=h:raise ValueError(f'Dataset changed: {f}')
    if out.exists():raise ValueError('Choose a new output directory')
    if not torch.cuda.is_available():raise RuntimeError('CUDA required')
    out.mkdir(parents=True);(out/'experiment_cfg').mkdir()
    set_seed(args.seed);torch.set_num_threads(4);rng=np.random.default_rng(args.seed)
    report=dict(status='initializing',dataset=str(root),base_checkpoint=str(base),execution_profile_id=export['execution_profile_id'],
        scope='Frozen VLM/SONIC; G1 projector slices + action diffusion LoRA; merged standard checkpoint',
        planned_steps=args.steps,gradient_accumulation=args.accumulation,learning_rate=args.learning_rate,
        rank=args.rank,seed=args.seed,policy_pickup_success_validated=False,history=[])
    dump(out/'training_report.json',report)
    started=time.monotonic()
    try:
        backbone=out/'cached_backbone/nvidia/Cosmos-Reason2-2B';backbone.parent.mkdir(parents=True)
        backbone.symlink_to(snapshot_download('nvidia/Cosmos-Reason2-2B',local_files_only=True),target_is_directory=True)
        view=out/'source_checkpoint';view.mkdir()
        for p in base.iterdir():
            if p.name!='config.json':(view/p.name).symlink_to(p)
        conf=json.loads((base/'config.json').read_text());conf['model_name']=str(backbone);dump(view/'config.json',conf)
        config=get_default_config().load_dict({'data':{'download_cache':False,'datasets':[{
            'dataset_paths':[str(root/'train')],'mix_ratio':1.,'embodiment_tag':'unitree_g1_sonic'}]}})
        config.data.modality_configs={'unitree_g1_sonic':config.data.modality_configs['unitree_g1_sonic']}
        config.model.model_name=str(backbone);config.model.load_bf16=True
        config.model.tune_llm=False;config.model.tune_visual=False;config.model.tune_projector=True
        config.model.tune_diffusion_model=False;config.model.tune_vlln=False
        config.model.state_dropout_prob=0.;config.model.reproject_vision=False;config.model.use_relative_action=True
        config.training.start_from_checkpoint=str(view);config.training.transformers_local_files_only=True
        config.training.use_wandb=False;config.training.eval_strategy='no'
        config.training.output_dir=str(out);config.training.num_gpus=1
        config.data.shard_size=64;config.data.episode_sampling_rate=1.;config.data.num_shards_per_epoch=1
        config.data.override_pretraining_statistics=True;config.data.allow_padding=False
        pipeline=Gr00tN1d7Pipeline(config,out/'experiment_cfg');pipeline.setup()
        model=pipeline.return_model();processor=pipeline.return_processor();collator=pipeline.return_collator()
        model.requires_grad_(False);model.to(dtype=torch.bfloat16,device='cuda')
        category=processor.embodiment_id_mapping['unitree_g1_sonic']
        wrappers=[]
        for name,module in list(model.named_modules()):
            if module.__class__.__name__=='CategorySpecificLinear' and name.startswith(('action_head.state_encoder.','action_head.action_encoder.','action_head.action_decoder.')):
                wrapped=G1Linear(module,category);replace_module(model,name,wrapped);wrappers.append((name,wrapped))
            elif isinstance(module,nn.Linear) and name.startswith('action_head.model.transformer_blocks.') and ('.attn' in name or '.ff.' in name):
                wrapped=LoRALinear(module,args.rank);replace_module(model,name,wrapped);wrappers.append((name,wrapped))
        if not any(isinstance(w,LoRALinear) for _,w in wrappers):raise RuntimeError('No LoRA modules selected')
        model.action_head.tune_projector=True;model.action_head.tune_diffusion_model=True
        for block in model.action_head.model.transformer_blocks:
            original=block.forward
            def checkpoint_forward(*inputs,_original=original,**kwargs):
                return checkpoint(_original,*inputs,use_reentrant=False,**kwargs)
            block.forward=checkpoint_forward
        trainable={n:p for n,p in model.named_parameters() if p.requires_grad}
        report.update(trainable_parameters=sum(p.numel() for p in trainable.values()),trainable_names=list(trainable),
                      train_episode_count=8,validation_episode_count=2)
        processor.save_pretrained(out/'processor')
        train_sampler=EpisodeSampler(root/'train',config.data.modality_configs['unitree_g1_sonic'])
        val_sampler=EpisodeSampler(root/'validation',config.data.modality_configs['unitree_g1_sonic'])
        report.update(train_episode_count=len(train_sampler.tables),validation_episode_count=len(val_sampler.tables))
        val_keys=val_sampler.validation_keys(args.validation_samples_per_episode)
        def batch(sample):return collator([processor([{'type':'episode_step','content':sample}])])
        @torch.no_grad()
        def evaluate():
            model.eval();processor.eval();losses=[]
            with torch.random.fork_rng(devices=[0]):
                for i,(e,t) in enumerate(val_keys):
                    torch.manual_seed(10000+i)
                    with torch.autocast('cuda',dtype=torch.bfloat16):loss=model(**batch(val_sampler.sample(e,t)))['loss']
                    losses.append(float(loss))
            model.train();processor.train()
            return float(np.mean(losses))
        def snapshot(path):save_file({n:p.detach().cpu().contiguous() for n,p in trainable.items()},str(path))
        optimizer=torch.optim.AdamW(trainable.values(),lr=args.learning_rate,weight_decay=1e-4)
        baseline=evaluate();best=baseline;best_step=0;snapshot(out/'best_adapter.safetensors')
        report.update(status='training',baseline_validation_flow_loss=baseline,best_validation_flow_loss=best)
        dump(out/'training_report.json',report);print('BASELINE',baseline,'trainable',report['trainable_parameters'],flush=True)
        running=[]
        for step in range(1,args.steps+1):
            optimizer.zero_grad(set_to_none=True)
            lr_factor=min(1.,step/max(1,args.warmup_steps))*(.1+.9*.5*(1+math.cos(math.pi*step/args.steps)))
            for group in optimizer.param_groups:group['lr']=args.learning_rate*lr_factor
            for _ in range(args.accumulation):
                with torch.autocast('cuda',dtype=torch.bfloat16):
                    loss=model(**batch(train_sampler.random_sample(rng)))['loss']
                if not torch.isfinite(loss):raise RuntimeError('Non-finite train loss')
                (loss/args.accumulation).backward();running.append(float(loss.detach()))
            norm=torch.nn.utils.clip_grad_norm_(list(trainable.values()),1.,error_if_nonfinite=True);optimizer.step()
            if step%10==0 or step==1 or step%args.eval_every==0 or step==args.steps:
                record=dict(step=step,train_flow_loss=float(np.mean(running)),grad_norm=float(norm),lr=optimizer.param_groups[0]['lr'],elapsed_s=time.monotonic()-started)
                running=[]
                if step%args.eval_every==0 or step==args.steps:
                    record['validation_flow_loss']=evaluate()
                    if record['validation_flow_loss']<best:
                        best=record['validation_flow_loss'];best_step=step;snapshot(out/'best_adapter.safetensors')
                    snapshot(out/'last_adapter.safetensors')
                report['history'].append(record);report.update(completed_steps=step,best_step=best_step,best_validation_flow_loss=best)
                dump(out/'training_report.json',report);print(json.dumps(record),flush=True)
        # Restore the selected adapter; merge G1 slices/LoRA into original module classes.
        saved=load_file(str(out/'best_adapter.safetensors'),device='cpu')
        with torch.no_grad():
            for name,p in trainable.items():p.copy_(saved[name])
        selected_loss=evaluate();del optimizer,saved
        for name,wrapper in wrappers:replace_module(model,name,wrapper.merge())
        wrappers.clear();trainable.clear();torch.cuda.empty_cache()
        merged_loss=evaluate()
        checkpoint_dir=out/'checkpoint-best';model.eval();model.to('cpu')
        model.save_pretrained(checkpoint_dir,safe_serialization=True,max_shard_size='4GB')
        processor.save_pretrained(checkpoint_dir)
        dump(checkpoint_dir/'simulation_profile.json',dict(execution_profile_id=export['execution_profile_id'],hand_format='dex3_joint_radians',
            inspire_grip_adapter=False,sonic_frozen=True,policy_pickup_success_validated=False))
        report.update(status='complete',best_step=best_step,best_validation_flow_loss=best,
            selected_validation_flow_loss=selected_loss,merged_validation_flow_loss=merged_loss,
            checkpoint=str(checkpoint_dir),peak_cuda_allocated_gib=torch.cuda.max_memory_allocated()/2**30,elapsed_s=time.monotonic()-started)
        dump(out/'training_report.json',report);print('COMPLETE',json.dumps(report,indent=2),flush=True)
    except Exception as exc:
        report.update(status='failed',error=f'{type(exc).__name__}: {exc}',elapsed_s=time.monotonic()-started)
        dump(out/'training_report.json',report);raise

if __name__=='__main__':
    os.environ.setdefault('HF_HUB_OFFLINE','1');os.environ.setdefault('TOKENIZERS_PARALLELISM','false')
    os.environ.setdefault('NO_ALBUMENTATIONS_UPDATE','1')
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset',default='outputs/gr00t_dex3_refined_v1')
    p.add_argument('--checkpoint',default='checkpoints/cloudwalk_g1_bottle_v10/checkpoint-30000')
    p.add_argument('--output',required=True);p.add_argument('--steps',type=int,default=500)
    p.add_argument('--accumulation',type=int,default=2);p.add_argument('--rank',type=int,default=8)
    p.add_argument('--learning-rate',type=float,default=1e-4);p.add_argument('--warmup-steps',type=int,default=20)
    p.add_argument('--eval-every',type=int,default=50);p.add_argument('--validation-samples-per-episode',type=int,default=8)
    p.add_argument('--seed',type=int,default=42)
    args=p.parse_args()
    if min(args.steps,args.accumulation,args.rank,args.eval_every,args.validation_samples_per_episode)<=0:
        p.error('steps, accumulation, rank and evaluation counts must be positive')
    if not 0<args.learning_rate<1:p.error('learning-rate must be in (0, 1)')
    train(args)
