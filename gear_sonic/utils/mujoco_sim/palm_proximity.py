"""Measure palm-centre clearance from the graspable bottle body in MuJoCo."""

import mujoco
import numpy as np


def cylinder_surface_distance(point, radius, half_height):
    """Signed shortest distance from a point to a finite cylinder's surface."""
    point = np.asarray(point, dtype=float)
    radial = np.linalg.norm(point[:2])
    delta = np.array([radial - radius, abs(point[2]) - half_height])
    distance = np.linalg.norm(np.maximum(delta, 0.)) + min(max(delta), 0.)
    return float(distance)


class PalmProximity:
    def __init__(self, model):
        native = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_MESH, "right_base_link") >= 0
        mesh = model.mesh("right_base_link" if native else "right_hand_palm_link").id
        self.palm = next(i for i in range(model.ngeom)
            if model.geom_type[i] == mujoco.mjtGeom.mjGEOM_MESH
            and model.geom_dataid[i] == mesh and (model.geom_contype[i] or model.geom_conaffinity[i]))
        self.bottle = model.geom("red_bottle_body").id
        if model.geom_type[self.bottle] != mujoco.mjtGeom.mjGEOM_CYLINDER:
            raise ValueError("Palm proximity expects the scene's cylindrical bottle body")
        self.radius, self.half_height = model.geom_size[self.bottle, :2]

    def measure(self, data):
        palm = data.geom_xpos[self.palm].copy()
        rotation = data.geom_xmat[self.bottle].reshape(3, 3)
        local = rotation.T @ (palm - data.geom_xpos[self.bottle])
        distance = cylinder_surface_distance(local, self.radius, self.half_height)
        tilt = float(np.degrees(np.arccos(np.clip(rotation[2, 2], -1., 1.))))
        return {"palm_center_world_m": palm.tolist(), "palm_surface_distance_m": distance,
                "bottle_tilt_deg": tilt, "distance_source": "MuJoCo palm centre to bottle-body surface"}
