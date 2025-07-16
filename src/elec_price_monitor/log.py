# Standard library imports
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
import platform
from . import config
class Log:
    # Class variables/attributes for singleton pattern. they are equivalent to global variables
    _instance = None  # Stores the single instance
    _initialized = False  # Tracks if initialization has been done

    # Log levels
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    def __new__(cls):
        """
        Singleton pattern implementation:
        Ensures only one instance of LoggerSetup exists
        """
        if cls._instance is None:
            cls._instance = super(Log, cls).__new__(cls) #calls the __new__ method for the base class,
            # which is implicitly the object i.e., all classes are defined as class abc(object):, in this case it will
            # call the __new__ method of the object which just ends up allocating the memory. signature of super is
            # super(type, obj_or_type=None)
        return cls._instance

    def __init__(self):
        """
        Initialize logging configuration.
        Only runs once due to _initialized flag
        """
        if not Log._initialized:
            # Define logging format and directory settings, instance varaibles (log_format, date_format etc)
            self.log_format = '%(asctime)s - %(name)s - %(levelname)s [%(filename)s:%(funcName)s:%(lineno)d] %(message)s'
            self.date_format = '%Y-%m-%d %H:%M:%S'
            self.log_dir = self._get_log_dir()
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self.log_file = self.log_dir / 'app.log'
            self.default_level = logging.INFO
            self._loggers = {}  # Dictionary to store logger instances
            # Mark initialization as complete
            Log._initialized = True

    def _get_log_dir(self):
        """
        Pick a log directory depending on OS.
        """
        system = platform.system()

        if system == "Windows":
            # Local to project root
            return Path.cwd() / "logs"
        else:
            # Standard Linux path
            return Path(f"{config.APP_NAME}/logs")

    def setup_logger(self, logger_name, level=None):
        """
        Configure and return a logger instance
        Args:
            logger_name: Name of the logger (usually __name__ from the calling module)
            level: Optional logging level
        """
        # Get or create logger with specified name
        if logger_name in self._loggers:
            return self._loggers[logger_name]

        logger = logging.getLogger(logger_name)
        # Use provided level or default
        level = level or self.default_level
        logger.setLevel(level)

        # Remove any existing handlers to avoid duplicates
        logger.handlers.clear()

        # Create file handler with rotation
        file_handler = RotatingFileHandler(
            self.log_file,
            maxBytes=1024 * 1024,  # 1MB
            backupCount=5
        )
        file_handler.setFormatter(logging.Formatter(self.log_format, self.date_format))

        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.ERROR)
        console_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
#        console_handler.setFormatter(logging.Formatter(self.log_format, self.date_format))

        # Add both handlers to logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        self._loggers[logger_name] = logger
        return logger

    @classmethod
    def debug(cls, logger_name, message):
        """Log debug message for specified logger"""
        logger = cls.get_logger(logger_name)
        logger.debug(message)

    @classmethod
    def info(cls, logger_name, message):
        """Log info message for specified logger"""
        logger = cls.get_logger(logger_name)
        logger.info(message)

    @classmethod
    def warning(cls, logger_name, message):
        """Log warning message for specified logger"""
        logger = cls.get_logger(logger_name)
        logger.warning(message)

    @classmethod
    def error(cls, logger_name, message):
        """Log error message for specified logger"""
        logger = cls.get_logger(logger_name)
        logger.error(message)

    def set_format(self, format_string, date_format=None):
        """
        Set custom format for log messages
        Args:
            format_string: New log format string
            date_format: Optional new date format string
        """
        self.log_format = format_string

        if date_format:
            self.date_format = date_format

        formatter = logging.Formatter(self.log_format, self.date_format)
        for logger in self._loggers.values():
            for handler in logger.handlers:
                handler.setFormatter(formatter)

    def change_log_level(self, logger_name, level):
        """
        Change the logging level for a specific logger
        Args:
            logger_name: Name of the logger to modify
            level: New logging level
        """
        if logger_name in self._loggers:
            self._loggers[logger_name].setLevel(level)
        else:
            logger = self.setup_logger(logger_name, level)
            self._loggers[logger_name] = logger

    @classmethod
    def get_logger(cls, name):
        """
        Class method to get a logger instance
        Args:
            name: Name for the logger
        """
        return cls().setup_logger(name)