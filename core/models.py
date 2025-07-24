from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    storage_quota = models.BigIntegerField(default=1073741824)  # 1GB default
    storage_used = models.BigIntegerField(default=0)

    def __str__(self):
        return self.username 