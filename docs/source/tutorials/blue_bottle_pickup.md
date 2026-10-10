# Assisted blue bottle pickup in MuJoCo

Run from the repository root:

```bash
.venv_sim/bin/python gear_sonic/scripts/run_blue_bottle_pickup.py
```

This opens an independent MuJoCo demo and automatically approaches, closes the
right Dex3 hand, lifts the blue bottle, and holds it. Close the viewer to finish.
No GR00T server, SONIC process, DDS, tmux launcher, or keyboard commands are needed.
It does not connect to a physical robot.

This is an **assisted inverse-kinematics grasp**, using the bottle pose from
MuJoCo. It is not a successful evaluation of the GR00T checkpoint. The pelvis is
anchored to the world to stabilize manipulation. The bottle remains a free body
and is held through physical finger contacts and friction, with no hand-object
weld, object teleportation, or external lifting force.

The CloudWalk checkpoint's training dataset uses Inspire FTP hands:
https://huggingface.co/datasets/cloudwalk-research/gr00t-g1-grab-bottle-right-hand-v2
The scene uses Dex3. Converting normalized grip level to a Dex3 closed pose does
not reproduce Inspire grasp geometry or reach/grip timing. A task-trained Dex3
checkpoint or a separately validated VLA/IK hybrid is needed for autonomous
vision-conditioned pickup with this embodiment.

The demo solves wrist position and orientation with waist pitch and the right
arm, applies PD joint control with gravity compensation, gradually closes the
hand, and lifts 18 cm. Joint limits and actuator effort limits remain enforced.
The initial arm pregrasp pose is set before simulation begins. Current grasp
geometry is tuned for this scene's cylindrical bottle, not arbitrary objects.

Validation and video recording:

```bash
MUJOCO_GL=egl .venv_sim/bin/python gear_sonic/scripts/run_blue_bottle_pickup.py \
  --headless --record
```

Outputs are written to `outputs/blue_bottle_pickup/`: `report.json`,
`third_person.mp4`, `ego_view.mp4`, and images of the held bottle. Success requires
at least 12 cm lift throughout a 3-second hold and persistent contact from both
thumb and index/middle fingers. Reports contain actual bottle/wrist coordinates
and finger contacts, not model-predicted object coordinates.

Small workspace perturbations can be checked using `--bottle-offset X Y` in
meters. IK raises an error if it cannot reach the requested grasp pose.
