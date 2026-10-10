"""Audit the CloudWalk Inspire FTP checkpoint against this Dex3 simulator.

Does not load GPU weights or infer that equal dimensionality means compatibility.
"""
import argparse
import json
from pathlib import Path
import struct


def audit(path):
    path = Path(path).expanduser().resolve()
    processor = json.loads((path / 'processor_config.json').read_text())
    modalities = processor['processor_kwargs']['modality_configs']['unitree_g1_sonic']
    stats = json.loads((path / 'statistics.json').read_text())['unitree_g1_sonic']
    index = json.loads((path / 'model.safetensors.index.json').read_text())['weight_map']
    missing = []
    for shard in sorted(set(index.values())):
        file = path / shard
        if not file.is_file():
            missing.append(shard)
            continue
        with file.open('rb') as stream:
            raw = stream.read(8)
            if len(raw) != 8:
                raise ValueError('Truncated safetensors shard: ' + shard)
            size = struct.unpack('<Q', raw)[0]
            if size > 100_000_000:
                raise ValueError('Invalid safetensors header: ' + shard)
            header = json.loads(stream.read(size))
        if any(name not in header for name, owner in index.items() if owner == shard):
            raise ValueError('Shard does not contain tensors declared in index: ' + shard)
        for name, tensor in header.items():
            if name != '__metadata__' and 8 + size + tensor['data_offsets'][1] > file.stat().st_size:
                raise ValueError('Incomplete tensor data: ' + name)
    hand_zero = all(all(v == 0 for v in stats['state'][key]['min']) and
                    all(v == 0 for v in stats['state'][key]['max'])
                    for key in ['left_hand', 'right_hand'])
    source_file = path.parent / 'source.json'
    source = json.loads(source_file.read_text()) if source_file.exists() else None
    return {'checkpoint': str(path), 'missing_shards': missing,
            'source': source,
            'weight_files_complete': not missing,
            'embodiment': 'unitree_g1_sonic',
            'action_keys': modalities['action']['modality_keys'],
            'action_horizon': len(modalities['action']['delta_indices']),
            'training_hand_observations_constant_zero': hand_zero,
            'source_hand': 'Normalized grip channels; native joint mapping requires dataset verification',
            'right_hand_action_statistics': stats['action']['right_hand_joints'],
            'current_simulator_hand': 'Unitree Dex3',
            'native_hand_compatibility': False,
            'dex3_adapter_status': 'Experimental grip-intent mapping; not Inspire geometry',
            'required_for_native_deployment': ['Inspire FTP URDF/MJCF and collision meshes',
                'InspireFTPGripMapper channel order/ranges',
                'matching SONIC controller checkpoint and deployment configuration']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('checkpoint', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = audit(args.checkpoint)
    text = json.dumps(report, indent=2)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + '\n')
    if report['missing_shards']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
