# keepmesafe/urls.py
from django.urls import path
from .views import profile_accessed, create_profile, profile_created, close_vault, delete_vault, admin_gate, login_profile

urlpatterns = [
    path('create_profile/', create_profile, name='create_profile'),
    path('profile_created/<uuid:profile_id>/', profile_created, name='profile_created'),
    path('', login_profile, name='login_profile_input'),
    path('profile_accessed/<uuid:profile_id>/', profile_accessed, name='profile_accessed'),
    path('vault/close/', close_vault, name='close_vault'),
    path('vault/delete/<uuid:profile_id>/', delete_vault, name='delete_vault'),
    path('admin-auth/', admin_gate, name='admin_gate'),
]

