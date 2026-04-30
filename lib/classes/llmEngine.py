import os
import asyncio
import litert_lm
from contextlib import asynccontextmanager
from typing import Optional
from lib.classes.logger import LoggerManager
from lib.config import LLM_BACKEND, LLM_MODEL_FILENAME, LLM_AUDIO_BACKEND, LLM_VISION_BACKEND

logger = LoggerManager(__name__)

litert_lm.set_min_log_severity(litert_lm.LogSeverity.ERROR)


class LlmEngine:
    def __init__(self):
        self.model_path = os.path.join("models", f"{LLM_MODEL_FILENAME}.litertlm")
        self.engine: Optional[litert_lm.Engine] = None
        self.backend = litert_lm.Backend.GPU if LLM_BACKEND == "GPU" else litert_lm.Backend.CPU
        self.audio_backend = litert_lm.Backend.GPU if LLM_AUDIO_BACKEND == "GPU" else litert_lm.Backend.CPU
        self.vision_backend = litert_lm.Backend.GPU if LLM_VISION_BACKEND == "GPU" else litert_lm.Backend.CPU
        self._lock = asyncio.Lock()

    def load(self) -> None:
        """Eagerly load the model. Call once at startup to avoid cold-start on first request."""
        if self.engine is None:
            logger.info(f"Loading model from {self.model_path}...")
            self.engine = litert_lm.Engine(
                self.model_path,
                backend=self.backend,
                audio_backend=self.audio_backend,
                vision_backend=self.vision_backend,
            )
            logger.info("Model loaded successfully.")

    def getEngine(self) -> litert_lm.Engine:
        """Return the engine instance, loading it if necessary."""
        if self.engine is None:
            self.load()
        return self.engine

    @asynccontextmanager
    async def acquire(self):
        """Acquire the serialization lock and yield the engine for the full duration of inference.
        Ensures strictly one request at a time on memory-constrained edge hardware."""
        async with self._lock:
            yield self.getEngine()
