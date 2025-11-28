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
            except InvalidToken:
                pass

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

        if not getattr(settings, 'ALLOW_WS_TOKEN_QUERY', settings.DEBUG):
            return None

        query_string = scope.get('query_string', b'').decode()
        if query_string:
            params = urllib.parse.parse_qs(query_string)
            for key in ('token', 'access_token'):
                if key in params and params[key]:
                    return params[key][0]
        return None

