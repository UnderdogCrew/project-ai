import logging

try:
    from rich.logging import RichHandler
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

LOGGER_NAME = "strands_agents"


def get_logger(logger_name: str) -> logging.Logger:
    """Get a logger configured for Strands agents."""
    if RICH_AVAILABLE:
        rich_handler = RichHandler(
            show_time=False,
            rich_tracebacks=False,
            show_path=False,
            tracebacks_show_locals=False,
        )
        rich_handler.setFormatter(
            logging.Formatter(
                fmt="%(message)s",
                datefmt="[%X]",
            )
        )
        handler = rich_handler
    else:
        # Fallback to standard handler if Rich is not available
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    _logger = logging.getLogger(logger_name)
    _logger.addHandler(handler)
    _logger.setLevel(logging.INFO)
    _logger.propagate = False
    return _logger


logger: logging.Logger = get_logger(LOGGER_NAME)


def set_log_level_to_debug():
    """Set the main logger level to DEBUG."""
    _logger = logging.getLogger(LOGGER_NAME)
    _logger.setLevel(logging.DEBUG)


def set_log_level_to_info():
    """Set the main logger level to INFO."""
    _logger = logging.getLogger(LOGGER_NAME)
    _logger.setLevel(logging.INFO) 