"""Fixed grasp-region centre and independent world-X/world-Y grasp gates."""

import mujoco
import numpy as np


def cylinder_y_surface_gap(point, centre, rotation, radius, half_height):
    """Signed world-Y clearance at this point's X/Z; None outside the profile.

    Intersect a line parallel to world Y with the finite cylinder. This measures
    only Y clearance, rather than Euclidean distance or centre-to-centre Y.
    """
    local = rotation.T @ (np.asarray(point) - centre)
    direction = rotation.T @ np.array([0., 1., 0.])
    a = float(direction[:2] @ direction[:2])
    b = float(2. * (local[:2] @ direction[:2]))
    c = float(local[:2] @ local[:2] - radius ** 2)
    if a > 1e-12:
        discriminant = b * b - 4. * a * c
        if discriminant < -1e-12:
            return None
        root = np.sqrt(max(discriminant, 0.))
        low, high = (-b - root) / (2. * a), (-b + root) / (2. * a)
    elif c <= 1e-12:
        low, high = -np.inf, np.inf
    else:
        return None
    if abs(direction[2]) > 1e-12:
        ends = sorted(((-half_height - local[2]) / direction[2],
                       (half_height - local[2]) / direction[2]))
        low, high = max(low, ends[0]), min(high, ends[1])
    elif abs(local[2]) > half_height + 1e-12:
        return None
    if low > high + 1e-12:
        return None
    return float(max(low, -high))


class HandGraspAlignment:
    def __init__(self, model):
        # The palm inertia is fused into the wrist-yaw body in this MJCF.
        # Its descendants are all finger links; wrist pitch/roll and forearm
        # are ancestors and must not contribute to the whole-hand COM.
        self.root = model.body("right_wrist_yaw_link").id
        bodies = [self.root]
        for body in range(self.root + 1, model.nbody):
            if int(model.body_parentid[body]) in bodies:
                bodies.append(body)
        self.bodies = np.asarray(bodies, dtype=int)
        self.masses = model.body_mass[self.bodies].copy()
        self.mass = float(self.masses.sum())
        if not np.isfinite(self.mass) or self.mass <= 0.:
            raise ValueError("Whole hand must have positive finite mass")
        self.grasp_site = model.site("right_hand_grasp_center").id
        if model.site_bodyid[self.grasp_site] != self.root:
            raise ValueError("Grasp centre must attach to the wrist/palm, not a finger")
        self.grasp_local = model.site_pos[self.grasp_site].copy()
        self.bottle = model.geom("red_bottle_body").id
        if model.geom_type[self.bottle] != mujoco.mjtGeom.mjGEOM_CYLINDER:
            raise ValueError("Hand alignment expects the cylindrical bottle body")
        self.radius, self.half_height = model.geom_size[self.bottle, :2]

    def measure(self, data):
        # Finger flexion must not move the reference used to start closing.
        # Keep the physical COM as a separate diagnostic only.
        hand = data.site_xpos[self.grasp_site]
        hand_com = np.average(data.xipos[self.bodies], axis=0, weights=self.masses)
        centre = data.geom_xpos[self.bottle]
        rotation = data.geom_xmat[self.bottle].reshape(3, 3)
        gap = cylinder_y_surface_gap(hand, centre, rotation, self.radius, self.half_height)
        tilt = float(np.degrees(np.arccos(np.clip(rotation[2, 2], -1., 1.))))
        return {"grasp_center_world_m": hand.tolist(),
                "grasp_center_wrist_local_m": self.grasp_local.tolist(),
                "whole_hand_com_world_m": hand_com.tolist(), "hand_mass_kg": self.mass,
                "bottle_body_center_world_m": centre.tolist(),
                "x_error_m": float(hand[0] - centre[0]),
                "y_center_offset_m": float(hand[1] - centre[1]),
                "y_surface_gap_m": gap, "bottle_tilt_deg": tilt,
                "distance_source": "MuJoCo fixed grasp-region centre: X alignment and Y surface gap"}
