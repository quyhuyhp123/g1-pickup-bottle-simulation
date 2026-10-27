"""MuJoCo simulation environment and loop for the G1 (and H1) humanoid robots.

DefaultEnv owns the MuJoCo model/data, computes PD torques from Unitree SDK
commands, steps physics, and publishes observations back via the SDK bridge.
BaseSimulator wraps DefaultEnv with rate-limiting and viewer/image update loops.
"""

import os
import pathlib
from pathlib import Path
import pickle
import tempfile
from queue import Queue
from threading import Event, Lock, Thread
import time
from typing import Dict
import xml.etree.ElementTree as ET

import mujoco
import mujoco.viewer
import numpy as np
from scipy.spatial.transform import Rotation
from unitree_sdk2py.core.channel import ChannelFactoryInitialize

from gear_sonic.utils.mujoco_sim.metric_utils import check_contact, check_height
from gear_sonic.utils.mujoco_sim.sim_utils import get_subtree_body_names
from gear_sonic.utils.mujoco_sim.unitree_sdk2py_bridge import ElasticBand, UnitreeSdk2Bridge
from gear_sonic.utils.mujoco_sim.robot import Robot
from gear_sonic.utils.diagnostic_writer import DiagnosticWriter

GEAR_SONIC_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class DefaultEnv:
    """Base environment class that handles simulation environment setup and step"""

    def __init__(
        self,
        config: Dict[str, any],
        env_name: str = "default",
        camera_configs: Dict[str, any] = {},
        onscreen: bool = False,
        offscreen: bool = False,
        enable_image_publish: bool = False,
    ):
        from gear_sonic.utils.inference.policy_control import validate_policy_simulation
        validate_policy_simulation(config)
        self.config = config
        self.env_name = env_name
        self.robot = Robot(self.config)
        self.num_body_dof = self.robot.NUM_JOINTS
        self.num_hand_dof = self.robot.NUM_HAND_JOINTS
        self.sim_dt = self.config["SIMULATE_DT"]
        self.obs = None
        self.torques = np.zeros(self.num_body_dof + self.num_hand_dof * 2)
        self.torque_limit = np.array(self.robot.MOTOR_EFFORT_LIMIT_LIST)
        self.camera_configs = camera_configs

        if not camera_configs and offscreen and enable_image_publish:
            self.camera_configs = {
                "ego_view": {"height": 480, "width": 640, "mjcf_name": "head_camera"},
            }

        self.reward_lock = Lock()
        self.unitree_bridge = None
        self.onscreen = onscreen
        self.elastic_band = None
        self._bottle_reset_requested = Event()
        self.ui_commands = Queue()
        self.ui_snapshot = {}
        self.ground_start = self.config.get("GROUND_START", False)
        self.standby = self.ground_start
        self._control_transition_started = None
        self.bottle_placement = None
        self.scene_changed_at = time.monotonic()
        self.detection_preview = None
        self._preview_capture = 0.
        self._viewer_overlay_worker = None

        self.native_inspire = self.config.get("NATIVE_INSPIRE", False)
        self.init_scene()
        self.assisted_pickup = None
        if self.config.get('ASSISTED_PICKUP', False):
            from gear_sonic.utils.mujoco_sim.assisted_pickup import AssistedPickup
            self.assisted_pickup = AssistedPickup(self.mj_model)
        if self.viewer is not None:
            from gear_sonic.utils.mujoco_sim.viewer_overlay import ViewerOverlayWorker
            self._viewer_overlay_worker = ViewerOverlayWorker(self.viewer)
        self.last_reward = 0

        self.offscreen = offscreen
        self.async_image_render = bool(offscreen and enable_image_publish
                                       and self.config.get("ASYNC_IMAGE_RENDER", False))
        if self.offscreen and not self.async_image_render:
            self.init_renderers()
        self.image_dt = self.config.get("IMAGE_DT", 0.033333)
        self.image_publish_process = None
        diagnostic_path = self.config.get("REACH_DIAGNOSTIC_PATH", "")
        self.reach_diagnostic_writer = (DiagnosticWriter(
            Path(diagnostic_path).with_suffix(".jsonl"), latest_path=diagnostic_path
        ) if diagnostic_path else None)

        if self.config.get('RECORD_DIR'):
            from gear_sonic.utils.mujoco_sim.episode_recorder import EpisodeRecorder
            self.episode_recorder = EpisodeRecorder(self.mj_model, self.config['RECORD_DIR'],
                self.config['RECORD_PROMPT'], self.config['RECORD_FPS'])
            print('[Recorder] Preparing camera before simulation start...', flush=True)
            self.episode_recorder.prepare(self.mj_data)
            print('[Recorder] Camera ready.', flush=True)

    def start_image_publish_subprocess(self, start_method: str = "spawn", camera_port: int = 5555):
        if self._viewer_overlay_worker is not None:
            self._viewer_overlay_worker.camera_port = camera_port
        if self.async_image_render:
            from gear_sonic.utils.mujoco_sim.async_camera import AsyncCameraProcess
            self.image_publish_process = AsyncCameraProcess(
                pathlib.Path(GEAR_SONIC_ROOT) / self.config["ROBOT_SCENE"],
                self.camera_configs, port=camera_port,
                publish_depth=self.config.get("ENABLE_DEPTH_PUBLISH", False),
            )
            self.image_publish_process.start_process()
            return
        from gear_sonic.utils.mujoco_sim.image_publish_utils import ImagePublishProcess

        if len(self.camera_configs) == 0:
            print(
                "Warning: No camera configs provided, image publishing subprocess will not be started"
            )
            return
        start_method = self.config.get("MP_START_METHOD", "spawn")
        self.image_publish_process = ImagePublishProcess(
            camera_configs=self.camera_configs,
            image_dt=self.image_dt,
            zmq_port=camera_port,
            start_method=start_method,
            verbose=self.config.get("verbose", False),
        )
        self.image_publish_process.start_process()

    def _get_dof_indices_by_class(self):
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".xml") as f:
            mujoco.mj_saveLastXML(f.name, self.mj_model)
            temp_xml_path = f.name

        try:
            tree = ET.parse(temp_xml_path)
            root = tree.getroot()

            joint_class_map = {}
            for joint_element in root.findall(".//joint[@class]"):
                joint_name = joint_element.get("name")
                joint_class = joint_element.get("class")
                if joint_name and joint_class:
                    joint_id = mujoco.mj_name2id(
                        self.mj_model, mujoco.mjtObj.mjOBJ_JOINT, joint_name
                    )
                    if joint_id != -1:
                        dof_adr = self.mj_model.jnt_dofadr[joint_id]
                        if joint_class not in joint_class_map:
                            joint_class_map[joint_class] = []
                        joint_class_map[joint_class].append(dof_adr)
        finally:
            os.remove(temp_xml_path)

        return joint_class_map

    def _get_default_dof_properties(self):
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".xml") as f:
            mujoco.mj_saveLastXML(f.name, self.mj_model)
            temp_xml_path = f.name

        try:
            tree = ET.parse(temp_xml_path)
            root = tree.getroot()

            default_dof_properties = {}
            for default_element in root.findall(".//default/default[@class]"):
                class_name = default_element.get("class")
                joint_element = default_element.find("joint")
                if class_name and joint_element is not None:
                    properties = {}
                    if "damping" in joint_element.attrib:
                        properties["damping"] = float(joint_element.get("damping"))
                    if "armature" in joint_element.attrib:
                        properties["armature"] = float(joint_element.get("armature"))
                    if "frictionloss" in joint_element.attrib:
                        properties["frictionloss"] = float(joint_element.get("frictionloss"))

                    if properties:
                        default_dof_properties[class_name] = properties
        finally:
            os.remove(temp_xml_path)

        return default_dof_properties

    def init_scene(self):
        """Initialize the default robot scene"""
        xml_path = str(pathlib.Path(GEAR_SONIC_ROOT) / self.config["ROBOT_SCENE"])
        self.mj_model = mujoco.MjModel.from_xml_path(xml_path)
        if self.config.get('FIXED_PICKUP_BASE', False):
            from gear_sonic.scripts.run_blue_bottle_pickup import load_anchored_scene
            self.mj_model = load_anchored_scene(xml_path)
        self.mj_data = mujoco.MjData(self.mj_model)
        mujoco.mj_forward(self.mj_model, self.mj_data)
        self.mj_model.opt.timestep = self.sim_dt
        self.torso_index = mujoco.mj_name2id(self.mj_model, mujoco.mjtObj.mjOBJ_BODY, "torso_link")
        self.root_body = "pelvis"
        self.root_body_id = self.mj_model.body(self.root_body).id
        if self.ground_start:
            floor = self.mj_model.geom('floor').id
            foot_geoms = [g for g in range(self.mj_model.ngeom)
                          if 'ankle' in self.mj_model.body(int(self.mj_model.geom_bodyid[g])).name
                          and self.mj_model.geom_contype[g]]
            if foot_geoms:
                clearance = min(mujoco.mj_geomDistance(self.mj_model, self.mj_data, floor, g, 1., np.zeros(6))
                                for g in foot_geoms)
                # The XML pose has a ~1 mm sole gap. Seat the locked startup
                # pose on the floor instead of suspending it above contact.
                if 0. < clearance < .05:
                    self.mj_model.qpos0[2] -= clearance + 1e-5
                    self.mj_data.qpos[:] = self.mj_model.qpos0
                    mujoco.mj_forward(self.mj_model, self.mj_data)
        self.initial_qpos = self.mj_model.qpos0.copy()
        if self.ground_start:
            # Retract the right palm before an object is placed; keep the left
            # fingers above the tabletop when the waist leans forward.
            # Keep qpos0 (joint reference angles) unchanged.
            for side, pitch in (('left', -.2), ('right', .35)):
                joint = self.mj_model.joint(f'{side}_shoulder_pitch_joint')
                self.initial_qpos[int(joint.qposadr[0])] = pitch
            self.initial_qpos[int(self.mj_model.joint('left_elbow_joint').qposadr[0])] = .3
            if self.native_inspire:
                for side in ('left', 'right'):
                    self.initial_qpos[self.mj_model.joint(side+'_shoulder_pitch_joint').qposadr[0]] = .35
                    self.initial_qpos[self.mj_model.joint(side+'_elbow_joint').qposadr[0]] = -.7
                    self.initial_qpos[self.mj_model.joint(side+'_thumb_1_joint').qposadr[0]] = 1.0
            self.mj_data.qpos[:] = self.initial_qpos
            mujoco.mj_forward(self.mj_model, self.mj_data)

        self.joint_class_map = self._get_dof_indices_by_class()

        self.perform_sysid_search = self.config.get("perform_sysid_search", False)

        # Check for static root link (fixed base)
        self.use_floating_root_link = "floating_base_joint" in [
            self.mj_model.joint(i).name for i in range(self.mj_model.njnt)
        ]
        self.use_constrained_root_link = "constrained_base_joint" in [
            self.mj_model.joint(i).name for i in range(self.mj_model.njnt)
        ]

        # MuJoCo qpos/qvel arrays start with root DOFs before joint DOFs:
        # floating base has 7 qpos (pos + quat) and 6 qvel (lin + ang velocity)
        if self.use_floating_root_link:
            self.qpos_offset = 7
            self.qvel_offset = 6
        else:
            if self.use_constrained_root_link:
                self.qpos_offset = 1
                self.qvel_offset = 1
            else:
                raise ValueError(
                    "No root link found --"
                    "The absolute static root will make the simulation unstable."
                )

        # Enable the elastic band
        if self.config["ENABLE_ELASTIC_BAND"] and self.use_floating_root_link:
            self.elastic_band = ElasticBand()
            if "g1" in self.config["ROBOT_TYPE"]:
                if self.config["enable_waist"]:
                    self.band_attached_link = self.mj_model.body("pelvis").id
                else:
                    self.band_attached_link = self.mj_model.body("torso_link").id
            elif "h1" in self.config["ROBOT_TYPE"]:
                self.band_attached_link = self.mj_model.body("torso_link").id
            else:
                self.band_attached_link = self.mj_model.body("base_link").id

            if self.ground_start:
                self._ground_support_point = self.mj_data.xpos[self.band_attached_link].copy()
                self.elastic_band.point = self._ground_support_point.copy()

            if self.onscreen:
                self.viewer = mujoco.viewer.launch_passive(
                    self.mj_model,
                    self.mj_data,
                    key_callback=self._viewer_key_callback,
                    show_left_ui=False,
                    show_right_ui=False,
                )
            else:
                mujoco.mj_forward(self.mj_model, self.mj_data)
                self.viewer = None
        else:
            if self.onscreen:
                self.viewer = mujoco.viewer.launch_passive(
                    self.mj_model, self.mj_data, key_callback=self._viewer_key_callback,
                    show_left_ui=False, show_right_ui=False
                )
            else:
                mujoco.mj_forward(self.mj_model, self.mj_data)
                self.viewer = None

        if self.viewer:
            # The green grasp-reference marker is for the human viewer only.
            # Offscreen cameras keep default sitegroup[5] = 0.
            self.viewer.opt.sitegroup[5] = 1
            self.viewer.cam.azimuth = 120
            self.viewer.cam.elevation = -30
            self.viewer.cam.distance = 2.0
            self.viewer.cam.lookat = np.array([0, 0, 0.5])
            self.viewer.cam.type = mujoco.mjtCamera.mjCAMERA_TRACKING
            self.viewer.cam.trackbodyid = self.mj_model.body("pelvis").id

        self.body_joint_index = []
        self.left_hand_index = []
        self.right_hand_index = []
        for i in range(self.mj_model.njnt):
            name = self.mj_model.joint(i).name
            if any(
                [
                    part_name in name
                    for part_name in ["hip", "knee", "ankle", "waist", "shoulder", "elbow", "wrist"]
                ]
            ):
                self.body_joint_index.append(i)
            elif "left_hand" in name:
                self.left_hand_index.append(i)
            elif "right_hand" in name:
                self.right_hand_index.append(i)

        if self.native_inspire:
            from gear_sonic.scripts.prepare_inspire_ftp_sim import HAND_NAMES
            self.left_hand_index = [self.mj_model.joint('left_'+n+'_joint').id for n in HAND_NAMES]
            self.right_hand_index = [self.mj_model.joint('right_'+n+'_joint').id for n in HAND_NAMES]
        assert len(self.body_joint_index) == self.robot.NUM_JOINTS
        assert len(self.left_hand_index) == self.robot.NUM_HAND_JOINTS
        assert len(self.right_hand_index) == self.robot.NUM_HAND_JOINTS

        self.body_joint_index = np.array(self.body_joint_index)
        self.arm_motor_indices = np.asarray([i for i, joint in enumerate(self.body_joint_index)
            if any(part in self.mj_model.joint(int(joint)).name for part in ("shoulder", "elbow", "wrist"))], dtype=int)
        self.arm_dof_addresses = self.mj_model.jnt_dofadr[self.body_joint_index[self.arm_motor_indices]]
        self.left_hand_index = np.array(self.left_hand_index)
        self.right_hand_index = np.array(self.right_hand_index)

        # Passive finger joints mean joint IDs are no longer actuator IDs.
        self.joint_actuator = {int(j): i for i, j in enumerate(self.mj_model.actuator_trnid[:, 0])}
        self.body_actuator = np.array([self.joint_actuator[int(j)] for j in self.body_joint_index])
        self.left_hand_actuator = np.array([self.joint_actuator[int(j)] for j in self.left_hand_index])
        self.right_hand_actuator = np.array([self.joint_actuator[int(j)] for j in self.right_hand_index])
        if self.native_inspire:
            self.torques = np.zeros(self.mj_model.nu)
            self.torque_limit = self.mj_model.actuator_forcerange[:, 1].copy()
        if mujoco.mj_name2id(self.mj_model, mujoco.mjtObj.mjOBJ_BODY, "red_bottle") >= 0:
            from gear_sonic.utils.mujoco_sim.object_reset import BottlePlacement
            self.bottle_placement = BottlePlacement(self.mj_model, self.mj_data)
            if self.config.get('BOTTLE_XY') is not None:
                self.bottle_placement.reset(self.mj_model, self.mj_data, self.config['BOTTLE_XY'])

    def restore_ground_support(self):
        if self.ground_start and self.elastic_band is not None:
            self.elastic_band.point = self._ground_support_point.copy()
            self.elastic_band.length = 0
            self.elastic_band.enable = True

    def release_ground_support(self):
        if self.ground_start and self.elastic_band is not None:
            self.elastic_band.enable = False
            self.mj_data.xfrc_applied[self.band_attached_link] = 0
            print("[Simulation] Ground support released automatically.", flush=True)

    def init_renderers(self):
        self.renderers = {}
        for camera_name, camera_config in self.camera_configs.items():
            renderer = mujoco.Renderer(
                self.mj_model, height=camera_config["height"], width=camera_config["width"]
            )
            self.renderers[camera_name] = renderer

    def compute_body_torques(self) -> np.ndarray:
        # PD control: tau = tau_ff + kp * (q_des - q) + kd * (dq_des - dq)
        if self.standby:
            addresses = self.mj_model.jnt_qposadr[self.body_joint_index]
            dofs = self.mj_model.jnt_dofadr[self.body_joint_index]
            return (np.asarray(self.robot.MOTOR_KP) * (self.initial_qpos[addresses] - self.mj_data.qpos[addresses])
                    - np.asarray(self.robot.MOTOR_KD) * self.mj_data.qvel[dofs])
        body_torques = np.zeros(self.num_body_dof)
        if self.unitree_bridge is not None and self.unitree_bridge.low_cmd:
            for i in range(self.unitree_bridge.num_body_motor):
                if self.unitree_bridge.use_sensor:
                    body_torques[i] = (
                        self.unitree_bridge.low_cmd.motor_cmd[i].tau
                        + self.unitree_bridge.low_cmd.motor_cmd[i].kp
                        * (self.unitree_bridge.low_cmd.motor_cmd[i].q - self.mj_data.sensordata[i])
                        + self.unitree_bridge.low_cmd.motor_cmd[i].kd
                        * (
                            self.unitree_bridge.low_cmd.motor_cmd[i].dq
                            - self.mj_data.sensordata[i + self.unitree_bridge.num_body_motor]
                        )
                    )
                else:
                    body_torques[i] = (
                        self.unitree_bridge.low_cmd.motor_cmd[i].tau
                        + self.unitree_bridge.low_cmd.motor_cmd[i].kp
                        * (
                            self.unitree_bridge.low_cmd.motor_cmd[i].q
                            - self.mj_data.qpos[self.mj_model.jnt_qposadr[self.body_joint_index[i]]]
                        )
                        + self.unitree_bridge.low_cmd.motor_cmd[i].kd
                        * (
                            self.unitree_bridge.low_cmd.motor_cmd[i].dq
                            - self.mj_data.qvel[self.mj_model.jnt_dofadr[self.body_joint_index[i]]]
                        )
                    )
        if (self.config.get("ARM_GRAVITY_COMPENSATION", False)
                and self.unitree_bridge is not None
                and getattr(self.unitree_bridge, "low_cmd_received", False)):
            # SONIC's C++ deployment sends tau_ff=0. Without feedforward the
            # weak arm PD gains need a large position error to hold gravity.
            # qfrc_bias includes gravity and Coriolis; mj_step already computes
            # it. Compensate arms only; keep body balance and all q/dq targets.
            body_torques[self.arm_motor_indices] += self.mj_data.qfrc_bias[self.arm_dof_addresses]
        return body_torques

    def begin_control_transition(self):
        self._control_transition_started = float(self.mj_data.time)
        self.standby = False

    def hold_initial_robot_pose(self):
        """Lock robot joints/base only while idle; leave objects free to settle."""
        if not self.standby:
            return
        model, data = self.mj_model, self.mj_data
        if not hasattr(self, '_idle_robot_indices'):
            bodies = {self.root_body_id}
            for body in range(self.root_body_id + 1, model.nbody):
                if int(model.body_parentid[body]) in bodies:
                    bodies.add(body)
            positions, velocities = [], []
            for joint in range(model.njnt):
                if int(model.jnt_bodyid[joint]) not in bodies:
                    continue
                kind = int(model.jnt_type[joint])
                nq = 7 if kind == int(mujoco.mjtJoint.mjJNT_FREE) else 4 if kind == int(mujoco.mjtJoint.mjJNT_BALL) else 1
                nv = nq - 1 if nq > 1 else nq
                qa, va = int(model.jnt_qposadr[joint]), int(model.jnt_dofadr[joint])
                positions.extend(range(qa, qa + nq))
                velocities.extend(range(va, va + nv))
            self._idle_robot_indices = np.array(positions), np.array(velocities), list(bodies)
        positions, velocities, bodies = self._idle_robot_indices
        data.qpos[positions] = self.initial_qpos[positions]
        data.qvel[velocities] = 0.
        data.qacc_warmstart[velocities] = 0.
        data.qfrc_applied[velocities] = 0.
        data.xfrc_applied[bodies] = 0.
        mujoco.mj_forward(model, data)

    def blend_startup_torques(self, body, hands):
        started = self._control_transition_started
        if started is None:
            return body, hands
        t = float(np.clip((self.mj_data.time - started) / 2., 0., 1.))
        blend = t*t*(3.-2.*t)
        def hold(joints, kp, kd):
            qa, va = self.mj_model.jnt_qposadr[joints], self.mj_model.jnt_dofadr[joints]
            return (kp * (self.initial_qpos[qa] - self.mj_data.qpos[qa])
                    - kd * self.mj_data.qvel[va] + self.mj_data.qfrc_bias[va])
        body_hold = hold(self.body_joint_index, np.asarray(self.robot.MOTOR_KP), np.asarray(self.robot.MOTOR_KD))
        hand_hold = hold(np.r_[self.left_hand_index, self.right_hand_index], 1.5, .1)
        if t >= 1.:
            self._control_transition_started = None
        return (1.-blend)*body_hold + blend*body, (1.-blend)*hand_hold + blend*hands

    def get_head_pose(self) -> np.ndarray:
        root_pos = self.mj_data.body("torso_link").xpos.copy()
        # Reorder quaternion from MuJoCo [w,x,y,z] to scipy [x,y,z,w]
        root_quat = self.mj_data.body("torso_link").xquat.copy()[[1, 2, 3, 0]]
        head_pos = root_pos + Rotation.from_quat(root_quat).apply(np.array([0.0, 0.0, -0.044]))
        return np.concatenate((head_pos, root_quat))

    def get_root_vel(self) -> np.ndarray:
        return self.mj_data.qvel[:6]

    def compute_hand_torques(self) -> np.ndarray:
        if self.standby:
            indices = np.concatenate((self.left_hand_index, self.right_hand_index))
            addresses = self.mj_model.jnt_qposadr[indices]
            dofs = self.mj_model.jnt_dofadr[indices]
            return 1.5 * (self.initial_qpos[addresses] - self.mj_data.qpos[addresses]) - .1 * self.mj_data.qvel[dofs]
        left_hand_torques = np.zeros(self.num_hand_dof)
        right_hand_torques = np.zeros(self.num_hand_dof)
        if self.unitree_bridge is not None and self.unitree_bridge.low_cmd:
            for i in range(self.unitree_bridge.num_hand_motor):
                left_hand_torques[i] = (
                    self.unitree_bridge.left_hand_cmd.motor_cmd[i].tau
                    + self.unitree_bridge.left_hand_cmd.motor_cmd[i].kp
                    * (
                        self.unitree_bridge.left_hand_cmd.motor_cmd[i].q
                        - self.mj_data.qpos[self.mj_model.jnt_qposadr[self.left_hand_index[i]]]
                    )
                    + self.unitree_bridge.left_hand_cmd.motor_cmd[i].kd
                    * (
                        self.unitree_bridge.left_hand_cmd.motor_cmd[i].dq
                        - self.mj_data.qvel[self.mj_model.jnt_dofadr[self.left_hand_index[i]]]
                    )
                )
                right_hand_torques[i] = (
                    self.unitree_bridge.right_hand_cmd.motor_cmd[i].tau
                    + self.unitree_bridge.right_hand_cmd.motor_cmd[i].kp
                    * (
                        self.unitree_bridge.right_hand_cmd.motor_cmd[i].q
                        - self.mj_data.qpos[self.mj_model.jnt_qposadr[self.right_hand_index[i]]]
                    )
                    + self.unitree_bridge.right_hand_cmd.motor_cmd[i].kd
                    * (
                        self.unitree_bridge.right_hand_cmd.motor_cmd[i].dq
                        - self.mj_data.qvel[self.mj_model.jnt_dofadr[self.right_hand_index[i]]]
                    )
                )
        return np.concatenate((left_hand_torques, right_hand_torques))

    def compute_body_qpos(self) -> np.ndarray:
        body_qpos = np.zeros(self.num_body_dof)
        if self.unitree_bridge is not None and self.unitree_bridge.low_cmd:
            for i in range(self.unitree_bridge.num_body_motor):
                body_qpos[i] = self.unitree_bridge.low_cmd.motor_cmd[i].q
        return body_qpos

    def compute_hand_qpos(self) -> np.ndarray:
        hand_qpos = np.zeros(self.num_hand_dof * 2)
        if self.unitree_bridge is not None and self.unitree_bridge.low_cmd:
            for i in range(self.unitree_bridge.num_hand_motor):
                hand_qpos[i] = self.unitree_bridge.left_hand_cmd.motor_cmd[i].q
                hand_qpos[i + self.num_hand_dof] = self.unitree_bridge.right_hand_cmd.motor_cmd[i].q
        return hand_qpos

    def prepare_obs(self) -> Dict[str, any]:
        obs = {}
        if self.use_floating_root_link:
            obs["floating_base_pose"] = self.mj_data.qpos[:7]
            obs["floating_base_vel"] = self.mj_data.qvel[:6]
            obs["floating_base_acc"] = self.mj_data.qacc[:6]
        else:
            obs["floating_base_pose"] = np.zeros(7)
            obs["floating_base_vel"] = np.zeros(6)
            obs["floating_base_acc"] = np.zeros(6)

        obs["secondary_imu_quat"] = self.mj_data.xquat[self.torso_index]

        pose = np.zeros(13)
        torso_link = self.mj_model.body("torso_link").id
        # mj_objectVelocity returns [ang_vel, lin_vel]; swap to [lin_vel, ang_vel]
        mujoco.mj_objectVelocity(
            self.mj_model, self.mj_data, mujoco.mjtObj.mjOBJ_BODY, torso_link, pose[7:13], 1
        )
        pose[7:10], pose[10:13] = (
            pose[10:13],
            pose[7:10].copy(),
        )
        obs["secondary_imu_vel"] = pose[7:13]

        obs["body_q"] = self.mj_data.qpos[self.mj_model.jnt_qposadr[self.body_joint_index]]
        obs["body_dq"] = self.mj_data.qvel[self.mj_model.jnt_dofadr[self.body_joint_index]]
        obs["body_ddq"] = self.mj_data.qacc[self.mj_model.jnt_dofadr[self.body_joint_index]]
        obs["body_tau_est"] = self.mj_data.actuator_force[self.body_actuator]
        if self.num_hand_dof > 0:
            obs["left_hand_q"] = self.mj_data.qpos[self.mj_model.jnt_qposadr[self.left_hand_index]]
            obs["left_hand_dq"] = self.mj_data.qvel[self.mj_model.jnt_dofadr[self.left_hand_index]]
            obs["left_hand_ddq"] = self.mj_data.qacc[self.mj_model.jnt_dofadr[self.left_hand_index]]
            obs["left_hand_tau_est"] = self.mj_data.actuator_force[self.left_hand_actuator]
            obs["right_hand_q"] = self.mj_data.qpos[self.mj_model.jnt_qposadr[self.right_hand_index]]
            obs["right_hand_dq"] = self.mj_data.qvel[self.mj_model.jnt_dofadr[self.right_hand_index]]
            obs["right_hand_ddq"] = self.mj_data.qacc[self.mj_model.jnt_dofadr[self.right_hand_index]]
            obs["right_hand_tau_est"] = self.mj_data.actuator_force[self.right_hand_actuator]
        obs["time"] = self.mj_data.time
        return obs

    def sim_step(self):
        self.hold_initial_robot_pose()
        # Viewer callbacks run on a different thread; mutate physics only here.
        if self._bottle_reset_requested.is_set():
            self._bottle_reset_requested.clear()
            if self.bottle_placement and self.bottle_placement.reset(self.mj_model, self.mj_data):
                self.scene_changed_at = time.monotonic()
                print("[Simulation] Bottle reset to its initial pose.", flush=True)
            else:
                print("[Simulation] No free bottle found in this scene.", flush=True)
        self.obs = self.prepare_obs()
        self.unitree_bridge.PublishLowState(self.obs)
        if self.unitree_bridge.joystick:
            self.unitree_bridge.PublishWirelessController()
        if self.elastic_band:
            if self.elastic_band.enable and self.use_floating_root_link:
                pose = np.concatenate(
                    [
                        self.mj_data.xpos[self.band_attached_link],
                        self.mj_data.xquat[self.band_attached_link],
                        np.zeros(6),
                    ]
                )
                mujoco.mj_objectVelocity(
                    self.mj_model,
                    self.mj_data,
                    mujoco.mjtObj.mjOBJ_BODY,
                    self.band_attached_link,
                    pose[7:13],
                    0,
                )
                pose[7:10], pose[10:13] = pose[10:13], pose[7:10].copy()
                self.mj_data.xfrc_applied[self.band_attached_link] = self.elastic_band.Advance(pose)
            else:
                self.mj_data.xfrc_applied[self.band_attached_link] = np.zeros(6)
        body_torques = self.compute_body_torques()
        hand_torques = self.compute_hand_torques()
        body_torques, hand_torques = self.blend_startup_torques(body_torques, hand_torques)
        if self.config.get('FIXED_PICKUP_BASE', False) and not self.standby:
            # Explicit stationary manipulation mode: model inference remains
            # observable, while only the RGB-D waist/right-arm correction moves
            # robot joints. The bottle has no constraint or external force.
            qa = self.mj_model.jnt_qposadr[self.body_joint_index]
            va = self.mj_model.jnt_dofadr[self.body_joint_index]
            body_torques = 100. * (self.initial_qpos[qa] - self.mj_data.qpos[qa]) - 4. * self.mj_data.qvel[va] + self.mj_data.qfrc_bias[va]
            joints = np.r_[self.left_hand_index, self.right_hand_index]
            qa, va = self.mj_model.jnt_qposadr[joints], self.mj_model.jnt_dofadr[joints]
            hand_torques = 8. * (self.initial_qpos[qa] - self.mj_data.qpos[qa]) - .2 * self.mj_data.qvel[va] + self.mj_data.qfrc_bias[va]
        if self.assisted_pickup is not None and not self.standby:
            self.assisted_pickup.apply_torques(self.mj_data, body_torques, hand_torques, self.body_joint_index)
        # Map active joints to motor slots; passive Inspire joints have no slot.
        self.torques[self.body_actuator - (6 if self.config["FREE_BASE"] else 0)] = body_torques
        if self.num_hand_dof > 0:
            self.torques[self.left_hand_actuator - (6 if self.config["FREE_BASE"] else 0)] = hand_torques[: self.num_hand_dof]
            self.torques[self.right_hand_actuator - (6 if self.config["FREE_BASE"] else 0)] = hand_torques[self.num_hand_dof :]

        self.torques = np.clip(self.torques, -self.torque_limit, self.torque_limit)

        if self.config["FREE_BASE"]:
            # Prepend 6 zeros for the floating-base root DOF actuators
            self.mj_data.ctrl = np.concatenate((np.zeros(6), self.torques))
        else:
            self.mj_data.ctrl = self.torques
        if self.config.get('RECORD_DIR'):
            from gear_sonic.utils.mujoco_sim.episode_recorder import EpisodeRecorder
            if not hasattr(self, 'episode_recorder'):
                self.episode_recorder = EpisodeRecorder(self.mj_model, self.config['RECORD_DIR'],
                    self.config['RECORD_PROMPT'], self.config['RECORD_FPS'])
            self.episode_recorder.capture(self.mj_data, not self.standby,
                getattr(self, 'scene_changed_at', None), self.assisted_pickup)
        mujoco.mj_step(self.mj_model, self.mj_data)
        self.hold_initial_robot_pose()

        self.check_fall()
        if self.reach_diagnostic_writer and time.monotonic() - getattr(self, "_last_reach_diagnostic", 0) > 0.1:
            from gear_sonic.utils.mujoco_sim.reach_diagnostics import measure_reach
            targets = {}
            with self.unitree_bridge.low_cmd_lock:
                if self.unitree_bridge.low_cmd_received:
                    for i, jid in enumerate(self.body_joint_index):
                        targets[int(jid)] = self.unitree_bridge.low_cmd.motor_cmd[i].q
            for indices, cmd, lock, received in (
                (self.left_hand_index, self.unitree_bridge.left_hand_cmd,
                 self.unitree_bridge.left_hand_cmd_lock, self.unitree_bridge.left_hand_cmd_received),
                (self.right_hand_index, self.unitree_bridge.right_hand_cmd,
                 self.unitree_bridge.right_hand_cmd_lock, self.unitree_bridge.right_hand_cmd_received),
            ):
                with lock:
                    if received:
                        for i, jid in enumerate(indices):
                            targets[int(jid)] = cmd.motor_cmd[i].q
            report = measure_reach(self.mj_model, self.mj_data, targets)
            report["wall_time_unix_s"] = time.time()
            report["monotonic_s"] = time.monotonic()
            report["elastic_band_enabled"] = bool(self.elastic_band and self.elastic_band.enable)
            report["arm_gravity_compensation"] = self.config.get("ARM_GRAVITY_COMPENSATION", False)
            report["assisted_pickup"] = self.assisted_pickup.snapshot() if self.assisted_pickup else None
            report['fixed_pickup_base'] = self.config.get('FIXED_PICKUP_BASE', False)
            report["proximity_grasp"] = {key: self.ui_snapshot.get(key) for key in
                ("grasp_threshold_m", "grasp_x_tolerance_m", "grasp_latched", "bottle_seen", "grasp_status", "policy_action", "phase")}
            self.reach_diagnostic_writer.submit(report)
            self._last_reach_diagnostic = time.monotonic()

    def apply_perturbation(self, key):
        perturbation_x_body = 0.0
        perturbation_y_body = 0.0
        if key == "up":
            perturbation_x_body = 1.0
        elif key == "down":
            perturbation_x_body = -1.0
        elif key == "left":
            perturbation_y_body = 1.0
        elif key == "right":
            perturbation_y_body = -1.0

        vel_body = np.array([perturbation_x_body, perturbation_y_body, 0.0])
        vel_world = np.zeros(3)
        base_quat = self.mj_data.qpos[3:7]
        mujoco.mju_rotVecQuat(vel_world, vel_body, base_quat)

        self.mj_data.qvel[0] += vel_world[0]
        self.mj_data.qvel[1] += vel_world[1]
        mujoco.mj_forward(self.mj_model, self.mj_data)

    def update_viewer(self):
        if self.viewer is not None:
            snapshot = self.coordinate_snapshot()
            labels, values = ["WORLD XYZ (m)"], ["X       Y       Z"]
            for label, key in (("Bottle centre", "bottle"), ("Hand grasp centre (green)", "right_grasp_center"),
                               ("Right wrist origin", "right_wrist"), ("Left wrist origin", "left_wrist")):
                if snapshot.get(key) is not None:
                    labels.append(label)
                    values.append("  ".join(f"{v:+.3f}" for v in snapshot[key]))
            target = self.ui_snapshot.get("right_wrist_target")
            if target is not None:
                labels.extend(["SONIC wrist command (FK)", "Wrist tracking error"])
                values.extend(["  ".join(f"{v:+.3f}" for v in target),
                               f"{self.ui_snapshot['wrist_tracking_error_m'] * 100:.1f} cm"])
            grasp_target = self.ui_snapshot.get("right_grasp_target")
            if grasp_target is not None:
                labels.extend(["SONIC grasp centre (FK)", "Grasp tracking error"])
                values.extend(["  ".join(f"{v:+.3f}" for v in grasp_target),
                               f"{self.ui_snapshot['grasp_tracking_error_m'] * 100:.1f} cm"])
            policy_action = self.ui_snapshot.get("policy_action", {})
            alignment = self.ui_snapshot.get("hand_alignment", {})
            grasp = alignment.get("grasp_center_world_m")
            gap = alignment.get("y_surface_gap_m")
            gap_text = f"{gap * 100:.2f} cm" if gap is not None else "-- (outside profile)"
            x_error = alignment.get("x_error_m")
            if grasp is not None:
                labels.extend(["Grasp centre (fixed in hand)", "X error (grasp - bottle)", "Y gap to bottle surface", "Hand closure"])
                values.extend(["  ".join(f"{v:+.3f}" for v in grasp),
                               f"{x_error * 100:+.2f} cm", gap_text + " (MuJoCo)", self.ui_snapshot.get("grasp_status", "")])
            grip = policy_action.get("right_grip")
            labels.extend(["GR00T right grip", "GR00T actions sent"])
            values.extend([f"{grip * 100:.1f}%" if grip is not None else "--",
                           str(self.ui_snapshot.get("actions_published", 0))])
            detection = self.ui_snapshot.get("detection", {})
            point = detection.get("world_point_m")
            labels.extend(["Detector surface XYZ", "YOLO bottle confidence", "GR00T detected XYZ", "Run state", "Ground support", "Controls"])
            values.extend(["  ".join(f"{v:+.3f}" for v in point) if point is not None else detection.get("status", "disabled"),
                           f"{detection['confidence']:.2f}" if "confidence" in detection else "--",
                           "Unavailable in checkpoint output", self.ui_snapshot.get("phase", "keyboard"),
                           "ON (standby)" if self.elastic_band and self.elastic_band.enable else "OFF",
                           "F2 panel | R bottle reset | F5 robot reset | F6 start"])
            labels.append("Arm gravity compensation")
            values.append("ON" if self.config.get("ARM_GRAVITY_COMPENSATION", False) else "OFF")
            assisted = self.ui_snapshot.get('assisted_pickup')
            if assisted:
                labels.extend(['Assisted pickup (RGB-D + IK)', 'Visual bottle centre target'])
                target = assisted.get('target_center_world_m')
                values.extend([assisted['stage'], '  '.join(f'{v:+.3f}' for v in target) if target else '--'])
                labels.append('Pelvis / body mode')
                values.append('FIXED (simulation fixture)' if self.config.get('FIXED_PICKUP_BASE', False) else 'Free / SONIC')
                error = assisted.get('position_error_m')
                labels.append('Assisted arm target error')
                values.append(f'{error * 100:.2f} cm' if error is not None else '--')
            # set_texts forwards its font argument directly to mjr_overlay:
            # valid values are mjtFont (0..2), NOT mjtFontScale (50..300).
            # A scale value indexes native font tables outside their bounds.
            detector_text = (f"X {point[0]:+.3f}    Y {point[1]:+.3f}    Z {point[2]:+.3f} m"
                             if point is not None else detection.get("status", "disabled"))
            confidence_text = f"Confidence {detection['confidence']:.2f}" if "confidence" in detection else ""
            texts = [(mujoco.mjtFont.mjFONT_SHADOW,
                                   mujoco.mjtGridPos.mjGRID_TOPLEFT,
                                   "\n".join(labels), "\n".join(values)),
                                  (mujoco.mjtFont.mjFONT_BIG, mujoco.mjtGridPos.mjGRID_BOTTOMLEFT,
                                   "DETECTED BOTTLE - YOLO (RGB + DEPTH)\n" + detector_text
                                   + "\n" + confidence_text, "")]
            if assisted:
                texts.append((mujoco.mjtFont.mjFONT_BIG, mujoco.mjtGridPos.mjGRID_BOTTOMRIGHT,
                    'ASSISTED PICKUP - RGB-D + IK\n' + assisted['stage'] + '\n' + assisted.get('error', ''), ''))
            if self.ui_snapshot.get("grasp_threshold_m") and grasp is not None:
                texts.append((mujoco.mjtFont.mjFONT_BIG, mujoco.mjtGridPos.mjGRID_BOTTOMRIGHT,
                    f"GRASP CENTRE - X/Y\nX error {x_error * 100:+.2f} cm | tol {self.ui_snapshot.get('grasp_x_tolerance_m', .005) * 100:.1f}\n"
                    f"Y gap {gap_text} | target {self.ui_snapshot['grasp_threshold_m'] * 100:.1f}\n"
                    + self.ui_snapshot.get("grasp_status", ""), ""))
            if self._viewer_overlay_worker is not None:
                self._viewer_overlay_worker.submit(texts, detection)
            else:
                self.viewer.set_texts(texts)
            self.viewer.sync()

    def coordinate_snapshot(self):
        result = {}
        site = mujoco.mj_name2id(self.mj_model, mujoco.mjtObj.mjOBJ_SITE, "right_hand_grasp_center")
        if site >= 0:
            result["right_grasp_center"] = self.mj_data.site_xpos[site].tolist()
        for key, name in (("bottle", "red_bottle"), ("right_wrist", "right_wrist_yaw_link"),
                          ("left_wrist", "left_wrist_yaw_link")):
            body = mujoco.mj_name2id(self.mj_model, mujoco.mjtObj.mjOBJ_BODY, name)
            if body >= 0:
                result[key] = self.mj_data.xpos[body].tolist()
        return result

    def command_coordinate_snapshot(self):
        """FK of SONIC joint commands at the current base; display only."""
        if self.config.get('FIXED_PICKUP_BASE', False):
            # These proposed SONIC targets are not executed by the fixed-base
            # fixture. Displaying their tracking error would be misleading.
            return {}
        bridge = self.unitree_bridge
        if self.standby or bridge is None or not getattr(bridge, "low_cmd_received", False):
            return {}
        if not hasattr(self, "_command_fk"):
            self._command_fk = mujoco.MjData(self.mj_model)
        target = self._command_fk
        target.qpos[:] = self.mj_data.qpos
        with bridge.low_cmd_lock:
            for i, joint in enumerate(self.body_joint_index):
                target.qpos[self.mj_model.jnt_qposadr[joint]] = bridge.low_cmd.motor_cmd[i].q
        mujoco.mj_forward(self.mj_model, target)
        wrist = self.mj_model.body("right_wrist_yaw_link").id
        commanded = target.xpos[wrist].copy()
        result = {"right_wrist_target": commanded.tolist(),
                  "wrist_tracking_error_m": float(np.linalg.norm(commanded - self.mj_data.xpos[wrist]))}
        site = mujoco.mj_name2id(self.mj_model, mujoco.mjtObj.mjOBJ_SITE, "right_hand_grasp_center")
        if site >= 0:
            result.update(right_grasp_target=target.site_xpos[site].tolist(),
                          grasp_tracking_error_m=float(np.linalg.norm(target.site_xpos[site] - self.mj_data.site_xpos[site])))
        return result

    def update_viewer_camera(self):
        if self.viewer is not None:
            if self.viewer.cam.type == mujoco.mjtCamera.mjCAMERA_TRACKING:
                self.viewer.cam.type = mujoco.mjtCamera.mjCAMERA_FREE
            else:
                self.viewer.cam.type = mujoco.mjtCamera.mjCAMERA_TRACKING

    def update_reward(self):
        with self.reward_lock:
            self.last_reward = 0

    def get_reward(self):
        with self.reward_lock:
            return self.last_reward

    def set_unitree_bridge(self, unitree_bridge):
        self.unitree_bridge = unitree_bridge

    def get_privileged_obs(self):
        return {}

    def update_render_caches(self):
        if self.async_image_render:
            if self.image_publish_process is not None:
                # Pair proprioception with the image exposure, not with the
                # later time at which rendering/network delivery completes.
                state = {
                    "body_q": self.mj_data.qpos[self.mj_model.jnt_qposadr[self.body_joint_index]].tolist(),
                    "left_hand_q": self.mj_data.qpos[self.mj_model.jnt_qposadr[self.left_hand_index]].tolist(),
                    "right_hand_q": self.mj_data.qpos[self.mj_model.jnt_qposadr[self.right_hand_index]].tolist(),
                    "base_quat": self.mj_data.qpos[3:7].tolist(),
                }
                if self.native_inspire:
                    state['hand_state_format'] = 'inspire_ftp_motor_radians'
                self.image_publish_process.submit(self.mj_data, robot_state=state)
            return {}
        render_caches = {}
        for camera_name, camera_config in self.camera_configs.items():
            renderer = self.renderers[camera_name]
            if "params" in camera_config:
                renderer.update_scene(self.mj_data, camera=camera_config["params"])
            elif "mjcf_name" in camera_config:
                renderer.update_scene(self.mj_data, camera=camera_config["mjcf_name"])
            else:
                renderer.update_scene(self.mj_data, camera=camera_name)
            render_caches[camera_name + "_image"] = renderer.render()

        if self.image_publish_process is not None:
            self.image_publish_process.update_shared_memory(render_caches)

        return render_caches

    def _viewer_key_callback(self, key):
        # GLFW F2 / F5 / F6; commands are processed on the physics thread.
        if key in (291, 294, 295):
            self.ui_commands.put({"command": {291: "open_panel", 294: "reset", 295: "start"}[key]})
            return
        if key == ord("R"):
            self._bottle_reset_requested.set()
        elif self.elastic_band:
            self.elastic_band.MujuocoKeyCallback(key)

    def handle_keyboard_button(self, key):
        if self.elastic_band:
            self.elastic_band.handle_keyboard_button(key)

        if key == "backspace":
            self.reset()
        if key.lower() == "r":
            self._bottle_reset_requested.set()
        if key == "v":
            self.update_viewer_camera()
        if key in ["up", "down", "left", "right"]:
            self.apply_perturbation(key)

    def check_fall(self):
        self.fall = False
        if self.mj_data.qpos[2] < 0.2:
            self.fall = True
            print(f"Warning: Robot has fallen, height: {self.mj_data.qpos[2]:.3f} m")

        if self.fall:
            if self.config.get("SIM_CONTROLS", False):
                self.ui_commands.put({"command": "reset"})
                # Hold the reset pose while awaiting the policy pause acknowledgement.
                self.reset()
            else:
                self.reset()

    def check_self_collision(self):
        robot_bodies = get_subtree_body_names(self.mj_model, self.mj_model.body(self.root_body).id)
        self_collision, contact_bodies = check_contact(
            self.mj_model, self.mj_data, robot_bodies, robot_bodies, return_all_contact_bodies=True
        )
        if self_collision:
            print(f"Warning: Self-collision detected: {contact_bodies}")
        return self_collision

    def reset(self):
        if getattr(self, 'episode_recorder', None) is not None:
            self.episode_recorder.finish('robot_reset')
        self._control_transition_started = None
        if getattr(self, 'assisted_pickup', None) is not None:
            self.assisted_pickup.reset()
        mujoco.mj_resetData(self.mj_model, self.mj_data)
        self.mj_data.qpos[:] = self.initial_qpos
        self.standby = self.ground_start
        self.restore_ground_support()
        mujoco.mj_forward(self.mj_model, self.mj_data)
        if self.bottle_placement:
            self.bottle_placement.reset(self.mj_model, self.mj_data)
        self.scene_changed_at = time.monotonic()


