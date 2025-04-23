# keepmesafe/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('create_profile/', views.create_profile, name='create_profile'),
    path('profile_created/<uuid:profile_id>/', views.profile_created, name='profile_created'),
    path('', views.login_profile, name='login_profile_input'),
    path('profile_accessed/<uuid:profile_id>/', views.profile_accessed, name='profile_accessed'),
    path('vault/close/', views.close_vault, name='close_vault'),
    path('vault/delete/<uuid:profile_id>/', views.delete_vault, name='delete_vault'),
    path('admin-auth/', views.admin_gate, name='admin_gate'),
]

