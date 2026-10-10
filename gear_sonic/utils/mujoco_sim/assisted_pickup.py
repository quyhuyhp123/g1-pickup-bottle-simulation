"""Opt-in visual pickup correction for the simulated right arm and Dex3 hand.

SONIC retains the floating base, legs and left arm. This controller only
sets joint torques; it never attaches, teleports or applies a force to the bottle.
Target XY comes from RGB-D recognition plus the known bottle radius/table height.
MuJoCo object pose/contact is used only to measure the outcome.
"""

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation
from scipy.optimize import least_squares


def visual_bottle_center(detection, radius, centre_height):
    if detection.get("status") != "detected":
        return None
    point = np.asarray(detection.get("world_point_m"), dtype=float)
    camera = np.asarray(detection.get("camera_position_world_m"), dtype=float)
    if point.shape != (3,) or camera.shape != (3,) or not np.isfinite([point, camera]).all():
        return None
    # A box-centre depth point lies on the near cylindrical surface. Correct
    # horizontally to its axis; Z comes from the known tabletop and bottle size.
    if not centre_height - .07 < point[2] < centre_height + .095:
        return None
    direction = point[:2] - camera[:2]
    length = np.linalg.norm(direction)
    if length < .05:
        return None
    return np.r_[point[:2] + radius * direction / length, centre_height]


