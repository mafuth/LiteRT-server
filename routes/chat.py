import os
import uuid
import json
import base64
import time
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from lib.config import LLM_MODEL_FILENAME
from lib.classes.logger import LoggerManager

logger = LoggerManager(__name__)
router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: Union[str, List[Dict[str, Any]]]


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: bool = False
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None


@router.get("/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": LLM_MODEL_FILENAME,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "litert-lm",
            }
        ],
    }


def handle_content(msg: ChatMessage) -> Dict[str, Any]:
    """Parse OpenAI message and handle modalities like audio/images."""
    if isinstance(msg.content, str):
        return {"role": msg.role, "content": msg.content}

    new_content = []
    for item in msg.content:
        if item.get("type") == "text":
            new_content.append({"type": "text", "text": item["text"]})
        elif item.get("type") == "image_url":
            try:
                url = item.get("image_url", {}).get("url", "")
                if url.startswith("data:image/"):
                    header, encoded = url.split(",", 1)
                    ext = header.split(";")[0].split("/")[1]
                    data = base64.b64decode(encoded)
                    filepath = f"/tmp/{uuid.uuid4()}.{ext}"
                    with open(filepath, "wb") as f:
                        f.write(data)
                    new_content.append({"type": "image", "path": filepath})
            except Exception as e:
                logger.error(f"Failed to process image_url: {e}")
        elif item.get("type") == "input_audio":
            try:
                audio_data = item.get("input_audio", {}).get("data", "")
                audio_format = item.get("input_audio", {}).get("format", "wav")
                data = base64.b64decode(audio_data)
                filepath = f"/tmp/{uuid.uuid4()}.{audio_format}"
                with open(filepath, "wb") as f:
                    f.write(data)
                new_content.append({"type": "audio", "path": filepath})
            except Exception as e:
                logger.error(f"Failed to process input_audio: {e}")

    return {"role": msg.role, "content": new_content}


def _count_tokens(engine, text: str) -> int:
    """Return token count for text. Falls back to char-based estimate when
    engine.tokenize() is not available (litert-lm-api <= 0.10.1 ships only
    the C extension which does not expose tokenize())."""
    if hasattr(engine, "tokenize"):
        try:
            return len(engine.tokenize(text))
        except Exception as e:
            logger.warning(f"engine.tokenize() failed, falling back to estimate: {e}")
    return max(1, len(text) // 4)


@router.post("/chat/completions")
async def chat_completions(request: Request, body: ChatCompletionRequest):
    logger.info(f"Received chat completion request. Stream: {body.stream}")

    # acquire() holds the lock for the entire duration of the block,
    # ensuring strictly one request is processed at a time.
    async with request.app.state.llmEngine.acquire() as engine:
        processed_messages = [handle_content(msg) for msg in body.messages]

        if not processed_messages:
            raise HTTPException(status_code=400, detail="No messages provided.")

        history_multimedia = []
        history = []
        for msg in processed_messages[:-1]:
            if isinstance(msg["content"], list):
                text_parts = []
                for item in msg["content"]:
                    if item.get("type") == "text":
                        text_parts.append(item["text"])
                    elif item.get("type") in ["image", "audio"]:
                        history_multimedia.append(item)
                history.append({"role": msg["role"], "content": " ".join(text_parts)})
            else:
                history.append(msg)

        last_msg = processed_messages[-1]
        if history_multimedia:
            if isinstance(last_msg["content"], str):
                last_msg["content"] = history_multimedia + [{"type": "text", "text": last_msg["content"]}]
            else:
                last_msg["content"] = history_multimedia + last_msg["content"]

        logger.debug(f"Received input message: {last_msg}")

        if body.stream:
            def stream_generator():
                try:
                    start_time = time.time()
                    first_token_time = None
                    completion_text = ""

                    with engine.create_conversation(messages=history) as conversation:
                        stream = conversation.send_message_async(last_msg)
                        for chunk in stream:
                            content_list = chunk.get("content", [])
                            text = ""
                            for c in content_list:
                                if c.get("type") == "text":
                                    text += c["text"]

                            if text:
                                if first_token_time is None:
                                    first_token_time = time.time()
                                completion_text += text

                                chunk_data = {
                                    "id": f"chatcmpl-{uuid.uuid4()}",
                                    "object": "chat.completion.chunk",
                                    "created": int(time.time()),
                                    "model": body.model,
                                    "choices": [{"delta": {"content": text}}],
                                }
                                logger.debug(f"Received output message: {chunk_data}")
                                yield f"data: {json.dumps(chunk_data)}\n\n"

                        end_time = time.time()
                        total_elapsed = end_time - start_time
                        ttft = (first_token_time - start_time) if first_token_time else total_elapsed
                        num_tokens = _count_tokens(engine, completion_text)
                        gen_time = end_time - first_token_time if first_token_time else total_elapsed
                        tps = num_tokens / gen_time if gen_time > 0 else 0

                        logger.info(
                            f"Performance: TTFT={ttft:.4f}s, TPS={tps:.2f}, "
                            f"Total={total_elapsed:.4f}s, Tokens={num_tokens}"
                        )

                        stats_chunk = {
                            "id": f"chatcmpl-{uuid.uuid4()}",
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": body.model,
                            "choices": [],
                            "usage": {"completion_tokens": num_tokens},
                            "performance": {
                                "time_to_first_token": round(ttft, 4),
                                "tokens_per_second": round(tps, 2),
                                "total_elapsed_time": round(total_elapsed, 4),
                            },
                        }
                        yield f"data: {json.dumps(stats_chunk)}\n\n"
                        yield "data: [DONE]\n\n"
                except Exception as e:
                    logger.error(f"Error during streaming: {str(e)}")
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"

            return StreamingResponse(stream_generator(), media_type="text/event-stream")

        else:
            try:
                start_time = time.time()
                with engine.create_conversation(messages=history) as conversation:
                    response = conversation.send_message(last_msg)
                    end_time = time.time()

                    content_list = response.get("content", [])
                    text = ""
                    for c in content_list:
                        if c.get("type") == "text":
                            text += c["text"]

                    logger.debug(f"Received output message: {text}")

                    total_elapsed = end_time - start_time
                    num_tokens = _count_tokens(engine, text)
                    tps = num_tokens / total_elapsed if total_elapsed > 0 else 0

                    logger.info(
                        f"Performance: TPS={tps:.2f}, Total={total_elapsed:.4f}s, Tokens={num_tokens}"
                    )

                    return {
                        "id": f"chatcmpl-{uuid.uuid4()}",
                        "object": "chat.completion",
                        "created": int(time.time()),
                        "model": body.model,
                        "choices": [
                            {
                                "index": 0,
                                "message": {"role": "assistant", "content": text},
                                "finish_reason": "stop",
                            }
                        ],
                        "usage": {"completion_tokens": num_tokens},
                        "performance": {
                            "tokens_per_second": round(tps, 2),
                            "total_elapsed_time": round(total_elapsed, 4),
                        },
                    }
            except Exception as e:
                logger.error(f"Error during response generation: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
