#!/usr/bin/env python3
"""Download upstream LFS assets outside Git; default is simulation/runtime assets."""
import argparse, hashlib, json, pathlib, urllib.request, os
ROOT = pathlib.Path(__file__).resolve().parents[1]
REVISION = 'b042411fae38ee4d1af9aac82a37a1f8d14d6dd0'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--all', action='store_true', help='Also download optional training/demo assets')
args = parser.parse_args()
for item in json.loads((ROOT/'runtime_assets_manifest.json').read_text()):
    name = item['path']
    if not args.all and not name.startswith(('gear_sonic/data/', 'gear_sonic_deploy/', 'external_dependencies/')):
        continue
    path = ROOT/name
    if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256']:
        continue
    path.parent.mkdir(parents=True, exist_ok=True)
    url = 'https://media.githubusercontent.com/media/NVlabs/GR00T-WholeBodyControl/' + REVISION + '/' + name
    print('Downloading', name, flush=True)
    temporary = path.with_suffix(path.suffix+'.download')
    urllib.request.urlretrieve(url, temporary)
    if hashlib.sha256(temporary.read_bytes()).hexdigest() != item['sha256']:
        temporary.unlink()
        raise RuntimeError('Checksum mismatch: '+name)
    os.replace(temporary, path)
print('Runtime assets ready. SONIC ONNX and GR00T weights must be downloaded separately; see README.')
