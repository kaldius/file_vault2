from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('token/refresh/', views.token_refresh, name='token_refresh'),
    path('files/upload/', views.file_upload, name='file_upload'),
    path('files/stats/', views.file_stats, name='file_stats'),
    path('files/<int:file_id>/', views.file_detail, name='file_detail'),
    path('files/<int:file_id>/download/', views.file_download, name='file_download'),
    path('files/<int:file_id>/delete/', views.file_delete, name='file_delete'),
    path('files/', views.file_list, name='file_list'),
] 