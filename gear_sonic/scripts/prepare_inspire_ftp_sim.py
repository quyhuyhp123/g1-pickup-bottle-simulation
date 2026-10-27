"""Build a separate G1 + native Inspire FTP scene from pinned Unitree URDFs.

Downloads only model descriptions/meshes. Never starts a hardware connection.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import urllib.request
import xml.etree.ElementTree as ET

import mujoco

REVISION = '5994d4faef0a9cadd3287f8de0199a67eeb2a259'
BASE = f'https://raw.githubusercontent.com/unitreerobotics/unitree_ros/{REVISION}/robots/g1_description/'
ROOT = Path(__file__).resolve().parents[2]
URDF = 'g1_29dof_rev_1_0_with_inspire_hand_FTP.urdf'
HAND_NAMES = ('thumb_1', 'thumb_2', 'index_1', 'middle_1', 'ring_1', 'little_1')


def download(output):
    output.mkdir(parents=True, exist_ok=True)
    def fetch(relative):
        path = output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            with urllib.request.urlopen(BASE + relative, timeout=60) as response:
                blob = response.read()
            temporary = path.with_suffix(path.suffix + '.download')
            temporary.write_bytes(blob)
            temporary.replace(path)
        return path
    source = fetch(URDF)
    names = sorted({Path(m.get('filename')).name for m in ET.parse(source).findall('.//mesh')})
    with ThreadPoolExecutor(max_workers=6) as pool:
        paths = list(pool.map(fetch, ['meshes/' + name for name in names]))
    manifest = {'repository': 'https://github.com/unitreerobotics/unitree_ros',
        'revision': REVISION, 'files': {str(p.relative_to(output)): hashlib.sha256(p.read_bytes()).hexdigest()
                                      for p in [source, *paths]}}
    (output/'source.json').write_text(json.dumps(manifest, indent=2))
    return source


def build(source, output):
    output.mkdir(parents=True, exist_ok=True)
    urdf = ET.parse(source)
    compiler = urdf.find('mujoco/compiler')
    compiler.set('meshdir', str((source.parent/'meshes').resolve()))
    # Preserve fixed palm/sensor link inertias. Fusing a fixed root into world
    # otherwise discards its mass when a standalone hand is later attached.
    compiler.set('fusestatic', 'false')
    for mesh in urdf.findall('.//mesh'):
        mesh.set('filename', Path(mesh.get('filename')).name)
    with tempfile.TemporaryDirectory() as tmp:
        converted = Path(tmp)/'g1.urdf'
        urdf.write(converted)
        imported = mujoco.MjModel.from_xml_path(str(converted))
        mjcf = output/'g1_inspire_ftp.xml'
        mujoco.mj_saveLastXML(str(mjcf), imported)
    tree = ET.parse(mjcf)
    root = tree.getroot()
    root.set('model', 'G1 Inspire RH56DFTP - 41 active joints')
    ET.SubElement(root, 'option', timestep='0.002', integrator='implicitfast')
    pelvis = root.find("worldbody/body[@name='pelvis']")
    pelvis.set('pos', '0 0 0.793')
    ET.SubElement(pelvis, 'freejoint', name='floating_base_joint')
    equality = root.find('equality')
    if equality is None:
        equality = ET.SubElement(root, 'equality')
    # Explicit preview fixture. There is no standing/balance controller here.
    ET.SubElement(equality, 'weld', name='preview_pelvis_fixture', body1='pelvis')
    contact = ET.SubElement(root, 'contact')
    for side in ('left', 'right'):
        # Convex palm mesh overlaps the internal thumb hinge at zero angle.
        # Exclude only this mechanical neighbour, keeping finger/object contacts.
        ET.SubElement(contact, 'exclude', body1=side+'_base_link', body2=side+'_thumb_2')
    actuators = ET.SubElement(root, 'actuator')
    for joint in urdf.findall('joint'):
        if joint.get('type') not in ('revolute', 'continuous'):
            continue
        name = joint.get('name')
        mimic = joint.find('mimic')
        if mimic is not None:
            for old in list(equality):
                if old.get('joint1') == name:
                    equality.remove(old)
            ET.SubElement(equality, 'joint', name=name+'_mimic', joint1=name,
                joint2=mimic.get('joint'), polycoef=f"{mimic.get('offset', '0')} {mimic.get('multiplier', '1')} 0 0 0",
                solref='0.004 1')
        else:
            hand = any(name == side+'_'+finger+'_joint' for side in ('left', 'right') for finger in HAND_NAMES)
            limit = joint.find('limit')
            effort = limit.get('effort')
            ET.SubElement(actuators, 'position', name=name+'_act', joint=name,
                kp='4' if hand else '150', kv='.08' if hand else '6',
                forcelimited='true', forcerange=f'-{effort} {effort}',
                ctrllimited='true', ctrlrange=f"{limit.get('lower')} {limit.get('upper')}")
        mj_joint = root.find(f".//joint[@name='{name}']")
        mj_joint.set('armature', '.001' if any(f in name for f in ('thumb', 'index', 'middle', 'ring', 'little')) else '.01')
        mj_joint.set('damping', '.02')
    # The hand's numerous welded tactile mesh pieces belong to one rigid link.
    # Native MuJoCo contact filtering excludes welded bodies automatically.
    scene = ET.parse(ROOT/'gear_sonic/data/robot_model/model_data/g1/scene_43dof.xml').getroot()
    for section in ('visual', 'statistic'):
        root.append(copy.deepcopy(scene.find(section)))
    root.find('asset').extend(copy.deepcopy(list(scene.find('asset'))))
    root.find('worldbody').extend(copy.deepcopy(list(scene.find('worldbody'))))
    ET.indent(tree)
    tree.write(mjcf)
    model = mujoco.MjModel.from_xml_path(str(mjcf))
    if model.nu != 41 or model.njnt != 55 or model.neq != 13:
        raise ValueError(f'Unexpected topology: {model.nu=}, {model.njnt=}, {model.neq=}')
    # Runtime variant uses torque actuators; DefaultEnv supplies PD control.
    runtime = copy.deepcopy(root)
    runtime.find("equality").remove(runtime.find("equality/weld[@name='preview_pelvis_fixture']"))
    for actuator in runtime.find('actuator'):
        actuator.tag = 'motor'
        for key in ('kp', 'kv', 'ctrllimited', 'ctrlrange'):
            actuator.attrib.pop(key, None)
    torso = runtime.find(".//body[@name='torso_link']")
    ET.SubElement(torso, 'camera', name='head_camera', pos='0.06 0 0.45', euler='0 -0.8 -1.57')
    for side in ('left', 'right'):
        wrist = runtime.find(f".//body[@name='{side}_wrist_yaw_link']")
        ET.SubElement(wrist, 'site', name=side+'_hand_grasp_center',
                      pos='0.165 0.045 0' if side == 'right' else '0.165 -0.045 0',
                      size='.005', rgba='0 1 0 1', group='5')
    runtime_path = output/'g1_inspire_ftp_pickup.xml'
    ET.indent(runtime)
    ET.ElementTree(runtime).write(runtime_path)
    mujoco.MjModel.from_xml_path(str(runtime_path))
    return mjcf


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'models/g1_inspire_ftp')
    args = parser.parse_args()
    source = download(args.output)
    result = build(source, args.output)
    print(f'Built {result}: 29 body + 12 active hand joints; 12 passive mimic joints.')
