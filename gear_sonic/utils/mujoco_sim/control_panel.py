"""Native bottle/run controls in a separate process, leaving physics responsive."""

import multiprocessing as mp
import os
import queue


class SimulationControlPanel:
    def __init__(self, xy, z, bounds):
        context = mp.get_context("spawn")
        self.commands = context.Queue(maxsize=16)
        self.snapshots = context.Queue(maxsize=1)
        self.stop_event = context.Event()
        self.process = context.Process(
            target=_panel_worker,
            args=(list(xy), z, bounds.tolist(), self.commands, self.snapshots, self.stop_event, os.getpid()),
            daemon=True,
        )
        self.process.start()

    def read(self):
        try:
            return self.commands.get_nowait()
        except queue.Empty:
            return None

    def update(self, snapshot):
        try:
            self.snapshots.put_nowait(snapshot)
        except queue.Full:
            try:
                self.snapshots.get_nowait()
            except queue.Empty:
                return
            try:
                self.snapshots.put_nowait(snapshot)
            except queue.Full:
                pass

    def close(self):
        self.stop_event.set()
        self.process.join(timeout=2)
        if self.process.is_alive():
            self.process.terminate()
            self.process.join(timeout=1)
        for channel in (self.commands, self.snapshots):
            channel.cancel_join_thread()
            channel.close()


