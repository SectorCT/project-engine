from rest_framework import status, views
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from google.oauth2 import id_token
from google.auth.transport import requests
from django.conf import settings

from .models import User
from .serializers import LoginSerializer, RegisterSerializer, UserSerializer


class RegisterView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            user_data = UserSerializer(user).data
            return Response(
                {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                    'user': user_data,
                },
                status=status.HTTP_201_CREATED,
            )

        error_messages = " ".join([" ".join(messages) for messages in serializer.errors.values()])
        return Response({"detail": error_messages}, status=status.HTTP_400_BAD_REQUEST)


class LoginView(views.APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            user_data = UserSerializer(user).data
            return Response(
                {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                    "user": user_data,
                },
                status=status.HTTP_200_OK,
            )
        error_messages = " ".join([" ".join(messages) for messages in serializer.errors.values()])
        return Response({"detail": error_messages}, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if refresh_token is None:
            return Response({"detail": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception as exc:  # pragma: no cover - defensive path
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"detail": "Logout successful."}, status=status.HTTP_205_RESET_CONTENT)


class UserListView(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request):
        users = User.objects.all().order_by('-date_joined')
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CurrentUserView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class GoogleLoginView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        token = request.data.get('credential')  # Google sends the token as 'credential'
        
        if not token:
            return Response(
                {"detail": "Google credential token is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        google_client_id = settings.GOOGLE_CLIENT_ID
        if not google_client_id:
            return Response(
                {"detail": "Google OAuth is not configured on the server."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            # Verify the Google ID token
            idinfo = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                google_client_id
            )

            # Verify the token was issued to our client
            if idinfo['aud'] != google_client_id:
                return Response(
                    {"detail": "Invalid token audience."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Extract user information
            google_id = idinfo['sub']
            email = idinfo['email']
            name = idinfo.get('name', '')
            email_verified = idinfo.get('email_verified', False)

            if not email_verified:
                return Response(
                    {"detail": "Email address not verified by Google."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Try to find existing user by google_id or email
            user = None
            try:
                user = User.objects.get(google_id=google_id)
            except User.DoesNotExist:
                try:
                    user = User.objects.get(email=email)
                    # Link Google account to existing user
                    user.google_id = google_id
                    user.save()
                except User.DoesNotExist:
                    # Create new user - UserManager will auto-generate unique username
                    user = User.objects.create_user(
                        email=email,
                        username=None,  # Let UserManager generate unique username
                        name=name,
                        google_id=google_id,
                        password=None  # OAuth users don't have passwords
                    )

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            user_data = UserSerializer(user).data

            return Response(
                {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                    'user': user_data,
                },
                status=status.HTTP_200_OK
            )

        except ValueError as e:
            # Invalid token
            return Response(
                {"detail": f"Invalid Google token: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"detail": f"Error authenticating with Google: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )