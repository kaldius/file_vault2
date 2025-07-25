from django.contrib.auth.models import AbstractUser
from django.db import models
import os


class User(AbstractUser):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    storage_quota = models.BigIntegerField(default=1073741824)  # 1GB default
    storage_used = models.BigIntegerField(default=0)

    def __str__(self):
        return self.username


class File(models.Model):
    """
    Stores unique files with deduplication based on SHA-256 hash
    """
    hash = models.CharField(max_length=64, unique=True, db_index=True)
    size = models.BigIntegerField(db_index=True)
    storage_path = models.TextField()
    mime_type = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'files'
        indexes = [
            models.Index(fields=['hash']),
            models.Index(fields=['size']),
            models.Index(fields=['mime_type']),
        ]

    def __str__(self):
        return f"File {self.hash[:8]}... ({self.size} bytes)"


class UserFile(models.Model):
    """
    Associates users with files, allowing multiple users to reference the same file
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_files')
    file = models.ForeignKey(File, on_delete=models.CASCADE, related_name='user_associations')
    original_filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True, db_index=True)
    tags = models.JSONField(default=list, blank=True)
    deleted = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = 'user_files'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'file', 'original_filename'],
                name='unique_user_file_name'
            )
        ]
        indexes = [
            models.Index(fields=['user', 'deleted']),
            models.Index(fields=['uploaded_at']),
            models.Index(fields=['original_filename']),
            models.Index(fields=['deleted']),
        ]

    def __str__(self):
        return f"{self.user.username}: {self.original_filename}" 