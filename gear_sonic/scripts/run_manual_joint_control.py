"""Standalone MuJoCo Dex3 joint panel. No DDS, GR00T, SONIC or hardware connection."""
import queue
import time
import tkinter as tk
from tkinter import ttk

import mujoco
import glfw
import numpy as np

from gear_sonic.utils.mujoco_sim.base_sim import DefaultEnv
from gear_sonic.utils.mujoco_sim.configs import SimLoopConfig


class ManualJoints:
    def __init__(self):
        config = SimLoopConfig(enable_onscreen=False).load_wbc_yaml()
        config.update(GROUND_START=True, POLICY_CONTROL=False, ASSISTED_PICKUP=False,
                      FIXED_PICKUP_BASE=False, NATIVE_INSPIRE=False)
        env = DefaultEnv(config, onscreen=False)
        self.model, self.data = env.mj_model, env.mj_data
        self.home = env.initial_qpos.copy()
        self.groups = {}
        for side in ('left', 'right'):
            arm = [side + '_' + name + '_joint' for name in
                   ('shoulder_pitch', 'shoulder_roll', 'shoulder_yaw', 'elbow',
                    'wrist_roll', 'wrist_pitch', 'wrist_yaw')]
            hand = [self.model.joint(int(j)).name for j in
                    (env.left_hand_index if side == 'left' else env.right_hand_index)]
            self.groups[side] = [self.model.joint(name).id for name in arm + hand]
        for side in ('left', 'right'):
            self.groups[side + '_leg'] = [self.model.joint(side + '_' + name + '_joint').id
                for name in ('hip_pitch', 'hip_roll', 'hip_yaw', 'knee', 'ankle_pitch', 'ankle_roll')]
        self.groups['waist'] = [self.model.joint('waist_' + axis + '_joint').id
                                for axis in ('yaw', 'roll', 'pitch')]
        self.offsets = {}
        joints = []
        for group, ids in self.groups.items():
            self.offsets[group] = len(joints)
            joints.extend(ids)
        self.joints = np.array(joints)
        self.qa = self.model.jnt_qposadr[self.joints]
        self.va = self.model.jnt_dofadr[self.joints]
        self.targets = self.home[self.qa].copy()
        self.setpoints = self.targets.copy()
        self.side, self.index = 'right', 0
        self.step_degrees = 2.
        self.home_hold = False
        self.actuators = []
        for joint in self.joints:
            ids = np.flatnonzero(self.model.actuator_trnid[:, 0] == joint)
            if len(ids) != 1:
                raise ValueError(f'Expected one actuator for {self.model.joint(int(joint)).name}')
            self.actuators.append(ids[0])
        self.actuators = np.array(self.actuators)
        env.hold_initial_robot_pose()
        positions, velocities, _ = env._idle_robot_indices
        self.robot_q = np.array(positions, dtype=int)
        self.robot_v = np.array(velocities, dtype=int)
        self.lock_q = np.setdiff1d(positions, self.qa)
        self.lock_v = np.setdiff1d(velocities, self.va)
        self.kp = np.array([5. if '_hand_' in self.model.joint(int(j)).name else 60. for j in self.joints])
        self.kd = np.where(self.kp < 10, .3, 3.)
        self.original_rgba = self.model.geom_rgba.copy()
        self.original_material = self.model.geom_matid.copy()
        self.body_to_selection = {int(self.model.jnt_bodyid[j]): i for i, j in enumerate(self.joints)}
        self._highlighted_selection = None
        self.highlight()

    def select_body(self, body):
        # A fixed visual sub-link belongs to the nearest actuated ancestor.
        while body > 0:
            if body in self.body_to_selection:
                i = self.body_to_selection[body]
                for group, offset in self.offsets.items():
                    if offset <= i < offset + len(self.groups[group]):
                        self.side, self.index = group, i - offset
                        break
                self.highlight()
                return True
            body = int(self.model.body_parentid[body])
        return False

    def highlight(self):
        if self._highlighted_selection == self.selected:
            return
        self._highlighted_selection = self.selected
        self.model.geom_rgba[:] = self.original_rgba
        self.model.geom_matid[:] = self.original_material
        selected_body = int(self.model.jnt_bodyid[self.joints[self.selected]])
        for geom in range(self.model.ngeom):
            body = int(self.model.geom_bodyid[geom])
            while body > 0 and body not in self.body_to_selection:
                body = int(self.model.body_parentid[body])
            if body == selected_body:
                self.model.geom_rgba[geom] = [0.1, 1., 0.2, 1.]
                self.model.geom_matid[geom] = -1

    @property
    def selected(self):
        return self.index + self.offsets[self.side]

    def set_target(self, degrees):
        if not np.isfinite(degrees):
            raise ValueError('Angle must be finite')
        i = self.selected
        joint = self.joints[i]
        lo, hi = self.model.jnt_range[joint]
        self.targets[i] = np.clip(np.deg2rad(degrees), lo, hi)
        self.home_hold = False

    def command(self, key):
        if key in ('1', '2', '3', '4', '5'):
            self.side = ('left', 'right', 'left_leg', 'right_leg', 'waist')[int(key)-1]
            self.index = min(self.index, len(self.groups[self.side])-1)
        elif key in ('Left', 'Right'):
            self.index = (self.index + (1 if key == 'Right' else -1)) % len(self.groups[self.side])
        elif key in ('Up', 'Down'):
            self.set_target(np.rad2deg(self.targets[self.selected]) + self.step_degrees * (1 if key == 'Up' else -1))
        elif key.lower() == 'h':
            self.home_all()

    def home_all(self):
        """Reset robot state in this standalone simulation; preserve object poses."""
        self.targets[:] = self.home[self.qa]
        self.home_hold = True
        self.setpoints[:] = self.targets
        self.data.qpos[self.robot_q] = self.home[self.robot_q]
        self.data.qvel[self.robot_v] = 0.
        self.data.qacc[self.robot_v] = 0.
        self.data.qacc_warmstart[:] = 0.
        self.data.qfrc_applied[self.robot_v] = 0.
        bodies = np.unique(self.model.dof_bodyid[self.robot_v])
        self.data.xfrc_applied[bodies] = 0.
        self.data.ctrl[:] = 0.
        mujoco.mj_forward(self.model, self.data)

    def step(self):
        m, d = self.model, self.data
        d.qpos[self.lock_q] = self.home[self.lock_q]
        d.qvel[self.lock_v] = 0.
        d.qacc_warmstart[self.lock_v] = 0.
        mujoco.mj_forward(m, d)
        # Slew manual targets at 30 degrees/second; Home resets state directly.
        delta = np.deg2rad(30.) * m.opt.timestep
        self.setpoints += np.clip(self.targets - self.setpoints, -delta, delta)
        tau = self.kp * (self.setpoints - d.qpos[self.qa]) - self.kd * d.qvel[self.va] + d.qfrc_bias[self.va]
        d.ctrl[:] = 0.
        limits = m.actuator_ctrlrange[self.actuators]
        d.ctrl[self.actuators] = np.clip(tau, limits[:, 0], limits[:, 1])
        mujoco.mj_step(m, d)
        d.qpos[self.lock_q] = self.home[self.lock_q]
        d.qvel[self.lock_v] = 0.
        if self.home_hold:
            d.qpos[self.robot_q] = self.home[self.robot_q]
            d.qvel[self.robot_v] = 0.
            d.qacc_warmstart[self.robot_v] = 0.
        mujoco.mj_forward(m, d)



