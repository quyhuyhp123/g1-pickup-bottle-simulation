"""
VLA inference runner — NO ROS 2 DEPENDENCY.

Runs an Isaac-GR00T VLA policy against the Sonic whole-body control stack.
All communication uses ZMQ:
  1. Robot state  -> ZMQ SUB on ``g1_debug`` topic (from C++ zmq_output_handler)
  2. Actions out  -> ZMQ PUB (latent protocol v4: motion token + hand joints)
  3. Camera       -> ZMQ/TCP via ComposedCameraClientSensor
  4. Keyboard     -> ZMQ SUB via ZMQKeyboardSubscriber

Uses the Isaac-GR00T PolicyClient (ZMQ REQ/REP) to communicate with a
running PolicyServer.

Keyboard commands (received via ZMQ from the standalone keyboard publisher):
  p  -> pause / resume the policy loop
  k  -> start / stop the C++ control loop
  i  -> blend smoothly to initial pose (or snap if no prior token) and switch to POSE mode
  t  -> change prompt at runtime (publisher sends ``prompt:<text>``)
  [  -> toggle left hand open/closed for initial pose
  ]  -> toggle right hand open/closed for initial pose
  c  -> start recording (handled by data exporter if running)
  s  -> stop recording success (handled by data exporter)
  f  -> stop recording failure (handled by data exporter)
"""

from dataclasses import dataclass
import queue
import threading
import time

import numpy as np
import tyro
import zmq

from gear_sonic.camera.composed_camera import ComposedCameraClientSensor
from gear_sonic.data.robot_model.instantiation.g1 import instantiate_g1_robot_model
from gear_sonic.utils.data_collection.keyboard_subscriber import (
    DEFAULT_ZMQ_KEYBOARD_PORT,
    ZMQKeyboardSubscriber,
)
from gear_sonic.utils.data_collection.telemetry import Telemetry
from gear_sonic.utils.data_collection.transforms import compute_projected_gravity
from gear_sonic.utils.data_collection.zmq_state_subscriber import ZMQStateSubscriber
from gear_sonic.utils.diagnostic_writer import DiagnosticWriter
from gear_sonic.utils.inference.initial_poses import LATENT_INITIAL_MOTION_TOKEN
from gear_sonic.utils.inference.vla_utils import (
    calculate_latency_compensated_index,
    concat_action,
    prepare_observation_for_eval,
    should_trigger_new_inference,
)
from gear_sonic.utils.teleop.solver.hand.g1_gripper_ik_solver import (
    G1GripperInverseKinematicsSolver,
)
from gear_sonic.utils.teleop.zmq.zmq_planner_sender import (
    build_command_message,
    pack_pose_message,
)


@dataclass
class InferenceConfig:
    """CLI config for the VLA inference runner."""

    # Policy server (Isaac-GR00T PolicyServer)
    host: str = "localhost"
    """The host address of the Isaac-GR00T PolicyServer."""

    port: int = 5550
    """The port of the Isaac-GR00T PolicyServer."""

    action_diagnostic_path: str = ""
    """Optional JSONL recording of raw policy chunks and published actions."""

    sim_control_port: int = 0
    """Enable simulation reset/start/status channel; 0 disables it for hardware."""

    sim_policy_control: bool = False
    """Strict GR00T-to-SONIC simulation profile; body tokens are forwarded unchanged."""

    sim_grasp_distance: float = 0.
    """Optional right-hand closure at grasp-region centre X alignment and Y surface gap (m)."""

    sim_grasp_x_tolerance: float = .005
    """Maximum X error between grasp-region centre and bottle centre (m)."""

    # Control
    action_publish_rate: int = 50
    """Rate at which individual actions are published to the C++ control loop (Hz)."""

    action_horizon: int = 40
    """Action horizon of the VLA policy (number of future actions per inference)."""

    rate: float = 1 / 0.4
    """Rate at which we run the forward pass of the VLA policy (Hz)."""

    # Camera
    camera_host: str = "localhost"
    """Camera server host."""

    camera_port: int = 5555
    """Camera server port."""

    # ZMQ: Robot state (from C++ zmq_output_handler, g1_debug topic)
    state_zmq_host: str = "localhost"
    """ZMQ host for robot state (g1_debug topic from C++ deploy)."""

    state_zmq_port: int = 5557
    """ZMQ port for robot state (same socket as robot_config topic)."""

    # ZMQ: Action output (latent actions to C++ control loop)
    action_zmq_host: str = "localhost"
    """ZMQ host for action output (PUB socket)."""

    action_zmq_port: int = 5556
    """ZMQ port for action output."""

    # ZMQ: Keyboard input
    keyboard_zmq_host: str = "localhost"
    """ZMQ host for keyboard input."""

    keyboard_zmq_port: int = DEFAULT_ZMQ_KEYBOARD_PORT
    """ZMQ port for keyboard input."""

    # Embodiment
    embodiment_tag: str = "unitree_g1_sonic"
    """Embodiment tag for policy inference."""

    # Prompt / eval
    prompt: str = "demo"
    """The language prompt for the VLA policy."""

    inspire_ftp_hands: bool = False
    """Experimental simulation adapter for CloudWalk Inspire FTP checkpoints.
    Maps grip levels to Dex3 poses and uses zero hand observations as in training."""

    sim_stationary_body: bool = False
    """Simulation assisted pickup: hold SONIC's standing token while the RGB-D controller corrects waist/right arm."""

    # Initial pose
    initial_pose_blend_duration: float = 1.0
    """Duration (seconds) for smooth interpolation to initial pose. The robot
    blends from its current motion token to the initial pose token over this
    period. Set to 0 to snap instantly (no blend)."""

    # Debug
    verbose_timing: bool = False
    """Whether to always print timing info (not just when loop is slow)."""


