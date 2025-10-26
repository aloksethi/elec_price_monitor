# Standard library imports
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
import platform
from . import config
#import pdb
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
            self.default_level = logging.DEBUG
            self._setup_root_logger()

            # Silence urllib3
            logging.getLogger("requests").setLevel(logging.WARNING)
            logging.getLogger("urllib3").setLevel(logging.WARNING)
            # Mark initialization as complete
            Log._initialized = True
            #pdb.set_trace()

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

    def _setup_root_logger(self):
        """
        Configure the root logger with file and console handlers.
        This runs only once.
        """
        root_logger = logging.getLogger() # Get the root logger
        root_logger.setLevel(self.default_level)

        # Clear existing handlers from root logger to prevent duplicates on re-init (if any)
        # This is important if your application might re-instantiate Log
        if not root_logger.handlers:
            # File Handler
            file_handler = RotatingFileHandler(
                self.log_file,
                maxBytes=1024 * 1024,  # 1MB
                backupCount=5
            )
            file_handler.setFormatter(logging.Formatter(self.log_format, self.date_format))
            root_logger.addHandler(file_handler)

            # Console Handler (for errors only)
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.ERROR) # Only show ERRORs on console
            console_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
            root_logger.addHandler(console_handler)

    def setup_logger(self, logger_name, level=None):
        """
        Get or create a named logger. These loggers will propagate messages
        to the root logger's handlers by default.
        """
        logger = logging.getLogger(logger_name)
        logger.setLevel(level or self.default_level)
        # Ensure propagation is True by default for named loggers to send to root
        logger.propagate = True
        return logger

    @classmethod
    def get_logger(cls, name):
        """
        Class method to get a logger instance.
        Ensures the Log singleton is initialized and then returns the named logger.
        """
        # Ensure the singleton is initialized before getting any logger
        log_instance = cls()
        return log_instance.setup_logger(name)
    """
    @classmethod
    def debug(cls, logger_name, message):
        logger = cls.get_logger(logger_name)
        logger.debug(message)

    @classmethod
    def info(cls, logger_name, message):
        logger = cls.get_logger(logger_name)
        logger.info(message)

    @classmethod
    def warning(cls, logger_name, message):
        logger = cls.get_logger(logger_name)
        logger.warning(message)

    @classmethod
    def error(cls, logger_name, message):
        logger = cls.get_logger(logger_name)
        logger.error(message)
    """
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
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
                handler.setFormatter(formatter)

    def change_log_level(self, logger_name, level):
        """
        Change the logging level for a specific named logger.
        If logger_name is empty or "root", it changes the root logger's level.
        """
        if not logger_name or logger_name == "root":
            logging.getLogger().setLevel(level)
        else:
            logger = self.setup_logger(logger_name, level)
            logger.setLevel(level) # Ensure the level is set on the specific logger
