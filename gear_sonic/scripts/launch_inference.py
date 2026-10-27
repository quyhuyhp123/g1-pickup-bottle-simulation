"""
All-in-one tmux launcher for SONIC VLA inference.

Starts the inference stack in a single tmux session:

    Window 0 — inference (4 panes):
    ┌───────────────────────┬───────────────────────┐
    │ Pane 0: C++ Deploy    │ Pane 1: VLA Inference │
    │ (gear_sonic_deploy)   │ (.venv_inference)     │
    ├───────────────────────┼───────────────────────┤
    │ Pane 2: Keyboard Pub  │ Pane 3: Data Exporter │
    │ (.venv_inference)     │ (.venv_data_collection)│
    └───────────────────────┴───────────────────────┘

    Window 1 — sim  (only when --sim is passed):
    ┌─────────────────────────────────────────────────┐
    │ MuJoCo Simulator (run_sim_loop.py)              │
    │ (.venv_sim)                                     │
    └─────────────────────────────────────────────────┘

Prerequisites:
    - tmux installed (sudo apt install tmux)
    - Virtual environments set up:
        bash install_scripts/install_inference.sh     -> .venv_inference
        bash install_scripts/install_data_collection.sh -> .venv_data_collection (optional, for recording)
    - gear_sonic_deploy built (see docs)
    - Isaac-GR00T PolicyServer running separately

Usage (from repo root — no venv activation needed):
    python gear_sonic/scripts/launch_inference.py                        # real robot
    python gear_sonic/scripts/launch_inference.py --sim                  # MuJoCo sim
    python gear_sonic/scripts/launch_inference.py --no-data-exporter     # no recording pane
"""

from dataclasses import dataclass
from pathlib import Path
import os
import re
import shutil
import signal
import socket
import base64
import subprocess
import sys
import textwrap
import time


def _bootstrap_venv():
    """Re-exec with the .venv_inference Python if tyro is not available."""
    try:
        import tyro  # noqa: F401
        return
    except ImportError:
        pass

    repo_root = Path(__file__).resolve().parent.parent.parent
    venv_python = repo_root / ".venv_inference" / "bin" / "python"
    if not venv_python.exists():
        print(
            "ERROR: tyro is not installed and .venv_inference not found.\n"
            "  Run: bash install_scripts/install_inference.sh"
        )
        sys.exit(1)

    print(f"Re-launching with {venv_python} ...")
    os.execv(str(venv_python), [str(venv_python)] + sys.argv)


_bootstrap_venv()

import tyro