def print_green(x):
    print(f"\033[92m{x}\033[0m")


# ---------------------------------------------------------------------------
# Action packing (latent protocol v4)
# ---------------------------------------------------------------------------


def pack_latent_action_message(
    motion_token: np.ndarray,
    frame_index: np.ndarray,
    left_hand_joints: np.ndarray = None,
    right_hand_joints: np.ndarray = None,
) -> bytes:
    """Pack a single motion-token action into a ZMQ message (Protocol v4).

    Args:
        motion_token: Shape ``[64]`` (flat) or ``[1, 64]``.
        frame_index:  Shape ``[1]``.
        left_hand_joints:  Shape ``[7]`` or ``[1, 7]``, optional.
        right_hand_joints: Shape ``[7]`` or ``[1, 7]``, optional.

    Returns:
        Packed ZMQ message bytes.
    """
    motion_token = np.asarray(motion_token, dtype=np.float32)
    frame_index = np.asarray(frame_index, dtype=np.int64)

    if frame_index.ndim == 0:
        frame_index = np.array([frame_index], dtype=np.int64)
    elif frame_index.shape[0] != 1:
        frame_index = frame_index[:1]

    if motion_token.ndim == 1:
        motion_token = motion_token.reshape(1, -1)

    pose_data = {
        "token_state": motion_token,
        "frame_index": frame_index,
    }

    if left_hand_joints is not None:
        left_hand_joints = np.asarray(left_hand_joints, dtype=np.float32)
        if left_hand_joints.ndim == 1:
            if left_hand_joints.shape[0] != 7:
                raise ValueError(
                    f"left_hand_joints must have shape [7], got {left_hand_joints.shape}"
                )
            left_hand_joints = left_hand_joints.reshape(1, 7)
        pose_data["left_hand_joints"] = left_hand_joints

    if right_hand_joints is not None:
        right_hand_joints = np.asarray(right_hand_joints, dtype=np.float32)
        if right_hand_joints.ndim == 1:
            if right_hand_joints.shape[0] != 7:
                raise ValueError(
                    f"right_hand_joints must have shape [7], got {right_hand_joints.shape}"
                )
            right_hand_joints = right_hand_joints.reshape(1, 7)
        pose_data["right_hand_joints"] = right_hand_joints

    return pack_pose_message(pose_data, topic="pose", version=4)


def get_action_field(action_dict: dict, key: str):
    """Get action field from dict, checking both with and without 'action.' prefix."""
    value = action_dict.get(key)
    if value is not None:
        return value
    value = action_dict.get(f"action.{key}")
    if value is not None:
        return value
    raise AssertionError(
        f"Required action field '{key}' (or 'action.{key}') not found in processed_action. "
        f"Available keys: {list(action_dict.keys())}"
    )


# ---------------------------------------------------------------------------
# Observation / inference helpers
# ---------------------------------------------------------------------------


