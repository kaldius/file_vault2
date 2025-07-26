from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.files.storage import default_storage
from django.db import transaction
import hashlib
import json
import mimetypes
import os
from .models import User, File, UserFile


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'password_confirm', 
                 'first_name', 'last_name', 'access', 'refresh')

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Password fields didn't match.")
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        # Add tokens to the user instance for serialization
        user.access = str(refresh.access_token)
        user.refresh = str(refresh)
        
        return user

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Structure response as specified in documentation
        return {
            'user': {
                'id': data['id'],
                'username': data['username'],
                'email': data['email'],
                'first_name': data['first_name'],
                'last_name': data['last_name']
            },
            'access': data['access'],
            'refresh': data['refresh']
        }


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError('Invalid username or password.')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled.')
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            attrs['user'] = user
            attrs['access'] = str(refresh.access_token)
            attrs['refresh'] = str(refresh)
            
        else:
            raise serializers.ValidationError('Must include username and password.')
        
        return attrs

    def to_representation(self, instance):
        user = instance['user']
        return {
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name
            },
            'access': instance['access'],
            'refresh': instance['refresh']
        }


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, attrs):
        self.token = attrs['refresh']
        return attrs

    def save(self, **kwargs):
        try:
            RefreshToken(self.token).blacklist()
        except TokenError:
            raise serializers.ValidationError('Invalid or expired refresh token.')


class FileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    tags = serializers.CharField(required=False, allow_blank=True)

    def validate_file(self, value):
        # Check file size (configurable via environment variable)
        max_size_mb = int(os.getenv('MAX_FILE_SIZE_MB', '100'))  # Default 100MB
        max_size = max_size_mb * 1024 * 1024  # Convert MB to bytes
        if value.size > max_size:
            raise serializers.ValidationError(f'File size cannot exceed {max_size_mb}MB')
        return value

    def validate_tags(self, value):
        if not value:
            return []
        
        try:
            tags = json.loads(value)
            if not isinstance(tags, list):
                raise serializers.ValidationError('Tags must be a JSON array')
            
            # Validate each tag
            for tag in tags:
                if not isinstance(tag, str):
                    raise serializers.ValidationError('Each tag must be a string')
                if len(tag) > 50:
                    raise serializers.ValidationError('Each tag must be 50 characters or less')
            
            return tags
        except json.JSONDecodeError:
            raise serializers.ValidationError('Tags must be valid JSON')

    def create(self, validated_data):
        user = self.context['request'].user
        uploaded_file = validated_data['file']
        tags = validated_data.get('tags', [])

        # Calculate SHA-256 hash
        file_hash = hashlib.sha256()
        for chunk in uploaded_file.chunks():
            file_hash.update(chunk)
        hash_hex = file_hash.hexdigest()

        # Reset file pointer
        uploaded_file.seek(0)

        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(uploaded_file.name)
        
        with transaction.atomic():
            # Check if file already exists
            existing_file = File.objects.filter(hash=hash_hex).first()
            
            if existing_file:
                # Check if user has a deleted file with this content and name
                deleted_user_file = UserFile.objects.filter(
                    user=user,
                    file=existing_file,
                    original_filename=uploaded_file.name,
                    deleted=True
                ).first()
                
                if deleted_user_file:
                    # Undelete the existing file
                    deleted_user_file.deleted = False
                    deleted_user_file.tags = tags  # Update tags
                    deleted_user_file.save()
                    
                    # Update user storage usage (restore the file size)
                    user.storage_used += existing_file.size
                    user.save()
                    
                    return deleted_user_file
                
                # Check if user already has this file with same name (not deleted)
                existing_user_file = UserFile.objects.filter(
                    user=user,
                    file=existing_file,
                    original_filename=uploaded_file.name,
                    deleted=False
                ).first()
                
                if existing_user_file:
                    raise serializers.ValidationError({
                        'file': 'You already have a file with this name and content'
                    })
                
                # Create new user file association (deduplication)
                user_file = UserFile.objects.create(
                    user=user,
                    file=existing_file,
                    original_filename=uploaded_file.name,
                    tags=tags
                )
                
                # Update user storage usage for the new association
                user.storage_used += existing_file.size
                user.save()
                
            else:
                # Create storage path using hash
                storage_path = f"files/{hash_hex[:2]}/{hash_hex[2:4]}/{hash_hex}"
                
                # Save file to storage
                saved_path = default_storage.save(storage_path, uploaded_file)
                
                # Create new file record
                file_obj = File.objects.create(
                    hash=hash_hex,
                    size=uploaded_file.size,
                    storage_path=saved_path,
                    mime_type=mime_type
                )
                
                # Create user file association
                user_file = UserFile.objects.create(
                    user=user,
                    file=file_obj,
                    original_filename=uploaded_file.name,
                    tags=tags
                )
                
                # Update user storage usage for the new file
                user.storage_used += uploaded_file.size
                user.save()

        return user_file

    def to_representation(self, instance):
        return {
            'id': instance.id,
            'original_filename': instance.original_filename,
            'uploaded_at': instance.uploaded_at.isoformat(),
            'tags': instance.tags,
            'size': instance.file.size,
            'mime_type': instance.file.mime_type,
            'file_hash': instance.file.hash
        } 


class FileListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing user files
    """
    size = serializers.IntegerField(source='file.size', read_only=True)
    mime_type = serializers.CharField(source='file.mime_type', read_only=True)
    file_hash = serializers.CharField(source='file.hash', read_only=True)

    class Meta:
        model = UserFile
        fields = ('id', 'original_filename', 'uploaded_at', 'tags', 'size', 'mime_type', 'file_hash')
        read_only_fields = ('id', 'uploaded_at', 'size', 'mime_type', 'file_hash')


class FileStatsSerializer(serializers.Serializer):
    """
    Serializer for user file storage statistics
    """
    total_files = serializers.IntegerField()
    total_size = serializers.IntegerField()
    storage_used = serializers.IntegerField()
    storage_quota = serializers.IntegerField()
    storage_percentage = serializers.FloatField()


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile information (/api/users/me/)
    """
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 
                 'created_at', 'storage_quota', 'storage_used')
        read_only_fields = ('id', 'username', 'email', 'created_at', 
                           'storage_quota', 'storage_used') 