class PickingViewer:
    """Single-click picking on a GLFW viewer owned by the Tk/main thread."""
    def __init__(self, control, key_callback):
        self.control = control
        if not glfw.init():
            raise RuntimeError('Cannot initialize GLFW display')
        self.window = glfw.create_window(1000, 800, 'Dex3 - Click a link, Up/Down to move', None, None)
        if not self.window:
            glfw.terminate()
            raise RuntimeError('Cannot open MuJoCo window')
        glfw.make_context_current(self.window)
        glfw.swap_interval(0)
        self.cam = mujoco.MjvCamera()
        self.opt = mujoco.MjvOption()
        self.scene = mujoco.MjvScene(control.model, maxgeom=10000)
        # Shadows/reflections multiply rendering work over the detailed hand
        # meshes, particularly through WSLg. They do not affect physics/picking.
        for flag in ('mjRND_SHADOW', 'mjRND_REFLECTION', 'mjRND_SKYBOX', 'mjRND_FOG'):
            self.scene.flags[getattr(mujoco.mjtRndFlag, flag)] = 0
        self.context = mujoco.MjrContext(control.model, mujoco.mjtFontScale.mjFONTSCALE_100)
        self.mouse = (0., 0.)
        self.press = None
        glfw.set_key_callback(self.window, lambda w, k, sc, action, mods:
                              key_callback(k) if action in (glfw.PRESS, glfw.REPEAT) else None)
        glfw.set_mouse_button_callback(self.window, self.button)
        glfw.set_cursor_pos_callback(self.window, self.motion)
        glfw.set_scroll_callback(self.window, self.scroll)

    def scroll(self, window, x, y):
        mujoco.mjv_moveCamera(self.control.model, mujoco.mjtMouse.mjMOUSE_ZOOM,
                             0., -.05*y, self.cam)

    def button(self, window, button, action, mods):
        x, y = glfw.get_cursor_pos(window)
        self.mouse = (x, y)
        if button == glfw.MOUSE_BUTTON_LEFT:
            if action == glfw.PRESS:
                self.press = (x, y)
            elif self.press is not None:
                if np.hypot(x-self.press[0], y-self.press[1]) < 5:
                    width, height = glfw.get_window_size(window)
                    fw, fh = glfw.get_framebuffer_size(window)
                    if min(width, height, fw, fh) > 0:
                        point = np.zeros(3)
                        ids = [np.zeros(1, dtype=np.int32) for _ in range(3)]
                        body = mujoco.mjv_select(self.control.model, self.control.data, self.opt,
                            fw/fh, x/width, 1-y/height, self.scene, point, *ids)
                        if self.control.select_body(body):
                            self.on_pick()
                self.press = None

    def motion(self, window, x, y):
        dx, dy = x-self.mouse[0], y-self.mouse[1]
        self.mouse = (x, y)
        height = max(1, glfw.get_window_size(window)[1])
        if glfw.get_mouse_button(window, glfw.MOUSE_BUTTON_RIGHT) == glfw.PRESS:
            mujoco.mjv_moveCamera(self.control.model, mujoco.mjtMouse.mjMOUSE_ROTATE_V,
                                 dx/height, dy/height, self.cam)
        elif glfw.get_mouse_button(window, glfw.MOUSE_BUTTON_MIDDLE) == glfw.PRESS:
            mujoco.mjv_moveCamera(self.control.model, mujoco.mjtMouse.mjMOUSE_MOVE_V,
                                 dx/height, dy/height, self.cam)

    def on_pick(self):
        pass

    def is_running(self):
        glfw.poll_events()
        return self.window is not None and not glfw.window_should_close(self.window)

    def sync(self):
        glfw.make_context_current(self.window)
        w, h = glfw.get_framebuffer_size(self.window)
        if min(w, h) <= 0:
            return
        self.control.highlight()
        mujoco.mjv_updateScene(self.control.model, self.control.data, self.opt, None,
                              self.cam, mujoco.mjtCatBit.mjCAT_ALL, self.scene)
        rect = mujoco.MjrRect(0, 0, w, h)
        mujoco.mjr_render(rect, self.scene, self.context)
        joint = self.control.model.joint(int(self.control.joints[self.control.selected])).name
        mujoco.mjr_overlay(mujoco.mjtFont.mjFONT_NORMAL, mujoco.mjtGridPos.mjGRID_TOPLEFT,
            rect, 'SELECTED: '+joint+'\nLeft click: select | Up/Down: angle\nRight drag: rotate | Wheel: zoom | Middle drag: pan', '', self.context)
        glfw.swap_buffers(self.window)

    def close(self):
        if self.window is not None:
            glfw.make_context_current(self.window)
            self.context.free()
            glfw.destroy_window(self.window)
            self.window = None
            glfw.terminate()


