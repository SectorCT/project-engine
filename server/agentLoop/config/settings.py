import os
from dotenv import load_dotenv

try:
    from django.conf import settings as django_settings
    from django.core.exceptions import ImproperlyConfigured
except Exception:  # pragma: no cover - Django not available for CLI usage
    django_settings = None
    ImproperlyConfigured = Exception


def _get_django_setting(name: str, default=None):
    if not django_settings:
        return default
    try:
        return getattr(django_settings, name, default)
    except ImproperlyConfigured:
        return default


load_dotenv()


class Settings:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or _get_django_setting("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", _get_django_setting("OPENAI_MODEL", "gpt-5.1"))
    MAX_DISCUSSION_ROUNDS = int(os.getenv("MAX_DISCUSSION_ROUNDS", str(_get_django_setting("MAX_DISCUSSION_ROUNDS", 10))))
    MAX_REQUIREMENTS_ROUNDS = int(os.getenv("MAX_REQUIREMENTS_ROUNDS", str(_get_django_setting("MAX_REQUIREMENTS_ROUNDS", 5))))
    OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", str(_get_django_setting("OPENAI_TEMPERATURE", 0.7))))
    CURSOR_API_KEY = os.getenv("CURSOR_API_KEY") or _get_django_setting("CURSOR_API_KEY")
    DOCKER_SOCKET_PATH = os.getenv("DOCKER_SOCKET_PATH") or _get_django_setting("DOCKER_SOCKET_PATH")


settings = Settings()
