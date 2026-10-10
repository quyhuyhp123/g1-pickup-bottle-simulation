"""Reset a free object's pose without resetting the robot or simulation clock."""

import mujoco
import numpy as np


def reset_free_object(model, data, joint_name="red_bottle_free_joint", xy=None):
    joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)
    if joint_id < 0:
        return False
    if model.jnt_type[joint_id] != mujoco.mjtJoint.mjJNT_FREE:
        raise ValueError(f"{joint_name} must be a free joint")
    qpos_start = model.jnt_qposadr[joint_id]
    dof_start = model.jnt_dofadr[joint_id]
    data.qpos[qpos_start:qpos_start + 7] = model.qpos0[qpos_start:qpos_start + 7]
    if xy is not None:
        data.qpos[qpos_start:qpos_start + 2] = xy
    data.qvel[dof_start:dof_start + 6] = 0
    data.qacc_warmstart[dof_start:dof_start + 6] = 0
    data.qfrc_applied[dof_start:dof_start + 6] = 0
    data.xfrc_applied[model.jnt_bodyid[joint_id]] = 0
    mujoco.mj_forward(model, data)
    return True


class BottlePlacement:
    """Upright bottle placement, with a fixed Z and footprint inside the table."""

    def __init__(self, model, data):
        joint = model.joint("red_bottle_free_joint")
        self.address = int(joint.qposadr[0])
        self.xy = model.qpos0[self.address:self.address + 2].copy()
        self.z = float(model.qpos0[self.address + 2])
        top = model.geom("pickup_table_top").id
        rotation = data.geom_xmat[top].reshape(3, 3)
        if not np.allclose(rotation, np.eye(3)):
            raise ValueError("Bottle XY controls require an axis-aligned tabletop")
        radius = float(model.geom("red_bottle_body").size[0]) + .001
        self.bounds = np.column_stack((
            data.geom_xpos[top, :2] - model.geom_size[top, :2] + radius,
            data.geom_xpos[top, :2] + model.geom_size[top, :2] - radius,
        ))

    def validate(self, xy):
        values = np.asarray(xy, dtype=float)
        if values.shape != (2,) or not np.isfinite(values).all():
            raise ValueError("X and Y must be finite numbers in metres")
        if np.any(values < self.bounds[:, 0]) or np.any(values > self.bounds[:, 1]):
            raise ValueError(
                f"On table: X {self.bounds[0, 0]:.3f}..{self.bounds[0, 1]:.3f}, "
                f"Y {self.bounds[1, 0]:.3f}..{self.bounds[1, 1]:.3f} m"
            )
        return values.copy()

    def reset(self, model, data, xy=None):
        if xy is not None:
            self.xy = self.validate(xy)
        return reset_free_object(model, data, xy=self.xy)
