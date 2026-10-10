# CloudWalk checkpoint and Inspire FTP compatibility

The local `~/models/g1_sonic_grab_bottle` identifies itself as a deployment export
of a 4-GPU, batch-64, 10k-step run. It is not the official v2 `checkpoint-20000`
(6-GPU, batch-48 training recipe). Both have the same embodiment name; that does
not imply identical training or interchangeable hand kinematics.

Official v2 source:
https://huggingface.co/cloudwalk-research/gr00t-n17-g1-grab-bottle-rh-210ep-v2-finetune
Dataset:
https://huggingface.co/datasets/cloudwalk-research/gr00t-g1-grab-bottle-right-hand-v2

The official weights are stored separately at
`checkpoints/cloudwalk_g1_bottle_v2/checkpoint-20000`. The existing weights are
not modified. Audit tensor headers, shard completeness and hand statistics:

```bash
.venv_inference/bin/python gear_sonic/scripts/check_cloudwalk_checkpoint.py \
  checkpoints/cloudwalk_g1_bottle_v2/checkpoint-20000
```

After stopping the existing policy server on port 5550, start the official one:

```bash
bash gear_sonic/scripts/run_cloudwalk_policy_server.sh
```

The server still emits motion tokens plus Inspire FTP hand channels. This is not
an Inspire hand simulator. The experimental `--inspire-ftp-hands` client option
maps aggregate grip intent to a Dex3 pose; it does not emulate the original hand.

Native deployment still requires the CloudWalk `InspireFTPGripMapper` (or a
validated equivalent) and an Inspire-compatible simulator/DDS bridge. The
official Unitree repository does provide a G1 Inspire FTP URDF and meshes:
https://github.com/unitreerobotics/unitree_ros/blob/master/robots/g1_description/g1_29dof_rev_1_0_with_inspire_hand_FTP.urdf
The hand URDFs also define passive finger mimic joints. These must be preserved
as constraints in MuJoCo; replacing a filename does not convert the current
seven-motor Dex3 bridge into the six-motor Inspire interface. The CloudWalk repository
linked in the dataset (`cloudwalk-research/GR00T-WholeBodyControl`) returned 404
when inspected. The two supplied NVIDIA repositories contain the server and
Dex3 control stack. Isaac-GR00T includes RoboCasa references to `InspireRightHand`
for Fourier GR1, which do not establish the correct G1 RH56DFTP mount or channel
mapping. Upstream compatibility discussion:
https://github.com/NVlabs/GR00T-WholeBodyControl/issues/121

Do not reinterpret seven FTP channels as seven Dex3 joint angles or rename the
Dex3 scene as Inspire. Needed next: original hand model + mapper, or task data
and fine-tuning collected with the actual Dex3 embodiment.

The official model card also reports grasp anticipation even with an absent
bottle; successful reach motion alone is not proof of reliable object detection.
The simulation task must be evaluated closed loop after hand compatibility is
resolved. Neither checkpoint download nor a successful server query demonstrates
physical pickup.

## Recorded-input verification

`outputs/input_audit/training_inference.json` records calls to the running
checkpoint-20000 server using synchronized RGB frames and joint states from
episode 0 of the training dataset. At frame 480, the source grip begins at 0.30
and reaches 1.00 in the next 40 frames; the model predicts 0.307 to 1.00.
At frame 500, source grip begins at 0.70; the model predicts 0.676 to 1.00.
This checks the server's ability to emit a closing sequence without sending any
action to the robot. It does not demonstrate simulated pickup.

`outputs/input_audit/input_ablation.json` contains three inference trials per
combination of recorded/live image and recorded/live body state. Grip predictions
vary, and even a simulation image without the bottle in view can elicit closing
with recorded grasp-phase body state. Therefore neither reaching nor closing is
evidence of object detection. The experiment cannot attribute failure to only
the image or only the body state.

The model card's success rates describe the physical G1 + Inspire stack, not
this MuJoCo scene. Preserve that distinction when evaluating a port.

## Bottle position and manual reset

The blue bottle's initial body position in `scene_43dof.xml` is
`0.43 -0.11 0.801` metres, 5 cm closer to the initial robot position than before.
Restart the simulation stack to load XML/Python changes and reconnect deploy;
the policy server does not need restarting.

Focus the MuJoCo window and press **R** to restore only the bottle's initial
position and upright orientation, with zero object velocity. The reset is
queued onto the physics thread and does not reset the robot, controls, or clock.
To repeat a trial, first send **i** + Enter in the keyboard publisher pane to
pause the policy and return to the initial open-hand pose, then press **R** in
MuJoCo and send **p** + Enter in the keyboard pane to resume inference. The
MuJoCo key is separate from the keyboard publisher's policy controls.
