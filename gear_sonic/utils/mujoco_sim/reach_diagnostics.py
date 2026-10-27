"""Measure reach geometry directly in the simulator's world frame."""
import mujoco
import numpy as np
from gear_sonic.utils.mujoco_sim.palm_proximity import PalmProximity
from gear_sonic.utils.mujoco_sim.hand_alignment import HandGraspAlignment


def measure_reach(model, data, joint_targets=None):
    # Use a separate data object so diagnostics never change the running physics.
    actual = mujoco.MjData(model)
    actual.qpos[:] = data.qpos
    actual.qvel[:] = data.qvel
    mujoco.mj_forward(model, actual)
    bottle = model.body('red_bottle').id
    wrist = model.body('right_wrist_yaw_link').id
    grasp_site = model.site('right_hand_grasp_center').id
    palm = PalmProximity(model).palm
    def pose(d):
        return {'wrist_world_m': d.xpos[wrist].tolist(),
                'grasp_center_world_m': d.site_xpos[grasp_site].tolist(),
                'palm_world_m': d.geom_xpos[palm].tolist(),
                'palm_to_bottle_center_m': float(np.linalg.norm(d.geom_xpos[palm] - actual.xpos[bottle]))}
    result = {'sim_time_s': float(data.time), 'bottle_world_m': actual.xpos[bottle].tolist(),
              'robot_base_quat_wxyz': actual.qpos[3:7].tolist(),
              'robot_base_world_m': actual.qpos[:3].tolist(), 'actual': pose(actual)}
    result['actual'].update(PalmProximity(model).measure(actual))
    result['whole_hand_alignment'] = HandGraspAlignment(model).measure(actual)
    result['bottle_quat_wxyz'] = actual.xquat[bottle].tolist()
    result['bottle_tilt_deg'] = float(np.degrees(np.arccos(np.clip(actual.xmat[bottle].reshape(3, 3)[2, 2], -1, 1))))
    bottle_joint = model.joint('red_bottle_free_joint').id
    bottle_adr = model.jnt_qposadr[bottle_joint]
    result['bottle_lift_from_initial_m'] = float(actual.xpos[bottle, 2] - model.qpos0[bottle_adr + 2])
    bottle_geoms = [i for i in range(model.ngeom) if model.geom_bodyid[i] == bottle
                    and (model.geom_contype[i] or model.geom_conaffinity[i])]
    hand_bodies = {wrist}
    for body in range(wrist + 1, model.nbody):
        if int(model.body_parentid[body]) in hand_bodies:
            hand_bodies.add(body)
    hand_geoms = [i for i in range(model.ngeom)
                  if int(model.geom_bodyid[i]) in hand_bodies
                  and (model.geom_contype[i] or model.geom_conaffinity[i])]
    distances = [mujoco.mj_geomDistance(model, actual, a, b, 2.0, None)
                 for a in bottle_geoms for b in hand_geoms]
    result['nearest_hand_bottle_surface_m'] = float(min(distances)) if distances else None
    result['hand_bottle_contacts'] = sum(
        (c.geom1 in bottle_geoms and c.geom2 in hand_geoms) or
        (c.geom2 in bottle_geoms and c.geom1 in hand_geoms) for c in actual.contact)
    result['contacts'] = []
    # Solver forces come from the running physics step, not the FK-only copy.
    for i, contact in enumerate(data.contact):
        hand = contact.geom2 if contact.geom1 in bottle_geoms else contact.geom1 if contact.geom2 in bottle_geoms else None
        if hand is None or hand not in hand_geoms:
            continue
        force = np.zeros(6)
        mujoco.mj_contactForce(model, data, i, force)
        result['contacts'].append({'hand_body': model.body(int(model.geom_bodyid[hand])).name,
                                   'normal_force_n': float(force[0])})
    if joint_targets:
        target = mujoco.MjData(model)
        target.qpos[:] = actual.qpos
        errors = {}
        for joint_id, value in joint_targets.items():
            adr = model.jnt_qposadr[joint_id]
            target.qpos[adr] = value
            errors[model.joint(joint_id).name] = float(value - actual.qpos[adr])
        mujoco.mj_forward(model, target)
        result['command_at_current_base'] = pose(target)
        result['joint_target_minus_actual_rad'] = errors
        result['actual_joint_q_rad'] = {model.joint(jid).name: float(actual.qpos[model.jnt_qposadr[jid]]) for jid in joint_targets}
        result['palm_tracking_error_m'] = float(np.linalg.norm(target.geom_xpos[palm] - actual.geom_xpos[palm]))
        result['grasp_tracking_error_m'] = float(np.linalg.norm(target.site_xpos[grasp_site] - actual.site_xpos[grasp_site]))
    return result
