import os
from dotenv import load_dotenv
from datetime import timedelta, timezone

# Load environment variables
load_dotenv()

# APP INFO
APP_TITLE = os.getenv('APP_TITLE', 'Edge AI API')
APP_DESCRIPTION = os.getenv('APP_DESCRIPTION', 'Running an Open AI API compatible server for LiteRT-LM.')
APP_VERSION = os.getenv('VERSION', os.getenv('APP_VERSION', '0.0.1'))
APP_ENV = os.getenv('APP_ENV', 'dev')

# App scaling and server configuration
UVICORN_WORKERS = int(os.getenv('UVICORN_WORKERS', '1'))
UVICORN_RELOAD = os.getenv('UVICORN_RELOAD', 'false').lower() == 'true'
UVICORN_HOST = os.getenv('UVICORN_HOST', '0.0.0.0')
UVICORN_PORT = int(os.getenv('UVICORN_PORT', '8000'))
UVICORN_LOOP = os.getenv('UVICORN_LOOP', 'asyncio')  # Use asyncio for cross-platform compatibility
UVICORN_HTTP = os.getenv('UVICORN_HTTP', 'httptools')  # Use httptools for better performance
UVICORN_ACCESS_LOG = os.getenv('UVICORN_ACCESS_LOG', 'false').lower() == 'true'

# CORS configuration
CORS_ALLOW_ORIGINS = [origin.strip() for origin in os.getenv('CORS_ALLOW_ORIGINS', '*').split(',') if origin.strip()]
CORS_ALLOW_CREDENTIALS = os.getenv('CORS_ALLOW_CREDENTIALS', 'true').lower() == 'true'
CORS_ALLOW_METHODS = [method.strip() for method in os.getenv('CORS_ALLOW_METHODS', '*').split(',') if method.strip()]
CORS_ALLOW_HEADERS = [header.strip() for header in os.getenv('CORS_ALLOW_HEADERS', '*').split(',') if header.strip()]

# Logging configuration
LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '3'))
LOG_ROTATION_INTERVAL = int(os.getenv('LOG_ROTATION_INTERVAL', '1'))
LOG_ROTATION_WHEN = os.getenv('LOG_ROTATION_WHEN', 'midnight')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE_PATH = os.getenv('LOG_FILE_PATH', 'logs/app.log')

# LLM Configuration
LLM_MODEL_FILENAME = os.getenv('LLM_MODEL', 'gemma4-4B')
LLM_BACKEND = os.getenv('LLM_BACKEND', 'CPU')
LLM_AUDIO_BACKEND = os.getenv('LLM_AUDIO_BACKEND', 'CPU')
LLM_VISION_BACKEND = os.getenv('LLM_VISION_BACKEND', 'CPU')