def prepare_observation_from_sensors(
    camera_subscriber,
    state_subscriber,
    robot_model,
    language_prompt: str,
    log_errors: bool = False,
    minimum_capture_monotonic: float | None = None,
    sensor_status: dict | None = None,
):
    """Read sensors and prepare observation for the VLA policy.

    Returns:
        observation dict, or None if sensor data not yet available.
    """
    camera_msg = camera_subscriber.read()
    if camera_msg is None:
        if log_errors:
            print("[DEBUG] prepare_observation: waiting for camera msg..", flush=True)
        return None

    if minimum_capture_monotonic is not None:
        captured = camera_msg.get("capture_monotonic", 0.)
        age = time.monotonic() - captured
        if captured < minimum_capture_monotonic or not 0 <= age < 1.:
            if sensor_status is not None:
                sensor_status.update(input_ready=False, error="Waiting for a fresh post-start camera frame")
            return None
        if sensor_status is not None:
            sensor_status.update(input_ready=True, camera_capture_monotonic=captured, error="")

    state_msg = camera_msg.get("robot_state")
    if state_msg is None:
        state_msg = state_subscriber.get_msg()
    if state_msg is None:
        if log_errors:
            print("[DEBUG] prepare_observation: waiting for state msg..", flush=True)
        return None

    state_msg = dict(state_msg)
    hand_format = state_msg.pop('hand_state_format', 'dex3_joint_radians')
    if hand_format == 'inspire_ftp_motor_radians':
        from gear_sonic.utils.mujoco_sim.inspire_hand import dex3_observation_from_inspire
        for side in ('left', 'right'):
            state_msg[side+'_hand_q'] = dex3_observation_from_inspire(state_msg[side+'_hand_q'], side)
    elif hand_format != 'dex3_joint_radians':
        raise ValueError(f'Unsupported hand observation format: {hand_format}')
    state_msg = {key: np.asarray(value).copy() for key, value in state_msg.items()}

    cam_img = camera_msg["images"]["ego_view"]

    # Copy index finger data to middle finger (hardware coupling)
    state_msg["left_hand_q"][5] = state_msg["left_hand_q"][3]
    state_msg["left_hand_q"][6] = state_msg["left_hand_q"][4]

    qpos = robot_model.get_configuration_from_actuated_joints(
        body_actuated_joint_values=state_msg["body_q"],
        left_hand_actuated_joint_values=state_msg["left_hand_q"],
        right_hand_actuated_joint_values=state_msg["right_hand_q"],
    )

    video = {"ego_view": cam_img[np.newaxis, np.newaxis]}
    if "left_wrist" in camera_msg["images"]:
        video["left_wrist"] = camera_msg["images"]["left_wrist"][np.newaxis, np.newaxis]
    if "right_wrist" in camera_msg["images"]:
        video["wrist_view"] = camera_msg["images"]["right_wrist"][np.newaxis, np.newaxis]

    observation = {
        "video": video,
        "state": {},
        "language": {
            "annotation.human.task_description": [[language_prompt]],
        },
        "q": np.asarray(qpos, dtype=np.float32)[np.newaxis, np.newaxis],
        "timestamps": camera_msg["timestamps"]["ego_view"],
    }

    observation = prepare_observation_for_eval(robot_model, observation)
    # Local scheduling metadata only; never send this field to the policy.
    # Only paired simulation frames share this process's monotonic clock.
    if minimum_capture_monotonic is not None and camera_msg.get('robot_state') is not None:
        observation['_capture_monotonic'] = camera_msg['capture_monotonic']

    # Projected gravity for Sonic latent embodiment
    assert "base_quat" in state_msg, "base_quat not found in state_msg"
    base_quat = np.asarray(state_msg["base_quat"], dtype=np.float64)
    assert base_quat.shape == (4,), "base_quat must have shape (4,)"
    projected_gravity = compute_projected_gravity(base_quat)
    observation["state"]["projected_gravity"] = np.asarray(
        projected_gravity, dtype=np.float32
    )[np.newaxis, np.newaxis]

    return observation


def run_policy_inference_and_process(policy, observation, robot_model):
    """Run policy inference via Isaac-GR00T PolicyClient and process results.

    Returns:
        processed_action dict or None on error.
    """
    try:
        action, _info = policy.get_action(observation)

        action.pop("task_progress", None)
        action.pop("action.task_progress", None)

        motion_key = "motion_token" if "motion_token" in action else "action.motion_token"
        if np.abs(action[motion_key]).max() > 1.25:
            print(
                f"[Warning] action['{motion_key}'] max "
                f"({np.abs(action[motion_key]).max():.4f}) > 1.25. "
                "Exceeds action bound, skipping."
            )
            return None

        processed_action = concat_action(robot_model, action)
        return processed_action
    except Exception as e:
        print(f"Error in inference: {e}")
        import traceback

        traceback.print_exc()
        return None


def _inference_worker_loop(
    inference_queue: queue.Queue,
    result_queue: queue.Queue,
    stop_event: threading.Event,
    busy_event: threading.Event,
    prepare_obs_fn,
    inference_fn,
):
    """Persistent worker thread for async inference."""
    while not stop_event.is_set():
        try:
            try:
                requested_at = inference_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            busy_event.set()
            try:
                observation = prepare_obs_fn()
                if observation is None:
                    print("[DEBUG] Worker thread: Observation is None, skipping", flush=True)
                    continue

                # Keep the request boundary, so an in-flight result from before
                # Reset cannot be accepted even if observation preparation ended later.
                inference_start_time = requested_at
                observation_at = observation.pop('_capture_monotonic', requested_at)
                processed_action = inference_fn(observation)

                if processed_action is not None:
                    try:
                        result_queue.put_nowait((processed_action, inference_start_time, observation_at))
                    except queue.Full:
                        try:
                            result_queue.get_nowait()
                            result_queue.put_nowait((processed_action, inference_start_time, observation_at))
                        except queue.Empty:
                            result_queue.put_nowait((processed_action, inference_start_time, observation_at))
            finally:
                busy_event.clear()
        except Exception as e:
            print(f"Error in inference worker thread: {e}")
            import traceback

            traceback.print_exc()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _compute_closed_hand_joints(side: str) -> np.ndarray:
    """Compute closed hand joint positions using G1GripperInverseKinematicsSolver."""
    side_str = "left" if side.upper() == "L" else "right"
    solver = G1GripperInverseKinematicsSolver(side=side_str)
    return solver._get_middle_close_q_desired().astype(np.float32)


