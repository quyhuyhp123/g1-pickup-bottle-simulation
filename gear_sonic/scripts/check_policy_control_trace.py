"""Audit recorded GR00T -> SONIC ownership separately from pickup success."""

import argparse
import json
from pathlib import Path

import numpy as np

from gear_sonic.utils.inference.policy_control import policy_action_step


def audit_trace(path):
    selected = {}
    matched, unmatched, violations, tokens, grips = 0, 0, [], [], []
    raw_chunks, hand_observations_zero = 0, True
    for line_number, line in enumerate(Path(path).read_text().splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if row['event'] == 'raw_chunk':
            raw_chunks += 1
            state = row.get('input_state', {})
            hand_observations_zero &= all(key in state and not np.asarray(state[key]).any()
                                           for key in ('left_hand', 'right_hand'))
        elif row['event'] == 'chunk_selected':
            selected[row['chunk_id']] = row.get('action')
        elif row['event'] == 'published':
            tokens.append(row['motion_token'])
            grips.append(float(np.mean(row['raw_right_hand'][:5])))
            action = selected.get(row['chunk_id'])
            if not action:
                unmatched += 1
                continue
            token, left, right, _ = policy_action_step(action, row['index'])
            valid = (np.array_equal(token, np.asarray(row['motion_token'], dtype=np.float32))
                     and np.array_equal(token, np.asarray(row['raw_motion_token'], dtype=np.float32))
                     and np.array_equal(left, np.asarray(row['raw_left_hand'], dtype=np.float32))
                     and np.array_equal(right, np.asarray(row['raw_right_hand'], dtype=np.float32))
                     and row.get('closure_fraction') is None and row.get('body_source') == 'GR00T')
            matched += 1
            if not valid:
                violations.append(line_number)
    return {'raw_chunks': raw_chunks, 'published_actions': len(tokens),
            'matched_actions': matched, 'unmatched_actions': unmatched,
            'ownership_violation_lines': violations,
            'hand_observations_match_training_zero': hand_observations_zero if raw_chunks else None,
            'max_token_change': float(np.max(np.ptp(tokens, axis=0))) if tokens else None,
            'raw_grip_min_max': [min(grips), max(grips)] if grips else None,
            'policy_routing_verified': raw_chunks > 0 and matched > 0 and not violations and hand_observations_zero,
            'pickup_success': 'Not inferred from action routing; inspect physical lift and contacts.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace', nargs='?', type=Path, default=Path('outputs/gr00t_policy/actions.jsonl'))
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = audit_trace(args.trace)
    print(json.dumps(report, indent=2))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    if not report['policy_routing_verified']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
