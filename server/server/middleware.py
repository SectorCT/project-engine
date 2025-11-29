import urllib.parse

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken


class JWTAuthMiddleware(BaseMiddleware):
    """
    Channels middleware that attaches a JWT-authenticated user to the scope.

    Accepts tokens either via the Authorization header (Bearer ...) or the query
    string (?token=... / ?access_token=...).
    """

    def __init__(self, inner):
        super().__init__(inner)
        self.jwt_auth = JWTAuthentication()

    async def __call__(self, scope, receive, send):
        scope['user'] = AnonymousUser()
        close_old_connections()

        token = self._get_token_from_scope(scope)
        if token:
            try:
                validated = self.jwt_auth.get_validated_token(token)
                user = await database_sync_to_async(self.jwt_auth.get_user)(validated)
                scope['user'] = user
            except InvalidToken as e:
                # Log invalid token for debugging (only in DEBUG mode to avoid log spam)
                if settings.DEBUG:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Invalid token in WebSocket connection: {str(e)}")
        else:
            # Log missing token for debugging (only in DEBUG mode)
            if settings.DEBUG:
                import logging
                logger = logging.getLogger(__name__)
                is_websocket = scope.get('type') == 'websocket'
                query_string = scope.get('query_string', b'').decode()
                logger.warning(
                    f"No token found in WebSocket connection. "
                    f"Type: {scope.get('type')}, "
                    f"Has query string: {bool(query_string)}, "
                    f"Query: {query_string[:100] if query_string else 'none'}"
                )

        return await super().__call__(scope, receive, send)

    def _get_token_from_scope(self, scope):
        headers = dict(scope.get('headers') or [])
        auth_header = headers.get(b'authorization')
        if auth_header:
            try:
                auth_header = auth_header.decode()
            except UnicodeDecodeError:
                return None
            if auth_header.lower().startswith('bearer '):
                return auth_header.split(' ', 1)[1].strip()

        # For WebSocket connections, browsers cannot set custom headers,
        # so we must check query parameters as a fallback.
        # This is necessary for browser-based WebSocket clients.
        # The ALLOW_WS_TOKEN_QUERY setting controls whether query tokens are accepted,
        # but for WebSocket connections from browsers, this is the only option.
        allow_query = getattr(settings, 'ALLOW_WS_TOKEN_QUERY', settings.DEBUG)
        
        # Always allow query tokens for WebSocket connections (protocol is 'websocket')
        # since browsers cannot send custom headers. For HTTP, respect the setting.
        is_websocket = scope.get('type') == 'websocket'
        
        if not allow_query and not is_websocket:
            return None

        query_string = scope.get('query_string', b'').decode()
        if query_string:
            params = urllib.parse.parse_qs(query_string)
            for key in ('token', 'access_token'):
                if key in params and params[key]:
                    return params[key][0]
        return None