class AssistedPickup:
    def __init__(self, model):
        self.model = m = model
        self.arm = np.array([m.joint('waist_pitch_joint').id] + [m.joint('right_' + name + '_joint').id for name in
            ('shoulder_pitch', 'shoulder_roll', 'shoulder_yaw', 'elbow',
             'wrist_roll', 'wrist_pitch', 'wrist_yaw')])
        self.hand = np.array([m.joint('right_hand_' + name + '_joint').id for name in
            ('thumb_0', 'thumb_1', 'thumb_2', 'middle_0', 'middle_1', 'index_0', 'index_1')])
        self.arm_q, self.arm_v = m.jnt_qposadr[self.arm], m.jnt_dofadr[self.arm]
        self.hand_q, self.hand_v = m.jnt_qposadr[self.hand], m.jnt_dofadr[self.hand]
        self.site = m.site('right_hand_grasp_center').id
        self.wrist = m.body('right_wrist_yaw_link').id
        self.bottle = m.body('red_bottle').id
        self.geom = m.geom('red_bottle_body').id
        self.radius, self.half_height = m.geom_size[self.geom, :2]
        self.centre_height = float(m.body_pos[self.bottle, 2])
        self.scratch = mujoco.MjData(m)
        self.jp, self.jr = np.zeros((3, m.nv)), np.zeros((3, m.nv))
        self.closed = np.array([0., -.7, -.7, 1., 1.5, 1., 1.5])
        self.lower = m.jnt_range[self.arm, 0].copy() + .002
        self.upper = m.jnt_range[self.arm, 1].copy() - .002
        # Keep the right upper arm outside the torso. The redundant 8-DOF IK
        # otherwise changes elbow branches for millimetre-scale RGB-D noise.
        self.lower[0], self.upper[0] = 0., min(self.upper[0], .5)
        self.upper[2] = min(self.upper[2], -.05)
        self.lower[3], self.upper[3] = max(self.lower[3], -.6), min(self.upper[3], .6)
        self.reset()

    def reset(self):
        self.active = False
        self.stage = 'idle'
        self.error = ''
        self.target = None
        self.samples = []
        self.last_capture = None
        self.last_update = -np.inf
        self.success = False
        self.min_hold_lift = None
        self.hold_contacts = True
        self.contacts = []
        self.position_error = None
        self.orientation_error = None
        self.fraction = 0.
        self.placed = False
        self.place_xy = None

    def lower_to_table(self, data, xy=None):
        if not self.active or self.stage != 'success':
            return False
        from .object_reset import BottlePlacement
        destination = BottlePlacement(self.model, data).validate(self.target[:2] if xy is None else xy)
        shift = np.r_[destination - self.target[:2], 0.]
        self.place_low_q = self.table_arm_q.copy()
        self.place_high_q = self.arm_target.copy()
        if np.linalg.norm(shift) > .001:
            # Solve both endpoints before moving; reject unreachable destinations.
            targets = []
            for endpoint, seed in enumerate((self.table_arm_q, self.arm_target)):
                scratch = self.scratch
                scratch.qpos[:] = data.qpos
                scratch.qpos[self.arm_q] = seed
                mujoco.mj_kinematics(self.model, scratch)
                position = scratch.site_xpos[self.site].copy() + shift
                if endpoint == 0:
                    position[2] -= .006  # Contact stops descent before this small support margin.
                rotation = scratch.xmat[self.wrist].reshape(3, 3).copy()
                def residual(q):
                    scratch.qpos[self.arm_q] = q
                    mujoco.mj_kinematics(self.model, scratch)
                    angular = Rotation.from_matrix(rotation @ scratch.xmat[self.wrist].reshape(3, 3).T).as_rotvec()
                    return np.r_[scratch.site_xpos[self.site] - position, .15*angular, .002*(q-seed)]
                result = least_squares(residual, seed, bounds=(self.lower, self.upper), max_nfev=150)
                if np.linalg.norm(residual(result.x)[:6]) > .005:
                    raise ValueError('Place destination outside arm workspace; choose a closer X/Y.')
                targets.append(result.x)
            self.place_low_q, self.place_high_q = targets
        self.support_probe = None
        self.place_xy = destination
        self.lower_start_q = self.arm_target.copy()
        self.set_stage('transfer' if np.linalg.norm(shift) > .001 else 'lower', data.time)
        return True

    def table_support(self, data):
        for contact_id, contact in enumerate(data.contact):
            geoms = [int(contact.geom1), int(contact.geom2)]
            if self.geom in geoms:
                other = geoms[1] if geoms[0] == self.geom else geoms[0]
                if self.model.geom(other).name == 'pickup_table_top':
                    force = np.zeros(6)
                    mujoco.mj_contactForce(self.model, data, contact_id, force)
                    if force[0] > .05:
                        return True
        return False

    def start(self, data):
        self.reset()
        self.active = True
        self.arm_target = data.qpos[self.arm_q].copy()
        self.home_arm_q = self.arm_target.copy()
        self.hand_target = np.zeros(7)
        self.start_pos = data.site_xpos[self.site].copy()
        self.start_rot = data.xmat[self.wrist].reshape(3, 3).copy()
        self.set_stage('detecting', data.time)

    def set_stage(self, stage, now):
        self.stage, self.stage_since = stage, float(now)
        print(f'[Assisted pickup] {stage}', flush=True)

    def finger_contacts(self, data):
        names = set()
        for contact in data.contact:
            a, b = self.model.geom_bodyid[[contact.geom1, contact.geom2]]
            if a == self.bottle or b == self.bottle:
                name = self.model.body(int(b if a == self.bottle else a)).name
                if name.startswith('right_hand_'):
                    names.add(name)
        return sorted(names)

    def solve(self, data, position, rotation):
        m, scratch = self.model, self.scratch
        scratch.qpos[:] = data.qpos
        scratch.qpos[self.arm_q] = self.arm_target
        for _ in range(8):
            mujoco.mj_kinematics(m, scratch)
            mujoco.mj_comPos(m, scratch)
            linear = position - scratch.site_xpos[self.site]
            angular = Rotation.from_matrix(rotation @ scratch.xmat[self.wrist].reshape(3, 3).T).as_rotvec()
            if np.linalg.norm(linear) < .001 and np.linalg.norm(angular) < .015:
                break
            mujoco.mj_jacSite(m, scratch, self.jp, self.jr, self.site)
            jac = np.vstack((self.jp[:, self.arm_v], .15 * self.jr[:, self.arm_v]))
            error = np.r_[linear, .15 * angular]
            delta = jac.T @ np.linalg.solve(jac @ jac.T + .00002 * np.eye(6), error)
            scratch.qpos[self.arm_q] = np.clip(scratch.qpos[self.arm_q] + np.clip(delta, -.12, .12),
                self.lower, self.upper)
        # Bound commanded joint velocity even if a new IK branch is selected.
        self.arm_target += np.clip(scratch.qpos[self.arm_q] - self.arm_target, -.025, .025)
        self.position_error = float(np.linalg.norm(data.site_xpos[self.site] - position))
        self.orientation_error = float(np.linalg.norm(Rotation.from_matrix(
            rotation @ data.xmat[self.wrist].reshape(3, 3).T).as_rotvec()))

    def plan_pregrasp(self, data):
        """Choose a feasible IK branch before leaving the retracted home pose."""
        m, scratch = self.model, self.scratch
        scratch.qpos[:] = data.qpos
        lower, upper = self.lower, self.upper
        seed = np.array([.3, 0., -.2, 0., .8, 0., 0., 0.])
        def residual(q):
            scratch.qpos[self.arm_q] = q
            mujoco.mj_kinematics(m, scratch)
            rotation = Rotation.from_matrix(scratch.xmat[self.wrist].reshape(3, 3)).as_rotvec()
            return np.r_[scratch.site_xpos[self.site] - self.pregrasp, .15 * rotation, .003 * (q - seed)]
        result = least_squares(residual, np.clip(seed, lower, upper), bounds=(lower, upper), max_nfev=150)
        if np.linalg.norm(residual(result.x)[:6]) > .006:
            self.error = 'Visual bottle target outside the arm workspace. Move bottle closer and Reset.'
            self.set_stage('failed', data.time)
            return False
        self.approach_start_q = data.qpos[self.arm_q].copy()
        self.pregrasp_q = result.x
        return True

    def update(self, data, detection):
        if not self.active or data.time - self.last_update < .019:
            return
        self.last_update = float(data.time)
        elapsed = data.time - self.stage_since
        self.contacts = self.finger_contacts(data)
        opposed = (any('thumb' in name for name in self.contacts)
                   and any('index' in name or 'middle' in name for name in self.contacts))
        if self.stage == 'detecting':
            captured = detection.get('capture_monotonic')
            centre = visual_bottle_center(detection, self.radius, self.centre_height)
            if centre is not None and captured != self.last_capture:
                self.samples.append(centre)
                self.last_capture = captured
            if len(self.samples) >= 3:
                sample = np.array(self.samples[-3:])
                if np.max(np.ptp(sample[:, :2], axis=0)) < .015:
                    self.target = np.median(sample, axis=0)
                    self.grasp = self.target + [0., 0., .04]
                    self.pregrasp = self.grasp + [-self.radius - .02, 0., 0.]
                    self.start_pos = data.site_xpos[self.site].copy()
                    self.start_rot = data.xmat[self.wrist].reshape(3, 3).copy()
                    if self.plan_pregrasp(data):
                        self.set_stage('approach', data.time)
            if elapsed > 15:
                self.error = 'No stable RGB-D bottle target. Reset and retry.'
                self.set_stage('failed', data.time)
            return
        if self.stage == 'failed':
            return
        position, rotation = self.pregrasp.copy(), np.eye(3)
        if self.stage == 'approach':
            t = np.clip(elapsed / 3., 0., 1.)
            blend = t*t*(3.-2.*t)
            position = self.start_pos + blend * (self.pregrasp - self.start_pos)
            rotation = Rotation.from_rotvec((1.-blend) * Rotation.from_matrix(self.start_rot).as_rotvec()).as_matrix()
            self.arm_target = self.approach_start_q + blend * (self.pregrasp_q - self.approach_start_q)
            self.position_error = float(np.linalg.norm(data.site_xpos[self.site] - self.pregrasp))
            self.orientation_error = float(np.linalg.norm(Rotation.from_matrix(data.xmat[self.wrist].reshape(3, 3)).as_rotvec()))
            if elapsed > 3. and self.position_error is not None and self.position_error < .012 and self.orientation_error < .08:
                self.set_stage('close', data.time)
            elif elapsed > 10:
                self.error = 'Arm could not reach the visual pregrasp target.'
                self.set_stage('failed', data.time)
            return
        elif self.stage == 'close':
            advance = np.clip(elapsed / 1.5, 0., 1.)
            advance = advance*advance*(3.-2.*advance)
            position = self.pregrasp + advance * (self.grasp - self.pregrasp)
            # Begin a small closure at the 2 cm surface gap, then complete it
            # once the bottle is inside the grasp region. Closing fully while
            # still advancing makes the index finger sweep the bottle away.
            self.fraction = float(.05 * advance + .95 * np.clip((elapsed - 1.5) / 1.5, 0., 1.))
            self.hand_target = self.closed * self.fraction
            if elapsed > 3.5 and opposed:
                self.table_arm_q = self.arm_target.copy()
                self.set_stage('lift', data.time)
            elif elapsed > 5:
                self.error = 'No opposed finger contacts; lift cancelled. Reset to retry.'
                self.set_stage('failed', data.time)
        elif self.stage == 'transfer':
            t = np.clip(elapsed / 4., 0., 1.)
            self.arm_target = self.lower_start_q + t*t*(3.-2.*t)*(self.place_high_q-self.lower_start_q)
            if elapsed > 5.:
                self.lower_start_q = self.arm_target.copy()
                self.set_stage('lower', data.time)
            return
        elif self.stage in ('lower', 'release', 'placed'):
            if self.stage == 'lower':
                t = np.clip(elapsed / 5., 0., 1.)
                if elapsed <= 5.:
                    self.arm_target = self.lower_start_q + t*t*(3.-2.*t) * (self.place_low_q - self.lower_start_q)
                else:
                    # Small tracking/grasp offsets can leave the bottle just
                    # above the table. Search downward at 3 mm/s, at most 2 cm.
                    if self.support_probe is None:
                        self.scratch.qpos[:] = data.qpos
                        self.scratch.qpos[self.arm_q] = self.place_low_q
                        mujoco.mj_kinematics(self.model, self.scratch)
                        self.support_probe = self.scratch.site_xpos[self.site].copy()
                        self.support_probe_rot = self.scratch.xmat[self.wrist].reshape(3, 3).copy()
                    position = self.support_probe + [0., 0., -min(.02, .003*(elapsed-5.))]
                    self.solve(data, position, self.support_probe_rot)
                if self.table_support(data):
                    self.release_pos = data.site_xpos[self.site].copy()
                    self.release_rot = data.xmat[self.wrist].reshape(3, 3).copy()
                    position = self.release_pos.copy()
                    self.set_stage('release', data.time)
                elif elapsed > 13.:
                    self.error = 'No tabletop support; fingers remain closed. Reset to retry.'
                    self.set_stage('failed', data.time)
                return
            else:
                position = self.release_pos.copy()
                rotation = self.release_rot.copy()
                self.fraction = float(1. - np.clip(elapsed / 2., 0., 1.)) if self.stage == 'release' else 0.
                self.hand_target = self.closed * self.fraction
                if self.stage == 'release' and elapsed > 3.:
                    upright = data.xmat[self.bottle].reshape(3, 3)[2, 2] > .95
                    self.placed = bool(self.table_support(data) and upright
                        and np.linalg.norm(data.xpos[self.bottle, :2] - self.place_xy) < .025)
                    if not self.placed:
                        self.error = 'Bottle did not settle upright within 2.5 cm of the requested destination. Reset to retry.'
                    self.set_stage('retreat' if self.placed else 'failed', data.time)
        elif self.stage == 'retreat':
            t = np.clip(elapsed / 2., 0., 1.)
            position = self.release_pos + np.array([-.09, 0., .025]) * t*t*(3.-2.*t)
            rotation = self.release_rot.copy()
            self.solve(data, position, rotation)
            if elapsed > 3.:
                self.return_start_q = self.arm_target.copy()
                self.set_stage('return_home', data.time)
            return
        elif self.stage in ('return_home', 'complete'):
            t = np.clip(elapsed / 4., 0., 1.) if self.stage == 'return_home' else 1.
            self.arm_target = self.return_start_q + t*t*(3.-2.*t)*(self.home_arm_q-self.return_start_q)
            if self.stage == 'return_home' and elapsed > 5.:
                if np.max(np.abs(data.qpos[self.arm_q]-self.home_arm_q)) < .05:
                    self.set_stage('complete', data.time)
                elif elapsed > 8.:
                    self.error = 'Arm could not return home. Reset to retry.'
                    self.set_stage('failed', data.time)
            return
        elif self.stage in ('lift', 'hold', 'success'):
            t = np.clip(elapsed / 3., 0., 1.) if self.stage == 'lift' else 1.
            position = self.grasp + [0., 0., .20*t*t*(3.-2.*t)]
            if self.stage == 'lift' and elapsed > 3.:
                self.min_hold_lift = np.inf
                self.set_stage('hold', data.time)
                elapsed = 0.
            if self.stage in ('hold', 'success'):
                lift = float(data.xpos[self.bottle, 2] - self.centre_height)
                self.min_hold_lift = min(self.min_hold_lift, lift)
                self.hold_contacts &= opposed
                if self.stage == 'hold' and elapsed > 3.:
                    self.success = bool(self.min_hold_lift > .12 and self.hold_contacts)
                    if not self.success:
                        self.error = 'Bottle was not lifted and held with opposed contacts.'
                    self.set_stage('success' if self.success else 'failed', data.time)
        self.solve(data, position, rotation)

    def apply_torques(self, data, body, hand, body_joint_indices):
        if not self.active:
            return
        indices = [int(np.flatnonzero(body_joint_indices == joint)[0]) for joint in self.arm]
        body[indices] = (80. * (self.arm_target - data.qpos[self.arm_q])
                         - 3. * data.qvel[self.arm_v] + data.qfrc_bias[self.arm_v])
        hand[7:] = (8. * (self.hand_target - data.qpos[self.hand_q])
                    - .2 * data.qvel[self.hand_v] + data.qfrc_bias[self.hand_v])

    def snapshot(self):
        return {'stage': self.stage, 'active': self.active, 'success': self.success, 'placed': self.placed,
                'place_target_xy_m': self.place_xy.tolist() if self.place_xy is not None else None,
                'target_source': 'YOLO RGB-D surface + known radius and tabletop height',
                'target_center_world_m': self.target.tolist() if self.target is not None else None,
                'position_error_m': self.position_error, 'orientation_error_rad': self.orientation_error,
                'finger_contacts': self.contacts, 'closure_fraction': self.fraction,
                'minimum_hold_lift_m': self.min_hold_lift if self.min_hold_lift is not None and np.isfinite(self.min_hold_lift) else None,
                'error': self.error}
