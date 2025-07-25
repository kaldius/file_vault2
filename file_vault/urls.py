from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('api/auth/', include('core.urls')),
    path('api/', include('core.urls')),
] 