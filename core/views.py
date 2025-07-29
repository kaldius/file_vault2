from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from django.utils.dateparse import parse_datetime
from .serializers import UserRegistrationSerializer, UserLoginSerializer, LogoutSerializer, FileUploadSerializer, FileListSerializer
from .models import UserFile


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


class FileListPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def file_list(request):
    """
    List user's files with search and filtering
    """
    user = request.user
    queryset = UserFile.objects.filter(user=user, deleted=False).select_related('file')

    # Search in filename and tags
    search = request.GET.get('search')
    if search:
        queryset = queryset.filter(
            Q(original_filename__icontains=search) |
            Q(tags__icontains=search)
        )

    # Filter by specific tag
    tag_filter = request.GET.get('tags')
    if tag_filter:
        queryset = queryset.filter(tags__icontains=tag_filter)

    # Filter by filename
    filename_filter = request.GET.get('filename')
    if filename_filter:
        queryset = queryset.filter(original_filename__icontains=filename_filter)

    # Filter by MIME type
    mime_type_filter = request.GET.get('mime_type')
    if mime_type_filter:
        queryset = queryset.filter(file__mime_type=mime_type_filter)

    # Filter by file size range
    size_min = request.GET.get('size_min')
    if size_min:
        try:
            queryset = queryset.filter(file__size__gte=int(size_min))
        except ValueError:
            pass

    size_max = request.GET.get('size_max')
    if size_max:
        try:
            queryset = queryset.filter(file__size__lte=int(size_max))
        except ValueError:
            pass

    # Filter by upload date range
    uploaded_after = request.GET.get('uploaded_after')
    if uploaded_after:
        try:
            date_after = parse_datetime(uploaded_after)
            if date_after:
                queryset = queryset.filter(uploaded_at__gte=date_after)
        except ValueError:
            pass

    uploaded_before = request.GET.get('uploaded_before')
    if uploaded_before:
        try:
            date_before = parse_datetime(uploaded_before)
            if date_before:
                queryset = queryset.filter(uploaded_at__lte=date_before)
        except ValueError:
            pass

    # Ordering
    ordering = request.GET.get('ordering', '-uploaded_at')
    # Map ordering fields to actual model fields
    ordering_map = {
        'uploaded_at': 'uploaded_at',
        '-uploaded_at': '-uploaded_at',
        'original_filename': 'original_filename',
        '-original_filename': '-original_filename',
        'file__size': 'file__size',
        '-file__size': '-file__size'
    }

    if ordering in ordering_map:
        queryset = queryset.order_by(ordering_map[ordering])
    else:
        queryset = queryset.order_by('-uploaded_at')

    # Pagination
    paginator = FileListPagination()
    page = paginator.paginate_queryset(queryset, request)
    if page is not None:
        serializer = FileListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    serializer = FileListSerializer(queryset, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def file_detail(request, file_id):
    """
    Get detailed information about a specific file
    """
    user = request.user
    
    try:
        user_file = UserFile.objects.select_related('file').get(
            id=file_id,
            user=user,
            deleted=False
        )
    except UserFile.DoesNotExist:
        return Response(
            {'error': 'File not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = FileListSerializer(user_file)
    return Response(serializer.data)





@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def file_delete(request, file_id):
    """
    Delete a user file. If no other users own the file, physically delete it from storage.
    """
    from django.core.files.storage import default_storage
    from django.db import transaction
    
    user = request.user
    
    try:
        user_file = UserFile.objects.select_related('file').get(
            id=file_id,
            user=user,
            deleted=False
        )
    except UserFile.DoesNotExist:
        return Response(
            {'error': 'File not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    file_obj = user_file.file
    
    with transaction.atomic():
        # Perform soft delete
        user_file.deleted = True
        user_file.save()
        
        # Update user storage usage
        user.storage_used -= file_obj.size
        user.save()
        
        # Check if any other users still have non-deleted associations with this file
        remaining_associations = UserFile.objects.filter(
            file=file_obj,
            deleted=False
        ).exists()
        
        # If no users own this file anymore, physically delete it
        if not remaining_associations:
            try:
                if default_storage.exists(file_obj.storage_path):
                    default_storage.delete(file_obj.storage_path)
                # Also delete the File record from database
                file_obj.delete()
            except Exception as e:
                # Log the error but don't fail the request since the user association was already deleted
                # This prevents orphaned file records in case of storage deletion failure
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to delete physical file {file_obj.storage_path}: {str(e)}")
    
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def file_download(request, file_id):
    """
    Download file content
    """
    from django.http import FileResponse
    from django.core.files.storage import default_storage
    import os
    
    user = request.user
    
    try:
        user_file = UserFile.objects.select_related('file').get(
            id=file_id,
            user=user,
            deleted=False
        )
    except UserFile.DoesNotExist:
        return Response(
            {'error': 'File not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    file_obj = user_file.file
    
    # Check if file exists in storage
    if not default_storage.exists(file_obj.storage_path):
        return Response(
            {'error': 'File not found in storage'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Open file and return as response
    file_handle = default_storage.open(file_obj.storage_path)
    
    response = FileResponse(
        file_handle,
        content_type=file_obj.mime_type or 'application/octet-stream'
    )
    
    # Set appropriate headers
    response['Content-Disposition'] = f'attachment; filename="{user_file.original_filename}"'
    response['Content-Length'] = file_obj.size
    
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """
    Get current user's profile information
    """
    from .serializers import UserProfileSerializer
    
    user = request.user
    serializer = UserProfileSerializer(user)
    return Response(serializer.data) 