class BaseSimulator:
    """Base simulator class that handles initialization and running of simulations"""

    def __init__(
        self, config: Dict[str, any], env_name: str = "default", redis_client=None, **kwargs
    ):
        self.config = config
        self.env_name = env_name
        self.redis_client = redis_client
        if self.redis_client is not None:
            self.redis_client.set("push_left_hand", "false")
            self.redis_client.set("push_right_hand", "false")
            self.redis_client.set("push_torso", "false")

        # Create rate objects
        self.sim_dt = self.config["SIMULATE_DT"]
        self.reward_dt = self.config.get("REWARD_DT", 0.02)
        self.image_dt = self.config.get("IMAGE_DT", 0.033333)
        self.viewer_dt = self.config.get("VIEWER_DT", 0.02)
        self._running = True

        self.robot = Robot(self.config)

        # Create the environment
        if env_name == "default":
            self.sim_env = DefaultEnv(config, env_name, **kwargs)
        else:
            raise ValueError(
                f"Invalid environment name: {env_name}. "
                f"Only 'default' is supported in this minimal build."
            )

        try:
            if self.config.get("INTERFACE", None):
                ChannelFactoryInitialize(self.config["DOMAIN_ID"], self.config["INTERFACE"])
            else:
                ChannelFactoryInitialize(self.config["DOMAIN_ID"])
        except Exception as e:
            print(f"Note: Channel factory initialization attempt: {e}")

        self.init_unitree_bridge()
        self.sim_env.set_unitree_bridge(self.unitree_bridge)

        self.init_subscriber()
        self.init_publisher()

        self.interactive_controls = None
        if self.config.get("SIM_CONTROLS", False):
            from gear_sonic.utils.mujoco_sim.interactive_controls import InteractiveSimulationControls
            self.interactive_controls = InteractiveSimulationControls(
                self.sim_env, port=self.config.get("SIM_CONTROL_PORT", 5581))

        self.sim_thread = None

    def start_as_thread(self):
        self.sim_thread = Thread(target=self.start)
        self.sim_thread.start()

    def start_image_publish_subprocess(self, start_method: str = "spawn", camera_port: int = 5555):
        self.sim_env.start_image_publish_subprocess(start_method, camera_port)

    def init_subscriber(self):
        self.keyboard_subscriber = None
        if self.config.get("SIM_KEYBOARD_ZMQ_PORT"):
            from gear_sonic.utils.data_collection.keyboard_subscriber import ZMQKeyboardSubscriber
            self.keyboard_subscriber = ZMQKeyboardSubscriber(port=self.config["SIM_KEYBOARD_ZMQ_PORT"])

    def init_publisher(self):
        pass

    def init_unitree_bridge(self):
        self.unitree_bridge = UnitreeSdk2Bridge(self.config)
        if self.config["USE_JOYSTICK"]:
            self.unitree_bridge.SetupJoystick(
                device_id=self.config["JOYSTICK_DEVICE"], js_type=self.config["JOYSTICK_TYPE"]
            )

    def start(self):
        """Main simulation loop"""
        sim_cnt = 0
        ts = time.time()
        next_step = time.monotonic()

        try:
            while self._running and (
                (self.sim_env.viewer and self.sim_env.viewer.is_running())
                or (self.sim_env.viewer is None)
            ):
                if self.keyboard_subscriber is not None:
                    key = self.keyboard_subscriber.read_msg()
                    if key in ("r", "R", "9"):
                        self.sim_env.handle_keyboard_button(key.lower())
                    elif key in ("k", "i", "p") and self.interactive_controls is not None:
                        self.interactive_controls.handle_keyboard(key)

                if self.interactive_controls is not None:
                    self.interactive_controls.poll()

                self.sim_env.sim_step()
                now = time.time()
                if now - ts > 1 / 10.0 and self.redis_client is not None:
                    head_pose = self.sim_env.get_head_pose()
                    self.redis_client.set("head_pos", pickle.dumps(head_pose[:3]))
                    self.redis_client.set("head_quat", pickle.dumps(head_pose[3:]))
                    ts = now

                if sim_cnt % int(self.viewer_dt / self.sim_dt) == 0:
                    self.sim_env.update_viewer()

                if sim_cnt % int(self.reward_dt / self.sim_dt) == 0:
                    self.sim_env.update_reward()

                if sim_cnt % int(self.image_dt / self.sim_dt) == 0:
                    self.sim_env.update_render_caches()

                # Absolute deadlines avoid accumulating sleep/scheduling jitter.
                # Bound catch-up after a long stall (e.g. moving the viewer).
                next_step += self.sim_dt
                now_monotonic = time.monotonic()
                if now_monotonic - next_step > 0.1:
                    next_step = now_monotonic
                sleep_time = next_step - now_monotonic
                if sleep_time > 0:
                    time.sleep(sleep_time)

                sim_cnt += 1
        except KeyboardInterrupt:
            print("Simulator interrupted by user.")
        finally:
            self.close()

    def __del__(self):
        self.close()

    def reset(self):
        self.sim_env.reset()

    def close(self):
        self._running = False
        try:
            if getattr(self.sim_env, 'episode_recorder', None) is not None:
                self.sim_env.episode_recorder.close()
            if getattr(self, "interactive_controls", None) is not None:
                self.interactive_controls.close()
                self.interactive_controls = None
            if getattr(self, "keyboard_subscriber", None) is not None:
                self.keyboard_subscriber.close()
                self.keyboard_subscriber = None
            if getattr(self.sim_env, "reach_diagnostic_writer", None) is not None:
                self.sim_env.reach_diagnostic_writer.close()
            if self.sim_env.image_publish_process is not None:
                self.sim_env.image_publish_process.stop()
            if self.sim_env.viewer is not None:
                if self.sim_env._viewer_overlay_worker is not None:
                    self.sim_env._viewer_overlay_worker.close()
                self.sim_env.viewer.close()
        except Exception as e:
            print(f"Warning during close: {e}")

    def get_privileged_obs(self):
        return self.sim_env.get_privileged_obs()

    def handle_keyboard_button(self, key):
        self.sim_env.handle_keyboard_button(key)
