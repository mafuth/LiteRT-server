import os
import asyncio
import logging
import platform
import litert_lm
from typing import List, Dict, Any, Optional
from lib.classes.logger import LoggerManager
from lib.config import LLM_BACKEND, LLM_MODEL_FILENAME

logger = LoggerManager(__name__)

litert_lm.set_min_log_severity(litert_lm.LogSeverity.ERROR)

class LlmEngine:
    def __init__(self):
        self.model_path = os.path.join("models", f"{LLM_MODEL_FILENAME}.litertlm")
        self.engine: Optional[litert_lm.Engine] = None
        self.backend = litert_lm.Backend.GPU if LLM_BACKEND == "GPU" else litert_lm.Backend.CPU
        self.lock = asyncio.Lock()

    def getEngine(self):
        if self.engine is None:
            logger.info(f"Loading model from {self.model_path}...")
            self.engine = litert_lm.Engine(
                    self.model_path, 
                    backend=self.backend,
                    audio_backend=self.backend,
                    vision_backend=litert_lm.Backend.CPU
                )
            logger.info("Model loaded successfully.")
        return self.engine