def main():
    control = ManualJoints()
    root = tk.Tk()
    root.title('G1 Dex3 - Manual Joint Control (simulation only)')
    root.geometry('780x660')
    events = queue.Queue(maxsize=256)
    stopped = False
    def send(key):
        try:
            events.put_nowait(key)
        except queue.Full:
            pass
    keys = {49: '1', 50: '2', 51: '3', 52: '4', 53: '5', 265: 'Up', 264: 'Down', 263: 'Left', 262: 'Right', 72: 'h', 256: 'Escape'}
    def viewer_key(code):
        if code in keys:
            send(keys[code])
    viewer = PickingViewer(control, viewer_key)
    viewer.cam.lookat[:] = [.25, 0., .85]
    viewer.cam.distance = 2.
    viewer.cam.azimuth = 135
    viewer.cam.elevation = -20
    frame = ttk.Frame(root, padding=12)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text='MANUAL MODE | Dex3 | Floating base locked | All 43 joints adjustable', font=('', 13, 'bold')).pack(anchor='w')
    ttk.Label(frame, text='No policy server needed. This panel controls its own MuJoCo simulation.').pack(anchor='w')
    bar = ttk.Frame(frame); bar.pack(fill='x', pady=10)
    for label, key in [('1  Left arm + hand', '1'), ('2  Right arm + hand', '2'), ('3  Left leg', '3'), ('4  Right leg', '4'), ('5  Waist', '5'), ('H  Home all', 'h'), ('Esc  Stop', 'Escape')]:
        ttk.Button(bar, text=label, command=lambda k=key: send(k)).grid(row=(int(key)-1 if key.isdigit() else (5 if key == 'h' else 6))//4, column=(int(key)-1 if key.isdigit() else (5 if key == 'h' else 6))%4, sticky='w')
    tree = ttk.Treeview(frame, columns=('joint', 'actual', 'target', 'range'), show='headings', height=14, selectmode='browse')
    for column, title, width in [('joint', 'Joint', 275), ('actual', 'Actual (deg)', 105), ('target', 'Target (deg)', 105), ('range', 'Limits (deg)', 145)]:
        tree.heading(column, text=title); tree.column(column, width=width)
    tree.pack(fill='both', expand=True)
    status = tk.StringVar(); error = tk.StringVar()
    ttk.Label(frame, textvariable=status).pack(anchor='w', pady=7)
    row = ttk.Frame(frame); row.pack(fill='x')
    step = tk.StringVar(value='2'); target = tk.StringVar(value='0')
    ttk.Label(row, text='Step (deg):').pack(side='left')
    step_box = ttk.Spinbox(row, from_=.1, to=10, increment=.5, textvariable=step, width=6)
    step_box.pack(side='left', padx=4)
    ttk.Label(row, text='Target (deg):').pack(side='left')
    target_box = ttk.Entry(row, textvariable=target, width=9); target_box.pack(side='left', padx=4)
    def apply():
        try:
            control.set_target(float(target.get())); error.set('')
        except ValueError:
            error.set('Enter a finite numeric angle; targets are clamped to joint limits.')
    ttk.Button(row, text='Apply target', command=apply).pack(side='left')
    target_box.bind('<Return>', lambda e: apply())
    nav = ttk.Frame(frame); nav.pack(fill='x', pady=8)
    for label, key in [('Previous joint  [Left]', 'Left'), ('Next joint  [Right]', 'Right'), ('Increase  [Up]', 'Up'), ('Decrease  [Down]', 'Down')]:
        ttk.Button(nav, text=label, command=lambda k=key: send(k)).pack(side='left', padx=3)
    ttk.Label(frame, textvariable=error, foreground='red').pack(anchor='w')
    ttk.Label(frame, text='Click a robot link to select it (green), then Up/Down. Right drag rotates; wheel zooms.\nH resets all robot joints immediately; it does not reset the bottle. Esc closes both windows.').pack(anchor='w')
    def picked():
        target.set(f'{np.rad2deg(control.targets[control.selected]):.2f}')
        root.focus_set()
    viewer.on_pick = picked
    def select(event):
        values = tree.selection()
        if values:
            if int(values[0]) < len(control.groups[control.side]):
                control.index = int(values[0])
                control.highlight()
    tree.bind('<<TreeviewSelect>>', select)
    def keypress(event):
        if event.keysym == 'Escape':
            send('Escape'); return 'break'
        if isinstance(root.focus_get(), (ttk.Entry, ttk.Spinbox)):
            return
        if event.keysym in ('1', '2', '3', '4', '5', 'Up', 'Down', 'Left', 'Right', 'h', 'H'):
            send(event.keysym); return 'break'
    root.bind('<KeyPress>', keypress)
    def close():
        nonlocal stopped
        if stopped:
            return
        stopped = True
        viewer.close()
        root.destroy()
    root.protocol('WM_DELETE_WINDOW', close)
    last_time = time.monotonic(); last_ui = 0.; last_render = 0.; budget = 0.
    displayed_rows = {}
    def tick():
        nonlocal last_time, last_ui, last_render, budget
        if stopped:
            return
        if not viewer.is_running():
            close(); return
        now = time.monotonic(); budget = min(budget + now-last_time, .04); last_time = now
        try:
            value = float(step.get())
            if not np.isfinite(value) or not .1 <= value <= 10:
                raise ValueError
            control.step_degrees = value
            valid_step = True
        except ValueError:
            valid_step = False
        while not events.empty():
            key = events.get_nowait()
            if key == 'Escape':
                close(); return
            if key in ('Up', 'Down') and not valid_step:
                error.set('Step must be between 0.1 and 10 degrees.'); continue
            control.command(key)
        physics_deadline = time.perf_counter() + .004
        while budget >= control.model.opt.timestep:
            control.step(); budget -= control.model.opt.timestep
            if time.perf_counter() >= physics_deadline:
                break
        if now-last_ui >= .1:
            for row_id in tree.get_children():
                if int(row_id) >= len(control.groups[control.side]):
                    tree.delete(row_id)
                    displayed_rows.pop(int(row_id), None)
            for i, joint in enumerate(control.groups[control.side]):
                j = control.model.joint(joint)
                k = i + control.offsets[control.side]
                lo, hi = np.rad2deg(control.model.jnt_range[joint])
                values = (j.name, f'{np.rad2deg(control.data.qpos[j.qposadr[0]]):.2f}', f'{np.rad2deg(control.targets[k]):.2f}', f'{lo:.1f} .. {hi:.1f}')
                if displayed_rows.get(i) != values:
                    if tree.exists(str(i)):tree.item(str(i), values=values)
                    else:tree.insert('', 'end', iid=str(i), values=values)
                    displayed_rows[i] = values
            selected_row = str(control.index)
            if tree.selection() != (selected_row,):
                tree.selection_set(selected_row)
                tree.see(selected_row)
            status.set(f'{control.side.upper()} | {control.index+1}/{len(control.groups[control.side])} | {control.model.joint(int(control.joints[control.selected])).name}')
            last_ui = now
        if now-last_render >= 1/30:
            viewer.sync()
            last_render = time.monotonic()
        root.after(8, tick)
    root.after(0, tick)
    try:
        root.mainloop()
    finally:
        if not stopped:
            close()


if __name__ == '__main__':
    main()
