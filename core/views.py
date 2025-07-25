from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenRefreshView
from .serializers import UserRegistrationSerializer, UserLoginSerializer, LogoutSerializer, FileUploadSerializer


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    Register a new user account
    """
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response(serializer.to_representation(user), status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    Authenticate user and get JWT tokens
    """
    serializer = UserLoginSerializer(data=request.data)
    if serializer.is_valid():
        return Response(serializer.to_representation(serializer.validated_data), status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    Blacklist refresh token (logout)
    """
    serializer = LogoutSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(status=status.HTTP_205_RESET_CONTENT)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Use the built-in TokenRefreshView for token refresh functionality
token_refresh = TokenRefreshView.as_view()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def file_upload(request):
    """
    Upload a new file with automatic deduplication
    """
    serializer = FileUploadSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        user_file = serializer.save()
        return Response(serializer.to_representation(user_file), status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST) 