def main(config: InferenceConfig):
    if config.sim_policy_control:
        if not config.sim_control_port or config.sim_stationary_body or config.sim_grasp_distance:
            raise ValueError('Policy mode requires the simulation channel and forbids stationary-token/proximity overrides')
        config.inspire_ftp_hands = True
    if config.sim_stationary_body and not config.sim_control_port:
        raise ValueError("Stationary body mode requires the simulation control channel")
    if not 0 <= config.sim_grasp_distance <= .1:
        raise ValueError("sim_grasp_distance must be between 0 and 0.1 metres")
    if not 0 <= config.sim_grasp_x_tolerance <= .02:
        raise ValueError("sim_grasp_x_tolerance must be between 0 and 0.02 metres")
    if config.sim_grasp_distance and not config.sim_control_port:
        raise ValueError("Proximity hand closure requires the simulation control channel")
    pause_loop = True
    diagnostic_writer = (DiagnosticWriter(config.action_diagnostic_path)
                         if config.action_diagnostic_path else None)

    def record_action(event, **fields):
        if diagnostic_writer is not None:
            diagnostic_writer.submit({"event": event, "monotonic": time.monotonic(),
                                      "wall_time_unix_s": time.time(), **fields})

    chunk_id = 0

    robot_model = instantiate_g1_robot_model(waist_location="lower_and_upper_body")

    # Isaac-GR00T PolicyClient
    from gr00t.policy.server_client import PolicyClient

    n1_policy = PolicyClient(host=config.host, port=config.port)

    print(f"Connecting to PolicyServer at {config.host}:{config.port}...")
    if n1_policy.ping():
        print_green("PolicyServer is reachable.")
    else:
        print("WARNING: PolicyServer not reachable. Inference will fail until server is up.")

    state_subscriber = ZMQStateSubscriber(
        host=config.state_zmq_host,
        port=config.state_zmq_port,
    )

    camera_subscriber = ComposedCameraClientSensor(
        server_ip=config.camera_host, port=config.camera_port
    )
    # Separate socket on the control thread: the inference worker cannot refresh
    # its last observation while waiting for a slow/warm-up policy response.
    camera_monitor = (ComposedCameraClientSensor(server_ip=config.camera_host, port=config.camera_port)
                      if config.sim_control_port else None)
    live_camera_capture = 0.
    last_camera_health_check = 0.

    if config.inspire_ftp_hands:
        from gear_sonic.utils.inference.inspire_adapter import inspire_grip_to_dex3
        closed_left = _compute_closed_hand_joints("L")
        print("Experimental Inspire FTP -> Dex3 grip adapter enabled (simulation only).")
    if config.inspire_ftp_hands or config.sim_grasp_distance:
        closed_right = _compute_closed_hand_joints("R")
    hand_closure = None
    if config.sim_grasp_distance:
        from gear_sonic.utils.inference.proximity_hand import ProximityHandClosure
        hand_closure = ProximityHandClosure(closed_right)
        print(f"Grasp-region centre closure: |X error| <= {config.sim_grasp_x_tolerance * 100:.1f} cm, Y surface gap <= {config.sim_grasp_distance * 100:.1f} cm.")
    last_sent_right_hand = np.zeros(7, dtype=np.float32)

    zmq_context = zmq.Context()
    zmq_socket = zmq_context.socket(zmq.PUB)
    zmq_socket.bind(f"tcp://{config.action_zmq_host}:{config.action_zmq_port}")
    time.sleep(0.1)
    print_green(
        f"ZMQ action socket bound to tcp://{config.action_zmq_host}:{config.action_zmq_port}"
    )
    print_green(f"Using embodiment tag: {config.embodiment_tag}")

    keyboard_listener = ZMQKeyboardSubscriber(
        port=config.keyboard_zmq_port, host=config.keyboard_zmq_host
    )

    simulation_channel = None
    if config.sim_control_port:
        from gear_sonic.utils.inference.simulation_controls import SimulationControlChannel
        simulation_channel = SimulationControlChannel(port=config.sim_control_port)
    sensor_status = {"input_ready": False, "camera_capture_monotonic": 0., "error": ""}
    minimum_capture_monotonic = [0.]
    simulation_preparing = False
    last_initial_pose_publish = 0.
    actions_published = 0
    last_status_publish = 0.

    telemetry = Telemetry(window_size=100)

    loop_rate = config.action_publish_rate
    loop_period = 1.0 / loop_rate

    # Track C++ control loop state
    cpp_loop_running = False
    cpp_mode = "OFF"  # "OFF", "PLANNER", or "POSE"

    # Track initial pose hand states
    initial_pose_left_hand_closed = False
    initial_pose_right_hand_closed = False

    def publish_initial_pose(wait=True):
        """Publish initial pose command to move robot to starting position."""
        if wait:
            print("Moving to initial pose")
        left_hand = (
            _compute_closed_hand_joints("L")
            if initial_pose_left_hand_closed
            else np.zeros(7, dtype=np.float32)
        )
        right_hand = (
            _compute_closed_hand_joints("R")
            if initial_pose_right_hand_closed
            else np.zeros(7, dtype=np.float32)
        )
        zmq_message = pack_latent_action_message(
            motion_token=LATENT_INITIAL_MOTION_TOKEN,
            frame_index=np.array([0], dtype=np.int64),
            left_hand_joints=left_hand,
            right_hand_joints=right_hand,
        )
        zmq_socket.send(zmq_message)
        if wait:
            print_green("Sent latent initial pose via ZMQ")
            time.sleep(1.0)
            print("Initial pose done.")

    def blend_to_initial_pose(duration_s: float) -> bool:
        """Smoothly interpolate from the last sent motion token to the initial pose.

        Linearly blends over ``duration_s`` seconds at the action publish rate,
        sending intermediate tokens each loop iteration. Returns True if blend
        was performed, False if skipped (no previous token available).
        """
        nonlocal last_sent_motion_token
        if last_sent_motion_token is None:
            print("No previous motion token — snapping to initial pose instead.")
            publish_initial_pose()
            return False

        start_token = last_sent_motion_token.copy()
        target_token = LATENT_INITIAL_MOTION_TOKEN.copy()
        num_steps = max(1, round(config.action_publish_rate * duration_s))
        step_period = 1.0 / config.action_publish_rate

        left_hand = (
            _compute_closed_hand_joints("L")
            if initial_pose_left_hand_closed
            else np.zeros(7, dtype=np.float32)
        )
        right_hand = (
            _compute_closed_hand_joints("R")
            if initial_pose_right_hand_closed
            else np.zeros(7, dtype=np.float32)
        )

        print(
            f"Blending to initial pose over {duration_s:.2f}s "
            f"({num_steps} steps at {config.action_publish_rate} Hz)"
        )

        for step in range(num_steps):
            t_step_start = time.monotonic()
            alpha = (step + 1) / num_steps
            blended_token = ((1.0 - alpha) * start_token + alpha * target_token).astype(
                np.float32
            )
            zmq_message = pack_latent_action_message(
                motion_token=blended_token,
                frame_index=np.array([0], dtype=np.int64),
                left_hand_joints=left_hand,
                right_hand_joints=right_hand,
            )
            zmq_socket.send(zmq_message)
            last_sent_motion_token = blended_token.copy()

            elapsed = time.monotonic() - t_step_start
            remaining = step_period - elapsed
            if remaining > 0:
                time.sleep(remaining)

        print_green("Initial pose blend complete.")
        return True

    def send_cpp_control_command(start: bool, planner: bool = False):
        """Send C++ control loop start/stop commands via ZMQ."""
        nonlocal cpp_loop_running, cpp_mode
        try:
            cmd_msg = build_command_message(start=start, stop=not start, planner=planner)
            zmq_socket.send(cmd_msg)
            time.sleep(0.01)
            action_str = "start" if start else "stop"
            mode_str = "planner" if planner else "pose"
            cpp_loop_running = start
            if start:
                cpp_mode = "PLANNER" if planner else "POSE"
            else:
                cpp_mode = "OFF"
            print_green(f"Sent ZMQ command: {action_str} control loop ({mode_str} mode)")
            return True
        except Exception as e:
            action_str = "start" if start else "stop"
            print(f"Warning: Failed to send {action_str} command message: {e}")
            return False

    # Async inference state
    cached_action_chunk = None
    action_chunk_index = 0
    last_inference_time = 0.0
    accept_results_after = time.monotonic()
    inference_interval = 1.0 / config.rate

    zmq_frame_counter = 0
    last_sent_motion_token: np.ndarray | None = None

    PROMPT_MSG_PREFIX = "prompt:"

    def check_keyboard_input():
        nonlocal pause_loop, cpp_loop_running, cpp_mode
        nonlocal initial_pose_left_hand_closed, initial_pose_right_hand_closed
        nonlocal cached_action_chunk, action_chunk_index, last_inference_time
        nonlocal accept_results_after
        nonlocal zmq_frame_counter, last_sent_motion_token

        key = keyboard_listener.read_msg()
        if key is None:
            return
        record_action("keyboard", key=key)

        if key.startswith(PROMPT_MSG_PREFIX):
            new_prompt = key[len(PROMPT_MSG_PREFIX):]
            if new_prompt:
                old_prompt = language_prompt_ref[0]
                language_prompt_ref[0] = new_prompt
                print_green(f'Inference prompt changed: "{old_prompt}" -> "{new_prompt}"')
            else:
                print("Received empty prompt change -- ignoring.")
            return

        if key == "c":
            print("Keyboard: 'c' (start recording -- handled by data exporter)")
        elif key == "s":
            print("Keyboard: 's' (stop recording success -- handled by data exporter)")
        elif key == "f":
            print("Keyboard: 'f' (stop recording failure -- handled by data exporter)")
        elif key == "i":
            clear_policy_actions()
            accept_results_after = time.monotonic()
            if cpp_loop_running and cpp_mode == "PLANNER":
                if send_cpp_control_command(start=True, planner=False):
                    print("Switched to POSE mode (from PLANNER mode)")
                else:
                    print("Warning: Failed to switch to POSE mode")
            elif not cpp_loop_running:
                print("Note: C++ loop not running - press 'k' to start")

            pause_loop = True
            if config.initial_pose_blend_duration > 0 and last_sent_motion_token is not None:
                blend_to_initial_pose(config.initial_pose_blend_duration)
            else:
                publish_initial_pose()

            zmq_frame_counter = 0
            cached_action_chunk = None
            action_chunk_index = 0
            print("Cleared cached action chunk, reset frame counter")
        elif key == "p":
            pause_loop = not pause_loop
            clear_policy_actions()
            # A result computed before a pause/reset must not drive the next
            # trial. Request a fresh observation when resuming.
            accept_results_after = time.monotonic()
            cached_action_chunk = None
            action_chunk_index = 0
            last_inference_time = 0.0
            print(f"{'Paused' if pause_loop else 'Resumed'} policy loop")
            if pause_loop:
                print("Policy loop paused (C++ loop still running - press 'k' to stop)")
            else:
                print("Policy loop resumed")
        elif key == "k":
            if cpp_loop_running:
                current_planner = cpp_mode == "PLANNER"
                print(f"Stopping C++ control loop (from {cpp_mode} mode)...")
                if send_cpp_control_command(start=False, planner=current_planner):
                    print("Stopped C++ control loop")
            else:
                print("Starting C++ control loop in PLANNER mode...")
                if send_cpp_control_command(start=True, planner=True):
                    print("Started C++ control loop in PLANNER mode")
                    print("Press 'i' to send initial pose and switch to POSE mode")
                    if pause_loop:
                        print("Note: Policy loop is paused - press 'p' to resume")
        elif key == "[":
            initial_pose_left_hand_closed = not initial_pose_left_hand_closed
            print(
                f"Initial pose left hand: {'closed' if initial_pose_left_hand_closed else 'open'}"
            )
        elif key == "]":
            initial_pose_right_hand_closed = not initial_pose_right_hand_closed
            print(
                f"Initial pose right hand: "
                f"{'closed' if initial_pose_right_hand_closed else 'open'}"
            )

    # Mutable prompt container (single-writer from keyboard, single-reader from inference)
    language_prompt_ref: list[str] = [config.prompt]
    print(f"Starting the policy loop with language prompt: {language_prompt_ref[0]}")

    inference_queue = queue.Queue(maxsize=1)
    result_queue = queue.Queue(maxsize=1)
    inference_stop_event = threading.Event()
    inference_busy_event = threading.Event()

    def clear_policy_actions():
        nonlocal cached_action_chunk, action_chunk_index, last_inference_time
        nonlocal accept_results_after, zmq_frame_counter, last_sent_right_hand
        accept_results_after = time.monotonic()
        cached_action_chunk = None
        action_chunk_index = 0
        last_inference_time = 0.
        zmq_frame_counter = 0
        sensor_status.pop("policy_action", None)
        if hand_closure is not None:
            hand_closure.reset()
        last_sent_right_hand = np.zeros(7, dtype=np.float32)
        for channel in (inference_queue, result_queue):
            while True:
                try:
                    channel.get_nowait()
                except queue.Empty:
                    break

    def check_simulation_input():
        nonlocal pause_loop, simulation_preparing, last_initial_pose_publish
        nonlocal last_status_publish, last_sent_motion_token
        nonlocal initial_pose_left_hand_closed, initial_pose_right_hand_closed
        if simulation_channel is None:
            return
        while (message := simulation_channel.receive()) is not None:
            command = message.get("command")
            ok, error = True, ""
            if command in ("pause", "prepare"):
                pause_loop = True
                simulation_preparing = command == "prepare"
                clear_policy_actions()
                last_sent_motion_token = None
                initial_pose_left_hand_closed = initial_pose_right_hand_closed = False
                sensor_status.update(input_ready=False, error="")
                publish_initial_pose(wait=False)
                if simulation_preparing:
                    ok = send_cpp_control_command(start=True, planner=False)
                    last_initial_pose_publish = time.monotonic()
            elif command == "start":
                simulation_preparing = False
                clear_policy_actions()
                minimum_capture_monotonic[0] = time.monotonic()
                sensor_status.update(input_ready=False, error="Waiting for a fresh post-start camera frame")
                pause_loop = False
            elif command == "close_right_hand":
                from gear_sonic.utils.inference.proximity_hand import ready_to_close
                # No MuJoCo import is needed in VLA; validate both gates from
                # the physics-thread sample rather than accepting the old gap-only command.
                distance = message.get("y_surface_gap_m")
                x_error = message.get("x_error_m")
                if hand_closure is None or pause_loop or simulation_preparing:
                    ok, error = False, "Proximity closure is disabled or policy is paused"
                elif (not isinstance(distance, (int, float)) or not isinstance(x_error, (int, float))
                      or not ready_to_close(message, config.sim_grasp_distance, config.sim_grasp_x_tolerance, True, True)):
                    ok, error = False, "Grasp-region centre is not aligned with bottle X/Y"
                else:
                    hand_closure.activate(last_sent_right_hand, time.monotonic(), distance, x_error=x_error)
                    record_action("proximity_grasp_trigger", y_surface_gap_m=distance, x_error_m=x_error,
                                  grasp_center_world_m=message.get("grasp_center_world_m"), source=message.get("source"))
            else:
                ok, error = False, "Unknown simulation command"
            record_action("simulation_command", command=command, id=message.get("id"))
            simulation_channel.send({"type": "ack", "id": message.get("id"), "ok": ok, "error": error})
            print(f"[Simulation controls] {command}: {'OK' if ok else error}", flush=True)
        now = time.monotonic()
        if simulation_preparing and now - last_initial_pose_publish > .5:
            # Re-send while INIT/WAIT_FOR_CONTROL; the operator start signal and
            # initial token must both arrive before the simulation releases support.
            publish_initial_pose(wait=False)
            send_cpp_control_command(start=True, planner=False)
            last_initial_pose_publish = now
        if now - last_status_publish > .1:
            simulation_channel.send({"type": "status", "paused": pause_loop,
                "cpp_loop_running": cpp_loop_running, "actions_published": actions_published,
                **sensor_status})
            last_status_publish = now

    def infer_observation(obs):
        if config.inspire_ftp_hands:
            for key in ("left_hand", "right_hand"):
                obs["state"][key] = np.zeros_like(obs["state"][key])
        class RecordingPolicy:
            def get_action(self, observation):
                action, info = n1_policy.get_action(observation)
                record_action("raw_chunk", action={k: np.asarray(v).tolist() for k, v in action.items()},
                              input_state={k: np.asarray(v).tolist() for k, v in observation['state'].items()},
                              image_shape=list(observation['video']['ego_view'].shape),
                              image_timestamp=np.asarray(observation.get('timestamps')).tolist())
                return action, info
        return run_policy_inference_and_process(RecordingPolicy(), obs, robot_model)

    inference_worker_thread = threading.Thread(
        target=_inference_worker_loop,
        args=(
            inference_queue,
            result_queue,
            inference_stop_event,
            inference_busy_event,
            lambda: prepare_observation_from_sensors(
                camera_subscriber=camera_subscriber,
                state_subscriber=state_subscriber,
                robot_model=robot_model,
                language_prompt=language_prompt_ref[0],
                log_errors=True,
                minimum_capture_monotonic=minimum_capture_monotonic[0] if simulation_channel else None,
                sensor_status=sensor_status,
            ),
            lambda obs: infer_observation(obs),
        ),
        daemon=True,
    )
    inference_worker_thread.start()
    action_chunk_origin = 0.
    last_policy_latency = 0.

    try:
        while True:
            t_start = time.monotonic()
            check_keyboard_input()
            check_simulation_input()

            # Consume result first so last_inference_time is fresh before trigger check
            try:
                processed_action, inference_start_time, observation_at = result_queue.get_nowait()
                if pause_loop or inference_start_time < accept_results_after:
                    continue
                inference_delay = time.monotonic() - inference_start_time
                last_policy_latency = inference_delay
                action_chunk_index = calculate_latency_compensated_index(
                    inference_delay, config.action_publish_rate, config.action_horizon,
                    has_previous_chunk=cached_action_chunk is not None,
                )
                if config.sim_policy_control:
                    from gear_sonic.utils.inference.policy_control import policy_step_at
                    received_at = time.monotonic()
                    # First plan starts at zero while the robot was holding;
                    # later plans refer to the state paired with the RGB frame.
                    action_chunk_origin = observation_at if cached_action_chunk is not None else received_at
                    action_chunk_index = policy_step_at(received_at, action_chunk_origin,
                                                       config.action_publish_rate, config.action_horizon)
                cached_action_chunk = processed_action
                chunk_id += 1
                record_action("chunk_selected", chunk_id=chunk_id, start_index=action_chunk_index, latency=inference_delay,
                              observation_age_s=time.monotonic() - observation_at,
                              playback_clock='paired_capture' if config.sim_policy_control else 'publish_iterations',
                              action={k: np.asarray(v).tolist() for k, v in (processed_action or {}).items()})
                last_inference_time = time.monotonic()
                print_green(
                    f'New action chunk (prompt: "{language_prompt_ref[0]}", '
                    f"latency: {inference_delay:.3f}s)"
                )
            except queue.Empty:
                pass

            worker_is_busy = inference_busy_event.is_set()
            should_start = should_trigger_new_inference(
                cached_chunk_exists=(cached_action_chunk is not None),
                inference_thread_running=worker_is_busy,
                time_since_last_inference=(time.monotonic() - last_inference_time),
                inference_interval=inference_interval,
            )
            if config.sim_policy_control and cached_action_chunk is not None:
                from gear_sonic.utils.inference.policy_control import policy_chunk_needs_refresh
                should_start = should_start or policy_chunk_needs_refresh(
                    time.monotonic(), action_chunk_origin, config.action_publish_rate,
                    config.action_horizon, last_policy_latency)

            if should_start and not pause_loop and not worker_is_busy:
                try:
                    inference_queue.put_nowait(time.monotonic())
                except queue.Full:
                    pass

            if pause_loop:
                _sleep_remaining(t_start, loop_period)
                continue

            if simulation_channel is not None:
                now = time.monotonic()
                if now - last_camera_health_check >= .1:
                    latest_frame = camera_monitor.read()
                    if latest_frame is not None:
                        live_camera_capture = latest_frame.get("capture_monotonic", 0.)
                    last_camera_health_check = now
                captured = live_camera_capture
                waiting_for_first_frame = captured < minimum_capture_monotonic[0]
                stale = (now - minimum_capture_monotonic[0] > 5. if waiting_for_first_frame
                         else now - captured > 1.)
                if stale:
                    pause_loop = True
                    clear_policy_actions()
                    sensor_status.update(input_ready=False, error="Camera stale/disconnected. Reset before restarting.")
                    record_action("automatic_pause", reason="camera_stale")
                    print("[Simulation controls] Camera stale/disconnected; policy paused.", flush=True)
                    continue

            with telemetry.timer("total_loop"):
                if cached_action_chunk is None:
                    print("[DEBUG] No cached chunk yet, waiting...", flush=True)
                    _sleep_remaining(t_start, loop_period)
                    continue

                processed_action = cached_action_chunk

                if processed_action is None or not processed_action:
                    print("[DEBUG] processed_action is None or empty, skipping", flush=True)
                else:
                    from gear_sonic.utils.inference.policy_control import policy_action_step
                    if config.sim_policy_control:
                        action_chunk_index = policy_step_at(time.monotonic(), action_chunk_origin,
                                                           config.action_publish_rate, config.action_horizon)
                    try:
                        motion_token, left_hand_joints, right_hand_joints, current_idx = policy_action_step(
                            processed_action, action_chunk_index)
                    except ValueError as error:
                        pause_loop = True
                        clear_policy_actions()
                        sensor_status.update(input_ready=False, error=str(error))
                        record_action('automatic_pause', reason='invalid_policy_action', error=str(error))
                        continue

                    raw_right_hand = right_hand_joints.copy()
                    raw_left_hand = left_hand_joints.copy()
                    raw_motion_token = motion_token.copy()
                    if config.sim_stationary_body:
                        motion_token = np.asarray(LATENT_INITIAL_MOTION_TOKEN, dtype=np.float32).reshape(64).copy()
                    if config.inspire_ftp_hands:
                        left_hand_joints = inspire_grip_to_dex3(left_hand_joints, closed_left)
                        right_hand_joints = inspire_grip_to_dex3(right_hand_joints, closed_right)
                    closure_fraction = None
                    if hand_closure is not None:
                        right_hand_joints, closure_fraction = hand_closure.apply(right_hand_joints, time.monotonic())

                    frame_index = np.array([zmq_frame_counter], dtype=np.int64)
                    zmq_frame_counter += 1

                    zmq_message = pack_latent_action_message(
                        motion_token,
                        frame_index,
                        left_hand_joints=left_hand_joints,
                        right_hand_joints=right_hand_joints,
                    )
                    zmq_socket.send(zmq_message)
                    actions_published += 1
                    last_sent_right_hand = right_hand_joints.copy()
                    sensor_status["policy_action"] = {
                        "frame": int(frame_index[0]), "chunk": chunk_id, "index": current_idx,
                        "output": "motion_token + hand joints (no XYZ target)",
                        "body_source": "SONIC standing token" if config.sim_stationary_body else "GR00T",
                        "motion_token_changed": not np.array_equal(raw_motion_token, motion_token),
                        "hand_adapter": "CloudWalk grip intent -> Dex3 (experimental)" if config.inspire_ftp_hands else "none",
                        "right_grip": float(np.clip(raw_right_hand[:5].mean(), 0., 1.))
                            if config.inspire_ftp_hands else None,
                        "published_monotonic": time.monotonic(),
                        "hand_source": ("grasp_center_alignment_override" if closure_fraction is not None else
                                        "grasp_center_alignment_wait" if hand_closure else "GR00T"),
                        "closure_fraction": closure_fraction,
                        "grasp_trigger_y_gap_m": hand_closure.trigger_distance if hand_closure else None,
                        "grasp_trigger_x_error_m": hand_closure.trigger_x_error if hand_closure else None,
                    }
                    record_action("published", chunk_id=chunk_id, index=current_idx, frame=int(frame_index[0]),
                                  right_hand=right_hand_joints.tolist(), left_hand=left_hand_joints.tolist(),
                                  motion_token=motion_token.tolist(), closure_fraction=closure_fraction,
                                  raw_motion_token=raw_motion_token.tolist(),
                                  raw_left_hand=raw_left_hand.tolist(), raw_right_hand=raw_right_hand.tolist(),
                                  body_source=sensor_status['policy_action']['body_source'],
                                  hand_adapter=sensor_status['policy_action']['hand_adapter'],
                                  hand_source=sensor_status["policy_action"]["hand_source"])
                    last_sent_motion_token = motion_token.copy()
                    if zmq_frame_counter % 50 == 0:
                        print_green(
                            f"ZMQ: Sent latent action - "
                            f"frame: {frame_index[0]}, "
                            f"token shape: {motion_token.shape}"
                        )

                action_chunk_index = min(action_chunk_index + 1, config.action_horizon - 1)

            end_time = time.monotonic()

            if config.verbose_timing:
                telemetry.log_timing_info(context="VLA Inference Loop", threshold=0.0)
            elif (end_time - t_start) > (1 / config.rate):
                telemetry.log_timing_info(
                    context="VLA Inference Loop Missed", threshold=0.001
                )

            _sleep_remaining(t_start, loop_period)

    except KeyboardInterrupt:
        print("VLA inference loop terminated by user")

    finally:
        inference_stop_event.set()
        inference_worker_thread.join(timeout=1.0)
        if diagnostic_writer is not None:
            diagnostic_writer.close()
        if simulation_channel is not None:
            simulation_channel.close()
        if camera_monitor is not None:
            camera_monitor.close()
        zmq_socket.close()
        zmq_context.term()
        state_subscriber.close()
        keyboard_listener.close()
        print("Shutdown complete.")


def _sleep_remaining(t_start: float, loop_period: float):
    """Sleep for the remainder of the loop period."""
    elapsed = time.monotonic() - t_start
    remaining = loop_period - elapsed
    if remaining > 0:
        time.sleep(remaining)


if __name__ == "__main__":
    config = tyro.cli(InferenceConfig)
    main(config)
