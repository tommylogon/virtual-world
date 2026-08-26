import logging
from logging.handlers import TimedRotatingFileHandler
import sys
import os

# A dictionary to hold logger instances, ensuring they are only created once per name.
_loggers = {}

def setup_logger(name: str, level=logging.INFO):
    """
    Sets up a unique, rotating logger for each agent based on its module name.
    
    This function is a singleton factory: it ensures that for any given 'name',
    the logger is only configured once. Subsequent calls with the same name
    will return the already-existing logger instance.

    Args:
        name (str): The name for the logger, typically __name__ from the calling module.
        level (int): The logging level (e.g., logging.INFO, logging.DEBUG).
    """
    # If a logger with this name already exists, return the cached instance.
    if name in _loggers:
        return _loggers[name]

    # --- Create and configure the logger only if it doesn't exist ---

    # 1. Determine the log file name from the module name.
    # Example: 'Aura.Agents.monitoring_agent' becomes 'monitoring_agent.log'
    # Example: 'Aura.aura' becomes 'aura.log' for the main entry point.
    log_filename = f"{name.split('.')[-1]}.log"
    log_filepath = os.path.join('logs', log_filename)
    
    # Ensure the 'logs' directory exists.
    log_dir = os.path.dirname(log_filepath)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 2. Configure the formatter.
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(module)s.py:%(lineno)d] - %(message)s'
    )

    # 3. Create handlers.
    # Rotates at midnight, keeps 7 days of backups.
    file_handler = TimedRotatingFileHandler(log_filepath, when="midnight", interval=1, backupCount=7)
    file_handler.setFormatter(formatter)
    
    # Also log to the console.
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    # 4. Get the logger instance and add the handlers.
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    
    # 5. Cache the new logger and return it.
    _loggers[name] = logger
    return logger