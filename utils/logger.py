"""
Logger Configuration - Stoat bot logger
"""

import logging
from logging import config
import os
from typing import Dict, Any
import sys


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
        # Use UTF-8 stdout on Windows so emojis don't crash logging
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

        console_handler = logging.StreamHandler(sys.stdout)
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

    def debug(self, msg, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self.logger.critical(msg, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self.logger, name)
    
def setup_logger(config=None):
    """
    Backwards-compatible helper expected by utils.__init__.
    Returns the configured logger instance.
    """
    return BotLogger(config).logger