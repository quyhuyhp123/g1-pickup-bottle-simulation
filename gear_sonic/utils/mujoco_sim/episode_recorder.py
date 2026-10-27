"""Raw assisted demonstrations. Never invent SONIC token labels.

One sample per physics step, sampled RGB rendered from the SAME pre-step state.
Chunks bound memory use; PNGs are authoritative, MP4 is a review artifact.
"""
import json
import time
import uuid
import tempfile
from pathlib import Path

import mujoco
import numpy as np


class EpisodeRecorder:
    def __init__(self, model, root, prompt, fps=10, camera='head_camera', renderer=None):
        if not 0 < fps <= 60:
            raise ValueError('Recording FPS must be in (0, 60]')
        if model.camera(camera).id < 0:
            raise ValueError('Recording camera not found')
        self.model, self.root = model, Path(root)
        self.prompt, self.fps, self.camera = prompt, fps, camera
        self.renderer = renderer
        self.path = None
        self.rows = []

    def prepare(self, data):
        """Compile/upload render resources before controller start, not in capture."""
        if self.renderer is None:
            self.renderer = mujoco.Renderer(self.model, height=480, width=640)
        self.renderer.update_scene(data, camera=self.camera)
        self.renderer.render()
        with tempfile.TemporaryDirectory() as directory:
            snapshot = Path(directory) / 'model.xml'
            mujoco.mj_saveLastXML(str(snapshot), self.model)
            self.model_xml = snapshot.read_text()

    def _metadata(self):
        (self.path / 'meta.json').write_text(json.dumps(self.meta, indent=2))

    def start(self, data):
        self.path = self.root / (time.strftime('episode_%Y%m%d_%H%M%S_') + uuid.uuid4().hex[:8])
        self.path.mkdir(parents=True, exist_ok=False)
        (self.path / 'rgb').mkdir()
        np.savez_compressed(self.path / 'initial_state.npz', qpos=data.qpos.copy(), qvel=data.qvel.copy(),
            act=data.act.copy(), qacc_warmstart=data.qacc_warmstart.copy(),
            mocap_pos=data.mocap_pos.copy(), mocap_quat=data.mocap_quat.copy(),
            eq_active=data.eq_active.copy(), sim_time=np.array(data.time))
        if hasattr(self, 'model_xml'):
            (self.path / 'model.xml').write_text(self.model_xml)
        else:
            mujoco.mj_saveLastXML(str(self.path / 'model.xml'), self.model)
        self.count, self.chunk, self.frame_count = 0, 0, 0
        self.next_image = float(data.time)
        self.meta = dict(format='mujoco_assisted_raw_v1', status='recording', outcome='unreviewed',
            prompt=self.prompt, camera=self.camera, image_size=[640, 480], fps_requested=self.fps,
            timestep=float(self.model.opt.timestep), mujoco_version=mujoco.__version__,
            action_semantics='ctrl is actual clipped actuator command applied from this pre-step state',
            sonic_tokens_available=False, training_ready=False,
            joints=[self.model.joint(i).name for i in range(self.model.njnt)],
            jnt_qposadr=self.model.jnt_qposadr.tolist(), jnt_dofadr=self.model.jnt_dofadr.tolist(),
            actuator_trnid=self.model.actuator_trnid.tolist(),
            camera_fovy=float(self.model.cam_fovy[self.model.camera(self.camera).id]),
            model_note='XML snapshot may reference original mesh assets; retain repository assets',
            samples=0, frames=0)
        self._metadata()
        print(f'[Recorder] START {self.path}', flush=True)

    def capture(self, data, active, scene_version, assisted=None):
        if self.path is not None and (not active or scene_version != self.scene_version):
            self.finish('standby_or_scene_change')
        if not active:
            return
        if self.path is None:
            self.scene_version = scene_version
            self.start(data)
        # Recompute kinematics for the exact qpos copied below, not stale xpos.
        mujoco.mj_forward(self.model, data)
        frame_id = -1
        if float(data.time) + 1e-9 >= self.next_image:
            import cv2
            if self.renderer is None:
                self.renderer = mujoco.Renderer(self.model, height=480, width=640)
            self.renderer.update_scene(data, camera=self.camera)
            rgb = self.renderer.render()
            frame_id = self.frame_count
            if not cv2.imwrite(str(self.path / 'rgb' / f'{frame_id:06d}.png'), rgb[:, :, ::-1]):
                raise OSError('Could not write camera frame')
            self.frame_count += 1
            self.next_image = float(data.time) + 1/self.fps
        cam = self.model.camera(self.camera).id
        row = dict(sim_time=np.array(data.time), qpos=data.qpos.copy(), qvel=data.qvel.copy(),
            ctrl=data.ctrl.copy(), frame_id=np.array(frame_id),
            camera_xpos=data.cam_xpos[cam].copy(), camera_xmat=data.cam_xmat[cam].copy(),
            qfrc_applied=data.qfrc_applied.copy(), xfrc_applied=data.xfrc_applied.copy(),
            stage=np.array(getattr(assisted, 'stage', 'unknown')),
            assisted_arm_target=np.asarray(getattr(assisted, 'arm_target', data.qpos[getattr(assisted, 'arm_q', [])]), dtype=float).copy(),
            assisted_hand_target=np.asarray(getattr(assisted, 'hand_target', data.qpos[getattr(assisted, 'hand_q', [])]), dtype=float).copy())
        if assisted is not None:
            self.meta['assisted_arm_joint_ids'] = assisted.arm.tolist()
            self.meta['assisted_hand_joint_ids'] = assisted.hand.tolist()
            self.meta['controller_success_latest'] = bool(assisted.success)
            self.meta['controller_stage_latest'] = assisted.stage
        # Full qpos includes bottle pose; it is diagnostic ground truth, not VLA input.
        self.rows.append(row)
        self.count += 1
        if len(self.rows) >= 200:
            self.flush()

    def flush(self):
        if not self.rows:
            return
        np.savez_compressed(self.path / f'states_{self.chunk:06d}.npz',
                            **{k: np.stack([r[k] for r in self.rows]) for k in self.rows[0]})
        self.rows.clear()
        self.chunk += 1
        self.meta.update(samples=self.count, frames=self.frame_count)
        self._metadata()

    def finish(self, reason):
        if self.path is None:
            return
        self.flush()
        self.meta.update(status='complete', end_reason=reason, samples=self.count, frames=self.frame_count)
        self._metadata()
        print(f'[Recorder] SAVED {self.path} ({self.count} steps, {self.frame_count} images)', flush=True)
        self.path = None

    def close(self):
        self.finish('simulator_closed')
        if self.renderer is not None:
            self.renderer.close()
            self.renderer = None
