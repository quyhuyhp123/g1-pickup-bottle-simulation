"""Small real v10 optimizer smoke test; saves ONLY action-decoder weights.

Not a complete fine-tuned checkpoint and not for robot deployment. Frozen VLM,
SONIC and diffusion transformer. Explicit opt-in required for unvalidated tokens.
Run with Isaac-GR00T Python and its repository on PYTHONPATH.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path


def main(args):
    import torch
    from gr00t.configs.base_config import get_default_config
    from gr00t.model.gr00t_n1d7.setup import Gr00tN1d7Pipeline
    from safetensors.torch import save_file
    from transformers import set_seed
    from huggingface_hub import snapshot_download
    root=Path(args.dataset).resolve();out=Path(args.output).resolve()
    if not args.experimental_unvalidated_sonic:
        raise ValueError('Explicit --experimental-unvalidated-sonic required')
    if not (root/'loader_validation.json').is_file():raise ValueError('Run dataset loader validation first')
    validation=json.loads((root/'loader_validation.json').read_text())
    if not validation['loader_validation_passed']:raise ValueError('Invalid dataset')
    if not validation.get('artifact_sha256'):raise ValueError('Run loader validation again to fingerprint the dataset')
    for filename,digest in validation['artifact_sha256'].items():
        if hashlib.sha256((root/filename).read_bytes()).hexdigest()!=digest:
            raise ValueError(f'Dataset changed after loader validation: {filename}')
    if out.exists():raise ValueError('Use a new output directory; never overwrite a run')
    if not torch.cuda.is_available():raise RuntimeError('CUDA required for this smoke test')
    if not 1<=args.steps<=20:raise ValueError('Smoke test supports 1..20 steps only')
    out.mkdir(parents=True);(out/'experiment_cfg').mkdir()
    set_seed(42);torch.set_num_threads(4)
    report={'status':'initializing','training_ready':False,'sonic_validated':False,
        'base_checkpoint':str(Path(args.checkpoint).resolve()),'dataset':str(root),
        'dataset_report_sha256':hashlib.sha256((root/'export_report.json').read_bytes()).hexdigest(),
        'scope':'Only action_head.action_decoder updated; VLM/diffusion/SONIC frozen',
        'deployment_ready':False,'hand_contract':'native Dex3 joint radians, not Inspire normalized grip',
        'held_out_evaluation':'not performed by this pipeline smoke test','steps':[]}
    def save_report(): (out/'smoke_report.json').write_text(json.dumps(report,indent=2)+'\n')
    save_report()
    try:
        # Resolve the cached backbone to a local path. Some Transformers versions
        # query Hub metadata for tokenizer heuristics even with local_files_only.
        snapshot=snapshot_download('nvidia/Cosmos-Reason2-2B',local_files_only=True)
        # Upstream selects the backbone class by this name substring.
        backbone_view=out/'cached_backbone/nvidia/Cosmos-Reason2-2B'
        backbone_view.parent.mkdir(parents=True)
        backbone_view.symlink_to(snapshot,target_is_directory=True)
        backbone=str(backbone_view)
        base=Path(args.checkpoint).resolve()
        view=out/'source_checkpoint';view.mkdir()
        for source in base.iterdir():
            if source.name!='config.json': (view/source.name).symlink_to(source)
        model_config=json.loads((base/'config.json').read_text())
        model_config['model_name']=backbone
        (view/'config.json').write_text(json.dumps(model_config,indent=2)+'\n')
        config=get_default_config().load_dict({'data':{'download_cache':False,'datasets':[{
            'dataset_paths':[str(root/'train')],'mix_ratio':1.,'embodiment_tag':'unitree_g1_sonic'}]}})
        # Other registered embodiments have a 50-step horizon; this checkpoint
        # and dataset use 40. Only register the embodiment used in this run.
        config.data.modality_configs={'unitree_g1_sonic':config.data.modality_configs['unitree_g1_sonic']}
        config.model.model_name=backbone
        config.model.tune_llm=False;config.model.tune_visual=False
        config.model.tune_projector=True;config.model.tune_diffusion_model=False;config.model.tune_vlln=False
        config.model.load_bf16=True;config.model.state_dropout_prob=0.
        config.model.reproject_vision=False;config.model.use_relative_action=True
        config.training.start_from_checkpoint=str(view)
        config.training.transformers_local_files_only=True
        config.training.use_wandb=False;config.training.eval_strategy='no'
        config.training.output_dir=str(out);config.training.num_gpus=1
        config.data.shard_size=64;config.data.episode_sampling_rate=1.
        config.data.num_shards_per_epoch=1;config.data.override_pretraining_statistics=True
        config.data.allow_padding=False
        pipeline=Gr00tN1d7Pipeline(config,out/'experiment_cfg');pipeline.setup()
        model=pipeline.return_model()
        model.requires_grad_(False);model.to(dtype=torch.bfloat16)
        model.action_head.action_decoder.float().requires_grad_(True)
        model.to('cuda');model.train()
        trainable={n:p for n,p in model.named_parameters() if p.requires_grad}
        report['trainable_parameters']=sum(p.numel() for p in trainable.values())
        report['trainable_names']=list(trainable)
        before={n:p.detach().cpu().clone() for n,p in trainable.items()}
        optimizer=torch.optim.AdamW(trainable.values(),lr=args.learning_rate)
        train_dataset,_=pipeline.return_dataset()
        collator=pipeline.return_collator()
        processor=pipeline.return_processor();processor.save_pretrained(out/'processor')
        iterator=iter(train_dataset)
        report['status']='training';save_report()
        for step in range(args.steps):
            batch=collator([next(iterator)])
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast('cuda',dtype=torch.bfloat16):
                result=model(**batch)
                loss=result['loss']
            if not torch.isfinite(loss):raise RuntimeError('Non-finite loss')
            loss.backward()
            norm=torch.nn.utils.clip_grad_norm_(list(trainable.values()),1.,error_if_nonfinite=True)
            optimizer.step()
            record={'step':step+1,'loss':float(loss.detach()),'grad_norm':float(norm)}
            report['steps'].append(record);save_report();print(record,flush=True)
        state={n:p.detach().cpu().contiguous() for n,p in trainable.items()}
        max_change=max(float((state[n]-before[n]).abs().max()) for n in state)
        if max_change<=0:raise RuntimeError('Optimizer did not change weights')
        save_file(state,str(out/'action_decoder_only.safetensors'))
        report.update(status='complete',max_parameter_change=max_change,
            peak_cuda_allocated_gib=torch.cuda.max_memory_allocated()/2**30,
            artifact='action_decoder_only.safetensors (partial weights, NOT a full policy checkpoint)')
        save_report();print(json.dumps(report,indent=2),flush=True)
    except Exception as exc:
        report.update(status='failed',error=f'{type(exc).__name__}: {exc}');save_report();raise

if __name__=='__main__':
    os.environ.setdefault('HF_HUB_OFFLINE','1')
    os.environ.setdefault('TOKENIZERS_PARALLELISM','false')
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset',default='outputs/gr00t_dex3_refined_v1')
    p.add_argument('--checkpoint',default='checkpoints/cloudwalk_g1_bottle_v10/checkpoint-30000')
    p.add_argument('--output',required=True)
    p.add_argument('--steps',type=int,default=3)
    p.add_argument('--learning-rate',type=float,default=1e-5)
    p.add_argument('--experimental-unvalidated-sonic',action='store_true')
    main(p.parse_args())