def _panel_worker(xy, z, bounds, commands, snapshots, stop_event, parent_pid=None):
    from gear_sonic.utils.mujoco_sim.process_lifecycle import follow_parent
    if parent_pid is not None and not follow_parent(parent_pid):
        return
    import tkinter as tk
    from tkinter import ttk

    try:
        root = tk.Tk()
    except tk.TclError as error:
        print(f"[Simulation controls] Cannot open control panel: {error}", flush=True)
        return
    root.title("MuJoCo - Bottle / Robot Controls")
    root.geometry("540x850+20+70")
    root.minsize(490, 700)
    root.attributes("-topmost", True)
    frame = ttk.Frame(root, padding=14)
    frame.pack(fill="both", expand=True)
    detector_coordinates = tk.StringVar(value="DETECTED BOTTLE - YOLO\nWaiting for camera...")
    tk.Label(frame, textvariable=detector_coordinates, background="#073b45", foreground="#79ffb1",
             font=("TkFixedFont", 12, "bold"), justify="left", anchor="w", padx=12, pady=14).pack(fill="x", pady=(0, 12))
    # Some WSL Tk builds expose only the X11 bitmap font (no Vietnamese glyphs).
    # ASCII labels keep the native controls readable without extra dependencies.
    ttk.Label(frame, text="Bottle position on table (metres, world frame)").pack(anchor="w")
    entries = ttk.Frame(frame)
    entries.pack(fill="x", pady=8)
    x, y = tk.StringVar(value=f"{xy[0]:.3f}"), tk.StringVar(value=f"{xy[1]:.3f}")
    for label, variable in (("X", x), ("Y", y)):
        ttk.Label(entries, text=label).pack(side="left", padx=4)
        ttk.Entry(entries, textvariable=variable, width=10).pack(side="left", padx=4)
    ttk.Label(frame, text=f"Placement Z = {z:.3f} m (fixed, bottle body centre)").pack(anchor="w")
    ttk.Label(frame, text=(f"X: {bounds[0][0]:.3f}..{bounds[0][1]:.3f}   "
                           f"Y: {bounds[1][0]:.3f}..{bounds[1][1]:.3f}")).pack(anchor="w")
    error_text = tk.StringVar()
    status = tk.StringVar(value="Connecting to simulation...")
    coordinates = tk.StringVar()
    detector_status = tk.StringVar()
    inference = tk.StringVar()

    def send(command):
        try:
            payload = {"command": command}
            if command == "place":
                payload["xy"] = [float(x.get()), float(y.get())]
            if command == "lower":
                payload["xy"] = [float(place_x.get()), float(place_y.get())]
            commands.put_nowait(payload)
            error_text.set("")
        except ValueError:
            error_text.set("X/Y must be numbers; use a decimal point.")
        except queue.Full:
            error_text.set("Please wait for the previous command.")

    apply_button = ttk.Button(frame, text="Apply X/Y / Reset bottle", command=lambda: send("place"))
    apply_button.pack(fill="x", pady=(10, 5))
    ttk.Button(frame, text="Reset robot + bottle", command=lambda: send("reset")).pack(fill="x", pady=5)
    start_button = ttk.Button(frame, text="Start GR00T", command=lambda: send("start"))
    start_button.pack(fill="x", pady=5)
    ttk.Label(frame, text="Place destination X/Y (metres, world frame)").pack(anchor="w")
    place_entries = ttk.Frame(frame)
    place_entries.pack(fill="x", pady=4)
    place_x, place_y = tk.StringVar(value=f"{xy[0]:.3f}"), tk.StringVar(value=f"{xy[1]:.3f}")
    for label, variable in (("X", place_x), ("Y", place_y)):
        ttk.Label(place_entries, text=label).pack(side="left", padx=4)
        ttk.Entry(place_entries, textvariable=variable, width=10).pack(side="left", padx=4)
    lower_button = ttk.Button(frame, text="Lower / Place on table", command=lambda: send("lower"), state="disabled")
    lower_button.pack(fill="x", pady=5)
    grasp_text = tk.StringVar(value="GRASP CENTRE\nWaiting for X/Y measurements...")
    tk.Label(frame, textvariable=grasp_text, background="#163553", foreground="#ffffff",
             font=("TkFixedFont", 11, "bold"), anchor="w", justify="left", padx=10, pady=10).pack(fill="x", pady=5)
    ttk.Label(frame, textvariable=error_text, foreground="#b00020", wraplength=455).pack(anchor="w")
    ttk.Separator(frame).pack(fill="x", pady=10)
    ttk.Label(frame, textvariable=status, wraplength=455).pack(anchor="w")
    ttk.Label(frame, textvariable=coordinates, font=("TkFixedFont", 10), justify="left").pack(anchor="w", pady=10)
    ttk.Label(frame, textvariable=detector_status, wraplength=455).pack(anchor="w", pady=(0, 10))
    ttk.Label(frame, textvariable=inference, wraplength=455).pack(anchor="w")
    ttk.Label(frame, text="MuJoCo = scene bottle centre.\n"
              "YOLO = estimated visible surface point from RGB + depth.\n"
              "Arm: GR00T/SONIC; assisted mode corrects right-arm pickup.\n"
              "Reset clears the motion. Change X/Y, Apply, then Start.",
              wraplength=455, foreground="#555555").pack(anchor="w", pady=10)

    def poll():
        if stop_event.is_set() or (parent_pid is not None and os.getppid() != parent_pid):
            root.destroy()
            return
        latest = None
        while True:
            try:
                latest = snapshots.get_nowait()
            except queue.Empty:
                break
        if latest is not None:
            status.set(latest["status"])
            error_text.set(latest.get("error", ""))
            lines = []
            for label, key in (("Bottle centre", "bottle"), ("GRASP CENTRE", "right_grasp_center"),
                               ("SONIC grasp", "right_grasp_target"), ("Wrist origin", "right_wrist")):
                pos = latest.get(key)
                if pos is not None:
                    lines.append(f"{label:13s} X {pos[0]:+.3f}\n"
                                 f"              Y {pos[1]:+.3f} Z {pos[2]:+.3f}")
            alignment = latest.get("hand_alignment", {})
            grasp = alignment.get("grasp_center_world_m")
            gap = alignment.get("y_surface_gap_m")
            x_error = alignment.get("x_error_m")
            x_text = f"{x_error * 100:+.2f}" if x_error is not None else "--"
            gap_text = f"{gap * 100:.2f}" if gap is not None else "--"
            position_text = (f"X {grasp[0]:+.3f} Y {grasp[1]:+.3f} Z {grasp[2]:+.3f} m\n" if grasp is not None else "")
            grasp_text.set("GRASP CENTRE - green marker (MuJoCo)\n" + position_text
                + f"X error {x_text} cm | tolerance {latest.get('grasp_x_tolerance_m', .005) * 100:.1f} cm\n"
                + f"Y surface gap {gap_text} cm | target {latest.get('grasp_threshold_m', 0.) * 100:.1f} cm\n"
                + latest.get("grasp_status", "Disabled"))
            detection = latest.get("detection", {})
            point = detection.get("world_point_m")
            if point is not None:
                detector_coordinates.set("DETECTED BOTTLE - YOLO (world, metres)\n"
                    f"X {point[0]:+.3f}    Y {point[1]:+.3f}    Z {point[2]:+.3f}\n"
                    f"Confidence {detection.get('confidence', 0.):.2f} | visible surface")
            else:
                detector_coordinates.set("DETECTED BOTTLE - YOLO\n"
                    + detection.get("status", "disabled") + "\nX --    Y --    Z --")
            detector_status.set("YOLO bottle: " + detection.get("status", "disabled")
                + (f" | confidence {detection['confidence']:.2f}" if "confidence" in detection else ""))
            coordinates.set("\n".join(lines))
            action = latest.get("policy_action", {})
            grip = action.get("right_grip")
            details = "\nGR00T right grip: " + (f"{grip * 100:.1f}%" if grip is not None else "--")
            if "wrist_tracking_error_m" in latest:
                details += f"\nSONIC wrist tracking error: {latest['wrist_tracking_error_m'] * 100:.1f} cm"
            if "grasp_tracking_error_m" in latest:
                details += f"\nSONIC grasp tracking error: {latest['grasp_tracking_error_m'] * 100:.1f} cm"
            inference.set(latest["inference"] + details)
            start_button.configure(state="normal" if latest["can_start"] else "disabled")
            lower_button.configure(state="normal" if latest.get("can_lower", False) else "disabled")
            apply_button.configure(state="normal" if latest["can_place"] else "disabled")
        root.after(100, poll)

    # Closing this optional panel does not stop physics; F2 reopens it.
    root.after(100, poll)
    root.mainloop()
