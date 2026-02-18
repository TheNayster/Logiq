"""
Stoat Feature Flags - Pure Stoat feature management
"""

import logging
from typing import Dict, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class FeatureStatus(str, Enum):
    """Feature status for Stoat"""
    DISABLED = "disabled"
    INTERNAL = "internal"     # Internal testing
    BETA = "beta"             # Closed beta
    GRADUAL = "gradual"       # Gradual rollout
    ENABLED = "enabled"       # Fully enabled


class StoatFeatureFlags:
    """Stoat-only feature flag manager"""

    # Default Stoat features
    DEFAULT_FLAGS = {
        'verification': {
            'status': FeatureStatus.ENABLED,
            'rollout': 100,
            'description': 'User verification system'
        },
        'moderation': {
            'status': FeatureStatus.ENABLED,
            'rollout': 100,
            'description': 'Moderation tools'
        },
        'economy': {
            'status': FeatureStatus.GRADUAL,
            'rollout': 50,
            'description': 'Economy system'
        },
        'leveling': {
            'status': FeatureStatus.GRADUAL,
            'rollout': 50,
            'description': 'XP leveling system'
        },
        'tickets': {
            'status': FeatureStatus.BETA,
            'rollout': 25,
            'description': 'Support tickets'
        },
        'giveaways': {
            'status': FeatureStatus.BETA,
            'rollout': 25,
            'description': 'Giveaway system'
        },
        'social_alerts': {
            'status': FeatureStatus.INTERNAL,
            'rollout': 5,
            'description': 'Social media alerts (testing)'
        },
        'ai_chat': {
            'status': FeatureStatus.INTERNAL,
            'rollout': 10,
            'description': 'AI chat integration (testing)'
        },
    }

    def __init__(self):
        self.flags = self.DEFAULT_FLAGS.copy()

    def is_enabled(
        self,
        feature: str,
        server_id: Optional[str] = None
    ) -> bool:
        """Check if feature is enabled for server"""
        flag = self.flags.get(feature)
        if not flag:
            logger.warning(f"Unknown feature flag: {feature}")
            return False

        status = flag.get('status', FeatureStatus.DISABLED)

        if status == FeatureStatus.DISABLED:
            return False
        elif status == FeatureStatus.ENABLED:
            return True

        # Gradual/Beta - use hash-based rollout
        if server_id:
            rollout = flag.get('rollout', 0)
            rollout_hash = hash(f"{server_id}_{feature}") % 100
            return rollout_hash < rollout

        return False

    def get_status(self, feature: str) -> Optional[str]:
        """Get feature status"""
        flag = self.flags.get(feature)
        return flag.get('status', FeatureStatus.DISABLED).value if flag else None

    def set_status(self, feature: str, status: FeatureStatus) -> None:
        """Set feature status"""
        if feature in self.flags:
            self.flags[feature]['status'] = status
            logger.info(f"Feature '{feature}' status: {status.value}")

    def set_rollout(self, feature: str, percentage: int) -> None:
        """Set rollout percentage"""
        if feature in self.flags:
            percentage = max(0, min(100, percentage))
            self.flags[feature]['rollout'] = percentage
            logger.info(f"Feature '{feature}' rollout: {percentage}%")

    def get_all_features(self) -> Dict[str, Any]:
        """Get all features with status"""
        return self.flags.copy()


# Global instance
_global_flags: Optional[StoatFeatureFlags] = None


def get_feature_flags() -> StoatFeatureFlags:
    """Get global feature flags"""
    global _global_flags
    if _global_flags is None:
        _global_flags = StoatFeatureFlags()
    return _global_flags


def is_feature_enabled(feature: str, server_id: Optional[str] = None) -> bool:
    """Convenience function to check feature"""
    flags = get_feature_flags()
    return flags.is_enabled(feature, server_id)