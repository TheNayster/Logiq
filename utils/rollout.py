"""
Stoat Rollout Manager - Gradual rollout for Stoat-only bot
Manages server enrollment in beta/gradual features
"""

import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class RolloutPhase(str, Enum):
    """Stoat rollout phases"""
    INTERNAL = "internal"      # Internal testing only
    BETA = "beta"              # Selected servers (whitelist)
    GRADUAL = "gradual"        # Percentage-based rollout
    STABLE = "stable"          # All servers
    DEPRECATED = "deprecated"  # Being phased out


@dataclass
class ServerEnrollment:
    """Server enrollment in rollout"""
    server_id: str
    phase: RolloutPhase
    enrolled_at: str
    features: List[str]
    notes: Optional[str] = None


class StoatRolloutManager:
    """Manage gradual rollout for Stoat bot"""

    def __init__(self, db_manager=None):
        self.db = db_manager
        self._phase_config: Dict[str, RolloutPhase] = {
            'core_features': RolloutPhase.STABLE,
            'verification': RolloutPhase.STABLE,
            'moderation': RolloutPhase.STABLE,
            'economy': RolloutPhase.GRADUAL,
            'leveling': RolloutPhase.GRADUAL,
            'tickets': RolloutPhase.BETA,
            'giveaways': RolloutPhase.BETA,
            'social_alerts': RolloutPhase.INTERNAL,
            'ai_chat': RolloutPhase.INTERNAL,
        }
        self._rollout_percentages: Dict[str, int] = {
            'economy': 50,          # 50% of servers
            'leveling': 50,
            'tickets': 25,          # 25% of servers
            'giveaways': 25,
            'social_alerts': 5,     # 5% for internal testing
            'ai_chat': 10,
        }
        self._whitelist: Dict[str, Set[str]] = {}
        self._blacklist: Dict[str, Set[str]] = {}

        logger.info("Stoat rollout manager initialized")

    async def can_use_feature(
        self,
        feature: str,
        server_id: str
    ) -> bool:
        """Check if server can use feature based on rollout phase"""
        phase = self._phase_config.get(feature, RolloutPhase.INTERNAL)

        if phase == RolloutPhase.STABLE:
            return True
        elif phase == RolloutPhase.DEPRECATED:
            return False

        # Check blacklist first
        if server_id in self._blacklist.get(feature, set()):
            logger.debug(f"Server {server_id} blacklisted from {feature}")
            return False

        # Check whitelist
        if phase == RolloutPhase.BETA:
            is_whitelisted = server_id in self._whitelist.get(feature, set())
            if not is_whitelisted:
                logger.debug(f"Server {server_id} not whitelisted for {feature}")
            return is_whitelisted

        # Gradual rollout
        if phase == RolloutPhase.GRADUAL:
            percentage = self._rollout_percentages.get(feature, 0)
            rollout_hash = hash(f"{server_id}_{feature}") % 100
            return rollout_hash < percentage

        # Internal - not available to public
        return False

    def set_phase(self, feature: str, phase: RolloutPhase) -> None:
        """Set rollout phase for feature"""
        self._phase_config[feature] = phase
        logger.info(f"Feature '{feature}' set to phase: {phase.value}")

    def set_rollout_percentage(self, feature: str, percentage: int) -> None:
        """Set gradual rollout percentage (0-100)"""
        percentage = max(0, min(100, percentage))
        self._rollout_percentages[feature] = percentage
        logger.info(f"Feature '{feature}' rollout set to: {percentage}%")

    def add_whitelist(self, feature: str, server_id: str) -> None:
        """Add server to feature whitelist (beta access)"""
        if feature not in self._whitelist:
            self._whitelist[feature] = set()
        self._whitelist[feature].add(server_id)
        logger.info(f"Server {server_id} whitelisted for {feature}")

    def remove_whitelist(self, feature: str, server_id: str) -> None:
        """Remove server from whitelist"""
        if feature in self._whitelist:
            self._whitelist[feature].discard(server_id)

    def add_blacklist(self, feature: str, server_id: str) -> None:
        """Block server from feature"""
        if feature not in self._blacklist:
            self._blacklist[feature] = set()
        self._blacklist[feature].add(server_id)
        logger.info(f"Server {server_id} blacklisted from {feature}")

    def remove_blacklist(self, feature: str, server_id: str) -> None:
        """Remove server from blacklist"""
        if feature in self._blacklist:
            self._blacklist[feature].discard(server_id)

    def get_feature_status(self, feature: str) -> Dict[str, any]:
        """Get detailed status of feature rollout"""
        phase = self._phase_config.get(feature, RolloutPhase.INTERNAL)
        percentage = self._rollout_percentages.get(feature, 0)

        return {
            'feature': feature,
            'phase': phase.value,
            'percentage': percentage if phase == RolloutPhase.GRADUAL else (100 if phase == RolloutPhase.STABLE else 0),
            'whitelisted': len(self._whitelist.get(feature, set())),
            'blacklisted': len(self._blacklist.get(feature, set())),
        }

    def get_all_features_status(self) -> Dict[str, Dict]:
        """Get status of all features"""
        return {
            feature: self.get_feature_status(feature)
            for feature in self._phase_config.keys()
        }

    def export_config(self) -> str:
        """Export rollout configuration as JSON"""
        config = {
            'phases': {k: v.value for k, v in self._phase_config.items()},
            'percentages': self._rollout_percentages,
            'whitelist': {k: list(v) for k, v in self._whitelist.items()},
            'blacklist': {k: list(v) for k, v in self._blacklist.items()},
            'exported_at': datetime.utcnow().isoformat()
        }
        return json.dumps(config, indent=2)

    def import_config(self, config_json: str) -> None:
        """Import rollout configuration from JSON"""
        try:
            config = json.loads(config_json)
            
            for feature, phase_str in config.get('phases', {}).items():
                self._phase_config[feature] = RolloutPhase(phase_str)

            self._rollout_percentages.update(config.get('percentages', {}))

            for feature, servers in config.get('whitelist', {}).items():
                self._whitelist[feature] = set(servers)

            for feature, servers in config.get('blacklist', {}).items():
                self._blacklist[feature] = set(servers)

            logger.info("Rollout config imported successfully")
        except Exception as e:
            logger.error(f"Failed to import config: {e}")

    def get_phase_progress(self) -> Dict[str, Dict]:
        """Get progress through rollout phases"""
        progress = {}
        for feature, phase in self._phase_config.items():
            progress[feature] = {
                'phase': phase.value,
                'progress_percentage': self._get_progress_percentage(phase),
                'next_phase': self._get_next_phase(phase).value if phase != RolloutPhase.STABLE else None,
                'eta': self._estimate_eta(feature, phase)
            }
        return progress

    def _get_progress_percentage(self, phase: RolloutPhase) -> int:
        """Get progress through phase"""
        phase_order = [
            RolloutPhase.INTERNAL,
            RolloutPhase.BETA,
            RolloutPhase.GRADUAL,
            RolloutPhase.STABLE
        ]
        if phase == RolloutPhase.DEPRECATED:
            return 100
        try:
            return (phase_order.index(phase) + 1) / len(phase_order) * 100
        except ValueError:
            return 0

    def _get_next_phase(self, current: RolloutPhase) -> Optional[RolloutPhase]:
        """Get next phase in rollout"""
        phase_order = [
            RolloutPhase.INTERNAL,
            RolloutPhase.BETA,
            RolloutPhase.GRADUAL,
            RolloutPhase.STABLE
        ]
        try:
            current_idx = phase_order.index(current)
            return phase_order[current_idx + 1] if current_idx < len(phase_order) - 1 else None
        except ValueError:
            return None

    def _estimate_eta(self, feature: str, phase: RolloutPhase) -> Optional[str]:
        """Estimate time to next phase"""
        # Days per phase (configurable)
        phase_days = {
            RolloutPhase.INTERNAL: 7,
            RolloutPhase.BETA: 14,
            RolloutPhase.GRADUAL: 21,
        }
        days = phase_days.get(phase, 0)
        if days > 0:
            from datetime import datetime, timedelta
            eta = datetime.utcnow() + timedelta(days=days)
            return eta.isoformat()
        return None


# Global instance
_global_rollout: Optional[StoatRolloutManager] = None


def get_rollout_manager(db_manager=None) -> StoatRolloutManager:
    """Get global rollout manager"""
    global _global_rollout
    if _global_rollout is None:
        _global_rollout = StoatRolloutManager(db_manager)
    return _global_rollout