import os
import logging
from logging.handlers import TimedRotatingFileHandler, QueueHandler, QueueListener
from queue import Queue

from lib.helpers.jsonLogFormatter import JSONFormatter
from lib.config import (
    LOG_FILE_PATH,
    LOG_BACKUP_COUNT,
    LOG_ROTATION_INTERVAL,
    LOG_ROTATION_WHEN,
    LOG_LEVEL,
    APP_ENV,
)


class LoggerManager:
    _configured = False
    _listener: QueueListener | None = None
    _queue: Queue | None = None

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        if not LoggerManager._configured:
            self._setup_logging()
            LoggerManager._configured = True
        # return self.logger

    @classmethod
    def _setup_logging(cls, log_file: str | None = None) -> None:
        if log_file is None:
            log_file = LOG_FILE_PATH

        # Root logger
        root = logging.getLogger()
        numeric_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
        root.setLevel(numeric_level)

        # --- Create the queue ---
        log_queue: Queue = Queue(-1)
        cls._queue = log_queue

        # --- Handlers (they will run in listener thread) ---
        handlers: list[logging.Handler] = []

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - [PID:%(process)d] - %(levelname)s - %(name)s - %(message)s"
            )
        )
        handlers.append(console_handler)

        # File handler only in dev, and only when a real path is configured
        if APP_ENV == 'dev' and log_file.lower() != 'stdout':
            try:
                log_dir = os.path.dirname(log_file)
                if log_dir:
                    os.makedirs(log_dir, exist_ok=True)
                file_handler = TimedRotatingFileHandler(
                    filename=log_file,
                    when=LOG_ROTATION_WHEN,
                    interval=LOG_ROTATION_INTERVAL,
                    backupCount=LOG_BACKUP_COUNT,
                    encoding='utf-8',
                )
                file_handler.suffix = '%Y-%m-%d'
                file_handler.setFormatter(JSONFormatter())
                handlers.append(file_handler)
            except Exception as e:
                # Can't use the logger here - it isn't set up yet. Print is safe.
                print(f"WARNING: Could not set up file log handler: {e}")

        # --- Queue handler and listener setup ---
        queue_handler = QueueHandler(log_queue)
        root.addHandler(queue_handler)

        listener = QueueListener(log_queue, *handlers, respect_handler_level=True)
        listener.start()
        cls._listener = listener

        root.info("Logging system initialized (env=%s, level=%s)", APP_ENV, LOG_LEVEL)

    @classmethod
    def shutdown(cls) -> None:
        """Gracefully stop the QueueListener and allow re-configuration on next init."""
        if cls._listener:
            cls._listener.stop()
            cls._listener = None
        cls._configured = False

    def debug(self, msg, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        self.logger.exception(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self.logger.critical(msg, *args, **kwargs)
