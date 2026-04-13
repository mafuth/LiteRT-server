import json
import logging
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "process_id": record.process,
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "thread_id": record.thread,
        }
        return json.dumps(log_entry, ensure_ascii=False)