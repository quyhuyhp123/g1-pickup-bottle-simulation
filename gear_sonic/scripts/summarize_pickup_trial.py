"""Evaluate recorded MuJoCo contact/lift evidence; never controls the robot."""
import argparse
import json
from pathlib import Path


def summarize(samples, lift_threshold=.12, hold_seconds=3.):
    if not samples:
        raise ValueError("No diagnostic samples in the selected interval")
    longest = 0.
    held_since = None
    previous = None
    for sample in samples:
        now = sample["monotonic_s"]
        bodies = {c["hand_body"] for c in sample["contacts"] if c["normal_force_n"] > .01}
        pinch = any("thumb" in b for b in bodies) and any(
            "index" in b or "middle" in b for b in bodies)
        held = sample["bottle_lift_from_initial_m"] >= lift_threshold and pinch
        if previous is not None and (now - previous["monotonic_s"] > .25 or
                                     sample["sim_time_s"] < previous["sim_time_s"]):
            held_since = None
        if held:
            if held_since is None:
                held_since = now
            longest = max(longest, now - held_since)
        else:
            held_since = None
        previous = sample
    elapsed = samples[-1]["monotonic_s"] - samples[0]["monotonic_s"]
    reset = any(b["sim_time_s"] < a["sim_time_s"] for a, b in zip(samples, samples[1:]))
    return {
        "samples": len(samples), "duration_s": elapsed,
        "max_lift_m": max(s["bottle_lift_from_initial_m"] for s in samples),
        "max_tilt_deg": max(s["bottle_tilt_deg"] for s in samples),
        "contact_bodies": sorted({c["hand_body"] for s in samples for c in s["contacts"]}),
        "lift_threshold_m": lift_threshold, "required_hold_s": hold_seconds,
        "longest_lift_with_opposing_finger_contacts_s": longest,
        "simulation_reset_detected": reset,
        "realtime_factor": None if reset or elapsed <= 0 else (
            samples[-1]["sim_time_s"] - samples[0]["sim_time_s"]) / elapsed,
        "success": longest >= hold_seconds,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--actions", type=Path, help="Select last policy-resume interval")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    samples = [json.loads(line) for line in args.trace.read_text().splitlines() if line.strip()]
    if args.actions:
        actions = [json.loads(line) for line in args.actions.read_text().splitlines() if line.strip()]
        published = [a for a in actions if a["event"] == "published"]
        if not published:
            raise ValueError("No checkpoint actions published")
        # Every new trial resets frame numbering; pauses need not reset it.
        start = max((a["monotonic"] for a in published if a["frame"] == 0),
                    default=published[0]["monotonic"])
        end = published[-1]["monotonic"]
        samples = [s for s in samples if start <= s["monotonic_s"] <= end]
    report = summarize(samples)
    text = json.dumps(report, indent=2) + "\n"
    print(text, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)


if __name__ == "__main__":
    main()
