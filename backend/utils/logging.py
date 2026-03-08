import structlog
import logging
import sys
import os

def setup_logging(console_output: bool = True):
    """Configure structured logging with file and optional console output.

    Args:
        console_output: If True, also log to console (useful for debugging)
    """
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)

    # Configure structlog
    processors = [
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ]

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Setup file handler
    file_handler = logging.FileHandler("logs/pulse.log", mode="a")
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter("%(message)s")
    file_handler.setFormatter(file_formatter)

    # Setup console handler if requested
    handlers = [file_handler]
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(console_formatter)
        handlers.append(console_handler)

    # Configure root logger
    logging.basicConfig(
        format="%(message)s",
        handlers=handlers,
        level=logging.INFO,
        force=True,  # Override any existing configuration
    )

    logger = structlog.get_logger()
    logger.info("logging_configured", console=console_output, log_file="logs/pulse.log")
    return logger

logger = structlog.get_logger()
