"""
Logger Configuration - Stoat bot logger
"""

import logging
import os
from typing import Dict, Any


class BotLogger:
    """Custom logger for Stoat bot"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Setup logger with handlers"""
        logger = logging.getLogger("Logiq")
        level = os.getenv('LOG_LEVEL', self.config.get('level', 'INFO'))
        logger.setLevel(getattr(logging, level))

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, level))

        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)

        logger.addHandler(console_handler)

        # File handler (optional)
        log_file = self.config.get('file')
        if log_file:
            os.makedirs(os.path.dirname(log_file) or '.', exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(getattr(logging, level))
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        return logger

    def debug(self, msg):
        self.logger.debug(msg)

    def info(self, msg):
        self.logger.info(msg)

    def warning(self, msg):
        self.logger.warning(msg)

    def error(self, msg):
        self.logger.error(msg)

    def critical(self, msg):
        self.logger.critical(msg)

    def __getattr__(self, name):
        return getattr(self.logger, name)
