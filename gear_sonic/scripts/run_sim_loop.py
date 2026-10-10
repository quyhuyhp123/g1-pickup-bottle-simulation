"""Entry point for running a MuJoCo simulation loop with the G1 robot model.

Parses a YAML-based WBC config via tyro CLI, instantiates the G1 robot model,
and launches the simulator (optionally with offscreen image publishing).
"""

from typing import Dict

import tyro

from gear_sonic.utils.mujoco_sim.simulator_factory import SimulatorFactory, init_channel
from gear_sonic.utils.mujoco_sim.configs import SimLoopConfig
from gear_sonic.data.robot_model.instantiation.g1 import (
    instantiate_g1_robot_model,
)
from gear_sonic.data.robot_model.robot_model import RobotModel

ArgsConfig = SimLoopConfig


class SimWrapper:
    def __init__(self, robot_model: RobotModel, env_name: str, config: Dict[str, any], **kwargs):
        self.robot_model = robot_model
        self.config = config

        init_channel(config=self.config)

        # Create simulator using factory
        self.sim = SimulatorFactory.create_simulator(
            config=self.config,
            env_name=env_name,
            **kwargs,
        )


def main(config: ArgsConfig):
    if not 0 <= config.sim_grasp_distance <= .1 or not 0 <= config.sim_grasp_x_tolerance <= .02:
        raise ValueError("Invalid simulation grasp Y gap or X tolerance")
    wbc_config = config.load_wbc_yaml()
    # NOTE: we will override the interface to local if it is not specified
    wbc_config["ENV_NAME"] = config.env_name
    wbc_config["REACH_DIAGNOSTIC_PATH"] = config.reach_diagnostic_path
    wbc_config["ASYNC_IMAGE_RENDER"] = config.async_image_render
    wbc_config["SIM_KEYBOARD_ZMQ_PORT"] = 5580
    wbc_config["SIM_CONTROLS"] = config.sim_controls
    wbc_config["SIM_CONTROL_PORT"] = config.sim_control_port
    wbc_config["SIM_GRASP_DISTANCE"] = config.sim_grasp_distance
    wbc_config["SIM_GRASP_X_TOLERANCE"] = config.sim_grasp_x_tolerance
    wbc_config["ARM_GRAVITY_COMPENSATION"] = config.arm_gravity_compensation
    if config.assisted_pickup and (not config.sim_controls or not config.bottle_detection_port):
        raise ValueError("Assisted pickup requires simulation controls and the RGB-D detector")
    wbc_config["ASSISTED_PICKUP"] = config.assisted_pickup
    if config.fixed_pickup_base and not config.assisted_pickup:
        raise ValueError("Fixed pickup base requires assisted pickup")
    wbc_config["FIXED_PICKUP_BASE"] = config.fixed_pickup_base
    wbc_config["BOTTLE_XY"] = config.bottle_xy
    wbc_config["GROUND_START"] = config.ground_start
    wbc_config["ENABLE_DEPTH_PUBLISH"] = config.enable_depth_publish
    wbc_config["BOTTLE_DETECTION_PORT"] = config.bottle_detection_port

    if config.enable_image_publish:
        assert (
            config.enable_offscreen
        ), "enable_offscreen must be True when enable_image_publish is True"

    robot_model = instantiate_g1_robot_model()

    sim_wrapper = SimWrapper(
        robot_model=robot_model,
        env_name=config.env_name,
        config=wbc_config,
        onscreen=wbc_config.get("ENABLE_ONSCREEN", True),
        offscreen=wbc_config.get("ENABLE_OFFSCREEN", False),
        enable_image_publish=config.enable_image_publish,
    )
    # Start simulator as independent process
    SimulatorFactory.start_simulator(
        sim_wrapper.sim,
        as_thread=False,
        enable_image_publish=config.enable_image_publish,
        mp_start_method=config.mp_start_method,
        camera_port=config.camera_port,
    )


if __name__ == "__main__":
    config = tyro.cli(ArgsConfig)
    main(config)
