"""
Logging configuration module for the Zoom meeting management system.

This module sets up a centralized logger instance for consistent logging across
all components of the application, including Telegram bot, Zoom API interactions,
YouTube uploads, and database operations.

Attributes:
    logger (logging.Logger): Configured logger instance with appropriate handlers,
        formatters, and log levels for debugging and error tracking.
"""

import logging

# Create the logger
logger = logging.getLogger("zoom-bot")  # Set the logger name
logger.setLevel(logging.DEBUG)  # Logging level

# Log format
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Logging to file
file_handler = logging.FileHandler("zoom-bot.log")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

# Logging to console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# Add handlers
logger.addHandler(file_handler)
logger.addHandler(console_handler)
