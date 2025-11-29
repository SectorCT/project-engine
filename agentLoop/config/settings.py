import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    MAX_DISCUSSION_ROUNDS = int(os.getenv("MAX_DISCUSSION_ROUNDS", "10"))
    MAX_REQUIREMENTS_ROUNDS = int(os.getenv("MAX_REQUIREMENTS_ROUNDS", "5"))
    OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    CURSOR_API_KEY = os.getenv("CURSOR_API_KEY")
    DOCKER_SOCKET_PATH = os.getenv("DOCKER_SOCKET_PATH") # Optional: custom docker socket

settings = Settings()
