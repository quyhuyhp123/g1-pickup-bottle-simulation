"""Convert an official Inspire FTP hand URDF to a standalone MuJoCo model.

This prepares geometry and mimic constraints; it does not replace the G1 DDS
bridge or establish the CloudWalk channel-to-motor mapping.
"""
import argparse
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

import mujoco


def convert(source: Path, destination: Path):
    urdf = ET.parse(source)
    root = urdf.getroot()
    compiler = root.find("mujoco/compiler")
    if compiler is None:
        raise ValueError("Expected the official URDF's MuJoCo compiler element")
    compiler.set("meshdir", str((source.parent / "meshes").resolve()))
    for mesh in root.findall(".//mesh"):
        mesh.set("filename", Path(mesh.get("filename")).name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        imported = Path(temporary) / "hand.urdf"
        urdf.write(imported)
        model = mujoco.MjModel.from_xml_path(str(imported))
        mujoco.mj_saveLastXML(str(destination), model)
    tree = ET.parse(destination)
    xml = tree.getroot()
    equality = xml.find("equality")
    if equality is None:
        equality = ET.SubElement(xml, "equality")
    existing_mimics = {joint.get("joint1") for joint in equality.findall("joint")}
    actuators = ET.SubElement(xml, "actuator")
    for joint in root.findall("joint"):
        if joint.get("type") not in ("revolute", "continuous"):
            continue
        mimic = joint.find("mimic")
        if mimic is not None:
            if joint.get("name") not in existing_mimics:
                ET.SubElement(equality, "joint", {
                    "joint1": joint.get("name"), "joint2": mimic.get("joint"),
                    "polycoef": f"{mimic.get('offset', '0')} {mimic.get('multiplier', '1')} 0 0 0",
                })
        else:
            limit = joint.find("limit")
            ET.SubElement(actuators, "position", {
                "name": joint.get("name") + "_act", "joint": joint.get("name"),
                "kp": "20", "kv": "0.5", "forcerange": "-10 10",
                "ctrllimited": "true", "ctrlrange": limit.get("lower") + " " + limit.get("upper"),
            })
    ET.indent(tree)
    tree.write(destination)
    model = mujoco.MjModel.from_xml_path(str(destination))
    if (model.nu, model.njnt, model.neq) != (6, 12, 6):
        raise ValueError(f"Unexpected FTP topology: {model.nu=}, {model.njnt=}, {model.neq=}")
    return model


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    model = convert(args.source, args.destination)
    print(f"Compiled {args.destination}: {model.nu} motors, {model.njnt} joints, {model.neq} mimic constraints")