def _get_local_ip() -> str:
    """Best-effort detection of the PC's LAN IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "unknown"


@dataclass
class InferenceLaunchConfig:
    """CLI config for the all-in-one VLA inference tmux launcher."""

    # Deployment mode
    record_dir: str = ""
    """Raw assisted simulation episodes; empty disables recording."""
    record_fps: int = 10
    """Synchronized raw camera recording frequency in simulation time."""

    sim: bool = False
    """Run against MuJoCo sim instead of real robot."""

    sim_finetuned_policy: bool = False
    """Run the fine-tuned native Dex3 checkpoint through SONIC, with its fixed-base training profile and no RGB-D/IK."""

    finetuned_model_path: str = "outputs/gr00t_g1_dex3_finetune_v1/checkpoint-best"
    """Full local checkpoint for --sim-finetuned-policy. The launcher starts its own verified policy server."""

    sim_policy_control: bool = False
    """Strict GR00T -> SONIC baseline; selected automatically for simulation without explicit assistance."""

    sim_grasp_distance: float | None = None
    """Optional proximity closure (m). Default 0: finger timing comes from the policy."""

    sim_grasp_x_tolerance: float = .005
    """World-X matching tolerance for grasp-region centre vs bottle centre (metres)."""

    sim_arm_gravity_compensation: bool = True
    """Add arm bias feedforward in MuJoCo to reduce sag relative to SONIC joint targets; simulation only."""

    sim_assisted_pickup: bool = False
    """Use RGB-D target correction for right-arm approach, physical grasp and lift; SONIC controls the body. Simulation only."""

    sim_native_inspire: bool = False
    """Native Inspire FTP hand model, requires assisted fixed-base simulation."""

    sim_fixed_base: bool = False
    """Anchor the simulated pelvis and hold unused joints for repeatable table pickup. Requires --sim-assisted-pickup."""

    sim_bottle_xy: tuple[float, float] | None = None
    """Initial bottle X/Y in metres; can also be changed in the simulation panel."""

    bottle_detection: bool = True
    """Show YOLO detections; optional proximity mode also requires bottle recognition."""

    detector_model: str = "models/detectors/yolo11n.pt"
    """Local YOLO bottle detector checkpoint; its XYZ is never fed into GR00T."""

    reach_diagnostic_path: str = ""
    """Optional simulator reach diagnostics JSON path (requires --sim)."""

    action_diagnostic_path: str = ""
    """Optional JSONL recording of policy chunks and published actions."""

    # C++ deploy options
    deploy_input_type: str = "zmq_manager"
    """Input type for the C++ deploy."""

    deploy_zmq_host: str = "localhost"
    """ZMQ host for the C++ deploy to listen on."""

    deploy_checkpoint: str = ""
    """Checkpoint path for deploy.sh. Leave empty for default."""

    deploy_obs_config: str = ""
    """Observation config file for deploy.sh. Leave empty for default."""

    deploy_planner: str = ""
    """Planner model path for deploy.sh. Leave empty for default."""

    deploy_motion_data: str = ""
    """Motion data path for deploy.sh. Leave empty for default."""

    deploy_output_type: str = ""
    """Output type for deploy.sh. Leave empty for default."""

    deploy_motor_kp_scale: str = ""
    """Kp scale specification for hardware motor indices (for example, 4,10=1.5)."""

    deploy_motor_kd_scale: str = ""
    """Kd scale specification for hardware motor indices (for example, 4,10=1.5)."""

    # VLA inference options
    policy_host: str = "localhost"
    """Isaac-GR00T PolicyServer host."""

    policy_port: int = 5550
    """Isaac-GR00T PolicyServer port."""

    embodiment_tag: str = "unitree_g1_sonic"
    """Embodiment tag for policy inference."""

    prompt: str = "demo"
    """Language prompt for inference."""

    action_publish_rate: int = 50
    """Rate at which individual actions are published to the C++ control loop (Hz)."""

    action_horizon: int = 40
    """Action horizon of the VLA policy."""

    inspire_ftp_hands: bool = False
    """Experimental CloudWalk Inspire FTP hand adapter; requires --sim."""

    # Camera
    camera_host: str = "localhost"
    """Camera server host."""

    camera_port: int = 5555
    """Camera server port."""

    # Data exporter (optional recording during inference)
    data_exporter: bool = True
    """Start the data exporter pane for recording during inference."""

    data_exporter_frequency: int = 50
    """Data collection frequency (Hz) for the data exporter."""

    task_prompt: str = ""
    """Task prompt for the data exporter. Defaults to the inference prompt if empty."""

    dataset_name: str = ""
    """Dataset name for the data exporter. Leave empty to auto-generate."""


SESSION_NAME = "sonic_inference"


def _resolve_sim_grasp_config(config: InferenceLaunchConfig):
    if config.sim_finetuned_policy:
        if (not config.sim or config.sim_assisted_pickup or config.sim_native_inspire
                or config.sim_fixed_base or config.inspire_ftp_hands or config.sim_grasp_distance
                or config.record_dir):
            raise ValueError('--sim-finetuned-policy requires --sim with native Dex3 and no assisted/Inspire/proximity options')
        config.sim_policy_control=False
        config.sim_grasp_distance=0.
        config.bottle_detection=False
        config.data_exporter=False
        return
    if config.record_dir:
        if not config.sim or not config.sim_assisted_pickup or not 0 < config.record_fps <= 60:
            raise ValueError('--record-dir requires --sim --sim-assisted-pickup and record FPS in 1..60')
        # C++ exporter labels precede simulation IK and must not be mistaken for expert labels.
        config.data_exporter = False
    # Resolve after CLI parsing so --sim is known; hardware never inherits
    # a simulation-only hand override from the launcher's defaults.
    if config.sim_grasp_distance is None:
        config.sim_grasp_distance = 0.
    # A normal --sim launch must use learned actions, including the training
    # hand convention. Legacy assistance remains an explicit opt-in.
    if (config.sim and not config.sim_assisted_pickup and not config.sim_fixed_base
            and not config.sim_native_inspire and not config.sim_grasp_distance):
        config.sim_policy_control = True
    if config.sim_policy_control:
        if (not config.sim or config.sim_assisted_pickup or config.sim_fixed_base
                or config.sim_native_inspire or config.sim_grasp_distance):
            raise ValueError('--sim-policy-control requires --sim with Dex3 and no assisted/fixed-base/proximity options. '
                             'Native CloudWalk-to-Inspire motor mapping is not yet verified.')
        config.inspire_ftp_hands = True
        # No detector process or depth-derived target is needed by this policy.
        config.bottle_detection = False
        if not config.action_diagnostic_path:
            config.action_diagnostic_path = 'outputs/gr00t_policy/actions.jsonl'
        if not config.reach_diagnostic_path:
            config.reach_diagnostic_path = 'outputs/gr00t_policy/reach.json'
    if config.sim_assisted_pickup:
        # The assisted controller owns right-hand closure throughout its motion.
        config.sim_grasp_distance = 0.


def _check_prerequisites(config: InferenceLaunchConfig):
    """Verify that required tools and venvs exist."""
    errors = []
    if config.sim_bottle_xy is not None and not config.sim:
        errors.append("--sim-bottle-xy requires --sim")
    if config.sim_native_inspire and not (config.sim and config.sim_assisted_pickup and config.sim_fixed_base):
        errors.append('--sim-native-inspire requires --sim --sim-assisted-pickup --sim-fixed-base')
    if config.sim_fixed_base and (not config.sim or not config.sim_assisted_pickup):
        errors.append("--sim-fixed-base requires --sim --sim-assisted-pickup")
    if config.sim_assisted_pickup and (not config.sim or not config.bottle_detection):
        errors.append("--sim-assisted-pickup requires --sim and the bottle detector")
    if not 0 <= config.sim_grasp_distance <= .1:
        errors.append("--sim-grasp-distance must be between 0 and 0.1 metres")
    if not 0 <= config.sim_grasp_x_tolerance <= .02:
        errors.append("--sim-grasp-x-tolerance must be between 0 and 0.02 metres")
    if config.sim_grasp_distance and (not config.sim or not config.bottle_detection):
        errors.append("--sim-grasp-distance requires --sim and the bottle detector")
    if config.inspire_ftp_hands and not config.sim:
        errors.append("--inspire-ftp-hands requires --sim (experimental Dex3 adapter)")

    if not shutil.which("tmux"):
        errors.append("tmux is not installed. Install with: sudo apt install tmux")

    repo_root = Path(__file__).resolve().parent.parent.parent

    if config.sim_native_inspire and not (repo_root / 'models/g1_inspire_ftp/g1_inspire_ftp_pickup.xml').is_file():
        errors.append('Build native hands first: .venv_sim/bin/python gear_sonic/scripts/prepare_inspire_ftp_sim.py')

    if not (repo_root / ".venv_inference" / "bin" / "activate").exists():
        errors.append(
            ".venv_inference not found. Run: bash install_scripts/install_inference.sh"
        )

    deploy_dir = repo_root / "gear_sonic_deploy"
    if not (deploy_dir / "deploy.sh").exists():
        errors.append(
            f"gear_sonic_deploy/deploy.sh not found at {deploy_dir}. "
            "Ensure the deploy directory is set up."
        )

    if config.data_exporter:
        if not (repo_root / ".venv_data_collection" / "bin" / "activate").exists():
            errors.append(
                ".venv_data_collection not found (needed for data exporter). Run: "
                "bash install_scripts/install_data_collection.sh"
            )

    if config.sim and not (repo_root / ".venv_sim" / "bin" / "activate").exists():
        errors.append(
            ".venv_sim not found. Set up the simulation venv first."
        )

    if config.sim and config.bottle_detection:
        detector_path = Path(config.detector_model).expanduser()
        if not detector_path.is_absolute():
            detector_path = repo_root / detector_path
        if not detector_path.is_file():
            errors.append("Bottle detector missing. Run: bash install_scripts/install_bottle_detector.sh "
                          "(or disable it with --no-bottle-detection)")
        python = repo_root / ".venv_inference" / "bin" / "python"
        if python.is_file():
            check = subprocess.run([str(python), "-c",
                "import importlib.util,sys;sys.exit(importlib.util.find_spec('ultralytics') is None)"],
                capture_output=True)
            if check.returncode:
                errors.append("Ultralytics missing in .venv_inference. "
                              "Run: bash install_scripts/install_bottle_detector.sh")

    if errors:
        print("ERROR: Prerequisites not met:\n")
        for e in errors:
            print(f"  - {e}")
        print()
        sys.exit(1)


def _kill_existing_session():
    subprocess.run(
        ["tmux", "kill-session", "-t", SESSION_NAME],
        capture_output=True,
    )


def _create_tmux_session():
    # Killing the last session asynchronously shuts down the tmux server.
    # Allow that server to exit before retrying creation on its socket.
    for attempt in range(5):
        result = subprocess.run(
            ["tmux", "new-session", "-d", "-s", SESSION_NAME],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            break
        if "server exited unexpectedly" not in result.stderr or attempt == 4:
            raise RuntimeError(f"Cannot create tmux session: {result.stderr.strip()}")
        time.sleep(0.2)
    subprocess.run(
        ["tmux", "set-option", "-t", SESSION_NAME, "-g", "mouse", "on"],
    )
    subprocess.run(
        ["tmux", "bind-key", "-T", "root", "C-\\", "kill-session"],
    )
    subprocess.run(
        ["tmux", "rename-window", "-t", f"{SESSION_NAME}:0", "inference"],
    )

    # Split into 4 panes: 0|1 / 2|3
    subprocess.run(
        ["tmux", "split-window", "-t", f"{SESSION_NAME}:0", "-h"],
    )
    subprocess.run(
        ["tmux", "split-window", "-t", f"{SESSION_NAME}:0.0", "-v"],
    )
    subprocess.run(
        ["tmux", "split-window", "-t", f"{SESSION_NAME}:0.2", "-v"],
    )

    time.sleep(5)


def _send_to_pane(pane_index: int, cmd: str, wait: float = 1.0):
    target = f"{SESSION_NAME}:0.{pane_index}"
    subprocess.run(
        ["tmux", "send-keys", "-t", target, cmd, "C-m"],
    )
    time.sleep(wait)


def _check_pane_alive(pane_index: int) -> bool:
    target = f"{SESSION_NAME}:0.{pane_index}"
    result = subprocess.run(
        ["tmux", "list-panes", "-t", target, "-F", "#{pane_dead}"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() != "1"


def main(config: InferenceLaunchConfig):
    repo_root = Path(__file__).resolve().parent.parent.parent

    _resolve_sim_grasp_config(config)
    if config.sim_finetuned_policy:
        model_path=Path(config.finetuned_model_path)
        if not model_path.is_absolute():model_path=repo_root/model_path
        command=[str(repo_root/'.venv_sim/bin/python'),str(repo_root/'gear_sonic/scripts/run_finetuned_sim.py'),
                 '--model-path',str(model_path),'--policy-host',config.policy_host,
                 '--policy-port',str(5551 if config.policy_port==5550 else config.policy_port),'--prompt',config.prompt]
        if config.sim_bottle_xy is not None:command+=['--bottle-xy',*[str(v) for v in config.sim_bottle_xy]]
        os.execv(command[0],command)
    _check_prerequisites(config)
    _kill_existing_session()

    exporter_prompt = config.task_prompt if config.task_prompt else config.prompt

    print("=" * 60)
    print("  SONIC VLA Inference Launcher")
    print("=" * 60)
    print(f"  Mode:            {'Simulation' if config.sim else 'Real Robot'}")
    if config.sim_policy_control:
        print('  Control owner:   GR00T v10 motion_token -> SONIC; hand timing from GR00T (Dex3 grip adapter)')
        print('  Overrides:       IK OFF | pelvis fixture OFF | proximity closure OFF')
        print('  Perception:      GR00T RGB + prompt + state; YOLO OFF; checkpoint emits no object XYZ')
        print('  Arm tracking:    PD bias feedforward may support SONIC targets; it never changes joint targets')
    print(f"  PolicyServer:    {config.policy_host}:{config.policy_port}")
    print(f"  Embodiment:      {config.embodiment_tag}")
    print(f"  Prompt:          {config.prompt}")
    print(f"  Action rate:     {config.action_publish_rate} Hz")
    print(f"  Action horizon:  {config.action_horizon}")
    print(f"  Camera:          {config.camera_host}:{config.camera_port}")
    print(f"  Data exporter:   {'Yes' if config.data_exporter else 'No'}")
    if config.sim_grasp_distance:
        print(f"  Hand closure:    grasp-region centre | X +/- {config.sim_grasp_x_tolerance * 100:.1f} cm | "
              f"Y surface gap <= {config.sim_grasp_distance * 100:.1f} cm")
    if config.sim:
        print(f"  Hand model:      {'Native Inspire FTP (six motors per hand)' if config.sim_native_inspire else 'Dex3'}")
        if config.sim_native_inspire:
            print("  Policy state:    approximate Dex3-compatible projection; native hand motion owned by assisted controller")
        print(f"  Arm feedforward: {'ON' if config.sim_arm_gravity_compensation else 'OFF'} (MuJoCo bias)")
        if config.sim_assisted_pickup:
            print("  Pickup:          RGB-D waist/right-arm correction; SONIC standing token")
            print(f"  Pelvis:          {'FIXED simulation fixture' if config.sim_fixed_base else 'Free / SONIC balance'}")
        else:
            print("  Pickup:          GR00T/SONIC trajectory only; assisted approach/lift OFF")
            print("  Table pickup:    add --sim-assisted-pickup --sim-fixed-base")
    if config.data_exporter:
        print(f"    DC frequency:  {config.data_exporter_frequency} Hz")
        print(f"    Task prompt:   {exporter_prompt}")
    print(f"  PC IP:           {_get_local_ip()}")
    print("=" * 60)

    _create_tmux_session()
    print(f"Created tmux session: {SESSION_NAME}")

    # --- Window 1 (sim only): MuJoCo Simulator ---
    if config.sim:
        subprocess.run(
            ["tmux", "new-window", "-t", SESSION_NAME, "-n", "sim"],
        )
        sim_cmd = (
            f"cd {repo_root} && "
            f"source .venv_sim/bin/activate && "
            f"python gear_sonic/scripts/run_sim_loop.py "
            f"--enable-image-publish --enable-offscreen "
            f"--camera-port {config.camera_port}"
        )
        if config.record_dir:
            import shlex
            if not config.sim_assisted_pickup:
                raise ValueError('Recording currently requires --sim-assisted-pickup')
            sim_cmd += (' --record-dir ' + shlex.quote(str((repo_root / config.record_dir).resolve()))
                        + ' --record-prompt ' + shlex.quote(config.prompt)
                        + f' --record-fps {config.record_fps}')
        if config.reach_diagnostic_path:
            import shlex
            sim_cmd += " --reach-diagnostic-path " + shlex.quote(config.reach_diagnostic_path)
        if config.bottle_detection:
            sim_cmd += " --enable-depth-publish --bottle-detection-port 5582"
        if config.sim_grasp_distance:
            sim_cmd += f" --sim-grasp-distance {config.sim_grasp_distance}"
            sim_cmd += f" --sim-grasp-x-tolerance {config.sim_grasp_x_tolerance}"
        if config.sim_arm_gravity_compensation:
            sim_cmd += " --arm-gravity-compensation"
        if config.sim_assisted_pickup:
            sim_cmd += " --assisted-pickup"
        if config.sim_native_inspire:
            sim_cmd += " --native-inspire"
        if config.sim_policy_control:
            sim_cmd += " --policy-control"
        if config.sim_fixed_base:
            sim_cmd += " --fixed-pickup-base"
        if config.sim_bottle_xy is not None:
            sim_cmd += f" --bottle-xy {config.sim_bottle_xy[0]} {config.sim_bottle_xy[1]}"
        sim_target = f"{SESSION_NAME}:sim"
        subprocess.run(
            ["tmux", "send-keys", "-t", sim_target, sim_cmd, "C-m"],
        )
        print("Starting MuJoCo simulator (window: sim)...")
        time.sleep(3.0)

        subprocess.run(
            ["tmux", "select-window", "-t", f"{SESSION_NAME}:inference"],
        )

    # --- Pane 0 (top-left): C++ Deploy ---
    deploy_mode = "sim" if config.sim else "real"
    deploy_cmd = (
        f"cd {repo_root / 'gear_sonic_deploy'} && "
        f"./deploy.sh "
        f"--input-type {config.deploy_input_type} "
        f"--zmq-host {config.deploy_zmq_host} "
    )
    if config.deploy_checkpoint:
        deploy_cmd += f"--cp {config.deploy_checkpoint} "
    if config.deploy_obs_config:
        deploy_cmd += f"--obs-config {config.deploy_obs_config} "
    if config.deploy_planner:
        deploy_cmd += f"--planner {config.deploy_planner} "
    if config.deploy_motion_data:
        deploy_cmd += f"--motion-data {config.deploy_motion_data} "
    if config.deploy_output_type:
        deploy_cmd += f"--output-type {config.deploy_output_type} "
    if config.deploy_motor_kp_scale:
        deploy_cmd += f"--motor-kp-scale {config.deploy_motor_kp_scale} "
    if config.deploy_motor_kd_scale:
        deploy_cmd += f"--motor-kd-scale {config.deploy_motor_kd_scale} "
    deploy_cmd += deploy_mode

    print("Starting C++ deploy (pane 0)...")
    _send_to_pane(0, deploy_cmd, wait=3.0)

    if config.sim:
        # The user requested simulation. Confirm only after deploy.sh has
        # explicitly resolved loopback and printed its simulation confirmation.
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            result = subprocess.run(
                ["tmux", "capture-pane", "-p", "-J", "-t", f"{SESSION_NAME}:inference.0", "-S", "-1000"],
                capture_output=True, text=True,
            )
            output = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", result.stdout)
            if ("This will start the simulation control system." in output
                    and re.search(r"(?:Resolved interface|Network Interface):\s+lo(?:0)?\b", output)
                    and "Proceed with deployment?" in output):
                _send_to_pane(0, "y", wait=.2)
                print("Simulation deploy confirmed on loopback; use the Start button in the control panel.")
                break
            time.sleep(.2)
        else:
            print("Simulation deploy did not reach its loopback confirmation. Check pane 0.")

    if not _check_pane_alive(0):
        print("WARNING: C++ deploy pane may have failed to start.")

    # --- Pane 2 (bottom-left): Keyboard Publisher ---
    keyboard_script = textwrap.dedent("""\
        import zmq, time
        ctx = zmq.Context()
        pub = ctx.socket(zmq.PUB)
        pub.bind('tcp://localhost:5580')
        time.sleep(0.5)
        print('Keyboard publisher ready. Keys: p=pause, k=start/stop, i=init pose, [/]=toggle hands, t=prompt')
        while True:
            key = input()
            if key.startswith('t '):
                pub.send_string('prompt:' + key[2:])
                print('Sent prompt: ' + key[2:])
            else:
                pub.send_string(key)
                print('Sent: ' + key)
    """)
    encoded = base64.b64encode(keyboard_script.encode()).decode()
    keyboard_cmd = (
        f"cd {repo_root} && "
        f"source .venv_inference/bin/activate && "
        f"python -c \"import base64;exec(base64.b64decode('{encoded}'))\""
    )

    print("Starting keyboard publisher (pane 2)...")
    _send_to_pane(1, keyboard_cmd, wait=2.0)

    # --- Pane 3 (bottom-right): Data Exporter (optional) ---
    if config.data_exporter:
        exporter_cmd = (
            f"cd {repo_root} && "
            f"source .venv_data_collection/bin/activate && "
            f"python gear_sonic/scripts/run_data_exporter.py "
            f"--task-prompt '{exporter_prompt}' "
            f"--data-collection-frequency {config.data_exporter_frequency} "
            f"--camera-host {config.camera_host} "
            f"--camera-port {config.camera_port}"
        )
        if config.dataset_name:
            exporter_cmd += f" --dataset-name '{config.dataset_name}'"

        print("Starting data exporter (pane 3)...")
        _send_to_pane(3, exporter_cmd, wait=2.0)

    # --- Pane 1 (top-right): VLA Inference ---
    inference_cmd = (
        f"cd {repo_root} && "
        f"source .venv_inference/bin/activate && "
        f"python gear_sonic/scripts/run_vla_inference.py "
        f"--host {config.policy_host} "
        f"--port {config.policy_port} "
        f"--embodiment-tag {config.embodiment_tag} "
        f"--prompt '{config.prompt}' "
        f"--action-publish-rate {config.action_publish_rate} "
        f"--action-horizon {config.action_horizon} "
        f"--camera-host {config.camera_host} "
        f"--camera-port {config.camera_port}"
    )

    if config.inspire_ftp_hands:
        inference_cmd += " --inspire-ftp-hands"
    if config.sim_policy_control:
        inference_cmd += " --sim-policy-control"
    if config.sim:
        inference_cmd += " --sim-control-port 5581"
    if config.sim_grasp_distance:
        inference_cmd += f" --sim-grasp-distance {config.sim_grasp_distance}"
        inference_cmd += f" --sim-grasp-x-tolerance {config.sim_grasp_x_tolerance}"
    if config.sim_assisted_pickup:
        inference_cmd += " --sim-stationary-body"
    if config.action_diagnostic_path:
        import shlex
        inference_cmd += " --action-diagnostic-path " + shlex.quote(config.action_diagnostic_path)

    print("Starting VLA inference (pane 1)...")
    _send_to_pane(2, inference_cmd, wait=1.0)

    if config.sim and config.bottle_detection:
        import shlex
        detector_command = (
            f"cd {shlex.quote(str(repo_root))} && "
            f".venv_inference/bin/python gear_sonic/scripts/run_bottle_detector.py "
            f"--model-path {shlex.quote(config.detector_model)} --camera-port {config.camera_port}"
        )
        subprocess.run(["tmux", "new-window", "-t", SESSION_NAME, "-n", "vision"])
        subprocess.run(["tmux", "send-keys", "-t", f"{SESSION_NAME}:vision", detector_command, "C-m"])
        subprocess.run(["tmux", "select-window", "-t", f"{SESSION_NAME}:inference"])
        print("Starting YOLO bottle detector (window: vision)...")

    # Select the VLA inference pane
    subprocess.run(
        ["tmux", "select-pane", "-t", f"{SESSION_NAME}:0.2"],
    )

    print()
    print("=" * 60)
    print("  All components launched!")
    print()
    print(f"  tmux session: {SESSION_NAME}")
    print()
    if config.sim:
        print("  Window 'sim':")
        print("    MuJoCo Simulator (.venv_sim)")
        print()
    print("  Window 'inference':")
    print("    Pane 0 (top-left):     C++ Deploy")
    print("    Pane 1 (bottom-left):  Keyboard Publisher")
    print("    Pane 2 (top-right):    VLA Inference  <-- you are here")
    if config.data_exporter:
        print("    Pane 3 (bottom-right): Data Exporter")
    print()
    if config.sim:
        print("  Simulation panel: enter bottle X/Y, Reset robot + bottle, Start GR00T.")
        print("  Robot starts on the ground; startup support releases automatically.")
        if config.bottle_detection:
            print("  YOLO surface XYZ and a camera preview show separate bottle detections.")
        if config.sim_grasp_distance:
            print(f"  Grasp-region centre: |X error| <= {config.sim_grasp_x_tolerance * 100:.1f} cm and Y surface gap <= {config.sim_grasp_distance * 100:.1f} cm, then close.")
    else:
        print("  ** deploy.sh (pane 0) is waiting for confirmation --")
        print("     click on pane 0 and press Enter to proceed **")
    print()
    print("  Keyboard controls (type in pane 1):")
    print("    p        - Pause / resume inference")
    print("    k        - Start / stop C++ control loop")
    print("    i        - Send initial pose")
    print("    [        - Toggle left hand open/closed (initial pose)")
    print("    ]        - Toggle right hand open/closed (initial pose)")
    print("    t <text> - Change inference prompt")
    if config.sim:
        print("    F2       - Reopen simulation control panel (viewer focus)")
        print("    F5 / F6  - Reset robot / Start GR00T (viewer focus)")
        print("    9        - Manually toggle support (optional)")
        print("    r        - Reset bottle only (pause with i before repeating a trial)")
    if config.data_exporter:
        print("    c        - Start recording episode")
        print("    s        - Stop recording (success)")
        print("    f        - Stop recording (failure)")
    print()
    print("  Navigation:")
    print("    Ctrl+b, arrow keys  - Switch between panes")
    if config.sim:
        print("    Ctrl+b, n / p       - Next / previous window")
    print("    Ctrl+b, d           - Detach from session")
    print("    Ctrl+\\              - Kill entire session")
    print("=" * 60)

    try:
        subprocess.run(["tmux", "attach", "-t", SESSION_NAME])
    except KeyboardInterrupt:
        pass

    result = subprocess.run(
        ["tmux", "has-session", "-t", SESSION_NAME],
        capture_output=True,
    )
    if result.returncode == 0:
        print(f"\nSession '{SESSION_NAME}' is still running.")
        print(f"  Reattach:  tmux attach -t {SESSION_NAME}")
        print(f"  Kill:      tmux kill-session -t {SESSION_NAME}")


def _signal_handler(_sig, _frame):
    print("\nShutdown requested...")
    subprocess.run(
        ["tmux", "kill-session", "-t", SESSION_NAME],
        capture_output=True,
    )
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, _signal_handler)
    config = tyro.cli(InferenceLaunchConfig)
    main(config)
