"""
Gradual Rollout Script - Manage Stoat feature rollout
"""

import asyncio
import argparse
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.rollout import StoatRolloutManager, RolloutPhase
from utils.feature_flags import get_feature_flags

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(
        description='Stoat gradual rollout management'
    )

    parser.add_argument('--status', action='store_true', help='Show rollout status')
    parser.add_argument('--monitor', metavar='FEATURE', help='Monitor feature')
    parser.add_argument('--set', nargs=2, metavar=('FEATURE', 'PERCENTAGE'),
                       help='Set rollout percentage')
    parser.add_argument('--phase', nargs=2, metavar=('FEATURE', 'PHASE'),
                       help='Set feature phase')
    parser.add_argument('--whitelist', nargs=2, metavar=('FEATURE', 'SERVER_ID'),
                       help='Add server to whitelist')
    parser.add_argument('--remove-whitelist', nargs=2, metavar=('FEATURE', 'SERVER_ID'),
                       help='Remove from whitelist')
    parser.add_argument('--blacklist', nargs=2, metavar=('FEATURE', 'SERVER_ID'),
                       help='Block server from feature')
    parser.add_argument('--export', metavar='FILE', help='Export config to JSON')
    parser.add_argument('--import', metavar='FILE', dest='import_file',
                       help='Import config from JSON')

    args = parser.parse_args()

    rollout = StoatRolloutManager()

    # Show status
    if args.status:
        print("\n📊 Stoat Rollout Status:\n")
        status = rollout.get_all_features_status()
        progress = rollout.get_phase_progress()

        for feature, info in status.items():
            phase = info['phase']
            pct = info['percentage']
            print(f"  {feature:20} | {phase:10} | {pct:3d}%")

            prog = progress.get(feature, {})
            if prog.get('next_phase'):
                print(f"    → Next: {prog['next_phase']} (ETA: {prog.get('eta', 'N/A')})")
        print()

    # Monitor feature
    elif args.monitor:
        feature = args.monitor.lower()
        info = rollout.get_feature_status(feature)
        print(f"\n📈 Monitoring: {feature}\n")
        print(f"  Phase: {info['phase']}")
        print(f"  Rollout: {info['percentage']}%")
        print(f"  Whitelisted servers: {info['whitelisted']}")
        print(f"  Blacklisted servers: {info['blacklisted']}\n")

    # Set rollout percentage
    elif args.set:
        feature, pct = args.set
        try:
            pct = int(pct)
            rollout.set_rollout_percentage(feature, pct)
            print(f"✅ {feature} rollout set to {pct}%")
        except ValueError:
            print(f"❌ Invalid percentage: {pct}")

    # Set phase
    elif args.phase:
        feature, phase_str = args.phase
        try:
            phase = RolloutPhase(phase_str.lower())
            rollout.set_phase(feature, phase)
            print(f"✅ {feature} phase set to {phase.value}")
        except ValueError:
            print(f"❌ Invalid phase: {phase_str}")

    # Add to whitelist
    elif args.whitelist:
        feature, server_id = args.whitelist
        rollout.add_whitelist(feature, server_id)
        print(f"✅ {server_id} whitelisted for {feature}")

    # Remove from whitelist
    elif args.remove_whitelist:
        feature, server_id = args.remove_whitelist
        rollout.remove_whitelist(feature, server_id)
        print(f"✅ {server_id} removed from {feature} whitelist")

    # Add to blacklist
    elif args.blacklist:
        feature, server_id = args.blacklist
        rollout.add_blacklist(feature, server_id)
        print(f"✅ {server_id} blacklisted from {feature}")

    # Export
    elif args.export:
        config_json = rollout.export_config()
        with open(args.export, 'w') as f:
            f.write(config_json)
        print(f"✅ Exported to {args.export}")

    # Import
    elif args.import_file:
        with open(args.import_file, 'r') as f:
            config_json = f.read()
        rollout.import_config(config_json)
        print(f"✅ Imported from {args.import_file}")

    else:
        parser.print_help()


if __name__ == '__main__':
    asyncio.run(main())