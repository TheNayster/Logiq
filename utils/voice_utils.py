"""
Voice channel utilities for Stoat.
Provides capability detection and fallback handlers.
Stoat voice support - NOT YET AVAILABLE
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class VoiceCapability:
    """Detect and handle Stoat voice capabilities"""

    # Stoat-only voice features status
    VOICE_FEATURES = {
        "stoat": {
            "join_channel": False,  # ⏳ Coming in Stoat v1.1+
            "audio_playback": False,
            "voice_effects": False,
            "voice_activity": False,
        }
    }

    @staticmethod
    def is_feature_supported(feature: str) -> bool:
        """Check if feature is supported on Stoat"""
        features = VoiceCapability.VOICE_FEATURES.get("stoat", {})
        return features.get(feature, False)

    @staticmethod
    def get_available_features() -> Dict[str, bool]:
        """Get all available Stoat voice features"""
        return VoiceCapability.VOICE_FEATURES.get("stoat", {})

    @staticmethod
    def get_unsupported_features() -> list:
        """Get list of unsupported Stoat voice features"""
        features = VoiceCapability.get_available_features()
        return [f for f, supported in features.items() if not supported]


class VoiceNotAvailable(Exception):
    """Raised when voice feature is not available on Stoat"""

    def __init__(self, feature: str):
        self.feature = feature
        super().__init__(
            f"{feature} is not yet available on Stoat.chat.\n"
            f"Voice support is coming in Stoat v1.1+\n"
            f"Please use text-based alternatives for now."
        )


class VoiceFallback:
    """Fallback implementations for unsupported Stoat voice features"""

    @staticmethod
    def get_fallback_message(feature: str) -> str:
        """Get fallback message for unsupported feature"""
        fallbacks = {
            "join_channel": (
                "🎤 Voice channel joining is not yet supported on Stoat.\n"
                "However, you can queue music using `/play` command!\n"
                "This feature is coming in Stoat v1.1+"
            ),
            "audio_playback": (
                "🔊 Audio playback is not yet supported on Stoat.\n"
                "Queued tracks are stored and can be viewed with `/queue`.\n"
                "Coming soon!"
            ),
            "pause": (
                "⏸️ Pause/resume will be available when voice support is added.\n"
                "Use `/skip` and `/clear` commands for now."
            ),
            "volume": (
                "🔉 Volume control is not yet available on Stoat.\n"
                "This will be added when voice support is implemented."
            ),
            "effects": (
                "🎚️ Voice effects are not available in text mode.\n"
                "Use text-based commands for music management."
            ),
        }
        return fallbacks.get(feature, f"{feature} is not currently available on Stoat.")

    @staticmethod
    def create_fallback_embed(
        feature: str,
        title: str = "Feature Not Available",
        color: int = 0xFFA500
    ) -> Dict[str, Any]:
        """Create embed for unsupported feature"""
        message = VoiceFallback.get_fallback_message(feature)
        return {
            "title": f"⚠️ {title}",
            "description": message,
            "color": color,
            "footer": {"text": "🔄 Planned for Stoat v1.1+"}
        }


class VoiceChannelStub:
    """Stub for voice channel operations (not yet supported on Stoat)"""

    def __init__(self, channel_id: str):
        self.channel_id = channel_id
        self._verify_support()

    def _verify_support(self):
        """Verify voice is supported"""
        if not VoiceCapability.is_feature_supported("join_channel"):
            raise VoiceNotAvailable("Voice channel operations")

    async def join(self) -> bool:
        """Join voice channel (stub - not supported)"""
        logger.warning("Voice join not supported on Stoat")
        return False

    async def leave(self) -> bool:
        """Leave voice channel (stub - not supported)"""
        logger.warning("Voice leave not supported on Stoat")
        return False

    async def play(self, source: str) -> bool:
        """Play audio (stub - not supported)"""
        logger.warning("Audio playback not supported on Stoat")
        return False

    async def stop(self) -> bool:
        """Stop audio (stub - not supported)"""
        logger.warning("Audio stop not supported on Stoat")
        return False


def check_voice_support() -> Dict[str, bool]:
    """Check Stoat voice support status"""
    capabilities = {}

    for feature in VoiceCapability.get_available_features():
        capabilities[feature] = VoiceCapability.is_feature_supported(feature)

    return capabilities