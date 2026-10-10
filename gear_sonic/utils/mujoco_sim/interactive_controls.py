"""Simulation UI state machine. All physics changes happen on the sim thread."""

import time
import zmq

from gear_sonic.utils.inference.simulation_controls import SimulationControlChannel
from gear_sonic.utils.data_collection.zmq_state_subscriber import ZMQStateSubscriber


class InteractiveSimulationControls:
    def __init__(self, env, port=5581):
        self.env = env
        self.channel = SimulationControlChannel(port=port, bind=True)
        self.controller_state = ZMQStateSubscriber()
        self.controller_seen = 0.
        self.client_seen = 0.
        self.client_status = {}
        self.pending = None
        self.serial = 0
        self.phase = "idle"
        self.phase_since = time.monotonic()
        self.error = ""
        self.panel = None
        self.last_ui_update = 0.
        self._first_action_count = 0
        self.detector_socket = None
        self.detector_result = None
        from gear_sonic.utils.mujoco_sim.hand_alignment import HandGraspAlignment
        self.hand_alignment = HandGraspAlignment(env.mj_model) if env.bottle_placement is not None else None
        self.grasp_sample = {}
        self.grasp_latched = False
        self.bottle_seen = False
        self.recognition_scene = env.scene_changed_at
        if self.env.config.get("BOTTLE_DETECTION_PORT"):
            self.detector_socket = self.channel.context.socket(zmq.SUB)
            self.detector_socket.setsockopt_string(zmq.SUBSCRIBE, "")
            self.detector_socket.setsockopt(zmq.CONFLATE, 1)
            self.detector_socket.connect(f"tcp://127.0.0.1:{self.env.config['BOTTLE_DETECTION_PORT']}")
        self.open_panel()

    def open_panel(self):
        if self.env.viewer is None or self.env.bottle_placement is None:
            return
        if self.panel is not None:
            if self.panel.process.is_alive():
                return
            self.panel.close()
        from gear_sonic.utils.mujoco_sim.control_panel import SimulationControlPanel
        bottle = self.env.bottle_placement
        self.panel = SimulationControlPanel(bottle.xy, bottle.z, bottle.bounds)

    def connected(self):
        return time.monotonic() - self.client_seen < 2.

    def request(self, command, **fields):
        self.serial += 1
        message = {"command": command, "id": self.serial, **fields}
        if not self.channel.send(message):
            self.error = "VLA disconnected. Check inference pane / policy server."
            return False
        self.pending = (message, time.monotonic())
        return True

    def can_repeat_pickup(self):
        pickup = getattr(self.env, 'assisted_pickup', None)
        return (self.phase == 'running' and pickup is not None
                and pickup.active and pickup.stage == 'complete')

    def handle(self, message):
        command = message["command"]
        if command == "open_panel":
            self.open_panel()
            return
        if self.pending is not None and command != 'reset':
            self.error = "Please wait for the previous command."
            return
        self.error = ""
        if command == "place":
            if self.phase != "idle":
                self.error = "Click Reset robot + bottle before changing X/Y."
                return
            try:
                self.env.bottle_placement.reset(self.env.mj_model, self.env.mj_data, message["xy"])
                self.env.scene_changed_at = time.monotonic()
                self.bottle_seen = False
                self.grasp_latched = False
                print(f"[Simulation] Bottle XY = {self.env.bottle_placement.xy.tolist()}", flush=True)
            except (TypeError, ValueError) as error:
                self.error = str(error)
        elif command == "reset":
            self.pending = None  # Reset supersedes an unfinished Start/prepare.
            self.env.standby = True
            pickup = getattr(self.env, 'assisted_pickup', None)
            if pickup is not None:
                pickup.reset()
            if self.connected():
                if self.request("pause"):
                    self.phase = "resetting"
            else:
                # Local standby ignores stale DDS targets even without a VLA client.
                self.reset_scene()
        elif command == "lower":
            pickup = getattr(self.env, 'assisted_pickup', None)
            try:
                if self.phase != 'running' or pickup is None or not pickup.lower_to_table(self.env.mj_data, message.get('xy')):
                    self.error = 'Lower is available only after a successful assisted pickup.'
            except (TypeError, ValueError) as error:
                self.error = str(error)
        elif command == "start":
            if self.can_repeat_pickup():
                if not self.connected():
                    self.error = "VLA disconnected. Check inference pane / policy server."
                    return
                # Keep the live scene and standing controller. Only restart the
                # visual pickup state machine, requiring observations after this click.
                self.env.scene_changed_at = time.monotonic()
                self.detector_result = None
                self.bottle_seen = False
                self.grasp_latched = False
                self.env.assisted_pickup.start(self.env.mj_data)
                return
            if self.phase not in ("idle", "paused"):
                return
            if not self.connected():
                self.error = "VLA disconnected. Check inference pane / policy server."
                return
            if self.env.viewer is not None:
                # F6 also toggles MuJoCo's native body-frame drawing. Keep
                # that built-in shortcut from obscuring the pickup scene.
                with self.env.viewer.lock():
                    self.env.viewer.opt.frame = 0
            if self.request("prepare"):
                self.grasp_latched = False
                self.phase = "preparing"
                self.phase_since = time.monotonic()
                self.controller_seen = 0.
                self.controller_state.get_msg()  # Discard a pre-reset queued state.
                self.env.standby = True
                self.env.restore_ground_support()

    def handle_keyboard(self, key):
        """Keep the existing k/i/p terminal workflow usable alongside the panel."""
        if self.pending is not None:
            return
        if key in ("k", "i"):
            self.env.standby = False
            self.phase = "paused"
        elif key == "p":
            if self.client_status.get("paused", True):
                if time.monotonic() - self.controller_seen < .5:
                    self.env.release_ground_support()
                self.phase = "observing"
                self._first_action_count = self.client_status.get("actions_published", 0)
            else:
                self.phase = "paused"

    def reset_scene(self):
        self.env.reset()
        self.grasp_latched = False
        self.bottle_seen = False
        self.grasp_sample = {}
        self.phase = "idle"
        self.phase_since = time.monotonic()
        self.error = ""
        print("[Simulation] Robot + bottle reset; policy paused, ground standby active.", flush=True)

    def poll(self):
        now = time.monotonic()
        if self.detector_socket is not None:
            try:
                self.detector_result = self.detector_socket.recv_json(zmq.NOBLOCK)
            except zmq.Again:
                pass
        if self.controller_state.get_msg() is not None:
            self.controller_seen = now
        while (message := self.channel.receive()) is not None:
            if message.get("type") == "status":
                self.client_status = message
                self.client_seen = now
            elif message.get("type") == "ack" and self.pending is not None:
                request, _ = self.pending
                if message.get("id") != request["id"]:
                    continue
                self.pending = None
                if not message.get("ok", False):
                    self.error = message.get("error", "VLA command failed.")
                    self.phase = "paused"
                elif request["command"] == "pause":
                    self.reset_scene()
                elif request["command"] == "start":
                    self.phase = "observing"
                    self.phase_since = now
                    self._first_action_count = self.client_status.get("actions_published", 0)
        if self.pending is not None and now - self.pending[1] > 10:
            self.error = "VLA command timed out. Check logs, then click Reset."
            self.pending = None
            self.phase = "paused"
        if self.phase == "preparing" and self.pending is None:
            if (now - self.controller_seen < .5 and now - self.phase_since >= 2.
                    and getattr(self.env.unitree_bridge, 'low_cmd_received', False)):
                self.env.begin_control_transition()
                self.phase = "grounded"
                self.phase_since = now
            elif now - self.phase_since > 15:
                self.error = "SONIC not ready. Check C++ deploy (Init Done / LowState)."
        elif self.phase == "grounded" and self.env._control_transition_started is None:
            if now - self.controller_seen < .5 and self.request("start"):
                self.env.release_ground_support()
                self.phase = "starting"
        elif self.phase == "observing":
            if self.client_status.get("actions_published", 0) > self._first_action_count:
                self.phase = "running"
            elif self.client_status.get("paused", False) and now - self.phase_since > .3:
                self.phase = "paused"
        elif self.phase == "running" and self.client_status.get("paused", False):
            self.phase = "paused"

        # Queue events from Tk/viewer; no callbacks are allowed to modify MjData.
        while not self.env.ui_commands.empty():
            self.handle(self.env.ui_commands.get_nowait())
        if self.panel is not None:
            while (command := self.panel.read()) is not None:
                self.handle(command)
        self.check_hand_alignment()
        pickup = getattr(self.env, 'assisted_pickup', None)
        if pickup is not None:
            from gear_sonic.utils.perception.bottle_detector import current_detection
            if self.phase == 'running':
                if not pickup.active:
                    pickup.start(self.env.mj_data)
                pickup.update(self.env.mj_data, current_detection(self.detector_result, self.env.scene_changed_at))
            elif pickup.active:
                pickup.reset()
        if now - self.last_ui_update >= .1:
            snapshot = self.snapshot()
            self.env.ui_snapshot = snapshot
            if self.panel is not None and self.panel.process.is_alive():
                self.panel.update(snapshot)
            self.last_ui_update = now

    def check_hand_alignment(self):
        proximity = getattr(self, "hand_alignment", None)
        if proximity is None:
            return
        from gear_sonic.utils.perception.bottle_detector import current_detection
        from gear_sonic.utils.inference.proximity_hand import ready_to_close
        self.grasp_sample = proximity.measure(self.env.mj_data)
        if self.recognition_scene != self.env.scene_changed_at:
            self.bottle_seen = False
            self.recognition_scene = self.env.scene_changed_at
        # Recognition may precede approach and then be occluded by the hand.
        # A reset/place invalidates this trial's recognition latch.
        if self.detector_socket and current_detection(self.detector_result, self.env.scene_changed_at).get("status") == "detected":
            self.bottle_seen = True
        threshold = self.env.config.get("SIM_GRASP_DISTANCE", 0.)
        tolerance = self.env.config.get("SIM_GRASP_X_TOLERANCE", .005)
        if (threshold > 0 and not self.grasp_latched and self.pending is None and self.connected()
                and ready_to_close(self.grasp_sample, threshold, tolerance, self.phase == "running", self.bottle_seen)):
            if self.request("close_right_hand", source=self.grasp_sample["distance_source"], **self.grasp_sample):
                self.grasp_latched = True
                print(f"[Simulation] Grasp-region centre: X error {self.grasp_sample['x_error_m'] * 100:.2f} cm, "
                      f"Y surface gap {self.grasp_sample['y_surface_gap_m'] * 100:.2f} cm: closing right hand.", flush=True)

    def snapshot(self):
        snapshot = self.env.coordinate_snapshot()
        snapshot.update(self.env.command_coordinate_snapshot())
        from gear_sonic.utils.perception.bottle_detector import current_detection
        detection = current_detection(self.detector_result, self.env.scene_changed_at) if self.detector_socket else {"status": "disabled"}
        labels = {
            "idle": "Robot pose locked. Enter bottle X/Y, then click Start.",
            "resetting": "Pausing GR00T before reset...",
            "preparing": "Pose locked. Waiting for fresh SONIC commands...",
            "grounded": "Smoothly transferring joint control to SONIC...",
            "starting": "Requesting a new camera frame...",
            "observing": "Waiting for GR00T: fresh RGB + prompt + robot state...",
            "running": "GR00T is controlling the robot. Click Reset to repeat.",
            "paused": "Paused. Click Reset to return to the initial position.",
        }
        snapshot.update(
            hand_alignment=getattr(self, "grasp_sample", {}),
            grasp_threshold_m=self.env.config.get("SIM_GRASP_DISTANCE", 0.),
            grasp_x_tolerance_m=self.env.config.get("SIM_GRASP_X_TOLERANCE", .005),
            grasp_latched=getattr(self, "grasp_latched", False),
            bottle_seen=getattr(self, "bottle_seen", False),
            detection=detection,
            policy_action=self.client_status.get("policy_action", {}),
            actions_published=self.client_status.get("actions_published", 0),
            phase=self.phase, status=labels[self.phase], error=self.error,
            can_start=self.connected() and (self.phase in ("idle", "paused") or self.can_repeat_pickup()) and self.pending is None,
            can_place=self.phase == "idle" and self.pending is None,
            inference=(f"VLA: {'connected' if self.connected() else 'disconnected'} | "
                       f"Published actions: {self.client_status.get('actions_published', 0)}\n"
                       "GR00T detected XYZ: unavailable in checkpoint output.\n"
                       + self.client_status.get("error", "")),
        )
        sample = snapshot["hand_alignment"]
        action = snapshot["policy_action"]
        fraction = action.get("closure_fraction")
        if not snapshot["grasp_threshold_m"]:
            grasp_status = "Disabled (GR00T hand commands)"
        elif fraction is not None:
            grasp_status = "Holding closed" if fraction >= 1. else f"Closing {fraction * 100:.0f}%"
        elif snapshot["grasp_latched"]:
            grasp_status = "Closure requested"
        elif self.phase != "running":
            grasp_status = "Waiting for Start"
        elif not snapshot["bottle_seen"]:
            grasp_status = "Waiting for YOLO recognition"
        elif sample.get("bottle_tilt_deg", 0.) >= 30.:
            grasp_status = "Bottle tipped - Reset to retry"
        elif abs(sample.get("x_error_m", float("inf"))) > snapshot["grasp_x_tolerance_m"] + 1e-9:
            grasp_status = "Waiting for X alignment"
        elif sample.get("y_surface_gap_m") is None:
            grasp_status = "Grasp centre outside bottle profile"
        elif sample["y_surface_gap_m"] < -1e-9:
            grasp_status = "Grasp centre inside bottle - Reset"
        else:
            grasp_status = f"Waiting for Y gap <= {snapshot['grasp_threshold_m'] * 100:.1f} cm"
        snapshot["grasp_status"] = grasp_status
        pickup = getattr(self.env, 'assisted_pickup', None)
        snapshot['can_lower'] = bool(pickup is not None and pickup.active
            and pickup.stage == 'success' and self.phase == 'running' and self.pending is None)
        if pickup is not None:
            snapshot['assisted_pickup'] = pickup.snapshot()
            snapshot['grasp_status'] = 'Assisted RGB-D pickup: ' + pickup.stage
            if self.env.config.get('FIXED_PICKUP_BASE', False):
                snapshot['inference'] += '\nExecuted motion: RGB-D/IK, pelvis fixed in simulation.'
                if self.phase == 'running':
                    snapshot['status'] = ('Arm home. Click Start to pick up the bottle again at its current position.'
                        if pickup.stage == 'complete' else
                        'Assisted table pickup: ' + pickup.stage + '. Reset to stop or change scene X/Y.')
        return snapshot

    def close(self):
        if self.connected() and self.request("pause"):
            deadline = time.monotonic() + .5
            while time.monotonic() < deadline:
                message = self.channel.receive()
                if message and message.get("type") == "ack" and message.get("id") == self.serial:
                    break
                time.sleep(.005)
        if self.panel is not None:
            self.panel.close()
        if self.detector_socket is not None:
            self.detector_socket.close(linger=0)
        self.channel.close()
        self.controller_state.close()
